from __future__ import annotations

import base64
import json
import shutil
import uuid
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "Data"
OUTPUT_ROOT = PROJECT_ROOT / "PowerBI" / "Ecommerce_Demand_Inventory_PBIP"
PROJECT_NAME = "Ecommerce_Demand_Inventory_Analytics"
REPORT_NAME = f"{PROJECT_NAME}.Report"
MODEL_NAME = f"{PROJECT_NAME}.SemanticModel"
PBIP_PATH = OUTPUT_ROOT / f"{PROJECT_NAME}.pbip"

TEMPLATE_ROOT = (
    PROJECT_ROOT.parent
    / "outputs"
    / "crm_dashboard_suite"
    / "CRM_Sales_Analytics_PBIP"
)


def csv_m_expression(frame: pd.DataFrame, type_map: dict[str, str]) -> list[str]:
    export = frame.copy()
    for column in export.columns:
        if pd.api.types.is_datetime64_any_dtype(export[column]):
            export[column] = export[column].dt.strftime("%Y-%m-%d")
    csv_text = export.to_csv(index=False, lineterminator="\n")
    encoded = base64.b64encode(csv_text.encode("utf-8")).decode("ascii")
    type_pairs = ", ".join(
        f'{{"{column}", {power_query_type}}}'
        for column, power_query_type in type_map.items()
    )
    return [
        "let",
        f'    Binary = Binary.FromText("{encoded}", BinaryEncoding.Base64),',
        f'    Source = Csv.Document(Binary, [Delimiter=",", Columns={len(frame.columns)}, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
        "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
        f'    Typed = Table.TransformColumnTypes(Promoted, {{{type_pairs}}}, "en-US")',
        "in",
        "    Typed",
    ]


def column_metadata(frame: pd.DataFrame, type_map: dict[str, str]) -> list[dict]:
    columns = []
    for column in frame.columns:
        pq_type = type_map[column]
        if pq_type == "type date":
            metadata = {
                "name": column,
                "dataType": "dateTime",
                "sourceColumn": column,
                "formatString": "mmm yyyy" if column == "Month" else "yyyy-mm-dd",
            }
        elif pq_type == "Int64.Type":
            metadata = {
                "name": column,
                "dataType": "int64",
                "sourceColumn": column,
                "formatString": "#,0",
            }
        elif pq_type == "type number":
            metadata = {
                "name": column,
                "dataType": "double",
                "sourceColumn": column,
            }
        elif pq_type == "type logical":
            metadata = {
                "name": column,
                "dataType": "boolean",
                "sourceColumn": column,
            }
        else:
            metadata = {
                "name": column,
                "dataType": "string",
                "sourceColumn": column,
            }
        columns.append(metadata)
    return columns


def table_metadata(
    name: str,
    frame: pd.DataFrame,
    type_map: dict[str, str],
    measures: list[dict] | None = None,
) -> dict:
    table = {
        "name": name,
        "columns": column_metadata(frame, type_map),
        "partitions": [
            {
                "name": name,
                "mode": "import",
                "source": {
                    "type": "m",
                    "expression": csv_m_expression(frame, type_map),
                },
            }
        ],
    }
    if measures:
        table["measures"] = measures
    return table


