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
"""Hooks that ask TypeSafe's Jev model questions and log the answers.

Jev answers typed questions (yes/no, pick-one-label, rubric score) about a
piece of text or JSON with probabilities attached, and never generates text.
Each answer is flattened into scalar metadata keys such as
`jev.failure_category` so they can be filtered on later, e.g. with
`Client().list_run_steps(run_metadata="jev.failure_category:data")` for step
hooks or `Client().list_pipeline_runs(run_metadata=...)` for run hooks.
"""

import os
import traceback
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional
from uuid import UUID

from typesafe_sdk import (
    Answer,
    Choice,
    ChoiceAnswer,
    JSONContent,
    Noul,
    NoulAnswer,
    Question,
    Score,
    SystemOneResponse,
    TypeSafeClient,
    TypeSafeError,
)

from zenml.client import Client
from zenml.execution.pipeline.dynamic.run_context import (
    DynamicPipelineRunContext,
)
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.steps.step_context import StepContext
from zenml.utils.metadata_utils import log_metadata

logger = get_logger(__name__)

TYPESAFE_SECRET_NAME = "typesafe"
TYPESAFE_API_KEY_ENV = "TYPESAFE_API_KEY"
DEFAULT_METADATA_PREFIX = "jev"

# Jev bills per input token, so tracebacks are cut from the top: the frames
# nearest the raise site carry most of the signal.
MAX_TRACEBACK_CHARS = 8000
RECENT_RUNS_FOR_COMPARISON = 5

FAILURE_TRIAGE_QUESTIONS: Dict[str, Question] = {
    "failure_category": Choice(
        instructions="What is the most likely root cause of this ML pipeline "
        "step failure?",
        criteria={
            "infrastructure": "Compute, network, storage, container or "
            "orchestrator problems: timeouts, connection resets, "
            "out-of-memory, preempted or evicted nodes, quota limits.",
            "data": "Unexpected, missing, malformed or schema-violating input "
            "data.",
            "code": "A bug in the user's own code: wrong logic, type errors, "
            "attribute errors, failed assertions.",
            "dependency": "Missing packages, import errors or version "
            "incompatibilities between libraries.",
            "credentials": "Authentication or authorization problems: expired "
            "tokens, missing secrets, permission denied.",
        },
    ),
    "retry_likely_to_help": Noul(
        instructions="Would rerunning this step unchanged, without any code, "
        "data or configuration change, likely succeed?",
        criteria={
            "true": "The error is transient, such as a network blip, a "
            "temporary outage or a preempted machine.",
            "false": "The error is deterministic and will happen again on "
            "rerun.",
        },
    ),
}

RUN_SUMMARY_QUESTIONS: Dict[str, Question] = {
    "needs_attention": Noul(
        instructions="Should a human look at this ML pipeline run? Consider "
        "failed steps, a failed run, and duration or step count that differ "
        "markedly from the recent runs of the same pipeline.",
    ),
    "anomaly": Score(
        instructions="How unusual is the current run compared with the recent "
        "runs of the same pipeline?",
        criteria=[
            "Looks like the recent runs.",
            "Somewhat unusual.",
            "Very unusual.",
        ],
    ),
}


def _get_api_key() -> Optional[str]:
    """Find the TypeSafe API key in the environment or the secret store.

    Returns:
        The API key, or `None` if it is not configured anywhere.
    """
    if api_key := os.environ.get(TYPESAFE_API_KEY_ENV, "").strip():
        return api_key
    try:
        secret = Client().get_secret(
            TYPESAFE_SECRET_NAME, allow_partial_name_match=False
        )
    except (KeyError, NotImplementedError):
        return None
    return secret.secret_values.get("api_key") or None


