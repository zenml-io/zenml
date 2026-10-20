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
from datetime import timedelta
from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, Field, SecretStr
from typesafe_sdk import (
    Answer,
    Choice,
    ChoiceAnswer,
    JSONContent,
    Noul,
    NoulAnswer,
    Question,
    Score,
    ScoreAnswer,
    SystemOneResponse,
    TypeSafeClient,
    TypeSafeError,
)

from zenml.client import Client
from zenml.constants import FILTERING_DATETIME_FORMAT
from zenml.enums import ExecutionStatus
from zenml.execution.pipeline.dynamic.run_context import (
    DynamicPipelineRunContext,
)
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.models import PipelineResponse, PipelineRunResponse
from zenml.steps.step_context import StepContext
from zenml.utils.metadata_utils import log_metadata

logger = get_logger(__name__)

TYPESAFE_SECRET_NAME = "typesafe"
TYPESAFE_API_KEY_ENV = "TYPESAFE_API_KEY"
DEFAULT_METADATA_PREFIX = "jev"


def _find_api_key() -> Optional[str]:
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


class JevConfig(BaseModel):
    """Settings shared by the Jev hooks.

    Lifecycle hooks take no arguments, so the built-in hooks call
    `JevConfig.load()`, which finds the API key in the environment or the
    secret store. Custom hooks pass overrides to `load()` to change the rest.
    """

    api_key: Optional[SecretStr] = Field(
        default=None,
        description="TypeSafe API key. Without one, the hooks log a warning "
        "and skip. Stored as a `SecretStr` so it never shows up in logs or "
        "reprs by accident",
    )
    model: Optional[str] = Field(
        default=None,
        description="Jev model override. Defaults to the SDK default, which "
        "the `TYPESAFE_DEFAULT_MODEL` environment variable can set",
    )
    metadata_prefix: str = Field(
        default=DEFAULT_METADATA_PREFIX,
        description="Prefix of every metadata key the hooks write, e.g. "
        "`jev` gives `jev.failure_category`",
    )
    max_traceback_chars: int = Field(
        default=8000,
        gt=0,
        description="Tracebacks are cut from the top to this many "
        "characters before they are sent to Jev, which bills per input "
        "token. The frames nearest the raise site carry most of the signal",
    )
    recent_runs: int = Field(
        default=5,
        gt=0,
        description="How many earlier runs of the pipeline the run summary "
        "hook sends to Jev as the baseline for what a normal run looks like",
    )
    recent_run_status: Optional[ExecutionStatus] = Field(
        default=None,
        description="Only use earlier runs with this status as the "
        "baseline, e.g. `ExecutionStatus.COMPLETED` to compare against "
        "successful runs after a string of failures. `None` uses every "
        "finished run",
    )

    @classmethod
    def load(cls, **overrides: Any) -> "JevConfig":
        """Build a config with the API key found in the environment or secrets.

        Args:
            **overrides: Field values that replace the defaults. An explicit
                `api_key` skips the lookup.

        Returns:
            The config.
        """
        if "api_key" not in overrides:
            overrides["api_key"] = _find_api_key()
        return cls(**overrides)