def prepare_model_frames() -> dict[str, tuple[pd.DataFrame, dict[str, str]]]:
    monthly = pd.read_csv(DATA_DIR / "monthly_performance.csv")
    sales = pd.read_csv(DATA_DIR / "fact_weekly_sales.csv", parse_dates=["WeekStart"])
    inventory = pd.read_csv(
        DATA_DIR / "fact_inventory_snapshot.csv", parse_dates=["WeekStart"]
    )
    forecast = pd.read_csv(DATA_DIR / "forecast_results.csv", parse_dates=["WeekStart"])
    products = pd.read_csv(DATA_DIR / "dim_product.csv")
    replenishment = pd.read_csv(DATA_DIR / "replenishment_recommendations.csv")
    scenario = pd.read_csv(DATA_DIR / "scenario_summary.csv").set_index("Scenario")

    calendar = pd.DataFrame(
        {
            "Date": pd.date_range("2023-01-01", "2026-12-01", freq="MS"),
        }
    )
    calendar["Month"] = calendar["Date"].dt.strftime("%b %Y")
    calendar["Month Key"] = calendar["Date"].dt.strftime("%Y-%m")

    historical_monthly = pd.DataFrame(
        {
            "Month": pd.to_datetime(monthly["YearMonth"] + "-01"),
            "Month Key": monthly["YearMonth"],
            "Estimated Demand": monthly["EstimatedDemandUnits"].round().astype(int),
            "Units Sold": monthly["UnitsSold"].round().astype(int),
            "Fulfilled Demand": monthly["UnitsSold"].round().astype(int),
            "Lost Sales": monthly["LostSalesUnits"].round().astype(int),
            "Stockout Events": monthly["StockoutSKUWeeks"].round().astype(int),
            "Average Inventory Value": monthly["AverageInventoryValueTRY"],
            "Net Revenue": monthly["NetRevenueTRY"],
            "Gross Profit": monthly["GrossProfitTRY"],
            "Inventory Value": monthly["AverageInventoryValueTRY"],
            "Weeks of Supply": monthly["AverageWeeksOfSupply"],
            "Stockout SKU Weeks": monthly["StockoutSKUWeeks"].round().astype(int),
            "Average Discount Rate": monthly["AverageDiscountPct"],
            "Demand Fulfillment Rate": monthly["DemandFulfillmentRate"],
            "Gross Margin Rate": monthly["GrossMarginPct"],
            "Service Level": monthly["DemandFulfillmentRate"],
            "Margin Attainment": monthly["GrossMarginPct"] / 0.55,
        }
    )
    forecast["Month Key"] = forecast["WeekStart"].dt.strftime("%Y-%m")
    future_grouped = (
        forecast.groupby("Month Key", as_index=False)
        .apply(
            lambda frame: pd.Series(
                {
                    "Estimated Demand": frame["ForecastUnits"].sum(),
                    "Net Revenue": frame["ForecastRevenueTRY"].sum(),
                    "Average Discount Rate": np.average(
                        frame["ExpectedDiscountPct"],
                        weights=np.maximum(frame["ForecastUnits"], 0.01),
                    ),
                }
            ),
            include_groups=False,
        )
        .reset_index(drop=True)
    )
    base = scenario.loc["Base"]
    future_monthly = pd.DataFrame(
        {
            "Month": pd.to_datetime(future_grouped["Month Key"] + "-01"),
            "Month Key": future_grouped["Month Key"],
            "Estimated Demand": future_grouped["Estimated Demand"].round().astype(int),
            "Units Sold": future_grouped["Estimated Demand"].round().astype(int),
            "Fulfilled Demand": future_grouped["Estimated Demand"].round().astype(int),
            "Lost Sales": 0,
            "Stockout Events": 0,
            "Average Inventory Value": base["RecommendedInvestmentTRY"] / 12,
            "Net Revenue": future_grouped["Net Revenue"],
            "Gross Profit": future_grouped["Net Revenue"] * 0.58,
            "Inventory Value": base["RecommendedInvestmentTRY"] / 12,
            "Weeks of Supply": base["AverageWeeksOfSupply"],
            "Stockout SKU Weeks": 0,
            "Average Discount Rate": future_grouped["Average Discount Rate"],
            "Demand Fulfillment Rate": 1.0,
            "Gross Margin Rate": 0.58,
            "Service Level": 0.97,
            "Margin Attainment": 0.58 / 0.55,
        }
    )
    monthly_model = pd.concat(
        [historical_monthly, future_monthly], ignore_index=True
    ).sort_values("Month")

    sales = sales.merge(
        products[["SKU", "ProductName", "Category"]], on="SKU", how="left"
    )
    sales["Month"] = sales["WeekStart"].dt.to_period("M").dt.to_timestamp()
    sales["Month Key"] = sales["Month"].dt.strftime("%Y-%m")
    sku_history = (
        sales.groupby(
            ["Month", "Month Key", "SKU", "ProductName"], as_index=False
        )
        .agg(
            **{
                "Estimated Demand": ("EstimatedDemandUnits", "sum"),
                "Lost Sales": ("LostSalesUnits", "sum"),
                "Stockout Events": ("StockoutFlag", "sum"),
                "Net Revenue": ("NetRevenueTRY", "sum"),
                "Gross Profit": ("GrossProfitTRY", "sum"),
            }
        )
    )
    inventory["Month"] = inventory["WeekStart"].dt.to_period("M").dt.to_timestamp()
    sku_inventory = (
        inventory.groupby(["Month", "SKU"], as_index=False)
        .agg(**{"Weeks of Supply": ("WeeksOfSupply", "mean")})
    )
    sku_history = sku_history.merge(sku_inventory, on=["Month", "SKU"], how="left")
    sku_history["Service Level"] = 1 - (
        sku_history["Lost Sales"] / sku_history["Estimated Demand"].replace(0, np.nan)
    )
    sku_history["Service Level"] = sku_history["Service Level"].fillna(1.0)
    sku_history["Estimated Demand"] = (
        sku_history["Estimated Demand"].round().astype(int)
    )
    sku_history["Lost Sales"] = sku_history["Lost Sales"].round().astype(int)
    sku_history["Stockout Events"] = sku_history["Stockout Events"].astype(int)
    sku_model = sku_history[
        [
            "Month",
            "Month Key",
            "ProductName",
            "Estimated Demand",
            "Lost Sales",
            "Stockout Events",
            "Net Revenue",
            "Gross Profit",
            "Service Level",
            "Weeks of Supply",
        ]
    ].rename(columns={"ProductName": "Product"})

    forecast_with_product = forecast.merge(
        products[["SKU", "ProductName"]], on="SKU", how="left"
    ).merge(
        replenishment[["SKU", "ProjectedWeeksOfSupply"]], on="SKU", how="left"
    )
    forecast_with_product["Month"] = (
        forecast_with_product["WeekStart"].dt.to_period("M").dt.to_timestamp()
    )
    sku_future = (
        forecast_with_product.groupby(
            ["Month", "Month Key", "SKU", "ProductName"], as_index=False
        )
        .agg(
            **{
                "Estimated Demand": ("ForecastUnits", "sum"),
                "Net Revenue": ("ForecastRevenueTRY", "sum"),
                "Weeks of Supply": ("ProjectedWeeksOfSupply", "first"),
            }
        )
    )
    sku_future["Lost Sales"] = 0
    sku_future["Stockout Events"] = 0
    sku_future["Gross Profit"] = sku_future["Net Revenue"] * 0.58
    sku_future["Service Level"] = 0.97
    sku_future["Estimated Demand"] = (
        sku_future["Estimated Demand"].round().astype(int)
    )
    sku_future = sku_future[
        [
            "Month",
            "Month Key",
            "ProductName",
            "Estimated Demand",
            "Lost Sales",
            "Stockout Events",
            "Net Revenue",
            "Gross Profit",
            "Service Level",
            "Weeks of Supply",
        ]
    ].rename(columns={"ProductName": "Product"})
    sku_model = pd.concat([sku_model, sku_future], ignore_index=True)

    category_history = (
        sales.groupby(["Month", "Month Key", "Category"], as_index=False)
        .agg(
            **{
                "Estimated Demand": ("EstimatedDemandUnits", "sum"),
                "Fulfilled Demand": ("UnitsSold", "sum"),
                "Gross Profit": ("GrossProfitTRY", "sum"),
            }
        )
    )
    category_history["Demand Fulfillment Rate"] = (
        category_history["Fulfilled Demand"]
        / category_history["Estimated Demand"].replace(0, np.nan)
    ).fillna(1.0)
    category_history["Estimated Demand"] = (
        category_history["Estimated Demand"].round().astype(int)
    )
    category_history["Fulfilled Demand"] = (
        category_history["Fulfilled Demand"].round().astype(int)
    )
    category_future = (
        forecast.groupby(["Month Key", "Category"], as_index=False)
        .agg(
            **{
                "Estimated Demand": ("ForecastUnits", "sum"),
                "Gross Profit": ("ForecastRevenueTRY", lambda values: values.sum() * 0.58),
            }
        )
    )
    category_future["Month"] = pd.to_datetime(category_future["Month Key"] + "-01")
    category_future["Fulfilled Demand"] = category_future[
        "Estimated Demand"
    ]
    category_future["Demand Fulfillment Rate"] = 1.0
    category_future["Estimated Demand"] = (
        category_future["Estimated Demand"].round().astype(int)
    )
    category_future["Fulfilled Demand"] = (
        category_future["Fulfilled Demand"].round().astype(int)
    )
    category_model = pd.concat(
        [
            category_history[
                [
                    "Month",
                    "Month Key",
                    "Category",
                    "Estimated Demand",
                    "Fulfilled Demand",
                    "Demand Fulfillment Rate",
                    "Gross Profit",
                ]
            ],
            category_future[
                [
                    "Month",
                    "Month Key",
                    "Category",
                    "Estimated Demand",
                    "Fulfilled Demand",
                    "Demand Fulfillment Rate",
                    "Gross Profit",
                ]
            ],
        ],
        ignore_index=True,
    )

    stages = pd.DataFrame(
        {
            "Stage": [
                "Estimated Demand",
                "Fulfilled Demand",
                "Lost Sales",
                "Stockout Events",
            ],
            "Stage Order": [1, 2, 3, 4],
        }
    )

    return {
        "dim_calendar": (
            calendar,
            {
                "Date": "type date",
                "Month": "type text",
                "Month Key": "type text",
            },
        ),
        "monthly_performance": (
            monthly_model,
            {
                "Month": "type date",
                "Month Key": "type text",
                "Estimated Demand": "Int64.Type",
                "Units Sold": "Int64.Type",
                "Fulfilled Demand": "Int64.Type",
                "Lost Sales": "Int64.Type",
                "Stockout Events": "Int64.Type",
                "Average Inventory Value": "type number",
                "Net Revenue": "type number",
                "Gross Profit": "type number",
                "Inventory Value": "type number",
                "Weeks of Supply": "type number",
                "Stockout SKU Weeks": "Int64.Type",
                "Average Discount Rate": "type number",
                "Demand Fulfillment Rate": "type number",
                "Gross Margin Rate": "type number",
                "Service Level": "type number",
                "Margin Attainment": "type number",
            },
        ),
        "sku_performance": (
            sku_model,
            {
                "Month": "type date",
                "Month Key": "type text",
                "Product": "type text",
                "Estimated Demand": "Int64.Type",
                "Lost Sales": "Int64.Type",
                "Stockout Events": "Int64.Type",
                "Net Revenue": "type number",
                "Gross Profit": "type number",
                "Service Level": "type number",
                "Weeks of Supply": "type number",
            },
        ),
        "category_performance": (
            category_model,
            {
                "Month": "type date",
                "Month Key": "type text",
                "Category": "type text",
                "Estimated Demand": "Int64.Type",
                "Fulfilled Demand": "Int64.Type",
                "Demand Fulfillment Rate": "type number",
                "Gross Profit": "type number",
            },
        ),
        "Demand Stages": (
            stages,
            {"Stage": "type text", "Stage Order": "Int64.Type"},
        ),
    }


