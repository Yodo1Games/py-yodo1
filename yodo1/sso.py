import logging
from datetime import datetime, timedelta
from typing import Optional, List

import jwt
import requests
from cachetools import cached, TTLCache
from fastapi import HTTPException, Security, Request
from fastapi.openapi.models import HTTPBearer as HTTPBearerModel
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from pydantic import BaseModel, Field
from starlette.status import HTTP_401_UNAUTHORIZED
import elasticapm


class HTTPBearerWithCookie(HTTPBearer):
    def __init__(
        self,
        *,
        bearerFormat: Optional[str] = None,
        scheme_name: Optional[str] = None,
        auto_error: bool = True,
    ):
        self.model = HTTPBearerModel(bearerFormat=bearerFormat)
        self.scheme_name = scheme_name or self.__class__.__name__
        self.auto_error = auto_error

    async def __call__(
        self, request: Request
    ) -> Optional[HTTPAuthorizationCredentials]:
        authorization_in_request: str = request.headers.get("Authorization")
        authorization_in_cookie: str = request.cookies.get("Authorization")
        if authorization_in_request:
            scheme, credentials = get_authorization_scheme_param(authorization_in_request)
        elif authorization_in_cookie:
            scheme, credentials = get_authorization_scheme_param(authorization_in_cookie)
        else:
            scheme, credentials = None, None
        if not (scheme and credentials):
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED, detail="Not authenticated"
                )
            else:
                return None
        if scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                )
            else:
                return None
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)


def _exp_default_factory(expire_hours: int = 168) -> datetime:
    return datetime.utcnow() + timedelta(hours=expire_hours)


class JWTPayload(BaseModel):
    sub: str
    email: str
    name: str
    scope: List[str]
    exp: datetime = Field(default_factory=_exp_default_factory)
    iat: datetime = Field(default_factory=datetime.utcnow)


class JWTHelper:
    def __init__(self) -> None:
        self.public_key: Optional[str] = None
        self.private_key: Optional[str] = None
        self.public_key_url: Optional[str] = None
        self.scope: Optional[str] = None

    @cached(cache=TTLCache(maxsize=1024, ttl=1800))
    def _fetch_public_key(self, url: str) -> str:
        try:
            response = requests.get(url)
            assert response.text.startswith('-----BEGIN PUBLIC KEY-----')
            self.public_key = response.text
        except Exception:  # flake8: noqa
            logging.error("Update public key from sso server failed.")

        if self.public_key is None:
            raise ValueError("No initial public key exists")

        return self.public_key

    def setup_with_sso_server(self, url: str, scope: Optional[str] = None) -> None:
        self.public_key = self._fetch_public_key(url=url)
        self.public_key_url = url
        self.scope = scope

    def setup_keys(self,
                   public_key: str,
                   private_key: Optional[str] = None) -> None:
        self.public_key = public_key
        self.private_key = private_key

    def encode_token(self, payload: JWTPayload) -> str:
        if self.private_key is None:
            raise ValueError('Need to setup `private_key` before call `encode_token`')
        token = jwt.encode(
            payload.dict(),
            self.private_key,
            algorithm='RS256'
        )

        # in macos, jwt.encode return bytes instead of string, so this is an ugly patch
        if isinstance(token, bytes):
            token_str = token.decode()
        else:
            token_str = token

        return token_str

    def decode_token(self, token: str) -> JWTPayload:
        if self.public_key_url:
            self.public_key = self._fetch_public_key(url=self.public_key_url)
        try:
            payload = jwt.decode(token, self.public_key, algorithms=['RS256'])
            return JWTPayload(**payload)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail='Token expired')
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail='Invalid token')

    def current_payload(self,
                        credentials: HTTPAuthorizationCredentials = Security(HTTPBearerWithCookie())
                        ) -> JWTPayload:
        token = credentials.credentials
        payload = self.decode_token(token)
        if self.scope:
            if self.scope not in payload.scope:
                raise HTTPException(status_code=401, detail='Invalid scope')
        elasticapm.set_user_context(username=payload.name, email=payload.email, user_id=payload.sub)
        return payload


__all__ = [
    'JWTHelper',
    'JWTPayload',
    'HTTPBearerWithCookie',
]
