import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


PASSWORD = "correct-horse-battery"


def register(client, email="a@example.com", password=PASSWORD, **extra):
    return client.post("/api/auth/register", json={"email": email, "password": password, **extra})


def signup(client, email="a@example.com", **extra):
    """Register and return Authorization headers."""
    body = register(client, email, **extra).get_json()
    return {"Authorization": f"Bearer {body['access_token']}"}


@pytest.fixture()
def auth(client):
    return signup(client)
