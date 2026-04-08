"""Tests for the Telegram bot module."""

from unittest.mock import patch, MagicMock

from telegram_bot import send_message, _split_message, handle_document, download_file


def test_split_message_short():
    """Short messages are not split."""
    result = _split_message("hello", 4096)
    assert result == ["hello"]


def test_split_message_long():
    """Long messages are split at newlines."""
    text = "line1\nline2\nline3\nline4"
    result = _split_message(text, 12)
    assert len(result) >= 2
    assert "line1" in result[0]


@patch("telegram_bot.requests.post")
def test_send_message_success(mock_post):
    """send_message sends via Telegram API."""
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {"ok": True}
    mock_post.return_value = mock_resp

    result = send_message("test", chat_id="123", token="fake-token")
    assert result.get("ok") is True
    mock_post.assert_called_once()


def test_send_message_no_config():
    """send_message returns empty dict when not configured."""
    result = send_message("test", chat_id="", token="")
    assert result == {}


@patch("telegram_bot.requests.get")
def test_download_file(mock_get):
    """download_file fetches file content from Telegram."""
    # First call: getFile
    file_resp = MagicMock()
    file_resp.json.return_value = {"result": {"file_path": "documents/file.csv"}}
    file_resp.status_code = 200
    file_resp.raise_for_status = MagicMock()

    # Second call: actual download
    content_resp = MagicMock()
    content_resp.text = "Date,Workout Name,Exercise Name,Set Order,Weight,Reps\n"
    content_resp.status_code = 200
    content_resp.raise_for_status = MagicMock()

    mock_get.side_effect = [file_resp, content_resp]

    result = download_file("file123", token="fake-token")
    assert "Date" in result


@patch("telegram_bot.send_message")
@patch("telegram_bot.download_file")
def test_handle_document_csv(mock_download, mock_send, sample_strong_csv, tmp_db):
    """handle_document parses an uploaded CSV file."""
    mock_download.return_value = sample_strong_csv

    update = {
        "message": {
            "chat": {"id": 123},
            "document": {
                "file_id": "abc123",
                "file_name": "workout.csv",
            },
        }
    }
    result = handle_document(update, db_path=tmp_db, token="fake")
    assert "Workout imported" in result
    mock_send.assert_called()


@patch("telegram_bot.send_message")
def test_handle_document_non_csv(mock_send):
    """handle_document rejects non-CSV files."""
    update = {
        "message": {
            "chat": {"id": 123},
            "document": {
                "file_id": "abc123",
                "file_name": "photo.jpg",
            },
        }
    }
    result = handle_document(update, token="fake")
    assert result is None
    mock_send.assert_called_once()
    assert ".csv" in mock_send.call_args[0][0]
