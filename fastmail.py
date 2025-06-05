"""Shared module for Fastmail JMAP client operations."""

import re
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
    client = Client.create_with_api_token(host=FASTMAIL_API_HOST, api_token=api_token)
    return client


def get_inbox_id(client: Client) -> str:
    """Get the ID of the inbox mailbox."""
    results = client.request(
        [
            MailboxQuery(filter=MailboxQueryFilterCondition(name="Inbox")),
            MailboxGet(ids=Ref("/ids")),
        ]
    )
    # From results, second result, MailboxGet instance, retrieve Mailbox data
    assert isinstance(
        results[1].response, MailboxGetResponse
    ), "Error in Mailbox/get method"
    mailbox_data = results[1].response.data
    if not mailbox_data:
        raise MailboxNotFound("Inbox not found on the server")

    # From the first mailbox result, retrieve the Mailbox ID
    mailbox_id = mailbox_data[0].id
    assert mailbox_id
    return mailbox_id


def fastmail_list_inbox_emails(api_token: str) -> list[Email]:
    """List all emails in the inbox.

    Returns:
        List of Email objects containing id, sender, subject, and date
    """
    client = get_client(api_token)
    inbox_id = get_inbox_id(client)

    results = client.request(
        [
            EmailQuery(
                filter=EmailQueryFilterCondition(in_mailbox=inbox_id),
                sort=[Comparator(property="receivedAt", is_ascending=False)],
            ),
            EmailGet(ids=Ref("/ids")),
        ]
    )

    # From results, second result, EmailGet instance, retrieve Email data
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

    return emails


def fastmail_get_email_content(api_token: str, email_id: str) -> str:
    """Get the content of an email by its ID."""
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
    return get_body_as_text(email)
