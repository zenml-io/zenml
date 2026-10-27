#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
from types import SimpleNamespace
from typing import Type
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.models import (
    FlavorResponse,
    FlavorResponseBody,
    FlavorResponseMetadata,
)
from zenml.orchestrators.base_orchestrator import BaseOrchestratorFlavor
from zenml.orchestrators.local.local_orchestrator import LocalOrchestrator
from zenml.pipelines import run_utils
from zenml.utils.time_utils import utc_now


def test_default_run_name():
    """Tests the default run name value."""
    assert (
        run_utils.get_default_run_name(pipeline_name="my_pipeline")
        == "my_pipeline-{date}-{time}"
    )


class CustomOrchestratorFlavor(BaseOrchestratorFlavor):
    @property
    def name(self) -> str:
        return "custom_orchestrator"

    @property
    def implementation_class(self) -> Type[LocalOrchestrator]:
        return LocalOrchestrator


def _custom_flavor_response(source: str) -> FlavorResponse:
    now = utc_now()
    return FlavorResponse(
        id=uuid4(),
        name="custom_orchestrator",
        body=FlavorResponseBody(
            user_id=uuid4(),
            type=StackComponentType.ORCHESTRATOR,
            display_name="Custom orchestrator",
            integration="custom",
            source=source,
            logo_url=None,
            is_custom=True,
            created=now,
            updated=now,
        ),
        metadata=FlavorResponseMetadata(
            config_schema={},
            connector_type=None,
            connector_resource_type=None,
            connector_resource_id_attr=None,
            docs_url=None,
            sdk_docs_url=None,
        ),
        resources=None,
    )


def _validate_stack_with_flavor(mocker, flavor_model: FlavorResponse) -> None:
    component = SimpleNamespace(
        flavor_name=flavor_model.name,
        type=flavor_model.type,
        configuration={},
    )
    stack = SimpleNamespace(
        components={StackComponentType.ORCHESTRATOR: [component]}
    )
    zen_store = mocker.MagicMock()
    zen_store.list_flavors.return_value = [flavor_model]

    run_utils.validate_stack_is_runnable_from_server(
        zen_store=zen_store, stack=stack
    )


def test_stack_with_importable_custom_flavor_is_runnable_from_server(mocker):
    """Tests that a custom flavor which can be imported passes validation."""
    flavor_model = _custom_flavor_response(
        source=f"{__name__}.CustomOrchestratorFlavor"
    )

    _validate_stack_with_flavor(mocker, flavor_model)


def test_stack_with_unimportable_custom_flavor_is_not_runnable_from_server(
    mocker,
):
    """Tests that a custom flavor which can't be imported fails validation."""
    flavor_model = _custom_flavor_response(
        source="not_installed_module.CustomOrchestratorFlavor"
    )

    with pytest.raises(ValueError) as exc_info:
        _validate_stack_with_flavor(mocker, flavor_model)

    message = str(exc_info.value)
    assert message.startswith(
        "Unable to run pipeline from the server on a stack that includes "
        "stack components with a custom flavor: "
    )
    assert "Couldn't import custom flavor custom_orchestrator" in message
