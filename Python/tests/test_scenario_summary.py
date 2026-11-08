import unittest

import pandas as pd
from ecom_opt.config import DATA_DIR


class ScenarioSummaryTests(unittest.TestCase):
    """The headline investment must reconcile to the per-SKU scenario rows."""

    @classmethod
    def setUpClass(cls):
        cls.scenarios = pd.read_csv(DATA_DIR / "inventory_scenarios.csv")
        cls.summary = pd.read_csv(DATA_DIR / "scenario_summary.csv").set_index("Scenario")

    def test_investment_splits_into_immediate_and_top_up(self):
        for scenario, rows in self.scenarios.groupby("Scenario"):
            with self.subTest(scenario=scenario):
                summary = self.summary.loc[scenario]
                immediate = rows.loc[
                    rows["Action"] == "ORDER NOW", "RecommendedInvestmentTRY"
                ].sum()
                self.assertAlmostEqual(
                    summary["ImmediateOrderInvestmentTRY"], immediate, places=2
                )
                self.assertAlmostEqual(
                    summary["ImmediateOrderInvestmentTRY"]
                    + summary["TopUpInvestmentTRY"],
                    summary["RecommendedInvestmentTRY"],
                    places=2,
                )

    def test_sku_counts_distinguish_immediate_from_all_orders(self):
        for scenario, rows in self.scenarios.groupby("Scenario"):
            with self.subTest(scenario=scenario):
                summary = self.summary.loc[scenario]
                self.assertEqual(
                    summary["SKUsWithOrder"], int((rows["RecommendedOrderQty"] > 0).sum())
                )
                self.assertEqual(
                    summary["SKUsToOrder"], int((rows["Action"] == "ORDER NOW").sum())
                )
                self.assertGreaterEqual(summary["SKUsWithOrder"], summary["SKUsToOrder"])

    def test_every_immediate_order_sku_has_an_order(self):
        immediate = self.scenarios[self.scenarios["Action"] == "ORDER NOW"]
        self.assertTrue((immediate["RecommendedOrderQty"] > 0).all())


if __name__ == "__main__":
    unittest.main()
