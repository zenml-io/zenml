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

from zenml.integrations.kubernetes import kube_utils
from zenml.io import fileio
from zenml.io.filesystem import PathType
from zenml.logger import get_logger
from zenml.utils import io_utils, source_utils

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
            resolved_path = self._resolve_template_path(
                str(custom_templates_dir)
            )
            if resolved_path:
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

        self.env.filters["to_yaml"] = self._yaml_filter
        self.env.filters["to_json"] = self._json_filter
        self.env.filters["k8s_name"] = self._k8s_name_filter
        self.env.filters["k8s_label_value"] = self._k8s_label_value_filter

    @staticmethod
    def _resolve_template_path(path: str) -> Optional[str]:
        """Resolve and validate template directory path.

        Args:
            path: Path to resolve (can be remote or local).

        Returns:
            Resolved path if it exists, None otherwise.
        """
        if io_utils.is_remote(path):
            resolved = io_utils.sanitize_remote_path(path)
        else:
            resolved = io_utils.resolve_relative_path(path)

        if fileio.exists(resolved):
            logger.info("Using custom Kubernetes templates from: %s", resolved)
            return resolved
        else:
            logger.warning(
                "Custom template directory not found: %s, falling back to built-in templates",
                resolved,
            )
            return None

    @staticmethod
    def _validate_k8s_resource(
        resource: Dict[str, Any],
        source: str = "resource",
        index: Optional[int] = None,
    ) -> None:
        """Validate that a resource has required Kubernetes fields.

        Note: Basic validation only. The Kubernetes API server performs
        comprehensive validation including schema, required fields, and CRDs.

        Args:
            resource: The resource dictionary to validate.
            source: Description of the resource source for error messages.
            index: Optional document index for error messages.

        Raises:
            ValueError: If the resource is invalid.
        """
        if "kind" not in resource:
            raise ValueError(
                f"Invalid Kubernetes manifest: missing 'kind' field "
                f"in {source}"
                f"{' document ' + str(index + 1) if index is not None else ''}"
            )
        if "apiVersion" not in resource:
            raise ValueError(
                f"Invalid Kubernetes manifest: missing 'apiVersion' field "
                f"in {source}"
                f"{' document ' + str(index + 1) if index is not None else ''}"
            )

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

        Delegates to kube_utils.sanitize_label for consistent behavior.

        Kubernetes names must:
        - Start and end with alphanumeric characters
        - Contain only lowercase letters, numbers, and hyphens
        - Be at most 63 characters long

        Args:
            value: The string to sanitize.
            max_length: Maximum allowed length (default 63, K8s limit).

        Returns:
            Sanitized Kubernetes name.
        """
        sanitized = kube_utils.sanitize_label(value)

        if max_length != 63 and len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip("-")

        return sanitized or "unnamed"

    @staticmethod
    def _k8s_label_value_filter(value: str, max_length: int = 63) -> str:
        """Sanitize a string to be a valid Kubernetes label value.

        Unlike resource names, label values are case-sensitive and allow dots.
        See: https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#syntax-and-character-set

        Args:
            value: The string to sanitize.
            max_length: Maximum allowed length (default 63).

        Returns:
            Sanitized label value, or empty string if input is empty.
        """
        if not value:
            return ""

        # Replace invalid characters with dash
        label = re.sub(r"[^a-zA-Z0-9._-]", "-", value)

        # Remove invalid leading/trailing characters
        label = re.sub(r"^[^a-zA-Z0-9]+", "", label)
        label = re.sub(r"[^a-zA-Z0-9]+$", "", label)

        if len(label) > max_length:
            label = label[:max_length].rstrip("._-")

        return label

    @staticmethod
    def _determine_default_manifest_dir(deployment_name: str) -> str:
        """Determine the default local manifest directory for a deployment.

        Tries in order:
        1. ZenML repository root/.zenml-deployments/
        2. Source root/.zenml-deployments/
        3. Temp directory (with warning)

        Args:
            deployment_name: Name of the deployment.

        Returns:
            Local filesystem path to the default manifest directory.
        """
        from zenml.client import Client

        try:
            repo_root = Client.find_repository()
            if repo_root is not None:
                manifest_path = (
                    repo_root / ".zenml-deployments" / deployment_name
                )
                return str(manifest_path)
        except Exception as e:
            logger.debug("Could not use repository root for manifests: %s", e)

        try:
            source_root = source_utils.get_source_root()
            if source_root:
                manifest_path = (
                    Path(source_root) / ".zenml-deployments" / deployment_name
                )
                return str(manifest_path)
        except Exception as e:
            logger.debug("Could not use source root for manifests: %s", e)

        temp_base = os.path.join(tempfile.gettempdir(), "zenml-k8s")
        fallback_dir = os.path.join(temp_base, deployment_name)
        logger.warning(
            "Could not determine project root. Saving manifests to temporary directory: %s. "
            "These manifests may be lost on system restart. "
            "Consider running from a ZenML repository or specifying manifest_output_dir.",
            fallback_dir,
        )
        return fallback_dir

    def save_k8s_objects(
        self,
        k8s_objects: List[Any],
        deployment_name: str,
        output_dir: Optional[PathType] = None,
    ) -> List[str]:
        """Save validated Kubernetes API objects as clean YAML files.

        This method takes Kubernetes API objects returned from server validation
        (e.g., after dry-run or actual deployment) and saves them as clean,
        readable YAML files without internal Kubernetes metadata.

        Args:
            k8s_objects: List of Kubernetes API objects (with .to_dict() method).
            deployment_name: Name of the deployment (used for directory name).
            output_dir: Optional custom local directory. If not provided,
                uses project root '.zenml-deployments/' directory.

        Returns:
            List of file paths where YAML files were saved.

        Raises:
            ValueError: If a remote path is provided or objects cannot be serialized.
        """
        if output_dir is not None:
            output_dir_str = str(output_dir)
            if io_utils.is_remote(output_dir_str):
                raise ValueError(
                    f"Remote paths are not supported: {output_dir_str}"
                )
            base_dir = io_utils.resolve_relative_path(output_dir_str)
            manifest_dir = os.path.join(base_dir, deployment_name)
        else:
            manifest_dir = (
                KubernetesTemplateEngine._determine_default_manifest_dir(
                    deployment_name
                )
            )

        os.makedirs(manifest_dir, exist_ok=True)

        saved_files = []
        for idx, k8s_obj in enumerate(k8s_objects):
            if not hasattr(k8s_obj, "to_dict"):
                raise ValueError(
                    f"Object at index {idx} does not have a to_dict() method"
                )
            obj_dict = k8s_obj.to_dict()

            obj_dict = self._clean_k8s_resource_dict(obj_dict)

            kind = obj_dict.get("kind", "unknown").lower()
            name = obj_dict.get("metadata", {}).get("name", f"resource-{idx}")
            filename = f"{kind}-{name}.yaml"
            filepath = os.path.join(manifest_dir, filename)

            with open(filepath, "w") as f:
                yaml.dump(
                    obj_dict, f, default_flow_style=False, sort_keys=False
                )

            saved_files.append(filepath)

        logger.info(
            "Saved %s validated Kubernetes manifest(s) to %s",
            len(saved_files),
            manifest_dir,
        )
        return saved_files

    @staticmethod
    def _clean_k8s_resource_dict(obj_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Remove Kubernetes internal metadata for clean YAML output.

        Kubernetes API responses include server-managed fields that are not
        useful in saved manifests. This method removes those fields to keep
        only the user-relevant configuration.

        Args:
            obj_dict: Raw Kubernetes resource dictionary.

        Returns:
            Cleaned dictionary with only user-relevant fields.
        """
        obj_dict.pop("status", None)

        metadata = obj_dict.get("metadata", {})
        if metadata:
            for field in [
                "managedFields",
                "uid",
                "resourceVersion",
                "generation",
                "creationTimestamp",
                "selfLink",
            ]:
                metadata.pop(field, None)

            obj_dict["metadata"] = {
                k: v
                for k, v in metadata.items()
                if v not in (None, "", {}, [])
            }

        return obj_dict

    # ========================================================================
    # Template and Resource Rendering
    # ========================================================================

    def render_template(
        self,
        template_or_file: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Render a template or load YAML resources with optional templating.

        This method handles both:
        1. Jinja2 template files (*.j2) from configured template directories
        2. Plain YAML files from filesystem with optional variable substitution

        Args:
            template_or_file: Template name (e.g., "deployment.yaml.j2") or
                file path to a YAML file.
            context: Dictionary of variables to pass to the template.

        Returns:
            List of resource dictionaries ready to apply.

        Raises:
            ValueError: If the template/file is invalid or produces invalid YAML.
            TemplateNotFound: If a .j2 template cannot be found.
        """
        context = context or {}

        if template_or_file.endswith(".j2"):
            return self._render_jinja_template(template_or_file, context)
        else:
            return self._render_yaml_file(template_or_file, context)

    def _render_jinja_template(
        self,
        template_name: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Render a Jinja2 template from configured template directories.

        Args:
            template_name: Name of the template file (e.g., "deployment.yaml.j2").
            context: Dictionary of variables to pass to the template.

        Returns:
            List of resource dictionaries.

        Raises:
            TemplateNotFound: If the template cannot be found.
            ValueError: If the rendered output is invalid YAML.
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

        try:
            resources = KubernetesTemplateEngine.load_yaml_documents(rendered)
        except ValueError as e:
            raise ValueError(
                f"Failed to parse template {template_name}: {e}"
            ) from e

        return resources if isinstance(resources, list) else [resources]

    def _render_yaml_file(
        self,
        file_path: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Load and optionally template a YAML file from the filesystem.

        Args:
            file_path: Path to the YAML file (local or remote).
            context: Optional Jinja2 template context for variable substitution.

        Returns:
            List of resource dictionaries.

        Raises:
            ValueError: If the file cannot be loaded, parsed, or validated.
        """
        try:
            if io_utils.is_remote(file_path):
                file_path_str = io_utils.sanitize_remote_path(file_path)
            else:
                file_path_str = io_utils.resolve_relative_path(file_path)

            if not fileio.exists(file_path_str):
                raise ValueError(f"Resource file not found: {file_path}")

            yaml_content = io_utils.read_file_contents_as_string(file_path_str)

            if context:
                template = self.env.from_string(yaml_content)
                yaml_content = template.render(**context)

            try:
                yaml_docs = KubernetesTemplateEngine.load_yaml_documents(
                    yaml_content
                )
            except ValueError as e:
                raise ValueError(
                    f"Failed to parse YAML from {file_path}: {e}"
                ) from e

            resources: List[Dict[str, Any]] = []
            for index, doc in enumerate(yaml_docs):
                try:
                    self._validate_k8s_resource(doc, file_path, index)
                    resources.append(doc)
                except ValueError as e:
                    logger.warning(
                        "Skipping invalid Kubernetes resource in %s (doc %d): %s",
                        file_path,
                        index,
                        e,
                    )

            if resources:
                logger.info(
                    "Loaded %d resource(s) from %s",
                    len(resources),
                    Path(file_path).name,
                )

            return resources

        except ValueError:
            raise
        except Exception as e:
            raise ValueError(
                f"Failed to load resource file '{file_path}': {e}"
            ) from e

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
    def load_yaml_documents(yaml_content: str) -> List[Dict[str, Any]]:
        """Load one or more YAML documents from a string.

        Handles both single-document and multi-document YAML (with --- separators).

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

    @staticmethod
    def dump_yaml_documents(
        documents: List[Dict[str, Any]],
        sort_keys: bool = False,
    ) -> str:
        """Serialize multiple YAML documents into a single YAML string.

        Args:
            documents: YAML document payloads (dicts or lists) to serialize.
            sort_keys: Whether to sort dictionary keys when dumping each document.

        Returns:
            A YAML string containing all documents separated by YAML document markers.
        """
        serialized_documents = []
        for document in documents:
            serialized = yaml.safe_dump(
                document,
                sort_keys=sort_keys,
                default_flow_style=False,
            ).rstrip()
            serialized_documents.append(serialized)
        return "\n---\n".join(serialized_documents)
