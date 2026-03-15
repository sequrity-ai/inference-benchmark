"""Dash web dashboard for inference benchmark results.

Run directly:  python -m src.reporting.app
Or:            python src/reporting/app.py
"""

from __future__ import annotations

import dash
from dash import dcc, html, dash_table, callback, Input, Output, State
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path

from src.reporting.loader import load_all, load_per_request, get_filter_options, get_series_list
from src.reporting import charts

# ---------------------------------------------------------------------------
# Data cache
# ---------------------------------------------------------------------------

_cache: dict[str, object] = {}


def _get_df() -> pd.DataFrame:
    if "df" not in _cache:
        _cache["df"] = load_all()
    return _cache["df"]


def _refresh():
    _cache.pop("df", None)
    return _get_df()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = dash.Dash(
    __name__,
    title="Inference Benchmark",
    suppress_callback_exceptions=True,
)

server = app.server

# ---------------------------------------------------------------------------
# Global CSS injected via index_string
# ---------------------------------------------------------------------------

app.index_string = """
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        /* ── Reset & base ─────────────────────────────────────── */
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        :root {
            --bg-base:      #0d1117;
            --bg-panel:     #161b22;
            --bg-raised:    #1c2128;
            --bg-overlay:   #21262d;
            --border:       #30363d;
            --border-light: #21262d;

            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --text-muted:   #484f58;

            --accent-teal:  #00bcd4;
            --accent-amber: #ff9800;
            --accent-violet:#ab47bc;
            --accent-red:   #ef5350;
            --accent-green: #66bb6a;

            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 14px;

            --shadow-card: 0 1px 3px rgba(0,0,0,0.4), 0 4px 16px rgba(0,0,0,0.25);
            --shadow-kpi:  0 2px 8px rgba(0,0,0,0.5);

            --font-sans: "DM Sans", "Helvetica Neue", Arial, sans-serif;
            --font-mono: "JetBrains Mono", "Fira Code", monospace;
        }

        html, body {
            background: var(--bg-base);
            color: var(--text-primary);
            font-family: var(--font-sans);
            font-size: 14px;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }

        /* ── Scrollbar ─────────────────────────────────────────── */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-base); }
        ::-webkit-scrollbar-thumb { background: var(--bg-overlay); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--border); }

        /* ── Dash Dropdown override ────────────────────────────── */
        .Select-control, .Select-menu-outer {
            background-color: var(--bg-raised) !important;
            border-color: var(--border) !important;
            border-radius: var(--radius-sm) !important;
            color: var(--text-primary) !important;
        }
        .Select-value-label {
            color: var(--text-primary) !important;
            font-family: var(--font-sans) !important;
            font-size: 13px !important;
        }
        .Select-placeholder {
            color: var(--text-muted) !important;
            font-family: var(--font-sans) !important;
            font-size: 13px !important;
        }
        .Select-option {
            background-color: var(--bg-raised) !important;
            color: var(--text-secondary) !important;
            font-size: 13px !important;
        }
        .Select-option:hover, .Select-option.is-focused {
            background-color: var(--bg-overlay) !important;
            color: var(--text-primary) !important;
        }
        .Select-option.is-selected {
            background-color: rgba(0,188,212,0.15) !important;
            color: var(--accent-teal) !important;
        }
        .Select-multi-value-wrapper { gap: 4px; }
        .Select-value {
            background-color: rgba(0,188,212,0.18) !important;
            border-color: rgba(0,188,212,0.4) !important;
            border-radius: 4px !important;
            color: var(--accent-teal) !important;
            font-size: 12px !important;
        }
        .Select-value .Select-value-label {
            color: var(--accent-teal) !important;
        }
        .Select-value-icon { color: var(--accent-teal) !important; }
        .Select-arrow-zone { color: var(--text-muted) !important; }
        .VirtualizedSelectFocusedOption {
            background-color: var(--bg-overlay) !important;
        }

        /* ── Tab pills ─────────────────────────────────────────── */
        .tab-pill-bar {
            display: flex;
            gap: 4px;
            padding: 6px;
            background: var(--bg-raised);
            border-radius: var(--radius-md);
            border: 1px solid var(--border-light);
            flex-wrap: wrap;
        }
        .tab-pill {
            padding: 7px 18px;
            border-radius: var(--radius-sm);
            font-size: 13px;
            font-weight: 500;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.15s ease;
            border: none;
            background: transparent;
            white-space: nowrap;
        }
        .tab-pill:hover { color: var(--text-primary); background: var(--bg-overlay); }
        .tab-pill-active {
            color: var(--accent-teal) !important;
            background: rgba(0,188,212,0.12) !important;
        }

        /* ── KPI card ──────────────────────────────────────────── */
        .kpi-card {
            background: var(--bg-panel);
            border: 1px solid var(--border-light);
            border-radius: var(--radius-md);
            padding: 16px 20px;
            display: flex;
            flex-direction: column;
            gap: 4px;
            box-shadow: var(--shadow-kpi);
            flex: 1;
            min-width: 160px;
            position: relative;
            overflow: hidden;
            transition: border-color 0.2s ease;
        }
        .kpi-card::before {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            border-radius: var(--radius-md) var(--radius-md) 0 0;
        }
        .kpi-card:nth-child(1)::before { background: var(--accent-teal); }
        .kpi-card:nth-child(2)::before { background: var(--accent-amber); }
        .kpi-card:nth-child(3)::before { background: var(--accent-violet); }
        .kpi-card:nth-child(4)::before { background: var(--accent-green); }
        .kpi-card:hover { border-color: var(--border); }

        .kpi-label {
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--text-muted);
        }
        .kpi-value {
            font-size: 28px;
            font-weight: 600;
            font-family: var(--font-mono);
            color: var(--text-primary);
            line-height: 1.1;
        }
        .kpi-sub {
            font-size: 11px;
            color: var(--text-secondary);
        }

        /* ── Chart card ────────────────────────────────────────── */
        .chart-card {
            background: var(--bg-panel);
            border: 1px solid var(--border-light);
            border-radius: var(--radius-md);
            padding: 4px 4px 0 4px;
            box-shadow: var(--shadow-card);
            overflow: hidden;
        }

        /* ── Controls panel ────────────────────────────────────── */
        .controls-panel {
            background: var(--bg-raised);
            border: 1px solid var(--border-light);
            border-radius: var(--radius-md);
            padding: 16px 20px;
        }
        .controls-label {
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 6px;
            display: block;
        }

        /* ── Section header ────────────────────────────────────── */
        .section-header {
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border-light);
        }

        /* ── Filter bar ────────────────────────────────────────── */
        .filter-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            align-items: flex-end;
        }
        .filter-item {
            display: flex;
            flex-direction: column;
            gap: 5px;
            flex: 1;
            min-width: 160px;
        }

        /* ── Refresh button ────────────────────────────────────── */
        .refresh-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 18px;
            background: rgba(0,188,212,0.1);
            color: var(--accent-teal);
            border: 1px solid rgba(0,188,212,0.3);
            border-radius: var(--radius-sm);
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            font-family: var(--font-sans);
            transition: all 0.15s ease;
            white-space: nowrap;
        }
        .refresh-btn:hover {
            background: rgba(0,188,212,0.18);
            border-color: rgba(0,188,212,0.5);
        }

        /* ── Status dot ────────────────────────────────────────── */
        .status-dot {
            display: inline-block;
            width: 7px; height: 7px;
            border-radius: 50%;
            background: var(--accent-green);
            box-shadow: 0 0 0 2px rgba(102,187,106,0.25);
        }

        /* ── DataTable override ────────────────────────────────── */
        .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th {
            background-color: var(--bg-raised) !important;
        }

        /* ── Two-column chart grid ─────────────────────────────── */
        .chart-grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }
        .chart-grid-1 {
            display: grid;
            grid-template-columns: 1fr;
            gap: 16px;
        }
        @media (max-width: 900px) {
            .chart-grid-2 { grid-template-columns: 1fr; }
        }

        /* ── Loading overlay ───────────────────────────────────── */
        ._dash-loading-callback {
            opacity: 0.5;
            transition: opacity 0.2s ease;
        }
    </style>
</head>
<body>
    {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
</body>
</html>
"""


