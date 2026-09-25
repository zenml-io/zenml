"""Render deterministic evaluation summaries without model-authored claims."""

import html
import json
from typing import Any

from zenml.types import HTMLString


def _outcome(episode: dict[str, Any]) -> str:
    """Classify an episode without treating infrastructure errors as task failures.

    Args:
        episode: Recorded episode and grading result.

    Returns:
        Outcome label for the recorded evidence.
    """
    grading = episode.get("grading") or {}
    if (
        grading.get("infrastructure_error")
        or (grading.get("test_counts") or {}).get("error", 0) > 0
        or episode.get("infrastructure_error")
        or episode.get("cleanup_complete") is False
        or episode.get("exit_reason")
        in {"infrastructure_error", "provider_error"}
    ):
        return "Infrastructure error"
    if not grading or grading.get("raw_reward") is None:
        return "Incomplete"
    if grading.get("audited_valid") is True:
        return "Passed"
    return "Failed"


def summarize_evaluation(evaluation: dict[str, Any]) -> dict[str, Any]:
    """Calculate counts from recorded episodes rather than narrative text.

    Args:
        evaluation: Evaluation metadata and recorded episodes.

    Returns:
        Counts, response validity, token totals, and elapsed episode seconds.
    """
    episodes = evaluation.get("episodes", [])
    outcomes = [_outcome(episode) for episode in episodes]
    turns = [turn for episode in episodes for turn in episode.get("turns", [])]
    valid_responses = sum(
        (turn.get("action") or {}).get("type") in {"command", "done"}
        for turn in turns
    )
    usage = [turn.get("usage") or {} for turn in turns]
    return {
        "attempts": len(episodes),
        "passes": outcomes.count("Passed"),
        "failures": outcomes.count("Failed"),
        "infrastructure_errors": outcomes.count("Infrastructure error"),
        "incomplete": outcomes.count("Incomplete"),
        "responses": len(turns),
        "valid_responses": valid_responses,
        "format_errors": len(turns) - valid_responses,
        "valid_response_percent": (
            100 * valid_responses / len(turns) if turns else None
        ),
        "prompt_tokens": sum(
            item.get("prompt_tokens", 0) or 0 for item in usage
        ),
        "completion_tokens": sum(
            item.get("completion_tokens", 0) or 0 for item in usage
        ),
        "total_tokens": sum(
            item.get("total_tokens", 0) or 0 for item in usage
        ),
        "elapsed_seconds": sum(
            episode.get("elapsed_seconds", 0) or 0 for episode in episodes
        ),
        "cleanup_complete": (evaluation.get("cleanup") or {}).get("complete")
        is True,
    }


def _validate_comparison(
    evaluation: dict[str, Any], baseline: dict[str, Any]
) -> None:
    """Reject comparisons without matching, explicit evaluation identities.

    Args:
        evaluation: Current evaluation.
        baseline: Prior evaluation to compare.

    Raises:
        ValueError: Evaluation identities are missing, invalid, or different.
    """
    if any(
        item.get("model", {}).get("revision_verified") is False
        for item in (evaluation, baseline)
    ):
        raise ValueError(
            "Cannot compare evaluations: endpoint revision is unverified"
        )
    for key in ("dataset_revision", "protocol", "task_hashes", "mode"):
        if not evaluation.get(key) or evaluation[key] != baseline.get(key):
            raise ValueError(
                f"Cannot compare evaluations: {key} differs or is missing"
            )
    task_ids = [
        _episode_key(episode) for episode in evaluation.get("episodes", [])
    ]
    baseline_ids = [
        _episode_key(episode) for episode in baseline.get("episodes", [])
    ]
    if (
        not task_ids
        or len(set(task_ids)) != len(task_ids)
        or len(set(baseline_ids)) != len(baseline_ids)
        or set(task_ids) != set(baseline_ids)
    ):
        raise ValueError(
            "Cannot compare evaluations: task sets differ or are invalid"
        )
    if not {task_id for task_id, _ in task_ids}.issubset(
        evaluation["task_hashes"]
    ):
        raise ValueError("Cannot compare evaluations: task hashes are missing")


