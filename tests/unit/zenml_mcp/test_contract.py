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
"""What `zenml_mcp` copies from ZenML core still matches core.

`zenml_mcp` never imports `zenml`, so it carries copies: enum values, the
defaults the SDK fills into a run configuration, REST routes, which flavors
are local, and how ZenML applies a trigger update. These tests import core
and compare, so a change in core that the copy misses fails here.
"""

import uuid
from enum import Enum
from typing import Any

import pytest

pytest.importorskip("mcp")

from pydantic import BaseModel  # noqa: E402

from zenml import enums  # noqa: E402
from zenml.config.cache_policy import CachePolicy  # noqa: E402
from zenml.config.retry_config import StepRetryConfig  # noqa: E402
from zenml.config.step_configurations import (  # noqa: E402
    GroupInfo,
    StepConfigurationUpdate,
)
from zenml.constants import API, VERSION_1  # noqa: E402
from zenml.enums import StackComponentType  # noqa: E402
from zenml.integrations.registry import integration_registry  # noqa: E402
from zenml.model.model import Model  # noqa: E402
from zenml.models.v2.core.triggers import (  # noqa: E402
    PlatformEventTriggerUpdate,
    ScheduleTriggerUpdate,
    TriggerUpdate,
)
from zenml.stack.flavor_registry import FlavorRegistry  # noqa: E402
from zenml.stack.stack_component import StackComponentConfig  # noqa: E402
from zenml.zen_stores.schemas.trigger_schemas import TriggerSchema  # noqa: E402
from zenml_mcp import resource_catalog, resource_spec, trigger  # noqa: E402
from zenml_mcp.resource_catalog import RESOURCE_REGISTRY  # noqa: E402

_ENUMS = resource_spec._ENUM_FILTERS
_RUN_CONFIGURATION = resource_catalog._TRIGGER_RUN_CONFIGURATION


@pytest.mark.parametrize(
    ("copied", "core"),
    [
        (
            resource_spec.COMPONENT_TYPE_SCHEMA["enum"],
            enums.StackComponentType,
        ),
        (_ENUMS[("tag", "resource_type")], enums.TaggableResourceTypes),
        (_ENUMS[("tag", "color")], enums.ColorVariants),
        (_ENUMS[("model_version", "stage")], enums.ModelStages),
        (resource_spec.CONCURRENCY, enums.TriggerRunConcurrency),
        (resource_catalog.EVENT_SOURCE_TYPES, enums.SourceType),
        (_ENUMS[("pipeline_run", "status")], enums.ExecutionStatus),
        (_ENUMS[("deployment", "status")], enums.DeploymentStatus),
        (_ENUMS[("resource_request", "status")], enums.ResourceRequestStatus),
        (
            _ENUMS[("run_wait_condition", "status")],
            enums.RunWaitConditionStatus,
        ),
        (
            RESOURCE_REGISTRY["service"]
            .mutations["update"]
            .payload_properties["admin_state"]["enum"],
            enums.ServiceState,
        ),
        (
            _RUN_CONFIGURATION["properties"]["execution_mode"]["enum"],
            enums.ExecutionMode,
        ),
    ],
)
def test_a_copied_enum_has_cores_values(copied: Any, core: type[Enum]) -> None:
    """Each enum the catalog lists is the one ZenML accepts.

    Args:
        copied: The values `zenml_mcp` carries.
        core: ZenML's enum.
    """
    assert sorted(copied) == sorted(member.value for member in core)


def test_a_wait_condition_resolution_is_one_zenml_accepts() -> None:
    """The action takes upper case, as the SDK does, and sends lower case."""
    action = RESOURCE_REGISTRY["run_wait_condition"].actions["resolve"]
    listed = action.payload_properties["resolution"]["enum"]
    assert sorted(value.lower() for value in listed) == sorted(
        member.value for member in enums.RunWaitConditionResolution
    )


def _sent_defaults(model: type[BaseModel]) -> dict[str, Any]:
    """The defaults the SDK serializes for `model`: the ones not null.

    Args:
        model: The SDK's model.

    Returns:
        Each optional field's default that is not null.
    """
    found = {}
    for name, field in model.model_fields.items():
        if field.is_required():
            continue
        default = field.get_default(call_default_factory=True)
        if default is not None:
            found[name] = (
                default.value if isinstance(default, Enum) else default
            )
    return found


def test_the_sdk_defaults_a_run_configuration_gets_are_cores() -> None:
    """A run started here carries the defaults the SDK's models add."""
    model = _sent_defaults(Model)
    # The SDK's model validator always sets this flag; `trigger.py` sets it
    # apart from the defaults.
    model.pop("suppress_class_validation_warnings")
    assert trigger._SDK_STEP_DEFAULTS == _sent_defaults(
        StepConfigurationUpdate
    )
    assert trigger._SDK_OBJECT_DEFAULTS == {
        "retry": _sent_defaults(StepRetryConfig),
        "cache_policy": _sent_defaults(CachePolicy),
        "model": model,
        "group": _sent_defaults(GroupInfo),
    }


