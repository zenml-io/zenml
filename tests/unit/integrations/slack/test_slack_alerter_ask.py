"""Tests for `SlackAlerter.ask()` rate-limit handling."""

from unittest.mock import MagicMock, patch

from slack_sdk.errors import SlackApiError

from zenml.integrations.slack.alerters.slack_alerter import SlackAlerter

MODULE = "zenml.integrations.slack.alerters.slack_alerter"


def _rate_limited_error() -> SlackApiError:
    response = MagicMock()
    response.status_code = 429
    response.headers = {"Retry-After": "2"}
    response.get.return_value = "ratelimited"
    return SlackApiError("ratelimited", response)


def _run_ask(history_side_effect):
    alerter = MagicMock()
    alerter._get_approve_msg_options.return_value = ["approve"]
    alerter._get_disapprove_msg_options.return_value = ["reject"]
    alerter._get_timeout_duration.return_value = 600
    client = MagicMock()
    client.chat_postMessage.return_value = {"ok": True, "ts": "1.0"}
    client.conversations_history.side_effect = history_side_effect
    with (
        patch(f"{MODULE}.WebClient", return_value=client),
        patch(f"{MODULE}.time.sleep") as sleep,
    ):
        result = SlackAlerter.ask(alerter, "Deploy?")
    return result, client, sleep


def test_ask_waits_out_rate_limit_and_returns_approval():
    """A 429 while polling is waited out instead of denying approval."""
    approval = {"messages": [{"ts": "2.0", "user": "U1", "text": "approve"}]}
    result, client, sleep = _run_ask([_rate_limited_error(), approval])

    assert result is True
    assert client.conversations_history.call_count == 2
    sleep.assert_any_call(2)


def test_ask_still_fails_on_non_rate_limit_slack_error():
    """Other Slack API errors still make `ask()` return False."""
    response = MagicMock()
    response.status_code = 403
    response.get.return_value = "missing_scope"
    error = SlackApiError("missing_scope", response)

    result, client, _ = _run_ask([error])

    assert result is False
    assert client.conversations_history.call_count == 1
