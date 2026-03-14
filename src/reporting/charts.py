"""Plotly chart generators for benchmark results."""

from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd

# ---------------------------------------------------------------------------
# Shared styling — Grafana-inspired dark palette
# ---------------------------------------------------------------------------

DARK_TEMPLATE = "plotly_dark"

# Primary palette: teal lead, then amber, violet, coral, lime, sky, rose, sage
COLORS = [
    "#00bcd4",  # teal
    "#ff9800",  # amber
    "#ab47bc",  # violet
    "#ef5350",  # coral-red
    "#66bb6a",  # lime-green
    "#42a5f5",  # sky-blue
    "#ec407a",  # rose
    "#26a69a",  # sage-teal
    "#ffa726",  # warm amber
    "#7e57c2",  # deep violet
]

# Panel / background colors (must match app.py)
BG_PAPER   = "#0d1117"
BG_PLOT    = "#161b22"
GRID_COLOR = "#21262d"
AXIS_COLOR = "#8b949e"
TEXT_COLOR = "#e6edf3"
TEXT_MUTED = "#8b949e"

_FONT_FAMILY = "DM Sans, Helvetica Neue, Arial, sans-serif"
_MONO_FAMILY = "JetBrains Mono, Fira Code, monospace"


def _base_layout(title: str, xaxis: str, yaxis: str) -> dict:
    return dict(
        template=DARK_TEMPLATE,
        paper_bgcolor=BG_PAPER,
        plot_bgcolor=BG_PLOT,
        title=dict(
            text=title,
            font=dict(size=15, family=_FONT_FAMILY, color=TEXT_COLOR),
            x=0.0,
            xanchor="left",
            pad=dict(l=4),
        ),
        xaxis=dict(
            title=dict(text=xaxis, font=dict(size=12, color=TEXT_MUTED)),
            tickfont=dict(size=11, color=TEXT_MUTED, family=_MONO_FAMILY),
            gridcolor=GRID_COLOR,
            gridwidth=1,
            linecolor=GRID_COLOR,
            zeroline=False,
            showgrid=True,
        ),
        yaxis=dict(
            title=dict(text=yaxis, font=dict(size=12, color=TEXT_MUTED)),
            tickfont=dict(size=11, color=TEXT_MUTED, family=_MONO_FAMILY),
            gridcolor=GRID_COLOR,
            gridwidth=1,
            linecolor=GRID_COLOR,
            zeroline=False,
            showgrid=True,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color=TEXT_MUTED, family=_FONT_FAMILY),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
        ),
        margin=dict(l=56, r=20, t=72, b=52),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#1c2128",
            bordercolor="#30363d",
            font=dict(size=12, color=TEXT_COLOR, family=_FONT_FAMILY),
        ),
    )


# ---------------------------------------------------------------------------
# Latency vs concurrency
# ---------------------------------------------------------------------------

def latency_vs_concurrency(
    df: pd.DataFrame,
    metric: str = "ttft",
    percentiles: list[str] | None = None,
) -> go.Figure:
    """Line chart: x=concurrency, y=latency (ms), one line per (series, percentile).

    metric: 'ttft' | 'tpot' | 'e2el'
    percentiles: subset of ['median', 'p90', 'p99', 'mean'] (default: median, p90, p99)
    """
    if percentiles is None:
        percentiles = ["median", "p90", "p99"]

    metric_upper = metric.upper()
    fig = go.Figure()
    series_list = sorted(df["series"].unique())

    dash_map   = {"median": "solid", "p90": "dash", "p99": "dot", "mean": "dashdot"}
    symbol_map = {"median": "circle", "p90": "square", "p99": "diamond", "mean": "cross"}
    # Opacity tiers so p99 doesn't visually overpower median
    opacity_map = {"median": 1.0, "p90": 0.75, "p99": 0.55, "mean": 0.65}

    for si, series in enumerate(series_list):
        sdf = df[df["series"] == series].sort_values("concurrency")
        color = COLORS[si % len(COLORS)]
        for pct in percentiles:
            col = f"{pct}_{metric}_ms"
            if col not in sdf.columns:
                continue
            vals = sdf[col]
            if vals.isna().all():
                continue

            opacity = opacity_map.get(pct, 1.0)
            is_primary = (pct == "median")

            fig.add_trace(go.Scatter(
                x=sdf["concurrency"],
                y=vals,
                mode="lines+markers",
                name=f"{series} — {pct}",
                opacity=opacity,
                line=dict(
                    color=color,
                    dash=dash_map.get(pct, "solid"),
                    width=2.5 if is_primary else 1.5,
                ),
                marker=dict(
                    symbol=symbol_map.get(pct, "circle"),
                    size=8 if is_primary else 5,
                    color=color,
                    line=dict(width=1.5, color=BG_PAPER),
                ),
                hovertemplate=(
                    f"<b>{pct.upper()} {metric_upper}</b>: %{{y:.1f}} ms"
                    f"<br>Concurrency: %{{x}}"
                    f"<extra><b>{series}</b></extra>"
                ),
            ))

    fig.update_layout(**_base_layout(
        f"{metric_upper} Latency vs Concurrency",
        "Concurrency",
        f"{metric_upper} Latency (ms)",
    ))
    return fig


