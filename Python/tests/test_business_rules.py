import unittest

import numpy as np
import pandas as pd
from ecom_opt.config import DATA_DIR
from ecom_opt.forecasting import _bias, _prepare_history, _train_ml, _wape
from ecom_opt.inventory import _validate_inventory_inputs


class BusinessRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products = pd.read_csv(DATA_DIR / "dim_product.csv")
        cls.forecast = pd.read_csv(DATA_DIR / "forecast_results.csv")
        cls.replenishment = pd.read_csv(DATA_DIR / "replenishment_recommendations.csv")
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
                int(row["RecommendedOrderQty"]) % int(pack_lookup.loc[row["SKU"]]),
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
            with (
                self.subTest(actual=actual, predicted=predicted),
                self.assertRaises(ValueError),
            ):
                _wape(actual, predicted)

    def test_training_window_rejects_ambiguous_or_oversized_values(self):
        sales = pd.read_csv(
            DATA_DIR / "fact_weekly_sales.csv", parse_dates=["WeekStart"]
        )
        products = pd.read_csv(DATA_DIR / "dim_product.csv", parse_dates=["LaunchDate"])
        history = _prepare_history(sales, products)
        for test_weeks, error in (
            (True, TypeError),
            (12.5, TypeError),
            (0, ValueError),
            (999, ValueError),
        ):
            with self.subTest(test_weeks=test_weeks), self.assertRaises(error):
                _train_ml(history, test_weeks=test_weeks)

    def test_inventory_inputs_fail_closed_on_invalid_decision_data(self):
        products = pd.DataFrame(
            {
                "SKU": ["SKU-1"],
                "UnitCostTRY": [10.0],
                "TargetServiceLevel": [0.95],
                "LeadTimeDays": [7],
                "MOQ": [10],
                "CasePack": [5],
            }
        )
        suppliers = pd.DataFrame({"SupplierID": ["SUP-1"], "OrderCostTRY": [20.0]})
        inventory = pd.DataFrame({"EndingOnHand": [10], "OnOrderUnits": [0]})
        forecast = pd.DataFrame(
            {
                "ForecastUnits": [20.0],
                "ForecastRevenueTRY": [200.0],
                "ResidualStdUnits": [2.0],
            }
        )
        _validate_inventory_inputs(products, suppliers, inventory, forecast)

        for frame_name, column, value in (
            ("products", "TargetServiceLevel", 1.2),
            ("products", "CasePack", 2.5),
            ("inventory", "EndingOnHand", -1),
            ("forecast", "ResidualStdUnits", np.nan),
        ):
            frames = {
                "products": products.copy(),
                "suppliers": suppliers.copy(),
                "inventory": inventory.copy(),
                "forecast": forecast.copy(),
            }
            frames[frame_name][column] = frames[frame_name][column].astype(object)
            frames[frame_name].loc[0, column] = value
            with self.subTest(column=column), self.assertRaises(ValueError):
                _validate_inventory_inputs(**frames)


if __name__ == "__main__":
    unittest.main()
