#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Functionality to administer projects of the ZenML CLI and server."""

from typing import Any, Dict, Optional

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    OutputFormat,
    is_sorted_or_filtered,
    list_options,
    warn_if_project_not_visible_on_oss,
)
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories, RetentionOutcome
from zenml.models import ProjectFilter, ProjectResponse
from zenml.models.v2.misc.retention import (
    RetentionDryRunResponse,
    RetentionSettings,
    RetentionStatusResponse,
)
from zenml.utils.string_utils import get_human_readable_filesize
from zenml.zen_stores.retention.eligibility import EXCLUSION_REASONS


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def project() -> None:
    """Commands for project management."""


@project.group("retention")
def retention() -> None:
    """Manage project execution retention."""


def _retention_policy_rows(policy: RetentionSettings) -> list[Dict[str, Any]]:
    """Build readable key/value rows for a retention policy.

    Args:
        policy: Saved or effective retention policy.

    Returns:
        Ordered setting rows suitable for the shared table printer.
    """
    values = policy.model_dump()
    values["archive_after_days"] = values["archive_after_days"] or "disabled"
    values["max_bytes"] = get_human_readable_filesize(values["max_bytes"])
    return [{"setting": key, "value": value} for key, value in values.items()]


def _print_retention_policy(
    policy: RetentionSettings, title: str = "Retention policy"
) -> None:
    """Print a retention policy as a key/value table.

    Args:
        policy: Saved or effective retention policy.
        title: Table title.
    """
    cli_utils.print_table(_retention_policy_rows(policy), title=title)


def _print_retention_dry_run(result: RetentionDryRunResponse) -> None:
    """Print a bounded retention preview without dictionary representations.

    Args:
        result: Typed preview returned by the client.
    """
    cli_utils.print_table(
        [
            {
                "property": "eligible trees",
                "value": result.eligible_tree_count,
            },
            {
                "property": "examined trees",
                "value": result.examined_tree_count,
            },
            {"property": "truncated", "value": result.truncated},
            {
                "property": "estimated archive size",
                "value": get_human_readable_filesize(result.estimated_bytes),
            },
        ],
        title="Retention preview",
    )
    cli_utils.print_table(
        [
            {
                "root run": tree.root_run_id,
                "rows": tree.rows,
                "status": tree.exclusion_reason or "eligible",
                "reason": (
                    EXCLUSION_REASONS.get(
                        tree.exclusion_reason, tree.exclusion_reason
                    )
                    if tree.exclusion_reason
                    else ""
                ),
            }
            for tree in result.trees
        ],
        title="Execution trees",
    )
    cli_utils.print_table(
        [
            {"detail": detail, "count": count}
            for detail, count in sorted(result.retained_details.items())
        ],
        title="Details retained in SQL",
    )
    _print_retention_policy(result.effective_policy, title="Effective policy")
    cli_utils.declare(
        "Preview only; fixed-weight estimate; no data was changed."
    )


def _retention_preview_summary(result: RetentionDryRunResponse) -> str:
    """Return the compact confirmation summary for an archive pass.

    Args:
        result: Typed preview returned by the client.

    Returns:
        Eligible trees, estimated MiB, and covered rows.
    """
    rows = sum(
        tree.rows for tree in result.trees if tree.exclusion_reason is None
    )
    return (
        f"{result.eligible_tree_count} eligible tree(s), about "
        f"{result.estimated_bytes / (1024 * 1024):.1f} MiB across {rows} rows"
    )


def _print_retention_status(result: RetentionStatusResponse) -> None:
    """Print project retention status as explicit scalar values.

    Args:
        result: Latest saved outcome and effective server configuration.
    """
    cli_utils.print_table(
        [
            {"property": "outcome", "value": result.outcome.value},
            {
                "property": "finished_at",
                "value": result.finished_at.isoformat()
                if result.finished_at
                else "never",
            },
            {
                "property": "archive_enabled",
                "value": result.archive_enabled,
            },
            {
                "property": "archive_configured",
                "value": result.archive_configured,
            },
            {
                "property": "archive_after_days",
                "value": result.archive_after_days or "disabled",
            },
        ],
        title="Retention status",
    )


@retention.command("dry-run")
@click.argument("project_name_or_id", type=str, required=False)
def retention_dry_run(project_name_or_id: Optional[str]) -> None:
    """Report a bounded inventory without changing any data or settings.

    Args:
        project_name_or_id: Project to inspect, or the active project.
    """
    result = Client().retention_dry_run(project=project_name_or_id)
    _print_retention_dry_run(result)


