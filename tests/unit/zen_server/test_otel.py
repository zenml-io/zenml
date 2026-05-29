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
"""Unit tests for ZenML server OpenTelemetry configuration."""

from collections.abc import Generator

import pytest

from zenml.config.server_config import (
    SUPPORTED_STANDARD_OTEL_ENV_VARS,
    ServerConfiguration,
)


@pytest.fixture(autouse=True)
def clean_otel_env(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    """Clear OTel env vars so config tests do not depend on local state."""
    for env_var in SUPPORTED_STANDARD_OTEL_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)
        # also delete ZENML_SERVER_ prefixed OTel env vars
        monkeypatch.delenv(f"ZENML_SERVER_{env_var}", raising=False)

    yield


def test_otel_config_derives_signal_endpoints_from_base_endpoint() -> None:
    """Server config derives OTLP/HTTP signal endpoints from the base endpoint."""
    config = ServerConfiguration(
        otel_exporter_otlp_endpoint="http://otel-collector:4318/"
    )

    assert (
        config.otel_exporter_otlp_traces_endpoint
        == "http://otel-collector:4318/v1/traces"
    )
    assert (
        config.otel_exporter_otlp_metrics_endpoint
        == "http://otel-collector:4318/v1/metrics"
    )
    assert (
        config.otel_exporter_otlp_logs_endpoint
        == "http://otel-collector:4318/v1/logs"
    )


def test_otel_config_prefers_signal_endpoint_overrides() -> None:
    """Per-signal endpoints take precedence over base endpoint derivation."""
    config = ServerConfiguration(
        otel_exporter_otlp_endpoint="http://otel-collector:4318",
        otel_exporter_otlp_traces_endpoint="http://traces/v1/traces",
        otel_exporter_otlp_metrics_endpoint="http://metrics/v1/metrics",
        otel_exporter_otlp_logs_endpoint="http://logs/v1/logs",
    )

    assert (
        config.otel_exporter_otlp_traces_endpoint == "http://traces/v1/traces"
    )
    assert (
        config.otel_exporter_otlp_metrics_endpoint
        == "http://metrics/v1/metrics"
    )
    assert config.otel_exporter_otlp_logs_endpoint == "http://logs/v1/logs"


def test_otel_config_disables_signal_endpoints() -> None:
    """Disabled OTel signals do not expose export endpoints."""
    config = ServerConfiguration(
        otel_exporter_otlp_endpoint="http://otel-collector:4318",
        otel_traces_enabled=False,
        otel_metrics_enabled=False,
        otel_logs_enabled=False,
    )

    assert config.otel_exporter_otlp_traces_endpoint is None
    assert config.otel_exporter_otlp_metrics_endpoint is None
    assert config.otel_exporter_otlp_logs_endpoint is None


def test_otel_config_reads_standard_otel_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Standard OTel env vars are normalized into server config."""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel:4318")
    monkeypatch.setenv(
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://traces/v1/traces"
    )
    monkeypatch.setenv("OTEL_SERVICE_NAME", "custom-server")

    config = ServerConfiguration.get_server_config()

    assert config.otel_exporter_otlp_endpoint == "http://otel:4318"
    assert (
        config.otel_exporter_otlp_traces_endpoint == "http://traces/v1/traces"
    )
    assert (
        config.otel_exporter_otlp_metrics_endpoint
        == "http://otel:4318/v1/metrics"
    )
    assert config.otel_service_name == "custom-server"


def test_otel_config_prefers_zenml_prefixed_env_vars_over_standard_otel_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ZenML server prefixed env vars take precedence over standard OTel env vars."""
    # Set standard OTel env vars
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://standard:4318")
    monkeypatch.setenv(
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "http://standard/v1/traces",
    )
    monkeypatch.setenv("OTEL_SERVICE_NAME", "standard-env-var-service-name")
    # Set ZenML server prefixed OTel env vars
    monkeypatch.setenv(
        "ZENML_SERVER_OTEL_EXPORTER_OTLP_ENDPOINT",
        "http://zenml:4318",
    )
    monkeypatch.setenv(
        "ZENML_SERVER_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "http://zenml/v1/traces",
    )
    monkeypatch.setenv(
        "ZENML_SERVER_OTEL_SERVICE_NAME", "zenml-prefixed-service-name"
    )

    config = ServerConfiguration.get_server_config()

    assert config.otel_exporter_otlp_endpoint == "http://zenml:4318"
    assert (
        config.otel_exporter_otlp_traces_endpoint == "http://zenml/v1/traces"
    )
    assert config.otel_service_name == "zenml-prefixed-service-name"


def test_otel_config_ignores_empty_standard_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty standard OTel env vars do not activate server OTel export."""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

    config = ServerConfiguration.get_server_config()

    assert config.otel_exporter_otlp_endpoint is None
    assert config.otel_exporter_otlp_traces_endpoint is None


def test_server_config_does_not_import_unsupported_otel_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only OTel env vars normalized by ZenML are added to server config."""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc")

    config = ServerConfiguration.get_server_config()

    assert config.model_extra is not None
    assert "otel_exporter_otlp_protocol" not in config.model_extra