def _empty_fig(msg: str = "No data") -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=charts.BG_PAPER,
        plot_bgcolor=charts.BG_PLOT,
        annotations=[dict(
            text=msg,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color=charts.TEXT_MUTED, family=charts.BG_PAPER),
        )],
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def _make_dropdown(id_: str, label: str, options: list, multi: bool = True, default=None):
    return html.Div(className="filter-item", children=[
        html.Span(label, className="controls-label"),
        dcc.Dropdown(
            id=id_,
            options=[{"label": o, "value": o} for o in options],
            value=default if default is not None else [],
            multi=multi,
            placeholder=f"All {label}s",
            clearable=True,
        ),
    ])


CMP_METRICS = [
    {"label": "TPOT Median (ms)",    "value": "median_tpot_ms"},
    {"label": "TPOT P99 (ms)",       "value": "p99_tpot_ms"},
    {"label": "TTFT Median (ms)",    "value": "median_ttft_ms"},
    {"label": "TTFT P99 (ms)",       "value": "p99_ttft_ms"},
    {"label": "E2EL Median (ms)",    "value": "median_e2el_ms"},
    {"label": "Output Tok/s",        "value": "output_tok_s"},
    {"label": "Total Tok/s",         "value": "total_tok_s"},
    {"label": "Request Throughput",  "value": "request_throughput"},
]

