"""Interactive investment-committee dashboard for Project Redwood.

The dashboard is deliberately presentation-oriented. It does not introduce new
model logic; it visualises the same deterministic and simulated outputs exported
by the core underwriting engine so every chart can be reconciled to CSV files.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .risk_engine import DealInputs

NAVY = "#0B1F33"
BLUE = "#2563EB"
TEAL = "#0F766E"
GREEN = "#15803D"
RED = "#B91C1C"
AMBER = "#D97706"
GRAY = "#64748B"
LIGHT = "#F1F5F9"


def _base_layout(title: str) -> dict:
    return {
        "title": {"text": title, "x": 0.0, "xanchor": "left", "font": {"size": 18, "color": NAVY}},
        "paper_bgcolor": "white",
        "plot_bgcolor": "white",
        "font": {"family": "Arial, sans-serif", "color": NAVY},
        "margin": {"l": 55, "r": 25, "t": 60, "b": 50},
        "height": 420,
        "showlegend": True,
        "legend": {"orientation": "h", "y": 1.08, "x": 0.0},
    }


def build_dashboard(
    simulation: pd.DataFrame,
    curve: pd.DataFrame,
    drivers: pd.DataFrame,
    scenarios: pd.DataFrame,
    scorecard: pd.DataFrame,
    p: DealInputs,
    output_path: str | Path,
) -> Path:
    """Build a self-contained HTML dashboard from already-computed outputs."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1) IRR distribution
    irr = simulation["gross_irr"] * 100
    fig_irr = go.Figure()
    fig_irr.add_histogram(x=irr, nbinsx=55, marker_color=BLUE, opacity=0.78, name="Synthetic paths")
    fig_irr.add_vline(x=p.target_irr * 100, line_color=RED, line_dash="dash", annotation_text="25% hurdle")
    fig_irr.add_vline(x=float(irr.median()), line_color=NAVY, annotation_text=f"Median {irr.median():.1f}%")
    fig_irr.update_layout(**_base_layout("Gross IRR distribution"))
    fig_irr.update_xaxes(title="Gross IRR (%)", gridcolor="#E5E7EB")
    fig_irr.update_yaxes(title="Path count", gridcolor="#E5E7EB")

    # 2) Bid probability curve
    fig_bid = go.Figure()
    fig_bid.add_scatter(
        x=curve["Entry EV / EBITDA"],
        y=curve["Probability IRR >= 25%"] * 100,
        mode="lines+markers",
        line={"color": TEAL, "width": 3},
        marker={"size": 6},
        name="P(IRR >= 25%)",
        hovertemplate="Entry: %{x:.1f}x<br>Probability: %{y:.1f}%<extra></extra>",
    )
    fig_bid.add_hline(y=50, line_color=GRAY, line_dash="dash")
    fig_bid.add_hline(y=75, line_color=GRAY, line_dash="dot")
    fig_bid.add_vline(x=p.entry_multiple, line_color=RED, line_dash="dash", annotation_text="Seller ask 8.5x")
    fig_bid.update_layout(**_base_layout("Probability of clearing the 25% IRR hurdle"))
    fig_bid.update_xaxes(title="Entry EV / EBITDA (x)", gridcolor="#E5E7EB")
    fig_bid.update_yaxes(title="Probability (%)", range=[0, 100], gridcolor="#E5E7EB")

    # 3) Driver sensitivity
    ordered = drivers.sort_values("Spearman correlation with gross IRR")
    vals = ordered["Spearman correlation with gross IRR"]
    fig_drv = go.Figure(
        go.Bar(
            x=vals,
            y=ordered["Driver"],
            orientation="h",
            marker_color=[GREEN if v >= 0 else RED for v in vals],
            hovertemplate="%{y}<br>Correlation: %{x:.2f}<extra></extra>",
        )
    )
    fig_drv.add_vline(x=0, line_color=NAVY)
    fig_drv.update_layout(**_base_layout("What drives gross IRR?"))
    fig_drv.update_xaxes(title="Spearman rank correlation", gridcolor="#E5E7EB")
    fig_drv.update_yaxes(title="")

    # 4) Scenario returns
    fig_scn = make_subplots(specs=[[{"secondary_y": True}]])
    fig_scn.add_bar(
        x=scenarios["Scenario"],
        y=scenarios["gross_irr"] * 100,
        name="Gross IRR",
        marker_color=BLUE,
        secondary_y=False,
    )
    fig_scn.add_scatter(
        x=scenarios["Scenario"],
        y=scenarios["gross_moic"],
        mode="lines+markers",
        name="Gross MOIC",
        line={"color": TEAL, "width": 3},
        marker={"size": 8},
        secondary_y=True,
    )
    fig_scn.add_hline(y=25, line_color=RED, line_dash="dash", secondary_y=False)
    fig_scn.update_layout(**_base_layout("Downside / base / upside returns"))
    fig_scn.update_yaxes(title_text="Gross IRR (%)", gridcolor="#E5E7EB", secondary_y=False)
    fig_scn.update_yaxes(title_text="Gross MOIC (x)", secondary_y=True)

    score = dict(zip(scorecard["Metric"], scorecard["Value"]))
    ask = score["Seller ask"]
    base_irr = score["Base-case gross IRR"]
    det_bid = score["Deterministic max bid"]
    p50 = score["Risk-adjusted bid ceiling - 50% threshold"]
    prob_at_ask = score["P(IRR >= 25%) at ask"]

    figures = [
        fig_irr.to_html(full_html=False, include_plotlyjs="inline", config={"displaylogo": False, "responsive": True}),
        fig_bid.to_html(full_html=False, include_plotlyjs=False, config={"displaylogo": False, "responsive": True}),
        fig_drv.to_html(full_html=False, include_plotlyjs=False, config={"displaylogo": False, "responsive": True}),
        fig_scn.to_html(full_html=False, include_plotlyjs=False, config={"displaylogo": False, "responsive": True}),
    ]

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Project Redwood - Interactive IC Dashboard</title>
<style>
  body {{ margin:0; font-family: Arial, sans-serif; background:#F8FAFC; color:{NAVY}; }}
  .wrap {{ max-width:1220px; margin:0 auto; padding:30px 24px 48px; }}
  .hero {{ background:{NAVY}; color:white; border-radius:18px; padding:30px 32px; }}
  .eyebrow {{ color:#94A3B8; font-size:12px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; }}
  h1 {{ font-size:34px; margin:8px 0 10px; line-height:1.08; }}
  .sub {{ color:#CBD5E1; max-width:820px; line-height:1.5; }}
  .kpis {{ display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin-top:22px; }}
  .kpi {{ background:white; color:{NAVY}; border-radius:12px; padding:15px 16px; }}
  .kpi strong {{ display:block; font-size:23px; margin-bottom:4px; }}
  .kpi span {{ color:{GRAY}; font-size:12px; }}
  .section {{ margin-top:24px; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
  .card {{ background:white; border:1px solid #E2E8F0; border-radius:14px; padding:8px 10px 2px; }}
  .decision {{ background:#FFF7ED; border-left:5px solid {AMBER}; border-radius:12px; padding:18px 20px; margin-top:18px; line-height:1.5; }}
  .foot {{ color:{GRAY}; font-size:12px; margin-top:22px; line-height:1.45; }}
  @media (max-width:900px) {{ .grid,.kpis {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="wrap">
  <section class="hero">
    <div class="eyebrow">Take-Private Reverse LBO & Probabilistic Underwriting</div>
    <h1>Project Redwood - Interactive Investment Committee Dashboard</h1>
    <div class="sub">A fictional private equity case study built around one question: what is the highest price a sponsor can pay while preserving return hurdles, debt capacity and downside protection?</div>
    <div class="kpis">
      <div class="kpi"><strong>{ask:.1f}x</strong><span>Seller ask</span></div>
      <div class="kpi"><strong>{base_irr:.1%}</strong><span>Base-case gross IRR</span></div>
      <div class="kpi"><strong>{det_bid:.1f}x</strong><span>Deterministic max bid</span></div>
      <div class="kpi"><strong>{p50:.1f}x</strong><span>50% probability bid ceiling</span></div>
      <div class="kpi"><strong>{prob_at_ask:.1%}</strong><span>P(IRR >= 25%) at ask</span></div>
    </div>
  </section>

  <div class="decision"><strong>IC framing:</strong> the 8.5x ask produces an attractive MOIC, but misses the 25% gross IRR hurdle in the deterministic case. The reverse LBO and probability curve therefore turn the model into a bid-discipline exercise rather than a template that simply forces the deal to work.</div>

  <section class="section grid">
    <div class="card">{figures[0]}</div>
    <div class="card">{figures[1]}</div>
    <div class="card">{figures[2]}</div>
    <div class="card">{figures[3]}</div>
  </section>

  <div class="foot">All company data, transaction terms and outputs are synthetic and created for educational purposes. The dashboard visualises the same outputs exported by the Python engine; it is not live market data or an investment recommendation.</div>
</div>
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    return output_path
