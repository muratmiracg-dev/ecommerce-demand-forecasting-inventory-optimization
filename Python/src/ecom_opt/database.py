from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from .config import DATA_DIR, SQL_DIR


TABLE_FILES = {
    "dim_calendar": "dim_calendar.csv",
    "dim_product": "dim_product.csv",
    "dim_supplier": "dim_supplier.csv",
    "fact_weekly_sales": "fact_weekly_sales.csv",
    "fact_inventory_snapshot": "fact_inventory_snapshot.csv",
    "fact_purchase_orders": "fact_purchase_orders.csv",
    "fact_promotions": "fact_promotions.csv",
    "forecast_results": "forecast_results.csv",
    "forecast_backtest": "forecast_backtest.csv",
    "model_comparison": "model_comparison.csv",
    "replenishment_recommendations": "replenishment_recommendations.csv",
    "inventory_scenarios": "inventory_scenarios.csv",
    "scenario_summary": "scenario_summary.csv",
    "monthly_performance": "monthly_performance.csv",
    "category_performance": "category_performance.csv",
    "sku_performance": "sku_performance.csv",
    "forecast_monthly": "forecast_monthly.csv",
    "supplier_scorecard": "supplier_scorecard.csv",
}


def build_database(db_path: Path | None = None) -> Path:
    SQL_DIR.mkdir(parents=True, exist_ok=True)
    db_path = db_path or SQL_DIR / "ecommerce_demand_inventory.db"
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as connection:
        for table_name, filename in TABLE_FILES.items():
            frame = pd.read_csv(DATA_DIR / filename)
            frame.to_sql(table_name, connection, if_exists="replace", index=False)
        connection.executescript(
            """
            CREATE INDEX idx_sales_week_sku
                ON fact_weekly_sales (WeekStart, SKU);
            CREATE INDEX idx_inventory_week_sku
                ON fact_inventory_snapshot (WeekStart, SKU);
            CREATE INDEX idx_forecast_week_sku
                ON forecast_results (WeekStart, SKU);
            CREATE INDEX idx_product_category
                ON dim_product (Category);

            CREATE VIEW vw_weekly_category_performance AS
            SELECT
                s.WeekStart,
                p.Category,
                SUM(s.EstimatedDemandUnits) AS EstimatedDemandUnits,
                SUM(s.UnitsSold) AS UnitsSold,
                SUM(s.LostSalesUnits) AS LostSalesUnits,
                SUM(s.NetRevenueTRY) AS NetRevenueTRY,
                SUM(s.GrossProfitTRY) AS GrossProfitTRY,
                CASE
                    WHEN SUM(s.EstimatedDemandUnits) = 0 THEN 1.0
                    ELSE SUM(s.UnitsSold) / SUM(s.EstimatedDemandUnits)
                END AS DemandFulfillmentRate
            FROM fact_weekly_sales s
            JOIN dim_product p ON p.SKU = s.SKU
            GROUP BY s.WeekStart, p.Category;

            CREATE VIEW vw_forecast_category_summary AS
            SELECT
                f.Category,
                SUM(f.ForecastUnits) AS ForecastUnits,
                SUM(f.ForecastRevenueTRY) AS ForecastRevenueTRY,
                AVG(f.ResidualStdUnits) AS AverageResidualStdUnits
            FROM forecast_results f
            GROUP BY f.Category;

            CREATE VIEW vw_replenishment_priority AS
            SELECT
                r.SKU,
                r.ProductName,
                r.Category,
                r.SupplierName,
                r.Action,
                r.RecommendedOrderQty,
                r.RecommendedInvestmentTRY,
                r.ProjectedWeeksOfSupply,
                r.ReorderPointUnits,
                r.InventoryPosition,
                r.ChampionWAPE
            FROM replenishment_recommendations r
            ORDER BY
                CASE r.Action
                    WHEN 'ORDER NOW' THEN 1
                    WHEN 'MONITOR' THEN 2
                    WHEN 'HEALTHY' THEN 3
                    ELSE 4
                END,
                r.RecommendedInvestmentTRY DESC;
            """
        )
    return db_path


if __name__ == "__main__":
    created_path = build_database()
    print(created_path)