PR_X_OPTIONS = [
    {"label": "Input Tokens",  "value": "input_tokens"},
    {"label": "Output Tokens", "value": "output_tokens"},
]

PR_Y_OPTIONS = [
    {"label": "TPOT (ms)", "value": "tpot_ms"},
    {"label": "TTFT (ms)", "value": "ttft_ms"},
    {"label": "E2EL (ms)", "value": "e2el_ms"},
]


def _kpi_card(label: str, value: str, sub: str = ""):
    return html.Div(className="kpi-card", children=[
        html.Span(label, className="kpi-label"),
        html.Div(value, className="kpi-value"),
        html.Span(sub, className="kpi-sub") if sub else None,
    ])


def _compute_kpis(df: pd.DataFrame) -> tuple[str, str, str, str]:
    """Return (runs, hardware, models, avg_throughput_str)."""
    if df.empty:
        return "0", "0", "0", "—"

    runs     = str(len(df))
    hardware = str(df["hardware"].nunique()) if "hardware" in df.columns else "—"
    models   = str(df["model_short"].nunique()) if "model_short" in df.columns else "—"

    if "output_tok_s" in df.columns and df["output_tok_s"].notna().any():
        avg_tps = df["output_tok_s"].median()
        tps_str = f"{avg_tps:,.0f} tok/s"
    else:
        tps_str = "—"

    return runs, hardware, models, tps_str


