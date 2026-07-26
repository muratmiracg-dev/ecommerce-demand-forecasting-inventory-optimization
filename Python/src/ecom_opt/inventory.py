from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import norm

from .config import DATA_DIR, SCENARIOS


def _round_to_pack(value: float, case_pack: int) -> int:
    return int(math.ceil(max(0, value) / case_pack) * case_pack)


def optimize_inventory() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    products = pd.read_csv(DATA_DIR / "dim_product.csv", parse_dates=["LaunchDate"])
    suppliers = pd.read_csv(DATA_DIR / "dim_supplier.csv")
    inventory = pd.read_csv(
        DATA_DIR / "fact_inventory_snapshot.csv", parse_dates=["WeekStart"]
    )
    forecast = pd.read_csv(DATA_DIR / "forecast_results.csv", parse_dates=["WeekStart"])
    metrics = pd.read_csv(DATA_DIR / "model_comparison.csv")

    latest_week = inventory["WeekStart"].max()
    latest_inventory = inventory[inventory["WeekStart"] == latest_week].copy()
    forecast_summary = (
        forecast.groupby("SKU", as_index=False)
        .agg(
            AnnualForecastUnits=("ForecastUnits", "sum"),
            AverageWeeklyForecastUnits=("ForecastUnits", "mean"),
            ForecastRevenueTRY=("ForecastRevenueTRY", "sum"),
            ResidualStdUnits=("ResidualStdUnits", "mean"),
            ChampionModel=("ChampionModel", "first"),
        )
    )
    champion_metrics = metrics[metrics["ChampionFlag"]].copy()
    champion_metrics = champion_metrics[["SKU", "WAPE", "Bias"]].rename(
        columns={"WAPE": "ChampionWAPE", "Bias": "ChampionBias"}
    )
    base = (
        products.merge(
            suppliers[["SupplierID", "SupplierName", "OrderCostTRY", "OnTimeDeliveryRate"]],
            on="SupplierID",
            how="left",
        )
        .merge(
            latest_inventory[
                ["SKU", "EndingOnHand", "OnOrderUnits", "InventoryValueTRY", "WeeksOfSupply"]
            ],
            on="SKU",
            how="left",
        )
        .merge(forecast_summary, on="SKU", how="left")
        .merge(champion_metrics, on="SKU", how="left")
    )

    scenario_rows = []
    for scenario_name, assumptions in SCENARIOS.items():
        for _, row in base.iterrows():
            demand_multiplier = float(assumptions["demand_multiplier"])
            service_level = min(
                0.995,
                max(
                    0.85,
                    float(row["TargetServiceLevel"])
                    + float(assumptions["service_level_delta"]),
                ),
            )
            lead_time_days = max(
                1,
                int(row["LeadTimeDays"]) + int(assumptions["lead_time_days_delta"]),
            )
            lead_time_weeks = lead_time_days / 7.0
            avg_weekly = float(row["AverageWeeklyForecastUnits"]) * demand_multiplier
            annual_demand = float(row["AnnualForecastUnits"]) * demand_multiplier
            residual_std = max(1.0, float(row["ResidualStdUnits"]) * demand_multiplier)
            z_score = float(norm.ppf(service_level))
            safety_stock = z_score * residual_std * math.sqrt(lead_time_weeks)
            reorder_point = avg_weekly * lead_time_weeks + safety_stock
            holding_cost_per_unit = max(float(row["UnitCostTRY"]) * 0.24, 1.0)
            eoq = math.sqrt(
                2
                * max(annual_demand, 1)
                * float(row["OrderCostTRY"])
                / holding_cost_per_unit
            )
            inventory_position = float(row["EndingOnHand"]) + float(row["OnOrderUnits"])
            cycle_stock = max(eoq / 2, avg_weekly * 4)
            raw_order = max(0.0, reorder_point + cycle_stock - inventory_position)
            raw_order = max(raw_order, float(row["MOQ"])) if raw_order > 0 else 0
            recommended_qty = _round_to_pack(raw_order, int(row["CasePack"]))
            projected_wos = (
                inventory_position / avg_weekly if avg_weekly > 0 else np.nan
            )
            if recommended_qty > 0 and inventory_position <= reorder_point:
                action = "ORDER NOW"
            elif projected_wos > 18:
                action = "OVERSTOCK REVIEW"
            elif inventory_position <= reorder_point * 1.20:
                action = "MONITOR"
            else:
                action = "HEALTHY"
            scenario_rows.append(
                {
                    "Scenario": scenario_name,
                    "SKU": row["SKU"],
                    "ProductName": row["ProductName"],
                    "Category": row["Category"],
                    "SupplierID": row["SupplierID"],
                    "SupplierName": row["SupplierName"],
                    "ChampionModel": row["ChampionModel"],
                    "ChampionWAPE": row["ChampionWAPE"],
                    "DemandMultiplier": demand_multiplier,
                    "TargetServiceLevel": service_level,
                    "LeadTimeDays": lead_time_days,
                    "AverageWeeklyForecastUnits": round(avg_weekly, 3),
                    "AnnualForecastUnits": round(annual_demand, 3),
                    "CurrentOnHand": int(row["EndingOnHand"]),
                    "OnOrderUnits": int(row["OnOrderUnits"]),
                    "InventoryPosition": round(inventory_position, 3),
                    "ProjectedWeeksOfSupply": round(projected_wos, 3),
                    "SafetyStockUnits": round(safety_stock, 3),
                    "ReorderPointUnits": round(reorder_point, 3),
                    "EOQUnits": round(eoq, 3),
                    "RecommendedOrderQty": recommended_qty,
                    "RecommendedInvestmentTRY": round(
                        recommended_qty * float(row["UnitCostTRY"]), 2
                    ),
                    "ForecastRevenueTRY": round(
                        float(row["ForecastRevenueTRY"]) * demand_multiplier, 2
                    ),
                    "Action": action,
                }
            )

    scenarios = pd.DataFrame(scenario_rows)
    recommendations = scenarios[scenarios["Scenario"] == "Base"].copy()
    recommendations = recommendations.sort_values(
        ["Action", "RecommendedInvestmentTRY"], ascending=[True, False]
    )
    summaries = (
        scenarios.groupby("Scenario", as_index=False)
        .agg(
            ForecastUnits=("AnnualForecastUnits", "sum"),
            ForecastRevenueTRY=("ForecastRevenueTRY", "sum"),
            RecommendedInvestmentTRY=("RecommendedInvestmentTRY", "sum"),
            RecommendedOrderUnits=("RecommendedOrderQty", "sum"),
            AverageWeeksOfSupply=("ProjectedWeeksOfSupply", "mean"),
            AverageSafetyStockUnits=("SafetyStockUnits", "mean"),
            SKUsToOrder=("Action", lambda values: int((values == "ORDER NOW").sum())),
            OverstockReviewSKUs=(
                "Action",
                lambda values: int((values == "OVERSTOCK REVIEW").sum()),
            ),
        )
    )
    summaries["ProjectedGrossMarginTRY"] = (
        summaries["ForecastRevenueTRY"] * 0.58
    ).round(2)
    summaries["InventoryInvestmentToRevenuePct"] = (
        summaries["RecommendedInvestmentTRY"] / summaries["ForecastRevenueTRY"]
    ).round(4)

    recommendations.to_csv(
        DATA_DIR / "replenishment_recommendations.csv", index=False
    )
    scenarios.to_csv(DATA_DIR / "inventory_scenarios.csv", index=False)
    summaries.to_csv(DATA_DIR / "scenario_summary.csv", index=False)
    return recommendations, scenarios, summaries


if __name__ == "__main__":
    recommendations, scenarios, summary = optimize_inventory()
    print(f"replenishment_recommendations: {len(recommendations):,} rows")
    print(f"inventory_scenarios: {len(scenarios):,} rows")
    print(summary.to_string(index=False))

