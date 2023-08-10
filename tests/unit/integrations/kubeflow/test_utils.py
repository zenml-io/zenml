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
"""Unit tests for utils.py."""

import sys

import pytest

from zenml.integrations.kubeflow.utils import apply_pod_settings
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings


@pytest.mark.skipif(
    sys.version_info > (3, 10),
    reason="Kubeflow integration not installed in python 3.11",
)
def test_apply_pod_settings():
    """Unit test for `apply_pod_settings`."""
    from kfp.dsl import ContainerOp

    container_op = ContainerOp(
        name="test",
        image="test",
    )
    pod_settings = KubernetesPodSettings(
        annotations={"blupus_loves": "strawberries"},
    )
    apply_pod_settings(container_op, pod_settings)
    assert container_op.pod_annotations["blupus_loves"] == "strawberries"
