"""Unit tests for KubernetesTemplateEngine."""

from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from zenml.integrations.kubernetes.template_engine import (
    KubernetesTemplateEngine,
)


class TestInitialization:
    """Test engine initialization."""

    def test_init_default(self):
        """Test default initialization."""
        engine = KubernetesTemplateEngine()
        assert engine.env is not None
        assert engine.custom_templates_dir is None

    def test_init_with_custom_dir(self, tmp_path: Path):
        """Test initialization with custom template directory."""
        engine = KubernetesTemplateEngine(custom_templates_dir=str(tmp_path))
        assert engine.custom_templates_dir == str(tmp_path)

    def test_init_nonexistent_dir_warns(self, caplog):
        """Test that nonexistent custom directory logs warning."""
        engine = KubernetesTemplateEngine(custom_templates_dir="/nonexistent")
        assert engine.custom_templates_dir is None
        assert "not found" in caplog.text.lower()


class TestTemplateRendering:
    """Test template rendering."""

    def test_render_deployment_template(self, sample_template_context):
        """Test rendering deployment template with full context."""
        engine = KubernetesTemplateEngine()

        resources = engine.render_template(
            "deployment.yaml.j2", sample_template_context
        )

        assert len(resources) == 1
        dep = resources[0]
        assert dep["kind"] == "Deployment"
        assert dep["apiVersion"] == "apps/v1"
        assert "name" in dep["metadata"]

    def test_render_nonexistent_template(self):
        """Test rendering nonexistent template raises error."""
        engine = KubernetesTemplateEngine()

        with pytest.raises(Exception):
            engine.render_template("nonexistent.yaml.j2", {})


class TestValidation:
    """Test resource validation."""

    def test_validate_valid_resource(self):
        """Test validation accepts valid resources."""
        engine = KubernetesTemplateEngine()
        resource = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "test"},
        }
        engine._validate_k8s_resource(resource)

    def test_validate_missing_kind(self):
        """Test validation rejects missing kind."""
        engine = KubernetesTemplateEngine()
        resource = {"apiVersion": "v1"}

        with pytest.raises(ValueError, match="kind"):
            engine._validate_k8s_resource(resource)

    def test_validate_missing_api_version(self):
        """Test validation rejects missing apiVersion."""
        engine = KubernetesTemplateEngine()
        resource = {"kind": "ConfigMap"}

        with pytest.raises(ValueError, match="apiVersion"):
            engine._validate_k8s_resource(resource)


class TestManifestSaving:
    """Test manifest persistence."""

    def test_save_k8s_objects(self, tmp_path: Path):
        """Test saving Kubernetes objects to files."""
        engine = KubernetesTemplateEngine()

        mock_obj = Mock()
        mock_obj.to_dict = Mock(
            return_value={
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {"name": "test", "namespace": "default"},
                "data": {"key": "value"},
            }
        )

        saved_files = engine.save_k8s_objects([mock_obj], str(tmp_path))

        assert len(saved_files) == 1
        assert Path(saved_files[0]).exists()

        with open(saved_files[0]) as f:
            loaded = yaml.safe_load(f)
            assert loaded["kind"] == "ConfigMap"

    def test_save_strips_internal_metadata(self, tmp_path: Path):
        """Test that internal metadata is stripped when saving."""
        engine = KubernetesTemplateEngine()

        mock_obj = Mock()
        mock_obj.to_dict = Mock(
            return_value={
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": "test",
                    "uid": "should-be-removed",
                    "resourceVersion": "should-be-removed",
                },
            }
        )

        saved_files = engine.save_k8s_objects([mock_obj], str(tmp_path))

        with open(saved_files[0]) as f:
            loaded = yaml.safe_load(f)
            assert "uid" not in loaded["metadata"]
            assert "resourceVersion" not in loaded["metadata"]
