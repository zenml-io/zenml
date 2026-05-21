"""Tests for Kubernetes manifest utilities."""

from zenml.integrations.kubernetes.constants import STEP_NAME_ANNOTATION_KEY
from zenml.integrations.kubernetes.manifest_utils import (
    build_pod_manifest,
    pod_template_manifest_from_pod,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings


def test_build_pod_manifest_merges_explicit_annotations_with_pod_settings() -> (
    None
):
    """Test explicit annotations preserve user-provided pod annotations."""
    pod_manifest = build_pod_manifest(
        pod_name=None,
        image_name="image",
        command=["python"],
        args=["-m", "entrypoint"],
        privileged=False,
        pod_settings=KubernetesPodSettings(annotations={"user": "annotation"}),
        annotations={STEP_NAME_ANNOTATION_KEY: "exact_step_name"},
    )

    assert pod_manifest.metadata.annotations == {
        "user": "annotation",
        STEP_NAME_ANNOTATION_KEY: "exact_step_name",
    }


def test_static_step_pod_template_keeps_exact_step_annotation() -> None:
    """Test static step pod templates preserve exact step annotations."""
    pod_manifest = build_pod_manifest(
        pod_name=None,
        image_name="image",
        command=["python"],
        args=["-m", "entrypoint"],
        privileged=False,
        pod_settings=KubernetesPodSettings(annotations={"user": "annotation"}),
        annotations={STEP_NAME_ANNOTATION_KEY: "exact_step_name"},
    )

    pod_template = pod_template_manifest_from_pod(pod_manifest)

    assert pod_template.metadata.annotations == {
        "user": "annotation",
        STEP_NAME_ANNOTATION_KEY: "exact_step_name",
    }