def _episode_key(episode: dict[str, Any]) -> tuple[str, int]:
    """Identify an evaluation attempt, including legacy single attempts.

    Args:
        episode: Recorded task attempt.

    Returns:
        Task ID and one-based attempt index.

    Raises:
        ValueError: The attempt index is invalid.
    """
    index = episode.get("attempt_index", 1)
    if type(index) is not int or index < 1:
        raise ValueError("Cannot compare evaluations: invalid attempt index")
    return episode["task_id"], index


def _episode_label(episode: dict[str, Any]) -> str:
    """Label individual attempts while preserving legacy task labels.

    Args:
        episode: Recorded task attempt.

    Returns:
        Task label with the one-based attempt number when recorded.
    """
    if "attempt_index" in episode:
        return f"{episode['task_id']} (attempt {episode['attempt_index']})"
    return str(episode["task_id"])


def _escape(value: Any) -> str:
    """Escape all dynamic values, including task identifiers and model output.

    Args:
        value: Value to display as text.

    Returns:
        Escaped HTML text.
    """
    return html.escape(str(value), quote=True)


def _details(label: str, value: Any) -> str:
    """Render recorded text in a native disclosure element.

    Args:
        label: Disclosure heading.
        value: Recorded text or JSON-compatible data.

    Returns:
        Escaped disclosure HTML.
    """
    if not isinstance(value, str):
        value = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
    return f"<details><summary>{_escape(label)}</summary><pre>{_escape(value)}</pre></details>"


def _task_rows(evaluation: dict[str, Any]) -> str:
    """Render per-task outcomes with their original evidence.

    Args:
        evaluation: Evaluation containing recorded episodes.

    Returns:
        Escaped table rows.
    """
    rows = []
    for episode in sorted(evaluation.get("episodes", []), key=_episode_key):
        turns = episode.get("turns", [])
        errors = sum(
            (turn.get("action") or {}).get("type") not in {"command", "done"}
            for turn in turns
        )
        grading = episode.get("grading") or {}
        evidence = _details(
            "Verifier output",
            grading.get("verifier_output", "No verifier output recorded."),
        )
        evidence += _details("Transcript", episode.get("transcript", []))
        evidence += _details(
            "Grading and exit reason",
            {
                "grading": grading,
                "exit_reason": episode.get("exit_reason"),
                "cleanup_complete": episode.get("cleanup_complete"),
            },
        )
        values = [
            _episode_label(episode),
            _outcome(episode),
            len(turns),
            errors,
            f"{episode.get('elapsed_seconds', 0) or 0:.2f}",
        ]
        rows.append(
            "<tr>"
            + "".join(f"<td>{_escape(value)}</td>" for value in values)
            + f"<td>{evidence}</td></tr>"
        )
    return (
        "".join(rows) or '<tr><td colspan="6">No episodes recorded.</td></tr>'
    )