def build_measures() -> dict[str, list[dict]]:
    monthly_measures = [
        ("Historical Demand", "SUM(monthly_performance[Estimated Demand])", "#,0"),
        ("Units Sold", "SUM(monthly_performance[Units Sold])", "#,0"),
        ("Fulfilled Demand", "SUM(monthly_performance[Fulfilled Demand])", "#,0"),
        ("Lost Sales", "SUM(monthly_performance[Lost Sales])", "#,0"),
        ("Stockout Events", "SUM(monthly_performance[Stockout Events])", "#,0"),
        ("Historical Revenue", "SUM(monthly_performance[Net Revenue])", "₺#,0"),
        ("Gross Profit", "SUM(monthly_performance[Gross Profit])", "₺#,0"),
        ("Inventory Value", "SUM(monthly_performance[Inventory Value])", "₺#,0"),
        (
            "Average Inventory Value",
            "AVERAGE(monthly_performance[Average Inventory Value])",
            "₺#,0",
        ),
        (
            "Demand Fulfillment",
            "DIVIDE([Fulfilled Demand],[Historical Demand],0)",
            "0.0%",
        ),
        (
            "Gross Margin",
            "DIVIDE([Gross Profit],[Historical Revenue],0)",
            "0.0%",
        ),
        (
            "Service Level",
            "AVERAGE(monthly_performance[Service Level])",
            "0.0%",
        ),
        (
            "Margin Attainment",
            "AVERAGE(monthly_performance[Margin Attainment])",
            "0.0%",
        ),
        (
            "Weeks of Supply",
            "AVERAGE(monthly_performance[Weeks of Supply])",
            "0.0",
        ),
        (
            "Stockout SKU Weeks",
            "SUM(monthly_performance[Stockout SKU Weeks])",
            "#,0",
        ),
        (
            "Average Discount",
            "AVERAGE(monthly_performance[Average Discount Rate])",
            "0.0%",
        ),
        (
            "Historical Demand PY",
            "CALCULATE([Historical Demand],DATEADD(dim_calendar[Date],-1,YEAR))",
            "#,0",
        ),
        (
            "Historical Revenue PY",
            "CALCULATE([Historical Revenue],DATEADD(dim_calendar[Date],-1,YEAR))",
            "₺#,0",
        ),
        (
            "Demand YoY %",
            "DIVIDE([Historical Demand]-[Historical Demand PY],[Historical Demand PY],0)",
            "0.0%",
        ),
        (
            "Revenue YoY %",
            "DIVIDE([Historical Revenue]-[Historical Revenue PY],[Historical Revenue PY],0)",
            "0.0%",
        ),
        (
            "Gross Profit Variance",
            "[Historical Revenue]-[Gross Profit]",
            "₺#,0",
        ),
        (
            "Revenue vs GP Variance %",
            "DIVIDE([Gross Profit Variance],[Gross Profit],0)",
            "0.0%",
        ),
        ("Service Level Target", "0.95", "0.0%"),
        ("Inventory Target", "[Gross Profit]*0.08", "₺#,0"),
    ]
    sku_measures = [
        ("SKU Revenue", "SUM(sku_performance[Net Revenue])", "₺#,0"),
        ("SKU Gross Profit", "SUM(sku_performance[Gross Profit])", "₺#,0"),
        ("SKU Units Sold", "SUM(sku_performance[Estimated Demand])", "#,0"),
        ("SKU Lost Sales", "SUM(sku_performance[Lost Sales])", "#,0"),
        (
            "SKU Fulfillment Rate",
            "AVERAGE(sku_performance[Service Level])",
            "0.0%",
        ),
        (
            "SKU Weeks of Supply",
            "AVERAGE(sku_performance[Weeks of Supply])",
            "0.0",
        ),
    ]
    category_measures = [
        (
            "Category Demand",
            "SUM(category_performance[Estimated Demand])",
            "#,0",
        ),
        (
            "Category Units Sold",
            "SUM(category_performance[Fulfilled Demand])",
            "#,0",
        ),
        (
            "Category Fulfillment",
            "DIVIDE([Category Units Sold],[Category Demand],0)",
            "0.0%",
        ),
        (
            "Category Gross Profit",
            "SUM(category_performance[Gross Profit])",
            "₺#,0",
        ),
    ]
    stage_measures = [
        (
            "Demand Stage Value",
            'SWITCH(SELECTEDVALUE(\'Demand Stages\'[Stage]),"Estimated Demand",[Historical Demand],"Fulfilled Demand",[Fulfilled Demand],"Lost Sales",[Lost Sales],"Stockout Events",[Stockout Events],BLANK())',
            "#,0",
        )
    ]

    def convert(items: list[tuple[str, str, str]]) -> list[dict]:
        return [
            {"name": name, "expression": expression, "formatString": fmt}
            for name, expression, fmt in items
        ]

    return {
        "monthly_performance": convert(monthly_measures),
        "sku_performance": convert(sku_measures),
        "category_performance": convert(category_measures),
        "Demand Stages": convert(stage_measures),
    }


