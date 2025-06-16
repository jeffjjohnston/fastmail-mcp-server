import os
import json
from unittest.mock import patch
from pathlib import Path
import sys

from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Set token before importing server
TEST_TOKEN = "test-token"
os.environ["BEARER_TOKEN"] = TEST_TOKEN

import server
from fastmail import EmailPage, Email


def create_app():
    server.mcp.settings.stateless_http = True
    server.mcp.settings.json_response = True
    app = server.mcp.http_app()
    app.add_middleware(server.BearerAuthMiddleware)
    return app


def call_tool(client: TestClient, name: str, args: dict | None = None, *, include_api_token: bool = True):
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": args or {}},
    }
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
    }
    if include_api_token:
        headers["fastmail-api-token"] = "api-token"
    return client.post("/mcp/", data=json.dumps(message), headers=headers)


def test_list_inbox_emails_endpoint():
    app = create_app()
    page = EmailPage(
        emails=[Email(id="e1", sender="Alice <a@example.com>", subject="Hi", date="2024-01-02")],
        offset=0,
        total=1,
    )
    expected = server.display_email_page(page)
    with patch("server.fastmail_list_inbox_emails", return_value=page):
        with TestClient(app) as client:
            resp = call_tool(client, "list_inbox_emails", {"offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"]["isError"] is False
    assert data["result"]["content"][0]["text"] == expected


def test_query_emails_by_keyword_endpoint():
    app = create_app()
    page = EmailPage(
        emails=[Email(id="e1", sender="Bob <b@example.com>", subject="Meeting", date="2024-02-03")],
        offset=0,
        total=1,
    )
    expected = server.display_email_page(page)
    with patch("server.fastmail_query_emails_by_keyword", return_value=page):
        with TestClient(app) as client:
            resp = call_tool(client, "query_emails_by_keyword", {"keyword": "meet", "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert not data["result"]["isError"]
    assert data["result"]["content"][0]["text"] == expected


def test_get_email_content_endpoint():
    app = create_app()
    with patch("server.fastmail_get_email_content", return_value="the body"):
        with TestClient(app) as client:
            resp = call_tool(client, "get_email_content", {"email_id": "e1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"]["isError"] is False
    assert data["result"]["content"][0]["text"] == "Content of email e1:\nthe body"


def test_missing_api_token_header():
    app = create_app()
    with patch("server.fastmail_list_inbox_emails", return_value=None):
        with TestClient(app) as client:
            resp = call_tool(client, "list_inbox_emails", {"offset": 0}, include_api_token=False)
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"]["isError"] is True
    assert "Fastmail API token is required" in data["result"]["content"][0]["text"]
