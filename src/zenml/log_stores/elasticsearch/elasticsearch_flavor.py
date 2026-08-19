#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Elasticsearch log store flavor."""

from typing import Any, Dict, Optional, Type

from pydantic import Field, model_validator

from zenml.enums import StackComponentType
from zenml.log_stores import BaseLogStore, BaseLogStoreConfig
from zenml.log_stores.otel.otel_flavor import OtelLogStoreConfig
from zenml.stack.flavor import Flavor
from zenml.utils.secret_utils import PlainSerializedSecretStr

# Elasticsearch caps a single page of hits at `index.max_result_window`, which
# defaults to 10000 documents.
ELASTICSEARCH_MAX_PAGE_SIZE = 10000

# Document fields that both the exporter and the query side depend on. The two
# sort fields exist to make paging exact: the nanosecond timestamp avoids the
# millisecond truncation of a dynamically mapped date, and the sequence number
# breaks a tie between entries written within the same nanosecond.
TIMESTAMP_FIELD = "timestamp_nanos"
SEQUENCE_FIELD = "sequence_number"
MESSAGE_FIELD = "message"
SEVERITY_NUMBER_FIELD = "severity_number"
LOG_ID_FIELD = "zenml.log.id"


class ElasticsearchLogStoreConfig(OtelLogStoreConfig):
    """Configuration for the Elasticsearch log store.

    Attributes:
        url: Base URL of the Elasticsearch cluster.
        index: Index or data stream to write log entries to.
        api_key: Encoded API key to authenticate with.
        username: Username for HTTP basic authentication.
        password: Password for HTTP basic authentication.
    """

    url: str = Field(
        description="Base URL of the Elasticsearch or OpenSearch cluster, "
        "including the scheme and port. Examples: 'http://localhost:9200', "
        "'https://my-deployment.es.eu-central-1.aws.cloud.es.io:9243'",
    )
    index: str = Field(
        default="zenml-logs",
        description="Index or data stream that log entries are written to and "
        "queried from. Must be writable with the configured credentials, and is "
        "created on first write if the cluster allows automatic creation. "
        "Examples: 'zenml-logs', 'logs-zenml-production'",
    )
    api_key: Optional[PlainSerializedSecretStr] = Field(
        default=None,
        description="Base64 encoded API key sent as an `Authorization: ApiKey` "
        "header, as produced by the Elasticsearch create API key endpoint. "
        "Cannot be combined with `username` and `password`",
    )
    username: Optional[str] = Field(
        default=None,
        description="Username for HTTP basic authentication against the "
        "cluster. Must be set together with `password`, and cannot be combined "
        "with `api_key`. Example: 'elastic'",
    )
    password: Optional[PlainSerializedSecretStr] = Field(
        default=None,
        description="Password for HTTP basic authentication against the "
        "cluster. Must be set together with `username`",
    )

    @model_validator(mode="before")
    @classmethod
    def set_default_endpoint(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Point the ingestion endpoint at the bulk API of the index.

        Args:
            data: The input data dictionary.

        Returns:
            The data dictionary with the endpoint set if it was missing.
        """
        if isinstance(data, dict) and not data.get("endpoint"):
            url = data.get("url")
            if isinstance(url, str):
                index = data.get("index") or "zenml-logs"
                data["endpoint"] = f"{url.rstrip('/')}/{index}/_bulk"

        return data

    @model_validator(mode="after")
    def validate_authentication(self) -> "ElasticsearchLogStoreConfig":
        """Check that exactly one authentication mode is configured.

        Returns:
            The validated configuration.

        Raises:
            ValueError: If basic authentication is half configured, or if both
                authentication modes are configured at once.
        """
        if (self.username is None) != (self.password is None):
            raise ValueError(
                "`username` and `password` must be configured together."
            )

        if self.api_key is not None and self.username is not None:
            raise ValueError(
                "Configure either `api_key` or `username` and `password`, "
                "not both."
            )

        return self


class ElasticsearchLogStoreFlavor(Flavor):
    """Elasticsearch log store flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return "elasticsearch"

    @property
    def docs_url(self) -> str:
        """URL to the flavor documentation.

        Returns:
            The URL to the flavor documentation.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> str:
        """URL to the SDK docs for this flavor.

        Returns:
            The URL to the SDK docs for this flavor.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """URL to the flavor logo.

        Returns:
            The URL to the flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/log_store/elasticsearch.png"

    @property
    def type(self) -> StackComponentType:
        """Stack component type.

        Returns:
            The stack component type.
        """
        return StackComponentType.LOG_STORE

    @property
    def config_class(self) -> Type[BaseLogStoreConfig]:
        """Returns `ElasticsearchLogStoreConfig` config class.

        Returns:
            The config class.
        """
        return ElasticsearchLogStoreConfig

    @property
    def implementation_class(self) -> Type[BaseLogStore]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.log_stores.elasticsearch.elasticsearch_log_store import (
            ElasticsearchLogStore,
        )

        return ElasticsearchLogStore
