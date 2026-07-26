import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const projectRoot = path.resolve(process.argv[2] || ".");
const dataDir = path.join(projectRoot, "Data");
const outputDir = path.join(projectRoot, "Presentation");

const C = {
  navy: "#0B132B",
  navy2: "#14213D",
  blue: "#3D8DFF",
  cyan: "#6DCBF4",
  paleBlue: "#EAF5FB",
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
  purple: "#7C3AED",
  palePurple: "#F1ECFF",
};

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (char === '"') {
      if (quoted && text[index + 1] === '"') {
        field += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (char === "," && !quoted) {
      row.push(field);
      field = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && text[index + 1] === "\n") index += 1;
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
  const headers = rows[0];
  return rows.slice(1).map((row) =>
    Object.fromEntries(headers.map((header, index) => [header, coerce(row[index])])),
  );
}

const monthly = await loadCsv("monthly_performance.csv");
const category = await loadCsv("category_performance.csv");
const forecastMonthlyRaw = await loadCsv("forecast_monthly.csv");
const metrics = await loadCsv("model_comparison.csv");
const replenishment = await loadCsv("replenishment_recommendations.csv");
const suppliers = await loadCsv("supplier_scorecard.csv");
const scenarios = await loadCsv("scenario_summary.csv");

const champions = metrics.filter((row) => row.ChampionFlag === true);
const modelNames = [...new Set(metrics.map((row) => row.Model))];
const modelSummary = modelNames
  .map((model) => {
    const rows = metrics.filter((row) => row.Model === model);
    return {
      model,
      wape: rows.reduce((sum, row) => sum + row.WAPE, 0) / rows.length,
      winners: champions.filter((row) => row.Model === model).length,
    };
  })
  .sort((a, b) => a.wape - b.wape);

const forecastByMonth = [...new Set(forecastMonthlyRaw.map((row) => row.YearMonth))]
  .sort()
  .map((month) => {
    const rows = forecastMonthlyRaw.filter((row) => row.YearMonth === month);
    return {
      month,
      units: rows.reduce((sum, row) => sum + row.ForecastUnits, 0),
      lower: rows.reduce((sum, row) => sum + row.Lower80Units, 0),
      upper: rows.reduce((sum, row) => sum + row.Upper80Units, 0),
      revenue: rows.reduce((sum, row) => sum + row.ForecastRevenueTRY, 0),
    };
  });

const categoryWos = [...new Set(replenishment.map((row) => row.Category))]
  .map((name) => {
    const rows = replenishment.filter((row) => row.Category === name);
    return {
      category: name,
      wos: rows.reduce((sum, row) => sum + row.ProjectedWeeksOfSupply, 0) / rows.length,
    };
  })
  .sort((a, b) => a.wos - b.wos);

const topOrders = replenishment
  .filter((row) => row.Action === "ORDER NOW")
  .sort((a, b) => b.RecommendedInvestmentTRY - a.RecommendedInvestmentTRY)
  .slice(0, 8);

const historicalRevenue = monthly.reduce((sum, row) => sum + row.NetRevenueTRY, 0);
const totalDemand = monthly.reduce((sum, row) => sum + row.EstimatedDemandUnits, 0);
const totalSold = monthly.reduce((sum, row) => sum + row.UnitsSold, 0);
const lostSales = monthly.reduce((sum, row) => sum + row.LostSalesUnits, 0);
const averageChampionWape =
  champions.reduce((sum, row) => sum + row.WAPE, 0) / champions.length;
const baseScenario = scenarios.find((row) => row.Scenario === "Base");
const portfolioMargin =
  category.reduce((sum, row) => sum + row.GrossProfitTRY, 0)
  / category.reduce((sum, row) => sum + row.NetRevenueTRY, 0);

const TR_CATEGORY = {
  Dresses: "Elbiseler",
  Knitwear: "Triko",
  Outerwear: "Dış Giyim",
  Tops: "Üst Giyim",
  Bottoms: "Alt Giyim",
  Accessories: "Aksesuarlar",
};

const TR_MODEL = {
  "Gradient Boosting": "Gradient Boosting",
  "Seasonal Naive": "Mevsimsel Naif",
  "8-Week Moving Average": "8 Haftalık Hareketli Ort.",
};

const TR_SCENARIO = {
  Lean: "Yalın",
  Base: "Baz",
  Growth: "Büyüme",
  Resilience: "Dayanıklılık",
};

const COPY = {
  en: {
    eyebrow: "PROFESSIONAL PORTFOLIO PROJECT",
    project: "E-Commerce Demand Forecasting\n& Inventory Optimization Platform",
    subtitle: "Statistical forecasting, machine learning, SQL, Power BI, and inventory decision science",
    author: "Murat Miraç Gedik  |  July 2026",
    dataNotice: "MonacoLuxe-inspired synthetic portfolio data | TRY | 2023-2026",
    slides: [
      ["Executive Summary", "The decision case in four numbers"],
      ["Business Problem", "Why retrospective reporting is not enough"],
      ["Project Objectives", "What the analytical platform must deliver"],
      ["Data Landscape", "Three years of demand, commercial, inventory, promotion, and supplier signals"],
      ["End-to-End Analytics Architecture", "A reproducible path from source data to management decisions"],
      ["Relational Data Model", "A calendar-centered semantic layer for time-aware analysis"],
      ["Historical Performance", "Revenue scale, category mix, and demand fulfillment"],
      ["Demand Seasonality", "How promotions and seasonal patterns shape volume"],
      ["Forecasting Approach", "Three models, one governed champion per SKU"],
      ["Model Performance", "Backtest evidence for model selection"],
      ["2026 Demand Forecast", "A planning baseline with explicit uncertainty"],
      ["Inventory Optimization Logic", "Translating forecast uncertainty into purchase decisions"],
      ["Inventory Health", "Coverage, stock exposure, and action status"],
      ["Replenishment Plan", "Immediate purchase priorities under the base scenario"],
      ["Supplier Performance", "Lead-time reliability and purchasing exposure"],
      ["Scenario Analysis", "Capital and service trade-offs across four planning cases"],
      ["BI Delivery Layer", "Decision-ready outputs across Power BI, Excel, SQL, PDF, and PowerPoint"],
      ["Business Recommendations", "A 90-day path to operational adoption"],
    ],
    closeTitle: "From reporting to forward-looking decisions",
    closeBody: "A complete portfolio project connecting statistical reasoning, machine learning, inventory mathematics, business intelligence, and executive communication.",
    thankYou: "Thank you",
  },
  tr: {
    eyebrow: "PROFESYONEL PORTFÖY PROJESİ",
    project: "E-Ticaret Talep Tahmini\nve Stok Optimizasyonu Platformu",
    subtitle: "İstatistiksel tahminleme, makine öğrenmesi, SQL, Power BI ve stok karar bilimi",
    author: "Murat Miraç Gedik  |  Temmuz 2026",
    dataNotice: "MonacoLuxe ilhamlı sentetik portföy verisi | TRY | 2023-2026",
    slides: [
      ["Yönetici Özeti", "Karar senaryosunu özetleyen dört temel gösterge"],
      ["İş Problemi", "Geçmişe dönük raporlamanın neden yeterli olmadığı"],
      ["Proje Hedefleri", "Analitik platformun sunması gereken çıktılar"],
      ["Veri Kapsamı", "Üç yıllık talep, ticari performans, stok, kampanya ve tedarikçi sinyalleri"],
      ["Uçtan Uca Analitik Mimari", "Kaynak veriden yönetim kararına tekrarlanabilir akış"],
      ["İlişkisel Veri Modeli", "Zaman zekâsını destekleyen takvim merkezli semantik katman"],
      ["Tarihsel Performans", "Ciro ölçeği, kategori karması ve talep karşılama"],
      ["Talep Mevsimselliği", "Kampanya ve sezon etkilerinin satış hacmine yansıması"],
      ["Tahminleme Yaklaşımı", "Üç model, her SKU için yönetişimli tek şampiyon"],
      ["Model Performansı", "Model seçimini destekleyen geri test kanıtları"],
      ["2026 Talep Tahmini", "Belirsizliği görünür kılan planlama baz çizgisi"],
      ["Stok Optimizasyonu Mantığı", "Tahmin belirsizliğini satın alma kararına dönüştürme"],
      ["Stok Sağlığı", "Kapsama, stok riski ve aksiyon durumu"],
      ["Yeniden Sipariş Planı", "Baz senaryodaki öncelikli satın alma ihtiyaçları"],
      ["Tedarikçi Performansı", "Teslimat güvenilirliği ve satın alma maruziyeti"],
      ["Senaryo Analizi", "Dört planlama vakasında sermaye ve hizmet dengesi"],
      ["BI Teslimat Katmanı", "Power BI, Excel, SQL, PDF ve PowerPoint üzerinden karar desteği"],
      ["İş Önerileri", "Operasyonel kullanıma geçiş için 90 günlük yol haritası"],
    ],
    closeTitle: "Raporlamadan ileriye dönük kararlara",
    closeBody: "İstatistiksel düşünme, makine öğrenmesi, stok matematiği, iş zekâsı ve yönetici iletişimini tek sistemde birleştiren eksiksiz bir portföy projesi.",
    thankYou: "Teşekkürler",
  },
};

function fmtM(value, lang) {
  return `${lang === "tr" ? "₺" : "TRY "}${(value / 1_000_000).toFixed(1)}M`;
}

function fmtPct(value) {
  return `${(value * 100).toFixed(1)}%`;
}

function addText(slide, text, position, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name: options.name,
    position,
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    fontSize: options.fontSize ?? 18,
    bold: options.bold ?? false,
    color: options.color ?? C.text,
    fontFamily: "Arial",
  };
  shape.text.alignment = options.align ?? "left";
  shape.text.verticalAlignment = options.vertical ?? "top";
  return shape;
}

