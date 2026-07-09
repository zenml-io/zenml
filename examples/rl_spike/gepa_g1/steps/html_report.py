"""Self-contained HTML artifact: how the cheatsheet improved, at a glance.

Returns a zenml HTMLString so the Pro dashboard renders it inline. The
chart is hand-built SVG (no external JS/CSS — the dashboard iframe must
render it offline): a step line of best-score-so-far in candidate
discovery order, with each candidate's own score as a dot. Palette is the
dataviz reference pair (blue/aqua), validated for both light and dark
surfaces; the tables double as the accessibility table-view.
"""

import html
from typing import Annotated, Any, Dict, List, Tuple

from zenml import step
from zenml.types import HTMLString

CHART_W, CHART_H = 720, 300
MARGIN_L, MARGIN_R, MARGIN_T, MARGIN_B = 56, 24, 24, 40
PLOT_W = CHART_W - MARGIN_L - MARGIN_R
PLOT_H = CHART_H - MARGIN_T - MARGIN_B


def _xy(index: int, count: int, score: float) -> Tuple[float, float]:
    """Map (candidate index, score) to SVG plot coordinates."""
    x = MARGIN_L + (index / max(count - 1, 1)) * PLOT_W
    y = MARGIN_T + (1.0 - score) * PLOT_H
    return round(x, 1), round(y, 1)


def _chart_svg(aggregate: List[float], parents: List[Any]) -> str:
    """Best-so-far step line (blue) + per-candidate dots (aqua)."""
    count = len(aggregate)
    best_so_far = []
    best = 0.0
    for score in aggregate:
        best = max(best, score)
        best_so_far.append(best)

    grid = "".join(
        f'<line x1="{MARGIN_L}" y1="{_xy(0, count, tick)[1]}" '
        f'x2="{MARGIN_L + PLOT_W}" y2="{_xy(0, count, tick)[1]}" '
        f'class="grid"/>'
        f'<text x="{MARGIN_L - 8}" y="{_xy(0, count, tick)[1] + 4}" '
        f'class="axis" text-anchor="end">{tick:.2f}</text>'
        for tick in (0.0, 0.25, 0.5, 0.75, 1.0)
    )
    points = [_xy(i, count, s) for i, s in enumerate(best_so_far)]
    path = f"M {points[0][0]} {points[0][1]} " + " ".join(
        f"H {x} V {y}" if y != prev_y else f"H {x}"
        for (x, y), (_, prev_y) in zip(points[1:], points[:-1])
    )
    dots = "".join(
        f'<circle cx="{_xy(i, count, s)[0]}" cy="{_xy(i, count, s)[1]}" '
        f'r="5" class="dot" data-tip="candidate #{i} — score '
        f"{s:.3f}, parent "
        f'{html.escape(str(parents[i]))}"/>'
        for i, s in enumerate(aggregate)
    )
    x_labels = "".join(
        f'<text x="{_xy(i, count, 0)[0]}" y="{CHART_H - 14}" class="axis" '
        f'text-anchor="middle">#{i}</text>'
        for i in range(count)
    )
    seed_x, seed_y = _xy(0, count, aggregate[0])
    best_idx = max(range(count), key=lambda i: aggregate[i])
    best_x, best_y = _xy(best_idx, count, aggregate[best_idx])
    labels = (
        f'<text x="{seed_x + 8}" y="{seed_y + 16}" class="label">'
        f"seed {aggregate[0]:.3f}</text>"
        f'<text x="{best_x - 8}" y="{best_y - 10}" class="label" '
        f'text-anchor="end">best {aggregate[best_idx]:.3f}</text>'
    )
    return (
        f'<svg viewBox="0 0 {CHART_W} {CHART_H}" role="img" '
        f'aria-label="Best cheatsheet score by candidate">'
        f"{grid}"
        f'<path d="{path}" class="line" fill="none"/>'
        f"{dots}{labels}{x_labels}"
        f'<text x="{MARGIN_L + PLOT_W / 2}" y="{CHART_H - 2}" class="axis" '
        f'text-anchor="middle">candidate (discovery order)</text>'
        "</svg>"
    )


def _tree_rows(gepa_result: Dict[str, Any], task_ids: List[str]) -> str:
    """Candidate-tree table body rows."""
    frontier = gepa_result["per_val_instance_best_candidates"]
    rows = []
    for index, _ in enumerate(gepa_result["candidates"]):
        wins = [
            task_ids[int(val_id)]
            for val_id, front in frontier.items()
            if index in front and int(val_id) < len(task_ids)
        ]
        parent = gepa_result["parents"][index]
        parent_label = (
            ", ".join(str(p) for p in parent)
            if isinstance(parent, list)
            else str(parent)
        )
        rows.append(
            f"<tr><td>#{index}</td><td>{html.escape(parent_label)}</td>"
            f"<td>{gepa_result['val_aggregate_scores'][index]:.3f}</td>"
            f"<td>{html.escape(', '.join(wins) or '—')}</td></tr>"
        )
    return "".join(rows)


