import pytest
import types
from unittest.mock import patch, MagicMock
import fastmail


def _make_email(id="e1", sender="Sender", email="s@example.com", subject="Subj", date="2024-01-01"):
    addr = types.SimpleNamespace(name=sender, email=email)
    return types.SimpleNamespace(
        id=id,
        mail_from=[addr],
        subject=subject,
        received_at=date,
        body_values={"1": types.SimpleNamespace(value="body")},
        text_body=[types.SimpleNamespace(part_id="1", type="text/plain")],
        html_body=[],
    )


@patch("fastmail.get_client")
@patch("fastmail.get_mailbox_id_for_role")
def test_fastmail_list_inbox_emails(mock_get_mailbox, mock_get_client):
    client = MagicMock()
    mock_get_client.return_value = client
    mock_get_mailbox.return_value = "inbox123"
    email = _make_email()
    client.request.return_value = [
        types.SimpleNamespace(response=types.SimpleNamespace(position=0, total=1)),
        types.SimpleNamespace(response=types.SimpleNamespace(data=[email])),
    ]

    page = fastmail.fastmail_list_inbox_emails("token")

    expected = fastmail.Email(
        id="e1",
        sender="Sender <s@example.com>",
        subject="Subj",
        date="2024-01-01",
    )
    assert page == fastmail.EmailPage(emails=[expected], offset=0, total=1)


@patch("fastmail.get_client")
@patch("fastmail.get_mailbox_id_for_role")
def test_fastmail_list_inbox_emails_mailbox_missing(mock_get_mailbox, mock_get_client):
    mock_get_client.return_value = MagicMock()
    mock_get_mailbox.return_value = None
    with pytest.raises(fastmail.MailboxNotFound):
        fastmail.fastmail_list_inbox_emails("token")


@patch("fastmail.get_client")
@patch("fastmail.get_mailbox_id_for_role")
def test_fastmail_query_emails_by_keyword_empty(mock_get_mailbox, mock_get_client):
    client = MagicMock()
    mock_get_client.return_value = client
    mock_get_mailbox.side_effect = ["trash-id", "junk-id"]
    client.request.return_value = [
        types.SimpleNamespace(response=types.SimpleNamespace(position=2, total=0)),
        types.SimpleNamespace(response=types.SimpleNamespace(data=[])),
    ]

    page = fastmail.fastmail_query_emails_by_keyword("token", "hello", offset=2)
    assert page == fastmail.EmailPage(emails=[], offset=2, total=0)


@patch("fastmail.get_client")
@patch("fastmail.get_mailbox_id_for_role")
def test_fastmail_query_emails_by_keyword_pagination(mock_get_mailbox, mock_get_client):
    client = MagicMock()
    mock_get_client.return_value = client
    mock_get_mailbox.side_effect = ["trash-id", "junk-id"]
    email = _make_email()
    client.request.return_value = [
        types.SimpleNamespace(response=types.SimpleNamespace(position=5, total=10)),
        types.SimpleNamespace(response=types.SimpleNamespace(data=[email])),
    ]

    page = fastmail.fastmail_query_emails_by_keyword("token", "hello", offset=5)
    assert page.offset == 5
    assert page.total == 10
    assert page.emails[0].id == "e1"


@patch("fastmail.get_client")
def test_fastmail_get_email_content_found(mock_get_client):
    client = MagicMock()
    mock_get_client.return_value = client
    email = _make_email()
    client.request.return_value = [
        types.SimpleNamespace(response=types.SimpleNamespace(data=[email])),
    ]
    content = fastmail.fastmail_get_email_content("token", "e1")
    assert content == "body"


@patch("fastmail.get_client")
def test_fastmail_get_email_content_not_found(mock_get_client):
    client = MagicMock()
    mock_get_client.return_value = client
    client.request.return_value = [
        types.SimpleNamespace(response=types.SimpleNamespace(data=[])),
    ]
    content = fastmail.fastmail_get_email_content("token", "e1")
    assert content == "No email found with the given ID."
