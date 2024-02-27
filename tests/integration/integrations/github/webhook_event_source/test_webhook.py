import pytest

from zenml.integrations.github.plugins.event_sources.github_webhook_event_source import (
    GithubEvent,
    GithubWebhookEventSourceHandler,
)

EXAMPLE_EVENT = correct_event = {
    "ref": "refs/heads/feature/feature_branch",
    "before": "aeb7f6e40c7aaef5e4e7032ef43b5a099ac99c8c",
    "after": "9d20eda4b61e691b9e22f3s5e73fd3f4fca658d0",
    "repository": {
        "id": 314197645,
        "name": "zenml",
        "full_name": "zenml-io/zenml",
        "private": False,
        "html_url": "https://github.com/zenml-io/zenml",
        "pushed_at": 1706547064,
    },
    "pusher": {"name": "AriaTheSupercat", "email": "aria@zenml.io"},
    "organization": {
        "login": "zenml-io",
        "id": 88676955,
        "node_id": "MDEyOk9yZ2FuaXphdGlvbjg4Njc2OTU1",
        "url": "https://api.github.com/orgs/zenml-io",
        "repos_url": "https://api.github.com/orgs/zenml-io/repos",
        "events_url": "https://api.github.com/orgs/zenml-io/events",
        "hooks_url": "https://api.github.com/orgs/zenml-io/hooks",
        "issues_url": "https://api.github.com/orgs/zenml-io/issues",
        "members_url": "https://api.github.com/orgs/zenml-io/members{"
        "/member}",
        "public_members_url": "https://api.github.com/orgs/zenml-io/public_members{/member}",
        "avatar_url": "https://avatars.githubusercontent.com/u/88676955?v"
        "=4",
        "description": "Building production MLOps tooling.",
    },
    "sender": {
        "login": "AriaTheSupercat",
        "id": 38859294,
        "node_id": "MDQ6VXNlcjM4ODU5Mjk0",
        "avatar_url": "https://avatars.githubusercontent.com/u/38859294?v"
        "=4",
        "url": "https://api.github.com/users/AriaTheSupercat",
        "html_url": "https://github.com/AriaTheSupercat",
    },
    "commits": [
        {
            "id": "9d20eda4b61e691b9e22f8d5e73fd3f4fca658d0",
            "message": "Introduced mouse-catching capabilities.",
            "timestamp": "2024-01-29T17:51:00+01:00",
            "url": "https://github.com/zenml-io/zenml/commit"
            "/9d20eda4b61e691b9e34f8d5e73fd3f4fca658d0",
            "author": {
                "name": "Aria Linschoten",
                "email": "aria@zenml.io",
                "username": "AriaTheSupercat",
            },
            "committer": {
                "name": "Aria Linschoten",
                "email": "aria@zenml.io",
                "username": "AriaTheSupercat",
            },
            "added": [],
            "removed": [],
            "modified": [
                "src/zenml/mouse-traps" "/arias-personal-moustrap.py"
            ],
        }
    ],
}


def test__interpret_event():
    handler = GithubWebhookEventSourceHandler()
    # clear event data
    clear_event = dict()
    with pytest.raises(ValueError):
        handler._interpret_event(clear_event)
    # correct event data
    real_event = EXAMPLE_EVENT
    assert isinstance(handler._interpret_event(real_event), GithubEvent)


def test__load_payload():
    handler = GithubWebhookEventSourceHandler()
    # urlencode payload
    headers = {"content-type": "application/x-www-form-urlencoded"}
    raw_body = b"payload=%7B%22key%22:%22value%22%7D"
    expected = {"key": "value"}
    assert handler._load_payload(raw_body, headers) == expected
    # non-urlencoded payload
    headers = {"content-type": "application/json"}
    raw_body = b'{"key": "value"}'
    expected = {"key": "value"}
    assert handler._load_payload(raw_body, headers) == expected
