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

import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    Template,
    TemplateNotFound,
    Undefined,
)
from kubernetes import client as k8s_client
from pydantic import BaseModel, ConfigDict

from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import io_utils

logger = get_logger(__name__)


class _FakeHTTPResponse:
    """Fake HTTP response for K8s API client deserializer.

    The Kubernetes Python client's deserializer expects an HTTP response object.
    This class provides a minimal fake response to deserialize YAML strings.

    IMPORTANT: This is a workaround for the K8s client deserializer. The K8s
    client deserializer expects an HTTP response but we're deserializing from
    a string. This approach is commonly used by Helm, Kluctl, and other K8s
    tools. If this breaks in future K8s client versions, consider using:
    kubernetes.utils.create_from_yaml()
    """

    def __init__(self, data: str):
        """Initialize with YAML data.

        Args:
            data: YAML string to deserialize.
        """
        self.data = data
        # Add commonly checked attributes for robustness
        self.status = 200
        self.reason = "OK"

    def read(self) -> bytes:
        """Read method that may be called by some deserializers.

        Returns:
            The data as bytes.
        """
        return (
            self.data.encode("utf-8")
            if isinstance(self.data, str)
            else self.data
        )


class RenderedKubernetesManifest(BaseModel):
    """Bundle containing various representations of a rendered manifest."""

    k8s_object: Any
    template_yaml: str
    canonical_yaml: str

    model_config = ConfigDict(arbitrary_types_allowed=True)


