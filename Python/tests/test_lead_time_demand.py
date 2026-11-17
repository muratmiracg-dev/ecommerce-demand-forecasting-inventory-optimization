import math
import unittest

import numpy as np
import pandas as pd
from ecom_opt.config import DATA_DIR
from ecom_opt.inventory import _horizon_demand


class HorizonDemandTests(unittest.TestCase):
    def test_whole_and_fractional_weeks(self):
        weekly = np.array([10.0, 20.0, 30.0, 40.0])
        self.assertEqual(_horizon_demand(weekly, 0.0, 2.0), 30.0)
        self.assertAlmostEqual(_horizon_demand(weekly, 0.0, 1.5), 20.0)
        self.assertAlmostEqual(_horizon_demand(weekly, 1.5, 2.0), 10.0 + 30.0 + 20.0)
        self.assertEqual(_horizon_demand(weekly, 0.0, 0.0), 0.0)

    def test_weeks_beyond_horizon_use_the_mean(self):
        weekly = np.array([10.0, 30.0])
        self.assertEqual(_horizon_demand(weekly, 0.0, 4.0), 10.0 + 30.0 + 20.0 + 20.0)

    def test_rejects_invalid_horizons(self):
        with self.assertRaises(ValueError):
            _horizon_demand(np.array([1.0]), 0.0, -1.0)
        with self.assertRaises(ValueError):
            _horizon_demand(np.array([]), 0.0, 1.0)


class CommittedReplenishmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products = pd.read_csv(DATA_DIR / "dim_product.csv").set_index("SKU")
        cls.forecast = pd.read_csv(DATA_DIR / "forecast_results.csv", parse_dates=["WeekStart"])
        cls.scenarios = pd.read_csv(DATA_DIR / "inventory_scenarios.csv")
        cls.summary = pd.read_csv(DATA_DIR / "scenario_summary.csv").set_index("Scenario")

    def test_reorder_point_uses_forecast_over_the_coming_lead_time(self):
        # With the old annual-average formula, ROP - safety stock equalled
        # average weekly forecast x lead-time weeks for every SKU.
        weekly = {
            sku: group.sort_values("WeekStart")["ForecastUnits"].to_numpy()
            for sku, group in self.forecast.groupby("SKU")
        }
        differs_from_annual_average = 0
        for _, row in self.scenarios.iterrows():
            lead_time_weeks = row["LeadTimeDays"] / 7.0
            expected = _horizon_demand(
                weekly[row["SKU"]] * row["DemandMultiplier"], 0.0, lead_time_weeks
            )
            lead_time_demand = row["ReorderPointUnits"] - row["SafetyStockUnits"]
            self.assertAlmostEqual(lead_time_demand, expected, delta=0.01)
            annual_average = row["AverageWeeklyForecastUnits"] * lead_time_weeks
            if not math.isclose(lead_time_demand, annual_average, abs_tol=0.5):
                differs_from_annual_average += 1
        self.assertGreater(differs_from_annual_average, len(self.scenarios) // 2)

    def test_projected_gross_margin_uses_unit_cost(self):
        cost = self.products["UnitCostTRY"]
        for scenario, group in self.scenarios.groupby("Scenario"):
            cogs = (group["AnnualForecastUnits"] * group["SKU"].map(cost)).sum()
            expected = self.summary.loc[scenario, "ForecastRevenueTRY"] - cogs
            self.assertAlmostEqual(
                self.summary.loc[scenario, "ProjectedGrossMarginTRY"], expected, delta=5.0
            )


if __name__ == "__main__":
    unittest.main()
