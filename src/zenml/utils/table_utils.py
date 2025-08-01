#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Enhanced table utilities for ZenML CLI commands.

This module provides a centralized table rendering system for all ZenML CLI
commands. It ensures consistent formatting, supports multiple output formats,
and handles special cases like active stack indicators and status colorization.

Key Features:
- Consistent table formatting across all CLI commands
- Multiple output formats: table, json, yaml, tsv, none
- Special formatting for stack data (active indicators)
- Status value colorization (active=green, failed=red, pending=yellow)
- Terminal width detection and responsive formatting
- Pagination support for JSON/YAML outputs
- Proper handling of Unicode, special characters, and missing data

Usage Examples:
    Basic table display:
        >>> data = [{"name": "test", "status": "active"}]
        >>> zenml_table(data)

    JSON output with pagination:
        >>> pagination = {"index": 1, "total": 10, "max_size": 20}
        >>> zenml_table(data, output_format="json", pagination=pagination)

    Custom column selection and sorting:
        >>> zenml_table(data, columns=["name"], sort_by="status", reverse=True)

Guidelines for CLI Command Integration:
1. Always use zenml_table() instead of custom table formatting
2. Pass pagination metadata for paginated responses
3. Use consistent column naming (lowercase with underscores)
4. Include "__is_active__" field for stack data to enable special formatting
5. Status-like columns will be automatically colorized

Internal Field Conventions:
- Fields starting with "__" are considered internal and removed from
  non-table outputs
- "__is_active__" triggers special stack formatting (green dot, bold text)
"""

import json
import os
import shutil
from typing import Any, Dict, List, Literal, Optional

import yaml
from rich import box
from rich.console import Console
from rich.table import Table


def zenml_table(
    data: List[Dict[str, Any]],
    output_format: str = "table",
    columns: Optional[List[str]] = None,
    sort_by: Optional[str] = None,
    reverse: bool = False,
    no_truncate: bool = False,
    no_color: bool = False,
    max_width: Optional[int] = None,
    pagination: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> None:
    """Render data in specified format following ZenML CLI table guidelines.

    This function provides a centralized way to render tabular data across
    all ZenML CLI commands with consistent formatting and multiple output
    formats.

    Args:
        data: List of dictionaries to render
        output_format: Output format (table, json, yaml, tsv, none)
        columns: Optional list of column names to include
        sort_by: Column to sort by
        reverse: Whether to reverse sort order
        no_truncate: Whether to disable truncation
        no_color: Whether to disable colored output
        max_width: Maximum table width (default: use terminal width)
        pagination: Optional pagination metadata for JSON/YAML output
        **kwargs: Additional formatting options

    Raises:
        ValueError: If an unsupported output format is provided
    """
    if not data:
        return

    # Handle output format
    if output_format == "none":
        return
    elif output_format == "json":
        _render_json(data, columns, sort_by, reverse, pagination)
    elif output_format == "yaml":
        _render_yaml(data, columns, sort_by, reverse, pagination)
    elif output_format == "tsv":
        _render_tsv(data, columns, sort_by, reverse)
    elif output_format == "table":
        _render_table(
            data, columns, sort_by, reverse, no_truncate, no_color, max_width
        )
    else:
        raise ValueError(f"Unsupported output format: {output_format}")


def _apply_stack_formatting(
    data: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Apply special formatting for stack tables when rendering to table format.

    This function detects stack data and applies visual formatting for active
    stacks. Only applies formatting for table output - JSON/YAML output
    remains clean.

    Args:
        data: List of data dictionaries to format

    Returns:
        List of formatted data dictionaries with stack formatting applied
    """
    if not data or not isinstance(data, list):
        return data

    # Check if this looks like stack data (has '__is_active__' field)
    if not any(
        isinstance(row, dict) and "__is_active__" in row for row in data
    ):
        return data

    formatted_data = []
    for row in data:
        if not isinstance(row, dict):
            formatted_data.append(row)
            continue

        # Create a copy to avoid modifying original data
        formatted_row = dict(row)

        # Apply formatting for active stacks
        if row.get("__is_active__", False):
            # Format name with green dot and active indicator
            name = row.get("name", "")
            formatted_row["name"] = (
                f"[green]●[/green] [bold green]{name}[/bold green] (active)"
            )

            # Apply bold formatting to other fields
            for key, value in formatted_row.items():
                if key not in ["name", "__is_active__"] and value is not None:
                    formatted_row[key] = f"[bold]{value}[/bold]"

        # Remove the __is_active__ field as it's just for formatting logic
        formatted_row.pop("__is_active__", None)
        formatted_data.append(formatted_row)

    return formatted_data


