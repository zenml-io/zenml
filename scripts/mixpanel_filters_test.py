import datetime
from typing import Any, Dict

import analytics

"""
Test script to verify our North Star Metrics and Telemetry

Within this script we have 3 classes of users.
Daily users, weekly users and monthly users that post with different
frequencies.
"""

analytics.write_key = "mDBYI0m7GcCj59EZ4f9d016L1T3rh8J5"


def mock_4_pipeline_run_posts(user: str, metadata: Dict[str, Any]) -> None:
    """
    Post 4 consecutive pipeline runs.

    Args:
        user: user id
        metadata: Metadata dict
    """
    event = "Pipeline Run"
    analytics.track(user, event, metadata)
    analytics.track(user, event, metadata)
    analytics.track(user, event, metadata)
    analytics.track(user, event, metadata)


daily_users = [
    "daily_user_0",
    "daily_user_1",
    "daily_user_2",
    "daily_user_3",
    "daily_user_4",
    "daily_user_5",
    "daily_user_6",
    "daily_user_7",
    "daily_user_8",
    "daily_user_9",
    "daily_user_10",
    "daily_user_11",
    "daily_user_12",
    "daily_user_13",
    "daily_user_14",
    "daily_user_15",
    "daily_user_16",
    "daily_user_17",
    "daily_user_18",
    "daily_user_19",
]

weekly_users = [
    "weekly_user_0",
    "weekly_user_1",
    "weekly_user_2",
    "weekly_user_3",
    "weekly_user_4",
    "weekly_user_5",
    "weekly_user_6",
    "weekly_user_7",
    "weekly_user_8",
    "weekly_user_9",
    "weekly_user_10",
    "weekly_user_11",
    "weekly_user_12",
    "weekly_user_13",
    "weekly_user_14",
]

monthly_users = [
    "monthly_user_0",
    "monthly_user_1",
    "monthly_user_2",
    "monthly_user_3",
    "monthly_user_4",
    "monthly_user_5",
    "monthly_user_6",
    "monthly_user_7",
    "monthly_user_8",
    "monthly_user_9",
]

metadata = {
    "store_type": "local",
    "orchestrator": "local",
    "metadata_store": "sqlite",
    "artifact_store": "local",
    "total_steps": 3,
    "schedule": False,
    "os": "linux",
    "linux_distro": "ubuntu",
    "linux_distro_like": "debian",
    "linux_distro_version": "20.04",
    "environment": "gh_action_test",
    "python_version": "3.8.10",
    "version": "0.7.0",
}

# Used as a way to choose the days on which weekly or monthly users post
days_since_epoch = (
    datetime.datetime.now() - datetime.datetime(1970, 1, 1)
).days

# Users post daily
for user in daily_users:
    mock_4_pipeline_run_posts(user, metadata)

# Weekly users post once a week, we stretch this out so not everyone posts
# on the same day
for user in weekly_users:
    weekly_user_num = int(user.split("_")[-1])
    if (days_since_epoch + weekly_user_num) % 7 == 0:
        mock_4_pipeline_run_posts(user, metadata)

# Monthly users post once a month, we stretch this out so not everyone posts
# on the same day
for user in monthly_users:
    monthly_user_num = int(user.split("_")[-1])
    if (days_since_epoch + monthly_user_num) % 30 == 0:
        mock_4_pipeline_run_posts(user, metadata)
