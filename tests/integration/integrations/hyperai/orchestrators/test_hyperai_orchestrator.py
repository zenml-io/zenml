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
from datetime import datetime
from uuid import uuid4

from zenml.enums import StackComponentType
from zenml.integrations.hyperai.flavors.hyperai_orchestrator_flavor import (
    HyperAIOrchestratorConfig,
)
from zenml.integrations.hyperai.orchestrators.hyperai_orchestrator import (
    HyperAIOrchestrator,
)


def test_hyperai_orchestrator_attributes():
    """Tests that the basic attributes of the HyperAI orchestrator are set correctly."""
    orchestrator = HyperAIOrchestrator(
        name="",
        id=uuid4(),
        config=HyperAIOrchestratorConfig(),
        flavor="hyperai",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )

    assert orchestrator.type == StackComponentType.ORCHESTRATOR
    assert orchestrator.flavor == "hyperai"
    assert orchestrator.config.is_remote is True
    assert orchestrator.config.container_registry_autologin is False
    assert orchestrator.config.automatic_cleanup_pipeline_files is True
    assert orchestrator.config.gpu_enabled_in_container is True


def test_validate_mount_path():
    """Tests that only valid mount paths are accepted by the HyperAI orchestrator."""
    orchestrator = HyperAIOrchestrator(
        name="",
        id=uuid4(),
        config=HyperAIOrchestratorConfig(),
        flavor="hyperai",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )

    # Valid POSIX path
    valid_posix_path = "/mnt/hello/there"
    assert (
        orchestrator._validate_mount_path(valid_posix_path) == valid_posix_path
    )

    # Valid Windows path
    valid_windows_path = r"C:\\Users\\user\\Documents"
    assert (
        orchestrator._validate_mount_path(valid_windows_path)
        == valid_windows_path
    )

    # Invalid POSIX path
    invalid_posix_path = "echo '>something>' ; /mnt/hello/there/.."
    try:
        orchestrator._validate_mount_path(invalid_posix_path)
    except RuntimeError:
        pass

    # Invalid Windows path
    invalid_windows_path = (
        "set SOMETHING=123; C:\\Users\\user\\Documents\\..\\file.txt"
    )
    try:
        orchestrator._validate_mount_path(invalid_windows_path)
    except RuntimeError:
        pass