@step
def build_html_report(
    gepa_result: Dict[str, Any], tasks: List[Dict[str, Any]]
) -> Annotated[HTMLString, "gepa_evolution_html"]:
    """Render the evolution story as a dashboard-embeddable HTML page.

    Args:
        gepa_result: Serialized GEPAResult from evolve_prompt.
        tasks: Task records (for column labels).

    Returns:
        Self-contained HTML with hero numbers, the score-progression
        chart, the candidate tree, and the best evolved cheatsheet.
    """
    aggregate = gepa_result["val_aggregate_scores"]
    best_idx = gepa_result["best_idx"]
    task_ids = [task["id"] for task in tasks]
    usage = gepa_result.get("usage", {})
    seed_score, best_score = aggregate[0], aggregate[best_idx]
    lift = (best_score - seed_score) / seed_score * 100 if seed_score else 0.0

    heroes = "".join(
        f'<div class="hero"><div class="hero-num">{value}</div>'
        f'<div class="hero-cap">{caption}</div></div>'
        for value, caption in (
            (f"{seed_score:.3f}", "seed cheatsheet score"),
            (f"{best_score:.3f}", f"best (candidate #{best_idx})"),
            (f"+{lift:.0f}%", "improvement"),
            (str(len(aggregate)), "candidates explored"),
            (
                str(gepa_result.get("total_metric_calls", "?")),
                "sandbox evaluations",
            ),
        )
    )
    usage_line = " · ".join(
        f"{role}: {counters['calls']} calls, "
        f"{counters['prompt_tokens'] + counters['completion_tokens']:,} tokens"
        for role, counters in usage.items()
    )
    best_cheatsheet = html.escape(
        gepa_result["candidates"][best_idx]["cheatsheet"]
    )

    return HTMLString(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>GEPA cheatsheet evolution</title>
<style>
.viz-root {{
  --surface-1: #fcfcfb; --text-primary: #0b0b0b; --text-secondary: #52514e;
  --grid: #e4e3df; --series-1: #2a78d6; --series-2: #1baf7a;
  background: var(--surface-1); color: var(--text-primary);
  font: 14px/1.5 system-ui, sans-serif; max-width: 780px;
  margin: 0 auto; padding: 16px;
}}
@media (prefers-color-scheme: dark) {{
  .viz-root {{
    --surface-1: #1a1a19; --text-primary: #ffffff;
    --text-secondary: #c3c2b7; --grid: #33332f;
    --series-1: #3987e5; --series-2: #199e70;
  }}
}}
.heroes {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 12px 0 20px; }}
.hero-num {{ font-size: 26px; font-weight: 650; }}
.hero-cap {{ color: var(--text-secondary); font-size: 12px; }}
.grid {{ stroke: var(--grid); stroke-width: 1; }}
.axis, .label {{ fill: var(--text-secondary); font-size: 11px; }}
.label {{ fill: var(--text-primary); font-weight: 600; }}
.line {{ stroke: var(--series-1); stroke-width: 2; }}
.dot {{ fill: var(--series-2); stroke: var(--surface-1); stroke-width: 2; }}
.dot:hover {{ r: 7; }}
.legend {{ color: var(--text-secondary); font-size: 12px; margin: 4px 0 16px; }}
.swatch {{ display: inline-block; width: 10px; height: 10px;
  border-radius: 2px; margin: 0 4px 0 12px; }}
table {{ border-collapse: collapse; margin: 8px 0 20px; width: 100%; }}
th, td {{ text-align: left; padding: 4px 10px;
  border-bottom: 1px solid var(--grid); font-size: 13px; }}
th {{ color: var(--text-secondary); font-weight: 600; }}
#tip {{ position: fixed; display: none; background: var(--text-primary);
  color: var(--surface-1); padding: 4px 8px; border-radius: 4px;
  font-size: 12px; pointer-events: none; z-index: 10; }}
details {{ margin: 12px 0; }} pre {{ white-space: pre-wrap; font-size: 12px;
  background: color-mix(in srgb, var(--grid) 40%, var(--surface-1));
  padding: 12px; border-radius: 6px; }}
h1 {{ font-size: 20px; }} h2 {{ font-size: 15px; margin-top: 24px; }}
p {{ color: var(--text-secondary); }}
</style></head><body><div class="viz-root">
<h1>GEPA cheatsheet evolution</h1>
<p>Starting from a one-line prompt, GEPA evolved a ZenML-API cheatsheet
using only the sandbox scorer's feedback: each round, gpt-5-nano wrote
pipelines under a candidate cheatsheet, the sandbox scored them, and
gpt-5.4 read the failures and proposed a rewrite. Accepted rewrites are
the dots that push the blue line up.</p>
<div class="heroes">{heroes}</div>
{_chart_svg(aggregate, gepa_result["parents"])}
<div class="legend">
  <span class="swatch" style="background:var(--series-1)"></span>best score so far
  <span class="swatch" style="background:var(--series-2)"></span>candidate score
</div>
<h2>Candidate tree</h2>
<p>GEPA keeps a Pareto <em>frontier</em>, not one winner: "best on" lists
the tasks each candidate still wins. The seed survives on the frontier for
tasks the evolution traded away.</p>
<table><thead><tr><th>candidate</th><th>parent</th><th>mean score</th>
<th>best on</th></tr></thead><tbody>{_tree_rows(gepa_result, task_ids)}</tbody></table>
<p class="legend">API usage — {usage_line}</p>
<details><summary>Best evolved cheatsheet (candidate #{best_idx})</summary>
<pre>{best_cheatsheet}</pre></details>
<div id="tip"></div>
<script>
const tip = document.getElementById('tip');
for (const dot of document.querySelectorAll('.dot')) {{
  dot.addEventListener('mousemove', e => {{
    tip.textContent = dot.dataset.tip;
    tip.style.left = (e.clientX + 12) + 'px';
    tip.style.top = (e.clientY - 10) + 'px';
    tip.style.display = 'block';
  }});
  dot.addEventListener('mouseleave', () => tip.style.display = 'none');
}}
</script>
</div></body></html>""")
