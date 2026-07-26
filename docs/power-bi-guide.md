# Power BI PBIP Guide

## Open the Project

1. Install a current version of Power BI Desktop.
2. Open
   `PowerBI/Ecommerce_Demand_Inventory_PBIP/Ecommerce_Demand_Inventory_Analytics.pbip`.
3. Allow Power BI Desktop to load the report and semantic model.

The reporting data is embedded in the semantic model. No CSV path remapping is
required.

## Included Report Structure

- 10 report pages
- 81 visuals
- 5 semantic-model tables
- 3 calendar relationships
- 35 reusable measures
- 2023–2025 history plus 2026 forecast context

## Important Notes

- Keep relationship filter direction single-direction.
- Do not rename model columns without updating dependent measures and visuals.
- The included `pbip_validation.json` confirms that all referenced visual fields
  resolve to valid model entities and properties.
- To create a `.pbix`, open the `.pbip` project and use **File → Save As** in
  Power BI Desktop.

## Suggested Portfolio Screenshots

Use 16:9 page view and export at full report size. Recommended pages:

1. Executive Overview
2. Demand History
3. Inventory Health
4. Forecast Accuracy
5. History & Forecast

## Publish to Power BI Service

Publishing to a public or organizational workspace may expose the report.
Review the data and tenant policy first. The included data is synthetic, but the
user should still choose the correct workspace and sharing scope.
