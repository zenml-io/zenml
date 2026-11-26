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
"""mcp-zenml's views, the tools that open them, its prompts and its resources.

Ported from mcp-zenml's `server/zenml_server.py` and `server/ui/` (commit
3de0643). The HTML files under `ui/` are upstream's, byte for byte. Upstream's
views import their App library from unpkg; this server inlines the same
published build, `ui/ext-apps-1.0.1/app-with-deps.js`, so a view loads nothing
from another origin. The views call tools by upstream's names; the one this
server names differently is renamed. A view sends the arguments of the call
that opened it with each of its own tool calls, so a host whose view tools
take an argument, such as the server to read, has every call read the same.
"""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path
from typing import Any

from zenml_mcp.call import ZenMLCall
from zenml_mcp.client import ZenMLBadRequest
from zenml_mcp.common import ZENML_READ, default_project_id
from zenml_mcp.registry import Tools
from zenml_mcp.resources import catalog, projected

_UI_ROOT = Path(__file__).resolve().parent / "ui"
DASHBOARD_UI_URI = "ui://zenml/apps/pipeline-runs/index.html"
CHART_UI_URI = "ui://zenml/apps/run-activity-chart/index.html"
APP_MIME_TYPE = "text/html;profile=mcp-app"
_EXT_APPS_IMPORT = (
    'import { App } from "https://unpkg.com/@modelcontextprotocol/ext-apps@1.0.1/'
    'app-with-deps";'
)
# Upstream's tool names that this server spells differently.
_STEP_LOGS = re.compile(r"(?<!\w)get_step_logs(?!\w)")
# The views recognize upstream's error envelope; this server's names its
# `kind` where upstream has `tool` and `type`, so a refusal shows as an error.
_ERROR_FIELDS = (
    (
        "typeof data.error.tool ===",
        "typeof (data.error.tool ?? data.error.kind) ===",
    ),
    (
        "typeof data.error.type ===",
        "typeof (data.error.type ?? data.error.kind) ===",
    ),
)
# The step log tool returns the newest 200 entries unless asked for more, so the
# run dashboard asks for them by number and shows the note of a cut answer.
_BOUNDED_LOGS = (
    (
        'callServerToolSafe("get_step_logs", { step_run_id: stepId })',
        'callServerToolSafe("get_step_logs", { step_run_id: stepId, tail: 200 })',
    ),
    (
        'const text = data.logs.map(e => e.message ?? JSON.stringify(e)).join("\\n");',
        "const text = [\n"
        "          ...data.logs.map(e => e.message ?? JSON.stringify(e)),\n"
        '          ...(data.note ? ["", data.note] : []),\n'
        '        ].join("\\n");',
    ),
)
# A list answer too large for one tool result is cut, and its `next` holds the
# size and page of the call that reads on. The views count the items of the
# pages they ask for, so each of their list calls follows `next` until its page
# is whole, or until the list's `total` ends it: ZenML refuses a page past the
# last item.
_LIST_PAGE = r"""    /** Page `args.page` of `args.size` items, read on through cut answers. */
    async function listPage(args) {
      const size = args.size;
      let next = { size, page: args.page ?? 1 };
      let first;
      const items = [];
      while (items.length < size) {
        const data = await callServerToolSafe("zenml_list_resources", {
          ...args,
          ...next,
        });
        if (!Array.isArray(data?.items)) return data;
        first ??= data;
        items.push(...data.items);
        if (data.next) {
          next = { size: data.next.size, page: data.next.page };
        } else if (
          data.items.length === next.size &&
          next.page * next.size < data.total
        ) {
          next = { size: next.size, page: next.page + 1 };
        } else {
          break;
        }
      }
      const { note, truncated, next: _, ...whole } = first;
      return { ...whole, items: items.slice(0, size) };
    }

"""
_ENVELOPE_CHECK = (
    "    /** Check if a parsed result is a structured error envelope. */"
)
_WHOLE_PAGES = (
    ('callServerToolSafe("zenml_list_resources", ', "listPage("),
    (_ENVELOPE_CHECK, _LIST_PAGE + _ENVELOPE_CHECK),
)
# The host hands a view the arguments of the tool call that opened it, but only
# after the view's first fetch has left. If that call is refused, it is asked
# again with them, or its refusal would stay on screen over the runs that
# follow.
_IN_WORKSPACE = (
    (
        "app.callServerTool({ name: toolName, arguments: args })",
        "callOpenedIn(toolName, args)",
    ),
    (
        "    app.ontoolresult = () => {",
        "    let openedIn = {};\n"
        "    app.ontoolinput = (input) => {\n"
        "      const opened = input?.arguments ?? {};\n"
        "      const changed = JSON.stringify(opened) !== JSON.stringify(openedIn);\n"
        "      if (Object.keys(opened).length && changed) {\n"
        "        openedIn = { ...opened };\n"
        "      }\n"
        "    };\n"
        "    async function callOpenedIn(name, args) {\n"
        "      const sent = openedIn;\n"
        "      const result = await app.callServerTool({\n"
        "        name,\n"
        "        arguments: { ...args, ...sent },\n"
        "      });\n"
        "      const again = result.isError && sent !== openedIn;\n"
        "      return again ? callOpenedIn(name, args) : result;\n"
        "    }\n\n"
        "    app.ontoolresult = () => {",
    ),
)
RECENT_RUNS_URI = (
    "resource://zenml_server/most_recent_runs?run_count={run_count}"
)
# A larger `run_count` is answered with this many runs.
RECENT_RUNS_MAX = 100
# Upstream allows unpkg here; the inlined library needs no other origin.
_VIEW_META: dict[str, Any] = {"ui": {"csp": {"resourceDomains": []}}}


