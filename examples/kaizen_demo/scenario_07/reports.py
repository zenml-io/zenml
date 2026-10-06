# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Self-contained visual reports for historical bike sharing demand."""

import math
from html import escape
from urllib.parse import urlsplit, urlunsplit

import pandas as pd

TEAL = "#087f83"
ORANGE = "#dd7946"
NAVY = "#20394e"
GRAY = "#a5aeb7"

CSS = """
*{box-sizing:border-box}body{margin:0;background:#f3f5f5;color:#20394e;
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1280px;margin:auto;padding:32px 36px 40px}
.hero{background:#17384a;color:#fff;border-radius:20px;padding:32px 36px;
position:relative;overflow:hidden}.hero:after{content:"";position:absolute;
width:230px;height:230px;border:44px solid #24505d;border-radius:50%;
right:-75px;top:-96px;pointer-events:none}.eyebrow{text-transform:uppercase;
letter-spacing:.15em;font-size:11px;font-weight:750;color:#ace0d8}
h1{font-size:34px;line-height:1.16;letter-spacing:-.035em;margin:12px 0;
position:relative;z-index:1}h2{font-size:19px;line-height:1.3;margin:0 0 7px;
letter-spacing:-.02em}h3{font-size:15px;margin:0 0 7px}
.hero p{color:#cee0e6;max-width:820px;margin:0;position:relative;z-index:1}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:22px 0}
.metric{background:white;border:1px solid #e0e7e9;border-radius:14px;padding:20px}
.metric-label{font-size:12px;font-weight:650;color:#617482}
.metric-value{font-size:31px;font-weight:720;line-height:1.2;
letter-spacing:-.04em;margin:9px 0 5px}.metric-unit{font-size:11px;
color:#617482}.panel{background:white;border:1px solid #e0e7e9;
border-radius:16px;padding:25px 26px;margin-bottom:20px;min-width:0}
.description{font-size:13px;color:#617482;margin:0 0 18px;max-width:930px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.grid>.panel{margin-bottom:0}.grid{margin-bottom:20px}
.chart{width:100%;height:auto;display:block;overflow:visible}
.chart text{font-family:inherit;fill:#617482;font-size:13px}
.chart .axis-title{font-size:12px;fill:#617482}
.legend{display:flex;gap:20px;flex-wrap:wrap;font-size:12px;color:#617482;
margin:12px 0 0}.legend span{display:inline-flex;align-items:center;gap:7px}
.swatch{width:18px;height:3px;display:inline-block;border-radius:2px}
.note{border-left:3px solid #087f83;background:#eef7f5;border-radius:0 9px 9px 0;
padding:13px 17px;font-size:13px;margin:20px 0;color:#345968}
.insights{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}
.insights p{font-size:13px;color:#617482;margin:0}
.provenance{border-top:1px solid #d9e2e5;padding-top:20px;margin-top:28px;
font-size:11px;color:#617482}.provenance h2{font-size:13px;color:#345968}
.provenance dl{display:grid;grid-template-columns:150px 1fr;gap:5px 12px;
margin:10px 0 14px}.provenance dt{font-weight:650}.provenance dd{margin:0;
overflow-wrap:anywhere}.provenance a{color:#087f83}code{font-size:11px}
.empty{padding:42px;color:#617482;text-align:center;background:#f8fafb;
border-radius:10px}svg [tabindex]:focus{outline:2px solid #dd7946}
@media(max-width:850px){main{padding:18px}.hero{padding:26px}.cards{
grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}
.insights{grid-template-columns:1fr}.panel{padding:20px}h1{font-size:28px}}
@media(max-width:440px){.cards{gap:10px}.metric{padding:15px}
.metric-value{font-size:25px}.provenance dl{grid-template-columns:1fr}}
@media print{body{background:white}main{padding:0}.panel,.metric,.hero{
break-inside:avoid}.hero{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""


def _format(value: float, digits: int = 0) -> str:
    if not math.isfinite(float(value)):
        return "Not available"
    return f"{value:,.{digits}f}"


def _cards(items: list[tuple[str, str, str]]) -> str:
    return (
        '<section class="cards" aria-label="Key measurements">'
        + "".join(
            '<article class="metric">'
            f'<div class="metric-label">{escape(label)}</div>'
            f'<div class="metric-value">{escape(value)}</div>'
            f'<div class="metric-unit">{escape(unit)}</div></article>'
            for label, value, unit in items
        )
        + "</section>"
    )


def _panel(title: str, description: str, content: str) -> str:
    return (
        '<section class="panel">'
        f"<h2>{escape(title)}</h2>"
        f'<p class="description">{escape(description)}</p>{content}</section>'
    )


def _legend(series: list[tuple[str, list[float], str]]) -> str:
    return (
        '<div class="legend">'
        + "".join(
            f'<span><i class="swatch" style="background:{color}"></i>'
            f"{escape(label)}</span>"
            for label, _, color in series
        )
        + "</div>"
    )


def _svg(title: str, content: str, width: int, height: int) -> str:
    return (
        f'<svg class="chart" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{escape(title, quote=True)}">'
        f"<title>{escape(title)}</title>{content}</svg>"
    )


def _line_chart(
    labels: list[str], series: list[tuple[str, list[float], str]], title: str
) -> str:
    width, height = 760, 310
    left, right, top, bottom = 64, 20, 28, 42
    plot_width = width - left - right
    plot_height = height - top - bottom
    maximum = max(
        (max(values, default=0) for _, values, _ in series), default=0
    )
    ceiling = max(maximum * 1.12, 1)
    parts = ['<text class="axis-title" x="64" y="14">Rentals / hour</text>']
    for tick in range(5):
        y = top + plot_height * tick / 4
        value = ceiling * (1 - tick / 4)
        parts.append(
            f'<path d="M{left},{y:.1f}H{width - right}" stroke="#e6edef"/>'
            f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end">'
            f"{_format(value)}</text>"
        )
    denominator = max(len(labels) - 1, 1)
    indices = sorted({round(i * denominator / 6) for i in range(7)})
    for index in indices:
        if index < len(labels):
            x = left + index / denominator * plot_width
            parts.append(
                f'<text x="{x:.1f}" y="{height - 13}" text-anchor="middle">'
                f"{escape(labels[index])}</text>"
            )
    for name, values, color in series:
        coordinates = [
            (
                left + index / denominator * plot_width,
                top + plot_height * (1 - float(value) / ceiling),
            )
            for index, value in enumerate(values)
        ]
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in coordinates)
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" '
            'stroke-width="2.5" stroke-linejoin="round"/>'
        )
        for index, (x, y) in enumerate(coordinates):
            tooltip = f"{labels[index]} · {name}: {_format(values[index], 1)} rentals/hour"
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{color}" '
                f'fill-opacity="0" tabindex="0"><title>{escape(tooltip)}</title></circle>'
            )
    return _svg(title, "".join(parts), width, height) + _legend(series)


def _bars(
    labels: list[str],
    series: list[tuple[str, list[float], str]],
    title: str,
    unit: str,
) -> str:
    width, height = 760, 310
    left, right, top, bottom = 64, 20, 28, 42
    all_values = [float(value) for _, values, _ in series for value in values]
    lower = min(min(all_values, default=0), 0)
    upper = max(max(all_values, default=1), 1)
    span = upper - lower
    lower = lower - span * 0.08 if lower else 0
    upper += span * 0.12
    chart_height = height - top - bottom

    def position(value: float) -> float:
        return top + (upper - value) / (upper - lower) * chart_height

    parts = [f'<text class="axis-title" x="64" y="14">{escape(unit)}</text>']
    for tick in range(5):
        value = lower + (upper - lower) * tick / 4
        y = position(value)
        parts.append(
            f'<path d="M{left},{y:.1f}H{width - right}" stroke="#e6edef"/>'
            f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end">{_format(value)}</text>'
        )
    group_width = (width - left - right) / max(len(labels), 1)
    bar_width = group_width * 0.72 / max(len(series), 1)
    zero = position(0)
    parts.append(
        f'<path d="M{left},{zero:.1f}H{width - right}" stroke="#adbdc5"/>'
    )
    for index, label in enumerate(labels):
        group_x = left + index * group_width
        parts.append(
            f'<text x="{group_x + group_width / 2:.1f}" y="{height - 13}" '
            f'text-anchor="middle">{escape(label)}</text>'
        )
        for offset, (name, values, color) in enumerate(series):
            value = float(values[index])
            x = group_x + group_width * 0.14 + offset * bar_width
            y = position(value)
            tooltip = f"{label} · {name}: {_format(value, 1)} {unit.lower()}"
            parts.append(
                f'<rect x="{x:.1f}" y="{min(y, zero):.1f}" width="{bar_width:.1f}" '
                f'height="{max(abs(zero - y), 0.5):.1f}" fill="{color}" rx="2" '
                f'tabindex="0"><title>{escape(tooltip)}</title></rect>'
            )
    return _svg(title, "".join(parts), width, height) + _legend(series)


def _heatmap(data: pd.DataFrame) -> str:
    means = data.groupby(["weekday", "hr"])["cnt"].mean()
    maximum = max(float(means.max()), 1)
    weekdays = [
        (1, "Monday"),
        (2, "Tuesday"),
        (3, "Wednesday"),
        (4, "Thursday"),
        (5, "Friday"),
        (6, "Saturday"),
        (0, "Sunday"),
    ]
    parts = []
    for hour in range(24):
        parts.append(
            f'<text x="{119 + hour * 38}" y="20" text-anchor="middle">{hour:02d}</text>'
        )
    for row, (weekday, name) in enumerate(weekdays):
        parts.append(
            f'<text x="91" y="{56 + row * 35}" text-anchor="end">{name}</text>'
        )
        for hour in range(24):
            value = means.get((weekday, hour))
            if value is None or pd.isna(value):
                color, tooltip = (
                    "#edf0f1",
                    f"{name} {hour:02d}:00: no observations",
                )
            else:
                ratio = math.sqrt(float(value) / maximum)
                start, end = (225, 243, 238), (8, 112, 121)
                rgb = [round(a + (b - a) * ratio) for a, b in zip(start, end)]
                color = "#" + "".join(f"{component:02x}" for component in rgb)
                tooltip = f"{name} {hour:02d}:00: {_format(value, 1)} rentals/hour on average"
            parts.append(
                f'<rect x="{102 + hour * 38}" y="{34 + row * 35}" width="34" height="30" '
                f'rx="4" fill="{color}" tabindex="0"><title>{escape(tooltip)}</title></rect>'
            )
    parts.append(
        '<text x="102" y="304">Hour of day · darker cells indicate more demand</text>'
    )
    return _svg(
        "Average hourly rentals by weekday and hour", "".join(parts), 1040, 325
    )


def _importance_chart(importance: pd.DataFrame) -> str:
    if importance.empty:
        return '<p class="empty">No permutation importance measurements are available.</p>'
    rows = importance.sort_values("importance", ascending=False).head(8)
    low = min(float(rows["importance"].min()), 0)
    high = max(float(rows["importance"].max()), 0.01)
    span = high - low
    width, left, right = 760, 186, 80
    height = len(rows) * 35 + 65
    scale = (width - left - right) / span
    zero = left - low * scale
    parts = [f'<path d="M{zero:.1f},16V{height - 35}" stroke="#ccd8dd"/>']
    for index, (_, row) in enumerate(rows.iterrows()):
        value = float(row["importance"])
        end = zero + value * scale
        y = 21 + index * 35
        name = str(row["feature"]).replace("_", " ")
        parts.append(
            f'<text x="{left - 12}" y="{y + 17}" text-anchor="end">{escape(name)}</text>'
            f'<rect x="{min(zero, end):.1f}" y="{y}" width="{max(abs(end - zero), 0.5):.1f}" '
            f'height="24" rx="3" fill="{TEAL if value >= 0 else ORANGE}" tabindex="0">'
            f"<title>{escape(name)}: {_format(value, 2)} rentals/hour MAE change</title></rect>"
            f'<text x="{end + 8:.1f}" y="{y + 17}">{_format(value, 2)}</text>'
        )
    parts.append(
        f'<text x="{left}" y="{height - 8}">Change in MAE · rentals / hour</text>'
    )
    return _svg(
        "Permutation feature importance on held-out observations",
        "".join(parts),
        width,
        height,
    )


def _provenance(provenance: dict) -> str:
    fields = [
        ("dataset_name", "Dataset"),
        ("source_uri", "Source"),
        ("source_artifact_id", "Source artifact UUID"),
        ("dataset_version", "Dataset version"),
        ("sha256", "Dataset SHA-256"),
        ("training_run_id", "Training run UUID"),
        ("model_version", "Model version"),
        ("model_artifact_id", "Model artifact UUID"),
    ]
    rows = []
    for key, label in fields:
        value = provenance.get(key)
        if value is None or value == "":
            continue
        value = str(value)
        if key == "source_uri":
            parts = urlsplit(value)
            value = urlunsplit(
                (
                    parts.scheme,
                    parts.netloc.rsplit("@", 1)[-1],
                    parts.path,
                    "",
                    "",
                )
            )
        rows.append(f"<dt>{escape(label)}</dt><dd>{escape(value)}</dd>")
    return (
        '<footer class="provenance"><h2>Data &amp; model provenance</h2>'
        f"<dl>{''.join(rows)}</dl><p>Historical observations from the "
        '<a href="https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset">'
        "UCI Bike Sharing Dataset</a>, contributed by Hadi Fanaee-T; "
        "Capital Bikeshare records, licensed under CC BY 4.0. "
        "Weather inputs describe observed historical conditions, not weather forecasts. "
        "All rental counts cover the recorded observations only.</p></footer>"
    )


def _document(title: str, subtitle: str, body: str, provenance: dict) -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{escape(title)}</title><style>{CSS}</style></head><body><main>"
        '<header class="hero"><div class="eyebrow">Bike sharing · Demand intelligence</div>'
        f"<h1>{escape(title)}</h1><p>{escape(subtitle)}</p></header>"
        f"{body}{_provenance(provenance)}</main></body></html>"
    )


def render_demand_explorer(data: pd.DataFrame, provenance: dict) -> str:
    """Render observed hourly demand patterns and dataset provenance.

    Args:
        data: UCI hourly records with timestamp, cnt, hr, weekday, workingday,
            and weathersit columns.
        provenance: Available dataset and source artifact identifiers.

    Returns:
        A self-contained HTML document with accessible SVG charts.

    Raises:
        ValueError: If no hourly observations are supplied.
    """
    if data.empty:
        raise ValueError("Demand exploration requires hourly observations.")
    data = data.copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"])
    hourly = data.groupby("hr")["cnt"].mean()
    peak = int(hourly.idxmax())
    cards = _cards(
        [
            (
                "Recorded rentals",
                _format(data["cnt"].sum()),
                "Across the full source dataset",
            ),
            (
                "Hourly observations",
                _format(len(data)),
                "Each row describes one recorded hour",
            ),
            (
                "Average demand",
                _format(data["cnt"].mean(), 1),
                "Rentals per recorded hour",
            ),
            (
                "Busiest hour",
                f"{peak:02d}:00",
                f"{_format(hourly.loc[peak], 1)} rentals/hour on average",
            ),
        ]
    )
    heatmap = _panel(
        "The weekly rhythm",
        "Average rentals per recorded hour. Hover or focus a cell for its exact value. Unobserved hours are shown in gray.",
        _heatmap(data),
    )
    hours = [f"{hour:02d}" for hour in range(24)]
    day_series = []
    for value, name, color in [
        (1, "Working day", TEAL),
        (0, "Weekend / holiday", ORANGE),
    ]:
        means = (
            data.loc[data["workingday"] == value]
            .groupby("hr")["cnt"]
            .mean()
            .reindex(range(24))
        )
        if means.notna().all():
            day_series.append((name, means.astype(float).tolist(), color))
    monthly = (
        data.groupby(data["timestamp"].dt.month)["cnt"].mean().sort_index()
    )
    months = [
        pd.Timestamp(2000, int(month), 1).strftime("%b")
        for month in monthly.index
    ]
    patterns = '<div class="grid">' + _panel(
        "Two shapes of a day",
        "Compare working days with weekends and holidays. Values average the available observations.",
        _line_chart(hours, day_series, "Demand by hour and type of day"),
    )
    patterns += (
        _panel(
            "The seasonal rhythm",
            "Mean hourly demand by calendar month, combining the recorded years.",
            _line_chart(
                months,
                [("Observed mean", monthly.tolist(), TEAL)],
                "Average demand by calendar month",
            ),
        )
        + "</div>"
    )
    weather = data.groupby("weathersit")["cnt"].mean().sort_index()
    names = {
        1: "Clear",
        2: "Mist / clouds",
        3: "Light rain / snow",
        4: "Heavy rain / snow",
    }
    weather_labels = [
        names.get(int(code), f"Weather {code}") for code in weather.index
    ]
    weather_panel = _panel(
        "Demand and observed weather",
        "These are descriptive averages, not causal effects. Season, time of day, and the number of observations also differ across weather categories.",
        _bars(
            weather_labels,
            [("Observed mean", weather.tolist(), TEAL)],
            "Average hourly demand by observed weather",
            "Rentals / hour",
        ),
    )
    period = f"{data['timestamp'].min():%d %b %Y} – {data['timestamp'].max():%d %b %Y}"
    return _document(
        "When the city rides",
        f"Explore historical bike sharing demand · {period}. See how the daily commute, calendar, and recorded weather shape demand.",
        cards + heatmap + patterns + weather_panel,
        provenance,
    )


def render_model_scorecard(
    predictions: pd.DataFrame,
    metrics: dict,
    importance: pd.DataFrame,
    provenance: dict,
) -> str:
    """Render held-out model quality, baseline comparisons, and error patterns.

    Args:
        predictions: Hourly timestamp, hr, cnt, predicted, and baseline_predicted
            observations from the evaluation period.
        metrics: Measured mae, baseline_mae, r2, optional rush_hour_mae, and
            evaluation period metadata.
        importance: Feature and importance columns with measured permutation
            increases in held-out mean absolute error.
        provenance: Available dataset, model, and training run identifiers.

    Returns:
        A self-contained HTML scorecard using measured evaluation results.

    Raises:
        ValueError: If no evaluation observations are supplied.
    """
    if predictions.empty:
        raise ValueError("A model scorecard requires evaluation observations.")
    frame = predictions.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    frame = frame.sort_values("timestamp")
    frame["model_error"] = (frame["predicted"] - frame["cnt"]).abs()
    frame["baseline_error"] = (
        frame["baseline_predicted"] - frame["cnt"]
    ).abs()
    cards = _cards(
        [
            (
                "Selected model MAE",
                _format(metrics["mae"], 1),
                "Average absolute error · rentals/hour",
            ),
            (
                "Baseline MAE",
                _format(metrics["baseline_mae"], 1),
                "Same held-out observations",
            ),
            (
                "Rush-hour MAE",
                _format(metrics.get("rush_hour_mae", float("nan")), 1),
                "Rentals/hour · working days, 07–09h & 16–18h"
                if "rush_hour_mae" in metrics
                else "No working-day rush-hour observations",
            ),
            (
                "Model fit · R²",
                _format(metrics["r2"], 3),
                "Held-out coefficient of determination",
            ),
        ]
    )
    baseline_mae = float(metrics["baseline_mae"])
    comparison = "Model and baseline are evaluated on the same historical holdout. Lower MAE is better."
    if baseline_mae > 0:
        change = 100 * (float(metrics["mae"]) / baseline_mae - 1)
        direction = "lower" if change <= 0 else "higher"
        comparison = f"Selected-model MAE is {abs(change):.1f}% {direction} than baseline MAE on the same historical holdout. Lower MAE is better."
    if "baseline_rush_hour_mae" in metrics and "rush_hour_mae" in metrics:
        comparison += (
            f" During working-day rush hours (07–09h and 16–18h), MAE is "
            f"{_format(metrics['rush_hour_mae'], 1)} rentals/hour for the "
            f"selected model versus {_format(metrics['baseline_rush_hour_mae'], 1)} "
            "for the baseline."
        )
    note = f'<div class="note">{escape(comparison)}</div>'
    recent = frame.loc[
        frame["timestamp"] > frame["timestamp"].max() - pd.Timedelta(days=7)
    ]
    labels = recent["timestamp"].dt.strftime("%d %b %Hh").tolist()
    demand = _panel(
        "Observed demand and model estimates",
        f"The final seven calendar days of the evaluation period are shown. Metrics above use all {len(frame):,} held-out hourly observations.",
        _line_chart(
            labels,
            [
                ("Observed", recent["cnt"].tolist(), NAVY),
                ("Selected model", recent["predicted"].tolist(), TEAL),
            ],
            "Observed and estimated hourly demand in the last evaluation week",
        ),
    )
    errors = (
        frame.groupby("hr")[["model_error", "baseline_error"]]
        .mean()
        .sort_index()
    )
    error_panel = _panel(
        "Where the errors accumulate",
        "Mean absolute error by hour on the full holdout. The same observed counts are used for both models.",
        _bars(
            [f"{hour:02d}" for hour in errors.index],
            [
                ("Baseline", errors["baseline_error"].tolist(), GRAY),
                ("Selected model", errors["model_error"].tolist(), TEAL),
            ],
            "Baseline and selected-model absolute error by hour",
            "MAE · rentals / hour",
        ),
    )
    importance_panel = _panel(
        "What the model depends on",
        "Held-out permutation importance: change in MAE after shuffling each feature. Higher positive values indicate greater dependence; negative values mean shuffling reduced the measured error.",
        _importance_chart(importance),
    )
    period = f"{frame['timestamp'].min():%d %b %Y} – {frame['timestamp'].max():%d %b %Y}"
    subtitle = f"Selected model: {metrics.get('model_variant', 'demand estimator')} · Evaluation: {period}. Estimates use observed historical weather."
    return _document(
        "How well demand is estimated",
        subtitle,
        cards + note + demand + error_panel + importance_panel,
        provenance,
    )


def render_daily_operations(
    predictions: pd.DataFrame, metrics: dict, provenance: dict
) -> str:
    """Render a historical day's observed and estimated rental demand.

    Args:
        predictions: Historical hourly timestamp, hr, cnt, and predicted values.
        metrics: Measured daily scores and optional scoring_date metadata.
        provenance: Available dataset, model, and training run identifiers.

    Returns:
        A self-contained historical operations report with hourly detail.

    Raises:
        ValueError: If no daily observations are supplied.
    """
    if predictions.empty:
        raise ValueError("Daily operations requires hourly observations.")
    frame = predictions.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    frame = frame.sort_values("timestamp")
    observed = float(frame["cnt"].sum())
    estimated = float(frame["predicted"].sum())
    peak = frame.loc[frame["cnt"].idxmax()]
    estimated_peak = frame.loc[frame["predicted"].idxmax()]
    errors = frame["predicted"] - frame["cnt"]
    cards = _cards(
        [
            (
                "Observed rentals",
                _format(observed),
                "Total across the recorded hours",
            ),
            (
                "Estimated rentals",
                _format(estimated),
                "Sum of the model's hourly estimates",
            ),
            (
                "Mean absolute error",
                _format(float(errors.abs().mean()), 1),
                "Rentals per recorded hour",
            ),
            (
                "Observed peak",
                f"{int(peak['hr']):02d}:00",
                f"{_format(peak['cnt'])} rentals in that hour",
            ),
        ]
    )
    labels = frame["timestamp"].dt.strftime("%H:%M").tolist()
    main_chart = _panel(
        "A day's demand, in detail",
        f"{len(frame)} recorded hourly observations. Estimates use the weather that was observed on this historical date; this is an operations replay, not a live forecast.",
        _line_chart(
            labels,
            [
                ("Observed", frame["cnt"].tolist(), NAVY),
                ("Estimated", frame["predicted"].tolist(), TEAL),
            ],
            "Observed and estimated rental demand throughout the historical day",
        ),
    )
    observed_time = f"{int(peak['hr']):02d}:00"
    estimated_time = f"{int(estimated_peak['hr']):02d}:00"
    difference = estimated - observed
    direction = "above" if difference >= 0 else "below"
    insights = '<div class="insights">'
    for title, text in [
        (
            "Observed demand peak",
            f"Demand reached {_format(peak['cnt'])} rentals at {observed_time}.",
        ),
        (
            "Estimated demand peak",
            f"The model's highest estimate was {_format(estimated_peak['predicted'], 1)} rentals at {estimated_time}.",
        ),
        (
            "Daily balance",
            f"Estimated demand was {_format(abs(difference), 1)} rentals {direction} the observed daily total.",
        ),
    ]:
        insights += (
            f"<article><h3>{escape(title)}</h3><p>{escape(text)}</p></article>"
        )
    insights += "</div>"
    error_chart = _panel(
        "Overestimates and underestimates",
        "Signed error is estimated minus observed demand. Positive bars overestimate rentals; negative bars underestimate them. Offset errors can cancel in the daily total.",
        _bars(
            [f"{hour:02d}" for hour in frame["hr"]],
            [("Estimate − observed", errors.tolist(), ORANGE)],
            "Signed hourly rental estimation error",
            "Error · rentals / hour",
        ),
    )
    day = frame["timestamp"].min().strftime("%A, %d %B %Y")
    return _document(
        "One day, hour by hour",
        f"Historical operations replay · {day}. Compare estimated demand with the actual rental counts before interpreting the daily total.",
        cards
        + main_chart
        + _panel(
            "The operating picture",
            "Read the peaks alongside the hourly errors.",
            insights,
        )
        + error_chart,
        provenance,
    )
