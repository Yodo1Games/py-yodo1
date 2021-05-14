from fastapi.testclient import TestClient

from example_api.base import db
from example_api.model import ItemModel


def test_db(client: TestClient) -> None:
    session = db.SessionLocal()
    total_count = session.query(ItemModel).count()

    model = ItemModel(
        title=f'Title {total_count + 1}'
    )
    session.add(model)
    session.commit()
    session.close()

    res = client.get('/items')
    items = res.json()
    assert len(items) > 0
