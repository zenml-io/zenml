import json
from pathlib import Path

import pytest
import yaml
from jinja2 import TemplateNotFound

from zenml.integrations.kubernetes.template_engine import (
    KubernetesTemplateEngine,
    create_manifest_directory,
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

    assert manifest.k8s_object.metadata.name == "svc"
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
    expected_yaml = yaml.safe_dump(
        manifest.k8s_object.to_dict(), sort_keys=False
    )
    assert manifest.canonical_yaml == expected_yaml


def test_render_to_k8s_object_invalid_yaml(custom_template_dir: Path) -> None:
    template_path = custom_template_dir / "broken.yaml.j2"
    template_path.write_text("apiVersion: v1\nkind: Service\nmetadata: [1, 2")

    engine = KubernetesTemplateEngine(
        custom_templates_dir=str(custom_template_dir)
    )

    with pytest.raises(ValueError):
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


def test_create_manifest_directory(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    created = create_manifest_directory(str(base_dir))
    assert created.exists()
    assert created.parent == base_dir

    temp_dir = create_manifest_directory()
    assert temp_dir.exists()
