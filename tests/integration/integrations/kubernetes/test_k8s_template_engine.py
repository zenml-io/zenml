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
from pathlib import Path

from zenml.integrations.kubernetes.template_engine import (
    KubernetesTemplateEngine,
)


def test_k8s_name_filter_basic():
    eng = KubernetesTemplateEngine(strict_undefined=False)
    f = eng._k8s_name_filter

    # Behavior depends on kube_utils.sanitize_label; we only assert invariants.
    out = f("My App")
    assert isinstance(out, str)
    assert len(out) <= 63
    assert out  # non-empty

    long_out = f("x" * 200)
    assert len(long_out) <= 63


def test_k8s_label_value_filter_respects_constraints():
    f = KubernetesTemplateEngine._k8s_label_value_filter

    # Valid label value should be unchanged
    assert f("valid.value-1_2") == "valid.value-1_2"

    # For "  bad$$value!! ":
    # - invalid chars become '-'
    # - leading/trailing invalid trimmed
    # - internal invalid => may result in double dashes, which is allowed
    assert f("  bad$$value!! ") == "bad--value"

    # Length capped
    assert len(f("x" * 200)) <= 63


def test_load_yaml_documents_multi_doc():
    yaml_content = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: cm1
---
apiVersion: v1
kind: Secret
metadata:
  name: s1
"""
    docs = KubernetesTemplateEngine.load_yaml_documents(yaml_content)
    assert len(docs) == 2
    assert {d["metadata"]["name"] for d in docs} == {"cm1", "s1"}


def test_dump_yaml_documents_round_trip():
    docs = [
        {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "cm1"}},
        {"apiVersion": "v1", "kind": "Secret", "metadata": {"name": "s1"}},
    ]

    out = KubernetesTemplateEngine.dump_yaml_documents(docs)
    loaded = KubernetesTemplateEngine.load_yaml_documents(out)
    assert loaded == docs


def test_render_jinja_template_from_custom_dir(tmp_path):
    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    tpl_file = tpl_dir / "deployment.yaml.j2"

    tpl_file.write_text(
        """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ name | k8s_name }}
spec:
  replicas: {{ replicas }}
"""
    )

    eng = KubernetesTemplateEngine(
        custom_templates_dir=str(tpl_dir),
        strict_undefined=True,
    )

    resources = eng.render_template(
        "deployment.yaml.j2",
        context={"name": "My App", "replicas": 2},
    )

    assert len(resources) == 1
    dep = resources[0]
    assert dep["apiVersion"] == "apps/v1"
    assert dep["kind"] == "Deployment"
    assert dep["spec"]["replicas"] == 2
    assert dep["metadata"]["name"]


def test_render_yaml_file_with_templating(tmp_path):
    yaml_file = tmp_path / "svc.yaml"
    yaml_file.write_text(
        """apiVersion: v1
kind: Service
metadata:
  name: {{ name }}
spec:
  type: ClusterIP
  ports:
    - port: {{ port }}
"""
    )

    eng = KubernetesTemplateEngine(strict_undefined=True)
    resources = eng.render_template(
        str(yaml_file),
        context={"name": "my-svc", "port": 8080},
    )

    assert len(resources) == 1
    svc = resources[0]
    assert svc["kind"] == "Service"
    assert svc["metadata"]["name"] == "my-svc"
    assert svc["spec"]["ports"][0]["port"] == 8080


def test_save_k8s_objects_strips_internal_fields(tmp_path):
    class DummyObj:
        def to_dict(self):
            return {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {
                    "name": "cm1",
                    "namespace": "ns",
                    "uid": "123",
                    "resourceVersion": "999",
                    "managedFields": [],
                },
                "status": {"foo": "bar"},
                "data": {"k": "v"},
            }

    eng = KubernetesTemplateEngine(strict_undefined=True)

    files = eng.save_k8s_objects(
        [DummyObj()],
        deployment_name="dep1",
        output_dir=str(tmp_path),
    )

    assert len(files) == 1
    path = Path(files[0])
    assert path.exists()

    content = path.read_text()
    # Internal fields should be stripped
    assert "status:" not in content
    assert "managedFields" not in content
    assert "resourceVersion" not in content
    assert "uid" not in content
    # User data remains
    assert "data:" in content