def _answer_to_metadata(key: str, answer: Answer) -> Dict[str, MetadataType]:
    """Flatten one Jev answer into metadata entries.

    The headline value sits on `key` itself so it can be filtered on directly;
    confidence and full distributions go on sub-keys.

    Args:
        key: The metadata key for the answer's headline value.
        answer: The Jev answer.

    Returns:
        The metadata entries for the answer.
    """
    if isinstance(answer, NoulAnswer):
        return {key: answer.noul}
    if isinstance(answer, ChoiceAnswer):
        return {
            key: answer.choice,
            f"{key}.confidence": answer.confidence,
            f"{key}.probabilities": dict(answer.probabilities),
        }
    return {
        key: answer.score,
        f"{key}.confidence": answer.confidence,
        # Score levels are integers in the SDK but metadata dicts need string
        # keys to survive the JSON round-trip.
        f"{key}.probabilities": {
            str(level): p for level, p in answer.probabilities.items()
        },
        f"{key}.legend": {
            str(level): str(text) for level, text in answer.legend.items()
        },
    }


def response_to_metadata(
    response: SystemOneResponse, prefix: str = DEFAULT_METADATA_PREFIX
) -> Dict[str, MetadataType]:
    """Convert a Jev response into flat ZenML metadata.

    Args:
        response: The Jev response.
        prefix: The prefix for all metadata keys.

    Returns:
        The metadata entries for all answers plus the model that answered.
    """
    metadata: Dict[str, MetadataType] = {f"{prefix}.model": response.model}
    for name, answer in response.answers.items():
        metadata.update(_answer_to_metadata(f"{prefix}.{name}", answer))
    return metadata


def _log_to_current_step_or_run(metadata: Dict[str, MetadataType]) -> bool:
    """Attach metadata to the step or dynamic pipeline run being executed.

    A step context wins over a run context because a step hook inside a
    dynamic pipeline should annotate its own step, not the whole run.

    Args:
        metadata: The metadata to log.

    Returns:
        Whether there was a step or run to attach the metadata to.
    """
    if StepContext.is_active():
        log_metadata(metadata=metadata)
        return True
    if run_context := DynamicPipelineRunContext.get():
        log_metadata(
            metadata=metadata, run_id_name_or_prefix=run_context.run.id
        )
        return True
    return False


def jev_classify_and_log(
    state: JSONContent,
    questions: Mapping[str, Question],
    metadata_prefix: str = DEFAULT_METADATA_PREFIX,
    model: Optional[str] = None,
) -> Optional[SystemOneResponse]:
    """Ask Jev questions about `state` and log the answers as metadata.

    Outside hooks this is best-effort by design: a missing API key or an API
    error logs a warning and returns `None` instead of failing the step.

    The API key is read from the `TYPESAFE_API_KEY` environment variable, or
    from the `api_key` key of a ZenML secret named `typesafe`. The model
    defaults to the SDK default, which `TYPESAFE_DEFAULT_MODEL` can override.

    Example, as a custom success hook:

        def triage_hook() -> None:
            jev_classify_and_log(
                state=get_step_context().step_run.config.parameters,
                questions={"risky": Noul(instructions="Is this config risky?")},
            )

    Args:
        state: Text, a JSON object or a JSON array for Jev to evaluate.
        questions: Jev questions keyed by the name used in metadata keys.
        metadata_prefix: The prefix for all metadata keys.
        model: Optional Jev model override.

    Returns:
        The Jev response, or `None` if nothing was classified.
    """
    api_key = _get_api_key()
    if not api_key:
        logger.warning(
            "No TypeSafe API key found in the `%s` environment variable or a "
            "ZenML secret named `%s`. Skipping Jev classification.",
            TYPESAFE_API_KEY_ENV,
            TYPESAFE_SECRET_NAME,
        )
        return None

    try:
        with TypeSafeClient(api_key=api_key) as client:
            response = client.system_one(
                state=state, questions=questions, model=model
            )
    except TypeSafeError as e:
        logger.warning("Jev classification failed, skipping: %s", e)
        return None

    metadata = response_to_metadata(response, prefix=metadata_prefix)
    if not _log_to_current_step_or_run(metadata):
        logger.warning(
            "Jev answered but there is no active step or dynamic pipeline "
            "run to attach the metadata to: %s",
            metadata,
        )
    return response


