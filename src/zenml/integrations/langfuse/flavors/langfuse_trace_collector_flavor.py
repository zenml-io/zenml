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
"""LangFuse trace collector flavor."""

from typing import Optional, Type

from pydantic import Field, SecretStr, validator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.langfuse import LANGFUSE
from zenml.logger import get_logger
from zenml.stack import StackComponent
from zenml.trace_collectors.base_trace_collector import (
    BaseTraceCollectorConfig,
    BaseTraceCollectorFlavor,
)
from zenml.utils.secret_utils import SecretField

logger = get_logger(__name__)


class LangFuseTraceCollectorConfig(BaseTraceCollectorConfig):
    """Configuration for the LangFuse trace collector.

    Attributes:
        host: The LangFuse host URL. Defaults to https://cloud.langfuse.com.
        public_key: The LangFuse public key for authentication.
        secret_key: The LangFuse secret key for authentication.
        project_id: The LangFuse project ID to connect to.
        debug: Enable debug logging for the LangFuse client.
        enabled: Whether the trace collector is enabled.
    """

    host: str = Field(
        default="https://cloud.langfuse.com",
        description="LangFuse host URL. Can be self-hosted or cloud instance. "
        "Examples: 'https://cloud.langfuse.com', 'https://langfuse.example.com'. "
        "Must be a valid HTTP/HTTPS URL accessible with provided credentials",
    )

    public_key: str = SecretField(
        description="LangFuse public key for API authentication. Obtained from "
        "the LangFuse dashboard under project settings. Required for all API "
        "operations including trace collection and querying"
    )

    secret_key: str = SecretField(
        description="LangFuse secret key for API authentication. Obtained from "
        "the LangFuse dashboard under project settings. Keep this secure as it "
        "provides full access to the LangFuse project"
    )

    project_id: Optional[str] = Field(
        default=None,
        description="LangFuse project ID to specify which project to connect to. "
        "Found in the LangFuse dashboard URL or project settings. "
        "Example: 'clabcdef123456789'. If not provided, uses the default project "
        "associated with the provided credentials",
    )

    debug: bool = Field(
        default=False,
        description="Controls debug logging for the LangFuse client. If True, "
        "enables verbose logging of API requests and responses. Useful for "
        "troubleshooting connection and authentication issues",
    )

    enabled: bool = Field(
        default=True,
        description="Controls whether trace collection is active. If False, "
        "all trace collection operations become no-ops. Useful for temporarily "
        "disabling tracing without removing the configuration",
    )

    trace_per_step: bool = Field(
        default=False,
        description="Controls trace hierarchy structure. If True, creates a "
        "separate trace for each pipeline step. If False, creates a single "
        "pipeline-level trace with steps as spans within that trace. "
        "Pipeline-level tracing provides better correlation between steps",
    )

    auto_configure_litellm: bool = Field(
        default=True,
        description="Controls whether to automatically configure LiteLLM "
        "callbacks for Langfuse integration. If True, sets up environment "
        "variables and callbacks for seamless LLM tracing integration",
    )

    fail_on_init_error: bool = Field(
        default=False,
        description="Controls behavior when trace initialization fails. If True, "
        "raises exceptions on initialization errors. If False, logs warnings "
        "and continues with fallback behavior. Useful for debugging",
    )

    @validator("host")
    def validate_host_url(cls, v: str) -> str:
        """Validate that host is a properly formatted URL.

        Args:
            v: The host URL to validate.

        Returns:
            The validated and normalized host URL.

        Raises:
            ValueError: If the host is not a valid HTTP/HTTPS URL.
        """
        if not v.startswith(("http://", "https://")):
            raise ValueError("Host must be a valid HTTP/HTTPS URL")
        return v.rstrip("/")

    @validator("project_id")
    def validate_project_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate project ID format.

        Args:
            v: The project ID to validate.

        Returns:
            The validated project ID.
        """
        if v and not v.startswith("cl"):
            logger.warning(
                f"Project ID '{v}' does not start with 'cl'. "
                "Langfuse project IDs typically start with 'cl'."
            )
        return v


class LangFuseTraceCollectorSettings(BaseSettings):
    """Settings for the LangFuse trace collector."""

    tags: list[str] = Field(
        default_factory=list,
        description="Additional tags to apply to traces collected in this run",
    )

    user_id: Optional[str] = Field(
        default=None,
        description="User ID to associate with traces in this run",
    )

    session_id: Optional[str] = Field(
        default=None,
        description="Session ID to associate with traces in this run",
    )


class LangFuseTraceCollectorFlavor(BaseTraceCollectorFlavor):
    """LangFuse trace collector flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return LANGFUSE

    @property
    def docs_url(self) -> Optional[str]:
        """A URL to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return "https://docs.zenml.io/integrations/langfuse"

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A URL to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return "https://langfuse.com/docs/sdk/python"

    @property
    def logo_url(self) -> str:
        """A URL to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://langfuse.com/images/logo.png"

    @property
    def config_class(self) -> Type[LangFuseTraceCollectorConfig]:
        """Returns `LangFuseTraceCollectorConfig` config class.

        Returns:
            The config class.
        """
        return LangFuseTraceCollectorConfig

    @property
    def implementation_class(self) -> Type[StackComponent]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.langfuse.trace_collectors import (
            LangFuseTraceCollector,
        )

        return LangFuseTraceCollector
