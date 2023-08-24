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
"""Model for mlstacks stack spec."""
from typing import Any, Dict, Optional

from pydantic import BaseModel


class MlstacksSpec(BaseModel):
    """Pydantic model for stack components."""

    provider: str
    stack_name: str
    region: str
    import_stack_flag: bool = False
    mlops_platform: Optional[str] = None
    artifact_store: Optional[bool] = None
    orchestrator: Optional[str] = None
    container_registry: Optional[bool] = None
    model_deployer: Optional[str] = None
    experiment_tracker: Optional[str] = None
    secrets_manager: Optional[bool] = None
    step_operator: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
