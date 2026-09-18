"""Render readable CPU qualification evidence without external assets."""

import html
import json
from typing import Any

STYLE = """
:root{color-scheme:light;--ink:#252334;--muted:#696477;--line:#e8e4ee;
--purple:#6742bc;--green:#247454;--red:#a33b45}
*{box-sizing:border-box}body{margin:0;background:#f6f5f9;color:var(--ink);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1080px;margin:auto;padding:36px 32px 28px}h1,h2,h3,p{margin:0}
.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;
font-weight:750;color:var(--purple)}h1{font-size:clamp(26px,4vw,38px);
line-height:1.15;letter-spacing:-.035em;margin:12px 0}
.lead{max-width:730px;color:var(--muted);font-size:16px}.hero{margin-bottom:28px}
.task{display:inline-block;margin-top:17px;font:12px ui-monospace,monospace;
color:#635775;background:#ede8f6;padding:7px 11px;border-radius:6px;
overflow-wrap:anywhere}.section-title{font-size:17px;letter-spacing:-.02em}
.section-note{color:var(--muted);font-size:13px;margin-top:3px}
.readiness,.cleanup{display:flex;gap:16px;align-items:flex-start;background:white;
border:1px solid var(--line);border-radius:12px;padding:20px;margin-bottom:24px}
.symbol{font-size:19px;width:34px;height:34px;display:grid;place-items:center;
flex-shrink:0;border-radius:50%;background:#eaf4ef;color:var(--green)}
.symbol.bad{background:#fbecee;color:var(--red)}.readiness p,.cleanup p{color:var(--muted);font-size:13px}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:16px 0 22px}
.card{background:white;border:1px solid var(--line);border-radius:14px;overflow:hidden}
.card-top{padding:23px 23px 18px}.card h3{font-size:20px;letter-spacing:-.025em;margin-top:9px}
.card-description{color:var(--muted);font-size:13px;min-height:41px;margin-top:6px}
.badge{display:inline-block;font-size:11px;font-weight:700;padding:4px 8px;
border-radius:5px;background:#eaf4ef;color:var(--green)}.badge.bad{background:#fbecee;color:var(--red)}
.compare{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:23px}
.label{font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);font-weight:700}
.value{font-size:21px;font-weight:650;margin-top:2px}.expected .value{color:var(--muted)}
.testbar{height:6px;display:flex;background:#eeeaf3;border-radius:6px;overflow:hidden;margin:18px 0 9px}
.testbar span{height:100%}.passed{background:#7e63b1}.failed{background:#d4b75e}
.error{background:#c1626c}.skipped{background:#b7b1bd}.test-summary{font-size:12px;color:var(--muted)}
.card-bottom{background:#fbfafc;border-top:1px solid var(--line);padding:12px 23px;
font-size:12px;color:var(--muted)}.card-bottom strong{color:var(--ink)}
.issue{margin-top:12px;padding:10px;background:#fff3f3;color:var(--red);font-size:12px;
border-radius:6px;overflow-wrap:anywhere}.cleanup{margin-bottom:28px}
.details-title{margin-bottom:12px}details{border-top:1px solid var(--line);padding:13px 0}
summary{cursor:pointer;font-weight:600;font-size:13px;list-style-position:inside}
summary span{font-weight:400;color:var(--muted);margin-left:6px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#fff;border:1px solid var(--line);
border-radius:8px;padding:16px;max-height:380px;overflow:auto;font:12px/1.6 ui-monospace,monospace;
margin:12px 0 0}dl{display:grid;grid-template-columns:140px 1fr;gap:8px 16px;font-size:12px}
dt{color:var(--muted)}dd{margin:0;overflow-wrap:anywhere}footer{font-size:12px;color:var(--muted);
margin-top:20px;padding-top:15px;border-top:1px solid var(--line)}
@media(max-width:620px){main{padding:24px 16px}.cards{grid-template-columns:1fr;gap:14px}
.card-description{min-height:0}.card-top{padding:20px}.readiness,.cleanup{padding:16px}
.summary span{display:block}dl{grid-template-columns:1fr;gap:3px}dd{margin-bottom:8px}}
"""