@cache
def _ext_apps() -> str:
    """The App class of ext-apps 1.0.1, defined where upstream imports it.

    Returns:
        JavaScript that defines `App` from the inlined bundle.
    """
    bundle = (_UI_ROOT / "ext-apps-1.0.1" / "app-with-deps.js").read_text(
        "utf-8"
    )
    body, exports = bundle.rsplit("export{", 1)
    local = next(
        name.removesuffix(" as App")
        for name in exports.rstrip().removesuffix("};").split(",")
        if name.endswith(" as App")
    )
    return f"const {{ App }} = (() => {{\n{body}\nreturn {{ App: {local} }};\n}})();"


@cache
def _view(name: str) -> str:
    html = (_UI_ROOT / name / "index.html").read_text("utf-8")
    logs = _BOUNDED_LOGS if name == "pipeline-runs" else ()
    for upstream, here in (
        *_ERROR_FIELDS,
        *logs,
        *_WHOLE_PAGES,
        *_IN_WORKSPACE,
    ):
        if upstream not in html:
            raise LookupError(
                f"upstream's {name} view no longer has {upstream!r}"
            )
        html = html.replace(upstream, here)
    return _STEP_LOGS.sub("zenml_get_step_log_entries", html).replace(
        _EXT_APPS_IMPORT, _ext_apps()
    )


async def stack_components_analysis() -> str:
    """Analyze the stacks in the ZenML workspace."""  # noqa: DOC201
    return (
        "Please generate a comprehensive report or dashboard on our ZenML stack components, "
        "showing which ones are most frequently used across our pipelines. "
        "Include information about version compatibility issues and performance variations."
    )


async def recent_runs_analysis() -> str:
    """Analyze the recent runs in the ZenML workspace."""  # noqa: DOC201
    return (
        "Please generate a comprehensive report or dashboard on our recent runs, "
        "showing which pipelines are most frequently run and which ones are most frequently failed."
        " Include information about the status of the runs, the duration, and the stack components used."
    )


async def pipeline_runs_dashboard_ui() -> str:
    """ZenML MCP App: Pipeline Run Dashboard (HTML entrypoint)."""  # noqa: DOC201
    return _view("pipeline-runs")


async def run_activity_chart_ui() -> str:
    """ZenML MCP App: Run Activity Chart (HTML entrypoint)."""  # noqa: DOC201
    return _view("run-activity-chart")


async def list_apps() -> str:
    """List available MCP Apps provided by this server."""  # noqa: DOC201
    return json.dumps(
        {
            "apps": [
                {
                    "id": "zenml.pipeline_runs_dashboard",
                    "title": "Pipeline Run Dashboard",
                    "description": "Interactive dashboard showing recent pipeline runs with status, steps, and logs.",
                    "entry": DASHBOARD_UI_URI,
                },
                {
                    "id": "zenml.run_activity_chart",
                    "title": "Run Activity Chart",
                    "description": "Interactive bar chart showing pipeline run activity over the last 30 days with status breakdown.",
                    "entry": CHART_UI_URI,
                },
            ]
        }
    )