def _apply_model_version_formatting(
    data: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Apply special formatting for model version tables when rendering to table.

    This function detects model version data and applies visual formatting for
    different stages:
    - Production: Green dot and bold text
    - Staging: Orange dot and text
    Only applies formatting for table output - JSON/YAML output remains clean.

    Args:
        data: List of data dictionaries to format

    Returns:
        List of formatted data dictionaries with model version formatting applied
    """
    if not data or not isinstance(data, list):
        return data

    # Check if this looks like model version data (has '__stage_value__' field)
    if not any(
        isinstance(row, dict) and "__stage_value__" in row for row in data
    ):
        return data

    formatted_data = []
    for row in data:
        if not isinstance(row, dict):
            formatted_data.append(row)
            continue

        # Create a copy to avoid modifying original data
        formatted_row = dict(row)

        # Apply formatting based on stage
        stage_value = row.get("__stage_value__", "") or ""
        stage_display = row.get("stage", "") or ""

        # Ensure stage_value is a string before calling lower()
        if not isinstance(stage_value, str):
            stage_value = str(stage_value) if stage_value is not None else ""
        stage_value = stage_value.lower()

        if stage_value == "production":
            # Format with green dot at beginning, green model name and version
            model_name = row.get("model", "")
            version_name = row.get("version", "")
            formatted_row["model"] = (
                f"[green]●[/green] [bold green]{model_name}[/bold green]"
            )
            formatted_row["version"] = (
                f"[bold green]{version_name}[/bold green]"
            )
            formatted_row["stage"] = (
                f"[bold green]{stage_display}[/bold green]"
            )
        elif stage_value == "staging":
            # Format with orange dot at beginning, orange name and version
            model_name = row.get("model", "")
            version_name = row.get("version", "")
            formatted_row["model"] = (
                f"[bright_yellow]●[/bright_yellow] "
                f"[bright_yellow]{model_name}[/bright_yellow]"
            )
            formatted_row["version"] = (
                f"[bright_yellow]{version_name}[/bright_yellow]"
            )
            formatted_row["stage"] = (
                f"[bright_yellow]{stage_display}[/bright_yellow]"
            )
        # For other stages (development, archived, etc.), keep default format

        # Remove the __stage_value__ field as it's just for formatting logic
        formatted_row.pop("__stage_value__", None)
        formatted_data.append(formatted_row)

    return formatted_data


def _prepare_data(
    data: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    sort_by: Optional[str] = None,
    reverse: bool = False,
    clean_internal_fields: bool = False,
) -> List[Dict[str, Any]]:
    """Prepare data for rendering by filtering columns and sorting.

    Args:
        data: List of dictionaries to prepare
        columns: Optional list of column names to include
        sort_by: Column to sort by
        reverse: Whether to reverse sort order
        clean_internal_fields: Whether to remove internal fields (starting
            with __)

    Returns:
        Prepared data list
    """
    if not data:
        return []

    # Clean internal fields if requested (for JSON/YAML output)
    if clean_internal_fields:
        cleaned_data = []
        for row in data:
            if isinstance(row, dict):
                clean_row = {
                    k: v for k, v in row.items() if not k.startswith("__")
                }
                cleaned_data.append(clean_row)
            else:
                cleaned_data.append(row)
        data = cleaned_data

    # Filter columns if specified
    if columns:
        filtered_data = []
        for row in data:
            filtered_row = {}
            for col in columns:
                if col in row:
                    filtered_row[col] = row[col]
                else:
                    filtered_row[col] = ""
            filtered_data.append(filtered_row)
        data = filtered_data

    # Sort data if specified
    if sort_by and data and sort_by in data[0]:
        try:
            data = sorted(
                data, key=lambda x: x.get(sort_by, ""), reverse=reverse
            )
        except (TypeError, ValueError):
            # If sorting fails, continue without sorting
            pass

    return data


def _render_json(
    data: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    sort_by: Optional[str] = None,
    reverse: bool = False,
    pagination: Optional[Dict[str, Any]] = None,
) -> None:
    """Render data as JSON.

    Args:
        data: List of data dictionaries to render
        columns: Optional list of column names to include
        sort_by: Column to sort by
        reverse: Whether to reverse sort order
        pagination: Optional pagination metadata
    """
    prepared_data = _prepare_data(
        data, columns, sort_by, reverse, clean_internal_fields=True
    )

    # Add pagination metadata if provided
    if pagination:
        output_data = {"items": prepared_data, "pagination": pagination}
        print(json.dumps(output_data, indent=2, default=str))
    else:
        print(json.dumps(prepared_data, indent=2, default=str))


def _render_yaml(
    data: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    sort_by: Optional[str] = None,
    reverse: bool = False,
    pagination: Optional[Dict[str, Any]] = None,
) -> None:
    """Render data as YAML.

    Args:
        data: List of data dictionaries to render
        columns: Optional list of column names to include
        sort_by: Column to sort by
        reverse: Whether to reverse sort order
        pagination: Optional pagination metadata
    """
    prepared_data = _prepare_data(
        data, columns, sort_by, reverse, clean_internal_fields=True
    )

    # Add pagination metadata if provided
    if pagination:
        output_data = {"items": prepared_data, "pagination": pagination}
        print(yaml.dump(output_data, default_flow_style=False))
    else:
        print(yaml.dump(prepared_data, default_flow_style=False))


def _render_tsv(
    data: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    sort_by: Optional[str] = None,
    reverse: bool = False,
) -> None:
    """Render data as TSV (Tab-Separated Values).

    Args:
        data: List of data dictionaries to render
        columns: Optional list of column names to include
        sort_by: Column to sort by
        reverse: Whether to reverse sort order
    """
    prepared_data = _prepare_data(
        data, columns, sort_by, reverse, clean_internal_fields=True
    )

    if not prepared_data:
        return

    # Get headers
    headers = columns if columns else list(prepared_data[0].keys())

    # Print headers
    print("\t".join(headers))

    # Print data
    for row in prepared_data:
        values = []
        for header in headers:
            value = str(row.get(header, ""))
            # Escape tabs and newlines in TSV
            value = (
                value.replace("\t", " ").replace("\n", " ").replace("\r", " ")
            )
            values.append(value)
        print("\t".join(values))


def _render_table(
    data: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    sort_by: Optional[str] = None,
    reverse: bool = False,
    no_truncate: bool = False,
    no_color: bool = False,
    max_width: Optional[int] = None,
) -> None:
    """Render data as a formatted table following ZenML guidelines.

    Args:
        data: List of data dictionaries to render
        columns: Optional list of column names to include
        sort_by: Column to sort by
        reverse: Whether to reverse sort order
        no_truncate: Whether to disable truncation
        no_color: Whether to disable colored output
        max_width: Maximum table width
    """
    prepared_data = _prepare_data(data, columns, sort_by, reverse)

    if not prepared_data:
        return

    # Apply special formatting for stack tables and model version tables
    prepared_data = _apply_stack_formatting(prepared_data)
    prepared_data = _apply_model_version_formatting(prepared_data)

    # Get headers - use columns if specified, otherwise all keys
    headers = columns if columns else list(prepared_data[0].keys())

    # Calculate content-based width requirements
    content_width = _calculate_content_width(prepared_data, headers)

    # Determine terminal width
    terminal_width = _get_terminal_width()
    if terminal_width:
        if max_width is not None:
            # Use provided max_width as a cap
            available_width = min(terminal_width, max_width)
        else:
            # Use terminal width (cap at reasonable maximum)
            available_width = min(terminal_width, 200)
    else:
        # Fallback if terminal width cannot be determined
        available_width = max_width if max_width is not None else 120

    # Decide table width strategy
    if no_truncate or content_width <= available_width:
        # Content fits or user wants no truncation - use content-based width
        table_width = None  # Let Rich auto-size
        expand_table = False
    else:
        # Content too wide - use available width with truncation
        table_width = available_width
        expand_table = True

    # Detect if this is a service connectors table by checking for specific columns
    is_service_connectors_table = (
        headers
        and "resource types" in [h.lower() for h in headers]
        and "type" in [h.lower() for h in headers]
        and len(
            [
                h
                for h in headers
                if h.lower()
                in [
                    "name",
                    "resource types",
                    "type",
                    "resource name",
                    "owner",
                    "expires",
                    "labels",
                ]
            ]
        )
        >= 3
    )

    # Create Rich table following ZenML guidelines
    rich_table = Table(
        box=box.SIMPLE_HEAD,  # Simple line below header only
        show_header=True,
        show_lines=False,  # Keep lines off by default
        pad_edge=False,
        collapse_padding=False,  # Increase spacing between columns
        expand=expand_table,  # Only expand to full width when needed
        width=table_width,  # Set explicit width only when needed
    )

    # Add columns with consistent left alignment
    for i, header in enumerate(headers):
        # Upper-case column headings
        header_display = header.upper()

        # Determine best overflow behavior for CLI
        overflow: Literal["fold", "crop", "ellipsis", "ignore"]

        # Special handling for resource types, labels, resource name, and name columns to allow multi-line content
        is_resources_column = header.lower() == "resource types"
        is_labels_column = header.lower() == "labels"
        is_resource_name_column = header.lower() == "resource name"
        is_name_column = header.lower() == "name"

        if (
            no_truncate
            or is_resources_column
            or is_labels_column
            or is_resource_name_column
            or is_name_column
        ):
            # Show full content, allow wrapping
            overflow = "fold"
            no_wrap = False
        else:
            # For CLI, crop content cleanly without ellipsis
            overflow = "crop"
            no_wrap = True

        # Calculate appropriate column width based on content
        col_width = _calculate_column_width(
            prepared_data,
            header,
            available_width,
            len(headers),
            no_truncate
            or is_resources_column
            or is_labels_column
            or is_resource_name_column
            or is_name_column,
        )

        # Special width adjustments for service connector table columns
        if is_service_connectors_table:
            if header.lower() == "type":
                # Ensure type column has enough width for emoji + short name
                col_width = max(
                    col_width or 0, 12
                )  # Minimum 12 chars for type column
            elif header.lower() == "resource types":
                # Give resource types column more space for multi-line content
                col_width = max(
                    col_width or 0, 25
                )  # Minimum 25 chars for resource types column
            elif header.lower() == "resource name":
                # Resource name column should have reasonable width
                col_width = max(
                    col_width or 0, 15
                )  # Minimum 15 chars for resource name column
            elif header.lower() == "labels":
                # Labels column should have enough space for key=value pairs
                col_width = max(
                    col_width or 0, 20
                )  # Minimum 20 chars for labels column

        rich_table.add_column(
            header_display,
            justify="left",
            overflow=overflow,
            no_wrap=no_wrap,
            min_width=6,  # Reduced minimum for better content adaptation
            max_width=col_width if col_width else None,
        )

    # Add data rows
    for i, row in enumerate(prepared_data):
        values = []
        for header in headers:
            value = row.get(header, "")
            # Convert to string and handle None values
            if value is None:
                value = ""
            else:
                value = str(value)

            # Apply colorization if enabled
            if not no_color:
                value = _colorize_value(header, value)

            values.append(value)

        rich_table.add_row(*values)

        # Add spacing row after each service connector row (except the last one)
        if is_service_connectors_table and i < len(prepared_data) - 1:
            # Add an empty row with a single space for spacing
            spacing_values = [" " for _ in headers]
            rich_table.add_row(*spacing_values)

    # Use console with appropriate width
    console_width = table_width if table_width else available_width
    table_console = Console(
        width=console_width,
        force_terminal=not no_color,
        no_color=no_color or os.getenv("NO_COLOR") is not None,
    )

    # Print with two spaces between columns (handled by Rich's padding)
    table_console.print(rich_table)


def _get_terminal_width() -> Optional[int]:
    """Get terminal width from environment or shutil.

    Returns:
        Terminal width in characters, or None if cannot be determined
    """
    # Check COLUMNS environment variable first
    columns_env = os.getenv("COLUMNS")
    if columns_env:
        try:
            return int(columns_env)
        except ValueError:
            pass

    # Fall back to shutil.get_terminal_size
    try:
        size = shutil.get_terminal_size()
        # Use a reasonable minimum width even if terminal reports smaller
        return max(size.columns, 100)
    except (AttributeError, OSError):
        # Default to a reasonable width if we can't detect terminal size
        return 120


def _colorize_value(column: str, value: str) -> str:
    """Apply colorization to values based on column type and content.

    Args:
        column: Column name to determine colorization rules
        value: Value to potentially colorize

    Returns:
        Potentially colorized value with Rich markup
    """
    # Status-like columns get color coding
    if any(
        keyword in column.lower() for keyword in ["status", "state", "health"]
    ):
        value_lower = value.lower()
        if value_lower in [
            "active",
            "healthy",
            "succeeded",
            "completed",
        ]:
            return f"[green]{value}[/green]"
        elif value_lower in [
            "running",
            "pending",
            "initializing",
            "starting",
            "warning",
        ]:
            return f"[yellow]{value}[/yellow]"
        elif value_lower in [
            "failed",
            "error",
            "unhealthy",
            "stopped",
            "crashed",
        ]:
            return f"[red]{value}[/red]"

    return value


def _calculate_content_width(
    data: List[Dict[str, Any]], headers: List[str]
) -> int:
    """Calculate the minimum width needed to display all content naturally.

    Args:
        data: List of data dictionaries
        headers: List of column headers

    Returns:
        Minimum table width needed for content
    """
    if not data or not headers:
        return 0

    total_width = 0

    for header in headers:
        # Header width
        header_width = len(header.upper())

        # Content width for this column
        max_content_width = 0
        for row in data:
            value = str(row.get(header, ""))
            # Remove Rich markup for width calculation
            clean_value = _strip_rich_markup(value)

            # Handle multi-line content - get the width of the longest line
            if "\n" in clean_value:
                lines = clean_value.split("\n")
                line_width = max(len(line) for line in lines) if lines else 0
                max_content_width = max(max_content_width, line_width)
            else:
                max_content_width = max(max_content_width, len(clean_value))

        # Column width is max of header and content, with reasonable limits
        col_width = max(header_width, max_content_width, 6)  # Min 6 chars
        col_width = min(col_width, 60)  # Max 60 chars per column
        total_width += col_width

    # Add padding between columns (2 spaces each, plus borders)
    padding = len(headers) * 2 + 2  # 2 spaces per column + table borders
    return total_width + padding


def _calculate_column_width(
    data: List[Dict[str, Any]],
    header: str,
    available_width: int,
    num_columns: int,
    no_truncate: bool,
) -> Optional[int]:
    """Calculate appropriate width for a specific column.

    Args:
        data: List of data dictionaries
        header: Column header name
        available_width: Available terminal width
        num_columns: Total number of columns
        no_truncate: Whether truncation is disabled

    Returns:
        Maximum column width, or None for auto-sizing
    """
    if no_truncate:
        return None  # Let Rich auto-size when no truncation

    if not data:
        return None

    # Calculate natural width needed for this column
    header_width = len(header.upper())
    max_content_width = 0

    for row in data:
        value = str(row.get(header, ""))
        clean_value = _strip_rich_markup(value)

        # Handle multi-line content - get the width of the longest line
        if "\n" in clean_value:
            lines = clean_value.split("\n")
            line_width = max(len(line) for line in lines) if lines else 0
            max_content_width = max(max_content_width, line_width)
        else:
            max_content_width = max(max_content_width, len(clean_value))

    natural_width = max(header_width, max_content_width, 6)

    # Calculate fair share of available width
    padding_per_col = 2  # 2 spaces between columns
    total_padding = num_columns * padding_per_col + 2  # + table borders
    available_for_content = available_width - total_padding
    fair_share = available_for_content // num_columns

    # Use natural width if it fits in fair share, otherwise limit to fair share
    return min(
        natural_width, max(fair_share, 8)
    )  # Min 8 chars even in tight spaces


def _strip_rich_markup(text: str) -> str:
    """Remove Rich markup tags from text for width calculation.

    Args:
        text: Text that may contain Rich markup

    Returns:
        Text with markup removed
    """
    import re

    # Remove Rich markup like [green]text[/green] or [bold]text[/bold]
    clean_text = re.sub(r"\[/?[^\]]*\]", "", text)
    return clean_text
