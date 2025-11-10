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

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateNotFound,
    Undefined,
)

from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import io_utils

logger = get_logger(__name__)


class KubernetesTemplateEngine:
    """Engine for generating Kubernetes resources from Jinja2 templates.

    Attributes:
        template_dirs: List of directories to search for templates.
        builtin_templates_dir: Path to ZenML's built-in templates.
        custom_templates_dir: Optional user-provided template directory.
        env: Jinja2 environment for rendering templates.
    """

    def __init__(
        self,
        custom_templates_dir: Optional[str] = None,
        strict_undefined: bool = True,
    ):
        """Initialize the template engine.

        Args:
            custom_templates_dir: Optional directory containing user's custom
                templates. If provided, these templates override built-in ones.
            strict_undefined: If True, raise an error for undefined template
                variables. If False, undefined variables are silently ignored.
        """
        self.builtin_templates_dir = (
            Path(__file__).parent / "templates" / "kubernetes"
        )
        template_dirs: List[str] = []
        self.custom_templates_dir = None

        if custom_templates_dir:
            resolved_path = self._resolve_template_path(
                str(custom_templates_dir)
            )
            template_dirs.append(resolved_path)
            self.custom_templates_dir = resolved_path

        template_dirs.append(str(self.builtin_templates_dir))

        self.template_dirs = template_dirs

        self.env = Environment(
            loader=FileSystemLoader(template_dirs),
            undefined=StrictUndefined if strict_undefined else Undefined,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    @staticmethod
    def _resolve_template_path(path: str) -> str:
        """Resolve and validate template directory path.

        Args:
            path: Path to resolve (can be remote or local).

        Returns:
            Resolved path if it exists.

        Raises:
            ValueError: If the path does not exist.
        """
        if io_utils.is_remote(path):
            resolved = io_utils.sanitize_remote_path(path)
        else:
            resolved = io_utils.resolve_relative_path(path)

        if fileio.exists(resolved):
            logger.info(f"Using custom Kubernetes templates from: {resolved}")
            return resolved
        else:
            raise ValueError(
                f"Custom template directory not found: {resolved}. "
                f"Please verify the path is correct and accessible."
            )

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
            ValueError: If the file cannot be loaded, parsed, or validated.
        """
        try:
            template = self.env.get_template(file)
        except TemplateNotFound as e:
            logger.info(f"Template not found: {file}: {e}")

            if io_utils.is_remote(file):
                file_str = io_utils.sanitize_remote_path(file)
            else:
                file_str = io_utils.resolve_relative_path(file)

            if not fileio.exists(file_str):
                raise ValueError(f"Resource file not found: {file}")

            yaml_content = io_utils.read_file_contents_as_string(file_str)

            if context:
                template = self.env.from_string(yaml_content)
                yaml_content = template.render(**context)

            try:
                yaml_docs = KubernetesTemplateEngine.load_yaml_documents(
                    yaml_content
                )
            except ValueError as e:
                raise ValueError(
                    f"Failed to parse YAML from {file}: {e}"
                ) from e

            resources: List[Dict[str, Any]] = []
            for index, doc in enumerate(yaml_docs):
                try:
                    resources.append(doc)
                except ValueError as e:
                    logger.warning(
                        f"Skipping invalid Kubernetes resource in {file} (doc {index}): {e}"
                    )

            if resources:
                logger.info(
                    f"Loaded {len(resources)} resource(s) from {Path(file).name}"
                )

            return resources

        except ValueError:
            raise
        except Exception as e:
            raise ValueError(
                f"Failed to load resource file '{file}': {e}"
            ) from e

    @staticmethod
    def load_yaml_documents(yaml_content: str) -> List[Dict[str, Any]]:
        """Load one or more YAML documents from a string.

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
            if not isinstance(document, dict):
                raise ValueError(
                    f"YAML document {index + 1} must be a dictionary, got {type(document).__name__}"
                )
            resources.append(document)

        if not resources:
            raise ValueError("YAML contains no valid documents")

        return resources
