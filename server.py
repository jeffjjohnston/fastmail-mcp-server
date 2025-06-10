"""Basic Fastmail MCP Server"""

import os
import logging

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
from fastmail import (
    EmailPage,
    fastmail_list_inbox_emails,
    fastmail_get_email_content,
    fastmail_query_emails_by_keyword,
)

load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Static key from the environment for authorization
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
if not BEARER_TOKEN:
    raise ValueError("BEARER_TOKEN environment variable is not set.")


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to handle Bearer token authentication."""

    async def dispatch(self, request: Request, call_next):
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer ") or auth.split(" ", 1)[1] != BEARER_TOKEN:
            logger.warning("Unauthorized request to %s", request.url.path)
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
    logger.debug("Received Fastmail API token in request")
    return api_token


# Initialize the MCP server
mcp = FastMCP("Fastmail Manager")


@mcp.tool(name="list_inbox_emails")
def list_inbox_emails(offset: int) -> str:
    """List all emails in the inbox.

    Returns:
        List of emails, including id, sender, subject, and date
    """
    logger.info("Listing inbox emails (offset=%s)", offset)
    fastmail_api_token = get_fastmail_api_token()
    email_page: EmailPage = fastmail_list_inbox_emails(
        fastmail_api_token, offset=offset
    )
    logger.debug("Retrieved %s emails", len(email_page.emails))
    if not email_page.emails:
        return f"No emails found in the inbox with offset {offset}."

    email_list = [
        (
            f"\nemail_id: {email.id}\nFrom: {email.sender}\n"
            f"Subject: {email.subject}\nDate: {email.date}\n"
        )
        for email in email_page.emails
    ]
    return (
        f"Total inbox emails: {email_page.total}\n"
        + f"Current page (offset {offset}) of inbox emails:\n"
        + "\n".join(email_list)
    )


@mcp.tool(name="query_emails_by_keyword")
def query_emails_by_keyword(keyword: str, offset: int = 0) -> str:
    """Query emails in the inbox by a keyword in the subject or body.

    Args:
        keyword: The keyword to search for in the emails
        offset: The offset for pagination (default is 0)
    Returns:
        The total number of emails matching the keyword and a list of emails
        (up to 30) matching the keyword, including id, sender, subject, and date
    """
    logger.info("Querying emails by keyword '%s' (offset=%s)", keyword, offset)
    fastmail_api_token = get_fastmail_api_token()
    if not keyword:
        return "Keyword is required for searching emails."
    try:
        email_page: EmailPage = fastmail_query_emails_by_keyword(
            fastmail_api_token, keyword, offset=offset
        )
        logger.debug("Query returned %s emails", len(email_page.emails))
        if not email_page.emails:
            return (
                "No emails found matching the keyword "
                + f"'{keyword}' with offset {offset}."
            )

        email_list = [
            (
                f"\nemail_id: {email.id}\nFrom: {email.sender}\n"
                f"Subject: {email.subject}\nDate: {email.date}\n"
            )
            for email in email_page.emails
        ]
        return (
            f"Total emails matching '{keyword}': {email_page.total}\n"
            f"Current page (offset {offset}) of emails:\n"
            "\n".join(email_list)
        )
    except ValueError as e:
        logger.error("Error querying emails: %s", e)
        return f"Error querying emails: {str(e)}"


@mcp.tool(name="get_email_content")
def get_email_content(email_id: str) -> str:
    """Get the content of an email by its ID.

    Args:
        email_id: The ID of the email to retrieve

    Returns:
        The content of the email (up to 1MB), or an error message if the email is not
        found
    """
    logger.info("Getting content for email %s", email_id)
    fastmail_api_token = get_fastmail_api_token()
    if not email_id:
        return "Email ID is required."
    try:
        content = fastmail_get_email_content(fastmail_api_token, email_id)
        logger.debug("Retrieved content length %s", len(content))
        return f"Content of email {email_id}:\n{content}"
    except ValueError as e:
        logger.error("Error retrieving email content: %s", e)
        return f"Error retrieving email content: {str(e)}"


if __name__ == "__main__":
    mcp.settings.stateless_http = True
    app = mcp.http_app()
    app.add_middleware(BearerAuthMiddleware)

    logger.info("Starting Fastmail MCP server on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
