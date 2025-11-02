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
from zenml.logger import get_logger
from zenml.utils import io_utils

logger = get_logger(__name__)


class RenderedKubernetesManifest(BaseModel):
    """Bundle containing various representations of a rendered manifest."""

    resource_dict: Dict[str, Any]
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
            resource_dict = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValueError(
                f"Failed to parse YAML from template {template_name}: {e}"
            ) from e

        if not isinstance(resource_dict, dict):
            raise ValueError(
                f"Invalid Kubernetes manifest in {template_name}: expected dict, got {type(resource_dict)}"
            )

        if "kind" not in resource_dict:
            raise ValueError(
                f"Invalid Kubernetes manifest: missing 'kind' field in {template_name}"
            )

        if "apiVersion" not in resource_dict:
            raise ValueError(
                f"Invalid Kubernetes manifest: missing 'apiVersion' field in {template_name}"
            )

        canonical_yaml = yaml.safe_dump(
            resource_dict,
            sort_keys=False,
        )

        return RenderedKubernetesManifest(
            resource_dict=resource_dict,
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

        # Use debug for individual file saves (verbose)
        logger.debug(f"💾 Saved manifest: {output_path}")
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
                uses project root '.zenml-deployments/' directory or temp directory as fallback.

        Returns:
            Path to the directory containing all saved manifests.
        """
        if output_dir:
            manifest_dir = (
                Path(output_dir).expanduser().resolve() / deployment_name
            )
        else:
            try:
                from zenml.client import Client
                from zenml.utils import source_utils

                # Try to get the project/repository root first
                repo_root = Client.find_repository()
                if repo_root:
                    # Use project root with .zenml-deployments directory
                    manifest_dir = (
                        repo_root / ".zenml-deployments" / deployment_name
                    )
                else:
                    # Fallback to source root if no repository found
                    source_root = source_utils.get_source_root()
                    manifest_dir = (
                        Path(source_root)
                        / ".zenml-deployments"
                        / deployment_name
                    )
            except Exception:
                manifest_dir = (
                    Path(tempfile.gettempdir()) / "zenml-k8s" / deployment_name
                )
                logger.warning(
                    "Could not determine project root. "
                    f"Saving manifests to temp directory: {manifest_dir}"
                )

        manifest_dir_str = str(manifest_dir)

        if not fileio.exists(manifest_dir_str):
            fileio.makedirs(manifest_dir_str)

        # Save all manifests
        for filename, content in manifests.items():
            output_path = manifest_dir / filename
            self.save_manifest(manifest=content, output_path=output_path)

        # Summary with better formatting
        logger.info(
            f"💾 Saved {len(manifests)} Kubernetes manifests\n"
            f"   └─ Location: {manifest_dir}"
        )
        return manifest_dir

    @staticmethod
    def load_additional_resources(
        resource_files: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Load additional resources from YAML files with Jinja2 templating.

        Args:
            resource_files: List of file paths to YAML files.
            context: Optional Jinja2 template context for variable substitution.

        Returns:
            List of resource dicts ready to apply.

        Raises:
            ValueError: If a file cannot be loaded or parsed, or if input validation fails.
        """
        from pathlib import Path

        if not isinstance(resource_files, list):
            raise ValueError(
                f"resource_files must be a list, got {type(resource_files)}"
            )

        loaded_resources = []

        for file_path in resource_files:
            if not isinstance(file_path, str):
                logger.warning(f"Skipping non-string file path: {file_path}")
                continue

            try:
                expanded_path = Path(file_path).expanduser().resolve()
                file_path_str = str(expanded_path)

                if not fileio.exists(file_path_str):
                    raise ValueError(
                        f"Additional resource file not found: {file_path}"
                    )

                yaml_content = io_utils.read_file_contents_as_string(
                    file_path_str
                )

                if context:
                    from jinja2 import Template

                    template = Template(yaml_content)
                    yaml_content = template.render(**context)

                yaml_docs = list(yaml.safe_load_all(yaml_content))

                valid_docs = []
                for doc in yaml_docs:
                    if doc and isinstance(doc, dict):
                        loaded_resources.append(doc)
                        valid_docs.append(doc)
                    elif doc:
                        logger.warning(
                            f"⚠️  Skipping invalid YAML document in {file_path}"
                        )

                if valid_docs:
                    logger.info(
                        f"📦 Loaded {len(valid_docs)} resource(s) from {Path(file_path).name}"
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
