from unittest.mock import Mock, patch

import pytest

from src.gmail_sender import send_application_email


def test_gmail_sender_rejects_missing_cv(tmp_path):
    with pytest.raises(FileNotFoundError):
        send_application_email("rh@example.com", "Subject", "Body", str(tmp_path / "missing.pdf"))


def test_gmail_sender_builds_and_sends_mime(tmp_path):
    cv = tmp_path / "cv.pdf"
    cv.write_bytes(b"%PDF-1.4 test")
    service = Mock()
    send_call = Mock()
    send_call.execute.return_value = {"id": "message-123"}
    service.users.return_value.messages.return_value.send.return_value = send_call

    with patch("src.gmail_sender.get_gmail_service", return_value=service):
        message_id = send_application_email("rh@example.com", "Subject", "Body", str(cv))

    assert message_id == "message-123"
    send_call_args = service.users.return_value.messages.return_value.send.call_args
    assert send_call_args.kwargs["body"]["raw"]