@retention.command("set")
@click.argument("project_name_or_id", type=str, required=False)
@click.option("--archive-after-days", type=int, default=None)
@click.option("--restored-grace-days", type=int, default=None)
@click.option(
    "--archive-model-linked-runs/--no-archive-model-linked-runs",
    default=None,
)
@click.option("--max-trees", type=int, default=None)
@click.option("--max-rows", type=int, default=None)
@click.option("--max-bytes", type=int, default=None)
@click.option("--disable", is_flag=True, help="Clear and disable the policy.")
def set_retention(
    project_name_or_id: Optional[str],
    archive_after_days: Optional[int],
    restored_grace_days: Optional[int],
    archive_model_linked_runs: Optional[bool],
    max_trees: Optional[int],
    max_rows: Optional[int],
    max_bytes: Optional[int],
    disable: bool,
) -> None:
    """Update the saved retention policy while preserving unspecified values.

    Args:
        project_name_or_id: Project to update, or the active project.
        archive_after_days: Minimum completed-run age.
        restored_grace_days: Minimum age after the latest restore.
        archive_model_linked_runs: Whether model-linked runs may be archived.
        max_trees: Maximum trees examined per pass.
        max_rows: Maximum detail rows per pass.
        max_bytes: Maximum fixed-weight estimated bytes per pass.
        disable: Clear the saved policy and disable retention.

    Raises:
        click.UsageError: If disable is combined with policy values.
    """
    updates = {
        "archive_after_days": archive_after_days,
        "restored_grace_days": restored_grace_days,
        "archive_model_linked_runs": archive_model_linked_runs,
        "max_trees": max_trees,
        "max_rows": max_rows,
        "max_bytes": max_bytes,
    }
    if disable and any(value is not None for value in updates.values()):
        raise click.UsageError(
            "--disable cannot be combined with policy values."
        )
    client = Client()
    saved = client.get_project(project_name_or_id).retention
    if disable:
        policy = RetentionSettings()
    else:
        values = saved.model_dump()
        values.update(
            {key: value for key, value in updates.items() if value is not None}
        )
        policy = RetentionSettings(**values)
    client.update_project(
        name_id_or_prefix=project_name_or_id,
        retention=policy,
    )
    cli_utils.success("Retention policy updated.")
    _print_retention_policy(policy)


@retention.command("show")
@click.argument("project_name_or_id", type=str, required=False)
def show_retention(project_name_or_id: Optional[str]) -> None:
    """Show the saved retention policy for a project.

    Args:
        project_name_or_id: Project to inspect, or the active project.
    """
    saved = Client().get_project(project_name_or_id).retention
    _print_retention_policy(saved)


@retention.command("archive")
@click.argument("project_name_or_id", type=str, required=False)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print the current preview without submitting an archive pass.",
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
def archive_project(
    project_name_or_id: Optional[str], dry_run: bool, yes: bool
) -> None:
    """Submit a bounded archive pass using the saved project policy.

    Args:
        project_name_or_id: Project to archive, or the active project.
        dry_run: Whether to stop after the non-destructive preview.
        yes: Whether to submit without interactive confirmation.
    """
    client = Client()
    preview = client.retention_dry_run(project=project_name_or_id)
    summary = _retention_preview_summary(preview)
    cli_utils.declare(summary)
    if dry_run:
        cli_utils.declare("Preview only; no data was changed.")
        return
    if preview.eligible_tree_count == 0:
        cli_utils.declare("No execution trees are currently eligible.")
        return
    if not yes and not cli_utils.confirmation(
        f"{summary}. Do you want to archive them?"
    ):
        cli_utils.declare("Execution retention canceled.")
        return
    result = client.archive_project(project=project_name_or_id)
    if result.outcome == RetentionOutcome.ACCEPTED:
        suffix = f" {project_name_or_id}" if project_name_or_id else ""
        cli_utils.declare(
            "Archive pass accepted; check completion with "
            f"`zenml project retention status{suffix}`."
        )
    else:
        cli_utils.print_pydantic_model("Retention", result)


@retention.command("status")
@click.argument("project_name_or_id", type=str, required=False)
def retention_status(project_name_or_id: Optional[str]) -> None:
    """Show the latest bounded archive pass without reading object storage.

    Args:
        project_name_or_id: Project to inspect, or the active project.
    """
    _print_retention_status(
        Client().get_retention_status(project=project_name_or_id)
    )


