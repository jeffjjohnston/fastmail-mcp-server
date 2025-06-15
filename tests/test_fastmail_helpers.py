import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import types
from dataclasses import dataclass

import pytest

from fastmail import format_addresses, normalize_whitespace, get_body_as_text


@dataclass
class MockAddress:
    email: str
    name: str | None = None


@dataclass
class MockBodyPart:
    part_id: str
    type: str


@dataclass
class MockBodyValue:
    value: str


@dataclass
class MockEmail:
    text_body: list[MockBodyPart]
    html_body: list[MockBodyPart]
    body_values: dict[str, MockBodyValue]


def test_format_addresses_with_display_names():
    addresses = [
        MockAddress(email="bob@example.com", name="Bob"),
        MockAddress(email="alice@example.com", name="Alice"),
    ]
    result = format_addresses(addresses)
    assert result == "Bob <bob@example.com>, Alice <alice@example.com>"


def test_format_addresses_without_display_names():
    addresses = [
        MockAddress(email="noname@example.com"),
        MockAddress(email="emptyname@example.com", name=""),
    ]
    result = format_addresses(addresses)
    assert result == "noname@example.com, emptyname@example.com"


def test_normalize_whitespace_multiple_spaces_and_newlines():
    text = "Hello   world\n\nThis   is\t\ta   test.\n\n"
    result = normalize_whitespace(text)
    assert result == "Hello world\nThis is a test."


def test_get_body_as_text_prefers_html_over_text():
    text_part = MockBodyPart(part_id="1", type="text/plain")
    html_part = MockBodyPart(part_id="2", type="text/html")

    email = MockEmail(
        text_body=[text_part],
        html_body=[html_part],
        body_values={
            "1": MockBodyValue(value="Plain text body"),
            "2": MockBodyValue(value="<p>Hello <b>World</b></p>"),
        },
    )

    result = get_body_as_text(email)
    assert result == "Hello World"
