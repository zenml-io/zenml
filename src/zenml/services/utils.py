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
"""Utility functions for service management."""

from typing import Optional
from uuid import UUID

from zenml.client import Client
from zenml.exceptions import StepContextError
from zenml.model.model import Model
from zenml.models.v2.core.service import ServiceUpdate
from zenml.new.steps.step_context import get_step_context


def link_service_to_model(
    service_id: UUID,
    model: Optional["Model"] = None,
    model_version_id: Optional[UUID] = None,
) -> None:
    """Links a service to a model.

    Args:
        service_id: The ID of the service to link to the model.
        model: The model to link the service to.
        model_version_id: The ID of the model version to link the service to.
    """
    client = Client()

    # If no model is provided, try to get it from the context
    if not model and not model_version_id:
        is_issue = False
        try:
            step_context = get_step_context()
            model = step_context.model
        except StepContextError:
            is_issue = True

        if model is None or is_issue:
            raise RuntimeError(
                "`link_artifact_to_model` called without `model` parameter "
                "and configured model context cannot be identified. Consider "
                "passing the `model` explicitly or configuring it in "
                "@step or @pipeline decorator."
            )

    model_version_id = (
        model_version_id or model._get_or_create_model_version().id
        if model
        else None
    )
    update_service = ServiceUpdate(model_version_id=model_version_id)
    client.zen_store.update_service(
        service_id=service_id, update=update_service
    )
