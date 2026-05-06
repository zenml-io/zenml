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
"""Unit tests for the Run:AI step operator flavor config."""

from typing import Any

import pytest
from pydantic import ValidationError

from zenml.integrations.runai.flavors import (
    RunAIConfigMapMountSettings,
    RunAIExternalURLSettings,
    RunAIPortSettings,
    RunAIPVCMountSettings,
    RunAISecurityContextSettings,
    RunAIStepOperatorConfig,
    RunAIStepOperatorSettings,
    RunAITolerationSettings,
)


def _build_config(runai_base_url: str) -> RunAIStepOperatorConfig:
    """Build a minimal valid Run:AI step operator config."""
    return RunAIStepOperatorConfig(
        client_id="client-id",
        client_secret="client-secret",
        runai_base_url=runai_base_url,
        project_name="demo-project",
    )


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://my-org.run.ai", "https://my-org.run.ai"),
        ("https://my-org.run.ai/", "https://my-org.run.ai"),
        (
            "http://runai.local:8443/control-plane/",
            "http://runai.local:8443/control-plane",
        ),
    ],
)
def test_runai_base_url_accepts_valid_urls(url: str, expected: str) -> None:
    """Tests validation and normalization of valid Run:AI base URLs."""
    config = _build_config(url)
    assert config.runai_base_url == expected


@pytest.mark.parametrize(
    "url,error_match",
    [
        ("my-org.run.ai", "Must start with http:// or https://"),
        ("ftp://my-org.run.ai", "Must start with http:// or https://"),
        ("https://", "must include a hostname"),
        ("http://", "must include a hostname"),
        (
            "https://my-org.run.ai/control-plane?foo=bar",
            "Query parameters and fragments are not supported",
        ),
        (
            "https://my-org.run.ai/control-plane#section",
            "Query parameters and fragments are not supported",
        ),
    ],
)
def test_runai_base_url_rejects_invalid_urls(
    url: str, error_match: str
) -> None:
    """Tests validation errors for invalid Run:AI base URLs."""
    with pytest.raises(ValidationError, match=error_match):
        _build_config(url)


def test_runai_settings_accept_advanced_training_fields() -> None:
    """Tests that advanced Run:AI training workload settings validate."""
    settings = RunAIStepOperatorSettings(
        pvc_mounts=[
            RunAIPVCMountSettings(
                claim_name="datasets-pvc",
                path="/mnt/datasets",
                read_only=True,
            )
        ],
        config_map_mounts=[
            RunAIConfigMapMountSettings(
                config_map="training-config",
                mount_path="/etc/training",
                default_mode="0644",
            )
        ],
        security_context=RunAISecurityContextSettings(
            uid_gid_source="custom",
            run_as_uid=1000,
            run_as_gid=1000,
            run_as_non_root=True,
            supplemental_groups=[1000, 2000],
        ),
        ports=[
            RunAIPortSettings(
                container=8888, service_type="ClusterIP", external=30088
            )
        ],
        external_urls=[
            RunAIExternalURLSettings(
                container=8888,
                authorization_type="authenticatedUsers",
            )
        ],
        tolerations=[
            {
                "key": "nvidia.com/gpu",
                "operator": "Exists",
                "effect": "NoSchedule",
            },
            RunAITolerationSettings(
                key="dedicated",
                operator="Equal",
                value="training",
                effect="NoExecute",
            ),
        ],
        workload_template_id="template-id",
        parallelism=2,
        completions=3,
    )

    assert settings.workload_template_id == "template-id"
    assert settings.parallelism == 2
    assert settings.completions == 3
    assert settings.tolerations is not None
    assert all(
        isinstance(toleration, RunAITolerationSettings)
        for toleration in settings.tolerations
    )


def test_runai_toleration_settings_ignore_unknown_fields() -> None:
    """Unknown toleration fields are ignored to preserve backwards compat.

    Tolerations were previously typed as ``List[Dict[str, Any]]``; existing
    components that include extra keys must still validate without error.
    """
    settings = RunAIStepOperatorSettings(
        tolerations=[
            {
                "key": "dedicated",
                "operator": "Equal",
                "value": "training",
                "effect": "NoExecute",
                "tolerationSeconds": 60,
            }
        ],
    )

    assert settings.tolerations is not None
    assert settings.tolerations[0].key == "dedicated"


@pytest.mark.parametrize(
    "settings_kwargs,error_match",
    [
        (
            {"pvc_mounts": [{"claim_name": "pvc", "path": "relative"}]},
            "Mount paths must be absolute",
        ),
        (
            {
                "pvc_mounts": [{"claim_name": "pvc", "path": "/data"}],
                "config_map_mounts": [
                    {"config_map": "cm", "mount_path": "/data"}
                ],
            },
            "Mount paths must be unique",
        ),
        ({"ports": [{"container": 0}]}, "greater than 0"),
        (
            {"ports": [{"container": 80, "external": 0}]},
            "greater than 0",
        ),
        (
            {"ports": [{"container": 80, "service_type": "ExternalUrl"}]},
            "Input should be",
        ),
        (
            {
                "config_map_mounts": [
                    {
                        "config_map": "cm",
                        "mount_path": "/cm",
                        "default_mode": "644",
                    }
                ]
            },
            "default_mode must be a four-character octal string",
        ),
        (
            {
                "secret_mounts": [
                    {
                        "secret": "secret",
                        "mount_path": "/secret",
                        "default_mode": "9999",
                    }
                ]
            },
            "default_mode must be a four-character octal string",
        ),
        (
            {
                "config_map_mounts": [
                    {
                        "config_map": "cm",
                        "mount_path": "/cm",
                        "default_mode": "abcd",
                    }
                ]
            },
            "default_mode must be a four-character octal string",
        ),
        (
            {"tolerations": [{"operator": "Invalid"}]},
            "Input should be",
        ),
        (
            {"tolerations": [{"effect": "Invalid"}]},
            "Input should be",
        ),
        (
            {
                "pvc_mounts": [
                    {
                        "claim_name": "pvc",
                        "path": "/data",
                        "unexpected": "value",
                    }
                ]
            },
            "Extra inputs are not permitted",
        ),
        (
            {"security_context": {"unexpected": "value"}},
            "Extra inputs are not permitted",
        ),
        ({"security_context": {"run_as_uid": -1}}, "greater than or equal"),
        (
            {"parallelism": 3, "completions": 2},
            "parallelism must be <= completions",
        ),
    ],
)
def test_runai_settings_reject_invalid_advanced_training_fields(
    settings_kwargs: Any, error_match: str
) -> None:
    """Tests validation errors for invalid advanced settings."""
    with pytest.raises(ValidationError, match=error_match):
        RunAIStepOperatorSettings(**settings_kwargs)