class KubernetesTemplateEngine:
    """Engine for generating Kubernetes resources from Jinja2 templates.

    This class implements the industry-standard approach (like Helm/Kluctl):
    1. Load Jinja2 templates (built-in or user-provided)
    2. Render templates with context from Pydantic settings
    3. Convert rendered YAML to K8s Python objects via deserializer
    4. Return both K8s objects (for API) and YAML (for inspection)
    5. NO kubectl required - uses pure Python!

    Attributes:
        template_dirs: List of directories to search for templates.
        builtin_templates_dir: Path to ZenML's built-in templates.
        custom_templates_dir: Optional user-provided template directory.
        env: Jinja2 environment for rendering templates.
        api_client: Kubernetes API client for deserialization.
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
            custom_path = Path(custom_templates_dir).expanduser().resolve()
            if custom_path.exists():
                template_dirs.append(str(custom_path))
                self.custom_templates_dir = str(custom_path)
                logger.info(
                    f"Using custom Kubernetes templates from: {custom_path}"
                )
            else:
                logger.warning(
                    f"Custom template directory not found: {custom_path}, "
                    "falling back to built-in templates"
                )

        template_dirs.append(str(self.builtin_templates_dir))

        self.template_dirs = template_dirs

        self.env = Environment(
            loader=FileSystemLoader(template_dirs),
            undefined=StrictUndefined if strict_undefined else Undefined,
            autoescape=False,  # Don't HTML-escape YAML content
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        self.env.filters["to_yaml"] = self._yaml_filter
        self.env.filters["to_json"] = self._json_filter
        self.env.filters["k8s_name"] = self._k8s_name_filter
        self.env.filters["k8s_label_value"] = self._k8s_label_value_filter

        self.api_client = k8s_client.ApiClient()

    @staticmethod
    def _yaml_filter(value: Any, indent: int = 2) -> str:
        """Convert Python object to YAML string.

        Args:
            value: The value to convert.
            indent: Indentation level.

        Returns:
            YAML string representation.
        """
        return yaml.dump(
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
        import json

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
        import re

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
        import re

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

    @lru_cache(maxsize=32)
    def _get_template_cached(self, template_name: str) -> Template:
        """Get a template with LRU caching for performance.

        Args:
            template_name: Name of the template file.

        Returns:
            The loaded Jinja2 template.

        Raises:
            TemplateNotFound: If template doesn't exist.
        """
        return self.env.get_template(template_name)

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
            RenderedKubernetesManifest containing the Kubernetes object, the
            original template YAML, and a canonical YAML string generated from
            the object (which mirrors what the Python client applies).

        Raises:
            TemplateNotFound: If the template file doesn't exist.
            yaml.YAMLError: If rendered output is invalid YAML.
            ValueError: If deserialization fails or kind is missing.
        """
        yaml_content = self.render_template(
            template_name=template_name, context=context
        )

        try:
            parsed = yaml.safe_load(yaml_content)
            if not isinstance(parsed, dict) or "kind" not in parsed:
                raise ValueError(
                    f"Invalid Kubernetes manifest: missing 'kind' field in {template_name}"
                )
            kind = parsed["kind"]
        except yaml.YAMLError as e:
            raise ValueError(
                f"Failed to parse YAML from template {template_name}: {e}"
            ) from e

        api_version = parsed.get("apiVersion", "")

        if not api_version:
            version_prefix = "V1"
        elif "/" in api_version:
            parts = api_version.split("/")
            if len(parts) != 2:
                raise ValueError(
                    f"Invalid API version format '{api_version}': "
                    "expected 'group/version' or 'version'"
                )
            group, version = parts
            if not version.startswith("v"):
                raise ValueError(
                    f"Invalid API version '{version}' in '{api_version}': "
                    "version must start with 'v' (e.g., 'v1', 'v2')"
                )
            version_prefix = version.upper()
        else:
            version = api_version
            if not version.startswith("v"):
                raise ValueError(
                    f"Invalid API version '{api_version}': "
                    "version must start with 'v' (e.g., 'v1', 'v1beta1')"
                )
            version_prefix = version.upper()

        k8s_object_type = f"{version_prefix}{kind}"

        try:
            k8s_object = self.api_client.deserialize(
                response=_FakeHTTPResponse(data=yaml_content),
                response_type=k8s_object_type,
            )
        except Exception as e:
            logger.error(
                f"Failed to deserialize YAML to {k8s_object_type}:\n{yaml_content}"
            )
            raise ValueError(
                f"Failed to convert template to K8s object: {e}"
            ) from e

        # Canonical representation produced by the client (what gets applied)
        if hasattr(k8s_object, "to_dict"):
            canonical_dict = k8s_object.to_dict()
        else:
            canonical_dict = self.api_client.sanitize_for_serialization(
                k8s_object
            )
        canonical_yaml = yaml.safe_dump(
            canonical_dict,
            sort_keys=False,
        )

        return RenderedKubernetesManifest(
            k8s_object=k8s_object,
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
            yaml.YAMLError: If validate_yaml is True and output is invalid.
        """
        try:
            template = self._get_template_cached(template_name)
        except TemplateNotFound as e:
            available_templates = self.list_available_templates()
            raise TemplateNotFound(
                f"Template '{template_name}' not found. "
                f"Available templates: {available_templates}"
            ) from e

        rendered = template.render(**context)

        if validate_yaml:
            try:
                yaml.safe_load(rendered)
            except yaml.YAMLError as e:
                logger.error(
                    f"Invalid YAML generated from template:\n{rendered}"
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

    def save_manifest(
        self,
        manifest: str,
        output_path: Path,
    ) -> Path:
        """Save a rendered manifest to disk.

        Args:
            manifest: The rendered YAML manifest.
            output_path: Full path where the manifest should be saved.

        Returns:
            Path to the saved file.
        """
        output_path_str = str(output_path)
        parent_dir = str(output_path.parent)

        if not fileio.exists(parent_dir):
            fileio.makedirs(parent_dir)

        io_utils.write_file_contents_as_string(
            file_path=output_path_str,
            content=manifest,
        )

        logger.info(f"Saved Kubernetes manifest to: {output_path}")
        return output_path

    def save_manifests(
        self,
        manifests: Dict[str, str],
        deployment_name: str,
        output_dir: Optional[str] = None,
    ) -> Path:
        """Save multiple rendered manifests to disk.

        Args:
            manifests: Dictionary mapping filename to YAML content.
            deployment_name: Name of the deployment (used for directory name).
            output_dir: Optional custom output directory. If not provided,
                uses the ZenML global config directory or temp directory as fallback.

        Returns:
            Path to the directory containing all saved manifests.
        """
        from zenml.client import Client

        if output_dir:
            manifest_dir = (
                Path(output_dir).expanduser().resolve() / deployment_name
            )
        else:
            try:
                client = Client()
                config_dir = client.config_directory
                if config_dir:
                    manifest_dir = (
                        Path(config_dir)
                        / "kubernetes"
                        / "manifests"
                        / deployment_name
                    )
                else:
                    manifest_dir = (
                        Path.home()
                        / ".config"
                        / "zenml"
                        / "kubernetes"
                        / "manifests"
                        / deployment_name
                    )
            except Exception:
                manifest_dir = (
                    Path(tempfile.gettempdir()) / "zenml-k8s" / deployment_name
                )
                logger.warning(
                    "Could not access ZenML config directory. "
                    f"Saving manifests to temp directory: {manifest_dir}"
                )

        manifest_dir_str = str(manifest_dir)

        if not fileio.exists(manifest_dir_str):
            fileio.makedirs(manifest_dir_str)
        for filename, content in manifests.items():
            output_path = manifest_dir / filename
            self.save_manifest(manifest=content, output_path=output_path)

        logger.info(
            f"Saved {len(manifests)} Kubernetes manifests to: {manifest_dir}"
        )
        return manifest_dir


def create_manifest_directory(base_dir: Optional[str] = None) -> Path:
    """Create a directory for storing manifests.

    Args:
        base_dir: Base directory for creating the manifest dir.
            If None, uses system temp directory.

    Returns:
        Path to the created directory.
    """
    if base_dir:
        base_path = Path(base_dir)
        base_path.mkdir(parents=True, exist_ok=True)
        manifest_dir = base_path / f"zenml-k8s-manifests-{os.getpid()}"
        manifest_dir.mkdir(exist_ok=True)
    else:
        manifest_dir = Path(tempfile.mkdtemp(prefix="zenml-k8s-manifests-"))

    logger.info(f"Created manifest directory: {manifest_dir}")
    return manifest_dir
