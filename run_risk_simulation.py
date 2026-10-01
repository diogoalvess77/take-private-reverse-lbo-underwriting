
"""Command-line runner for Project Redwood.

The script keeps the workflow deliberately simple:
1. run the probabilistic underwriting engine;
2. export auditable CSVs;
3. save investor-style charts; and
4. print the decision headlines that matter for an IC discussion.
"""
from __future__ import annotations

from pathlib import Path
import argparse

import matplotlib.pyplot as plt
import numpy as np

from src.dashboard import build_dashboard
from src.risk_engine import (
    DealInputs,
    bid_ceiling_for_probability,
    bid_probability_curve,
    decision_scorecard,
    deterministic_base_case,
    driver_correlations,
    hurdle_solver,
    reverse_lbo_max_entry_multiple,
    scenario_cases,
    simulate,
    summarise,
)

COLORS = {
    "navy": "#0B1F33",
    "blue": "#2563EB",
    "teal": "#0F766E",
    "amber": "#D97706",
    "red": "#B91C1C",
    "green": "#15803D",
    "gray": "#64748B",
    "light": "#F1F5F9",
}


def _style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, axis="y", color="#E5E7EB", linewidth=0.8)
    ax.set_axisbelow(True)


def _save_irr_distribution(df, p: DealInputs, out: Path, paths: int) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.8))
    irr = df["gross_irr"] * 100
    ax.hist(irr, bins=55, color=COLORS["blue"], alpha=0.75, edgecolor="white", linewidth=0.4)
    ax.axvline(p.target_irr * 100, color=COLORS["red"], linestyle="--", linewidth=2, label="25% IRR hurdle")
    ax.axvline(irr.median(), color=COLORS["navy"], linewidth=2, label=f"Median {irr.median():.1f}%")
    _style_ax(ax)
    ax.set_title(f"Gross IRR Distribution - {paths:,} Synthetic Deal Paths", loc="left", fontsize=14, fontweight="bold")
    ax.set_xlabel("Gross IRR (%)")
    ax.set_ylabel("Path count")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(out / "irr_distribution.png", dpi=220)
    plt.close(fig)


def _save_bid_probability_curve(curve, p: DealInputs, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.plot(curve["Entry EV / EBITDA"], curve["Probability IRR >= 25%"] * 100, marker="o", markersize=4,
            color=COLORS["teal"], linewidth=2.5)
    ax.axhline(50, color=COLORS["gray"], linestyle="--", linewidth=1.2)
    ax.axhline(75, color=COLORS["gray"], linestyle=":", linewidth=1.2)
    ax.axvline(p.entry_multiple, color=COLORS["red"], linestyle="--", linewidth=1.8, label=f"Seller ask: {p.entry_multiple:.1f}x")
    _style_ax(ax)
    ax.set_title("Probability of Meeting 25% IRR Hurdle vs Entry Multiple", loc="left", fontsize=14, fontweight="bold")
    ax.set_xlabel("Entry EV / EBITDA (x)")
    ax.set_ylabel("Probability (%)")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(out / "bid_probability_curve.png", dpi=220)
    plt.close(fig)


def _save_exit_multiple_scatter(df, p: DealInputs, out: Path, seed: int) -> None:
    sample = df.sample(min(len(df), 3000), random_state=seed)
    fig, ax = plt.subplots(figsize=(10, 5.8))
    hit = sample["gross_irr"] >= p.target_irr
    ax.scatter(sample.loc[~hit, "exit_multiple"], sample.loc[~hit, "gross_irr"] * 100, s=10, alpha=0.28, color=COLORS["gray"], label="Below hurdle")
    ax.scatter(sample.loc[hit, "exit_multiple"], sample.loc[hit, "gross_irr"] * 100, s=10, alpha=0.42, color=COLORS["green"], label="Meets hurdle")
    ax.axhline(p.target_irr * 100, color=COLORS["red"], linestyle="--", linewidth=1.5)
    _style_ax(ax)
    ax.set_title("Exit Multiple vs Gross IRR", loc="left", fontsize=14, fontweight="bold")
    ax.set_xlabel("Exit EV / EBITDA (x)")
    ax.set_ylabel("Gross IRR (%)")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(out / "exit_multiple_vs_irr.png", dpi=220)
    plt.close(fig)


def _save_driver_sensitivity(drivers, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.8))
    plot_df = drivers.iloc[::-1]
    vals = plot_df["Spearman correlation with gross IRR"]
    colors = [COLORS["green"] if x >= 0 else COLORS["red"] for x in vals]
    ax.barh(plot_df["Driver"], vals, color=colors, alpha=0.85)
    ax.axvline(0, color=COLORS["navy"], linewidth=1)
    _style_ax(ax)
    ax.grid(True, axis="x", color="#E5E7EB", linewidth=0.8)
    ax.set_title("Deal Outcome Sensitivity - Rank Correlation with Gross IRR", loc="left", fontsize=14, fontweight="bold")
    ax.set_xlabel("Spearman correlation")
    fig.tight_layout()
    fig.savefig(out / "driver_sensitivity.png", dpi=220)
    plt.close(fig)


