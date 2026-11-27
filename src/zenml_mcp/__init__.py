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
"""The ZenML MCP server's tools, for a local server or a hosting server.

This package imports only the MCP SDK, httpx and pydantic, never `zenml`:
importing anything under `zenml.` loads all of ZenML, which a server that
hosts these tools may not be able to install. Its tools call a ZenML server's
REST API with a client built for each call (`zenml_mcp.client`), and the
list of them is `zenml_mcp.tools.TOOL_SPECS`.
"""
