# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2026. All rights reserved.
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
"""Step: build the campaign report from job summaries."""

import html
import logging
from collections import defaultdict
from pathlib import Path
from typing import Annotated, Any, Dict, List, Tuple

from models.harbor_models import CampaignReport, JobSummary

from zenml import log_metadata, step
from zenml.types import HTMLString

logger = logging.getLogger(__name__)


def _load_text_asset(filename: str) -> str:
    """Load a text asset from the data/ directory, trying multiple paths."""
    candidates = [
        Path(__file__).parent.parent / "data" / filename,
        Path("/app") / "data" / filename,
        Path("/app/code") / "data" / filename,
        Path("data") / filename,
    ]
    for p in candidates:
        if p.exists():
            return p.read_text(encoding="utf-8")
    logger.warning("Asset %s not found, using empty string", filename)
    return ""


def _build_leaderboard(summaries: List[JobSummary]) -> List[Dict[str, object]]:
    """Rank job summaries by pass_rate descending."""
    ranked = sorted(summaries, key=lambda s: s.pass_rate, reverse=True)
    return [
        {
            "rank": i + 1,
            "label": s.spec.label,
            "agent": s.spec.agent,
            "model": s.spec.model or "n/a",
            "pass_rate": f"{s.pass_rate:.1%}",
            "passed": s.passed_trials,
            "total": s.total_trials,
            "mean_reward": f"{s.mean_reward:.2f}",
        }
        for i, s in enumerate(ranked)
    ]


def _build_matrix_table(
    summaries: List[JobSummary],
) -> List[Dict[str, object]]:
    """Build an agent x task result matrix."""
    task_results: Dict[str, Dict[str, str]] = defaultdict(dict)
    all_tasks: List[str] = []

    for s in summaries:
        for trial in s.trials:
            if trial.task_name not in all_tasks:
                all_tasks.append(trial.task_name)
            icon = "PASS" if trial.success else "FAIL"
            task_results[s.spec.label][trial.task_name] = icon

    rows: List[Dict[str, object]] = []
    for label in [s.spec.label for s in summaries]:
        row: Dict[str, object] = {"label": label}
        for task in all_tasks:
            row[task] = task_results.get(label, {}).get(task, "-")
        rows.append(row)

    return rows


def _find_failing_tasks(summaries: List[JobSummary]) -> List[str]:
    """Find tasks that failed in every agent+model combo."""
    if not summaries:
        return []

    task_pass_counts: Dict[str, int] = defaultdict(int)
    task_total_counts: Dict[str, int] = defaultdict(int)

    for s in summaries:
        for trial in s.trials:
            task_total_counts[trial.task_name] += 1
            if trial.success:
                task_pass_counts[trial.task_name] += 1

    return [
        task
        for task, total in task_total_counts.items()
        if task_pass_counts.get(task, 0) == 0 and total > 0
    ]


def _render_html(report: CampaignReport, css: str, template: str) -> str:
    """Render the HTML report from template + data."""
    leaderboard_rows = ""
    for row in report.ranked:
        leaderboard_rows += (
            f"<tr>"
            f"<td>{row['rank']}</td>"
            f"<td>{html.escape(str(row['label']))}</td>"
            f"<td>{html.escape(str(row['agent']))}</td>"
            f"<td>{html.escape(str(row['model']))}</td>"
            f"<td>{row['pass_rate']}</td>"
            f"<td>{row['passed']}/{row['total']}</td>"
            f"<td>{row['mean_reward']}</td>"
            f"</tr>\n"
        )

    matrix_headers = ""
    matrix_rows_html = ""
    if report.matrix_table:
        cols = [k for k in report.matrix_table[0].keys() if k != "label"]
        matrix_headers = "".join(
            f"<th>{html.escape(c)}</th>" for c in cols
        )
        for row in report.matrix_table:
            cells = f"<td><strong>{html.escape(str(row['label']))}</strong></td>"
            for col in cols:
                val = str(row.get(col, "-"))
                cls = "pass" if val == "PASS" else "fail" if val == "FAIL" else ""
                cells += f'<td class="{cls}">{html.escape(val)}</td>'
            matrix_rows_html += f"<tr>{cells}</tr>\n"

    failing_html = ""
    if report.failing_tasks:
        failing_html = "<ul>" + "".join(
            f"<li>{html.escape(t)}</li>" for t in report.failing_tasks
        ) + "</ul>"
    else:
        failing_html = "<p>None — at least one agent passed every task.</p>"

    return template.format(
        css=css,
        total_jobs=report.total_jobs,
        total_trials=report.total_trials,
        overall_pass_rate=f"{report.overall_pass_rate:.1%}",
        leaderboard_rows=leaderboard_rows,
        matrix_headers=matrix_headers,
        matrix_rows=matrix_rows_html,
        failing_tasks_html=failing_html,
    )


@step
def build_report(
    job_summaries: Any,
) -> Tuple[
    Annotated[CampaignReport, "campaign_report"],
    Annotated[HTMLString, "report"],
]:
    """Aggregate job summaries into a campaign report and HTML visualization.

    Receives dicts (from parse_harbor_job's model_dump()) and
    reconstructs JobSummary objects for typed processing.

    Args:
        job_summaries: List of job summary dicts from parse_harbor_job.

    Returns:
        Tuple of (structured CampaignReport, rendered HTML report).
    """
    # Normalize: single dict when fan-out has only 1 element
    if isinstance(job_summaries, dict):
        job_summaries = [job_summaries]

    summaries = [JobSummary(**d) for d in job_summaries]
    ranked = _build_leaderboard(summaries)
    matrix_table = _build_matrix_table(summaries)
    failing_tasks = _find_failing_tasks(summaries)

    total_jobs = len(summaries)
    total_trials = sum(s.total_trials for s in summaries)
    total_passed = sum(s.passed_trials for s in summaries)
    overall_pass_rate = total_passed / total_trials if total_trials > 0 else 0.0

    report = CampaignReport(
        summaries=summaries,
        ranked=ranked,
        total_jobs=total_jobs,
        total_trials=total_trials,
        overall_pass_rate=overall_pass_rate,
        failing_tasks=failing_tasks,
        matrix_table=matrix_table,
    )

    log_metadata(
        metadata={
            "total_jobs": total_jobs,
            "total_trials": total_trials,
            "overall_pass_rate": overall_pass_rate,
            "failing_tasks_count": len(failing_tasks),
        }
    )

    css = _load_text_asset("report.css")
    template = _load_text_asset("report_template.html")

    if template:
        html_str = _render_html(report, css, template)
    else:
        html_str = f"<h1>Campaign Report</h1><p>{total_jobs} jobs, {overall_pass_rate:.1%} pass rate</p>"

    logger.info(
        "Campaign report: %d jobs, %d trials, %.1f%% pass rate",
        total_jobs, total_trials, overall_pass_rate * 100,
    )
    return report, HTMLString(html_str)