def build_semantic_model(model_dir: Path) -> None:
    template_model_path = (
        TEMPLATE_ROOT
        / "CRM_Sales_Analytics.SemanticModel"
        / "model.bim"
    )
    model = json.loads(template_model_path.read_text(encoding="utf-8"))
    frames = prepare_model_frames()
    measure_map = build_measures()
    tables = []
    for name, (frame, type_map) in frames.items():
        tables.append(
            table_metadata(name, frame, type_map, measure_map.get(name))
        )
    model["model"]["tables"] = tables
    model["model"]["relationships"] = [
        {
            "name": "rel_monthly_calendar",
            "fromTable": "monthly_performance",
            "fromColumn": "Month",
            "toTable": "dim_calendar",
            "toColumn": "Date",
        },
        {
            "name": "rel_sku_calendar",
            "fromTable": "sku_performance",
            "fromColumn": "Month",
            "toTable": "dim_calendar",
            "toColumn": "Date",
        },
        {
            "name": "rel_category_calendar",
            "fromTable": "category_performance",
            "fromColumn": "Month",
            "toTable": "dim_calendar",
            "toColumn": "Date",
        },
    ]
    (model_dir / "model.bim").write_text(
        json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8"
    )


REPLACEMENTS = {
    "KPI Lead Qualification Rate": "Demand Fulfillment",
    "KPI Opportunity Conversion": "Gross Margin",
    "KPI Target Attainment": "Margin Attainment",
    "KPI Average Deal Size": "Average Inventory Value",
    "KPI Revenue Variance %": "Revenue vs GP Variance %",
    "KPI Revenue Variance": "Gross Profit Variance",
    "KPI New Leads PY": "Historical Demand PY",
    "KPI Won Revenue PY": "Historical Revenue PY",
    "KPI Leads YoY %": "Demand YoY %",
    "KPI Revenue YoY %": "Revenue YoY %",
    "KPI Pipeline Target": "Inventory Target",
    "KPI Win Rate Target": "Service Level Target",
    "KPI Sales Cycle Days": "Weeks of Supply",
    "KPI Qualified Leads": "Fulfilled Demand",
    "KPI Pipeline Value": "Inventory Value",
    "KPI Revenue Target": "Gross Profit",
    "KPI Won Revenue": "Historical Revenue",
    "KPI New Customers": "Stockout SKU Weeks",
    "KPI Opportunities": "Lost Sales",
    "KPI Won Deals": "Stockout Events",
    "KPI Lead Target": "Units Sold",
    "KPI New Leads": "Historical Demand",
    "KPI Win Rate": "Service Level",
    "KPI Churn Rate": "Average Discount",
    "Rep Sales Cycle Days": "SKU Weeks of Supply",
    "Rep Revenue Target": "SKU Gross Profit",
    "Rep Won Revenue": "SKU Revenue",
    "Rep Opportunities": "SKU Lost Sales",
    "Rep Won Deals": "SKU Units Sold",
    "Rep Win Rate": "SKU Fulfillment Rate",
    "Source Qualification Rate": "Category Fulfillment",
    "Source Acquisition Spend": "Category Gross Profit",
    "Source Qualified Leads": "Category Units Sold",
    "Source New Leads": "Category Demand",
    "Funnel Stage Value": "Demand Stage Value",
    "Lead Qualification Rate": "Demand Fulfillment Rate",
    "Opportunity Conversion": "Gross Margin Rate",
    "Average Deal Size": "Average Inventory Value",
    "Target Attainment": "Margin Attainment",
    "Sales Cycle Days": "Weeks of Supply",
    "Qualified Leads": "Fulfilled Demand",
    "Pipeline Value": "Inventory Value",
    "Revenue Target": "Gross Profit",
    "Won Revenue": "Net Revenue",
    "New Customers": "Stockout SKU Weeks",
    "Opportunities": "Lost Sales",
    "Won Deals": "Stockout Events",
    "Lead Target": "Units Sold",
    "New Leads": "Estimated Demand",
    "Churn Rate": "Average Discount Rate",
    "Win Rate": "Service Level",
    "Sales Rep": "Product",
    "Lead Source": "Category",
    "Qualification Rate": "Demand Fulfillment Rate",
    "Acquisition Spend": "Gross Profit",
    "crm_rep_performance": "sku_performance",
    "crm_lead_sources": "category_performance",
    "crm_monthly": "monthly_performance",
    "Funnel Stages": "Demand Stages",
    "Calendar": "dim_calendar",
    "CRM SALES ANALYTICS": "E-COMMERCE DEMAND ANALYTICS",
    "CRM Sales Analytics": "E-Commerce Demand Analytics",
    "Lead Generation": "Demand History",
    "Sales Funnel": "Demand Fulfillment",
    "Revenue Performance": "Revenue & Margin",
    "Pipeline Analysis": "Inventory Health",
    "Sales Rep Performance": "SKU Performance",
    "Lead Source Analysis": "Category Performance",
    "Customer & Segments": "Product Segments",
    "Target vs Actual": "Forecast Accuracy",
    "Three-Year Trends": "History & Forecast",
    "LEAD GENERATION": "DEMAND HISTORY",
    "SALES FUNNEL": "DEMAND FULFILLMENT",
    "PIPELINE ANALYSIS": "INVENTORY HEALTH",
    "SALES REP PERFORMANCE": "SKU PERFORMANCE",
    "LEAD SOURCE ANALYSIS": "CATEGORY PERFORMANCE",
    "CUSTOMER & SEGMENTS": "PRODUCT SEGMENTS",
    "TARGET VS ACTUAL": "FORECAST ACCURACY",
    "THREE-YEAR TRENDS": "HISTORY & FORECAST",
    "Leads Actual vs Target": "Demand vs Fulfilled",
    "Leads by Source": "Demand by Category",
    "Lead Mix by Source": "Demand Mix by Category",
    "New and Fulfilled Demand by Source": "Estimated and Fulfilled Demand by Category",
    "New and Qualified Leads by Source": "Estimated and Fulfilled Demand by Category",
    "Pipeline and Target Trend": "Inventory & Benchmark Trend",
    "Revenue Actual vs Target": "Revenue vs Gross Profit",
    "Revenue — Actual vs Target": "Revenue vs Gross Profit",
    "Rep Revenue vs Target": "SKU Revenue vs Gross Profit",
    "Selected Month Funnel": "Selected Month Demand Flow",
    "Conversion Rates": "Fulfillment & Margin Rates",
    "36-Month Commercial Trend": "48-Month Revenue Trend",
    "36-Month Conversion Trend": "48-Month Service Trend",
    "Three-Year Revenue Trend": "Four-Year Revenue Trend",
    "Monthly Revenue Variance": "Monthly Revenue-GP Gap",
    "New Customer Trend": "Stockout Event Trend",
    "CUSTOMER REVENUE": "SEGMENT REVENUE",
    "NEW CUSTOMERS": "STOCKOUT SKU WEEKS",
    "CHURN RATE": "AVG DISCOUNT",
    "AVG DEAL SIZE": "AVG INVENTORY VALUE",
    "TEAM SERVICE LEVEL": "PORTFOLIO SERVICE LEVEL",
    "TEAM WIN RATE": "PORTFOLIO SERVICE LEVEL",
    "TEAM TARGET": "PORTFOLIO GROSS PROFIT",
    "TEAM REVENUE": "PORTFOLIO REVENUE",
    "INVENTORY TARGET": "INVENTORY BENCHMARK",
    "PIPELINE TARGET": "INVENTORY BENCHMARK",
    "REVENUE TARGET": "GROSS PROFIT",
    "ACTUAL REVENUE": "NET REVENUE",
    "QUALIFICATION RATE": "FULFILLMENT RATE",
    "TOTAL LEADS": "TOTAL DEMAND",
    "WON DEALS": "STOCKOUT EVENTS",
    "OPPORTUNITIES": "LOST SALES",
    "QUALIFIED": "FULFILLED",
    "ATTAINMENT": "MARGIN ATTAINMENT",
    "VARIANCE": "REVENUE-GP GAP",
    "YOY GROWTH": "DEMAND YOY",
    "TARGET": "GROSS PROFIT",
    "NEW LEADS": "ESTIMATED DEMAND",
    "QUALIFIED LEADS": "FULFILLED DEMAND",
    "WON REVENUE": "NET REVENUE",
    "LEAD TARGET": "UNITS SOLD",
    "PIPELINE": "INVENTORY",
    "WIN RATE": "SERVICE LEVEL",
    "SALES CYCLE": "WEEKS OF SUPPLY",
    "SALES REP": "PRODUCT",
    "LEAD SOURCE": "CATEGORY",
}


