import json
from pathlib import Path

import pytest
import yaml
from jinja2 import TemplateNotFound

from zenml.integrations.kubernetes.template_engine import (
    KubernetesTemplateEngine,
)


@pytest.fixture
def custom_template_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "templates"
    directory.mkdir()
    return directory


def test_render_template_prefers_custom_directory(
    custom_template_dir: Path,
) -> None:
    template_path = custom_template_dir / "configmap.yaml.j2"
    template_path.write_text(
        "apiVersion: v1\n"
        "kind: ConfigMap\n"
        "metadata:\n  name: {{ name }}\n"
        "data:\n  value: {{ value }}\n"
    )

    engine = KubernetesTemplateEngine(
        custom_templates_dir=str(custom_template_dir)
    )
    rendered = engine.render_template(
        "configmap.yaml.j2", {"name": "demo", "value": "42"}
    )

    assert "demo" in rendered
    assert "42" in rendered


def test_render_template_raises_for_missing_template(
    custom_template_dir: Path,
) -> None:
    engine = KubernetesTemplateEngine(
        custom_templates_dir=str(custom_template_dir)
    )

    with pytest.raises(TemplateNotFound):
        engine.render_template("missing.yaml.j2", {})


def test_render_to_k8s_object_roundtrip(custom_template_dir: Path) -> None:
    template_path = custom_template_dir / "service.yaml.j2"
    template_path.write_text(
        "apiVersion: v1\n"
        "kind: Service\n"
        "metadata:\n  name: {{ name }}\n"
        "spec:\n  selector:\n    app: demo\n  ports:\n    - port: {{ port }}\n"
    )

    engine = KubernetesTemplateEngine(
        custom_templates_dir=str(custom_template_dir)
    )
    manifest = engine.render_to_k8s_object(
        template_name="service.yaml.j2",
        context={"name": "svc", "port": 80},
    )

    # Use resource_dict instead of k8s_object
    assert manifest.resource_dict["metadata"]["name"] == "svc"
    assert "port: 80" in manifest.template_yaml
    assert "kind: Service" in manifest.canonical_yaml


def test_render_to_k8s_object_returns_canonical_yaml(
    custom_template_dir: Path,
) -> None:
    template_path = custom_template_dir / "deployment.yaml.j2"
    template_path.write_text(
        "apiVersion: apps/v1\n"
        "kind: Deployment\n"
        "metadata:\n  name: {{ name }}\n"
        "spec:\n  selector:\n    matchLabels:\n      app: demo\n"
        "  template:\n    metadata:\n      labels:\n        app: demo\n"
        "    spec:\n      containers:\n        - name: web\n          image: nginx\n"
    )

    engine = KubernetesTemplateEngine(
        custom_templates_dir=str(custom_template_dir)
    )
    manifest = engine.render_to_k8s_object(
        "deployment.yaml.j2", {"name": "demo-deploy"}
    )

    assert "demo-deploy" in manifest.template_yaml
    # Use resource_dict instead of k8s_object
    expected_yaml = yaml.safe_dump(manifest.resource_dict, sort_keys=False)
    assert manifest.canonical_yaml == expected_yaml


def test_render_to_k8s_object_sets_metadata_attributes(
    custom_template_dir: Path,
) -> None:
    template_path = custom_template_dir / "job.yaml.j2"
    template_path.write_text(
        "apiVersion: batch/v1\n"
        "kind: Job\n"
        "metadata:\n"
        "  name: demo-job\n"
        "spec:\n"
        "  template:\n"
        "    metadata:\n"
        "      labels:\n"
        "        app: demo\n"
        "    spec:\n"
        "      containers:\n"
        "        - name: worker\n"
        "          image: busybox\n"
        "          command: ['echo', 'hello']\n"
        "      restartPolicy: Never\n"
    )

    engine = KubernetesTemplateEngine(
        custom_templates_dir=str(custom_template_dir)
    )
    manifest = engine.render_to_k8s_object(
        "job.yaml.j2",
        context={},
    )

    # Use resource_dict instead of k8s_object
    assert manifest.resource_dict.get("apiVersion") == "batch/v1"
    assert manifest.resource_dict.get("kind") == "Job"


def test_render_to_k8s_object_canonical_yaml_includes_metadata(
    custom_template_dir: Path,
) -> None:
    template_path = custom_template_dir / "configmap.yaml.j2"
    template_path.write_text(
        "apiVersion: v1\n"
        "kind: ConfigMap\n"
        "metadata:\n"
        "  name: demo-config\n"
        "data:\n"
        "  key: value\n"
    )

    engine = KubernetesTemplateEngine(
        custom_templates_dir=str(custom_template_dir)
    )
    manifest = engine.render_to_k8s_object(
        "configmap.yaml.j2",
        context={},
    )
    canonical = yaml.safe_load(manifest.canonical_yaml)

    assert canonical["apiVersion"] == "v1"
    assert canonical["kind"] == "ConfigMap"


def test_render_to_k8s_object_invalid_yaml(custom_template_dir: Path) -> None:
    template_path = custom_template_dir / "broken.yaml.j2"
    template_path.write_text("apiVersion: v1\nkind: Service\nmetadata: [1, 2")

    engine = KubernetesTemplateEngine(
        custom_templates_dir=str(custom_template_dir)
    )

    # Now raises yaml.YAMLError instead of ValueError
    with pytest.raises(yaml.YAMLError):
        engine.render_to_k8s_object("broken.yaml.j2", {})


def test_filters_behaviour() -> None:
    engine = KubernetesTemplateEngine(custom_templates_dir=None)

    assert engine._k8s_name_filter("My_Service") == "my-service"
    assert engine._k8s_label_value_filter("My Label") == "My-Label"

    data = {"a": 1}
    assert json.loads(engine._json_filter(data))["a"] == 1
    assert "a: 1" in engine._yaml_filter(data)


def test_save_manifests_and_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = KubernetesTemplateEngine()
    manifests = {"deployment.yaml": "apiVersion: v1\nkind: ConfigMap"}
    output_dir = tmp_path / "manifests"

    saved_path = engine.save_manifests(
        manifests=manifests,
        deployment_name="demo",
        output_dir=str(output_dir),
    )

    assert (saved_path / "deployment.yaml").read_text() == manifests[
        "deployment.yaml"
    ]

    def raising_client():
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "zenml.client.Client",
        raising_client,
    )

    fallback_path = engine.save_manifests(
        manifests, deployment_name="demo-two"
    )
    assert (fallback_path / "deployment.yaml").exists()