def _warn_missing_api_key() -> None:
    logger.warning(
        "No TypeSafe API key found in the `%s` environment variable or a "
        "ZenML secret named `%s`. Skipping Jev classification.",
        TYPESAFE_API_KEY_ENV,
        TYPESAFE_SECRET_NAME,
    )


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
    metadata: Dict[str, MetadataType] = {
        key: answer.choice
        if isinstance(answer, ChoiceAnswer)
        else answer.score,
        f"{key}.confidence": answer.confidence,
        # Score levels are integers in the SDK but metadata dicts need string
        # keys to survive the JSON round-trip.
        f"{key}.probabilities": {
            str(label): p for label, p in answer.probabilities.items()
        },
    }
    if isinstance(answer, ScoreAnswer):
        metadata[f"{key}.legend"] = {
            str(level): str(text) for level, text in answer.legend.items()
        }
    return metadata


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
    config: Optional[JevConfig] = None,
) -> Optional[SystemOneResponse]:
    """Ask Jev questions about `state` and log the answers as metadata.

    This is best-effort by design: a missing API key or an API error logs a
    warning and returns `None` instead of failing the step or run.

    Example, as a custom success hook:

        def triage_hook() -> None:
            jev_classify_and_log(
                state=get_step_context().step_run.config.parameters,
                questions={"risky": Noul(instructions="Is this config risky?")},
            )

    Args:
        state: Text, a JSON object or a JSON array for Jev to evaluate.
        questions: Jev questions keyed by the name used in metadata keys.
        config: Hook configuration. Defaults to `JevConfig.load()`.

    Returns:
        The Jev response, or `None` if nothing was classified.
    """
    config = config or JevConfig.load()
    if config.api_key is None:
        _warn_missing_api_key()
        return None

    try:
        with TypeSafeClient(
            api_key=config.api_key.get_secret_value()
        ) as client:
            response = client.system_one(
                state=state, questions=questions, model=config.model
            )
    except TypeSafeError as e:
        logger.warning("Jev classification failed, skipping: %s", e)
        return None

    metadata = response_to_metadata(response, prefix=config.metadata_prefix)
    if not _log_to_current_step_or_run(metadata):
        logger.warning(
            "Jev answered but there is no active step or dynamic pipeline "
            "run to attach the metadata to: %s",
            metadata,
        )
    return response


def build_failure_state(
    exception: BaseException, config: Optional[JevConfig] = None
) -> Dict[str, Any]:
    """Build the state the failure triage hook sends to Jev.

    Custom failure hooks can reuse it to ask extra questions about the same
    traceback.

    Args:
        exception: The exception that caused the failure.
        config: Hook configuration, for the traceback length. Defaults to
            `JevConfig()`.

    Returns:
        The tail of the traceback and, inside a step, the step name.
    """
    max_chars = (config or JevConfig()).max_traceback_chars
    # The traceback's last line already carries the exception type and
    # message, so they are not sent separately.
    formatted = "".join(traceback.format_exception(exception))
    state: Dict[str, Any] = {"traceback": formatted[-max_chars:]}
    if step_context := StepContext.get():
        state["step_name"] = step_context.step_run.name
    return state


def jev_failure_triage_hook(exception: BaseException) -> None:
    """Failure hook that asks Jev why a step or dynamic run failed.

    Logs `jev.failure_category` (infrastructure, data, code, dependency or
    credentials) and `jev.retry_likely_to_help` (the probability that an
    unchanged rerun succeeds) on the failed step run, or on the pipeline run
    when used as a run-level hook of a dynamic pipeline.

    Args:
        exception: The exception that caused the failure.
    """
    config = JevConfig.load()
    jev_classify_and_log(
        state=build_failure_state(exception, config),
        questions=FAILURE_TRIAGE_QUESTIONS,
        config=config,
    )


def _seconds(duration: Optional[timedelta]) -> Optional[float]:
    """Convert an optional duration to rounded seconds.

    Args:
        duration: The duration.

    Returns:
        The duration in seconds, or `None` if it is unknown.
    """
    return round(duration.total_seconds(), 1) if duration else None


def _run_duration(run: PipelineRunResponse) -> Optional[timedelta]:
    """Compute a pipeline run's duration if it has started and ended.

    Args:
        run: The pipeline run.

    Returns:
        The duration, or `None` if either time is missing.
    """
    if run.start_time is None or run.end_time is None:
        return None
    return run.end_time - run.start_time


