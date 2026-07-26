from __future__ import annotations

import pandas as pd

from .config import DATA_DIR


def build_reporting_tables() -> dict[str, pd.DataFrame]:
    sales = pd.read_csv(DATA_DIR / "fact_weekly_sales.csv", parse_dates=["WeekStart"])
    products = pd.read_csv(DATA_DIR / "dim_product.csv")
    inventory = pd.read_csv(
        DATA_DIR / "fact_inventory_snapshot.csv", parse_dates=["WeekStart"]
    )
    purchase_orders = pd.read_csv(
        DATA_DIR / "fact_purchase_orders.csv",
        parse_dates=["OrderDate", "ExpectedReceiptDate", "ActualReceiptDate"],
    )
    forecast = pd.read_csv(DATA_DIR / "forecast_results.csv", parse_dates=["WeekStart"])
    metrics = pd.read_csv(DATA_DIR / "model_comparison.csv")
    replenishment = pd.read_csv(DATA_DIR / "replenishment_recommendations.csv")

    sales_enriched = sales.merge(
        products[["SKU", "ProductName", "Category", "Segment", "SupplierID"]],
        on="SKU",
        how="left",
    )
    sales_enriched["YearMonth"] = sales_enriched["WeekStart"].dt.strftime("%Y-%m")
    inventory["YearMonth"] = inventory["WeekStart"].dt.strftime("%Y-%m")

    monthly = (
        sales_enriched.groupby("YearMonth", as_index=False)
        .agg(
            EstimatedDemandUnits=("EstimatedDemandUnits", "sum"),
            UnitsSold=("UnitsSold", "sum"),
            LostSalesUnits=("LostSalesUnits", "sum"),
            NetRevenueTRY=("NetRevenueTRY", "sum"),
            GrossProfitTRY=("GrossProfitTRY", "sum"),
            DiscountTRY=("DiscountTRY", "sum"),
            AverageDiscountPct=("DiscountPct", "mean"),
            StockoutSalesRows=("StockoutFlag", "sum"),
        )
        .sort_values("YearMonth")
    )
    monthly_inventory = (
        inventory.groupby("YearMonth", as_index=False)
        .agg(
            AverageInventoryValueTRY=("InventoryValueTRY", "mean"),
            AverageWeeksOfSupply=("WeeksOfSupply", "mean"),
            StockoutSKUWeeks=("StockoutFlag", "sum"),
        )
        .sort_values("YearMonth")
    )
    monthly = monthly.merge(monthly_inventory, on="YearMonth", how="left")
    monthly["DemandFulfillmentRate"] = (
        monthly["UnitsSold"] / monthly["EstimatedDemandUnits"]
    )
    monthly["GrossMarginPct"] = monthly["GrossProfitTRY"] / monthly["NetRevenueTRY"]

    category = (
        sales_enriched.groupby("Category", as_index=False)
        .agg(
            EstimatedDemandUnits=("EstimatedDemandUnits", "sum"),
            UnitsSold=("UnitsSold", "sum"),
            LostSalesUnits=("LostSalesUnits", "sum"),
            NetRevenueTRY=("NetRevenueTRY", "sum"),
            GrossProfitTRY=("GrossProfitTRY", "sum"),
            AverageDiscountPct=("DiscountPct", "mean"),
        )
        .sort_values("NetRevenueTRY", ascending=False)
    )
    category["DemandFulfillmentRate"] = (
        category["UnitsSold"] / category["EstimatedDemandUnits"]
    )
    category["GrossMarginPct"] = category["GrossProfitTRY"] / category["NetRevenueTRY"]

    champion = metrics[metrics["ChampionFlag"]][["SKU", "Model", "WAPE", "Bias"]].rename(
        columns={"Model": "ChampionModel", "WAPE": "ChampionWAPE", "Bias": "ChampionBias"}
    )
    sku = (
        sales_enriched.groupby(
            ["SKU", "ProductName", "Category", "Segment", "SupplierID"], as_index=False
        )
        .agg(
            EstimatedDemandUnits=("EstimatedDemandUnits", "sum"),
            UnitsSold=("UnitsSold", "sum"),
            LostSalesUnits=("LostSalesUnits", "sum"),
            NetRevenueTRY=("NetRevenueTRY", "sum"),
            GrossProfitTRY=("GrossProfitTRY", "sum"),
        )
        .merge(champion, on="SKU", how="left")
        .merge(
            replenishment[
                [
                    "SKU",
                    "ProjectedWeeksOfSupply",
                    "RecommendedOrderQty",
                    "RecommendedInvestmentTRY",
                    "Action",
                ]
            ],
            on="SKU",
            how="left",
        )
    )
    sku["DemandFulfillmentRate"] = sku["UnitsSold"] / sku["EstimatedDemandUnits"]
    sku["GrossMarginPct"] = sku["GrossProfitTRY"] / sku["NetRevenueTRY"]
    sku = sku.sort_values("NetRevenueTRY", ascending=False)

    forecast["YearMonth"] = forecast["WeekStart"].dt.strftime("%Y-%m")
    forecast_monthly = (
        forecast.groupby(["YearMonth", "Category"], as_index=False)
        .agg(
            ForecastUnits=("ForecastUnits", "sum"),
            Lower80Units=("Lower80Units", "sum"),
            Upper80Units=("Upper80Units", "sum"),
            ForecastRevenueTRY=("ForecastRevenueTRY", "sum"),
        )
        .sort_values(["YearMonth", "Category"])
    )

    supplier = (
        purchase_orders.groupby("SupplierID", as_index=False)
        .agg(
            PurchaseOrders=("POID", "nunique"),
            OrderedUnits=("OrderedQty", "sum"),
            PurchaseValueTRY=("POValueTRY", "sum"),
            AverageActualLeadTimeDays=("ActualLeadTimeDays", "mean"),
            OnTimeDeliveryRate=("OnTimeFlag", "mean"),
        )
        .merge(
            products[["SupplierID"]].value_counts().rename("SKUCount").reset_index(),
            on="SupplierID",
            how="left",
        )
        .sort_values("PurchaseValueTRY", ascending=False)
    )

    tables = {
        "monthly_performance": monthly,
        "category_performance": category,
        "sku_performance": sku,
        "forecast_monthly": forecast_monthly,
        "supplier_scorecard": supplier,
    }
    for name, frame in tables.items():
        frame.to_csv(DATA_DIR / f"{name}.csv", index=False)
    return tables


if __name__ == "__main__":
    built = build_reporting_tables()
    for table_name, frame in built.items():
        print(f"{table_name}: {len(frame):,} rows")

