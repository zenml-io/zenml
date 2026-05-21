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
"""Models representing the metric store read (fetch) path.

These are deliberately plain ``BaseModel``s rather than DB-backed
``ProjectScoped`` models: metrics are never persisted in ZenML's
database (they are exported straight to an OTLP collector), so there
is no metrics table to model. The shape exists so the read API
contract is stable for future flavors, even though the only built-in
flavor (``OtelMetricStore``) is fire-and-forget and does not implement
fetch.
"""

from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field


class MetricSample(BaseModel):
    """A single metric measurement returned by a fetch.

    The metric analogue of ``zenml.utils.logging_utils.LogEntry``: one
    value at one point in time, plus the identity labels it was recorded
    with (run id, step id, pipeline name, ...) so the caller can slice
    it the same way logs are sliced.
    """

    name: str = Field(
        title="The metric name, e.g. 'zenml.step.cpu_percent'.",
    )
    value: float = Field(
        title="The measured value at this point in time.",
    )
    timestamp: datetime = Field(
        title="When the sample was recorded.",
    )
    attributes: Dict[str, str] = Field(
        default_factory=dict,
        title="Identity labels attached to the sample (run/step/"
        "pipeline ids, ...).",
    )


class MetricsResponse(BaseModel):
    """Envelope returned by the metric store read path.

    A thin container around the samples (no pagination cursors / DB
    metadata, unlike ``LogsResponse``) so the API shape is stable for a
    future backend-specific flavor that can actually serve metrics back.
    """

    samples: List[MetricSample] = Field(
        default_factory=list,
        title="The metric samples matching the query.",
    )
    truncated: bool = Field(
        default=False,
        title="True if more samples matched than the requested limit.",
    )
