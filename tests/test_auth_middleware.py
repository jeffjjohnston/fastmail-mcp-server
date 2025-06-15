import os

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

# Set up test token before importing the middleware
TEST_TOKEN = "test-token"
os.environ["BEARER_TOKEN"] = TEST_TOKEN

from server import BearerAuthMiddleware


def dummy_endpoint(request):
    return PlainTextResponse("ok")


def create_app():
    app = Starlette(routes=[Route("/dummy", dummy_endpoint)])
    app.add_middleware(BearerAuthMiddleware)
    return app


def test_missing_authorization_header():
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/dummy")
    assert response.status_code == 401


def test_incorrect_token():
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/dummy", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401


def test_correct_token():
    app = create_app()
    with TestClient(app) as client:
        response = client.get(
            "/dummy", headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
    assert response.status_code == 200
    assert response.text == "ok"