# ---------------------------------------------------------------------------
# Throughput vs concurrency
# ---------------------------------------------------------------------------

_THROUGHPUT_COL_MAP = {
    "output_token": "output_tok_s",
    "total_token":  "total_tok_s",
    "input_token":  "input_tok_s",
    "request":      "request_throughput",
}

_THROUGHPUT_YLABEL = {
    "output_token": "Output Tokens / s",
    "total_token":  "Total Tokens / s",
    "input_token":  "Input Tokens / s",
    "request":      "Requests / s",
}


def throughput_vs_concurrency(
    df: pd.DataFrame,
    metric: str = "output_token",
) -> go.Figure:
    """Line chart: x=concurrency, y=throughput."""
    col    = _THROUGHPUT_COL_MAP.get(metric, metric)
    ylabel = _THROUGHPUT_YLABEL.get(metric, metric)

    fig = go.Figure()
    series_list = sorted(df["series"].unique())

    for si, series in enumerate(series_list):
        sdf = df[df["series"] == series].sort_values("concurrency")
        if col not in sdf.columns or sdf[col].isna().all():
            continue
        color = COLORS[si % len(COLORS)]

        # Filled area under curve — signature Grafana look
        fig.add_trace(go.Scatter(
            x=sdf["concurrency"],
            y=sdf[col],
            mode="lines+markers",
            name=series,
            fill="tozeroy",
            fillcolor=f"rgba({_hex_to_rgb(color)},0.08)",
            line=dict(color=color, width=2.5),
            marker=dict(
                size=8,
                color=color,
                line=dict(width=1.5, color=BG_PAPER),
            ),
            hovertemplate=(
                f"<b>{ylabel}</b>: %{{y:.1f}}"
                f"<br>Concurrency: %{{x}}"
                f"<extra><b>{series}</b></extra>"
            ),
        ))

    fig.update_layout(**_base_layout(
        f"{ylabel} vs Concurrency",
        "Concurrency",
        ylabel,
    ))
    return fig


