
"""Project Redwood risk engine.

This file is deliberately written as a readable companion to the Excel model,
not as an abstract quant library. The aim is to make the deal logic easy to
follow in an interview: start with a purchase price, run the operating case,
pay down debt, exit the business, and then ask whether the sponsor return is
strong enough for the risk taken.

All assumptions are synthetic and educational. Nothing here represents a real
company, live market data or investment advice.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, Tuple

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DealInputs:
    """Core assumptions for the fictional take-private case.

    Units are USD millions unless explicitly stated otherwise. Hardcoded values
    are kept here so the Python layer has a single source of truth and can be
    tested against the Excel model.
    """

    # Operating starting point
    ltm_revenue: float = 325.0
    ltm_ebitda_margin: float = 0.19
    revenue_growth: Tuple[float, ...] = (0.07, 0.06, 0.05, 0.04, 0.04)
    ebitda_margin: Tuple[float, ...] = (0.195, 0.20, 0.205, 0.208, 0.21)
    da_pct_revenue: float = 0.03
    capex_pct_revenue: float = 0.032
    nwc_pct_revenue: float = 0.085
    cash_tax_rate: float = 0.25

    # Transaction assumptions
    existing_net_debt: float = 45.0
    minimum_cash: float = 10.0
    transaction_fee_pct_ev: float = 0.02
    financing_fee_pct_debt: float = 0.02
    management_rollover_pct_equity: float = 0.08
    hold_period: int = 5
    entry_multiple: float = 8.5
    exit_multiple: float = 9.5

    # Sponsor hurdle rates
    target_irr: float = 0.25
    target_moic: float = 2.5

    # Financing package
    tlb_leverage: float = 4.0
    tlb_spread: float = 0.0425
    base_rate: float = 0.035
    base_rate_floor: float = 0.02
    tlb_amort_pct_original: float = 0.01
    second_lien_leverage: float = 1.0
    second_lien_coupon: float = 0.095
    rcf_capacity_leverage: float = 0.5
    rcf_spread: float = 0.0475
    cash_sweep_pct: float = 0.75
    minimum_interest_coverage: float = 2.0

    @property
    def ltm_ebitda(self) -> float:
        return self.ltm_revenue * self.ltm_ebitda_margin

    @property
    def original_tlb(self) -> float:
        return self.tlb_leverage * self.ltm_ebitda

    @property
    def second_lien(self) -> float:
        return self.second_lien_leverage * self.ltm_ebitda

    @property
    def debt_sources(self) -> float:
        return self.original_tlb + self.second_lien

    @property
    def rcf_capacity(self) -> float:
        return self.rcf_capacity_leverage * self.ltm_ebitda


def enterprise_value(entry_multiple: float, p: DealInputs) -> float:
    """Entry enterprise value implied by the selected EBITDA multiple."""
    return float(entry_multiple) * p.ltm_ebitda


def sponsor_equity_for_entry_multiple(entry_multiple: float, p: DealInputs) -> float:
    """Sponsor equity cheque after debt financing and management rollover.

    The calculation follows the Sources & Uses logic used in the Excel model.
    It intentionally excludes management rollover from sponsor cash equity,
    because the sponsor does not fund that rolled portion at close.
    """
    ev = enterprise_value(entry_multiple, p)
    financing_fees = p.financing_fee_pct_debt * p.debt_sources
    uses = ev + p.minimum_cash + p.transaction_fee_pct_ev * ev + financing_fees
    total_equity = uses - p.debt_sources
    return (1.0 - p.management_rollover_pct_equity) * total_equity


def run_path(
    p: DealInputs,
    growth: np.ndarray,
    margins: np.ndarray,
    base_rates: np.ndarray,
    exit_multiple: float,
    entry_multiple: float | None = None,
) -> Dict[str, float]:
    """Run one operating/debt/exit path.

    This is the core engine. It is purposefully close to the Excel waterfall so
    that each line maps to an underwriting concept: revenue growth, margins,
    tax, capex, working capital, interest, mandatory amortisation, revolver
    usage, cash sweep, net debt and sponsor returns.
    """
    entry_multiple = p.entry_multiple if entry_multiple is None else float(entry_multiple)
    revenue = p.ltm_revenue
    prior_nwc = revenue * p.nwc_pct_revenue
    cash = p.minimum_cash
    tlb = p.original_tlb
    second_lien = p.second_lien
    rcf = 0.0
    original_tlb = p.original_tlb

    min_coverage = np.inf
    max_rcf = 0.0
    last_ebitda = p.ltm_ebitda
    cumulative_fcf_before_debt_paydown = 0.0

    for year in range(p.hold_period):
        # 1) Operating case
        revenue *= 1.0 + float(growth[year])
        margin = float(margins[year])
        ebitda = revenue * margin
        da = revenue * p.da_pct_revenue
        ebit = ebitda - da
        capex = revenue * p.capex_pct_revenue
        nwc = revenue * p.nwc_pct_revenue
        delta_nwc = nwc - prior_nwc
        taxes = max(ebit, 0.0) * p.cash_tax_rate
        pre_interest_fcf = ebitda - capex - delta_nwc - taxes
        cumulative_fcf_before_debt_paydown += pre_interest_fcf

        # 2) Cash interest. Floating-rate debt is subject to a base-rate floor.
        tlb_rate = max(float(base_rates[year]), p.base_rate_floor) + p.tlb_spread
        rcf_rate = max(float(base_rates[year]), p.base_rate_floor) + p.rcf_spread
        tlb_interest = tlb * tlb_rate
        second_interest = second_lien * p.second_lien_coupon
        rcf_interest = rcf * rcf_rate
        total_interest = tlb_interest + second_interest + rcf_interest
        coverage = ebitda / total_interest if total_interest > 0 else np.inf
        min_coverage = min(min_coverage, coverage)

        # 3) Mandatory amortisation comes before discretionary cash sweep.
        mandatory = min(original_tlb * p.tlb_amort_pct_original, tlb)
        cash_before_actions = cash + pre_interest_fcf - total_interest - mandatory

        # 4) Revolver acts as the liquidity backstop when minimum cash is breached.
        if cash_before_actions < p.minimum_cash:
            required = p.minimum_cash - cash_before_actions
            available = max(p.rcf_capacity - rcf, 0.0)
            draw = min(required, available)
            rcf += draw
            cash_before_actions += draw

        # 5) Repay revolver before sweeping excess cash to the term loan.
        if cash_before_actions > p.minimum_cash and rcf > 0:
            excess = cash_before_actions - p.minimum_cash
            repay = min(excess, rcf)
            rcf -= repay
            cash_before_actions -= repay

        excess_after_rcf = max(cash_before_actions - p.minimum_cash, 0.0)
        tlb_sweep = min(p.cash_sweep_pct * excess_after_rcf, max(tlb - mandatory, 0.0))
        cash = cash_before_actions - tlb_sweep
        tlb = max(tlb - mandatory - tlb_sweep, 0.0)

        max_rcf = max(max_rcf, rcf)
        prior_nwc = nwc
        last_ebitda = ebitda

    gross_debt = tlb + second_lien + rcf
    net_debt = gross_debt - cash
    exit_ev = last_ebitda * exit_multiple
    exit_equity = max(exit_ev - net_debt, 0.0)
    sponsor_exit = (1.0 - p.management_rollover_pct_equity) * exit_equity
    sponsor_initial = sponsor_equity_for_entry_multiple(entry_multiple, p)
    moic = sponsor_exit / sponsor_initial if sponsor_initial > 0 else np.nan
    irr = moic ** (1.0 / p.hold_period) - 1.0 if moic > 0 else -1.0

    return {
        "exit_ebitda": last_ebitda,
        "exit_multiple": exit_multiple,
        "exit_ev": exit_ev,
        "exit_net_debt": net_debt,
        "sponsor_exit_proceeds": sponsor_exit,
        "sponsor_initial_equity": sponsor_initial,
        "gross_moic": moic,
        "gross_irr": irr,
        "minimum_interest_coverage": min_coverage,
        "maximum_rcf_draw": max_rcf,
        "ending_tlb": tlb,
        "ending_second_lien": second_lien,
        "ending_rcf": rcf,
        "ending_cash": cash,
        "cumulative_fcf_before_debt_paydown": cumulative_fcf_before_debt_paydown,
    }


def deterministic_base_case(p: DealInputs | None = None) -> Dict[str, float]:
    """The fixed base case used to reconcile Python to the Excel model."""
    p = p or DealInputs()
    return run_path(
        p,
        np.asarray(p.revenue_growth, dtype=float),
        np.asarray(p.ebitda_margin, dtype=float),
        np.repeat(p.base_rate, p.hold_period),
        p.exit_multiple,
    )


def reverse_lbo_max_entry_multiple(p: DealInputs | None = None) -> Dict[str, float]:
    """Solve the maximum entry multiple that satisfies the sponsor's return hurdles.

    Rather than forcing the asking price to work, this function converts target
    returns into a maximum sponsor equity cheque and then backs into the EV that
    can be supported after fees, debt financing and rollover.
    """
    p = p or DealInputs()
    base = deterministic_base_case(p)
    sponsor_exit = base["sponsor_exit_proceeds"]

    max_equity_from_irr = sponsor_exit / ((1.0 + p.target_irr) ** p.hold_period)
    max_equity_from_moic = sponsor_exit / p.target_moic
    max_sponsor_equity = min(max_equity_from_irr, max_equity_from_moic)
    binding = "IRR" if max_equity_from_irr <= max_equity_from_moic else "MOIC"

    # Reverse the same sponsor equity formula used in Sources & Uses.
    total_equity = max_sponsor_equity / (1.0 - p.management_rollover_pct_equity)
    financing_fees = p.financing_fee_pct_debt * p.debt_sources
    max_ev = (total_equity + p.debt_sources - p.minimum_cash - financing_fees) / (1.0 + p.transaction_fee_pct_ev)
    max_multiple = max_ev / p.ltm_ebitda

    return {
        "max_sponsor_equity": max_sponsor_equity,
        "max_enterprise_value": max_ev,
        "max_entry_multiple": max_multiple,
        "binding_constraint": binding,
        "seller_ask_multiple": p.entry_multiple,
        "bid_gap_multiple": max_multiple - p.entry_multiple,
        "bid_gap_ev": max_ev - enterprise_value(p.entry_multiple, p),
    }


def hurdle_solver(p: DealInputs | None = None) -> Dict[str, float]:
    """Solve what has to improve to justify the seller's current asking price.

    Each output is a separate, isolated lever. It is not saying that all three
    changes are needed at the same time; it frames the negotiation question.
    """
    p = p or DealInputs()
    base = deterministic_base_case(p)
    required_sponsor_exit = base["sponsor_initial_equity"] * ((1.0 + p.target_irr) ** p.hold_period)
    required_exit_equity = required_sponsor_exit / (1.0 - p.management_rollover_pct_equity)

    required_exit_ev = required_exit_equity + base["exit_net_debt"]
    required_exit_ebitda = required_exit_ev / p.exit_multiple
    required_exit_multiple = required_exit_ev / base["exit_ebitda"]
    required_net_debt = base["exit_ev"] - required_exit_equity

    return {
        "required_exit_ebitda": required_exit_ebitda,
        "base_exit_ebitda": base["exit_ebitda"],
        "incremental_exit_ebitda_pct": required_exit_ebitda / base["exit_ebitda"] - 1.0,
        "required_exit_multiple": required_exit_multiple,
        "base_exit_multiple": p.exit_multiple,
        "required_exit_net_debt": required_net_debt,
        "base_exit_net_debt": base["exit_net_debt"],
        "additional_debt_paydown_needed": base["exit_net_debt"] - required_net_debt,
    }


def simulate(n: int = 10_000, seed: int = 77, p: DealInputs | None = None) -> pd.DataFrame:
    """Generate synthetic deal paths and run each through the LBO waterfall.

    The factor structure is intentionally simple enough to explain in an
    interview: a macro factor, an execution factor, a rates factor and a
    valuation factor. They are mixed into growth, margins, rates and exit
    multiples so that good or bad outcomes move together instead of being fully
    independent.
    """
    p = p or DealInputs()
    rng = np.random.default_rng(seed)

    z = rng.standard_normal((n, 4))
    macro, execution, rates, valuation = z.T

    growth_shift = 0.015 * (0.72 * macro + 0.52 * execution)
    margin_shift = 0.012 * (0.35 * macro + 0.86 * execution)
    rate_shift = 0.010 * (-0.45 * macro + 0.82 * rates)
    multiple_shift = 0.85 * (0.45 * macro + 0.30 * execution - 0.45 * rates + 0.60 * valuation)

    annual_growth_noise = rng.normal(0.0, 0.006, size=(n, p.hold_period))
    annual_margin_noise = rng.normal(0.0, 0.003, size=(n, p.hold_period))
    annual_rate_noise = rng.normal(0.0, 0.0025, size=(n, p.hold_period))

    base_growth = np.asarray(p.revenue_growth)
    base_margin = np.asarray(p.ebitda_margin)

    growth = np.clip(base_growth + growth_shift[:, None] + annual_growth_noise, -0.05, 0.18)
    margins = np.clip(base_margin + margin_shift[:, None] + annual_margin_noise, 0.12, 0.30)
    base_rates = np.clip(p.base_rate + rate_shift[:, None] + annual_rate_noise, 0.005, 0.10)
    exit_multiples = np.clip(p.exit_multiple + multiple_shift, 6.0, 13.0)

    rows = []
    for i in range(n):
        out = run_path(p, growth[i], margins[i], base_rates[i], float(exit_multiples[i]))
        out.update(
            {
                "path": i + 1,
                "growth_shift": growth_shift[i],
                "margin_shift": margin_shift[i],
                "rate_shift": rate_shift[i],
                "exit_multiple_shift": multiple_shift[i],
                "avg_revenue_growth": float(growth[i].mean()),
                "exit_margin": float(margins[i, -1]),
                "avg_base_rate": float(base_rates[i].mean()),
                "covenant_breach": float(out["minimum_interest_coverage"] < p.minimum_interest_coverage),
                "rcf_drawn": float(out["maximum_rcf_draw"] > 1e-9),
                "irr_hurdle_met": float(out["gross_irr"] >= p.target_irr),
                "moic_hurdle_met": float(out["gross_moic"] >= p.target_moic),
                "both_hurdles_met": float((out["gross_irr"] >= p.target_irr) and (out["gross_moic"] >= p.target_moic)),
            }
        )
        rows.append(out)

    return pd.DataFrame(rows)


def summarise(df: pd.DataFrame, p: DealInputs | None = None) -> pd.DataFrame:
    p = p or DealInputs()
    q = df["gross_irr"].quantile([0.05, 0.25, 0.50, 0.75, 0.95])
    m = df["gross_moic"].quantile([0.05, 0.25, 0.50, 0.75, 0.95])
    rows = [
        ("Simulated paths", float(len(df)), "count"),
        ("Mean gross IRR", float(df["gross_irr"].mean()), "%"),
        ("Median gross IRR", float(q.loc[0.50]), "%"),
        ("5th percentile gross IRR", float(q.loc[0.05]), "%"),
        ("95th percentile gross IRR", float(q.loc[0.95]), "%"),
        ("Median gross MOIC", float(m.loc[0.50]), "x"),
        ("5th percentile gross MOIC", float(m.loc[0.05]), "x"),
        ("95th percentile gross MOIC", float(m.loc[0.95]), "x"),
        ("Probability IRR >= 25%", float(df["irr_hurdle_met"].mean()), "%"),
        ("Probability MOIC >= 2.5x", float(df["moic_hurdle_met"].mean()), "%"),
        ("Probability both hurdles met", float(df["both_hurdles_met"].mean()), "%"),
        ("Probability interest coverage < 2.0x", float(df["covenant_breach"].mean()), "%"),
        ("Probability RCF draw", float(df["rcf_drawn"].mean()), "%"),
        ("Median exit net debt", float(df["exit_net_debt"].median()), "$mm"),
        ("Median exit EV / EBITDA", float(df["exit_multiple"].median()), "x"),
    ]
    return pd.DataFrame(rows, columns=["Metric", "Value", "Units"])


def driver_correlations(df: pd.DataFrame) -> pd.DataFrame:
    drivers = [
        "avg_revenue_growth",
        "exit_margin",
        "avg_base_rate",
        "exit_multiple",
        "exit_net_debt",
    ]
    corr = df[drivers + ["gross_irr"]].corr(method="spearman")["gross_irr"].drop("gross_irr")
    out = corr.rename("Spearman correlation with gross IRR").reset_index().rename(columns={"index": "Driver"})
    return out.reindex(out["Spearman correlation with gross IRR"].abs().sort_values(ascending=False).index).reset_index(drop=True)


def bid_probability_curve(df: pd.DataFrame, p: DealInputs | None = None) -> pd.DataFrame:
    p = p or DealInputs()
    sponsor_exit = df["sponsor_exit_proceeds"].to_numpy()
    multiples = np.round(np.arange(6.5, 9.51, 0.1), 2)
    rows = []
    for multiple in multiples:
        sponsor_initial = sponsor_equity_for_entry_multiple(float(multiple), p)
        moic = sponsor_exit / sponsor_initial
        irr = np.power(moic, 1.0 / p.hold_period) - 1.0
        rows.append(
            {
                "Entry EV / EBITDA": multiple,
                "Sponsor Equity ($mm)": sponsor_initial,
                "Probability IRR >= 25%": float(np.mean(irr >= p.target_irr)),
                "Probability MOIC >= 2.5x": float(np.mean(moic >= p.target_moic)),
                "Median IRR": float(np.median(irr)),
                "5th Percentile IRR": float(np.quantile(irr, 0.05)),
                "95th Percentile IRR": float(np.quantile(irr, 0.95)),
            }
        )
    return pd.DataFrame(rows)


def bid_ceiling_for_probability(curve: pd.DataFrame, threshold: float) -> float:
    eligible = curve.loc[curve["Probability IRR >= 25%"] >= threshold, "Entry EV / EBITDA"]
    return float(eligible.max()) if len(eligible) else float("nan")


def scenario_cases(p: DealInputs | None = None) -> pd.DataFrame:
    """Run simple downside/base/upside cases for the investment committee view."""
    p = p or DealInputs()
    scenarios = {
        "Downside": {
            "growth": tuple(g - 0.025 for g in p.revenue_growth),
            "margin": tuple(m - 0.012 for m in p.ebitda_margin),
            "rates": p.base_rate + 0.015,
            "exit_multiple": p.exit_multiple - 1.0,
        },
        "Base": {
            "growth": p.revenue_growth,
            "margin": p.ebitda_margin,
            "rates": p.base_rate,
            "exit_multiple": p.exit_multiple,
        },
        "Upside": {
            "growth": tuple(g + 0.020 for g in p.revenue_growth),
            "margin": tuple(m + 0.010 for m in p.ebitda_margin),
            "rates": max(p.base_rate - 0.005, 0.005),
            "exit_multiple": p.exit_multiple + 0.75,
        },
    }
    rows = []
    for name, s in scenarios.items():
        out = run_path(
            p,
            np.asarray(s["growth"], dtype=float),
            np.asarray(s["margin"], dtype=float),
            np.repeat(float(s["rates"]), p.hold_period),
            float(s["exit_multiple"]),
        )
        rows.append({"Scenario": name, **out})
    return pd.DataFrame(rows)


def decision_scorecard(df: pd.DataFrame, p: DealInputs | None = None) -> pd.DataFrame:
    """Compact decision summary for the README and IC overview."""
    p = p or DealInputs()
    base = deterministic_base_case(p)
    reverse = reverse_lbo_max_entry_multiple(p)
    curve = bid_probability_curve(df, p)
    p50 = bid_ceiling_for_probability(curve, 0.50)
    p75 = bid_ceiling_for_probability(curve, 0.75)
    rows = [
        ("Seller ask", p.entry_multiple, "x EBITDA"),
        ("Base-case gross IRR", base["gross_irr"], "%"),
        ("Base-case gross MOIC", base["gross_moic"], "x"),
        ("Deterministic max bid", reverse["max_entry_multiple"], "x EBITDA"),
        ("Bid gap vs ask", reverse["bid_gap_multiple"], "x EBITDA"),
        ("P(IRR >= 25%) at ask", float(df["irr_hurdle_met"].mean()), "%"),
        ("Risk-adjusted bid ceiling - 50% threshold", p50, "x EBITDA"),
        ("Risk-adjusted bid ceiling - 75% threshold", p75, "x EBITDA"),
    ]
    return pd.DataFrame(rows, columns=["Metric", "Value", "Units"])
