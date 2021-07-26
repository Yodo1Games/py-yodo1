import datetime

from fastapi.testclient import TestClient


def test_login_with_keys(client: TestClient) -> None:
    from example_api.main import auth
    from example_api.keys import PUBLIC_KEY, PRIVATE_KEY
    from yodo1.sso import JWTPayload

    auth.public_key = PUBLIC_KEY
    auth.private_key = PRIVATE_KEY

    user_payload = JWTPayload(**{
        "sub": "1234567890",
        "name": "John Doe",
        "scope": [],
        "email": "test@yodo1.com"
    })

    token = auth.encode_token(payload=user_payload)

    r = client.get("/secret_data", headers={
        'Authorization': f"Bearer {token}"
    })
    assert r.status_code == 200

    assert r.json()['user']['sub'] == '1234567890'

    # Test No Token
    r = client.get("/secret_data")
    assert r.status_code == 401

    # Test Fake Token
    r = client.get("/secret_data", headers={
        'Authorization': f"Bearer fake-token"
    })
    assert r.status_code == 401

    # Test Expired Token
    user_payload.exp = datetime.datetime.utcnow() - datetime.timedelta(hours=1)

    token = auth.encode_token(payload=user_payload)

    r = client.get("/secret_data", headers={
        'Authorization': f"Bearer {token}"
    })
    assert r.status_code == 401

    # Test Right Scope
    right_scope_user_payload = JWTPayload(**{
        "sub": "1234567890",
        "name": "John Doe",
        "scope": ['secret_service'],
        "email": "test@yodo1.com"
    })

    token = auth.encode_token(payload=right_scope_user_payload)
    auth.scope = 'secret_service'
    r = client.get("/secret_data", headers={
        'Authorization': f"Bearer {token}"
    })
    assert r.status_code == 200

    # Test Wrong Scope
    right_scope_user_payload = JWTPayload(**{
        "sub": "1234567890",
        "name": "John Doe",
        "scope": ['secret_service'],
        "email": "test@yodo1.com"
    })

    token = auth.encode_token(payload=right_scope_user_payload)
    auth.scope = 'very_secret_service'
    r = client.get("/secret_data", headers={
        'Authorization': f"Bearer {token}"
    })
    assert r.status_code == 401