def _format_exception(exception: BaseException) -> str:
    """Format an exception with its traceback, keeping only the tail.

    Args:
        exception: The exception to format.

    Returns:
        The formatted traceback, cut to `MAX_TRACEBACK_CHARS`.
    """
    formatted = "".join(traceback.format_exception(exception))
    return formatted[-MAX_TRACEBACK_CHARS:]


def jev_failure_triage_hook(exception: BaseException) -> None:
    """Failure hook that asks Jev why a step or dynamic run failed.

    Logs `jev.failure_category` (infrastructure, data, code, dependency or
    credentials) and `jev.retry_likely_to_help` (the probability that an
    unchanged rerun succeeds) on the failed step run, or on the pipeline run
    when used as a run-level hook of a dynamic pipeline.

    Args:
        exception: The exception that caused the failure.
    """
    state: Dict[str, Any] = {
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
        "traceback": _format_exception(exception),
    }
    if step_context := StepContext.get():
        state["step_name"] = step_context.step_run.name
    jev_classify_and_log(state=state, questions=FAILURE_TRIAGE_QUESTIONS)


def _seconds_between(
    start: Optional[datetime], end: Optional[datetime]
) -> Optional[float]:
    """Compute a duration in seconds if both ends are known.

    Args:
        start: The start time.
        end: The end time.

    Returns:
        The duration in seconds, or `None` if either time is missing.
    """
    if start is None or end is None:
        return None
    return round((end - start).total_seconds(), 1)


def _summarize_recent_runs(
    pipeline_id: Optional[UUID], exclude_run_id: UUID
) -> List[Dict[str, Any]]:
    """Summarize the latest previous runs of a pipeline as a baseline.

    Args:
        pipeline_id: The pipeline to look up runs for.
        exclude_run_id: The run being assessed, which is left out.

    Returns:
        Status, duration and step count of up to
        `RECENT_RUNS_FOR_COMPARISON` recent runs.
    """
    if pipeline_id is None:
        return []
    runs = Client().list_pipeline_runs(
        pipeline_id=pipeline_id,
        sort_by="desc:created",
        size=RECENT_RUNS_FOR_COMPARISON + 1,
    )
    return [
        {
            "status": run.status.value,
            "duration_seconds": _seconds_between(run.start_time, run.end_time),
            "step_count": len(run.steps),
        }
        for run in runs.items
        if run.id != exclude_run_id
    ][:RECENT_RUNS_FOR_COMPARISON]


def jev_run_summary_hook(exception: Optional[BaseException] = None) -> None:
    """Run end hook for dynamic pipelines that asks Jev whether a run is odd.

    Sends Jev the finished run's status, duration and per-step results next
    to a summary of the pipeline's recent runs, then logs
    `jev.needs_attention` (probability that a human should look) and
    `jev.anomaly` (0 = normal, 2 = very unusual) on the pipeline run.

    Use it as `@pipeline(dynamic=True, on_end=jev_run_summary_hook)`. Static
    pipelines only copy pipeline hooks onto each step, so there is no finished
    run to assess and the hook skips with a warning.

    Args:
        exception: The exception that ended the run, if it failed.
    """
    run_context = DynamicPipelineRunContext.get()
    if run_context is None or StepContext.is_active():
        logger.warning(
            "`jev_run_summary_hook` only works as a run-level hook of a "
            "dynamic pipeline. Skipping."
        )
        return

    # The context holds the run as it was when execution started, so fetch it
    # again for the final status and end time.
    run = Client().get_pipeline_run(run_context.run.id)
    state: Dict[str, Any] = {
        "pipeline_name": run.pipeline.name if run.pipeline else None,
        "status": run.status.value,
        "duration_seconds": _seconds_between(run.start_time, run.end_time),
        "steps": [
            {
                "name": name,
                "status": step.status.value,
                "duration_seconds": _seconds_between(
                    step.start_time, step.end_time
                ),
            }
            for name, step in run.steps.items()
        ],
        "recent_runs": _summarize_recent_runs(
            run.pipeline.id if run.pipeline else None, exclude_run_id=run.id
        ),
    }
    if exception is not None:
        state["exception"] = f"{type(exception).__name__}: {exception}"
    jev_classify_and_log(state=state, questions=RUN_SUMMARY_QUESTIONS)
