"""Tests for the Resend transactional email integration."""

from unittest.mock import MagicMock, patch
import resend

from app.config import Settings
from app.mailer import send, send_verification_email, send_order_confirmed_email
from app.models import User, Order, OrderItem


def test_send_logs_when_resend_disabled(monkeypatch, caplog):
    test_settings = Settings(mail_mailer="log", resend_api_key="")
    monkeypatch.setattr("app.mailer.settings", test_settings)

    with caplog.at_level("INFO"):
        result = send("user@example.com", "Test Subject", "<p>Hello</p>")

    assert result is False
    assert "[mail:log]" in caplog.text
    assert "user@example.com" in caplog.text


def test_send_invokes_resend_when_enabled(monkeypatch):
    test_settings = Settings(
        mail_mailer="resend",
        resend_api_key="re_test_123",
        mail_from_address="onboarding@resend.dev",
        mail_from_name="MLC",
    )
    monkeypatch.setattr("app.mailer.settings", test_settings)

    with patch.object(resend.Emails, "send", return_value={"id": "email_123"}) as mock_send:
        result = send("buyer@example.com", "Order Update", "<p>Shipped</p>", text="Shipped")

    assert result is True
    mock_send.assert_called_once_with({
        "from": "MLC <onboarding@resend.dev>",
        "to": ["buyer@example.com"],
        "subject": "Order Update",
        "html": "<p>Shipped</p>",
        "text": "Shipped",
    })
    assert resend.api_key == "re_test_123"


def test_send_gracefully_handles_resend_error(monkeypatch):
    test_settings = Settings(
        mail_mailer="resend",
        resend_api_key="re_test_123",
    )
    monkeypatch.setattr("app.mailer.settings", test_settings)

    with patch.object(resend.Emails, "send", side_effect=Exception("API limit exceeded")):
        result = send("buyer@example.com", "Order Update", "<p>Shipped</p>")

    assert result is False


def test_send_verification_email_renders_and_sends(monkeypatch):
    test_settings = Settings(
        app_name="MLC",
        mail_mailer="resend",
        resend_api_key="re_test_123",
        mail_from_address="onboarding@resend.dev",
        frontend_url="http://localhost:5173",
    )
    monkeypatch.setattr("app.mailer.settings", test_settings)

    user = User(name="Ada Lovelace", email="ada@example.com", verification_token="tok_123")

    with patch.object(resend.Emails, "send", return_value={"id": "email_verify"}) as mock_send:
        result = send_verification_email(user, "http://localhost:5173/verify?token=tok_123")

    assert result is True
    call_args = mock_send.call_args[0][0]
    assert call_args["to"] == ["ada@example.com"]
    assert "Confirm your email" in call_args["subject"]
    assert "http://localhost:5173/verify?token=tok_123" in call_args["html"]