def _hex_to_rgb(hex_color: str) -> str:
    """Convert #rrggbb to 'r,g,b' string for rgba() use."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"


# ---------------------------------------------------------------------------
# Comparison chart (overlay two series)
# ---------------------------------------------------------------------------

def comparison_chart(
    df: pd.DataFrame,
    series_a: str,
    series_b: str,
    metric: str = "median_tpot_ms",
    metric_label: str | None = None,
) -> go.Figure:
    """Overlay two series on the same chart for direct comparison."""
    label = metric_label or metric.replace("_", " ").upper()
    fig = go.Figure()

    pair_colors = [COLORS[0], COLORS[1]]  # teal vs amber

    for si, series in enumerate([series_a, series_b]):
        sdf = df[df["series"] == series].sort_values("concurrency")
        if metric not in sdf.columns or sdf[metric].isna().all():
            continue
        color = pair_colors[si % len(pair_colors)]

        fig.add_trace(go.Scatter(
            x=sdf["concurrency"],
            y=sdf[metric],
            mode="lines+markers",
            name=series,
            line=dict(color=color, width=2.5),
            marker=dict(
                size=9,
                color=color,
                line=dict(width=1.5, color=BG_PAPER),
            ),
            hovertemplate=(
                f"<b>{label}</b>: %{{y:.1f}}"
                f"<br>Concurrency: %{{x}}"
                f"<extra><b>{series}</b></extra>"
            ),
        ))

    fig.update_layout(**_base_layout(
        f"Series Comparison — {label}",
        "Concurrency",
        label,
    ))
    return fig


# ---------------------------------------------------------------------------
# Per-request scatter
# ---------------------------------------------------------------------------

def per_request_scatter(
    per_request_df: pd.DataFrame,
    x: str = "input_tokens",
    y: str = "tpot_ms",
    color_by: str | None = None,
) -> go.Figure:
    """Scatter plot from per_request arrays."""
    fig = go.Figure()

    if color_by and color_by in per_request_df.columns:
        groups = per_request_df.groupby(color_by)
        for gi, (gname, gdf) in enumerate(groups):
            color = COLORS[gi % len(COLORS)]
            fig.add_trace(go.Scatter(
                x=gdf[x],
                y=gdf[y],
                mode="markers",
                name=str(gname),
                marker=dict(
                    color=color,
                    size=5,
                    opacity=0.65,
                    line=dict(width=0),
                ),
                hovertemplate=(
                    f"<b>{x}</b>: %{{x}}"
                    f"<br><b>{y}</b>: %{{y:.2f}}"
                    f"<extra><b>{gname}</b></extra>"
                ),
            ))
    else:
        fig.add_trace(go.Scatter(
            x=per_request_df[x],
            y=per_request_df[y],
            mode="markers",
            name="requests",
            marker=dict(
                color=COLORS[0],
                size=5,
                opacity=0.65,
                line=dict(width=0),
            ),
            hovertemplate=(
                f"<b>{x}</b>: %{{x}}"
                f"<br><b>{y}</b>: %{{y:.2f}}"
                f"<extra></extra>"
            ),
        ))

    x_label = x.replace("_", " ").title()
    y_label = y.replace("_", " ").title()
    fig.update_layout(**_base_layout(
        f"{y_label} vs {x_label} (per request)",
        x_label,
        y_label,
    ))
    return fig


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

_TABLE_COLS = [
    ("hardware",          "Hardware"),
    ("model_short",       "Model"),
    ("backend",           "Backend"),
    ("profile",           "Profile"),
    ("concurrency",       "Conc"),
    ("successful_requests","OK Reqs"),
    ("failed_requests",   "Fail"),
    ("output_tok_s",      "Out Tok/s"),
    ("total_tok_s",       "Tot Tok/s"),
    ("median_ttft_ms",    "TTFT p50"),
    ("p99_ttft_ms",       "TTFT p99"),
    ("median_tpot_ms",    "TPOT p50"),
    ("p99_tpot_ms",       "TPOT p99"),
    ("median_e2el_ms",    "E2EL p50"),
]


def summary_table(df: pd.DataFrame) -> go.Figure:
    """Plotly Table figure showing key metrics."""
    available = [(col, hdr) for col, hdr in _TABLE_COLS if col in df.columns]
    cols    = [c for c, _ in available]
    headers = [h for _, h in available]

    values = []
    for col in cols:
        series = df[col]
        if series.dtype in ("float64", "float32"):
            values.append([f"{v:.1f}" if pd.notna(v) else "—" for v in series])
        else:
            values.append(series.fillna("—").astype(str).tolist())

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=[f"<b>{h}</b>" for h in headers],
            fill_color="#1c2128",
            font=dict(color=TEXT_COLOR, size=12, family=_FONT_FAMILY),
            align="center",
            line_color=GRID_COLOR,
            height=36,
        ),
        cells=dict(
            values=values,
            fill_color=[[BG_PLOT if i % 2 == 0 else "#1c2128" for i in range(len(df))]
                        for _ in cols],
            font=dict(color=TEXT_COLOR, size=11, family=_MONO_FAMILY),
            align="center",
            line_color=GRID_COLOR,
            height=30,
        ),
    )])

    fig.update_layout(
        template=DARK_TEMPLATE,
        paper_bgcolor=BG_PAPER,
        title=dict(text="Benchmark Results Summary",
                   font=dict(size=15, family=_FONT_FAMILY, color=TEXT_COLOR)),
        margin=dict(l=10, r=10, t=50, b=10),
        height=max(400, 66 + 30 * len(df)),
    )
    return fig
