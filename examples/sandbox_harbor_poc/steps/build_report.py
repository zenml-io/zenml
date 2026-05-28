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


def _combo_label(summary: JobSummary) -> str:
    """Agent+model identity a trial belongs to (the leaderboard row key)."""
    agent = summary.spec.agent
    model = summary.spec.model
    return f"{agent}/{model}" if model else agent


def _passed(summary: JobSummary) -> bool:
    """Whether a single-task trial summary passed."""
    return summary.passed_trials > 0


def _build_leaderboard(summaries: List[JobSummary]) -> List[Dict[str, object]]:
    """Rank agent+model combos by pass rate across their tasks.

    Each summary is one task; grouping by combo turns the per-task trials
    into a combo-level pass rate (tasks passed / tasks attempted).
    """
    grouped: Dict[str, List[JobSummary]] = defaultdict(list)
    for s in summaries:
        grouped[_combo_label(s)].append(s)

    rows: List[Dict[str, object]] = []
    for combo, group in grouped.items():
        total = len(group)
        passed = sum(1 for s in group if _passed(s))
        pass_rate = passed / total if total else 0.0
        mean_reward = (
            sum(s.mean_reward for s in group) / total if total else 0.0
        )
        rows.append(
            {
                "label": combo,
                "agent": group[0].spec.agent,
                "model": group[0].spec.model or "n/a",
                "pass_rate": pass_rate,
                "passed": passed,
                "total": total,
                "mean_reward": mean_reward,
            }
        )

    rows.sort(key=lambda r: r["pass_rate"], reverse=True)
    for i, row in enumerate(rows):
        row["rank"] = i + 1
        row["pass_rate"] = f"{row['pass_rate']:.1%}"
        row["mean_reward"] = f"{row['mean_reward']:.2f}"
    return rows


def _build_matrix_table(
    summaries: List[JobSummary],
) -> List[Dict[str, object]]:
    """Build a combo x task PASS/FAIL matrix keyed on spec.task_name."""
    combos: List[str] = []
    all_tasks: List[str] = []
    results: Dict[str, Dict[str, str]] = defaultdict(dict)

    for s in summaries:
        combo = _combo_label(s)
        if combo not in combos:
            combos.append(combo)
        task = s.spec.task_name
        if task not in all_tasks:
            all_tasks.append(task)
        results[combo][task] = "PASS" if _passed(s) else "FAIL"

    rows: List[Dict[str, object]] = []
    for combo in combos:
        row: Dict[str, object] = {"label": combo}
        for task in all_tasks:
            row[task] = results[combo].get(task, "-")
        rows.append(row)
    return rows


def _find_failing_tasks(summaries: List[JobSummary]) -> List[str]:
    """Find tasks that failed in every agent+model combo."""
    pass_counts: Dict[str, int] = defaultdict(int)
    total_counts: Dict[str, int] = defaultdict(int)

    for s in summaries:
        task = s.spec.task_name
        total_counts[task] += 1
        if _passed(s):
            pass_counts[task] += 1

    return [
        task
        for task, total in total_counts.items()
        if pass_counts.get(task, 0) == 0 and total > 0
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
        matrix_headers = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
        for row in report.matrix_table:
            cells = (
                f"<td><strong>{html.escape(str(row['label']))}</strong></td>"
            )
            for col in cols:
                val = str(row.get(col, "-"))
                cls = (
                    "pass"
                    if val == "PASS"
                    else "fail"
                    if val == "FAIL"
                    else ""
                )
                cells += f'<td class="{cls}">{html.escape(val)}</td>'
            matrix_rows_html += f"<tr>{cells}</tr>\n"

    failing_html = ""
    if report.failing_tasks:
        failing_html = (
            "<ul>"
            + "".join(
                f"<li>{html.escape(t)}</li>" for t in report.failing_tasks
            )
            + "</ul>"
        )
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

    # One summary == one sandboxed trial; one leaderboard row == one combo.
    total_jobs = len(ranked)
    total_trials = len(summaries)
    total_passed = sum(1 for s in summaries if _passed(s))
    overall_pass_rate = (
        total_passed / total_trials if total_trials > 0 else 0.0
    )

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
            "total_combos": total_jobs,
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
        total_jobs,
        total_trials,
        overall_pass_rate * 100,
    )
    return report, HTMLString(html_str)