function addPanel(slide, position, options = {}) {
  return slide.shapes.add({
    geometry: "roundRect",
    name: options.name,
    position,
    fill: options.fill ?? C.white,
    line: {
      style: "solid",
      fill: options.line ?? C.line,
      width: options.lineWidth ?? 1,
    },
    borderRadius: "rounded-xl",
    shadow: options.shadow ? "shadow-sm" : undefined,
  });
}

function addHeader(slide, title, subtitle, pageNumber) {
  slide.background.fill = C.white;
  addText(slide, "E-COMMERCE DEMAND & INVENTORY", { left: 42, top: 26, width: 420, height: 22 }, {
    fontSize: 12,
    bold: true,
    color: C.blue,
    name: "eyebrow",
  });
  addText(slide, title, { left: 42, top: 55, width: 820, height: 50 }, {
    fontSize: 34,
    bold: true,
    color: C.navy,
    name: "title",
  });
  addText(slide, subtitle, { left: 870, top: 62, width: 365, height: 40 }, {
    fontSize: 13,
    color: C.muted,
    align: "right",
    name: "subtitle",
  });
  slide.shapes.add({
    geometry: "rect",
    position: { left: 42, top: 112, width: 1196, height: 3 },
    fill: C.blue,
    line: { style: "solid", fill: C.blue, width: 0 },
  });
  addText(slide, String(pageNumber).padStart(2, "0"), { left: 1184, top: 676, width: 54, height: 20 }, {
    fontSize: 11,
    bold: true,
    color: C.muted,
    align: "right",
  });
}

function addFooter(slide, text) {
  addText(slide, text, { left: 42, top: 676, width: 620, height: 18 }, {
    fontSize: 9,
    color: C.muted,
  });
}

function addNotes(slide, sources, presenterNote = "") {
  const body = [
    presenterNote,
    "[Sources]",
    ...sources.map((source) => `- ${source}`),
    "[/Sources]",
  ].filter(Boolean).join("\n");
  slide.speakerNotes.textFrame.setText(body);
  slide.speakerNotes.setVisible(true);
}

function metricCard(slide, x, y, w, label, value, note, accent = C.blue) {
  addPanel(slide, { left: x, top: y, width: w, height: 145 }, { shadow: false });
  slide.shapes.add({
    geometry: "roundRect",
    position: { left: x, top: y, width: w, height: 8 },
    fill: accent,
    line: { style: "solid", fill: accent, width: 0 },
    borderRadius: "rounded-xl",
  });
  addText(slide, label.toUpperCase(), { left: x + 20, top: y + 24, width: w - 40, height: 24 }, {
    fontSize: 12,
    bold: true,
    color: C.muted,
  });
  addText(slide, value, { left: x + 20, top: y + 56, width: w - 40, height: 44 }, {
    fontSize: 28,
    bold: true,
    color: accent,
  });
  addText(slide, note, { left: x + 20, top: y + 110, width: w - 40, height: 22 }, {
    fontSize: 11,
    color: C.muted,
  });
}

function bulletList(slide, items, x, y, w, options = {}) {
  items.forEach((item, index) => {
    const top = y + index * (options.rowHeight ?? 56);
    slide.shapes.add({
      geometry: "ellipse",
      position: { left: x, top: top + 5, width: 12, height: 12 },
      fill: options.accent ?? C.blue,
      line: { style: "solid", fill: options.accent ?? C.blue, width: 0 },
    });
    addText(slide, item, { left: x + 24, top, width: w - 24, height: options.rowHeight ?? 50 }, {
      fontSize: options.fontSize ?? 18,
      color: options.color ?? C.text,
    });
  });
}

function addSectionLabel(slide, text, x, y, w) {
  addText(slide, text, { left: x, top: y, width: w, height: 26 }, {
    fontSize: 15,
    bold: true,
    color: C.navy,
  });
  slide.shapes.add({
    geometry: "rect",
    position: { left: x, top: y + 32, width: w, height: 1 },
    fill: C.line,
    line: { style: "solid", fill: C.line, width: 0 },
  });
}

function addLineChart(slide, position, categories, series, yMax, yFormat) {
  return slide.charts.add("line", {
    position,
    categories,
    series: series.map((item) => ({
      name: item.name,
      categories,
      values: item.values,
      line: { style: "solid", width: 3, fill: item.color },
      marker: { symbol: "circle", size: 4 },
    })),
    hasLegend: true,
    legend: { position: "bottom", overlay: false },
    chartFill: C.white,
    chartLine: { style: "solid", width: 0, fill: C.white },
    plotAreaFill: { type: "none" },
    plotAreaLine: { style: "solid", width: 0, fill: C.white },
    xAxis: {
      visible: true,
      line: { style: "solid", width: 1, fill: C.line },
      textStyle: { typeface: "Arial", fontSize: "11px", color: C.muted },
    },
    yAxis: {
      visible: true,
      min: 0,
      max: yMax,
      numberFormatCode: yFormat,
      majorGridlines: { style: "solid", width: 1, fill: C.line },
      line: { style: "solid", width: 0, fill: C.white },
      textStyle: { typeface: "Arial", fontSize: "11px", color: C.muted },
    },
    lineOptions: { grouping: "standard" },
  });
}

function addBarChart(slide, position, categories, series, options = {}) {
  return slide.charts.add("bar", {
    position,
    categories,
    series: series.map((item) => ({
      name: item.name,
      categories,
      values: item.values,
      fill: item.color,
    })),
    hasLegend: options.hasLegend ?? series.length > 1,
    legend: { position: "bottom", overlay: false },
    dataLabels: { showValue: options.showValue ?? true, position: "outEnd" },
    chartFill: C.white,
    chartLine: { style: "solid", width: 0, fill: C.white },
    plotAreaFill: { type: "none" },
    plotAreaLine: { style: "solid", width: 0, fill: C.white },
    xAxis: {
      visible: true,
      line: { style: "solid", width: 1, fill: C.line },
      textStyle: { typeface: "Arial", fontSize: "11px", color: C.muted },
    },
    yAxis: {
      visible: true,
      min: 0,
      max: options.yMax,
      numberFormatCode: options.yFormat,
      majorGridlines: { style: "solid", width: 1, fill: C.line },
      line: { style: "solid", width: 0, fill: C.white },
      textStyle: { typeface: "Arial", fontSize: "11px", color: C.muted },
    },
    barOptions: {
      direction: options.horizontal ? "bar" : "column",
      grouping: "clustered",
      gapWidth: 90,
    },
  });
}

