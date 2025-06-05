"""Basic Fastmail MCP Server"""

import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
from fastmail import Email, fastmail_list_inbox_emails, fastmail_get_email_content

load_dotenv()

# Static key from the environment for authorization
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
if not BEARER_TOKEN:
    raise ValueError("BEARER_TOKEN environment variable is not set.")


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to handle Bearer token authentication."""

    async def dispatch(self, request: Request, call_next):
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer ") or auth.split(" ", 1)[1] != BEARER_TOKEN:
            return JSONResponse(
                content={"error": "Unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="FastMCP"'},
            )

        response = await call_next(request)
        return response


def get_fastmail_api_token() -> str:
    """Get the Fastmail API token from the request headers."""
    request = get_http_request()
    api_token = request.headers.get("fastmail-api-token")
    if not api_token:
        raise ValueError("Fastmail API token is required in the request headers.")
    return api_token


# Initialize the MCP server
mcp = FastMCP("Fastmail Manager")


@mcp.tool(name="list_inbox_emails")
def list_inbox_emails() -> str:
    """List all emails in the inbox.

    Returns:
        List of emails, including id, sender, subject, and date
    """
    fastmail_api_token = get_fastmail_api_token()
    emails: list[Email] = fastmail_list_inbox_emails(fastmail_api_token)
    if not emails:
        return "No emails found in the inbox."

    email_list = [
        (
            f"\nemail_id: {email.id}\nFrom: {email.sender}\n"
            f"Subject: {email.subject}\nDate: {email.date}\n"
        )
        for email in emails
    ]
    return f"Current inbox emails:\n{"\n".join(email_list)}"


@mcp.tool(name="get_email_content")
def get_email_content(email_id: str) -> str:
    """Get the content of an email by its ID.

    Args:
        email_id: The ID of the email to retrieve

    Returns:
        The content of the email
    """
    fastmail_api_token = get_fastmail_api_token()
    if not email_id:
        return "Email ID is required."
    try:
        content = fastmail_get_email_content(fastmail_api_token, email_id)
        return f"Content of email {email_id}:\n{content}"
    except ValueError as e:
        return f"Error retrieving email content: {str(e)}"


if __name__ == "__main__":
    mcp.settings.stateless_http = True
    app = mcp.http_app()
    app.add_middleware(BearerAuthMiddleware)

    uvicorn.run(app, host="127.0.0.1", port=8000)
