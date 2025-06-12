"""Shared module for Fastmail JMAP client operations."""

import re
import logging
from dataclasses import dataclass
from bs4 import BeautifulSoup
from jmapc import (
    Client,
    Comparator,
    EmailQueryFilterCondition,
    MailboxQueryFilterCondition,
    Ref,
)
from jmapc.methods import (
    EmailGet,
    EmailQuery,
    MailboxGet,
    MailboxGetResponse,
    MailboxQuery,
)

FASTMAIL_API_HOST = "api.fastmail.com/jmap/session"

logger = logging.getLogger(__name__)


@dataclass
class EmailPage:
    """Data class to represent a page of emails."""

    emails: list["Email"]
    offset: int
    total: int


@dataclass
class Email:
    """Data class to represent an email."""

    id: str
    sender: str
    subject: str
    date: str


# create MailboxNotFound exception
class MailboxNotFound(Exception):
    """Exception raised when the mailbox is not found on the server."""


def format_addresses(addresses: list) -> str:
    """Format email addresses for display."""
    return ", ".join(
        f"{address.name} <{address.email}>" if address.name else address.email
        for address in addresses
    )


def normalize_whitespace(text):
    """Normalize whitespace in a string."""
    # Replace multiple spaces or tabs with a single space
    text = re.sub(r"[ \t]+", " ", text)
    # Replace multiple newlines with a single newline
    text = re.sub(r"\n+", "\n", text)
    # Strip leading/trailing whitespace
    return text.strip()


def get_body_as_text(email) -> str:
    """Convert body values to text."""
    if not email.body_values:
        return ""

    html_parts = set()
    text_parts = set()

    for body_part in email.text_body:
        if body_part.type == "text/html":
            html_parts.add(body_part.part_id)
        else:
            text_parts.add(body_part.part_id)
    for body_part in email.html_body:
        if body_part.type == "text/html":
            html_parts.add(body_part.part_id)
        else:
            text_parts.add(body_part.part_id)

    body_text = ""
    if html_parts:
        for part_id in html_parts:
            body_text += (
                BeautifulSoup(
                    email.body_values.get(part_id).value, "html.parser"
                ).get_text()
                + "\n"
            )
    elif text_parts:
        for part_id in text_parts:
            body_text += email.body_values.get(part_id).value + "\n"
    return normalize_whitespace(body_text)


def get_client(api_token: str) -> Client:
    """Create and return a Fastmail JMAP client instance."""
    logger.debug("Creating Fastmail client")
    client = Client.create_with_api_token(host=FASTMAIL_API_HOST, api_token=api_token)
    return client


def get_mailbox_id_for_role(client: Client, role: str) -> str | None:
    """Get the ID of the mailbox for a specific role."""
    logger.debug("Fetching mailbox ID for role: %s", role)
    results = client.request(
        [
            MailboxQuery(filter=MailboxQueryFilterCondition(role=role)),
            MailboxGet(ids=Ref("/ids")),
        ]
    )
    assert isinstance(
        results[1].response, MailboxGetResponse
    ), "Error in Mailbox/get method"
    mailbox_data = results[1].response.data
    if not mailbox_data:
        return None

    mailbox_id = mailbox_data[0].id
    assert mailbox_id
    return mailbox_id


def fastmail_list_inbox_emails(api_token: str, offset: int = 0) -> EmailPage:
    """List all emails in the inbox.

    Returns:
        EmailPage object containing a list of up to 30 Email objects and pagination info
    """
    logger.debug("Listing inbox emails (offset=%s)", offset)
    client = get_client(api_token)
    inbox_id = get_mailbox_id_for_role(client, "inbox")
    if not inbox_id:
        logger.error("Inbox mailbox not found")
        raise MailboxNotFound("Inbox mailbox not found")

    results = client.request(
        [
            EmailQuery(
                filter=EmailQueryFilterCondition(in_mailbox=inbox_id),
                sort=[Comparator(property="receivedAt", is_ascending=False)],
                calculate_total=True,
                position=offset,
                limit=30,
            ),
            EmailGet(ids=Ref("/ids")),
        ]
    )

    query_data = results[0].response

    email_data = results[1].response.data
    emails = [
        Email(
            id=email.id,
            sender=format_addresses(email.mail_from),
            subject=email.subject,
            date=email.received_at,
        )
        for email in email_data
    ]

    logger.debug("Query returned %s emails", len(emails))

    logger.debug("Listed %s emails", len(emails))

    return EmailPage(
        emails=emails,
        offset=query_data.position,
        total=query_data.total,
    )


def fastmail_query_emails_by_keyword(
    api_token: str, keyword: str, offset: int = 0
) -> EmailPage:
    """Query emails in the inbox by a keyword in the subject or body.

    Args:
        api_token: Fastmail API token.
        keyword: Keyword to search for in email subjects or bodies.

    Returns:
        EmailPage object containing a list of Email objects and pagination info.
    """
    logger.debug("Querying emails for keyword '%s' (offset=%s)", keyword, offset)
    client = get_client(api_token)

    trash_id = get_mailbox_id_for_role(client, "trash")
    junk_id = get_mailbox_id_for_role(client, "junk")

    exclude_mailboxes = list(filter(None, [trash_id, junk_id]))

    filter_params: dict[str, str | list[str]] = {"text": keyword}
    if exclude_mailboxes:
        filter_params["in_mailbox_other_than"] = exclude_mailboxes

    results = client.request(
        [
            EmailQuery(
                filter=EmailQueryFilterCondition(**filter_params),
                sort=[Comparator(property="receivedAt", is_ascending=False)],
                position=offset,
                calculate_total=True,
                limit=30,
            ),
            EmailGet(ids=Ref("/ids")),
        ]
    )

    query_data = results[0].response
    if query_data.total == 0:
        return EmailPage(emails=[], offset=offset, total=0)

    email_data = results[1].response.data
    emails = [
        Email(
            id=email.id,
            sender=format_addresses(email.mail_from),
            subject=email.subject,
            date=email.received_at,
        )
        for email in email_data
    ]

    return EmailPage(
        emails=emails,
        offset=query_data.position,
        total=query_data.total,
    )


def fastmail_get_email_content(api_token: str, email_id: str) -> str:
    """Get the content of an email by its ID."""
    logger.debug("Retrieving content for email %s", email_id)
    client = get_client(api_token)
    results = client.request(
        [
            EmailGet(
                ids=[email_id],
                fetch_all_body_values=True,
                max_body_value_bytes=1024 * 1024,
            ),
        ]
    )
    email_data = results[0].response.data
    if not email_data:
        return "No email found with the given ID."

    email = email_data[0]
    content = get_body_as_text(email)
    logger.debug("Retrieved email content length %s", len(content))
    return content