PAGE_NAMES = [
    "1. Executive Overview",
    "2. Demand History",
    "3. Demand Fulfillment",
    "4. Revenue & Margin",
    "5. Inventory Health",
    "6. SKU Performance",
    "7. Category Performance",
    "8. Product Segments",
    "9. Forecast Accuracy",
    "10. History & Forecast",
]


def replace_report_text(report_dir: Path) -> None:
    for path in report_dir.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        for old, new in sorted(
            REPLACEMENTS.items(), key=lambda item: len(item[0]), reverse=True
        ):
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
    page_dirs = []
    pages_meta = json.loads(
        (report_dir / "definition" / "pages" / "pages.json").read_text(
            encoding="utf-8"
        )
    )
    for page_name in pages_meta["pageOrder"]:
        page_path = report_dir / "definition" / "pages" / page_name / "page.json"
        page = json.loads(page_path.read_text(encoding="utf-8"))
        page_dirs.append((page_path, page))
    for display_name, (page_path, page) in zip(PAGE_NAMES, page_dirs, strict=True):
        page["displayName"] = display_name
        page_path.write_text(
            json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def update_theme_and_metadata(report_dir: Path, model_dir: Path) -> None:
    old_theme = (
        report_dir
        / "StaticResources"
        / "RegisteredResources"
        / "CRMModernDark-7f3c2a91.json"
    )
    new_theme_name = "EcommerceDemandDark-7f3c2a91.json"
    new_theme = old_theme.with_name(new_theme_name)
    theme = json.loads(old_theme.read_text(encoding="utf-8"))
    theme["name"] = new_theme_name
    theme["dataColors"] = [
        "#3D8DFF",
        "#6DCBF4",
        "#18A558",
        "#F59E0B",
        "#D64545",
        "#7C3AED",
    ]
    new_theme.write_text(
        json.dumps(theme, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    old_theme.unlink()

    report_json_path = report_dir / "definition" / "report.json"
    report_json = json.loads(report_json_path.read_text(encoding="utf-8"))
    report_json["themeCollection"]["customTheme"]["name"] = new_theme_name
    report_json["resourcePackages"][0]["items"][0]["name"] = new_theme_name
    report_json["resourcePackages"][0]["items"][0]["path"] = new_theme_name
    report_json_path.write_text(
        json.dumps(report_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    report_platform_path = report_dir / ".platform"
    report_platform = json.loads(report_platform_path.read_text(encoding="utf-8"))
    report_platform["metadata"]["displayName"] = (
        "E-Commerce Demand & Inventory Analytics"
    )
    report_platform["config"]["logicalId"] = str(
        uuid.uuid5(uuid.NAMESPACE_URL, "ecommerce-demand-report")
    )
    report_platform_path.write_text(
        json.dumps(report_platform, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    model_platform_path = model_dir / ".platform"
    model_platform = json.loads(model_platform_path.read_text(encoding="utf-8"))
    model_platform["metadata"]["displayName"] = (
        "E-Commerce Demand & Inventory Analytics"
    )
    model_platform["config"]["logicalId"] = str(
        uuid.uuid5(uuid.NAMESPACE_URL, "ecommerce-demand-model")
    )
    model_platform_path.write_text(
        json.dumps(model_platform, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def validate_pbip(report_dir: Path, model_dir: Path) -> dict:
    errors = []
    json_files = list(report_dir.rglob("*.json")) + [
        report_dir / ".platform",
        report_dir / "definition.pbir",
        model_dir / ".platform",
        model_dir / "definition.pbism",
        model_dir / "model.bim",
        PBIP_PATH,
    ]
    for path in json_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"Invalid JSON: {path.relative_to(OUTPUT_ROOT)}: {exc}")

    pages_root = report_dir / "definition" / "pages"
    page_files = list(pages_root.glob("*/page.json"))
    if len(page_files) != 10:
        errors.append(f"Expected 10 pages; found {len(page_files)}")
    for page_file in page_files:
        page = json.loads(page_file.read_text(encoding="utf-8"))
        if page.get("width") != 1280 or page.get("height") != 720:
            errors.append(f"Non-HD page canvas: {page.get('displayName')}")
        visual_count = len(list(page_file.parent.glob("visuals/*/visual.json")))
        if visual_count < 4:
            errors.append(
                f"Too few visuals on {page.get('displayName')}: {visual_count}"
            )

    model = json.loads((model_dir / "model.bim").read_text(encoding="utf-8"))
    table_names = {table["name"] for table in model["model"]["tables"]}
    model_text = (model_dir / "model.bim").read_text(encoding="utf-8")
    report_text = "\n".join(
        path.read_text(encoding="utf-8") for path in report_dir.rglob("*.json")
    )
    for token in [
        "crm_",
        "CRM SALES",
        "Lead Generation",
        "Sales Funnel",
        "Leads ",
        "Lead ",
        "LEAD",
        "Won Deals",
        "WON DEALS",
        "Pipeline",
        "PIPELINE",
    ]:
        if token in report_text or token in model_text:
            errors.append(f"Legacy CRM token remains: {token}")

    entity_values = set()

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "Entity" and isinstance(item, str):
                    entity_values.add(item)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for path in report_dir.rglob("visual.json"):
        walk(json.loads(path.read_text(encoding="utf-8")))
    unknown_entities = sorted(entity_values - table_names)
    if unknown_entities:
        errors.append(f"Unknown visual entities: {unknown_entities}")

    report = {
        "project": PROJECT_NAME,
        "pages": len(page_files),
        "visuals": len(list(report_dir.rglob("visual.json"))),
        "tables": sorted(table_names),
        "relationships": len(model["model"].get("relationships", [])),
        "valid": not errors,
        "errors": errors,
    }
    (OUTPUT_ROOT / "pbip_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def build_pbip() -> Path:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    report_dir = OUTPUT_ROOT / REPORT_NAME
    model_dir = OUTPUT_ROOT / MODEL_NAME
    shutil.copytree(
        TEMPLATE_ROOT / "CRM_Sales_Analytics.Report",
        report_dir,
    )
    shutil.copytree(
        TEMPLATE_ROOT / "CRM_Sales_Analytics.SemanticModel",
        model_dir,
    )

    definition_pbir = json.loads(
        (report_dir / "definition.pbir").read_text(encoding="utf-8")
    )
    definition_pbir["datasetReference"]["byPath"]["path"] = f"../{MODEL_NAME}"
    (report_dir / "definition.pbir").write_text(
        json.dumps(definition_pbir, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    pbip = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [{"report": {"path": REPORT_NAME}}],
        "settings": {"enableAutoRecovery": True},
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    PBIP_PATH.write_text(
        json.dumps(pbip, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    build_semantic_model(model_dir)
    replace_report_text(report_dir)
    update_theme_and_metadata(report_dir, model_dir)

    readme = """E-Commerce Demand Forecasting & Inventory Optimization - Power BI Project

Open Ecommerce_Demand_Inventory_Analytics.pbip with a current version of Power BI Desktop.
The semantic model embeds the synthetic portfolio data, so no local CSV path remapping is required.

Pages:
1. Executive Overview
2. Demand History
3. Demand Fulfillment
4. Revenue & Margin
5. Inventory Health
6. SKU Performance
7. Category Performance
8. Product Segments
9. Forecast Accuracy
10. History & Forecast

Data notice: MonacoLuxe-inspired synthetic portfolio data. No real customer or company records are included.
"""
    (OUTPUT_ROOT / "README.txt").write_text(readme, encoding="utf-8")
    report = validate_pbip(report_dir, model_dir)
    if not report["valid"]:
        raise RuntimeError(json.dumps(report, ensure_ascii=False, indent=2))
    return PBIP_PATH


if __name__ == "__main__":
    print(build_pbip())
