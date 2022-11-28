#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Utility functions for the orchestrator."""

import random
from typing import TYPE_CHECKING
from uuid import UUID

from zenml.client import Client
from zenml.logger import get_logger
from zenml.utils import uuid_utils

if TYPE_CHECKING:
    from zenml.orchestrators import BaseOrchestrator

logger = get_logger(__name__)


def get_orchestrator_run_name(pipeline_name: str) -> str:
    """Gets an orchestrator run name.

    This run name is not the same as the ZenML run name but can instead be
    used to display in the orchestrator UI.

    Args:
        pipeline_name: Name of the pipeline that will run.

    Returns:
        The orchestrator run name.
    """
    user_name = Client().active_user.name
    return f"{pipeline_name}_{user_name}_{random.Random().getrandbits(32):08x}"


def get_run_id_for_orchestrator_run_id(
    orchestrator: "BaseOrchestrator", orchestrator_run_id: str
) -> UUID:
    """Generates a run ID from an orchestrator run id.

    Args:
        orchestrator: The orchestrator of the run.
        orchestrator_run_id: The orchestrator run id.

    Returns:
        The run id generated from the orchestrator run id.
    """
    run_id_seed = f"{orchestrator.id}-{orchestrator_run_id}"
    return uuid_utils.generate_uuid_from_string(run_id_seed)