def _text(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _counts(grade: dict[str, Any]) -> tuple[str, str]:
    counts = grade.get("test_counts") or {}
    keys = ("total", "failure", "error", "skipped")
    if not all(type(counts.get(key)) is int for key in keys):
        return "", "Test counts unavailable"
    total, failed, errors, skipped = (counts[key] for key in keys)
    passed = total - failed - errors - skipped
    if min(total, passed, failed, errors, skipped) < 0:
        return "", "Test counts inconsistent; inspect raw evidence"
    segments = "".join(
        f'<span class="{name}" style="width:{100 * count / total:.2f}%"></span>'
        for name, count in (
            ("passed", passed),
            ("failed", failed),
            ("error", errors),
            ("skipped", skipped),
        )
        if count and total
    )
    summary = f"{passed} passed · {failed} failed · {errors} errors · {skipped} skipped"
    return f'<div class="testbar" aria-hidden="true">{segments}</div>', summary


def _card(result: dict[str, Any], reference: bool, matched: bool) -> str:
    grade = result.get("grading") or {}
    title = "Reference solution" if reference else "Untouched task"
    description = (
        "Run the known solution to check that correct work is accepted."
        if reference
        else "Leave the task unsolved to check that missing work is rejected."
    )
    expected = "Pass" if reference else "Fail"
    raw = grade.get("raw_reward")
    observed = "Pass" if raw == 1 else "Fail" if raw == 0 else "Unavailable"
    if result.get("skipped"):
        observed = "Not run"
    badge = "As expected" if matched else "Needs attention"
    bar, counts = _counts(grade)
    cleanup = "Complete" if result.get("cleanup_complete") else "Unconfirmed"
    if result.get("skipped"):
        cleanup = "Not run"
    issue = (
        result.get("error")
        or grade.get("infrastructure_error")
        or result.get("skipped")
    )
    issue_html = f'<p class="issue">{_text(issue)}</p>' if issue else ""
    if not matched and not issue:
        issue_html = '<p class="issue">The result, execution or cleanup did not meet the fixture contract. Inspect the evidence below.</p>'
    return f"""<article class="card"><div class="card-top">
<span class="badge{"" if matched else " bad"}">{badge}</span><h3>{title}</h3>
<p class="card-description">{description}</p><div class="compare">
<div class="expected"><div class="label">Expected</div><div class="value">{expected}</div></div>
<div><div class="label">Observed test outcome</div><div class="value">{observed}</div></div></div>
{bar}<p class="test-summary">{_text(counts)}</p>{issue_html}</div>
<div class="card-bottom">Sandbox cleanup <strong>{cleanup}</strong></div></article>"""


def render_qualification_report(
    results: dict[str, Any], reference_passed: bool, noop_passed: bool
) -> str:
    """Render outcome-first qualification evidence while retaining full raw data.

    Args:
        results: Unmodified structured qualification results.
        reference_passed: Existing reference fixture contract result.
        noop_passed: Existing no-op fixture contract result.

    Returns:
        Escaped, responsive HTML with inline styles and no external resources.
    """
    initial, reference, noop = (
        results[key] for key in ("initial", "reference", "noop")
    )
    grade = initial.get("grading") or {}
    ready = bool(
        grade.get("audited_valid")
        and not grade.get("infrastructure_error")
        and initial.get("cleanup_complete")
    )
    passed = ready and reference_passed and noop_passed
    title = (
        "Sandbox qualification passed"
        if passed
        else "Qualification needs attention"
    )
    lead = (
        "The known solution passed and the untouched task failed as expected. The CPU environment is ready for model evaluation."
        if passed
        else "One or more qualification checks need review before model evaluation. Check readiness, fixture outcomes and cleanup below."
    )
    task = initial.get("task") or {}
    _, initial_counts = _counts(grade)
    initial_title = (
        "Initial environment ready"
        if ready
        else "Initial environment not qualified"
    )
    initial_note = f"{initial_counts}. Setup checks validate the starting environment; they do not solve the task."
    initial_issue = initial.get("error") or grade.get("infrastructure_error")
    if initial_issue:
        initial_note += " " + str(initial_issue)
    cleanup_values = [
        item.get("cleanup_complete") is True
        for item in (initial, reference, noop)
    ]
    all_clean = all(cleanup_values)
    cleanup_title = (
        "Cleanup confirmed" if all_clean else "Cleanup needs review"
    )
    cleanup_note = " · ".join(
        name
        + ": "
        + (
            "not run"
            if item.get("skipped")
            else "complete"
            if clean
            else "unconfirmed"
        )
        for name, item, clean in zip(
            ("Initial checks", "Reference", "Untouched task"),
            (initial, reference, noop),
            cleanup_values,
        )
    )
    logs = "".join(
        f"<details><summary>{name}<span>Verifier output</span></summary><pre>{_text((item.get('grading') or {}).get('verifier_output') or 'No verifier output recorded.')}</pre></details>"
        for name, item in (
            ("Initial environment", initial),
            ("Reference solution", reference),
            ("Untouched task", noop),
        )
    )
    provenance = "".join(
        f"<dt>{label}</dt><dd>{_text(value or 'Not recorded')}</dd>"
        for label, value in (
            ("Task", task.get("task_id")),
            ("Dataset revision", task.get("dataset_revision")),
            (
                "Task image",
                task.get("image_ref") or task.get("qualified_image_id"),
            ),
        )
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{STYLE}</style></head><body><main>
<header class="hero"><p class="eyebrow">ZenML · Endless Terminals</p><h1>{title}</h1>
<p class="lead">{lead}</p><span class="task">{_text(task.get("task_id") or "Task identity unavailable")}</span></header>
<section class="readiness" aria-label="Initial readiness"><span class="symbol{"" if ready else " bad"}" aria-hidden="true">{"✓" if ready else "!"}</span>
<div><h2 class="section-title">{initial_title}</h2><p>{_text(initial_note)}</p></div></section>
<section aria-label="Fixture comparison"><h2 class="section-title">Does the grader distinguish solved from unsolved?</h2>
<p class="section-note">Both outcomes are required. An untouched-task failure is the expected result.</p>
<div class="cards">{_card(reference, True, reference_passed)}{_card(noop, False, noop_passed)}</div></section>
<section class="cleanup"><span class="symbol{"" if all_clean else " bad"}" aria-hidden="true">{"✓" if all_clean else "!"}</span>
<div><h2 class="section-title">{cleanup_title}</h2><p>{_text(cleanup_note)}</p></div></section>
<section aria-label="Supporting evidence"><h2 class="section-title details-title">Evidence &amp; provenance</h2>
{logs}<details><summary>Task provenance<span>Pinned dataset and image</span></summary><dl>{provenance}</dl></details>
<details><summary>Full structured evidence<span>Results, logs, hashes and runtime identities</span></summary>
<pre>{_text(json.dumps(results, indent=2))}</pre></details></section>
<footer>CPU Kubernetes sandbox qualification · Scripted fixtures · No model inference or training.<br>
This report checks the evaluation environment. It does not measure model quality or learning.</footer>
</main></body></html>"""