function simpleTable(slide, x, y, widths, headers, rows, options = {}) {
  const rowHeight = options.rowHeight ?? 34;
  const totalWidth = widths.reduce((sum, width) => sum + width, 0);
  slide.shapes.add({
    geometry: "rect",
    position: { left: x, top: y, width: totalWidth, height: rowHeight },
    fill: C.navy2,
    line: { style: "solid", fill: C.navy2, width: 0 },
  });
  let left = x;
  headers.forEach((header, index) => {
    addText(slide, header, { left: left + 8, top: y + 7, width: widths[index] - 16, height: rowHeight - 12 }, {
      fontSize: options.headerSize ?? 12,
      bold: true,
      color: C.white,
    });
    left += widths[index];
  });
  rows.forEach((row, rowIndex) => {
    const top = y + (rowIndex + 1) * rowHeight;
    slide.shapes.add({
      geometry: "rect",
      position: { left: x, top, width: totalWidth, height: rowHeight },
      fill: rowIndex % 2 === 0 ? C.white : C.light,
      line: { style: "solid", fill: C.line, width: 0.5 },
    });
    let cellLeft = x;
    row.forEach((value, index) => {
      addText(slide, String(value), { left: cellLeft + 8, top: top + 7, width: widths[index] - 16, height: rowHeight - 12 }, {
        fontSize: options.fontSize ?? 12,
        color: C.text,
      });
      cellLeft += widths[index];
    });
  });
}

function addInsightBox(slide, x, y, w, h, title, body, accent = C.blue, fill = C.paleBlue) {
  addPanel(slide, { left: x, top: y, width: w, height: h }, { fill, line: accent });
  slide.shapes.add({
    geometry: "rect",
    position: { left: x, top: y, width: 6, height: h },
    fill: accent,
    line: { style: "solid", fill: accent, width: 0 },
  });
  addText(slide, title, { left: x + 20, top: y + 18, width: w - 38, height: 28 }, {
    fontSize: 16,
    bold: true,
    color: accent,
  });
  addText(slide, body, { left: x + 20, top: y + 52, width: w - 38, height: h - 66 }, {
    fontSize: 14,
    color: C.text,
  });
}

function localCategory(name, lang) {
  return lang === "tr" ? TR_CATEGORY[name] : name;
}

function localModel(name, lang) {
  return lang === "tr" ? TR_MODEL[name] : name;
}

function localScenario(name, lang) {
  return lang === "tr" ? TR_SCENARIO[name] : name;
}

function slideSources(...files) {
  return files.map((file) => `Internal synthetic project source: ${file}`);
}

