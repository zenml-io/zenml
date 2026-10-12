"""HTML report rendering for the operations control tower demo."""

from html import escape


CSS = """
*{box-sizing:border-box}body{margin:0;background:#f5f7fb;color:#182b49;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1100px;margin:auto;padding:34px}.hero{background:linear-gradient(120deg,#182b49,#22566b);color:white;border-radius:24px;padding:34px 38px}.eyebrow{color:#72f0d8;text-transform:uppercase;letter-spacing:.16em;font-weight:800;font-size:11px}h1{font-size:38px;letter-spacing:-.04em;margin:10px 0 6px}.hero p{color:#d7e9ed;margin:0;max-width:720px}.date{margin-top:20px;color:#a9c8d1;font-size:12px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:20px 0}.card,.panel{background:white;border:1px solid #e4e9f0;border-radius:16px;padding:20px;box-shadow:0 4px 18px #19334b0a}.card span,.card small{display:block;color:#6c7c91;font-size:12px}.card b{display:block;font-size:27px;letter-spacing:-.04em;margin:9px 0 3px}.grid{display:grid;grid-template-columns:1.1fr .9fr;gap:20px}h2{font-size:19px;margin:0 0 5px}.sub{color:#6c7c91;font-size:13px;margin:0 0 19px}.chart{width:100%;height:auto}.chart text{font:13px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#66778d}table{border-collapse:collapse;width:100%}td{border-top:1px solid #edf0f4;padding:13px 4px;vertical-align:top}td.right{text-align:right;white-space:nowrap;font-weight:700}small{color:#6c7c91}.pill{border-radius:20px;padding:4px 8px;font-size:10px;font-weight:800;letter-spacing:.06em}.high{background:#ffe4e5;color:#bd3c48}.medium{background:#fff0d8;color:#a86613}.low{background:#e1f7f2;color:#087e70}.footer{margin-top:22px;border-top:1px solid #dce3ec;padding-top:16px;color:#77869a;font-size:11px}@media(max-width:760px){main{padding:18px}.cards,.grid{grid-template-columns:1fr 1fr}}@media(max-width:500px){.cards,.grid{grid-template-columns:1fr}h1{font-size:30px}}
"""


def _bar_chart(metrics: dict[str, float | int]) -> str:
    """Render normalized operating signals as inline SVG bars."""
    values = [
        ("Revenue", float(metrics["revenue_at_risk"]), COLORS["orange"]),
        ("Stockouts", float(metrics["stockout_risk"]), "#ef6670"),
        ("Conversion", float(metrics["conversion_rate"]), COLORS["teal"]),
        ("Readiness", float(metrics["readiness_score"]), "#5b8def"),
    ]
    bars = []
    for index, (label, value, color) in enumerate(values):
        y = 32 + index * 54
        width = max(12, min(100, value)) * 5.2
        bars.append(
            f'<text x="0" y="{y + 16}">{escape(label)}</text>'
            f'<rect x="112" y="{y}" width="520" height="24" rx="12" fill="#edf1f5"/>'
            f'<rect x="112" y="{y}" width="{width:.1f}" height="24" rx="12" fill="{color}"/>'
            f'<text x="650" y="{y + 17}" text-anchor="end" font-weight="700">{value:.1f}%</text>'
        )
    return '<svg viewBox="0 0 670 250" class="chart">' + "".join(bars) + "</svg>"


COLORS = {"teal": "#16b8a6", "orange": "#ff9f43"}


def render_control_tower(
    metrics: dict[str, float | int], alerts: list[dict[str, str | int]], run_date: str
) -> str:
    """Render a self-contained executive brief.

    Args:
        metrics: Aggregated operational health metrics.
        alerts: Prioritized synthetic operational alerts.
        run_date: Business date represented by the snapshot.

    Returns:
        Complete HTML suitable for a ZenML HTMLString artifact.
    """
    cards = [
        ("Revenue at risk", f'${float(metrics["revenue_at_risk"]):,.0f}', "synthetic exposure"),
        ("Conversion rate", f'{float(metrics["conversion_rate"]):.1f}%', "customer funnel"),
        ("Stockout risk", f'{float(metrics["stockout_risk"]):.1f}%', "next 7 days"),
        ("Readiness score", f'{float(metrics["readiness_score"]):.1f}/100', "operational pulse"),
    ]
    card_html = "".join(
        f'<article class="card"><span>{escape(label)}</span><b>{value}</b><small>{escape(unit)}</small></article>'
        for label, value, unit in cards
    )
    alert_rows = "".join(
        f'<tr><td><span class="pill {escape(str(alert["severity"]))}">{escape(str(alert["severity"]).upper())}</span></td>'
        f'<td><strong>{escape(str(alert["title"]))}</strong><br><small>{escape(str(alert["action"]))}</small></td>'
        f'<td class="right">{escape(str(alert["impact"]))}</td></tr>'
        for alert in alerts
    )
    return (
        '<!doctype html><html><head><meta charset="utf-8"><title>Orbit Operations Control Tower</title>'
        f"<style>{CSS}</style></head><body><main>"
        '<header class="hero"><div class="eyebrow">Orbit / Operations intelligence</div>'
        '<h1>Control Tower Brief</h1><p>One governed snapshot across customers, inventory, and warehouse capacity—built for the next decision, not the last dashboard.</p>'
        f'<div class="date">Synthetic demo snapshot · {escape(run_date)}</div></header>'
        f'<section class="cards">{card_html}</section>'
        '<section class="grid"><article class="panel"><h2>Signal health</h2><p class="sub">Normalized indicators make the trade-offs visible at a glance.</p>'
        f'{_bar_chart(metrics)}</article><article class="panel"><h2>Priority queue</h2><p class="sub">The three actions with the highest modeled impact.</p><table>{alert_rows}</table></article></section>'
        '<footer class="footer">Built by ZenML steps on a local stack · All data and recommendations are synthetic and for demonstration only.</footer>'
        '</main></body></html>'
    )
