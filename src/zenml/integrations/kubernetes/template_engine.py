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
"""Kubernetes template engine."""

import json
from typing import Any, Dict, List

import yaml
from jinja2 import (
    Environment,
    StrictUndefined,
    TemplateError,
    Undefined,
    select_autoescape,
)

from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import io_utils

logger = get_logger(__name__)


def _to_yaml_filter(obj: Any) -> str:
    """Convert Python object to YAML string.

    Args:
        obj: Python object to convert.

    Returns:
        YAML string representation.
    """
    return yaml.safe_dump(
        obj, default_flow_style=False, allow_unicode=True
    ).rstrip()


def _to_json_filter(obj: Any) -> str:
    """Convert Python object to JSON string.

    Args:
        obj: Python object to convert.

    Returns:
        JSON string representation.
    """
    return json.dumps(obj)


class KubernetesTemplateEngine:
    """Engine for generating Kubernetes resources from Jinja2 templates.

    Attributes:
        env: Jinja2 environment for rendering templates.
    """

    def __init__(
        self,
        strict_undefined: bool = True,
    ):
        """Initialize the template engine.

        Args:
            strict_undefined: If True, raise an error for undefined template
                variables. If False, undefined variables are silently ignored.
        """
        # autoescape must be disabled for YAML manifests rendered from plain
        # strings because select_autoescape defaults to escaping string-based
        # templates as HTML. That would turn `"foo"` into `&#34;foo&#34;`, making
        # the rendered YAML invalid.
        self.env = Environment(
            undefined=StrictUndefined if strict_undefined else Undefined,
            autoescape=select_autoescape(
                enabled_extensions=("html", "htm", "xml"),
                default=False,
                default_for_string=False,
            ),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        self.env.filters["to_yaml"] = _to_yaml_filter
        self.env.filters["tojson"] = _to_json_filter

    # ========================================================================
    # Template and Resource Rendering
    # ========================================================================

    def render_template(
        self,
        file: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Render a YAML file with optional Jinja2 template context.

        Args:
            file: Path to the YAML file (local or remote).
            context: Optional Jinja2 template context for variable substitution.

        Returns:
            List of resource dictionaries.

        Raises:
            FileNotFoundError: If the template file doesn't exist.
            ValueError: If template rendering or YAML parsing fails.
        """
        if io_utils.is_remote(file):
            file_path = io_utils.sanitize_remote_path(file)
        else:
            file_path = io_utils.resolve_relative_path(file)

        if not fileio.exists(file_path):
            raise FileNotFoundError(f"Template file not found: {file}")

        file_contents = io_utils.read_file_contents_as_string(file_path)

        try:
            template = self.env.from_string(file_contents)
            yaml_content = template.render(**context)
        except TemplateError as e:
            raise ValueError(
                f"Failed to render Jinja2 template '{file}': {e}"
            ) from e

        return self.load_yaml_documents(yaml_content)

    @staticmethod
    def load_yaml_documents(yaml_content: str) -> List[Dict[str, Any]]:
        """Load one or more YAML documents from a string.

        Supports two common Kubernetes YAML patterns:
        1. Multiple documents separated by `---`:
           ```yaml
           ---
           apiVersion: v1
           kind: ConfigMap
           ---
           apiVersion: apps/v1
           kind: Deployment
           ```
        2. Top-level list of resources:
           ```yaml
           - apiVersion: v1
             kind: ConfigMap
           - apiVersion: apps/v1
             kind: Deployment
           ```

        Args:
            yaml_content: YAML string potentially containing multiple documents.

        Returns:
            List of resource dictionaries (skips None documents).

        Raises:
            ValueError: If YAML is invalid or contains non-dict documents.
        """
        try:
            documents = list(yaml.safe_load_all(yaml_content))
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}") from e

        resources: List[Dict[str, Any]] = []
        for index, document in enumerate(documents):
            if document is None:
                continue
            if isinstance(document, list):
                for item_index, item in enumerate(document):
                    if item is None:
                        continue
                    if not isinstance(item, dict):
                        raise ValueError(
                            f"YAML document {index + 1}, item {item_index + 1} "
                            f"must be a dictionary, got {type(item).__name__}"
                        )
                    resources.append(item)
            elif isinstance(document, dict):
                resources.append(document)
            else:
                raise ValueError(
                    f"YAML document {index + 1} must be a dictionary or list, "
                    f"got {type(document).__name__}"
                )

        return resources
