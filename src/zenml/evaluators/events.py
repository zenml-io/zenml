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
"""Event types emitted by the evaluator framework.

Discovery notes (Task 8 inspection of the ZenML event-trigger system):

  Base class: No project-wide ``BaseEvent`` class exists. The event system
  is modelled as trigger *configurations* rather than typed event objects.
  ``PlatformEventTrigger`` (src/zenml/models/v2/core/triggers.py) is the
  Pydantic model users create to subscribe to platform events; it holds a
  ``source_entity`` (SourceType + id) and a list of ``target_events``
  (string enum values validated against ``PLATFORM_EVENT_REGISTRY``).

  Registration mechanism: ``PLATFORM_EVENT_REGISTRY``
  (src/zenml/enums.py:724) maps each ``SourceType`` enum member to a
  ``DescribedValuesEnum`` subclass (e.g. ``PipelineEvent``,
  ``PipelineRunEvent``).  To introduce a new source type you would add a new
  ``SourceType`` member, define a ``DescribedValuesEnum`` for its event
  values, and register both in that dict.  The ``EvalRegressionEvent``
  payload does *not* map to a ``SourceType``; it is an evaluator-framework
  concept surfaced through a dedicated emit path (Task 9) rather than through
  the platform-event trigger machinery.

  Emit API: ``EventDispatcher`` (src/zenml/dispatcher/dispatcher.py) is a
  singleton that fans out to registered ``EventHandler`` instances.  The
  only method currently wired is ``handle_run_status_update(run)``, which is
  called from ``sql_zen_store.py`` after a pipeline-run status change.
  Task 9's ``_emit_event`` helper will call a new method on this dispatcher
  (or call handlers directly) to route ``EvalRegressionEvent`` payloads.

  Decision: ``EvalRegressionEvent`` subclasses plain ``pydantic.BaseModel``
  because there is no ``BaseEvent`` to inherit from, and attaching it to the
  ``PLATFORM_EVENT_REGISTRY`` would require adding a new ``SourceType``
  value to core enums — an invasive change deferred to a later task.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.evaluators.result import EvaluationMode


class EvalRegressionEvent(BaseModel):
    """Emitted when an evaluator run regresses against its baseline.

    Carries both the current aggregates and the baseline so downstream
    handlers (Slack, PagerDuty, re-run triggers) can decide routing based
    on metric deltas without re-fetching artifacts.
    """

    suite_name: str
    mode: EvaluationMode
    evaluator: str
    pipeline_run_id: UUID
    artifact_id: UUID
    aggregates: Dict[str, float]
    baseline_aggregates: Dict[str, float]
    regressed_metrics: Dict[str, float]
    model_version_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