@project.command("list")
@list_options(
    ProjectFilter, default_columns=["active", "id", "name", "description"]
)
@click.pass_context
def list_projects(
    ctx: click.Context,
    /,
    columns: str,
    output_format: OutputFormat,
    **kwargs: Any,
) -> None:
    """List all projects.

    Args:
        ctx: The click context object
        columns: Columns to display in output.
        output_format: Format for output (table/json/yaml/csv/tsv).
        **kwargs: Keyword arguments to filter the list of projects.
    """
    client = Client()
    with console.status("Listing projects...\n"):
        projects = client.list_projects(**kwargs, hydrate=True)

    show_active = not is_sorted_or_filtered(ctx)
    if show_active and projects.items:
        try:
            active_project_id = client.active_project.id
            if active_project_id not in {p.id for p in projects.items}:
                projects.items.insert(0, client.active_project)
            projects.items.sort(key=lambda p: p.id != active_project_id)
        except RuntimeError:
            active_project_id = None
    else:
        active_project_id = None

    cli_utils.print_page(
        projects,
        columns,
        output_format,
        empty_message="No projects found for the given filter.",
        row_generator=cli_utils.generate_project_row,
        active_id=active_project_id,
    )


@project.command("register")
@click.option(
    "--set",
    "set_project",
    is_flag=True,
    help="Immediately set this project as active.",
    type=click.BOOL,
)
@click.option(
    "--display-name",
    "display_name",
    type=str,
    required=False,
    help="The display name of the project.",
)
@click.option(
    "--set-default",
    "set_default",
    is_flag=True,
    help="Set this project as the default project.",
)
@click.argument("project_name", type=str, required=True)
def register_project(
    project_name: str,
    set_project: bool = False,
    display_name: Optional[str] = None,
    set_default: bool = False,
) -> None:
    """Register a new project.

    Args:
        project_name: The name of the project to register.
        set_project: Whether to set the project as active.
        display_name: The display name of the project.
        set_default: Whether to set the project as the default project.
    """
    client = Client()
    with console.status("Creating project...\n"):
        try:
            project = client.create_project(
                project_name,
                description="",
                display_name=display_name,
            )
            cli_utils.success("✔ Project created successfully.")
        except Exception as e:
            cli_utils.exception(e)

    if set_project:
        client.set_active_project(project_name)
        cli_utils.success(
            f"✔ The active project has been set to {project_name}"
        )

    if set_default:
        client.update_user(
            name_id_or_prefix=client.active_user.id,
            updated_default_project_id=project.id,
        )
        cli_utils.success(
            f"✔ The default project has been set to {project.name}"
        )
    warn_if_project_not_visible_on_oss(project_name=project_name)


@project.command("set")
@click.argument("project_name_or_id", type=str, required=True)
@click.option(
    "--default",
    "default",
    is_flag=True,
    help="Set this project as the default project.",
)
def set_project(project_name_or_id: str, default: bool = False) -> None:
    """Set the active project.

    Args:
        project_name_or_id: The name or ID of the project to set as active.
        default: Whether to set the project as the default project.
    """
    client = Client()
    with console.status("Setting project...\n"):
        try:
            project = client.set_active_project(project_name_or_id)
            cli_utils.success(
                f"✔ The active project has been set to {project_name_or_id}"
            )
        except Exception as e:
            cli_utils.exception(e)

    if default:
        client.update_user(
            name_id_or_prefix=client.active_user.id,
            updated_default_project_id=project.id,
        )
        cli_utils.declare(
            f"The default project has been set to {project.name}"
        )
    warn_if_project_not_visible_on_oss(project_name=project_name_or_id)


@project.command("describe")
@click.argument("project_name_or_id", type=str, required=False)
def describe_project(project_name_or_id: Optional[str] = None) -> None:
    """Get the project.

    Args:
        project_name_or_id: The name or ID of the project to set as active.
    """
    client = Client()
    if not project_name_or_id:
        project_: ProjectResponse = client.active_project
    else:
        try:
            project_ = client.get_project(project_name_or_id)
        except KeyError as err:
            cli_utils.exception(err)
        else:
            warn_if_project_not_visible_on_oss(project_name=project_name_or_id)
    cli_utils.print_pydantic_models(
        [project_], exclude_columns=["created", "updated", "retention"]
    )
    _print_retention_policy(project_.retention)


@project.command("delete")
@click.argument("project_name_or_id", type=str, required=True)
def delete_project(project_name_or_id: str) -> None:
    """Delete a project.

    Args:
        project_name_or_id: The name or ID of the project to delete.
    """
    client = Client()
    with console.status("Deleting project...\n"):
        try:
            client.delete_project(project_name_or_id)
            cli_utils.declare(
                f"Project '{project_name_or_id}' deleted successfully."
            )
        except Exception as e:
            cli_utils.exception(e)
