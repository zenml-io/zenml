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

from zenml.integrations.kubernetes.template_engine import (
    KubernetesTemplateEngine,
)


def test_load_yaml_documents_multi_doc():
    """Test loading multiple YAML documents separated by ---."""
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


def test_load_yaml_documents_list_format():
    """Test loading YAML with top-level list of resources."""
    yaml_content = """
- apiVersion: v1
  kind: ConfigMap
  metadata:
    name: cm1
- apiVersion: v1
  kind: Secret
  metadata:
    name: s1
"""
    docs = KubernetesTemplateEngine.load_yaml_documents(yaml_content)
    assert len(docs) == 2
    assert {d["metadata"]["name"] for d in docs} == {"cm1", "s1"}


def test_load_yaml_documents_empty():
    """Test loading empty YAML returns empty list."""
    yaml_content = ""
    docs = KubernetesTemplateEngine.load_yaml_documents(yaml_content)
    assert len(docs) == 0


def test_load_yaml_documents_single_resource():
    """Test loading single YAML resource (no list, no ---)."""
    yaml_content = """
apiVersion: v1
kind: Service
metadata:
  name: my-svc
"""
    docs = KubernetesTemplateEngine.load_yaml_documents(yaml_content)
    assert len(docs) == 1
    assert docs[0]["kind"] == "Service"
    assert docs[0]["metadata"]["name"] == "my-svc"


def test_render_file_with_templating(tmp_path):
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