def _save_bid_gap_chart(p: DealInputs, out: Path) -> None:
    rev = reverse_lbo_max_entry_multiple(p)
    df = [("75% probability\nceiling", 7.5), ("50% probability\nceiling", 8.0), ("Deterministic\nmax bid", rev["max_entry_multiple"]), ("Seller\nask", p.entry_multiple)]
    fig, ax = plt.subplots(figsize=(10, 5.8))
    labels = [x[0] for x in df]
    values = [x[1] for x in df]
    colors = [COLORS["teal"], COLORS["blue"], COLORS["amber"], COLORS["red"]]
    bars = ax.bar(labels, values, color=colors, alpha=0.9)
    ax.set_ylim(6.5, 8.8)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.04, f"{val:.1f}x", ha="center", va="bottom", fontweight="bold")
    _style_ax(ax)
    ax.set_title("Bid Discipline: Ask vs Underwritable Price", loc="left", fontsize=14, fontweight="bold")
    ax.set_ylabel("Entry EV / EBITDA")
    fig.tight_layout()
    fig.savefig(out / "bid_gap_chart.png", dpi=220)
    plt.close(fig)


def _save_scenario_cases(cases, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.8))
    x = np.arange(len(cases))
    width = 0.35
    ax.bar(x - width/2, cases["gross_irr"] * 100, width, label="Gross IRR", color=COLORS["blue"], alpha=0.9)
    ax.bar(x + width/2, cases["gross_moic"], width, label="Gross MOIC", color=COLORS["teal"], alpha=0.9)
    ax.axhline(25, color=COLORS["red"], linestyle="--", linewidth=1.2, label="25% IRR hurdle")
    ax.set_xticks(x, cases["Scenario"])
    _style_ax(ax)
    ax.set_title("Downside / Base / Upside Case Outputs", loc="left", fontsize=14, fontweight="bold")
    ax.set_ylabel("IRR (%) / MOIC (x)")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(out / "scenario_cases.png", dpi=220)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Project Redwood probabilistic LBO underwriting.")
    parser.add_argument("--paths", type=int, default=10_000, help="Number of simulated deal paths")
    parser.add_argument("--seed", type=int, default=77, help="Random seed")
    parser.add_argument("--output", default="outputs", help="Output directory")
    args = parser.parse_args()

    if args.paths < 100:
        raise SystemExit("Use at least 100 paths for a meaningful demonstration.")

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    p = DealInputs()

    df = simulate(n=args.paths, seed=args.seed, p=p)
    summary = summarise(df, p)
    drivers = driver_correlations(df)
    curve = bid_probability_curve(df, p)
    cases = scenario_cases(p)
    scorecard = decision_scorecard(df, p)
    reverse = reverse_lbo_max_entry_multiple(p)
    hurdle = hurdle_solver(p)
    base = deterministic_base_case(p)

    # Audit-friendly exports
    df.to_csv(out / "simulation_paths.csv", index=False)
    summary.to_csv(out / "simulation_summary.csv", index=False)
    drivers.to_csv(out / "driver_correlations.csv", index=False)
    curve.to_csv(out / "bid_probability_curve.csv", index=False)
    cases.to_csv(out / "scenario_cases.csv", index=False)
    scorecard.to_csv(out / "decision_scorecard.csv", index=False)
    # reverse/hurdle/base are stored as one-row tables for easier review
    import pandas as pd
    pd.DataFrame([base]).to_csv(out / "deterministic_base_case.csv", index=False)
    pd.DataFrame([reverse]).to_csv(out / "reverse_lbo_summary.csv", index=False)
    pd.DataFrame([hurdle]).to_csv(out / "hurdle_solver_summary.csv", index=False)

    # Visuals for README / LinkedIn / IC deck
    _save_irr_distribution(df, p, out, args.paths)
    _save_bid_probability_curve(curve, p, out)
    _save_exit_multiple_scatter(df, p, out, args.seed)
    _save_driver_sensitivity(drivers, out)
    _save_bid_gap_chart(p, out)
    _save_scenario_cases(cases, out)
    build_dashboard(df, curve, drivers, cases, scorecard, p, out / "model_results_dashboard.html")

    p50 = bid_ceiling_for_probability(curve, 0.50)
    p75 = bid_ceiling_for_probability(curve, 0.75)

    print("TAKE-PRIVATE REVERSE LBO & PROBABILISTIC UNDERWRITING")
    print("Case name: Project Redwood")
    print(f"Paths: {len(df):,} | Seed: {args.seed}")
    print(f"Seller ask: {p.entry_multiple:.1f}x EBITDA")
    print(f"Base-case gross IRR / MOIC: {base['gross_irr']:.1%} / {base['gross_moic']:.2f}x")
    print(f"Deterministic max entry multiple: {reverse['max_entry_multiple']:.1f}x")
    print(f"P(IRR >= 25%) at the ask: {df['irr_hurdle_met'].mean():.1%}")
    print(f"P(both hurdles): {df['both_hurdles_met'].mean():.1%}")
    print(f"P(interest coverage < 2.0x): {df['covenant_breach'].mean():.1%}")
    print(f"Risk-adjusted bid ceiling @ >=50% chance of 25% IRR: {p50:.1f}x")
    print(f"Risk-adjusted bid ceiling @ >=75% chance of 25% IRR: {p75:.1f}x")
    print(f"Outputs written to: {out.resolve()}")


if __name__ == "__main__":
    main()