async def zenml_open_pipeline_run_dashboard(call: ZenMLCall) -> str:
    """Open an interactive dashboard of recent ZenML pipeline runs.

    The dashboard shows pipeline runs with status indicators, expandable step
    details, filtering, and drill-down into step logs — all in an interactive UI.
    The dashboard fetches its own data dynamically.
    """  # noqa: DOC101, DOC103, DOC201
    return (
        "Requested the ZenML pipeline runs dashboard. An MCP Apps-capable host "
        "can render it and load current data. If no interactive view appears, "
        "use zenml_list_resources for pipeline_run and run_step resources, then "
        "use zenml_get_step_log_entries for a selected step."
    )


async def zenml_open_run_activity_chart(call: ZenMLCall) -> str:
    """Open an interactive chart showing pipeline run activity over the last 30 days.

    Shows a bar chart with daily run counts, hover tooltips, and status
    breakdown (completed in green, failed in red, other in amber).
    """  # noqa: DOC101, DOC103, DOC201
    return (
        "Requested the ZenML pipeline run activity chart. An MCP Apps-capable "
        "host can render it and load current data. If no interactive view appears, "
        "use zenml_list_resources for pipeline_run resources with a descending "
        "created-time sort."
    )


async def most_recent_runs(call: ZenMLCall, run_count: int = 10) -> str:
    """Returns the ten most recent runs in the ZenML workspace.

    Args:
        call: The read's call.
        run_count: The number of runs to return, at most 100

    Returns:
        The runs' page, as JSON.

    Raises:
        ZenMLBadRequest: When `run_count` is below 1.
    """
    if run_count < 1:
        raise ZenMLBadRequest("run_count must be at least 1")
    client = call.client
    page = await client.get(
        "/runs",
        params={
            "sort_by": "desc:created",
            "page": 1,
            "size": min(run_count, RECENT_RUNS_MAX),
            "logical_operator": "and",
            "project": await default_project_id(client),
            "hydrate": False,
            "include_full_metadata": False,
        },
        what="Listing the most recent pipeline runs",
    )
    items = projected(page.get("items", []), resource_type="pipeline_run")
    return json.dumps({**page, "items": items})


def register(tools: Tools) -> None:
    """Register the views, the tools that open them, prompts and resources.

    Args:
        tools: Where they are registered.
    """

    async def zenml_resource_catalog(call: ZenMLCall) -> str:
        """Return the bounded generic-resource catalog without detailed schemas."""  # noqa: DOC101, DOC103, DOC201
        return json.dumps(catalog(read_only=call.read_only))

    async def zenml_resource_operation_schema(
        call: ZenMLCall, resource_type: str, operation: str
    ) -> str:
        """Return one bounded generic-resource operation schema."""  # noqa: DOC101, DOC103, DOC201
        return json.dumps(
            catalog(resource_type, operation, read_only=call.read_only)
        )

    for uri, read in (
        ("resource://zenml_server/resources", zenml_resource_catalog),
        (
            "resource://zenml_server/resource-schemas/{resource_type}/{operation}",
            zenml_resource_operation_schema,
        ),
        ("resource://zenml_server/apps", list_apps),
    ):
        tools.resource(uri, mime_type="application/json")(read)
    for uri, read in (
        (DASHBOARD_UI_URI, pipeline_runs_dashboard_ui),
        (CHART_UI_URI, run_activity_chart_ui),
    ):
        tools.resource(uri, mime_type=APP_MIME_TYPE, meta=_VIEW_META)(read)
    tools.resource(RECENT_RUNS_URI)(most_recent_runs)
    for name, prompt in (
        ("zenml_stack_components_analysis", stack_components_analysis),
        ("zenml_recent_runs_analysis", recent_runs_analysis),
    ):
        tools.prompt(name)(prompt)
    for uri, opens in (
        (DASHBOARD_UI_URI, zenml_open_pipeline_run_dashboard),
        (CHART_UI_URI, zenml_open_run_activity_chart),
    ):
        tools.tool(
            annotations=ZENML_READ,
            meta={"ui": {"resourceUri": uri}},
        )(opens)
