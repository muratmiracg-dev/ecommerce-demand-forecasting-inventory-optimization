-- 1. Historical revenue and fulfillment by category
SELECT
    p.Category,
    ROUND(SUM(s.NetRevenueTRY), 2) AS NetRevenueTRY,
    ROUND(SUM(s.GrossProfitTRY), 2) AS GrossProfitTRY,
    ROUND(SUM(s.UnitsSold) / NULLIF(SUM(s.EstimatedDemandUnits), 0), 4)
        AS DemandFulfillmentRate
FROM fact_weekly_sales s
JOIN dim_product p ON p.SKU = s.SKU
GROUP BY p.Category
ORDER BY NetRevenueTRY DESC;

-- 2. Champion model distribution
SELECT
    Model,
    COUNT(*) AS ChampionSKUCount,
    ROUND(AVG(WAPE), 4) AS AverageWAPE
FROM model_comparison
WHERE ChampionFlag = 1
GROUP BY Model
ORDER BY ChampionSKUCount DESC;

-- 3. Immediate replenishment priorities
SELECT
    SKU,
    ProductName,
    Category,
    SupplierName,
    RecommendedOrderQty,
    ROUND(RecommendedInvestmentTRY, 2) AS RecommendedInvestmentTRY,
    ROUND(ProjectedWeeksOfSupply, 2) AS ProjectedWeeksOfSupply
FROM replenishment_recommendations
WHERE Action = 'ORDER NOW'
ORDER BY RecommendedInvestmentTRY DESC
LIMIT 15;

-- 4. 2026 forecast by month
SELECT
    SUBSTR(WeekStart, 1, 7) AS YearMonth,
    ROUND(SUM(ForecastUnits), 0) AS ForecastUnits,
    ROUND(SUM(ForecastRevenueTRY), 2) AS ForecastRevenueTRY
FROM forecast_results
GROUP BY SUBSTR(WeekStart, 1, 7)
ORDER BY YearMonth;

-- 5. Scenario investment comparison
SELECT
    Scenario,
    ROUND(ForecastRevenueTRY, 2) AS ForecastRevenueTRY,
    ROUND(RecommendedInvestmentTRY, 2) AS RecommendedInvestmentTRY,
    RecommendedOrderUnits,
    SKUsToOrder,
    OverstockReviewSKUs
FROM scenario_summary
ORDER BY RecommendedInvestmentTRY;

