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
"""Every ZenML MCP tool, resource and prompt, in listing order.

A host registers `TOOL_SPECS` and `CONTENT_SPECS`; `zenml_mcp.registry`
says what each spec holds.
"""

from zenml_mcp import (
    diagnose,
    feedback,
    generic_tools,
    models,
    pipelines,
    run_control,
    stacks,
    steps,
    trigger,
    views,
)
from zenml_mcp.registry import ContentSpec, Tools, ToolSpec

_TOOLS = Tools()
# Registration order is the order of `tools/list`, which clients see, so a
# module whose tools sit in two places of it registers them in two calls.
for _register in (
    pipelines.register,
    steps.register,
    run_control.register_snapshots,
    trigger.register,
    run_control.register_run_control,
    stacks.register,
    models.register,
    pipelines.register_artifacts,
    generic_tools.register,
    views.register,
    pipelines.register_active,
    steps.register_entries_and_source,
    diagnose.register,
    feedback.register,
):
    _register(_TOOLS)

TOOL_SPECS: tuple[ToolSpec, ...] = tuple(_TOOLS.tools)
CONTENT_SPECS: tuple[ContentSpec, ...] = tuple(_TOOLS.contents)