def test_every_catalog_route_is_a_route_the_server_serves() -> None:
    """A route ZenML renamed or dropped fails here, not on a user's call.

    Each catalog route must be a list route the ZenML server mounts. This
    needs the server extra and is skipped without it.
    """
    server = pytest.importorskip("zenml.zen_server.zen_server_api")
    paths = server.app.openapi()["paths"]
    for spec in RESOURCE_REGISTRY.values():
        mounted = paths.get(f"{API}{VERSION_1}{spec.rest.route}", {})
        assert "get" in mounted, spec.resource_type


def _flavors() -> list[Any]:
    """Every flavor ZenML ships, its integrations' included.

    Returns:
        The flavor classes.
    """
    found = list(FlavorRegistry().builtin_flavors)
    for integration in integration_registry.integrations.values():
        found.extend(integration.flavors())
    return found


# The stored configurations that decide `is_local`, as ZenML keeps them: a
# boolean can be stored as text, which ZenML's config parses.
_CONFIGURATIONS: dict[str, list[dict[str, Any]]] = {
    "AirflowOrchestratorFlavor": [
        {},
        {"local": False},
        {"local": "false"},
        {"local": "No"},
    ],
    "KubernetesOrchestratorFlavor": [
        {},
        {"local": True},
        {"local": "true"},
        {"local": "0"},
    ],
    "KubernetesDeployerFlavor": [
        {},
        {"local": True},
        {"local": "off"},
        {"kubernetes_context": "kind-dev"},
        {"kubernetes_context": "gke_prod"},
    ],
    "FeastFeatureStoreFlavor": [
        {"feast_repo": "repo"},
        {"feast_repo": "repo", "online_host": "127.0.0.1"},
        {"feast_repo": "repo", "online_host": "redis.internal"},
    ],
    "GreatExpectationsDataValidatorFlavor": [
        {},
        {"context_root_dir": "/ge"},
    ],
    "MLFlowExperimentTrackerFlavor": [
        {},
        {"tracking_uri": "file:///mlruns"},
        {
            "tracking_uri": "https://mlflow.example",
            "tracking_username": "sample",
            "tracking_password": "sample",
        },
        {
            "tracking_uri": "databricks",
            "tracking_username": "sample",
            "tracking_password": "sample",
            "databricks_host": "https://dbc.example",
        },
    ],
}


# Its validator needs a real data context, and `is_local` only checks that
# the path is set.
_NOT_PARSED = {"GreatExpectationsDataValidatorFlavor"}


def test_a_local_component_is_found_as_zenml_finds_it() -> None:
    """`_is_local` agrees with each flavor's config class in core.

    Every flavor whose config class decides `is_local` itself is checked:
    with its defaults, and with the configurations that change the answer.
    Those are validated as ZenML parses them; the other flavors decide it
    without reading a field that needs parsing.
    """
    checked = set()
    for flavor_class in _flavors():
        flavor = flavor_class()
        config_class = flavor.config_class
        decides = next(
            klass
            for klass in config_class.__mro__
            if "is_local" in klass.__dict__
        )
        if decides is StackComponentConfig:
            continue
        source = f"{flavor_class.__module__}.{flavor_class.__qualname__}"
        body = {"source": source, "type": flavor.type.value}
        if flavor.type == StackComponentType.CONTAINER_REGISTRY:
            configurations = [
                {"uri": "localhost:5000"},
                {"uri": "registry.example/zenml"},
            ]
        else:
            configurations = _CONFIGURATIONS.get(flavor_class.__name__, [{}])
        parsed = (
            flavor_class.__name__ in _CONFIGURATIONS
            and flavor_class.__name__ not in _NOT_PARSED
        )
        for configuration in configurations:
            config = (
                config_class(**configuration)
                if parsed
                else config_class.model_construct(**configuration)
            )
            expected = config.is_local
            found = trigger._is_local({"body": body}, configuration)
            assert found == expected, (source, configuration)
        checked.add(flavor_class.__name__)
    assert set(_CONFIGURATIONS) <= checked


_RENAMES: list[tuple[type[TriggerUpdate], dict[str, Any]]] = [
    (
        ScheduleTriggerUpdate,
        {
            "type": "schedule",
            "flavor": "native schedule",
            "cron_expression": "0 * * * *",
        },
    ),
    (
        PlatformEventTriggerUpdate,
        {
            "type": "platform_event",
            "flavor": "platform event",
            "source_entity": {"type": "pipeline", "id": str(uuid.uuid4())},
            "target_events": ["run_completed"],
        },
    ),
]


@pytest.mark.parametrize(("update", "rest"), _RENAMES)
def test_a_trigger_update_that_names_no_state_keeps_the_stored_one(
    update: type[TriggerUpdate], rest: dict[str, Any]
) -> None:
    """D25: ZenML applies only the trigger fields an update sets.

    A rename that leaves out `active` and `concurrency` keeps what ZenML
    holds, not the update model's defaults (`active=True`), which would
    switch a disabled trigger on.

    Args:
        update: The update model ZenML parses the PUT body into.
        rest: The rest of the body this server sends for a rename.
    """
    stored = TriggerSchema(
        name="nightly",
        active=False,
        concurrency="submit",
        type=rest["type"],
        flavor=rest["flavor"],
        configuration="{}",
        is_archived=False,
        project_id=uuid.uuid4(),
    )
    stored.update(update.model_validate({"name": "renamed", **rest}))
    assert (stored.name, stored.active, stored.concurrency) == (
        "renamed",
        False,
        "submit",
    )