def build_layout():
    df      = _get_df()
    opts    = get_filter_options(df) if not df.empty else {}
    series  = sorted(df["series"].unique().tolist()) if not df.empty else []
    files   = (df[["filename", "file"]].drop_duplicates().sort_values("filename")
               if not df.empty else pd.DataFrame())
    file_options = [{"label": row["filename"], "value": row["file"]}
                    for _, row in files.iterrows()]

    runs, hw_count, model_count, avg_tps = _compute_kpis(df)

    return html.Div(
        style={
            "backgroundColor": "var(--bg-base)",
            "minHeight": "100vh",
            "fontFamily": "var(--font-sans)",
        },
        children=[

            # ── Top navigation bar ──────────────────────────────────────────
            html.Div(
                style={
                    "backgroundColor": "var(--bg-panel)",
                    "borderBottom": "1px solid var(--border-light)",
                    "padding": "0 28px",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "height": "56px",
                    "position": "sticky",
                    "top": "0",
                    "zIndex": "100",
                },
                children=[
                    # Brand
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "12px"},
                        children=[
                            html.Div(
                                style={
                                    "width": "28px", "height": "28px",
                                    "borderRadius": "6px",
                                    "background": "linear-gradient(135deg, #00bcd4, #0088a3)",
                                    "display": "flex", "alignItems": "center",
                                    "justifyContent": "center",
                                    "fontSize": "14px", "fontWeight": "700",
                                    "color": "#fff",
                                },
                                children="B"
                            ),
                            html.Span(
                                "Inference Benchmark",
                                style={
                                    "fontSize": "15px",
                                    "fontWeight": "600",
                                    "color": "var(--text-primary)",
                                    "letterSpacing": "-0.01em",
                                }
                            ),
                            html.Span(
                                "/ Dashboard",
                                style={
                                    "fontSize": "14px",
                                    "color": "var(--text-muted)",
                                    "fontWeight": "400",
                                }
                            ),
                        ]
                    ),

                    # Right side: status + refresh
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "16px"},
                        children=[
                            html.Div(
                                id="status-bar",
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "8px",
                                    "color": "var(--text-secondary)",
                                    "fontSize": "13px",
                                },
                                children=[
                                    html.Span(className="status-dot"),
                                    html.Span(f"{runs} result files loaded"),
                                ]
                            ),
                            html.Button(
                                "Refresh",
                                id="refresh-btn",
                                n_clicks=0,
                                className="refresh-btn",
                            ),
                        ]
                    ),
                ]
            ),

            # ── Main content ────────────────────────────────────────────────
            html.Div(
                style={"padding": "24px 28px", "maxWidth": "1600px", "margin": "0 auto"},
                children=[

                    # KPI row
                    html.Div(
                        style={
                            "display": "flex",
                            "gap": "14px",
                            "marginBottom": "24px",
                            "flexWrap": "wrap",
                        },
                        children=[
                            _kpi_card("Total Runs",       runs,       "benchmark data points"),
                            _kpi_card("Hardware Configs", hw_count,   "unique GPU setups"),
                            _kpi_card("Models Tested",    model_count,"distinct LLMs"),
                            _kpi_card("Median Throughput", avg_tps,   "output tokens / second"),
                        ]
                    ),

                    # ── Filters ─────────────────────────────────────────────
                    html.Div(
                        className="controls-panel",
                        style={"marginBottom": "20px"},
                        children=[
                            html.Div("Filters", className="section-header"),
                            html.Div(
                                className="filter-bar",
                                children=[
                                    _make_dropdown("filter-hardware", "Hardware",
                                                   opts.get("hardware", []),
                                                   default=[opts["hardware"][0]] if opts.get("hardware") else []),
                                    _make_dropdown("filter-model",    "Model",
                                                   opts.get("model_short", [])),
                                    _make_dropdown("filter-backend",  "Backend",
                                                   opts.get("backend", [])),
                                    _make_dropdown("filter-profile",  "Profile",
                                                   opts.get("profile", [])),
                                ],
                            ),
                        ]
                    ),

                    # ── Tab bar (pill style via dcc.Tabs) ───────────────────
                    dcc.Tabs(
                        id="tabs",
                        value="tab-latency",
                        colors={"border": "transparent", "primary": "transparent",
                                "background": "transparent"},
                        style={"marginBottom": "0", "borderBottom": "none"},
                        parent_style={"marginBottom": "0"},
                        content_style={"borderTop": "none"},
                        children=[
                            dcc.Tab(
                                label="Latency",
                                value="tab-latency",
                                style={
                                    "padding": "8px 20px",
                                    "backgroundColor": "var(--bg-raised)",
                                    "color": "var(--text-secondary)",
                                    "border": "1px solid var(--border-light)",
                                    "borderRadius": "var(--radius-sm)",
                                    "fontSize": "13px",
                                    "fontWeight": "500",
                                    "marginRight": "4px",
                                    "cursor": "pointer",
                                },
                                selected_style={
                                    "padding": "8px 20px",
                                    "backgroundColor": "rgba(0,188,212,0.12)",
                                    "color": "var(--accent-teal)",
                                    "border": "1px solid rgba(0,188,212,0.3)",
                                    "borderRadius": "var(--radius-sm)",
                                    "fontSize": "13px",
                                    "fontWeight": "600",
                                    "marginRight": "4px",
                                    "cursor": "pointer",
                                },
                            ),
                            dcc.Tab(
                                label="Throughput",
                                value="tab-throughput",
                                style={
                                    "padding": "8px 20px",
                                    "backgroundColor": "var(--bg-raised)",
                                    "color": "var(--text-secondary)",
                                    "border": "1px solid var(--border-light)",
                                    "borderRadius": "var(--radius-sm)",
                                    "fontSize": "13px",
                                    "fontWeight": "500",
                                    "marginRight": "4px",
                                    "cursor": "pointer",
                                },
                                selected_style={
                                    "padding": "8px 20px",
                                    "backgroundColor": "rgba(0,188,212,0.12)",
                                    "color": "var(--accent-teal)",
                                    "border": "1px solid rgba(0,188,212,0.3)",
                                    "borderRadius": "var(--radius-sm)",
                                    "fontSize": "13px",
                                    "fontWeight": "600",
                                    "marginRight": "4px",
                                    "cursor": "pointer",
                                },
                            ),
                            dcc.Tab(
                                label="Comparison",
                                value="tab-comparison",
                                style={
                                    "padding": "8px 20px",
                                    "backgroundColor": "var(--bg-raised)",
                                    "color": "var(--text-secondary)",
                                    "border": "1px solid var(--border-light)",
                                    "borderRadius": "var(--radius-sm)",
                                    "fontSize": "13px",
                                    "fontWeight": "500",
                                    "marginRight": "4px",
                                    "cursor": "pointer",
                                },
                                selected_style={
                                    "padding": "8px 20px",
                                    "backgroundColor": "rgba(0,188,212,0.12)",
                                    "color": "var(--accent-teal)",
                                    "border": "1px solid rgba(0,188,212,0.3)",
                                    "borderRadius": "var(--radius-sm)",
                                    "fontSize": "13px",
                                    "fontWeight": "600",
                                    "marginRight": "4px",
                                    "cursor": "pointer",
                                },
                            ),
                            dcc.Tab(
                                label="Per-Request",
                                value="tab-perreq",
                                style={
                                    "padding": "8px 20px",
                                    "backgroundColor": "var(--bg-raised)",
                                    "color": "var(--text-secondary)",
                                    "border": "1px solid var(--border-light)",
                                    "borderRadius": "var(--radius-sm)",
                                    "fontSize": "13px",
                                    "fontWeight": "500",
                                    "marginRight": "4px",
                                    "cursor": "pointer",
                                },
                                selected_style={
                                    "padding": "8px 20px",
                                    "backgroundColor": "rgba(0,188,212,0.12)",
                                    "color": "var(--accent-teal)",
                                    "border": "1px solid rgba(0,188,212,0.3)",
                                    "borderRadius": "var(--radius-sm)",
                                    "fontSize": "13px",
                                    "fontWeight": "600",
                                    "marginRight": "4px",
                                    "cursor": "pointer",
                                },
                            ),
                            dcc.Tab(
                                label="Raw Data",
                                value="tab-raw",
                                style={
                                    "padding": "8px 20px",
                                    "backgroundColor": "var(--bg-raised)",
                                    "color": "var(--text-secondary)",
                                    "border": "1px solid var(--border-light)",
                                    "borderRadius": "var(--radius-sm)",
                                    "fontSize": "13px",
                                    "fontWeight": "500",
                                    "marginRight": "4px",
                                    "cursor": "pointer",
                                },
                                selected_style={
                                    "padding": "8px 20px",
                                    "backgroundColor": "rgba(0,188,212,0.12)",
                                    "color": "var(--accent-teal)",
                                    "border": "1px solid rgba(0,188,212,0.3)",
                                    "borderRadius": "var(--radius-sm)",
                                    "fontSize": "13px",
                                    "fontWeight": "600",
                                    "marginRight": "4px",
                                    "cursor": "pointer",
                                },
                            ),
                        ],
                    ),

                    # -- Comparison controls (always in DOM) ─────────────────
                    html.Div(
                        id="cmp-controls",
                        style={"display": "none"},
                        children=[
                            html.Div(
                                className="controls-panel",
                                style={"marginTop": "12px"},
                                children=[
                                    html.Div("Comparison Settings", className="section-header"),
                                    html.Div(
                                        className="filter-bar",
                                        children=[
                                            html.Div(
                                                className="filter-item",
                                                style={"flex": "2", "minWidth": "240px"},
                                                children=[
                                                    html.Span("Series A", className="controls-label"),
                                                    dcc.Dropdown(
                                                        id="cmp-series-a",
                                                        options=[{"label": s, "value": s} for s in series],
                                                        value=series[0] if series else None,
                                                    ),
                                                ]
                                            ),
                                            html.Div(
                                                className="filter-item",
                                                style={"flex": "2", "minWidth": "240px"},
                                                children=[
                                                    html.Span("Series B", className="controls-label"),
                                                    dcc.Dropdown(
                                                        id="cmp-series-b",
                                                        options=[{"label": s, "value": s} for s in series],
                                                        value=(series[1] if len(series) > 1
                                                               else (series[0] if series else None)),
                                                    ),
                                                ]
                                            ),
                                            html.Div(
                                                className="filter-item",
                                                style={"flex": "1", "minWidth": "180px"},
                                                children=[
                                                    html.Span("Metric", className="controls-label"),
                                                    dcc.Dropdown(
                                                        id="cmp-metric",
                                                        options=CMP_METRICS,
                                                        value="median_tpot_ms",
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                ]
                            )
                        ]
                    ),

                    # -- Per-request controls (always in DOM) ─────────────────
                    html.Div(
                        id="pr-controls",
                        style={"display": "none"},
                        children=[
                            html.Div(
                                className="controls-panel",
                                style={"marginTop": "12px"},
                                children=[
                                    html.Div("Per-Request Settings", className="section-header"),
                                    html.Div(
                                        className="filter-bar",
                                        children=[
                                            html.Div(
                                                className="filter-item",
                                                style={"flex": "3", "minWidth": "280px"},
                                                children=[
                                                    html.Span("Result Files", className="controls-label"),
                                                    dcc.Dropdown(
                                                        id="pr-files",
                                                        options=file_options,
                                                        value=([file_options[0]["value"]]
                                                               if file_options else []),
                                                        multi=True,
                                                    ),
                                                ]
                                            ),
                                            html.Div(
                                                className="filter-item",
                                                style={"flex": "1", "minWidth": "140px"},
                                                children=[
                                                    html.Span("X Axis", className="controls-label"),
                                                    dcc.Dropdown(
                                                        id="pr-x",
                                                        options=PR_X_OPTIONS,
                                                        value="input_tokens",
                                                    ),
                                                ]
                                            ),
                                            html.Div(
                                                className="filter-item",
                                                style={"flex": "1", "minWidth": "140px"},
                                                children=[
                                                    html.Span("Y Axis", className="controls-label"),
                                                    dcc.Dropdown(
                                                        id="pr-y",
                                                        options=PR_Y_OPTIONS,
                                                        value="tpot_ms",
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                ]
                            )
                        ]
                    ),

                    # -- Tab content ─────────────────────────────────────────
                    html.Div(
                        id="tab-content",
                        style={"marginTop": "16px", "minHeight": "600px"},
                    ),

                ]
            ),
        ]
    )


app.layout = build_layout


# ---------------------------------------------------------------------------
# Callbacks (exactly 2 — do not add more)
# ---------------------------------------------------------------------------

def _apply_filters(df: pd.DataFrame, hw, model, backend, profile) -> pd.DataFrame:
    if hw:
        df = df[df["hardware"].isin(hw)]
    if model:
        df = df[df["model_short"].isin(model)]
    if backend:
        df = df[df["backend"].isin(backend)]
    if profile:
        df = df[df["profile"].isin(profile)]
    return df


@callback(
    Output("status-bar",       "children"),
    Output("filter-hardware",  "options"),
    Output("filter-model",     "options"),
    Output("filter-backend",   "options"),
    Output("filter-profile",   "options"),
    Input("refresh-btn", "n_clicks"),
    prevent_initial_call=True,
)
def refresh_data(n_clicks):
    df   = _refresh()
    opts = get_filter_options(df)
    runs, _, _, _ = _compute_kpis(df)
    return (
        [html.Span(className="status-dot"),
         html.Span(f"{runs} result files loaded (refreshed)")],
        [{"label": o, "value": o} for o in opts.get("hardware", [])],
        [{"label": o, "value": o} for o in opts.get("model_short", [])],
        [{"label": o, "value": o} for o in opts.get("backend", [])],
        [{"label": o, "value": o} for o in opts.get("profile", [])],
    )


@callback(
    Output("tab-content",  "children"),
    Output("cmp-controls", "style"),
    Output("pr-controls",  "style"),
    Input("tabs",             "value"),
    Input("filter-hardware",  "value"),
    Input("filter-model",     "value"),
    Input("filter-backend",   "value"),
    Input("filter-profile",   "value"),
    Input("cmp-series-a",     "value"),
    Input("cmp-series-b",     "value"),
    Input("cmp-metric",       "value"),
    Input("pr-files",         "value"),
    Input("pr-x",             "value"),
    Input("pr-y",             "value"),
)
def render_tab(tab, hw, model, backend, profile,
               cmp_a, cmp_b, cmp_metric,
               pr_files, pr_x, pr_y):

    df = _apply_filters(_get_df(), hw, model, backend, profile)

    hidden = {"display": "none"}
    shown  = {"display": "block"}

    cmp_style = shown if tab == "tab-comparison" else hidden
    pr_style  = shown if tab == "tab-perreq"     else hidden

    if df.empty:
        content = html.Div(
            "No matching data for current filters.",
            style={
                "color": "var(--text-muted)",
                "textAlign": "center",
                "padding": "80px 0",
                "fontSize": "15px",
            }
        )
        return content, cmp_style, pr_style

    if tab == "tab-latency":
        content = _render_latency(df)
    elif tab == "tab-throughput":
        content = _render_throughput(df)
    elif tab == "tab-comparison":
        content = _render_comparison_chart(df, cmp_a, cmp_b, cmp_metric)
    elif tab == "tab-perreq":
        content = _render_per_request_chart(pr_files, pr_x, pr_y)
    elif tab == "tab-raw":
        content = _render_raw(df)
    else:
        content = html.Div("Select a tab")

    return content, cmp_style, pr_style


# ---------------------------------------------------------------------------
# Tab renderers
# ---------------------------------------------------------------------------

def _chart_card(graph_element) -> html.Div:
    """Wrap a dcc.Graph in a styled card."""
    return html.Div(className="chart-card", children=[graph_element])


def _render_latency(df: pd.DataFrame) -> html.Div:
    return html.Div([
        html.Div(className="chart-grid-2", children=[
            _chart_card(dcc.Graph(
                figure=charts.latency_vs_concurrency(df, "ttft"),
                style={"height": "420px"},
                config={"displayModeBar": True, "displaylogo": False,
                        "modeBarButtonsToRemove": ["select2d", "lasso2d"]},
            )),
            _chart_card(dcc.Graph(
                figure=charts.latency_vs_concurrency(df, "tpot"),
                style={"height": "420px"},
                config={"displayModeBar": True, "displaylogo": False,
                        "modeBarButtonsToRemove": ["select2d", "lasso2d"]},
            )),
        ]),
        html.Div(style={"marginTop": "16px"}, children=[
            _chart_card(dcc.Graph(
                figure=charts.latency_vs_concurrency(df, "e2el"),
                style={"height": "380px"},
                config={"displayModeBar": True, "displaylogo": False,
                        "modeBarButtonsToRemove": ["select2d", "lasso2d"]},
            )),
        ]),
    ])


def _render_throughput(df: pd.DataFrame) -> html.Div:
    return html.Div([
        html.Div(className="chart-grid-2", children=[
            _chart_card(dcc.Graph(
                figure=charts.throughput_vs_concurrency(df, "output_token"),
                style={"height": "420px"},
                config={"displayModeBar": True, "displaylogo": False,
                        "modeBarButtonsToRemove": ["select2d", "lasso2d"]},
            )),
            _chart_card(dcc.Graph(
                figure=charts.throughput_vs_concurrency(df, "total_token"),
                style={"height": "420px"},
                config={"displayModeBar": True, "displaylogo": False,
                        "modeBarButtonsToRemove": ["select2d", "lasso2d"]},
            )),
        ]),
        html.Div(style={"marginTop": "16px"}, children=[
            _chart_card(dcc.Graph(
                figure=charts.throughput_vs_concurrency(df, "request"),
                style={"height": "380px"},
                config={"displayModeBar": True, "displaylogo": False,
                        "modeBarButtonsToRemove": ["select2d", "lasso2d"]},
            )),
        ]),
    ])


def _render_comparison_chart(df, series_a, series_b, metric):
    series_list = sorted(df["series"].unique().tolist())
    if len(series_list) < 2:
        return html.Div(
            html.P(
                "Need at least 2 series to compare. Try adjusting your filters.",
                style={"color": "var(--text-muted)", "padding": "60px",
                       "textAlign": "center", "fontSize": "14px"}
            )
        )
    if not series_a or not series_b or not metric:
        return _chart_card(dcc.Graph(
            figure=_empty_fig("Select two series and a metric above"),
            style={"height": "500px"},
        ))
    return _chart_card(dcc.Graph(
        figure=charts.comparison_chart(df, series_a, series_b, metric),
        style={"height": "520px"},
        config={"displayModeBar": True, "displaylogo": False,
                "modeBarButtonsToRemove": ["select2d", "lasso2d"]},
    ))


def _render_per_request_chart(files, x_col, y_col):
    if not files:
        return _chart_card(dcc.Graph(
            figure=_empty_fig("Select at least one result file above"),
            style={"height": "550px"},
        ))

    frames = []
    for fp in files:
        pr_df = load_per_request(Path(fp))
        if pr_df is not None:
            frames.append(pr_df)

    if not frames:
        return _chart_card(dcc.Graph(
            figure=_empty_fig("No per-request data found in selected files"),
            style={"height": "550px"},
        ))

    combined = pd.concat(frames, ignore_index=True)
    if "success" in combined.columns:
        combined = combined[combined["success"] == True]

    if x_col not in combined.columns or y_col not in combined.columns:
        return _chart_card(dcc.Graph(
            figure=_empty_fig("Column not found in per-request data"),
            style={"height": "550px"},
        ))

    return _chart_card(dcc.Graph(
        figure=charts.per_request_scatter(combined, x=x_col, y=y_col, color_by="filename"),
        style={"height": "570px"},
        config={"displayModeBar": True, "displaylogo": False,
                "modeBarButtonsToRemove": ["select2d", "lasso2d"]},
    ))


def _render_raw(df: pd.DataFrame):
    display_cols = [
        "hardware", "model_short", "backend", "profile", "concurrency",
        "successful_requests", "failed_requests",
        "output_tok_s", "total_tok_s", "request_throughput",
        "median_ttft_ms", "p99_ttft_ms",
        "median_tpot_ms", "p99_tpot_ms",
        "median_e2el_ms", "p99_e2el_ms",
        "filename",
    ]
    display_cols = [c for c in display_cols if c in df.columns]

    col_labels = {
        "hardware": "Hardware", "model_short": "Model", "backend": "Backend",
        "profile": "Profile", "concurrency": "Conc",
        "successful_requests": "OK", "failed_requests": "Fail",
        "output_tok_s": "Out Tok/s", "total_tok_s": "Tot Tok/s",
        "request_throughput": "Req/s",
        "median_ttft_ms": "TTFT p50", "p99_ttft_ms": "TTFT p99",
        "median_tpot_ms": "TPOT p50", "p99_tpot_ms": "TPOT p99",
        "median_e2el_ms": "E2EL p50", "p99_e2el_ms": "E2EL p99",
        "filename": "File",
    }

    display_df = df[display_cols].copy()
    for col in display_df.select_dtypes(include=["float64", "float32"]).columns:
        display_df[col] = display_df[col].round(1)

    return html.Div([
        dash_table.DataTable(
            data=display_df.to_dict("records"),
            columns=[{"name": col_labels.get(c, c), "id": c} for c in display_cols],
            sort_action="native",
            filter_action="native",
            page_size=50,
            style_table={
                "overflowX": "auto",
                "borderRadius": "var(--radius-md)",
                "overflow": "hidden",
                "border": "1px solid var(--border-light)",
            },
            style_header={
                "backgroundColor": "#1c2128",
                "color": "var(--text-secondary)",
                "fontWeight": "600",
                "fontSize": "11px",
                "letterSpacing": "0.06em",
                "textTransform": "uppercase",
                "border": "none",
                "borderBottom": "1px solid #30363d",
                "padding": "10px 14px",
                "fontFamily": "DM Sans, sans-serif",
            },
            style_cell={
                "backgroundColor": "#161b22",
                "color": "#e6edf3",
                "fontSize": "12px",
                "fontFamily": "JetBrains Mono, monospace",
                "padding": "9px 14px",
                "border": "none",
                "borderBottom": "1px solid #21262d",
                "textAlign": "center",
                "minWidth": "72px",
            },
            style_filter={
                "backgroundColor": "#1c2128",
                "color": "#8b949e",
                "border": "none",
                "borderBottom": "1px solid #30363d",
                "fontSize": "12px",
                "fontFamily": "JetBrains Mono, monospace",
            },
            style_data_conditional=[
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": "#1c2128",
                },
                {
                    "if": {"filter_query": "{failed_requests} > 0",
                           "column_id": "failed_requests"},
                    "color": "#ef5350",
                    "fontWeight": "700",
                },
                {
                    "if": {"column_id": ["hardware", "model_short", "backend",
                                         "profile", "filename"]},
                    "textAlign": "left",
                    "fontFamily": "DM Sans, sans-serif",
                    "color": "#8b949e",
                },
                {
                    "if": {"column_id": "concurrency"},
                    "color": "#00bcd4",
                    "fontWeight": "600",
                },
            ],
        ),
    ])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
