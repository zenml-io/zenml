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
"""Structured data models for the software factory pipeline."""

import os
from typing import Any, Dict, List

from pydantic import BaseModel

from zenml.enums import VisualizationType
from zenml.materializers.pydantic_materializer import PydanticMaterializer


class PRRef(BaseModel):
    """Pull request reference."""

    url: str
    number: int


class TestReport(BaseModel):
    """Test report."""

    passed: bool
    summary: str

    def to_markdown(self) -> str:
        """Render the report for the dashboard.

        Returns:
            The report as Markdown.
        """
        status = "passed" if self.passed else "failed"
        return f"## Tests {status}\n\n```\n{self.summary.strip()}\n```\n"


class ReviewVerdict(BaseModel):
    """Review verdict."""

    approved: bool
    comments: List[str]

    def to_markdown(self) -> str:
        """Render the verdict for the dashboard.

        Returns:
            The verdict as Markdown.
        """
        status = "approved" if self.approved else "changes requested"
        comments = "\n".join(f"- {c}" for c in self.comments) or "No comments."
        return f"## Review {status}\n\n{comments}\n"


class ReportMaterializer(PydanticMaterializer):
    """Stores test reports and review verdicts with a Markdown visualization.

    The dashboard shows the JSON of a Pydantic artifact by default. The
    visualization makes test output and review comments readable at a glance.
    """

    ASSOCIATED_TYPES = (TestReport, ReviewVerdict)

    def save_visualizations(self, data: Any) -> Dict[str, VisualizationType]:
        """Write the Markdown rendering next to the artifact.

        Args:
            data: The test report or review verdict.

        Returns:
            The visualization path and its type.
        """
        path = os.path.join(self.uri, "report.md").replace("\\", "/")
        with self.artifact_store.open(path, "w") as f:
            f.write(data.to_markdown())
        return {path: VisualizationType.MARKDOWN}


class Review(BaseModel):
    """Review."""

    approved: bool
    feedback: str = ""
