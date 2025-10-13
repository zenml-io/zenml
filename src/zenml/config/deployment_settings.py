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
"""Deployment settings."""

from enum import Enum
from types import FunctionType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zenml.config.base_settings import BaseSettings, ConfigurationLevel
from zenml.enums import LoggingLevels
from zenml.logger import get_logger
from zenml.utils import deprecation_utils
from zenml.utils.pydantic_utils import before_validator_handler
from zenml.constants import (
    DEFAULT_ZENML_SERVER_FILE_DOWNLOAD_SIZE_LIMIT,
)
from zenml.config.source import Source, SourceWithValidator


logger = get_logger(__name__)

MiddlewareSpecification = Union[str, Source, FunctionType, Callable[..., None]]
EndpointSpecification = Union[str, Source, FunctionType, Callable[..., Any]]
HookSpecification = Union[str, Source, FunctionType, Callable[..., None]]

DEFAULT_DEPLOYMENT_APP_THREAD_POOL_SIZE = 20

DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_HSTS = (
    "max-age=63072000; includeSubdomains"
)
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_XFO = "SAMEORIGIN"
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_XXP = "0"
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_CONTENT = "nosniff"
_csp_script_src_urls = []
_csp_connect_src_urls = []
_csp_img_src_urls = []
_csp_frame_src_urls = []
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_CSP = (
    "default-src 'none'; "
    f"script-src 'self' 'unsafe-inline' 'unsafe-eval' {' '.join(_csp_script_src_urls)}; "
    f"connect-src 'self' {' '.join(_csp_connect_src_urls)}; "
    f"img-src 'self' data: {' '.join(_csp_img_src_urls)}; "
    "style-src 'self' 'unsafe-inline'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "font-src 'self';"
    f"frame-src {' '.join(_csp_frame_src_urls)}"
)
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_REFERRER = "no-referrer-when-downgrade"
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_CACHE = (
    "no-store, no-cache, must-revalidate"
)
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_PERMISSIONS = (
    "accelerometer=(), autoplay=(), camera=(), encrypted-media=(), "
    "geolocation=(), gyroscope=(), magnetometer=(), microphone=(), midi=(), "
    "payment=(), sync-xhr=(), usb=()"
)
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_REPORT_TO = "default"
DEFAULT_DEPLOYMENT_APP_MAX_REQUEST_BODY_SIZE_IN_BYTES = 256 * 1024 * 1024


class DeploymentSettings(BaseSettings):
    """Settings for the pipeline deployment.

    Attributes:

    """

    # This settings is only available at the pipeline level
    LEVEL: ClassVar[ConfigurationLevel] = ConfigurationLevel.PIPELINE

    app_title: Optional[str] = None
    app_description: Optional[str] = None
    app_version: Optional[str] = None
    root_url_path: str = ""
    docs_url_path: str = "/docs"
    redoc_url_path: str = "/redoc"
    invoke_url_path: str = "/invoke"
    health_url_path: str = "/health"
    info_url_path: str = "/info"
    metrics_url_path: str = "/metrics"
    fastapi_kwargs: Dict[str, Any] = {}

    metadata: Dict[str, str] = {}
    cors_allow_origins: List[str] = ["*"]
    cors_allow_methods: List[str] = ["GET", "OPTIONS"]
    cors_allow_headers: List[str] = ["*"]
    cors_allow_credentials: bool = True
    secure_headers_server: Union[bool, str] = Field(
        default=True,
        union_mode="left_to_right",
    )
    secure_headers_hsts: Union[bool, str] = Field(
        default=DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_HSTS,
        union_mode="left_to_right",
    )
    secure_headers_xfo: Union[bool, str] = Field(
        default=DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_XFO,
        union_mode="left_to_right",
    )
    secure_headers_xxp: Union[bool, str] = Field(
        default=DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_XXP,
        union_mode="left_to_right",
    )
    secure_headers_content: Union[bool, str] = Field(
        default=DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_CONTENT,
        union_mode="left_to_right",
    )
    secure_headers_csp: Union[bool, str] = Field(
        default=DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_CSP,
        union_mode="left_to_right",
    )
    secure_headers_referrer: Union[bool, str] = Field(
        default=DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_REFERRER,
        union_mode="left_to_right",
    )
    secure_headers_cache: Union[bool, str] = Field(
        default=DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_CACHE,
        union_mode="left_to_right",
    )
    secure_headers_permissions: Union[bool, str] = Field(
        default=DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_PERMISSIONS,
        union_mode="left_to_right",
    )

    thread_pool_size: int = DEFAULT_DEPLOYMENT_APP_THREAD_POOL_SIZE

    file_download_size_limit: int = (
        DEFAULT_ZENML_SERVER_FILE_DOWNLOAD_SIZE_LIMIT
    )

    startup_hook_source: Optional[SourceWithValidator] = None
    shutdown_hook_source: Optional[SourceWithValidator] = None

    middlewares: Optional[List[SourceWithValidator]] = None
    endpoints: Optional[List[SourceWithValidator]] = None

    extra_settings: Optional[Dict[str, Any]] = None

    uvicorn_host: str = "0.0.0.0"
    uvicorn_port: int = 8000
    uvicorn_workers: int = 1
    log_level: LoggingLevels = LoggingLevels.INFO

    uvicorn_kwargs: Dict[str, Any] = {}

    deployment_service_source: Optional[SourceWithValidator] = None

    model_config = ConfigDict(
        # public attributes are immutable
        frozen=True,
        # prevent extra attributes during model initialization
        extra="ignore",
    )
