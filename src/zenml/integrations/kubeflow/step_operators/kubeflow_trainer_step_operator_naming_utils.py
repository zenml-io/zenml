#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Naming and metadata helpers for Kubeflow Trainer TrainJobs."""

import random
import re
from typing import Dict

_TRAINJOB_NAME_SUFFIX = "trainer"
_TRAINJOB_STEP_SEGMENT_MAX_LENGTH = 10


def sanitize_kubernetes_name(name: str) -> str:
    """Sanitizes a Kubernetes resource name.

    Args:
        name: Name to sanitize.

    Returns:
        Sanitized resource name.
    """
    sanitized = re.sub(r"[^a-z0-9-]", "-", name.lower())
    sanitized = re.sub(r"^-+", "", sanitized)
    sanitized = re.sub(r"-+", "-", sanitized)
    sanitized = sanitized[:63]
    return re.sub(r"-+$", "", sanitized)


def build_trainjob_name(step_name: str) -> str:
    """Builds a unique TrainJob name from a step name.

    Args:
        step_name: Name of the pipeline step.

    Returns:
        A Kubernetes-safe TrainJob name.
    """
    random_prefix = random.choice("abcdef") + "".join(
        random.choices("0123456789abcdef", k=7)
    )
    # Keep compact to avoid Kubernetes 63-char name limits on derived resources.
    step_segment = sanitize_kubernetes_name(step_name)[
        :_TRAINJOB_STEP_SEGMENT_MAX_LENGTH
    ]
    if not step_segment:
        step_segment = "step"

    return sanitize_kubernetes_name(
        f"{random_prefix}-{step_segment}-{_TRAINJOB_NAME_SUFFIX}"
    )


def build_trainjob_labels(
    project_id: str,
    run_id: str,
    run_name: str,
    pipeline_name: str,
    step_name: str,
) -> Dict[str, str]:
    """Builds standard labels for Kubeflow Trainer TrainJobs.

    Args:
        project_id: Project ID.
        run_id: Pipeline run ID.
        run_name: Pipeline run name.
        pipeline_name: Pipeline name.
        step_name: Pipeline step name.

    Returns:
        Sanitized label dictionary.
    """
    return {
        "project_id": sanitize_kubernetes_name(project_id),
        "run_id": sanitize_kubernetes_name(run_id),
        "run_name": sanitize_kubernetes_name(run_name),
        "pipeline": sanitize_kubernetes_name(pipeline_name),
        "step_name": sanitize_kubernetes_name(step_name),
    }


def build_trainjob_annotations(
    operator_id: str, step_name: str
) -> Dict[str, str]:
    """Builds standard annotations for Kubeflow Trainer TrainJobs.

    Args:
        operator_id: Step operator ID.
        step_name: Pipeline step name.

    Returns:
        Annotation dictionary.
    """
    return {
        "zenml.step_operator": operator_id,
        "zenml.step_name": step_name,
    }
