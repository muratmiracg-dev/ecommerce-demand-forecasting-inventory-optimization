# Data Dictionary

## Core Dimensions

### `dim_calendar.csv`

| Field | Meaning |
|---|---|
| Date / WeekStart | Weekly calendar key |
| Year, Quarter, Month | Reporting hierarchy |
| ISOWeek | ISO week number |
| IsForecast | Historical or forecast-period indicator |

### `dim_product.csv`

| Field | Meaning |
|---|---|
| SKU | Unique product identifier |
| ProductName | Synthetic product name |
| Category / Segment / Collection | Commercial hierarchy |
| SupplierID | Supplier foreign key |
| UnitCostTRY / ListPriceTRY | Unit economics |
| LeadTimeDays | Standard replenishment lead time |
| MOQ / CasePack | Purchasing constraints |
| TargetServiceLevel | SKU service-level objective |
| BaseWeeklyDemand | Synthetic demand baseline |
| LifecycleStage | Product lifecycle classification |

### `dim_supplier.csv`

| Field | Meaning |
|---|---|
| SupplierID | Unique supplier identifier |
| SupplierName | Synthetic supplier name |
| Country / Region | Supplier geography |
| StandardLeadTimeDays | Planned lead time |
| OnTimeDeliveryRate | Historical delivery reliability |
| QualityAcceptanceRate | Accepted-unit ratio |
| OrderCostTRY | Fixed purchasing cost |
| PaymentTermsDays | Commercial payment terms |

## Historical Facts

### `fact_weekly_sales.csv`

Grain: week × SKU × channel.

| Field | Meaning |
|---|---|
| WeekStart | Weekly date key |
| SKU | Product key |
| Channel | Website, Marketplace, or Social Shop |
| CampaignName / PromotionFlag | Promotion context |
| DiscountPct | Average discount rate |
| UnitsSold | Fulfilled sales units |
| EstimatedDemandUnits | Estimated unconstrained demand |
| LostSalesUnits | Demand not fulfilled because of stock constraints |
| GrossSalesTRY | Gross sales value |
| DiscountTRY | Discount value |
| NetRevenueTRY | Revenue after discount |
| COGSTRY | Cost of goods sold |
| GrossProfitTRY | Net revenue minus COGS |
| StockoutFlag | Stockout-affected observation |

### `fact_inventory_snapshot.csv`

Grain: week × SKU.

| Field | Meaning |
|---|---|
| BeginningOnHand / EndingOnHand | Weekly inventory balance |
| Receipts | Units received |
| OnOrderUnits | Open purchase-order quantity |
| InventoryValueTRY | Ending inventory value |
| WeeksOfSupply | Inventory position divided by expected weekly demand |
| ReorderPointReference | Synthetic operating reorder point |
| ReorderTriggered | Whether replenishment was triggered |

### `fact_purchase_orders.csv`

Grain: purchase order × SKU.

| Field | Meaning |
|---|---|
| POID | Purchase-order identifier |
| OrderDate | Order creation date |
| ExpectedReceiptDate / ActualReceiptDate | Planned and actual delivery |
| OrderedQty / ReceivedQty | Ordered and received units |
| UnitCostTRY / POValueTRY | Purchasing value |
| ActualLeadTimeDays | Realized lead time |
| OnTimeFlag | On-time delivery indicator |

### `fact_promotions.csv`

Grain: campaign × week × category.

Contains promotion type, discount, uplift, channel, and campaign-period context.

## Model Outputs

### `model_comparison.csv`

One row per SKU and candidate model, with MAE, RMSE, WAPE, bias, rank, and
champion flag.

### `forecast_backtest.csv`

Holdout-period actuals and model predictions used for model governance.

### `forecast_results.csv`

Grain: forecast week × SKU.

| Field | Meaning |
|---|---|
| ForecastUnits | Champion point forecast |
| Lower80Units / Upper80Units | 80% prediction interval |
| ChampionModel | Selected model |
| ResidualStdUnits | Backtest residual uncertainty |
| ForecastRevenueTRY | Expected revenue at forecast selling price |

## Inventory Outputs

### `inventory_scenarios.csv`

Grain: scenario × SKU. Includes service level, lead time, forecast demand,
inventory position, safety stock, reorder point, EOQ, recommended quantity,
required investment, and action.

### `replenishment_recommendations.csv`

Base-scenario SKU recommendations used by the operational reports.

### `scenario_summary.csv`

Scenario-level revenue, order units, investment, weeks of supply, safety stock,
order count, projected gross margin, and investment-to-revenue ratio.

## Reporting Tables

- `monthly_performance.csv`
- `category_performance.csv`
- `sku_performance.csv`
- `forecast_monthly.csv`
- `supplier_scorecard.csv`

These denormalized tables support Power BI, Excel, PDF, and presentation outputs.