def _summarize_recent_runs(
    pipeline: PipelineResponse, run: PipelineRunResponse, config: JevConfig
) -> List[Dict[str, Any]]:
    """Summarize the runs of a pipeline that finished before `run` started.

    "Finished before this run started" rather than "newest" keeps the
    baseline stable under concurrency: runs created and completed while
    `run` was executing, such as cached reruns, are not compared against.

    Args:
        pipeline: The pipeline to look up runs for.
        run: The run being assessed.
        config: Hook configuration with the baseline size and status filter.

    Returns:
        Status, duration and step count of up to `config.recent_runs` runs,
        newest first.
    """
    client = Client()
    started = run.start_time or run.created
    # The datetime filter has second granularity, so round up: a run that
    # finished within the second `run` started still counts as earlier. That
    # can let `run` itself through when it finishes within the same second,
    # so it is dropped by id below.
    before = started.replace(microsecond=0) + timedelta(seconds=1)
    filters: Dict[str, Any] = {
        "end_time": f"lt:{before.strftime(FILTERING_DATETIME_FORMAT)}"
    }
    if config.recent_run_status is not None:
        filters["status"] = config.recent_run_status.value
    # Hydrated because start and end times live in the run metadata, which
    # would otherwise be fetched with one extra request per run.
    runs = pipeline.get_runs(
        sort_by="desc:created",
        size=config.recent_runs + 1,
        hydrate=True,
        **filters,
    )
    return [
        {
            "status": earlier.status.value,
            "duration_seconds": _seconds(_run_duration(earlier)),
            # Only the count is needed, so ask for a one-item page instead of
            # listing every step.
            "step_count": client.list_run_steps(
                pipeline_run_id=earlier.id, exclude_retried=True, size=1
            ).total,
        }
        for earlier in runs
        if earlier.id != run.id
    ][: config.recent_runs]


def build_run_summary_state(
    exception: Optional[BaseException] = None,
    config: Optional[JevConfig] = None,
) -> Optional[Dict[str, Any]]:
    """Build the state the run summary hook sends to Jev.

    Only works as a run-level hook of a dynamic pipeline. Static pipelines
    copy pipeline hooks onto each step, so there is no finished run to assess.

    Args:
        exception: The exception that ended the run, if it failed.
        config: Hook configuration, for the baseline. Defaults to
            `JevConfig()`.

    Returns:
        The run's status, duration and steps next to a baseline of earlier
        runs, or `None` outside a run-level hook of a dynamic pipeline.
    """
    run_context = DynamicPipelineRunContext.get()
    if run_context is None or StepContext.is_active():
        logger.warning(
            "Jev run summaries only work as a run-level hook of a dynamic "
            "pipeline. Skipping."
        )
        return None

    config = config or JevConfig()
    # The context holds the run as it was when execution started, so fetch it
    # again for the final status and end time.
    run = Client().get_pipeline_run(run_context.run.id)
    pipeline = run.pipeline
    state: Dict[str, Any] = {
        "pipeline_name": pipeline.name if pipeline else None,
        "status": run.status.value,
        "duration_seconds": _seconds(_run_duration(run)),
        "steps": [
            {
                "name": name,
                "status": step.status.value,
                "duration_seconds": _seconds(step.duration),
            }
            for name, step in run.steps.items()
        ],
        "recent_runs": _summarize_recent_runs(pipeline, run, config)
        if pipeline
        else [],
    }
    if exception is not None:
        state["exception"] = f"{type(exception).__name__}: {exception}"
    return state


def jev_run_summary_hook(exception: Optional[BaseException] = None) -> None:
    """Run end hook for dynamic pipelines that asks Jev whether a run is odd.

    Sends Jev the finished run's status, duration and per-step results next
    to a summary of the pipeline's runs that finished before this one
    started, then logs `jev.needs_attention` (probability that a human
    should look) and `jev.anomaly` (0 = normal, 2 = very unusual) on the
    pipeline run.

    Use it as `@pipeline(dynamic=True, on_end=jev_run_summary_hook)`. Static
    pipelines only copy pipeline hooks onto each step, so there is no finished
    run to assess and the hook skips with a warning.

    Args:
        exception: The exception that ended the run, if it failed.
    """
    config = JevConfig.load()
    if config.api_key is None:
        # Checked before building the state, which costs server requests.
        _warn_missing_api_key()
        return
    state = build_run_summary_state(exception, config)
    if state is not None:
        jev_classify_and_log(
            state=state, questions=RUN_SUMMARY_QUESTIONS, config=config
        )
