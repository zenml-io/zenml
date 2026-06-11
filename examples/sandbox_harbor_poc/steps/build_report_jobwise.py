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
"""Shape A report: aggregate job-wise summaries (one combo = many trials).

Each JobSummary here covers a whole ``(agent, model)`` Harbor job, so it holds
many TrialResults. We rank combos by their internal pass rate and build the
agent x task matrix from each combo's trials. The HTML rendering is shared with
the shape-B ``build_report``.
"""

import logging
from collections import defaultdict
from typing import Annotated, Any, Dict, List, Tuple

from models.harbor_models import CampaignReport, JobSummary

from steps.build_report import _load_text_asset, _render_html
from zenml import log_metadata, step
from zenml.types import HTMLString

logger = logging.getLogger(__name__)


def _combo(summary: JobSummary) -> str:
    """Agent+model identity for a job-wise summary."""
    agent = summary.spec.agent
    model = summary.spec.model
    return f"{agent}/{model}" if model else agent


@step
def build_report_jobwise(
    job_summaries: Any,
) -> Tuple[
    Annotated[CampaignReport, "campaign_report"],
    Annotated[HTMLString, "report"],
]:
    """Aggregate per-combo Harbor jobs into a campaign report + HTML.

    Args:
        job_summaries: List of job summary dicts (one per agent/model combo,
            each covering many trials).

    Returns:
        Tuple of (structured CampaignReport, rendered HTML report).
    """
    if isinstance(job_summaries, dict):
        job_summaries = [job_summaries]
    summaries = [JobSummary(**d) for d in job_summaries]

    # Leaderboard: one row per combo, ranked by the combo's own pass rate.
    ranked: List[Dict[str, object]] = []
    for s in summaries:
        ranked.append(
            {
                "label": _combo(s),
                "agent": s.spec.agent,
                "model": s.spec.model or "n/a",
                "pass_rate": s.pass_rate,
                "passed": s.passed_trials,
                "total": s.total_trials,
                "mean_reward": s.mean_reward,
            }
        )
    ranked.sort(key=lambda r: r["pass_rate"], reverse=True)
    for i, row in enumerate(ranked):
        row["rank"] = i + 1
        row["pass_rate"] = f"{row['pass_rate']:.1%}"
        row["mean_reward"] = f"{row['mean_reward']:.2f}"

    # Matrix: combo x task, from each combo's per-trial results.
    combos: List[str] = []
    all_tasks: List[str] = []
    results: Dict[str, Dict[str, str]] = defaultdict(dict)
    pass_counts: Dict[str, int] = defaultdict(int)
    total_counts: Dict[str, int] = defaultdict(int)
    for s in summaries:
        combo = _combo(s)
        if combo not in combos:
            combos.append(combo)
        for trial in s.trials:
            if trial.task_name not in all_tasks:
                all_tasks.append(trial.task_name)
            results[combo][trial.task_name] = (
                "PASS" if trial.success else "FAIL"
            )
            total_counts[trial.task_name] += 1
            if trial.success:
                pass_counts[trial.task_name] += 1

    matrix_table: List[Dict[str, object]] = []
    for combo in combos:
        row: Dict[str, object] = {"label": combo}
        for task in all_tasks:
            row[task] = results[combo].get(task, "-")
        matrix_table.append(row)

    failing_tasks = [
        task
        for task, total in total_counts.items()
        if pass_counts.get(task, 0) == 0 and total > 0
    ]

    total_trials = sum(s.total_trials for s in summaries)
    total_passed = sum(s.passed_trials for s in summaries)
    overall_pass_rate = (
        total_passed / total_trials if total_trials > 0 else 0.0
    )

    report = CampaignReport(
        summaries=summaries,
        ranked=ranked,
        total_jobs=len(summaries),
        total_trials=total_trials,
        overall_pass_rate=overall_pass_rate,
        failing_tasks=failing_tasks,
        matrix_table=matrix_table,
    )
    log_metadata(
        metadata={
            "total_combos": len(summaries),
            "total_trials": total_trials,
            "overall_pass_rate": overall_pass_rate,
            "failing_tasks_count": len(failing_tasks),
        }
    )

    css = _load_text_asset("report.css")
    template = _load_text_asset("report_template.html")
    html_str = (
        _render_html(report, css, template)
        if template
        else f"<h1>Campaign Report</h1><p>{overall_pass_rate:.1%} pass</p>"
    )
    logger.info(
        "Job-wise report: %d combo(s), %d trials, %.1f%% pass rate",
        len(summaries),
        total_trials,
        overall_pass_rate * 100,
    )
    return report, HTMLString(html_str)
