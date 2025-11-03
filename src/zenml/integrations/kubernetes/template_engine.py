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
import os
import re
import tempfile
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
from pydantic import BaseModel, ConfigDict

from zenml.io import fileio
from zenml.io.filesystem import PathType
from zenml.logger import get_logger
from zenml.utils import io_utils, source_utils, yaml_utils

logger = get_logger(__name__)


class RenderedKubernetesManifest(BaseModel):
    """Bundle containing various representations of rendered manifest resources."""

    resources: List[Dict[str, Any]]
    template_yaml: str
    canonical_yaml: str

    model_config = ConfigDict(arbitrary_types_allowed=True)


class KubernetesTemplateEngine:
    """Engine for generating Kubernetes resources from Jinja2 templates.

    This class implements the industry-standard approach (like Helm/Kustomize):
    1. Load Jinja2 templates (built-in or user-provided)
    2. Render templates with context from Pydantic settings
    3. Parse rendered YAML to dictionaries
    4. Return both dicts (for API) and YAML (for inspection)
    5. NO kubectl required - uses pure Python!

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
            custom_templates_path = str(custom_templates_dir)
            if io_utils.is_remote(custom_templates_path):
                sanitized_custom_path = io_utils.sanitize_remote_path(
                    custom_templates_path
                )
                if fileio.exists(sanitized_custom_path):
                    template_dirs.append(sanitized_custom_path)
                    self.custom_templates_dir = sanitized_custom_path
                    logger.info(
                        "Using custom Kubernetes templates from: %s",
                        sanitized_custom_path,
                    )
                else:
                    logger.warning(
                        "Custom template directory not found: %s, falling back to built-in templates",
                        sanitized_custom_path,
                    )
            else:
                resolved_custom_path = io_utils.resolve_relative_path(
                    custom_templates_path
                )
                if fileio.exists(resolved_custom_path):
                    template_dirs.append(resolved_custom_path)
                    self.custom_templates_dir = resolved_custom_path
                    logger.info(
                        "Using custom Kubernetes templates from: %s",
                        resolved_custom_path,
                    )
                else:
                    logger.warning(
                        "Custom template directory not found: %s, falling back to built-in templates",
                        resolved_custom_path,
                    )

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

        self.env.filters["to_yaml"] = self._yaml_filter
        self.env.filters["to_json"] = self._json_filter
        self.env.filters["k8s_name"] = self._k8s_name_filter
        self.env.filters["k8s_label_value"] = self._k8s_label_value_filter

    @staticmethod
    def _yaml_filter(value: Any, indent: int = 2) -> str:
        """Convert Python object to YAML string.

        Args:
            value: The value to convert.
            indent: Indentation level.

        Returns:
            YAML string representation.
        """
        return yaml.safe_dump(
            value,
            default_flow_style=False,
            sort_keys=False,
            indent=indent,
        ).rstrip()

    @staticmethod
    def _json_filter(value: Any) -> str:
        """Convert Python object to JSON string.

        Args:
            value: The value to convert.

        Returns:
            JSON string representation.
        """
        return json.dumps(value, sort_keys=False, indent=2)

    @staticmethod
    def _k8s_name_filter(value: str, max_length: int = 63) -> str:
        """Sanitize a string to be a valid Kubernetes resource name.

        Kubernetes names must:
        - Start and end with alphanumeric characters
        - Contain only lowercase letters, numbers, and hyphens
        - Be at most 63 characters long

        Args:
            value: The string to sanitize.
            max_length: Maximum allowed length.

        Returns:
            Sanitized Kubernetes name.
        """
        # Convert to lowercase
        name = value.lower()

        # Replace invalid characters with hyphens
        name = re.sub(r"[^a-z0-9-]", "-", name)

        # Remove leading/trailing hyphens
        name = name.strip("-")

        # Ensure it starts with alphanumeric
        name = re.sub(r"^[^a-z0-9]+", "", name)

        # Truncate to max length
        if len(name) > max_length:
            name = name[:max_length].rstrip("-")

        return name or "unnamed"

    @staticmethod
    def _k8s_label_value_filter(value: str, max_length: int = 63) -> str:
        """Sanitize a string to be a valid Kubernetes label value.

        Args:
            value: The string to sanitize.
            max_length: Maximum allowed length.

        Returns:
            Sanitized label value.
        """
        # Label values can be empty
        if not value:
            return ""

        # Replace invalid characters
        label = re.sub(r"[^a-zA-Z0-9._-]", "-", value)

        # Remove leading/trailing special chars
        label = re.sub(r"^[^a-zA-Z0-9]+", "", label)
        label = re.sub(r"[^a-zA-Z0-9]+$", "", label)

        # Truncate to max length
        if len(label) > max_length:
            label = label[:max_length].rstrip("._-")

        return label

    def render_to_k8s_object(
        self,
        template_name: str,
        context: Dict[str, Any],
    ) -> RenderedKubernetesManifest:
        """Render a template and return the manifest bundle.

        Args:
            template_name: Name of the template file (e.g., "deployment.yaml.j2").
            context: Dictionary of variables to pass to the template.

        Returns:
            RenderedKubernetesManifest containing the resource dict, the
            original template YAML, and a canonical YAML string.

        Raises:
            ValueError: If rendered output is invalid YAML or kind is missing.
        """
        yaml_content = self.render_template(
            template_name=template_name, context=context
        )

        try:
            documents = list(yaml.safe_load_all(yaml_content))
        except yaml.YAMLError as e:
            raise ValueError(
                f"Failed to parse YAML from template {template_name}: {e}"
            ) from e

        resources: List[Dict[str, Any]] = []
        for index, document in enumerate(documents):
            if document is None:
                continue
            if not isinstance(document, dict):
                raise ValueError(
                    f"Invalid Kubernetes manifest in {template_name}: "
                    f"document {index + 1} is of type {type(document)}; expected dict."
                )
            if "kind" not in document:
                raise ValueError(
                    f"Invalid Kubernetes manifest: missing 'kind' field "
                    f"in document {index + 1} of {template_name}"
                )
            if "apiVersion" not in document:
                raise ValueError(
                    f"Invalid Kubernetes manifest: missing 'apiVersion' field "
                    f"in document {index + 1} of {template_name}"
                )
            resources.append(document)

        if not resources:
            raise ValueError(
                f"No valid Kubernetes resources found in template {template_name}."
            )

        canonical_yaml = yaml_utils.dump_yaml_documents(
            resources,
            sort_keys=False,
        )

        return RenderedKubernetesManifest(
            resources=resources,
            template_yaml=yaml_content,
            canonical_yaml=canonical_yaml,
        )

    def render_template(
        self,
        template_name: str,
        context: Dict[str, Any],
        validate_yaml: bool = True,
    ) -> str:
        """Render a Jinja2 template with the given context.

        Args:
            template_name: Name of the template file (e.g., "deployment.yaml.j2").
            context: Dictionary of variables to pass to the template.
            validate_yaml: If True, validate that the rendered output is valid YAML.

        Returns:
            Rendered template as a string.

        Raises:
            TemplateNotFound: If the template file doesn't exist.
            ValueError: If validate_yaml is True and output is invalid.
        """
        try:
            template = self.env.get_template(template_name)
        except TemplateNotFound as e:
            available_templates = self.list_available_templates()
            raise TemplateNotFound(
                f"Template '{template_name}' not found. "
                f"Available templates: {available_templates}"
            ) from e

        rendered = template.render(**context)

        if validate_yaml:
            try:
                list(yaml.safe_load_all(rendered))
            except yaml.YAMLError as e:
                logger.error(
                    "Invalid YAML generated from template '%s':\n%s",
                    template_name,
                    rendered,
                )
                raise yaml.YAMLError(
                    f"Template '{template_name}' generated invalid YAML: {e}"
                ) from e

        return rendered

    def list_available_templates(self) -> List[str]:
        """List all available template files.

        Returns:
            List of template filenames.
        """
        templates = set()
        for template_dir in self.template_dirs:
            template_path = Path(template_dir)
            if template_path.exists():
                for template_file in template_path.rglob("*.j2"):
                    rel_path = template_file.relative_to(template_path)
                    templates.add(str(rel_path))
        return sorted(templates)

    @staticmethod
    def _join_path(base: str, *parts: str) -> str:
        """Join path segments while preserving remote URI schemes.

        Args:
            base: The base path.
            *parts: The path segments to join.

        Returns:
            The joined path.
        """
        segments = [segment for segment in parts if segment]
        if io_utils.is_remote(base):
            sanitized_base = io_utils.sanitize_remote_path(base).rstrip("/")
            sanitized_segments = []
            for segment in segments:
                if io_utils.is_remote(segment):
                    sanitized_segments.append(
                        io_utils.sanitize_remote_path(segment).strip("/")
                    )
                else:
                    sanitized_segments.append(
                        segment.replace("\\", "/").strip("/")
                    )
            components = [sanitized_base] + [
                segment for segment in sanitized_segments if segment
            ]
            return "/".join(components) if components else sanitized_base
        return os.path.join(base, *segments)

    def _determine_default_manifest_dir(self, deployment_name: str) -> str:
        """Determine the default manifest directory for a deployment.

        Args:
            deployment_name: Name of the deployment.

        Returns:
            Path to the default manifest directory.
        """
        from zenml.client import Client

        if Client is not None:
            try:
                repo_root = Client.find_repository()
                if repo_root:
                    return self._join_path(
                        str(repo_root),
                        ".zenml-deployments",
                        deployment_name,
                    )
            except Exception:
                logger.debug(
                    "Unable to determine repository root for manifest directory.",
                    exc_info=True,
                )

        if source_utils is not None:
            try:
                source_root = source_utils.get_source_root()
                if source_root:
                    return self._join_path(
                        str(source_root),
                        ".zenml-deployments",
                        deployment_name,
                    )
            except Exception:
                logger.debug(
                    "Unable to determine source root for manifest directory.",
                    exc_info=True,
                )

        temp_base = os.path.join(tempfile.gettempdir(), "zenml-k8s")
        fallback_dir = self._join_path(temp_base, deployment_name)
        logger.warning(
            "Could not determine project root. Saving manifests to temporary directory: %s",
            fallback_dir,
        )
        return fallback_dir

    def save_manifest(
        self,
        manifest: str,
        output_path: PathType,
    ) -> str:
        """Save a rendered manifest to disk.

        Args:
            manifest: The rendered YAML manifest.
            output_path: Full path where the manifest should be saved.

        Returns:
            Path to the saved file as a string.
        """
        output_path_str = str(output_path)
        if io_utils.is_remote(output_path_str):
            output_path_str = io_utils.sanitize_remote_path(output_path_str)

        parent_dir = os.path.dirname(output_path_str)
        if parent_dir:
            io_utils.create_dir_recursive_if_not_exists(parent_dir)

        io_utils.write_file_contents_as_string(
            file_path=output_path_str,
            content=manifest,
        )

        logger.debug("Saved manifest to %s", output_path_str)
        return output_path_str

    def save_manifests(
        self,
        manifests: Dict[str, str],
        deployment_name: str,
        output_dir: Optional[PathType] = None,
    ) -> str:
        """Save multiple rendered manifests to disk.

        Args:
            manifests: Dictionary mapping filename to YAML content.
            deployment_name: Name of the deployment (used for directory name).
            output_dir: Optional custom output directory. If not provided,
                uses project root '.zenml-deployments/' directory or temp directory as fallback.

        Returns:
            Path string to the directory containing all saved manifests.
        """
        if output_dir is not None:
            output_dir_str = str(output_dir)
            if io_utils.is_remote(output_dir_str):
                base_dir = io_utils.sanitize_remote_path(output_dir_str)
            else:
                base_dir = io_utils.resolve_relative_path(output_dir_str)
            manifest_dir = self._join_path(base_dir, deployment_name)
        else:
            manifest_dir = self._determine_default_manifest_dir(
                deployment_name
            )

        io_utils.create_dir_recursive_if_not_exists(manifest_dir)

        for filename, content in manifests.items():
            destination_path = self._join_path(manifest_dir, filename)
            self.save_manifest(manifest=content, output_path=destination_path)

        logger.info(
            "Saved %s Kubernetes manifest(s) to %s",
            len(manifests),
            manifest_dir,
        )
        return manifest_dir

    def load_additional_resources(
        self,
        resource_files: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Load additional resources from YAML files with optional templating.

        Args:
            resource_files: List of file paths to YAML files.
            context: Optional Jinja2 template context for variable substitution.

        Returns:
            List of resource dicts ready to apply.

        Raises:
            ValueError: If a file cannot be loaded or parsed, or if input validation fails.
        """
        loaded_resources: List[Dict[str, Any]] = []

        for file_path in resource_files:
            if not isinstance(file_path, str):
                logger.warning("Skipping non-string file path: %s", file_path)
                continue

            try:
                if io_utils.is_remote(file_path):
                    file_path_str = io_utils.sanitize_remote_path(file_path)
                else:
                    file_path_str = io_utils.resolve_relative_path(file_path)

                if not fileio.exists(file_path_str):
                    raise ValueError(
                        f"Additional resource file not found: {file_path}"
                    )

                yaml_content = io_utils.read_file_contents_as_string(
                    file_path_str
                )

                if context:
                    template = self.env.from_string(yaml_content)
                    yaml_content = template.render(**context)

                yaml_docs = list(yaml.safe_load_all(yaml_content))

                valid_docs: List[Dict[str, Any]] = []
                for doc in yaml_docs:
                    if doc is None:
                        continue
                    if isinstance(doc, dict):
                        loaded_resources.append(doc)
                        valid_docs.append(doc)
                    else:
                        logger.warning(
                            "Skipping invalid YAML document in %s", file_path
                        )

                if valid_docs:
                    logger.info(
                        "Loaded %s resource(s) from %s",
                        len(valid_docs),
                        Path(file_path).name,
                    )

            except yaml.YAMLError as e:
                raise ValueError(
                    f"Failed to parse YAML file '{file_path}': {e}"
                ) from e
            except Exception as e:
                raise ValueError(
                    f"Failed to load additional resource file '{file_path}': {e}"
                ) from e

        return loaded_resources
