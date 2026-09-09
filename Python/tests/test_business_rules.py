import unittest

import numpy as np
import pandas as pd

from ecom_opt.config import DATA_DIR
from ecom_opt.forecasting import _bias, _wape


class BusinessRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products = pd.read_csv(DATA_DIR / "dim_product.csv")
        cls.forecast = pd.read_csv(DATA_DIR / "forecast_results.csv")
        cls.replenishment = pd.read_csv(
            DATA_DIR / "replenishment_recommendations.csv"
        )
        cls.metrics = pd.read_csv(DATA_DIR / "model_comparison.csv")

    def test_forecast_grain(self):
        self.assertEqual(self.forecast["WeekStart"].nunique(), 52)
        self.assertEqual(self.forecast["SKU"].nunique(), 60)
        self.assertEqual(len(self.forecast), 3_120)

    def test_single_champion_model(self):
        champions = self.metrics[self.metrics["ChampionFlag"]]
        self.assertTrue(champions.groupby("SKU").size().eq(1).all())

    def test_order_quantities_follow_case_pack(self):
        pack_lookup = self.products.set_index("SKU")["CasePack"]
        for _, row in self.replenishment.iterrows():
            self.assertEqual(
                int(row["RecommendedOrderQty"])
                % int(pack_lookup.loc[row["SKU"]]),
                0,
            )

    def test_reorder_points_cover_safety_stock(self):
        self.assertTrue(
            (
                self.replenishment["ReorderPointUnits"]
                >= self.replenishment["SafetyStockUnits"]
            ).all()
        )

    def test_zero_demand_penalizes_false_positive_forecasts(self):
        actual = np.zeros(3)
        predicted = np.array([0.0, 2.0, 1.0])

        self.assertEqual(_wape(actual, predicted), 3.0)
        self.assertEqual(_bias(actual, predicted), 3.0)
        self.assertEqual(_wape(actual, np.zeros(3)), 0.0)

    def test_forecast_metrics_reject_invalid_inputs(self):
        invalid_pairs = [
            (np.array([]), np.array([])),
            (np.array([1.0]), np.array([1.0, 2.0])),
            (np.array([1.0]), np.array([np.nan])),
            (np.array([1.0]), np.array([-1.0])),
        ]
        for actual, predicted in invalid_pairs:
            with self.subTest(actual=actual, predicted=predicted), self.assertRaises(ValueError):
                _wape(actual, predicted)


if __name__ == "__main__":
    unittest.main()
