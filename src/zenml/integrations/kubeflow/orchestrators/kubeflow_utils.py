# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Common utility for Kubeflow-based orchestrator."""


# utils.py should not be used in container_entrypoint.py because of its
# dependency on KFP.
from kfp import dsl
from tfx.dsl.components.base import base_node
from tfx.orchestration import data_types


def replace_placeholder(component: base_node.BaseNode) -> None:
    """Replaces the RuntimeParameter placeholders with kfp.dsl.PipelineParam."""
    keys = list(component.exec_properties.keys())
    for key in keys:
        exec_property = component.exec_properties[key]
        if not isinstance(exec_property, data_types.RuntimeParameter):
            continue
        component.exec_properties[key] = str(
            dsl.PipelineParam(name=exec_property.name)
        )


def fix_brackets(placeholder: str) -> str:
    """Fix the imbalanced brackets in placeholder.
    When ptype is not null, regex matching might grab a placeholder with }
    missing. This function fix the missing bracket.
    Args:
      placeholder: string placeholder of RuntimeParameter
    Returns:
      Placeholder with re-balanced brackets.
    Raises:
      RuntimeError: if left brackets are less than right brackets.
    """
    lcount = placeholder.count("{")
    rcount = placeholder.count("}")
    if lcount < rcount:
        raise RuntimeError(
            "Unexpected redundant left brackets found in {}".format(placeholder)
        )
    else:
        patch = "".join(["}"] * (lcount - rcount))
        return placeholder + patch
