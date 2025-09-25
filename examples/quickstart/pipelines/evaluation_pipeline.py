# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2025. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Pipeline for evaluating agent performance across different modes."""

import os
from typing import Any

from steps.evaluate import evaluate_agent_performance, generate_test_dataset

from zenml import pipeline
from zenml.config import DockerSettings


@pipeline(
    enable_cache=False,
    settings={
        "docker": DockerSettings(
            requirements="requirements.txt",
            environment={
                "OPENAI_API_KEY": "${OPENAI_API_KEY}",
            },
        )
    },
)
def agent_evaluation_pipeline() -> Any:
    """Compare LLM-only vs Hybrid agent performance.

    Returns:
        Tuple of evaluation results and HTML visualization for dashboard display.
    """
    # Generate test dataset
    test_texts, test_labels = generate_test_dataset()

    # Run comprehensive evaluation
    evaluation_results, confusion_matrices_html = evaluate_agent_performance(
        test_texts, test_labels
    )

    return evaluation_results, confusion_matrices_html
