
import unittest
import numpy as np

from src.risk_engine import (
    DealInputs,
    bid_ceiling_for_probability,
    bid_probability_curve,
    deterministic_base_case,
    hurdle_solver,
    reverse_lbo_max_entry_multiple,
    run_path,
    scenario_cases,
    simulate,
    sponsor_equity_for_entry_multiple,
)


class RiskEngineTests(unittest.TestCase):
    def setUp(self):
        self.p = DealInputs()

    def test_base_case_matches_excel_irr(self):
        out = deterministic_base_case(self.p)
        self.assertAlmostEqual(out["gross_irr"], 0.22312378, places=6)

    def test_base_case_matches_excel_moic(self):
        out = deterministic_base_case(self.p)
        self.assertAlmostEqual(out["gross_moic"], 2.73748689, places=6)

    def test_base_case_matches_exit_net_debt(self):
        out = deterministic_base_case(self.p)
        self.assertAlmostEqual(out["exit_net_debt"], 170.50924936, places=5)

    def test_higher_entry_multiple_requires_more_equity(self):
        self.assertGreater(
            sponsor_equity_for_entry_multiple(9.0, self.p),
            sponsor_equity_for_entry_multiple(8.0, self.p),
        )

    def test_higher_entry_multiple_lowers_return_holding_exit_constant(self):
        growth = np.asarray(self.p.revenue_growth)
        margin = np.asarray(self.p.ebitda_margin)
        rates = np.repeat(self.p.base_rate, self.p.hold_period)
        low = run_path(self.p, growth, margin, rates, self.p.exit_multiple, entry_multiple=8.0)
        high = run_path(self.p, growth, margin, rates, self.p.exit_multiple, entry_multiple=9.0)
        self.assertGreater(low["gross_irr"], high["gross_irr"])

    def test_higher_exit_multiple_improves_return(self):
        growth = np.asarray(self.p.revenue_growth)
        margin = np.asarray(self.p.ebitda_margin)
        rates = np.repeat(self.p.base_rate, self.p.hold_period)
        low = run_path(self.p, growth, margin, rates, 8.5)
        high = run_path(self.p, growth, margin, rates, 10.0)
        self.assertGreater(high["gross_irr"], low["gross_irr"])

    def test_reverse_lbo_bid_is_below_seller_ask(self):
        rev = reverse_lbo_max_entry_multiple(self.p)
        self.assertLess(rev["max_entry_multiple"], self.p.entry_multiple)
        self.assertEqual(rev["binding_constraint"], "IRR")

    def test_hurdle_solver_requires_positive_improvement(self):
        h = hurdle_solver(self.p)
        self.assertGreater(h["incremental_exit_ebitda_pct"], 0)
        self.assertGreater(h["required_exit_multiple"], self.p.exit_multiple)
        self.assertGreater(h["additional_debt_paydown_needed"], 0)

    def test_simulation_is_reproducible(self):
        a = simulate(200, 12, self.p)
        b = simulate(200, 12, self.p)
        np.testing.assert_allclose(a["gross_irr"].to_numpy(), b["gross_irr"].to_numpy())

    def test_bid_probability_declines_with_price(self):
        df = simulate(500, 7, self.p)
        curve = bid_probability_curve(df, self.p)
        probs = curve["Probability IRR >= 25%"].to_numpy()
        self.assertTrue(np.all(np.diff(probs) <= 1e-12))

    def test_bid_ceiling_is_within_grid(self):
        df = simulate(500, 9, self.p)
        curve = bid_probability_curve(df, self.p)
        ceiling = bid_ceiling_for_probability(curve, 0.50)
        self.assertTrue(np.isnan(ceiling) or 6.5 <= ceiling <= 9.5)

    def test_credit_metrics_are_finite(self):
        df = simulate(200, 3, self.p)
        self.assertTrue(np.isfinite(df["minimum_interest_coverage"]).all())
        self.assertTrue((df["maximum_rcf_draw"] >= 0).all())

    def test_scenario_cases_are_ordered(self):
        cases = scenario_cases(self.p).set_index("Scenario")
        self.assertLess(cases.loc["Downside", "gross_irr"], cases.loc["Base", "gross_irr"])
        self.assertLess(cases.loc["Base", "gross_irr"], cases.loc["Upside", "gross_irr"])

    def test_stricter_probability_threshold_lowers_bid_ceiling(self):
        df = simulate(800, 21, self.p)
        curve = bid_probability_curve(df, self.p)
        p50 = bid_ceiling_for_probability(curve, 0.50)
        p75 = bid_ceiling_for_probability(curve, 0.75)
        self.assertLessEqual(p75, p50)

    def test_downside_has_weaker_credit_metrics_than_base(self):
        cases = scenario_cases(self.p).set_index("Scenario")
        self.assertLess(
            cases.loc["Downside", "minimum_interest_coverage"],
            cases.loc["Base", "minimum_interest_coverage"],
        )
        self.assertGreater(
            cases.loc["Downside", "exit_net_debt"],
            cases.loc["Base", "exit_net_debt"],
        )


if __name__ == "__main__":
    unittest.main()
