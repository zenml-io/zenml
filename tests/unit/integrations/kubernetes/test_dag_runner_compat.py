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

# ruff: noqa: D100,D103

from zenml.integrations.kubernetes.orchestrators import dag_runner
from zenml.orchestrators import monitored_dag_runner


def test_kubernetes_dag_runner_import_path_reexports_monitored_runner() -> (
    None
):
    assert dag_runner.DagRunner is monitored_dag_runner.DagRunner
    assert dag_runner.InterruptMode is monitored_dag_runner.InterruptMode
    assert dag_runner.Node is monitored_dag_runner.Node
    assert dag_runner.NodeStatus is monitored_dag_runner.NodeStatus
