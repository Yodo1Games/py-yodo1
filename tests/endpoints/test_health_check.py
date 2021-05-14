from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    r = client.get(f"/health_check")
    assert r.status_code == 200
