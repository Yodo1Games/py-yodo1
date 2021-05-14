import os
from typing import Generator

import pytest
import requests_mock
from fastapi.testclient import TestClient

os.environ['EVA_API_ENV'] = 'ci'
from example_api.main import app
from example_api.keys import PUBLIC_KEY, PUBLIC_KEY_URL


@pytest.fixture
def client() -> Generator:
    """
    Generate test client
    :return:
    """
    with requests_mock.Mocker(real_http=True) as m:
        m.get(PUBLIC_KEY_URL, text=PUBLIC_KEY)
        with TestClient(app) as c:
            yield c
