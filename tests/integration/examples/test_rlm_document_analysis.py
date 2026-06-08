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

"""Smoke test for the RLM document analysis example in fallback mode.

Runs without OPENAI_API_KEY to exercise the keyword-fallback path
against the bundled 60-email sample dataset.
"""

import pytest

from tests.integration.examples.utils import run_example


def test_rlm_fallback_mode(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Runs the RLM document analysis example without an API key.

    Uses max-chunks=2 and max-iterations=2 for speed.
    Expected steps: load_documents, plan_decomposition,
    process_chunk x2, aggregate_results = 5 steps.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with run_example(
        request=request,
        name="rlm_document_analysis",
        is_public_example=True,
        example_args=[
            "--query",
            "What financial irregularities are discussed?",
            "--max-chunks",
            "2",
            "--max-iterations",
            "2",
        ],
        pipelines={"rlm_analysis_pipeline": (1, 5)},
    ):
        pass
