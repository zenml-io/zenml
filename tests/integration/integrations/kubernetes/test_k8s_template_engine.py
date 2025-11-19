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
#  OR implied. See the License for the specific language governing
#  permissions and limitations under the License.

import textwrap

import pytest
import yaml

from zenml.integrations.kubernetes.template_engine import (
    KubernetesTemplateEngine,
)

# ---------------------------------------------------------------------------
# load_yaml_documents
# ---------------------------------------------------------------------------


def test_load_yaml_documents_multi_doc():
    """Loading multiple YAML documents separated by --- yields multiple dicts."""
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
    docs = KubernetesTemplateEngine.load_yaml_documents(
        textwrap.dedent(yaml_content)
    )
    assert len(docs) == 2
    assert {d["metadata"]["name"] for d in docs} == {"cm1", "s1"}


def test_load_yaml_documents_list_format():
    """Top-level list of resources is supported and flattened."""
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
    docs = KubernetesTemplateEngine.load_yaml_documents(
        textwrap.dedent(yaml_content)
    )
    assert len(docs) == 2
    assert {d["metadata"]["name"] for d in docs} == {"cm1", "s1"}


def test_load_yaml_documents_empty_returns_empty_list():
    """Empty or whitespace-only YAML returns an empty list (no docs)."""
    for yaml_content in ("", "   ", "\n# just comment\n"):
        docs = KubernetesTemplateEngine.load_yaml_documents(yaml_content)
        assert docs == []


def test_load_yaml_documents_single_resource():
    """Single YAML resource (no list, no ---) is supported."""
    yaml_content = """
    apiVersion: v1
    kind: Service
    metadata:
      name: my-svc
    """
    docs = KubernetesTemplateEngine.load_yaml_documents(
        textwrap.dedent(yaml_content)
    )
    assert len(docs) == 1
    assert docs[0]["kind"] == "Service"
    assert docs[0]["metadata"]["name"] == "my-svc"


def test_load_yaml_documents_invalid_yaml_raises_value_error():
    """Invalid YAML should be turned into a ValueError."""
    yaml_content = "apiVersion: v1\nkind: ConfigMap\nmetadata: [unclosed"
    with pytest.raises(ValueError, match="Invalid YAML"):
        KubernetesTemplateEngine.load_yaml_documents(yaml_content)


def test_load_yaml_documents_non_dict_or_list_doc_raises():
    """YAML docs that are not dict or list of dicts are rejected."""
    yaml_content = """
    42
    """
    with pytest.raises(ValueError, match="must be a dictionary or list"):
        KubernetesTemplateEngine.load_yaml_documents(
            textwrap.dedent(yaml_content)
        )


def test_load_yaml_documents_list_with_non_dict_item_raises():
    """List docs must contain only dict items."""
    yaml_content = """
    - apiVersion: v1
      kind: ConfigMap
      metadata:
        name: cm1
    - 42
    """
    with pytest.raises(ValueError, match=r"item 2 must be a dictionary"):
        KubernetesTemplateEngine.load_yaml_documents(
            textwrap.dedent(yaml_content)
        )


# ---------------------------------------------------------------------------
# render_template
# ---------------------------------------------------------------------------


def test_render_template_with_templating(tmp_path):
    yaml_file = tmp_path / "svc.yaml"
    yaml_file.write_text(
        textwrap.dedent(
            """\
            apiVersion: v1
            kind: Service
            metadata:
              name: {{ name }}
            spec:
              type: ClusterIP
              ports:
                - port: {{ port }}
            """
        )
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


def test_render_template_strict_undefined_raises_for_missing_variable(
    tmp_path,
):
    yaml_file = tmp_path / "cm.yaml"
    yaml_file.write_text(
        textwrap.dedent(
            """\
            apiVersion: v1
            kind: ConfigMap
            metadata:
              name: {{ cm_name }}
            data:
              key: value
            """
        )
    )

    eng = KubernetesTemplateEngine(strict_undefined=True)

    with pytest.raises(ValueError, match="Failed to render Jinja2 template"):
        eng.render_template(str(yaml_file), context={})  # cm_name missing


def test_render_template_non_strict_undefined_renders_blank_for_missing_variable(
    tmp_path,
):
    yaml_file = tmp_path / "cm.yaml"
    yaml_file.write_text(
        textwrap.dedent(
            """\
            apiVersion: v1
            kind: ConfigMap
            metadata:
              name: {{ cm_name }}
            """
        )
    )

    eng = KubernetesTemplateEngine(strict_undefined=False)
    resources = eng.render_template(str(yaml_file), context={})
    assert len(resources) == 1
    cm = resources[0]
    assert cm["metadata"]["name"] in ("", None)


def test_render_template_invalid_yaml_after_rendering_raises(tmp_path):
    """Ensure YAML parsing errors after successful Jinja rendering get wrapped."""
    yaml_file = tmp_path / "bad.yaml"
    yaml_file.write_text(
        textwrap.dedent(
            """\
            apiVersion: v1
            kind: ConfigMap
            metadata:
              name: {{ name }}
            data:
              key: [unclosed
            """
        )
    )

    eng = KubernetesTemplateEngine(strict_undefined=True)
    with pytest.raises(ValueError, match="Invalid YAML"):
        eng.render_template(str(yaml_file), context={"name": "cm"})


def test_render_template_round_trips_to_yaml_and_back(tmp_path):
    """Sanity check that our to_yaml filter emits valid YAML."""
    yaml_file = tmp_path / "obj.yaml"
    yaml_file.write_text(
        textwrap.dedent(
            """\
            apiVersion: v1
            kind: ConfigMap
            metadata:
              name: cm
            data:
              as_yaml: |
                {{ data | to_yaml }}
            """
        )
    )

    eng = KubernetesTemplateEngine(strict_undefined=True)
    resources = eng.render_template(
        str(yaml_file),
        context={"data": {"a": 1, "b": "two"}},
    )
    assert len(resources) == 1
    cm = resources[0]
    assert cm["kind"] == "ConfigMap"
    embedded = cm["data"]["as_yaml"]
    parsed = yaml.safe_load(embedded)
    assert isinstance(parsed, dict)
    assert parsed.get("a") == 1
