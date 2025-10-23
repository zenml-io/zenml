#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Base app extension interface."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zenml.deployers.server.app import BaseDeploymentAppRunner


class BaseAppExtension(ABC):
    """Abstract base for app extensions.

    Extensions provide advanced framework-specific capabilities like:
    - Custom authentication/authorization
    - Observability (logging, tracing, metrics)
    - Complex routers with framework-specific features
    - OpenAPI customizations
    - Advanced middleware patterns

    Subclasses must implement install() to modify the app.
    """

    @abstractmethod
    def install(
        self,
        app_runner: "BaseDeploymentAppRunner",
    ) -> None:
        """Install extension into the application.

        Args:
            app_runner: The deployment app runner instance being used to build
                and run the web application.

        Raises:
            RuntimeError: If installation fails.
        """
