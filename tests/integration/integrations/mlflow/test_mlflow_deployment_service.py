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
"""Tests for MLflow deployment service endpoint configuration."""

import importlib
import logging
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

pytest.importorskip("mlflow")

from zenml.integrations.mlflow.services.mlflow_deployment import (
    MLFLOW_HEALTHCHECK_URL_PATH,
    MLFLOW_PREDICTION_URL_PATH,
    MLSERVER_HEALTHCHECK_URL_PATH,
    MLSERVER_PREDICTION_URL_PATH,
    MLFlowDeploymentConfig,
    MLFlowDeploymentService,
)
from zenml.services import ServiceEndpointProtocol


def _patch_mlserver_packages_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Patch MLServer imports for tests that only validate service config."""
    original_import_module = importlib.import_module

    def import_module(name: str) -> MagicMock:
        if name in {"mlserver", "mlserver_mlflow"}:
            return MagicMock()
        return original_import_module(name)

    monkeypatch.setattr(
        "zenml.integrations.mlflow.services.mlflow_deployment.importlib.import_module",
        import_module,
    )


def _deployment_service(*, mlserver: bool) -> MLFlowDeploymentService:
    """Create an MLflow deployment service without starting its daemon."""
    config = MLFlowDeploymentConfig(
        model_uri="runs:/test-run-id/model",
        model_name="model",
        mlserver=mlserver,
    )
    return MLFlowDeploymentService(uuid=uuid4(), config=config)


def test_standard_mlflow_deployment_healthcheck_uses_get() -> None:
    """Check that standard MLflow serving uses GET /ping health checks."""
    service = _deployment_service(mlserver=False)

    assert (
        service.endpoint.config.prediction_url_path
        == MLFLOW_PREDICTION_URL_PATH
    )
    assert (
        service.endpoint.monitor.config.healthcheck_uri_path
        == MLFLOW_HEALTHCHECK_URL_PATH
    )
    assert service.endpoint.monitor.config.use_head_request is False


def test_mlserver_deployment_healthcheck_uses_get(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Check that the MLServer endpoint keeps its existing GET readiness probe."""
    _patch_mlserver_packages_available(monkeypatch)
    monkeypatch.setattr(
        "zenml.integrations.mlflow.services.mlflow_deployment.MLFLOW_VERSION",
        "3.12.0",
    )

    with caplog.at_level(logging.WARNING):
        service = _deployment_service(mlserver=True)

    assert (
        service.endpoint.config.prediction_url_path
        == MLSERVER_PREDICTION_URL_PATH
    )
    assert (
        service.endpoint.monitor.config.healthcheck_uri_path
        == MLSERVER_HEALTHCHECK_URL_PATH
    )
    assert service.endpoint.monitor.config.use_head_request is False
    assert "MLServer backend is deprecated" in caplog.text


def test_mlserver_deployment_is_ignored_for_mlflow_3_13(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Check that MLServer deployments fall back for unsupported MLflow."""
    monkeypatch.setattr(
        "zenml.integrations.mlflow.services.mlflow_deployment.MLFLOW_VERSION",
        "3.13.0",
    )

    with caplog.at_level(logging.WARNING):
        service = _deployment_service(mlserver=True)

    assert service.config.mlserver is False
    assert (
        service.endpoint.config.prediction_url_path
        == MLFLOW_PREDICTION_URL_PATH
    )
    assert (
        service.endpoint.monitor.config.healthcheck_uri_path
        == MLFLOW_HEALTHCHECK_URL_PATH
    )
    assert "MLServer backend is not supported for MLflow 3.13.0" in caplog.text


def test_serialized_mlserver_endpoint_is_realigned_for_mlflow_3_13(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Check stale serialized MLServer endpoints match the effective backend."""
    _patch_mlserver_packages_available(monkeypatch)
    monkeypatch.setattr(
        "zenml.integrations.mlflow.services.mlflow_deployment.MLFLOW_VERSION",
        "3.12.0",
    )
    service = _deployment_service(mlserver=True)
    service.endpoint.status.protocol = ServiceEndpointProtocol.HTTP
    service.endpoint.status.hostname = "127.0.0.1"
    service.endpoint.status.port = 12345

    monkeypatch.setattr(
        "zenml.integrations.mlflow.services.mlflow_deployment.MLFLOW_VERSION",
        "3.13.0",
    )
    reloaded_service = MLFlowDeploymentService.from_json(
        service.model_dump_json()
    )

    assert isinstance(reloaded_service, MLFlowDeploymentService)
    assert reloaded_service.config.mlserver is False
    assert (
        reloaded_service.endpoint.config.prediction_url_path
        == MLFLOW_PREDICTION_URL_PATH
    )
    assert (
        reloaded_service.endpoint.monitor.config.healthcheck_uri_path
        == MLFLOW_HEALTHCHECK_URL_PATH
    )
    assert reloaded_service.endpoint.status.port == 12345