def _comparison(evaluation: dict[str, Any], baseline: dict[str, Any]) -> str:
    """Render paired task outcomes and aggregate counts for compatible runs.

    Args:
        evaluation: Current evaluation.
        baseline: Compatible prior evaluation.

    Returns:
        Escaped comparison HTML.

    Raises:
        ValueError: Evaluation identities do not match.
    """  # noqa: DOC502
    _validate_comparison(evaluation, baseline)
    current = summarize_evaluation(evaluation)
    previous = summarize_evaluation(baseline)
    previous_tasks = {
        _episode_key(episode): episode for episode in baseline["episodes"]
    }
    rows = "".join(
        f"<tr><td>{_escape(_episode_label(episode))}</td>"
        f"<td>{_escape(_outcome(previous_tasks[_episode_key(episode)]))}</td>"
        f"<td>{_escape(_outcome(episode))}</td></tr>"
        for episode in sorted(evaluation["episodes"], key=_episode_key)
    )
    return (
        "<h2>Matched evaluation comparison</h2>"
        f"<p>Baseline model: {_escape(baseline.get('model', {}).get('name', 'Unspecified'))} "
        f"(revision {_escape(baseline.get('model', {}).get('revision', 'Unspecified'))}). "
        f"Audited passes: {previous['passes']}/{previous['attempts']} baseline; "
        f"{current['passes']}/{current['attempts']} current. "
        "This comparison alone does not establish a training gain.</p>"
        "<table><thead><tr><th>Task</th><th>Baseline</th><th>Current</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def render_evaluation_report(
    evaluation: dict[str, Any], baseline: dict[str, Any] | None = None
) -> HTMLString:
    """Build a standalone HTML artifact with escaped, inspectable evidence.

    Args:
        evaluation: Current evaluation metadata and recorded episodes.
        baseline: Optional evaluation with matching tasks and protocol.

    Returns:
        A deterministic HTML document suitable for ZenML artifact visualization.

    Raises:
        ValueError: Comparison identities differ or required identities are missing.
    """  # noqa: DOC502
    summary = summarize_evaluation(evaluation)
    comparison = (
        _comparison(evaluation, baseline) if baseline is not None else ""
    )
    model = evaluation.get("model") or {}
    mode = evaluation.get("mode")
    badge = (
        "MODEL EVALUATION"
        if mode == "model"
        else "FIXTURE CHECK: NOT A MODEL SCORE"
    )
    percent = summary["valid_response_percent"]
    validity = (
        f"{percent:.1f}%" if percent is not None else "N/A (no responses)"
    )
    cleanup = (
        "Complete" if summary["cleanup_complete"] else "Not confirmed complete"
    )
    metadata = {
        key: evaluation.get(key)
        for key in (
            "model",
            "mode",
            "dataset_revision",
            "protocol",
            "task_hashes",
            "cleanup",
            "status",
        )
    }
    return HTMLString(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Endless Terminals evaluation</title><style>"
        "body{font:16px/1.5 system-ui,sans-serif;color:#172339;background:#f3f5f8;max-width:1200px;margin:32px auto;padding:0 24px}"
        "h1,h2{line-height:1.2}.badge{display:inline-block;background:#dce8ff;padding:5px 10px;border-radius:5px;font-weight:700}"
        ".stats{display:flex;flex-wrap:wrap;gap:16px}.stats p{background:white;border:1px solid #d4dce8;border-radius:8px;padding:14px;margin:0;min-width:140px}"
        ".stats strong{display:block;font-size:26px}table{border-collapse:collapse;width:100%;background:white;margin:16px 0}"
        "th,td{text-align:left;border:1px solid #d4dce8;padding:10px;vertical-align:top}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.5 ui-monospace,monospace;max-height:420px;overflow:auto}"
        "details{margin:6px 0}summary{cursor:pointer}footer{margin-top:24px;color:#43516a}"
        "@media(max-width:700px){body{padding:0 10px}table{display:block;overflow:auto}}"
        "</style></head><body>"
        f'<p class="badge">{badge}</p><h1>Endless Terminals evaluation</h1>'
        f"<p>Model: {_escape(model.get('name', 'Unspecified'))}. "
        f"Revision: {_escape(model.get('revision', 'Unspecified'))}.</p>"
        f"<p>Run status: {_escape(evaluation.get('status', 'Unspecified'))}. Cleanup: {cleanup}.</p>"
        '<div class="stats">'
        f"<p>Audited passes<strong>{summary['passes']}/{summary['attempts']}</strong></p>"
        f"<p>Task failures<strong>{summary['failures']}</strong></p>"
        f"<p>Infrastructure errors<strong>{summary['infrastructure_errors']}</strong></p>"
        f"<p>Incomplete<strong>{summary['incomplete']}</strong></p></div>"
        f"<p>Valid response format: {validity} ({summary['valid_responses']}/{summary['responses']}). "
        f"Recorded tokens: {summary['total_tokens']}. "
        f"Total episode time: {summary['elapsed_seconds']:.2f} seconds.</p>"
        "<p>All recorded attempts are shown. Infrastructure errors and incomplete episodes are separate from task failures. "
        "A pass requires the audited grader result. Format validity counts command and done actions.</p>"
        f"{comparison}<h2>Task results</h2><table><thead><tr><th>Task</th><th>Outcome</th>"
        "<th>Responses</th><th>Format errors</th><th>Seconds</th><th>Evidence</th></tr></thead>"
        f"<tbody>{_task_rows(evaluation)}</tbody></table>"
        f"{_details('Evaluation identity and cleanup', metadata)}"
        "<footer>This qualified pilot subset does not establish broad benchmark performance. "
        "Fixture results validate the runner and graders, not model capability.</footer></body></html>"
    )
