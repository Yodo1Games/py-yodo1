import os
from typing import Dict

from fastapi import Depends
from sqlalchemy import create_engine

from yodo1.sqlalchemy import DBManager
from yodo1.sso import JWTHelper, JWTPayload

# Define db base engine
APP_PATH = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

sqlite_path = os.path.join(APP_PATH, 'test-db.sqlite')
db_rui = f"sqlite:///{sqlite_path}"
engine = create_engine(
    db_rui, connect_args={"check_same_thread": False}
)

# Define auth helper
auth = JWTHelper()
# Define db manager
db = DBManager(engine=engine)


# Define helper class
# This is to add custom operation after get user info, like setup APM context
# https://www.elastic.co/guide/en/apm/agent/python/master/api.html#api-set-user-context
def get_current_user_dict(payload: JWTPayload = Depends(auth.current_payload)) -> Dict:
    return {
        'sub': payload.sub,
        'email': payload.email,
        'name': payload.name
    }


__all__ = [
    'auth',
    'db',
    'engine',
    'get_current_user_dict'
]
