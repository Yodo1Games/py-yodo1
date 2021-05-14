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

    client.get('/setup_auth_public_key')

    r = client.get("/secret_data", headers={
        'Authorization': f"Bearer {token}"
    })
    assert r.status_code == 200

    assert r.json()['user']['sub'] == '1234567890'
