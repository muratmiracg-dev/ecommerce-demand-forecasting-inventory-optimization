import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const projectRoot = path.resolve(process.argv[2] || ".");
const dataDir = path.join(projectRoot, "Data");
const outputDir = path.join(projectRoot, "Excel");
const previewDir = path.join(projectRoot, "Images", "excel-previews");

const C = {
  navy: "#0B132B",
  navy2: "#14213D",
  blue: "#3D8DFF",
  cyan: "#6DCBF4",
  lightBlue: "#EAF5FB",
  light: "#F4F7FB",
  line: "#DCE3ED",
  text: "#172033",
  muted: "#667085",
  white: "#FFFFFF",
  green: "#18A558",
  paleGreen: "#E8F7EE",
  amber: "#F59E0B",
  paleAmber: "#FFF4D6",
  red: "#D64545",
  paleRed: "#FDECEC",
  input: "#FFF2CC",
  inputFont: "#0000FF",
};

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (char === '"') {
      if (quoted && text[i + 1] === '"') {
        field += '"';
        i += 1;
      } else {
        quoted = !quoted;
      }
    } else if (char === "," && !quoted) {
      row.push(field);
      field = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && text[i + 1] === "\n") i += 1;
      row.push(field);
      if (row.some((cell) => cell !== "")) rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }
  if (field !== "" || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

function coerce(value) {
  if (value === "") return null;
  if (value === "True" || value === "TRUE") return true;
  if (value === "False" || value === "FALSE") return false;
  if (/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(value)) return Number(value);
  return value;
}

async function loadCsv(filename) {
  const rows = parseCsv(await fs.readFile(path.join(dataDir, filename), "utf8"));
  return {
    headers: rows[0],
    rows: rows.slice(1).map((row) => row.map(coerce)),
  };
}

function colName(index) {
  let n = index + 1;
  let result = "";
  while (n > 0) {
    const r = (n - 1) % 26;
    result = String.fromCharCode(65 + r) + result;
    n = Math.floor((n - 1) / 26);
  }
  return result;
}

function rangeFor(startRow, startCol, rows, cols) {
  const start = `${colName(startCol)}${startRow}`;
  const end = `${colName(startCol + cols - 1)}${startRow + rows - 1}`;
  return `${start}:${end}`;
}

function titleBand(sheet, title, subtitle, lastCol = "N") {
  sheet.showGridLines = false;
  sheet.getRange(`A1:${lastCol}2`).merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A1:${lastCol}2`).format = {
    fill: C.navy,
    font: { color: C.white, bold: true, size: 20 },
    verticalAlignment: "center",
  };
  sheet.getRange(`A3:${lastCol}3`).merge();
  sheet.getRange("A3").values = [[subtitle]];
  sheet.getRange(`A3:${lastCol}3`).format = {
    fill: C.navy2,
    font: { color: "#D7E3F7", italic: true, size: 10 },
    verticalAlignment: "center",
  };
  sheet.getRange(`A1:${lastCol}3`).format.rowHeight = 25;
}

function card(sheet, labelRange, valueRange, label, formula, numberFormat, accent = C.blue) {
  sheet.getRange(labelRange).merge();
  sheet.getRange(valueRange).merge();
  sheet.getRange(labelRange.split(":")[0]).values = [[label]];
  sheet.getRange(valueRange.split(":")[0]).formulas = [[formula]];
  sheet.getRange(labelRange).format = {
    fill: C.light,
    font: { color: C.muted, bold: true, size: 9 },
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: C.line },
  };
  sheet.getRange(valueRange).format = {
    fill: C.white,
    font: { color: accent, bold: true, size: 20 },
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: C.line },
    numberFormat,
  };
}

function styleDataTable(sheet, range, headerRange, currencyCols = [], percentCols = []) {
  sheet.getRange(range).format = {
    font: { color: C.text, size: 9 },
    borders: { preset: "all", style: "thin", color: C.line },
    verticalAlignment: "center",
  };
  sheet.getRange(headerRange).format = {
    fill: C.navy2,
    font: { color: C.white, bold: true, size: 9 },
    wrapText: true,
    verticalAlignment: "center",
    borders: { preset: "all", style: "thin", color: C.navy2 },
  };
  for (const rangeAddress of currencyCols) {
    sheet.getRange(rangeAddress).format.numberFormat = '₺#,##0;[Red]-₺#,##0';
  }
  for (const rangeAddress of percentCols) {
    sheet.getRange(rangeAddress).format.numberFormat = "0.0%";
  }
}

function setWidths(sheet, widths) {
  for (const [address, width] of Object.entries(widths)) {
    sheet.getRange(address).format.columnWidth = width;
  }
}

const monthly = await loadCsv("monthly_performance.csv");
const category = await loadCsv("category_performance.csv");
const sku = await loadCsv("sku_performance.csv");
const forecastMonthly = await loadCsv("forecast_monthly.csv");
const replenishment = await loadCsv("replenishment_recommendations.csv");
const metrics = await loadCsv("model_comparison.csv");
const scenarios = await loadCsv("scenario_summary.csv");
const products = await loadCsv("dim_product.csv");
const suppliers = await loadCsv("supplier_scorecard.csv");

const metricIndexes = Object.fromEntries(metrics.headers.map((header, index) => [header, index]));
const championRows = metrics.rows
  .filter((row) => row[metricIndexes.ChampionFlag] === true)
  .map((row) => [
    row[metricIndexes.SKU],
    row[metricIndexes.Model],
    row[metricIndexes.MAE],
    row[metricIndexes.WAPE],
    row[metricIndexes.Bias],
    row[metricIndexes.ChampionFlag],
  ]);

const workbook = Workbook.create();
const cover = workbook.worksheets.add("Cover");
const dashboard = workbook.worksheets.add("Executive Dashboard");
const planner = workbook.worksheets.add("Scenario Planner");
const replenishSheet = workbook.worksheets.add("Replenishment");
const accuracySheet = workbook.worksheets.add("Forecast Accuracy");
const monthlySheet = workbook.worksheets.add("Monthly Performance");
const productSheet = workbook.worksheets.add("Product Portfolio");
const forecastSheet = workbook.worksheets.add("Forecast Data");
const supplierSheet = workbook.worksheets.add("Supplier Scorecard");
const scenarioDataSheet = workbook.worksheets.add("Scenario Data");
const dashboardDataSheet = workbook.worksheets.add("Dashboard Data");
const assumptionsSheet = workbook.worksheets.add("Assumptions");
const dictionarySheet = workbook.worksheets.add("Data Dictionary");
const checksSheet = workbook.worksheets.add("Checks");
const sourcesSheet = workbook.worksheets.add("Sources");

// Cover
cover.showGridLines = false;
cover.getRange("A1:N4").merge();
cover.getRange("A1").values = [["E-Commerce Demand Forecasting\n& Inventory Optimization Platform"]];
cover.getRange("A1:N4").format = {
  fill: C.navy,
  font: { color: C.white, bold: true, size: 26 },
  verticalAlignment: "center",
  wrapText: true,
};
cover.getRange("A5:N5").merge();
cover.getRange("A5").values = [["Professional Excel Scenario Planning & KPI Dashboard"]];
cover.getRange("A5:N5").format = {
  fill: C.blue,
  font: { color: C.white, bold: true, size: 12 },
  verticalAlignment: "center",
};
cover.getRange("A7:H12").merge();
cover.getRange("A7").values = [[
  "Purpose\nConvert three years of synthetic fashion e-commerce history into 2026 demand forecasts, SKU-level replenishment priorities, and decision-ready inventory scenarios.",
]];
cover.getRange("A7:H12").format = {
  fill: C.light,
  font: { color: C.text, size: 14 },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: C.line },
};
cover.getRange("J7:N12").merge();
cover.getRange("J7").values = [[
  "Portfolio Scope\n• 60 SKUs\n• 157 historical weeks\n• 52 forecast weeks\n• 3 forecasting models\n• 4 inventory scenarios\n• TRY currency",
]];
cover.getRange("J7:N12").format = {
  fill: C.lightBlue,
  font: { color: C.navy, size: 13, bold: true },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: C.cyan },
};
cover.getRange("A14:N16").merge();
cover.getRange("A14").values = [[
  "Prepared by Murat Miraç Gedik  |  MonacoLuxe-inspired synthetic portfolio data  |  July 2026",
]];
cover.getRange("A14:N16").format = {
  fill: C.white,
  font: { color: C.muted, italic: true, size: 11 },
  verticalAlignment: "center",
};
setWidths(cover, { "A:N": 12 });
cover.getRange("A1:N16").format.rowHeight = 24;

// Monthly data
titleBand(monthlySheet, "Monthly Performance", "Historical performance | January 2023 - December 2025", "M");
monthlySheet.getRange(rangeFor(5, 0, monthly.rows.length + 1, monthly.headers.length)).values = [
  monthly.headers,
  ...monthly.rows,
];
styleDataTable(
  monthlySheet,
  rangeFor(5, 0, monthly.rows.length + 1, monthly.headers.length),
  rangeFor(5, 0, 1, monthly.headers.length),
  ["E6:H41", "I6:I41"],
  ["J6:J41", "N6:N41"],
);
monthlySheet.getRange("A5:M41").format.rowHeight = 18;
setWidths(monthlySheet, {
  "A:A": 12,
  "B:D": 17,
  "E:I": 18,
  "J:J": 16,
  "K:M": 19,
});
monthlySheet.freezePanes.freezeRows(5);
const monthlyChart = monthlySheet.charts.add("line", monthlySheet.getRange("A5:F41"));
monthlyChart.title = "Monthly Revenue and Gross Profit";
monthlyChart.hasLegend = true;
monthlyChart.setPosition("O5", "W23");
monthlyChart.yAxis = { numberFormatCode: '₺0,,"M"' };
monthlyChart.xAxis = { axisType: "textAxis", textStyle: { fontSize: 9 } };

// Forecast data
titleBand(forecastSheet, "2026 Forecast Data", "Monthly category forecast with 80% prediction intervals", "F");
forecastSheet.getRange(rangeFor(5, 0, forecastMonthly.rows.length + 1, forecastMonthly.headers.length)).values = [
  forecastMonthly.headers,
  ...forecastMonthly.rows,
];
styleDataTable(
  forecastSheet,
  rangeFor(5, 0, forecastMonthly.rows.length + 1, forecastMonthly.headers.length),
  rangeFor(5, 0, 1, forecastMonthly.headers.length),
  ["F6:F77"],
);
setWidths(forecastSheet, {
  "A:A": 12,
  "B:B": 18,
  "C:E": 17,
  "F:F": 20,
});
forecastSheet.freezePanes.freezeRows(5);

// Forecast accuracy
titleBand(accuracySheet, "Forecast Accuracy", "Champion model and backtest performance by SKU", "F");
accuracySheet.getRange("A5:F65").values = [
  ["SKU", "Champion Model", "MAE", "WAPE", "Bias", "Champion"],
  ...championRows,
];
styleDataTable(accuracySheet, "A5:F65", "A5:F5", [], ["D6:E65"]);
accuracySheet.getRange("D6:D65").conditionalFormats.add("colorScale", {
  criteria: [
    { type: "lowestValue", color: C.paleGreen },
    { type: "percentile", value: 50, color: C.paleAmber },
    { type: "highestValue", color: C.paleRed },
  ],
});
setWidths(accuracySheet, { "A:A": 13, "B:B": 24, "C:E": 13, "F:F": 12 });
accuracySheet.freezePanes.freezeRows(5);
accuracySheet.getRange("H5:I8").values = [
  ["Model", "Champion SKUs"],
  ["Gradient Boosting", championRows.filter((row) => row[1] === "Gradient Boosting").length],
  ["Seasonal Naive", championRows.filter((row) => row[1] === "Seasonal Naive").length],
  ["8-Week Moving Average", championRows.filter((row) => row[1] === "8-Week Moving Average").length],
];
styleDataTable(accuracySheet, "H5:I8", "H5:I5");
const accuracyChart = accuracySheet.charts.add("bar", accuracySheet.getRange("H5:I8"));
accuracyChart.title = "Champion Model Distribution";
accuracyChart.hasLegend = false;
accuracyChart.setPosition("H10", "N25");

// Replenishment
const replenishColumns = [
  "SKU",
  "ProductName",
  "Category",
  "SupplierName",
  "ChampionModel",
  "ChampionWAPE",
  "TargetServiceLevel",
  "LeadTimeDays",
  "AverageWeeklyForecastUnits",
  "AnnualForecastUnits",
  "CurrentOnHand",
  "OnOrderUnits",
  "InventoryPosition",
  "ProjectedWeeksOfSupply",
  "SafetyStockUnits",
  "ReorderPointUnits",
  "EOQUnits",
  "RecommendedOrderQty",
  "RecommendedInvestmentTRY",
  "ForecastRevenueTRY",
  "Action",
];
const replenishIndexes = Object.fromEntries(
  replenishment.headers.map((header, index) => [header, index]),
);
const replenishRows = replenishment.rows.map((row) =>
  replenishColumns.map((column) => row[replenishIndexes[column]]),
);
titleBand(replenishSheet, "SKU Replenishment Priorities", "Base scenario | recommended order quantities and investment", "U");
replenishSheet.getRange(rangeFor(5, 0, replenishRows.length + 1, replenishColumns.length)).values = [
  replenishColumns,
  ...replenishRows,
];
styleDataTable(
  replenishSheet,
  rangeFor(5, 0, replenishRows.length + 1, replenishColumns.length),
  rangeFor(5, 0, 1, replenishColumns.length),
  ["S6:T65"],
  ["F6:G65"],
);
replenishSheet.getRange("N6:N65").conditionalFormats.add("colorScale", {
  criteria: [
    { type: "lowestValue", color: C.paleRed },
    { type: "percentile", value: 50, color: C.paleAmber },
    { type: "highestValue", color: C.paleGreen },
  ],
});
replenishSheet.getRange("U6:U65").conditionalFormats.add("containsText", {
  text: "ORDER NOW",
  format: { fill: C.paleRed, font: { color: C.red, bold: true } },
});
replenishSheet.getRange("U6:U65").conditionalFormats.add("containsText", {
  text: "MONITOR",
  format: { fill: C.paleAmber, font: { color: "#8A5A00", bold: true } },
});
replenishSheet.getRange("U6:U65").conditionalFormats.add("containsText", {
  text: "HEALTHY",
  format: { fill: C.paleGreen, font: { color: C.green, bold: true } },
});
setWidths(replenishSheet, {
  "A:A": 12,
  "B:B": 24,
  "C:E": 18,
  "F:Q": 15,
  "R:R": 19,
  "S:T": 21,
  "U:U": 18,
});
replenishSheet.freezePanes.freezeRows(5);
replenishSheet.freezePanes.freezeColumns(2);

// Product portfolio
titleBand(productSheet, "Product Portfolio", "Historical economics, fulfillment, forecast accuracy, and replenishment status", "P");
productSheet.getRange(rangeFor(5, 0, sku.rows.length + 1, sku.headers.length)).values = [
  sku.headers,
  ...sku.rows,
];
styleDataTable(
  productSheet,
  rangeFor(5, 0, sku.rows.length + 1, sku.headers.length),
  rangeFor(5, 0, 1, sku.headers.length),
);
const productHeaderMap = Object.fromEntries(sku.headers.map((h, i) => [h, i]));
for (const column of ["NetRevenueTRY", "GrossProfitTRY", "RecommendedInvestmentTRY"]) {
  const c = colName(productHeaderMap[column]);
  productSheet.getRange(`${c}6:${c}65`).format.numberFormat = '₺#,##0';
}
for (const column of ["ChampionWAPE", "ChampionBias", "DemandFulfillmentRate", "GrossMarginPct"]) {
  const c = colName(productHeaderMap[column]);
  productSheet.getRange(`${c}6:${c}65`).format.numberFormat = "0.0%";
}
setWidths(productSheet, {
  "A:A": 12,
  "B:B": 24,
  "C:E": 18,
  "F:P": 17,
});
productSheet.freezePanes.freezeRows(5);
productSheet.freezePanes.freezeColumns(2);

// Supplier scorecard
titleBand(supplierSheet, "Supplier Scorecard", "Purchase order volume, lead time, and delivery reliability", "F");
supplierSheet.getRange(rangeFor(5, 0, suppliers.rows.length + 1, suppliers.headers.length)).values = [
  suppliers.headers,
  ...suppliers.rows,
];
styleDataTable(
  supplierSheet,
  rangeFor(5, 0, suppliers.rows.length + 1, suppliers.headers.length),
  rangeFor(5, 0, 1, suppliers.headers.length),
);
const supplierHeaderMap = Object.fromEntries(suppliers.headers.map((h, i) => [h, i]));
supplierSheet.getRange(
  `${colName(supplierHeaderMap.PurchaseValueTRY)}6:${colName(supplierHeaderMap.PurchaseValueTRY)}13`,
).format.numberFormat = '₺#,##0';
supplierSheet.getRange(
  `${colName(supplierHeaderMap.OnTimeDeliveryRate)}6:${colName(supplierHeaderMap.OnTimeDeliveryRate)}13`,
).format.numberFormat = "0.0%";
setWidths(supplierSheet, { "A:F": 20 });
const supplierChart = supplierSheet.charts.add(
  "bar",
  supplierSheet.getRange("A5:F13"),
);
supplierChart.title = "Supplier Purchase Value";
supplierChart.hasLegend = false;
supplierChart.setPosition("H5", "N22");

// Scenario data
titleBand(scenarioDataSheet, "Scenario Data", "Precalculated inventory scenarios generated by the Python optimization engine", "K");
scenarioDataSheet.getRange(rangeFor(5, 0, scenarios.rows.length + 1, scenarios.headers.length)).values = [
  scenarios.headers,
  ...scenarios.rows,
];
styleDataTable(
  scenarioDataSheet,
  rangeFor(5, 0, scenarios.rows.length + 1, scenarios.headers.length),
  rangeFor(5, 0, 1, scenarios.headers.length),
);
const scenarioHeaderMap = Object.fromEntries(scenarios.headers.map((h, i) => [h, i]));
for (const column of ["ForecastRevenueTRY", "RecommendedInvestmentTRY", "ProjectedGrossMarginTRY"]) {
  const c = colName(scenarioHeaderMap[column]);
  scenarioDataSheet.getRange(`${c}6:${c}9`).format.numberFormat = '₺#,##0';
}
scenarioDataSheet.getRange(
  `${colName(scenarioHeaderMap.InventoryInvestmentToRevenuePct)}6:${colName(scenarioHeaderMap.InventoryInvestmentToRevenuePct)}9`,
).format.numberFormat = "0.0%";
setWidths(scenarioDataSheet, { "A:K": 21 });

// Assumptions
titleBand(assumptionsSheet, "Assumptions & Methodology", "Editable business assumptions and model definitions", "H");
assumptionsSheet.getRange("A5:D10").values = [
  ["Scenario", "Demand Multiplier", "Service Level Delta", "Lead Time Delta (Days)"],
  ["Lean", 0.9, -0.02, 0],
  ["Base", 1.0, 0.0, 0],
  ["Growth", 1.15, 0.01, 0],
  ["Resilience", 1.05, 0.02, 14],
  ["Custom", 1.0, 0.0, 0],
];
styleDataTable(assumptionsSheet, "A5:D10", "A5:D5", [], ["B6:C10"]);
assumptionsSheet.getRange("F5:H11").values = [
  ["Model / Rule", "Definition", "Decision Use"],
  ["Seasonal Naive", "Same ISO week from prior year", "Transparent seasonal baseline"],
  ["8-Week Moving Average", "35% 4-week + 65% 13-week mean", "Stable short-term baseline"],
  ["Gradient Boosting", "Calendar, promotion, lag, and rolling features", "Non-linear demand patterns"],
  ["Champion Selection", "Lowest SKU-level WAPE on last 13 weeks", "Model governance"],
  ["Safety Stock", "z × residual std × sqrt(lead-time weeks)", "Service-level protection"],
  ["EOQ", "sqrt(2 × annual demand × order cost / holding cost)", "Order-size economics"],
];
styleDataTable(assumptionsSheet, "F5:H11", "F5:H5");
assumptionsSheet.getRange("A13:D16").values = [
  ["Global Input", "Value", "Unit", "Usage"],
  ["Annual Holding Cost Rate", 0.24, "% of unit cost", "EOQ"],
  ["Prediction Interval", 0.8, "probability", "Forecast bands"],
  ["Backtest Horizon", 13, "weeks", "Model comparison"],
];
styleDataTable(assumptionsSheet, "A13:D16", "A13:D13", [], ["B14:B15"]);
assumptionsSheet.getRange("B6:D10").format = {
  fill: C.input,
  font: { color: C.inputFont },
};
assumptionsSheet.getRange("B14:B16").format = {
  fill: C.input,
  font: { color: C.inputFont },
};
setWidths(assumptionsSheet, {
  "A:A": 25,
  "B:D": 20,
  "F:F": 24,
  "G:G": 48,
  "H:H": 26,
});

// Dashboard helper data
titleBand(
  dashboardDataSheet,
  "Dashboard Data",
  "Auditable helper ranges used by the Executive Dashboard charts",
  "E",
);
dashboardDataSheet.getRange("A5:B41").values = [
  ["YearMonth", "NetRevenueTRY"],
  ...monthly.rows.map((row) => [row[0], row[4]]),
];
dashboardDataSheet.getRange("D5:E11").values = [
  ["Category", "Historical Revenue"],
  ...category.rows.map((row) => [row[0], row[4]]),
];
styleDataTable(dashboardDataSheet, "A5:B41", "A5:B5", ["B6:B41"]);
styleDataTable(dashboardDataSheet, "D5:E11", "D5:E5", ["E6:E11"]);
setWidths(dashboardDataSheet, { "A:A": 14, "B:B": 22, "D:D": 20, "E:E": 22 });

// Scenario planner
titleBand(planner, "Inventory Scenario Planner", "Select a scenario and evaluate demand, investment, and budget implications", "N");
planner.getRange("A5:D5").merge();
planner.getRange("A5").values = [["Scenario Controls"]];
planner.getRange("A5:D5").format = {
  fill: C.navy2,
  font: { color: C.white, bold: true, size: 11 },
};
planner.getRange("A6:B11").values = [
  ["Selected Scenario", "Base"],
  ["Demand Multiplier", null],
  ["Service Level Delta", null],
  ["Lead Time Delta (Days)", null],
  ["Annual Holding Cost Rate", 0.24],
  ["Inventory Budget Cap (TRY M)", 15],
];
planner.getRange("B6").dataValidation = {
  rule: { type: "list", values: ["Lean", "Base", "Growth", "Resilience"] },
};
planner.getRange("B7").formulas = [[
  '=IF(B6="Lean",0.9,IF(B6="Growth",1.15,IF(B6="Resilience",1.05,1)))',
]];
planner.getRange("B8").formulas = [[
  '=IF(B6="Lean",-0.02,IF(B6="Growth",0.01,IF(B6="Resilience",0.02,0)))',
]];
planner.getRange("B9").formulas = [[
  '=IF(B6="Resilience",14,0)',
]];
styleDataTable(planner, "A6:B11", "A6:B6");
planner.getRange("B6:B11").format = {
  fill: C.input,
  font: { color: C.inputFont, bold: true },
};
planner.getRange("B7:B8").format.numberFormat = "0.0%";
planner.getRange("B10").format.numberFormat = "0.0%";
planner.getRange("B11").format.numberFormat = "0.0";

planner.getRange("A14:D14").merge();
planner.getRange("A14").values = [["Selected Scenario Outputs"]];
planner.getRange("A14:D14").format = {
  fill: C.navy2,
  font: { color: C.white, bold: true, size: 11 },
};
planner.getRange("A15:B22").values = [
  ["Forecast Units", null],
  ["Forecast Revenue (TRY M)", null],
  ["Inventory Investment (TRY M)", null],
  ["Budget Variance (TRY M)", null],
  ["Projected Gross Margin (TRY M)", null],
  ["SKUs to Order", null],
  ["Average Weeks of Supply", null],
  ["Budget Status", null],
];
planner.getRange("B15").formulas = [[
  '=SUMIF(\'Scenario Data\'!$A$6:$A$9,B6,\'Scenario Data\'!$B$6:$B$9)',
]];
planner.getRange("B16").formulas = [[
  '=SUMIF(\'Scenario Data\'!$A$6:$A$9,B6,\'Scenario Data\'!$C$6:$C$9)/1000000',
]];
planner.getRange("B17").formulas = [[
  '=SUMIF(\'Scenario Data\'!$A$6:$A$9,B6,\'Scenario Data\'!$D$6:$D$9)/1000000',
]];
planner.getRange("B18").formulas = [["=B11-B17"]];
planner.getRange("B19").formulas = [[
  '=SUMIF(\'Scenario Data\'!$A$6:$A$9,B6,\'Scenario Data\'!$J$6:$J$9)/1000000',
]];
planner.getRange("B20").formulas = [[
  '=SUMIF(\'Scenario Data\'!$A$6:$A$9,B6,\'Scenario Data\'!$H$6:$H$9)',
]];
planner.getRange("B21").formulas = [[
  '=SUMIF(\'Scenario Data\'!$A$6:$A$9,B6,\'Scenario Data\'!$F$6:$F$9)',
]];
planner.getRange("B22").formulas = [['=IF(B18>=0,"WITHIN BUDGET","OVER BUDGET")']];
styleDataTable(planner, "A15:B22", "A15:B15");
planner.getRange("B16:B19").format.numberFormat = "0.0";
planner.getRange("B21").format.numberFormat = "0.0";
planner.getRange("B22").conditionalFormats.add("containsText", {
  text: "WITHIN",
  format: { fill: C.paleGreen, font: { color: C.green, bold: true } },
});
planner.getRange("B22").conditionalFormats.add("containsText", {
  text: "OVER",
  format: { fill: C.paleRed, font: { color: C.red, bold: true } },
});

planner.getRange("F6:K10").values = [
  ["Scenario", "Forecast Revenue", "Inventory Investment", "Order Units", "SKUs to Order", "Avg WOS"],
  ...scenarios.rows.map((row) => [
    row[scenarioHeaderMap.Scenario],
    row[scenarioHeaderMap.ForecastRevenueTRY],
    row[scenarioHeaderMap.RecommendedInvestmentTRY],
    row[scenarioHeaderMap.RecommendedOrderUnits],
    row[scenarioHeaderMap.SKUsToOrder],
    row[scenarioHeaderMap.AverageWeeksOfSupply],
  ]),
];
styleDataTable(planner, "F6:K10", "F6:K6", ["G7:H10"]);
const scenarioChart = planner.charts.add("bar", planner.getRange("F6:H10"));
scenarioChart.title = "Revenue vs Inventory Investment";
scenarioChart.hasLegend = true;
scenarioChart.setPosition("F13", "N31");
scenarioChart.yAxis = { numberFormatCode: '₺0,,"M"' };
setWidths(planner, {
  "A:A": 27,
  "B:B": 21,
  "C:D": 4,
  "F:F": 15,
  "G:H": 20,
  "I:K": 16,
});

// Executive dashboard
titleBand(
  dashboard,
  "Executive Dashboard",
  "Historical performance, 2026 outlook, forecast accuracy, and replenishment exposure",
  "N",
);
card(
  dashboard,
  "A5:C5",
  "A6:C8",
  "Historical Revenue (TRY M)",
  "=SUM('Monthly Performance'!E6:E41)/1000000",
  "0.0",
);
card(
  dashboard,
  "D5:F5",
  "D6:F8",
  "2026 Forecast Revenue (TRY M)",
  "=SUM('Forecast Data'!F6:F77)/1000000",
  "0.0",
  C.cyan,
);
card(
  dashboard,
  "G5:I5",
  "G6:I8",
  "Average Champion WAPE",
  "=AVERAGE('Forecast Accuracy'!D6:D65)",
  "0.0%",
  C.green,
);
card(
  dashboard,
  "J5:L5",
  "J6:L8",
  "Recommended Investment (TRY M)",
  "=SUM('Replenishment'!S6:S65)/1000000",
  "0.0",
  C.amber,
);
const revenueChart = dashboard.charts.add(
  "line",
  dashboardDataSheet.getRange("A5:B41"),
);
revenueChart.title = "Monthly Net Revenue | 2023-2025";
revenueChart.hasLegend = false;
revenueChart.setPosition("A11", "G28");
revenueChart.yAxis = { numberFormatCode: '₺0,,"M"' };
revenueChart.xAxis = { axisType: "textAxis", textStyle: { fontSize: 8 } };
const categoryChart = dashboard.charts.add(
  "bar",
  dashboardDataSheet.getRange("D5:E11"),
);
categoryChart.title = "Revenue by Category";
categoryChart.hasLegend = false;
categoryChart.setPosition("H11", "N28");
categoryChart.yAxis = { numberFormatCode: '₺0,,"M"' };
dashboard.getRange("A31:N31").merge();
dashboard.getRange("A31").values = [["Executive Decision Summary"]];
dashboard.getRange("A31:N31").format = {
  fill: C.navy2,
  font: { color: C.white, bold: true, size: 11 },
};
dashboard.getRange("A32:N36").merge();
dashboard.getRange("A32").values = [[
  `Base scenario recommends action on ${replenishRows.filter((row) => row[20] === "ORDER NOW").length} SKUs. The selected forecast model averages ${(championRows.reduce((sum, row) => sum + Number(row[3]), 0) / championRows.length * 100).toFixed(1)}% WAPE across the portfolio. Use the Scenario Planner to test growth, lean, and supplier-disruption assumptions against the TRY 15M inventory budget.`,
]];
dashboard.getRange("A32:N36").format = {
  fill: C.lightBlue,
  font: { color: C.navy, size: 12 },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: C.cyan },
};
setWidths(dashboard, { "A:N": 12 });

// Data dictionary
titleBand(dictionarySheet, "Data Dictionary", "Primary entities and business definitions", "H");
dictionarySheet.getRange("A5:H25").values = [
  ["Table", "Field / Metric", "Type", "Definition", "Grain", "Source", "Owner", "Notes"],
  ["dim_product", "SKU", "Text", "Unique stock keeping unit", "Product", "Synthetic generator", "Merchandising", "60 SKUs"],
  ["dim_product", "TargetServiceLevel", "Decimal", "Probability of satisfying demand without stockout", "Product", "Business assumption", "Supply Chain", "93%-98%"],
  ["fact_weekly_sales", "EstimatedDemandUnits", "Number", "Units sold plus estimated lost sales", "Week-SKU-channel", "Synthetic generator", "Commercial", "Uncensored demand proxy"],
  ["fact_weekly_sales", "NetRevenueTRY", "Currency", "Gross sales less discount", "Week-SKU-channel", "Synthetic generator", "Finance", "TRY"],
  ["fact_weekly_sales", "GrossProfitTRY", "Currency", "Net revenue less cost of goods", "Week-SKU-channel", "Synthetic generator", "Finance", "TRY"],
  ["fact_inventory_snapshot", "EndingOnHand", "Number", "Units physically available at week end", "Week-SKU", "Inventory simulation", "Supply Chain", null],
  ["fact_inventory_snapshot", "WeeksOfSupply", "Decimal", "Ending stock divided by expected weekly demand", "Week-SKU", "Inventory simulation", "Supply Chain", null],
  ["forecast_results", "ForecastUnits", "Decimal", "Champion-model point forecast", "Forecast week-SKU", "Python model", "Analytics", "52 weeks"],
  ["forecast_results", "Lower80Units", "Decimal", "Lower bound of 80% prediction interval", "Forecast week-SKU", "Python model", "Analytics", null],
  ["model_comparison", "WAPE", "Percentage", "Sum absolute error divided by sum actual demand", "SKU-model", "Backtest", "Analytics", "Lower is better"],
  ["model_comparison", "Bias", "Percentage", "Net forecast error divided by total actual demand", "SKU-model", "Backtest", "Analytics", "Positive = over-forecast"],
  ["replenishment", "SafetyStockUnits", "Decimal", "Service-level buffer based on residual variability", "SKU", "Optimization", "Supply Chain", null],
  ["replenishment", "ReorderPointUnits", "Decimal", "Lead-time demand plus safety stock", "SKU", "Optimization", "Supply Chain", null],
  ["replenishment", "EOQUnits", "Decimal", "Economic order quantity", "SKU", "Optimization", "Supply Chain", null],
  ["replenishment", "RecommendedOrderQty", "Number", "Pack-rounded order recommendation", "SKU", "Optimization", "Supply Chain", "Respects MOQ"],
  ["scenario_summary", "RecommendedInvestmentTRY", "Currency", "Cost of recommended order quantities", "Scenario", "Optimization", "Finance", "TRY"],
  ["scenario_summary", "SKUsToOrder", "Number", "Count of products requiring immediate order", "Scenario", "Optimization", "Supply Chain", null],
  ["scenario_summary", "AverageWeeksOfSupply", "Decimal", "Average portfolio inventory coverage", "Scenario", "Optimization", "Supply Chain", null],
  ["supplier_scorecard", "OnTimeDeliveryRate", "Percentage", "Share of POs received by expected date plus tolerance", "Supplier", "PO simulation", "Procurement", null],
  ["validation_report", "all_passed", "Boolean", "All automated data and business-rule checks passed", "Project", "Validation", "Analytics", null],
];
styleDataTable(dictionarySheet, "A5:H25", "A5:H5");
dictionarySheet.getRange("A5:H25").format.wrapText = true;
setWidths(dictionarySheet, {
  "A:A": 24,
  "B:B": 27,
  "C:C": 14,
  "D:D": 48,
  "E:E": 20,
  "F:G": 22,
  "H:H": 23,
});

// Checks
titleBand(checksSheet, "Workbook Controls", "Formula-driven integrity checks for the delivered model", "F");
checksSheet.getRange("A5:F12").values = [
  ["Check", "Formula / Rule", "Result", "Expected", "Status", "Owner"],
  ["Product count", "COUNTA Product Portfolio SKU", null, 60, null, "Analytics"],
  ["Forecast month-category rows", "COUNTA Forecast Data", null, 72, null, "Analytics"],
  ["Replenishment SKU count", "COUNTA Replenishment SKU", null, 60, null, "Supply Chain"],
  ["Champion SKU count", "COUNTA Forecast Accuracy SKU", null, 60, null, "Analytics"],
  ["Scenario count", "COUNTA Scenario Data", null, 4, null, "Finance"],
  ["Negative order quantities", "COUNTIF RecommendedOrderQty < 0", null, 0, null, "Supply Chain"],
  ["Average WAPE threshold", "Average champion WAPE <= 25%", null, 0.25, null, "Analytics"],
];
checksSheet.getRange("C6").formulas = [["=COUNTA('Product Portfolio'!A6:A65)"]];
checksSheet.getRange("C7").formulas = [["=COUNTA('Forecast Data'!A6:A77)"]];
checksSheet.getRange("C8").formulas = [["=COUNTA('Replenishment'!A6:A65)"]];
checksSheet.getRange("C9").formulas = [["=COUNTA('Forecast Accuracy'!A6:A65)"]];
checksSheet.getRange("C10").formulas = [["=COUNTA('Scenario Data'!A6:A9)"]];
checksSheet.getRange("C11").formulas = [["=COUNTIF('Replenishment'!R6:R65,\"<0\")"]];
checksSheet.getRange("C12").formulas = [["=AVERAGE('Forecast Accuracy'!D6:D65)"]];
checksSheet.getRange("E6").formulas = [['=IF(C6=D6,"PASS","FAIL")']];
checksSheet.getRange("E6:E10").fillDown();
checksSheet.getRange("E11").formulas = [['=IF(C11=D11,"PASS","FAIL")']];
checksSheet.getRange("E12").formulas = [['=IF(C12<=D12,"PASS","FAIL")']];
styleDataTable(checksSheet, "A5:F12", "A5:F5");
checksSheet.getRange("C12:D12").format.numberFormat = "0.0%";
checksSheet.getRange("E6:E12").conditionalFormats.add("containsText", {
  text: "PASS",
  format: { fill: C.paleGreen, font: { color: C.green, bold: true } },
});
checksSheet.getRange("E6:E12").conditionalFormats.add("containsText", {
  text: "FAIL",
  format: { fill: C.paleRed, font: { color: C.red, bold: true } },
});
setWidths(checksSheet, {
  "A:A": 27,
  "B:B": 42,
  "C:E": 16,
  "F:F": 20,
});

// Sources
titleBand(sourcesSheet, "Sources & Data Notice", "Portfolio disclosure and file lineage", "H");
sourcesSheet.getRange("A5:H14").values = [
  ["Item", "Location / Reference", "Purpose", "Data Type", "Period", "Currency", "Disclosure", "Refresh"],
  ["Synthetic historical data", "Data/fact_weekly_sales.csv", "Demand and commercial history", "Generated", "2023-2025", "TRY", "Not real customer or company data", "Pipeline run"],
  ["Inventory snapshots", "Data/fact_inventory_snapshot.csv", "Stock health and stockouts", "Generated", "2023-2025", "TRY", "Simulation output", "Pipeline run"],
  ["Forecast output", "Data/forecast_results.csv", "2026 weekly demand forecast", "Model output", "2026", "TRY", "Champion model per SKU", "Pipeline run"],
  ["Model comparison", "Data/model_comparison.csv", "Backtest governance", "Model output", "Last 13 weeks", null, "WAPE/MAE/RMSE/Bias", "Pipeline run"],
  ["Replenishment", "Data/replenishment_recommendations.csv", "SKU order decisions", "Optimization output", "2026 planning", "TRY", "MOQ and case-pack constraints", "Pipeline run"],
  ["Scenario summary", "Data/scenario_summary.csv", "Budget planning", "Optimization output", "2026 planning", "TRY", "Lean/Base/Growth/Resilience", "Pipeline run"],
  ["SQLite database", "SQL/ecommerce_demand_inventory.db", "Relational analytics layer", "Database", "2023-2026", "TRY", "Generated from CSV sources", "Pipeline run"],
  ["Project methodology", "docs/methodology.md", "Definitions and limitations", "Documentation", null, null, "Read before business use", "Versioned"],
  ["Author", "Murat Miraç Gedik", "Portfolio attribution", "Metadata", "July 2026", null, "MonacoLuxe-inspired synthetic project", "Versioned"],
];
styleDataTable(sourcesSheet, "A5:H14", "A5:H5");
sourcesSheet.getRange("A5:H14").format.wrapText = true;
setWidths(sourcesSheet, {
  "A:A": 26,
  "B:B": 40,
  "C:C": 34,
  "D:H": 22,
});

for (const sheet of [
  cover,
  dashboard,
  planner,
  replenishSheet,
  accuracySheet,
  monthlySheet,
  productSheet,
  forecastSheet,
  supplierSheet,
  scenarioDataSheet,
  dashboardDataSheet,
  assumptionsSheet,
  dictionarySheet,
  checksSheet,
  sourcesSheet,
]) {
  sheet.getUsedRange()?.format?.autofitRows?.();
}

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
const outputPath = path.join(outputDir, "Ecommerce_Demand_Inventory_Scenario_Planner.xlsx");
await xlsx.save(outputPath);

const sheetsToRender = [
  "Cover",
  "Executive Dashboard",
  "Scenario Planner",
  "Replenishment",
  "Forecast Accuracy",
  "Monthly Performance",
  "Product Portfolio",
  "Forecast Data",
  "Supplier Scorecard",
  "Scenario Data",
  "Dashboard Data",
  "Assumptions",
  "Data Dictionary",
  "Checks",
  "Sources",
];

for (const sheetName of sheetsToRender) {
  const preview = await workbook.render({
    sheetName,
    autoCrop: "all",
    scale: sheetName === "Executive Dashboard" || sheetName === "Scenario Planner" ? 1.35 : 0.8,
    format: "png",
  });
  const safeName = sheetName.toLowerCase().replaceAll(" ", "-");
  await fs.writeFile(
    path.join(previewDir, `${safeName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const summary = await workbook.inspect({
  kind: "workbook,sheet,formula",
  maxChars: 12000,
  tableMaxRows: 8,
  tableMaxCols: 8,
  options: { maxResults: 120 },
});
await fs.writeFile(
  path.join(outputDir, "workbook_inspection.json"),
  JSON.stringify(summary, null, 2),
  "utf8",
);

console.log(outputPath);
