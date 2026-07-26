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
    Category,
    SUM(ForecastUnits) AS ForecastUnits,
    SUM(ForecastRevenueTRY) AS ForecastRevenueTRY,
    AVG(ResidualStdUnits) AS AverageResidualStdUnits
FROM forecast_results
GROUP BY Category;

CREATE VIEW vw_replenishment_priority AS
SELECT
    SKU,
    ProductName,
    Category,
    SupplierName,
    Action,
    RecommendedOrderQty,
    RecommendedInvestmentTRY,
    ProjectedWeeksOfSupply,
    ReorderPointUnits,
    InventoryPosition,
    ChampionWAPE
FROM replenishment_recommendations
ORDER BY
    CASE Action
        WHEN 'ORDER NOW' THEN 1
        WHEN 'MONITOR' THEN 2
        WHEN 'HEALTHY' THEN 3
        ELSE 4
    END,
    RecommendedInvestmentTRY DESC;

