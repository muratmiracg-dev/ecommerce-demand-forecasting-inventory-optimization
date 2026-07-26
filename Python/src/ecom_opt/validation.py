from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DATA_DIR


def validate_project(report_path: Path | None = None) -> dict:
    checks = []

    def add_check(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    products = pd.read_csv(DATA_DIR / "dim_product.csv")
    suppliers = pd.read_csv(DATA_DIR / "dim_supplier.csv")
    sales = pd.read_csv(DATA_DIR / "fact_weekly_sales.csv")
    inventory = pd.read_csv(DATA_DIR / "fact_inventory_snapshot.csv")
    forecast = pd.read_csv(DATA_DIR / "forecast_results.csv")
    metrics = pd.read_csv(DATA_DIR / "model_comparison.csv")
    replenishment = pd.read_csv(DATA_DIR / "replenishment_recommendations.csv")

    add_check("60 product SKUs", products["SKU"].nunique() == 60, f"{products['SKU'].nunique()} SKUs")
    add_check(
        "Product supplier keys",
        set(products["SupplierID"]).issubset(set(suppliers["SupplierID"])),
        "All product supplier IDs resolve",
    )
    add_check(
        "Sales product keys",
        set(sales["SKU"]).issubset(set(products["SKU"])),
        "All sales SKUs resolve",
    )
    add_check(
        "Non-negative sales measures",
        bool(
            (
                sales[
                    [
                        "UnitsSold",
                        "EstimatedDemandUnits",
                        "LostSalesUnits",
                        "NetRevenueTRY",
                        "COGSTRY",
                    ]
                ]
                >= 0
            ).all().all()
        ),
        "No negative unit or value measures",
    )
    add_check(
        "Demand balance",
        bool(
            np.allclose(
                sales.groupby(["WeekStart", "SKU"])["EstimatedDemandUnits"].sum().values,
                (
                    sales.groupby(["WeekStart", "SKU"])["UnitsSold"].sum()
                    + sales.groupby(["WeekStart", "SKU"])["LostSalesUnits"].sum()
                ).values,
                atol=1.1,
            )
        ),
        "Estimated demand approximately equals sold plus lost sales",
    )
    add_check(
        "Historical coverage",
        sales["WeekStart"].min() == "2023-01-02"
        and sales["WeekStart"].max() == "2025-12-29",
        f"{sales['WeekStart'].min()} to {sales['WeekStart'].max()}",
    )
    add_check(
        "Forecast coverage",
        forecast["WeekStart"].nunique() == 52 and forecast["SKU"].nunique() == 60,
        f"{forecast['WeekStart'].nunique()} weeks x {forecast['SKU'].nunique()} SKUs",
    )
    add_check(
        "Forecast completeness",
        len(forecast) == 52 * 60 and not forecast.isna().any().any(),
        f"{len(forecast):,} complete rows",
    )
    add_check(
        "One champion per SKU",
        metrics[metrics["ChampionFlag"]].groupby("SKU").size().eq(1).all(),
        "Exactly one selected model per SKU",
    )
    add_check(
        "Finite model metrics",
        np.isfinite(metrics[["MAE", "RMSE", "WAPE", "Bias"]].to_numpy()).all(),
        "All model metrics are finite",
    )
    pack_lookup = products.set_index("SKU")["CasePack"]
    pack_valid = all(
        int(row["RecommendedOrderQty"]) % int(pack_lookup[row["SKU"]]) == 0
        for _, row in replenishment.iterrows()
    )
    add_check(
        "Case-pack rounding",
        pack_valid,
        "Every recommendation is a multiple of the product case pack",
    )
    add_check(
        "Inventory non-negative",
        bool((inventory[["EndingOnHand", "OnOrderUnits", "InventoryValueTRY"]] >= 0).all().all()),
        "No negative ending stock, on-order stock, or inventory value",
    )

    report = {
        "project": "E-Commerce Demand Forecasting & Inventory Optimization Platform",
        "all_passed": all(check["passed"] for check in checks),
        "checks": checks,
    }
    report_path = report_path or DATA_DIR / "validation_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = validate_project()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["all_passed"] else 1)