function createDeck(lang) {
  const copy = COPY[lang];
  const presentation = Presentation.create({
    slideSize: { width: 1280, height: 720 },
  });

  // 1. Cover
  {
    const slide = presentation.slides.add();
    slide.background.fill = C.navy;
    addText(slide, copy.eyebrow, { left: 54, top: 44, width: 520, height: 28 }, {
      fontSize: 13,
      bold: true,
      color: C.cyan,
    });
    addText(slide, copy.project, { left: 54, top: 156, width: 820, height: 210 }, {
      fontSize: 52,
      bold: true,
      color: C.white,
    });
    addText(slide, copy.subtitle, { left: 54, top: 400, width: 760, height: 70 }, {
      fontSize: 20,
      color: "#D7E3F7",
    });
    slide.shapes.add({
      geometry: "rect",
      position: { left: 54, top: 500, width: 180, height: 5 },
      fill: C.blue,
      line: { style: "solid", fill: C.blue, width: 0 },
    });
    addText(slide, copy.author, { left: 54, top: 540, width: 520, height: 30 }, {
      fontSize: 15,
      color: C.white,
    });
    addText(slide, copy.dataNotice, { left: 54, top: 655, width: 620, height: 22 }, {
      fontSize: 10,
      color: "#B9C7DB",
    });
    addPanel(slide, { left: 930, top: 154, width: 260, height: 360 }, { fill: C.navy2, line: "#29415F" });
    const scope = lang === "tr"
      ? [["60", "SKU"], ["157", "tarihsel hafta"], ["52", "tahmin haftası"], ["4", "stok senaryosu"]]
      : [["60", "SKUs"], ["157", "historical weeks"], ["52", "forecast weeks"], ["4", "inventory scenarios"]];
    scope.forEach((item, index) => {
      addText(slide, item[0], { left: 960, top: 188 + index * 78, width: 90, height: 38 }, {
        fontSize: 28,
        bold: true,
        color: index % 2 === 0 ? C.cyan : C.blue,
      });
      addText(slide, item[1], { left: 960, top: 226 + index * 78, width: 190, height: 26 }, {
        fontSize: 13,
        color: "#D7E3F7",
      });
    });
    addNotes(slide, slideSources("Data/dim_product.csv", "Data/dim_calendar.csv"));
  }

  // 2. Executive Summary
  {
    const [title, subtitle] = copy.slides[0];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 2);
    metricCard(slide, 42, 148, 284, lang === "tr" ? "Tarihsel Ciro" : "Historical Revenue", fmtM(historicalRevenue, lang), "2023-2025", C.blue);
    metricCard(slide, 342, 148, 284, lang === "tr" ? "2026 Tahmini" : "2026 Forecast", fmtM(baseScenario.ForecastRevenueTRY, lang), lang === "tr" ? "Baz senaryo" : "Base scenario", C.cyan);
    metricCard(slide, 642, 148, 284, lang === "tr" ? "Şampiyon WAPE" : "Champion WAPE", fmtPct(averageChampionWape), lang === "tr" ? "60 SKU geri testi" : "60 SKU backtest", C.green);
    metricCard(slide, 942, 148, 296, lang === "tr" ? "Stok Yatırımı" : "Inventory Investment", fmtM(baseScenario.RecommendedInvestmentTRY, lang), `${baseScenario.SKUsToOrder} ${lang === "tr" ? "SKU sipariş" : "SKUs to order"}`, C.amber);
    addInsightBox(
      slide,
      42,
      332,
      1196,
      270,
      lang === "tr" ? "Yönetim kararı" : "Management decision",
      lang === "tr"
        ? `Baz plan, 2026 için ${fmtM(baseScenario.ForecastRevenueTRY, lang)} ciro öngörürken ${fmtM(baseScenario.RecommendedInvestmentTRY, lang)} stok yatırımı gerektiriyor. Portföyde ${baseScenario.SKUsToOrder} SKU için hemen sipariş aksiyonu bulunuyor. Tahmin yönetişimi, her SKU için en düşük WAPE değerine sahip modeli seçiyor.`
        : `The base plan forecasts ${fmtM(baseScenario.ForecastRevenueTRY, lang)} of 2026 revenue and requires ${fmtM(baseScenario.RecommendedInvestmentTRY, lang)} of inventory investment. ${baseScenario.SKUsToOrder} SKUs require immediate ordering. Forecast governance selects the lowest-WAPE model for every SKU.`,
      C.blue,
      C.paleBlue,
    );
    addFooter(slide, copy.dataNotice);
    addNotes(slide, slideSources("Data/monthly_performance.csv", "Data/model_comparison.csv", "Data/scenario_summary.csv"));
  }

  // 3. Business Problem
  {
    const [title, subtitle] = copy.slides[1];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 3);
    const items = lang === "tr"
      ? [
          ["01", "Talep belirsizliği", "Moda talebi sezon, kampanya ve ürün yaşam döngüsü nedeniyle hızlı değişir."],
          ["02", "Stok maliyeti", "Fazla stok işletme sermayesini kilitler; eksik stok satış kaybına yol açar."],
          ["03", "Karar boşluğu", "Geçmiş KPI’ları gelecekte ne kadar ve ne zaman sipariş verilmesi gerektiğini söylemez."],
        ]
      : [
          ["01", "Demand uncertainty", "Fashion demand shifts with seasonality, campaigns, and product lifecycle."],
          ["02", "Inventory cost", "Excess stock locks working capital; insufficient stock creates lost sales."],
          ["03", "Decision gap", "Historical KPIs do not answer how much to order or when to order it."],
        ];
    items.forEach((item, index) => {
      const x = 42 + index * 400;
      addPanel(slide, { left: x, top: 160, width: 374, height: 430 }, { fill: C.light, line: C.line });
      addText(slide, item[0], { left: x + 24, top: 188, width: 90, height: 54 }, {
        fontSize: 34,
        bold: true,
        color: [C.blue, C.amber, C.red][index],
      });
      addText(slide, item[1], { left: x + 24, top: 270, width: 320, height: 60 }, {
        fontSize: 23,
        bold: true,
        color: C.navy,
      });
      addText(slide, item[2], { left: x + 24, top: 352, width: 320, height: 150 }, {
        fontSize: 17,
        color: C.text,
      });
    });
    addFooter(slide, copy.dataNotice);
    addNotes(slide, slideSources("docs/methodology.md"));
  }

  // 4. Objectives
  {
    const [title, subtitle] = copy.slides[2];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 4);
    const objectives = lang === "tr"
      ? [
          ["Talebi tahmin et", "Her SKU için 52 haftalık baz tahmin ve %80 tahmin aralığı üret."],
          ["Modeli yönet", "Geri testte WAPE, MAE, RMSE ve sapma ile şampiyon modeli seç."],
          ["Stoku optimize et", "Güvenlik stoğu, yeniden sipariş noktası, EOQ, MOQ ve koli katını birleştir."],
          ["Kararı dağıt", "Power BI, Excel, SQL, PDF ve PowerPoint üzerinden yöneticiye ulaştır."],
        ]
      : [
          ["Forecast demand", "Produce a 52-week baseline and 80% prediction interval for every SKU."],
          ["Govern models", "Select the champion using WAPE, MAE, RMSE, and bias on a holdout period."],
          ["Optimize inventory", "Combine safety stock, reorder point, EOQ, MOQ, and case-pack constraints."],
          ["Deliver decisions", "Distribute insights through Power BI, Excel, SQL, PDF, and PowerPoint."],
        ];
    objectives.forEach((item, index) => {
      const x = 42 + (index % 2) * 610;
      const y = 154 + Math.floor(index / 2) * 238;
      addPanel(slide, { left: x, top: y, width: 586, height: 210 }, { fill: C.white, line: C.line, shadow: true });
      addText(slide, `0${index + 1}`, { left: x + 24, top: y + 24, width: 58, height: 40 }, {
        fontSize: 24,
        bold: true,
        color: [C.blue, C.cyan, C.amber, C.green][index],
      });
      addText(slide, item[0], { left: x + 98, top: y + 24, width: 430, height: 40 }, {
        fontSize: 22,
        bold: true,
        color: C.navy,
      });
      addText(slide, item[1], { left: x + 98, top: y + 82, width: 430, height: 90 }, {
        fontSize: 16,
        color: C.text,
      });
    });
    addFooter(slide, copy.dataNotice);
    addNotes(slide, slideSources("README.md", "docs/methodology.md"));
  }

  // 5. Data Landscape
  {
    const [title, subtitle] = copy.slides[3];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 5);
    const rows = lang === "tr"
      ? [
          ["Haftalık satış", "Hafta-SKU-kanal", "28.208", "Talep, ciro, kâr, indirim, satış kaybı"],
          ["Stok görünümü", "Hafta-SKU", "9.420", "Eldeki stok, yoldaki stok, WOS, stok tükenmesi"],
          ["Satın alma", "Sipariş-SKU", "1.208", "Miktar, maliyet, termin, zamanında teslimat"],
          ["Tahmin sonucu", "Tahmin haftası-SKU", "3.120", "Tahmin, aralık, model, tahmini ciro"],
          ["Stok senaryosu", "Senaryo-SKU", "240", "Güvenlik stoğu, ROP, EOQ, yatırım, aksiyon"],
        ]
      : [
          ["Weekly sales", "Week-SKU-channel", "28,208", "Demand, revenue, margin, discount, lost sales"],
          ["Inventory snapshot", "Week-SKU", "9,420", "On-hand, on-order, WOS, stockout status"],
          ["Purchase orders", "PO-SKU", "1,208", "Quantity, cost, lead time, on-time delivery"],
          ["Forecast output", "Forecast week-SKU", "3,120", "Forecast, interval, model, expected revenue"],
          ["Inventory scenarios", "Scenario-SKU", "240", "Safety stock, ROP, EOQ, investment, action"],
        ];
    simpleTable(
      slide,
      42,
      160,
      [210, 210, 130, 646],
      lang === "tr" ? ["Varlık", "Veri seviyesi", "Satır", "Karar alanı"] : ["Entity", "Grain", "Rows", "Decision coverage"],
      rows,
      { rowHeight: 76, headerSize: 14, fontSize: 14 },
    );
    addFooter(slide, copy.dataNotice);
    addNotes(slide, slideSources("Data/fact_weekly_sales.csv", "Data/fact_inventory_snapshot.csv", "Data/fact_purchase_orders.csv", "Data/forecast_results.csv", "Data/inventory_scenarios.csv"));
  }

  // 6. Architecture
  {
    const [title, subtitle] = copy.slides[4];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 6);
    const steps = lang === "tr"
      ? [
          ["01", "Sentetik Veri", "Python\n3 yıllık üretim"],
          ["02", "SQL Katmanı", "SQLite\n13 tablo + görünümler"],
          ["03", "Tahmin Motoru", "3 model\nSKU şampiyonu"],
          ["04", "Stok Motoru", "ROP + EOQ\n4 senaryo"],
          ["05", "BI Teslimatı", "Power BI + Excel\nPDF + PPT"],
        ]
      : [
          ["01", "Synthetic Data", "Python\n3-year generator"],
          ["02", "SQL Layer", "SQLite\n13 tables + views"],
          ["03", "Forecast Engine", "3 models\nSKU champion"],
          ["04", "Inventory Engine", "ROP + EOQ\n4 scenarios"],
          ["05", "BI Delivery", "Power BI + Excel\nPDF + PPT"],
        ];
    steps.forEach((step, index) => {
      const x = 42 + index * 244;
      addPanel(slide, { left: x, top: 224, width: 210, height: 240 }, {
        fill: index === 4 ? C.paleGreen : C.white,
        line: index === 4 ? C.green : C.blue,
      });
      addText(slide, step[0], { left: x + 18, top: 246, width: 52, height: 32 }, {
        fontSize: 18,
        bold: true,
        color: index === 4 ? C.green : C.blue,
      });
      addText(slide, step[1], { left: x + 18, top: 302, width: 174, height: 58 }, {
        fontSize: 20,
        bold: true,
        color: C.navy,
      });
      addText(slide, step[2], { left: x + 18, top: 378, width: 174, height: 58 }, {
        fontSize: 14,
        color: C.muted,
      });
      if (index < steps.length - 1) {
        slide.shapes.add({
          geometry: "rightArrow",
          position: { left: x + 214, top: 320, width: 26, height: 32 },
          fill: C.cyan,
          line: { style: "solid", fill: C.cyan, width: 0 },
        });
      }
    });
    addInsightBox(
      slide,
      42,
      510,
      1196,
      116,
      lang === "tr" ? "Tekrarlanabilirlik" : "Reproducibility",
      lang === "tr"
        ? "Tek komutla veri üretimi, model eğitimi, stok optimizasyonu, SQL veri tabanı ve doğrulama kontrolleri yeniden oluşturulur."
        : "One command regenerates the data, trains models, optimizes inventory, rebuilds the SQL database, and runs validation controls.",
      C.purple,
      C.palePurple,
    );
    addFooter(slide, copy.dataNotice);
    addNotes(slide, slideSources("Python/src/ecom_opt/run_pipeline.py", "SQL/ecommerce_demand_inventory.db"));
  }

  // 7. Data Model
  {
    const [title, subtitle] = copy.slides[5];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 7);
    addPanel(slide, { left: 490, top: 278, width: 300, height: 120 }, { fill: C.navy, line: C.navy });
    addText(slide, "dim_calendar", { left: 520, top: 304, width: 240, height: 36 }, {
      fontSize: 24,
      bold: true,
      color: C.white,
      align: "center",
    });
    addText(slide, lang === "tr" ? "Hafta • Ay • Çeyrek • Yıl" : "Week • Month • Quarter • Year", { left: 520, top: 350, width: 240, height: 24 }, {
      fontSize: 13,
      color: C.cyan,
      align: "center",
    });
    const nodes = [
      [72, 164, "fact_weekly_sales", lang === "tr" ? "Talep • Ciro • Kâr" : "Demand • Revenue • Profit"],
      [72, 438, "fact_inventory_snapshot", lang === "tr" ? "Stok • WOS • Tükenme" : "Stock • WOS • Stockout"],
      [908, 164, "forecast_results", lang === "tr" ? "Tahmin • Aralık • Model" : "Forecast • Interval • Model"],
      [908, 438, "replenishment", lang === "tr" ? "ROP • EOQ • Aksiyon" : "ROP • EOQ • Action"],
    ];
    nodes.forEach((node, index) => {
      addPanel(slide, { left: node[0], top: node[1], width: 300, height: 126 }, {
        fill: index < 2 ? C.paleBlue : C.paleGreen,
        line: index < 2 ? C.blue : C.green,
      });
      addText(slide, node[2], { left: node[0] + 20, top: node[1] + 26, width: 260, height: 34 }, {
        fontSize: 18,
        bold: true,
        color: C.navy,
        align: "center",
      });
      addText(slide, node[3], { left: node[0] + 20, top: node[1] + 76, width: 260, height: 28 }, {
        fontSize: 13,
        color: C.muted,
        align: "center",
      });
      const fromX = node[0] < 500 ? node[0] + 300 : node[0];
      const toX = node[0] < 500 ? 490 : 790;
      const lineY = node[1] + 63;
      slide.shapes.add({
        geometry: "rect",
        position: { left: Math.min(fromX, toX), top: lineY, width: Math.abs(toX - fromX), height: 3 },
        fill: C.cyan,
        line: { style: "solid", fill: C.cyan, width: 0 },
      });
    });
    addText(slide, lang === "tr" ? "Tek yönlü filtreleme • Tarih zekâsı • Güvenilir KPI bağlamı" : "Single-direction filtering • Time intelligence • Reliable KPI context", { left: 250, top: 610, width: 780, height: 32 }, {
      fontSize: 16,
      bold: true,
      color: C.purple,
      align: "center",
    });
    addFooter(slide, copy.dataNotice);
    addNotes(slide, slideSources("docs/data_dictionary.md", "PowerBI/Ecommerce_Demand_Inventory_PBIP"));
  }

  // 8. Historical Performance
  {
    const [title, subtitle] = copy.slides[6];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 8);
    addPanel(slide, { left: 42, top: 150, width: 718, height: 470 }, { fill: C.white, line: C.line });
    addSectionLabel(slide, lang === "tr" ? "Aylık Net Ciro | 2023-2025" : "Monthly Net Revenue | 2023-2025", 64, 168, 674);
    const monthlyLabels = monthly.map((row) => row.YearMonth);
    const monthlyRevenueM = monthly.map((row) => row.NetRevenueTRY / 1_000_000);
    addLineChart(
      slide,
      { left: 64, top: 218, width: 674, height: 360 },
      monthlyLabels,
      [{ name: lang === "tr" ? "Ciro (M TRY)" : "Revenue (TRY M)", values: monthlyRevenueM, color: C.blue }],
      Math.ceil(Math.max(...monthlyRevenueM) / 5) * 5 + 5,
      "0.0",
    );
    metricCard(slide, 790, 150, 448, lang === "tr" ? "Tarihsel Ciro" : "Historical Revenue", fmtM(historicalRevenue, lang), "2023-2025", C.blue);
    addInsightBox(slide, 790, 320, 448, 130, lang === "tr" ? "Brüt Marj" : "Gross Margin", `${fmtPct(portfolioMargin)} ${lang === "tr" ? "ağırlıklı portföy marjı" : "weighted portfolio margin"}`, C.green, C.paleGreen);
    addInsightBox(slide, 790, 470, 448, 150, lang === "tr" ? "Talep Karşılama" : "Demand Fulfillment", `${fmtPct(totalSold / totalDemand)} ${lang === "tr" ? "karşılama oranı; satış kaybı fırsatı görünür." : "fulfilled; lost-sales opportunity remains visible."}`, C.amber, C.paleAmber);
    addFooter(slide, copy.dataNotice);
    addNotes(slide, slideSources("Data/monthly_performance.csv", "Data/category_performance.csv"));
  }

  // 9. Demand Seasonality
  {
    const [title, subtitle] = copy.slides[7];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 9);
    addPanel(slide, { left: 42, top: 150, width: 1196, height: 400 }, { fill: C.white, line: C.line });
    addSectionLabel(slide, lang === "tr" ? "Üç Aylık Talep, Satış ve Satış Kaybı" : "Quarterly Demand, Sales, and Lost Sales", 64, 168, 1152);
    const sampled = monthly.filter((_, index) => index % 3 === 0);
    addBarChart(
      slide,
      { left: 64, top: 216, width: 1152, height: 310 },
      sampled.map((row) => row.YearMonth),
      [
        { name: lang === "tr" ? "Talep" : "Demand", values: sampled.map((row) => row.EstimatedDemandUnits / 1000), color: C.cyan },
        { name: lang === "tr" ? "Satış" : "Sold", values: sampled.map((row) => row.UnitsSold / 1000), color: C.blue },
        { name: lang === "tr" ? "Satış kaybı" : "Lost", values: sampled.map((row) => row.LostSalesUnits / 1000), color: C.red },
      ],
      {
        hasLegend: true,
        showValue: false,
        yMax: Math.ceil(Math.max(...sampled.map((row) => row.EstimatedDemandUnits / 1000)) / 5) * 5 + 5,
        yFormat: "0.0",
      },
    );
    addInsightBox(slide, 42, 572, 582, 76, lang === "tr" ? "Talep sinyali" : "Demand signal", lang === "tr" ? "Kampanya ve sezon haftaları hacmi belirgin biçimde artırıyor." : "Campaign and seasonal weeks create visible demand peaks.", C.blue, C.paleBlue);
    addInsightBox(slide, 642, 572, 596, 76, lang === "tr" ? "Stok etkisi" : "Inventory implication", lang === "tr" ? `${lostSales.toFixed(0)} adet tahmini satış kaybı planlamaya dâhil edildi.` : `${lostSales.toFixed(0)} estimated lost units are included in planning.`, C.red, C.paleRed);
    addFooter(slide, copy.dataNotice);
    addNotes(slide, slideSources("Data/monthly_performance.csv", "Data/fact_promotions.csv"));
  }

  // 10. Forecasting Approach
  {
    const [title, subtitle] = copy.slides[8];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 10);
    const process = lang === "tr"
      ? [["Özellik üretimi", "Takvim, kampanya, gecikmeli değer ve hareketli ortalamalar"], ["13 haftalık geri test", "Gelecek bilgisi sızdırmadan son dönemi ölç"], ["SKU bazlı seçim", "En düşük WAPE değerine göre şampiyonu belirle"]]
      : [["Feature engineering", "Calendar, promotion, lag, and rolling features"], ["13-week backtest", "Measure the latest holdout without future leakage"], ["SKU-level selection", "Choose the champion with the lowest WAPE"]];
    process.forEach((item, index) => {
      const x = 42 + index * 400;
      addPanel(slide, { left: x, top: 154, width: 374, height: 180 }, { fill: C.light, line: C.line });
      addText(slide, `0${index + 1}`, { left: x + 22, top: 176, width: 48, height: 30 }, { fontSize: 18, bold: true, color: C.blue });
      addText(slide, item[0], { left: x + 84, top: 174, width: 260, height: 34 }, { fontSize: 19, bold: true, color: C.navy });
      addText(slide, item[1], { left: x + 22, top: 230, width: 324, height: 72 }, { fontSize: 15, color: C.text });
    });
    const modelCards = [
      ["Seasonal Naive", lang === "tr" ? "Önceki yılın aynı ISO haftası" : "Same ISO week from prior year", C.cyan],
      ["8-Week Moving Average", lang === "tr" ? "Kısa ve orta vadeli hareketli ortalama" : "Blended short- and medium-term mean", C.amber],
      ["Gradient Boosting", lang === "tr" ? "Doğrusal olmayan talep ilişkileri" : "Non-linear demand relationships", C.green],
    ];
    modelCards.forEach((item, index) => {
      const x = 42 + index * 400;
      addPanel(slide, { left: x, top: 372, width: 374, height: 218 }, { fill: C.white, line: item[2] });
      addText(slide, localModel(item[0], lang), { left: x + 24, top: 404, width: 326, height: 56 }, { fontSize: 21, bold: true, color: item[2] });
      addText(slide, item[1], { left: x + 24, top: 482, width: 326, height: 70 }, { fontSize: 16, color: C.text });
    });
    addFooter(slide, copy.dataNotice);
    addNotes(slide, [
      ...slideSources("Python/src/ecom_opt/forecasting.py", "Data/model_comparison.csv"),
      "Official methodology reference: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html",
    ]);
  }

  // 11. Model Performance
  {
    const [title, subtitle] = copy.slides[9];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 11);
    addPanel(slide, { left: 42, top: 150, width: 650, height: 470 }, { fill: C.white, line: C.line });
    addSectionLabel(slide, lang === "tr" ? "Model Bazında Ortalama WAPE" : "Average WAPE by Model", 64, 168, 606);
    addBarChart(
      slide,
      { left: 64, top: 218, width: 606, height: 350 },
      modelSummary.map((row) => localModel(row.model, lang)),
      [{ name: "WAPE", values: modelSummary.map((row) => row.wape * 100), color: C.blue }],
      {
        hasLegend: false,
        yMax: 30,
        yFormat: "0.0",
      },
    );
    const championCounts = modelSummary.map((row) => [row.model, row.winners]);
    metricCard(slide, 720, 150, 518, lang === "tr" ? "Ortalama Şampiyon WAPE" : "Average Champion WAPE", fmtPct(averageChampionWape), lang === "tr" ? "Portföy geri testi" : "Portfolio backtest", C.green);
    addInsightBox(slide, 720, 326, 518, 126, lang === "tr" ? "Şampiyon Dağılımı" : "Champion Distribution", championCounts.map(([model, count]) => `${localModel(model, lang)}: ${count}`).join("  •  "), C.blue, C.paleBlue);
    addInsightBox(slide, 720, 474, 518, 146, lang === "tr" ? "Yönetişim" : "Governance", lang === "tr" ? "Her SKU için seçilen model, WAPE ve sapma değeri veri setine yazılır; stok hesabı aynı model belirsizliğini kullanır." : "The selected model, WAPE, and bias are persisted by SKU; the inventory engine reuses the same residual uncertainty.", C.purple, C.palePurple);
    addFooter(slide, copy.dataNotice);
    addNotes(slide, slideSources("Data/model_comparison.csv", "Data/forecast_backtest.csv"));
  }

  // 12. 2026 Forecast
  {
    const [title, subtitle] = copy.slides[10];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 12);
    addPanel(slide, { left: 42, top: 150, width: 760, height: 470 }, { fill: C.white, line: C.line });
    addSectionLabel(slide, lang === "tr" ? "Aylık Talep Tahmini" : "Monthly Demand Forecast", 64, 168, 716);
    const forecastUnitsK = forecastByMonth.map((row) => row.units / 1000);
    addLineChart(
      slide,
      { left: 64, top: 218, width: 716, height: 350 },
      forecastByMonth.map((row) => row.month),
      [{ name: lang === "tr" ? "Tahmin (bin adet)" : "Forecast (K units)", values: forecastUnitsK, color: C.blue }],
      Math.ceil(Math.max(...forecastUnitsK) / 5) * 5 + 5,
      "0.0",
    );
    metricCard(slide, 830, 150, 408, lang === "tr" ? "Tahmin Adedi" : "Forecast Units", Math.round(baseScenario.ForecastUnits).toLocaleString(lang === "tr" ? "tr-TR" : "en-US"), "52 weeks • 60 SKUs", C.blue);
    metricCard(slide, 830, 330, 408, lang === "tr" ? "Tahmini Ciro" : "Forecast Revenue", fmtM(baseScenario.ForecastRevenueTRY, lang), lang === "tr" ? "Beklenen satış fiyatı" : "Expected selling price", C.cyan);
    addInsightBox(slide, 830, 510, 408, 110, lang === "tr" ? "%80 Tahmin Aralığı" : "80% Prediction Interval", lang === "tr" ? "Alt ve üst bantlar, emniyet stoğu ve kapasite stres testini destekler." : "Lower and upper bands support safety-stock and capacity stress testing.", C.purple, C.palePurple);
    addFooter(slide, copy.dataNotice);
    addNotes(slide, slideSources("Data/forecast_results.csv", "Data/forecast_monthly.csv"));
  }

  // 13. Inventory Logic
  {
    const [title, subtitle] = copy.slides[11];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 13);
    const formulas = lang === "tr"
      ? [
          ["Güvenlik Stoğu", "z × hata standart sapması × √(termin haftası)", "Hizmet seviyesi koruması"],
          ["Yeniden Sipariş Noktası", "Termin talebi + güvenlik stoğu", "Ne zaman sipariş verilmeli?"],
          ["Ekonomik Sipariş Miktarı", "√(2 × yıllık talep × sipariş maliyeti / elde tutma maliyeti)", "Ne kadar sipariş verilmeli?"],
        ]
      : [
          ["Safety Stock", "z × residual standard deviation × √(lead-time weeks)", "Service-level protection"],
          ["Reorder Point", "Lead-time demand + safety stock", "When should an order be placed?"],
          ["Economic Order Quantity", "√(2 × annual demand × order cost / holding cost)", "How much should be ordered?"],
        ];
    formulas.forEach((item, index) => {
      const y = 154 + index * 154;
      addPanel(slide, { left: 42, top: y, width: 760, height: 130 }, { fill: C.white, line: [C.blue, C.cyan, C.green][index] });
      addText(slide, item[0], { left: 66, top: y + 20, width: 250, height: 34 }, { fontSize: 19, bold: true, color: [C.blue, C.cyan, C.green][index] });
      addText(slide, item[1], { left: 330, top: y + 20, width: 440, height: 42 }, { fontSize: 17, bold: true, color: C.navy });
      addText(slide, item[2], { left: 330, top: y + 72, width: 440, height: 28 }, { fontSize: 14, color: C.muted });
    });
    addPanel(slide, { left: 838, top: 154, width: 400, height: 438 }, { fill: C.light, line: C.line });
    addText(slide, lang === "tr" ? "İş Kuralları" : "Business Constraints", { left: 868, top: 190, width: 340, height: 40 }, { fontSize: 24, bold: true, color: C.navy });
    bulletList(
      slide,
      lang === "tr"
        ? ["Minimum sipariş miktarı (MOQ)", "Koli / paket katı", "Mevcut ve yoldaki stok", "Hizmet seviyesi hedefi", "Yıllık elde tutma oranı"]
        : ["Minimum order quantity (MOQ)", "Case-pack multiple", "On-hand and on-order inventory", "Target service level", "Annual holding-cost rate"],
      868,
      258,
      320,
      { fontSize: 16, rowHeight: 56, accent: C.amber },
    );
    addFooter(slide, copy.dataNotice);
    addNotes(slide, [
      ...slideSources("Python/src/ecom_opt/inventory.py", "Data/replenishment_recommendations.csv"),
      "Official statistical reference: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.norm.html",
    ]);
  }

  // 14. Inventory Health
  {
    const [title, subtitle] = copy.slides[12];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 14);
    addPanel(slide, { left: 42, top: 150, width: 720, height: 470 }, { fill: C.white, line: C.line });
    addSectionLabel(slide, lang === "tr" ? "Kategori Bazında Tahmini Stok Haftası" : "Projected Weeks of Supply by Category", 64, 168, 676);
    addBarChart(
      slide,
      { left: 64, top: 218, width: 676, height: 350 },
      categoryWos.map((row) => localCategory(row.category, lang)),
      [{ name: "WOS", values: categoryWos.map((row) => row.wos), color: C.cyan }],
      { hasLegend: false, yMax: 8, yFormat: "0.0" },
    );
    const actions = ["ORDER NOW", "MONITOR", "HEALTHY"].map((action) => ({
      action,
      count: replenishment.filter((row) => row.Action === action).length,
    }));
    metricCard(slide, 790, 150, 448, lang === "tr" ? "Ortalama Stok Haftası" : "Average Weeks of Supply", `${(replenishment.reduce((sum, row) => sum + row.ProjectedWeeksOfSupply, 0) / replenishment.length).toFixed(1)}`, lang === "tr" ? "Baz senaryo" : "Base scenario", C.cyan);
    addInsightBox(slide, 790, 330, 448, 126, lang === "tr" ? "Aksiyon Dağılımı" : "Action Distribution", actions.map((row) => `${row.action}: ${row.count}`).join("  •  "), C.blue, C.paleBlue);
    addInsightBox(slide, 790, 478, 448, 142, lang === "tr" ? "Öncelik" : "Priority", lang === "tr" ? "Düşük stok haftası ve yüksek satış potansiyeli birlikte değerlendirilerek sipariş sırası belirlenir." : "Ordering priority combines low weeks of supply with revenue potential and lead-time exposure.", C.red, C.paleRed);
    addFooter(slide, copy.dataNotice);
    addNotes(slide, slideSources("Data/replenishment_recommendations.csv"));
  }

  // 15. Replenishment Plan
  {
    const [title, subtitle] = copy.slides[13];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 15);
    addPanel(slide, { left: 42, top: 150, width: 650, height: 470 }, { fill: C.white, line: C.line });
    addSectionLabel(slide, lang === "tr" ? "En Yüksek Acil Sipariş Yatırımları" : "Largest Immediate Order Investments", 64, 168, 606);
    addBarChart(
      slide,
      { left: 64, top: 218, width: 606, height: 350 },
      topOrders.map((row) => row.SKU),
      [{ name: lang === "tr" ? "Yatırım (M TRY)" : "Investment (TRY M)", values: topOrders.map((row) => row.RecommendedInvestmentTRY / 1_000_000), color: C.amber }],
      { hasLegend: false, yMax: 0.5, yFormat: "0.0" },
    );
    simpleTable(
      slide,
      720,
      160,
      [110, 160, 100, 130],
      lang === "tr" ? ["SKU", "Kategori", "Miktar", "Yatırım"] : ["SKU", "Category", "Qty", "Investment"],
      topOrders.slice(0, 8).map((row) => [
        row.SKU,
        localCategory(row.Category, lang),
        Math.round(row.RecommendedOrderQty).toLocaleString(lang === "tr" ? "tr-TR" : "en-US"),
        fmtM(row.RecommendedInvestmentTRY, lang),
      ]),
      { rowHeight: 47, headerSize: 12, fontSize: 11 },
    );
    addFooter(slide, copy.dataNotice);
    addNotes(slide, slideSources("Data/replenishment_recommendations.csv"));
  }

  // 16. Supplier Performance
  {
    const [title, subtitle] = copy.slides[14];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 16);
    addPanel(slide, { left: 42, top: 150, width: 650, height: 470 }, { fill: C.white, line: C.line });
    addSectionLabel(slide, lang === "tr" ? "Tedarikçi Satın Alma Değeri" : "Supplier Purchase Value", 64, 168, 606);
    const sortedSuppliers = [...suppliers].sort((a, b) => b.PurchaseValueTRY - a.PurchaseValueTRY);
    addBarChart(
      slide,
      { left: 64, top: 218, width: 606, height: 350 },
      sortedSuppliers.map((row) => row.SupplierID),
      [{ name: lang === "tr" ? "Satın alma (M TRY)" : "Purchase (TRY M)", values: sortedSuppliers.map((row) => row.PurchaseValueTRY / 1_000_000), color: C.blue }],
      { hasLegend: false, yMax: 70, yFormat: "0.0" },
    );
    simpleTable(
      slide,
      720,
      160,
      [110, 110, 135, 145],
      lang === "tr" ? ["Tedarikçi", "Sipariş", "Termin", "Zamanında"] : ["Supplier", "POs", "Lead time", "On-time"],
      sortedSuppliers.map((row) => [
        row.SupplierID,
        row.PurchaseOrders,
        `${Number(row.AverageActualLeadTimeDays).toFixed(1)} ${lang === "tr" ? "gün" : "days"}`,
        fmtPct(row.OnTimeDeliveryRate),
      ]),
      { rowHeight: 47, headerSize: 12, fontSize: 11 },
    );
    addFooter(slide, copy.dataNotice);
    addNotes(slide, slideSources("Data/supplier_scorecard.csv", "Data/fact_purchase_orders.csv"));
  }

  // 17. Scenario Analysis
  {
    const [title, subtitle] = copy.slides[15];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 17);
    addPanel(slide, { left: 42, top: 150, width: 760, height: 470 }, { fill: C.white, line: C.line });
    addSectionLabel(slide, lang === "tr" ? "Senaryoya Göre Ciro ve Stok Yatırımı" : "Revenue and Inventory Investment by Scenario", 64, 168, 716);
    addBarChart(
      slide,
      { left: 64, top: 218, width: 716, height: 350 },
      scenarios.map((row) => localScenario(row.Scenario, lang)),
      [
        { name: lang === "tr" ? "Ciro (M TRY)" : "Revenue (TRY M)", values: scenarios.map((row) => row.ForecastRevenueTRY / 1_000_000), color: C.blue },
        { name: lang === "tr" ? "Stok yatırımı (M TRY)" : "Inventory investment (TRY M)", values: scenarios.map((row) => row.RecommendedInvestmentTRY / 1_000_000), color: C.amber },
      ],
      { hasLegend: true, yMax: 500, yFormat: "0.0" },
    );
    metricCard(slide, 830, 150, 408, lang === "tr" ? "Baz Yatırım" : "Base Investment", fmtM(baseScenario.RecommendedInvestmentTRY, lang), `${baseScenario.SKUsToOrder} ${lang === "tr" ? "SKU" : "SKUs"}`, C.blue);
    const growth = scenarios.find((row) => row.Scenario === "Growth");
    const resilience = scenarios.find((row) => row.Scenario === "Resilience");
    addInsightBox(slide, 830, 330, 408, 126, lang === "tr" ? "Büyüme" : "Growth", `${fmtM(growth.ForecastRevenueTRY, lang)} ${lang === "tr" ? "ciro; " : "revenue; "}${fmtM(growth.RecommendedInvestmentTRY, lang)} ${lang === "tr" ? "yatırım" : "investment"}`, C.green, C.paleGreen);
    addInsightBox(slide, 830, 478, 408, 142, lang === "tr" ? "Dayanıklılık" : "Resilience", lang === "tr" ? `14 günlük termin şoku yatırımı ${fmtM(resilience.RecommendedInvestmentTRY, lang)} seviyesine çıkarır.` : `A 14-day lead-time shock raises investment to ${fmtM(resilience.RecommendedInvestmentTRY, lang)}.`, C.red, C.paleRed);
    addFooter(slide, copy.dataNotice);
    addNotes(slide, slideSources("Data/scenario_summary.csv", "Data/inventory_scenarios.csv"));
  }

  // 18. BI Delivery
  {
    const [title, subtitle] = copy.slides[16];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 18);
    const deliverables = lang === "tr"
      ? [
          ["Power BI", "10 sayfa • 81 görsel • gömülü veri modeli"],
          ["Excel", "15 sekme • senaryo seçici • otomatik kontroller"],
          ["SQL + Python", "SQLite veri tabanı • 3 tahmin modeli • testler"],
          ["Yönetici Çıktıları", "10 sayfa vektör PDF • 20 slayt TR + EN"],
        ]
      : [
          ["Power BI", "10 pages • 81 visuals • embedded semantic model"],
          ["Excel", "15 sheets • scenario selector • automated controls"],
          ["SQL + Python", "SQLite database • 3 forecast models • tests"],
          ["Executive Outputs", "10-page vector PDF • 20-slide TR + EN decks"],
        ];
    deliverables.forEach((item, index) => {
      const x = 42 + index * 300;
      addPanel(slide, { left: x, top: 180, width: 278, height: 330 }, { fill: index % 2 === 0 ? C.paleBlue : C.light, line: index % 2 === 0 ? C.blue : C.line });
      addText(slide, `0${index + 1}`, { left: x + 24, top: 210, width: 60, height: 34 }, { fontSize: 18, bold: true, color: index % 2 === 0 ? C.blue : C.purple });
      addText(slide, item[0], { left: x + 24, top: 272, width: 230, height: 50 }, { fontSize: 24, bold: true, color: C.navy });
      addText(slide, item[1], { left: x + 24, top: 350, width: 230, height: 104 }, { fontSize: 16, color: C.text });
    });
    addInsightBox(slide, 42, 540, 1196, 92, lang === "tr" ? "Portföy avantajı" : "Portfolio advantage", lang === "tr" ? "İşe alım uzmanı hem yönetici sonucunu hem de veri, kod, model ve dokümantasyon katmanlarını inceleyebilir." : "A reviewer can inspect both the executive outcome and the underlying data, code, model, tests, and documentation.", C.green, C.paleGreen);
    addFooter(slide, copy.dataNotice);
    addNotes(slide, slideSources("Excel/Ecommerce_Demand_Inventory_Scenario_Planner.xlsx", "PowerBI/Ecommerce_Demand_Inventory_PBIP", "Reports/Ecommerce_Demand_Inventory_10_Page_Vector_HD.pdf"));
  }

  // 19. Recommendations
  {
    const [title, subtitle] = copy.slides[17];
    const slide = presentation.slides.add();
    addHeader(slide, title, subtitle, 19);
    const milestones = lang === "tr"
      ? [
          ["0-30 Gün", "Acil siparişleri doğrula", "10 ORDER NOW SKU için tedarikçi kapasitesi, koli katı ve kampanya tarihini kontrol et."],
          ["31-60 Gün", "Tahmin gözden geçirmesini işlet", "Gerçekleşen talebi haftalık ekle; sapma ve WAPE’yi kategori bazında izle."],
          ["61-90 Gün", "İstisna bazlı planlamaya geç", "ROP ihlali, bütçe aşımı ve yüksek hata için otomatik uyarı oluştur."],
        ]
      : [
          ["0-30 Days", "Validate immediate orders", "Confirm supplier capacity, case packs, and campaign timing for 10 ORDER NOW SKUs."],
          ["31-60 Days", "Operationalize forecast review", "Load actual demand weekly and monitor bias and WAPE by category."],
          ["61-90 Days", "Move to exception planning", "Automate alerts for reorder-point breaches, budget overruns, and high error."],
        ];
    milestones.forEach((item, index) => {
      const x = 42 + index * 400;
      addPanel(slide, { left: x, top: 164, width: 374, height: 420 }, { fill: C.white, line: [C.blue, C.cyan, C.green][index] });
      slide.shapes.add({
        geometry: "roundRect",
        position: { left: x, top: 164, width: 374, height: 58 },
        fill: [C.blue, C.cyan, C.green][index],
        line: { style: "solid", fill: [C.blue, C.cyan, C.green][index], width: 0 },
        borderRadius: "rounded-xl",
      });
      addText(slide, item[0], { left: x + 22, top: 181, width: 330, height: 28 }, { fontSize: 16, bold: true, color: C.white });
      addText(slide, item[1], { left: x + 24, top: 270, width: 326, height: 70 }, { fontSize: 22, bold: true, color: C.navy });
      addText(slide, item[2], { left: x + 24, top: 370, width: 326, height: 132 }, { fontSize: 16, color: C.text });
    });
    addFooter(slide, copy.dataNotice);
    addNotes(slide, slideSources("Reports/Ecommerce_Demand_Inventory_10_Page_Vector_HD.pdf"));
  }

  // 20. Close
  {
    const slide = presentation.slides.add();
    slide.background.fill = C.navy;
    addText(slide, copy.thankYou.toUpperCase(), { left: 54, top: 44, width: 300, height: 30 }, { fontSize: 13, bold: true, color: C.cyan });
    addText(slide, copy.closeTitle, { left: 54, top: 170, width: 950, height: 130 }, { fontSize: 50, bold: true, color: C.white });
    addText(slide, copy.closeBody, { left: 54, top: 360, width: 820, height: 100 }, { fontSize: 20, color: "#D7E3F7" });
    addText(slide, "Murat Miraç Gedik", { left: 54, top: 540, width: 360, height: 34 }, { fontSize: 18, bold: true, color: C.white });
    addText(slide, "GitHub • LinkedIn • Business Intelligence • Forecasting", { left: 54, top: 590, width: 650, height: 28 }, { fontSize: 14, color: C.cyan });
    addText(slide, copy.dataNotice, { left: 54, top: 655, width: 650, height: 20 }, { fontSize: 10, color: "#B9C7DB" });
    addNotes(slide, slideSources("README.md"));
  }

  return presentation;
}

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function exportDeck(lang) {
  const presentation = createDeck(lang);
  const previewDir = path.join(outputDir, `previews-${lang}`);
  await fs.mkdir(previewDir, { recursive: true });
  for (const [index, slide] of presentation.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    const png = await presentation.export({ slide, format: "png", scale: 1.5 });
    await writeBlob(path.join(previewDir, `${stem}.png`), png);
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(previewDir, `${stem}.layout.json`), await layout.text());
  }
  const montage = await presentation.export({
    format: "webp",
    montage: true,
    scale: 0.7,
  });
  await writeBlob(path.join(previewDir, "deck-montage.webp"), montage);
  const pptx = await PresentationFile.exportPptx(presentation);
  const filename =
    lang === "tr"
      ? "E_Ticaret_Talep_Tahmini_Stok_Optimizasyonu_Profesyonel_Sunum_TR.pptx"
      : "Ecommerce_Demand_Forecasting_Inventory_Optimization_Professional_Deck_EN.pptx";
  const outputPath = path.join(outputDir, filename);
  await pptx.save(outputPath);
  const inspection = await presentation.inspect({
    kind: "slide,textbox,shape,chart,notes,layout",
    maxChars: 16000,
    options: { maxResults: 400 },
  });
  await fs.writeFile(path.join(previewDir, "deck-inspection.ndjson"), inspection.ndjson, "utf8");
  return outputPath;
}

await fs.mkdir(outputDir, { recursive: true });
const english = await exportDeck("en");
const turkish = await exportDeck("tr");
console.log(JSON.stringify({ english, turkish }, null, 2));

