#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Github webhook event source flavor."""

from typing import ClassVar, Type

from zenml.event_sources.webhooks.base_webhook_event_source import (
    BaseWebhookEventSourceFlavor,
)
from zenml.integrations.github import GITHUB_EVENT_FLAVOR
from zenml.integrations.github.plugins.event_sources.github_webhook_event_source import (
    GithubWebhookEventFilterConfiguration,
    GithubWebhookEventSourceConfiguration,
    GithubWebhookEventSourceHandler,
)


class GithubWebhookEventSourceFlavor(BaseWebhookEventSourceFlavor):
    """Enables users to configure github event sources."""

    FLAVOR: ClassVar[str] = GITHUB_EVENT_FLAVOR
    PLUGIN_CLASS: ClassVar[Type[GithubWebhookEventSourceHandler]] = (
        GithubWebhookEventSourceHandler
    )

    # EventPlugin specific
    EVENT_SOURCE_CONFIG_CLASS: ClassVar[
        Type[GithubWebhookEventSourceConfiguration]
    ] = GithubWebhookEventSourceConfiguration
    EVENT_FILTER_CONFIG_CLASS: ClassVar[
        Type[GithubWebhookEventFilterConfiguration]
    ] = GithubWebhookEventFilterConfiguration
