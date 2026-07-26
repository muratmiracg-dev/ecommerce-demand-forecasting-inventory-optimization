from __future__ import annotations

import math
from pathlib import Path
from textwrap import wrap

import numpy as np
import pandas as pd
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "Data"
REPORT_DIR = PROJECT_ROOT / "Reports"
OUTPUT_PATH = REPORT_DIR / "Ecommerce_Demand_Inventory_10_Page_Vector_HD.pdf"

PAGE_W = 13.333 * inch
PAGE_H = 7.5 * inch
MARGIN = 32

NAVY = HexColor("#0B132B")
NAVY2 = HexColor("#14213D")
BLUE = HexColor("#3D8DFF")
CYAN = HexColor("#6DCBF4")
PALE_BLUE = HexColor("#EAF5FB")
LIGHT = HexColor("#F4F7FB")
LINE = HexColor("#DCE3ED")
TEXT = HexColor("#172033")
MUTED = HexColor("#667085")
WHITE = HexColor("#FFFFFF")
GREEN = HexColor("#18A558")
PALE_GREEN = HexColor("#E8F7EE")
AMBER = HexColor("#F59E0B")
PALE_AMBER = HexColor("#FFF4D6")
RED = HexColor("#D64545")
PALE_RED = HexColor("#FDECEC")
ORANGE = HexColor("#F97316")
PURPLE = HexColor("#7C3AED")

FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_ITALIC = FONT_REGULAR

pdfmetrics.registerFont(TTFont("DejaVu", FONT_REGULAR))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", FONT_BOLD))
pdfmetrics.registerFont(TTFont("DejaVu-Italic", FONT_ITALIC))


def money_m(value: float) -> str:
    return f"TRY {value / 1_000_000:,.1f}M"


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def draw_text(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    size: float = 10,
    color=TEXT,
    font: str = "DejaVu",
    align: str = "left",
) -> None:
    c.setFillColor(color)
    c.setFont(font, size)
    if align == "right":
        c.drawRightString(x, y, text)
    elif align == "center":
        c.drawCentredString(x, y, text)
    else:
        c.drawString(x, y, text)


def paragraph(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    height: float,
    size: float = 10,
    color=TEXT,
    leading: float | None = None,
    bold: bool = False,
) -> None:
    style = ParagraphStyle(
        "p",
        fontName="DejaVu-Bold" if bold else "DejaVu",
        fontSize=size,
        leading=leading or size * 1.3,
        textColor=color,
        alignment=TA_LEFT,
    )
    p = Paragraph(text, style)
    _, required = p.wrap(width, height)
    p.drawOn(c, x, y + height - min(required, height))


def rounded_panel(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    fill=WHITE,
    stroke=LINE,
    radius: float = 8,
) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(0.7)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)


def header(c: canvas.Canvas, title: str, subtitle: str, page_no: int) -> None:
    c.setFillColor(NAVY)
    c.rect(0, PAGE_H - 74, PAGE_W, 74, fill=1, stroke=0)
    draw_text(c, "E-COMMERCE DEMAND & INVENTORY", MARGIN, PAGE_H - 24, 9, CYAN, "DejaVu-Bold")
    draw_text(c, title, MARGIN, PAGE_H - 49, 21, WHITE, "DejaVu-Bold")
    draw_text(c, subtitle, PAGE_W - MARGIN, PAGE_H - 47, 8.5, HexColor("#D7E3F7"), "DejaVu-Italic", "right")
    c.setStrokeColor(BLUE)
    c.setLineWidth(2)
    c.line(MARGIN, PAGE_H - 69, PAGE_W - MARGIN, PAGE_H - 69)
    draw_text(c, f"{page_no:02d}", PAGE_W - MARGIN, 18, 8, MUTED, "DejaVu-Bold", "right")
    draw_text(
        c,
        "MonacoLuxe-inspired synthetic portfolio data | TRY | 2023-2026",
        MARGIN,
        18,
        7.5,
        MUTED,
        "DejaVu-Italic",
    )


def kpi_card(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    label: str,
    value: str,
    note: str,
    accent=BLUE,
) -> None:
    rounded_panel(c, x, y, w, h)
    c.setFillColor(accent)
    c.roundRect(x, y + h - 6, w, 6, 4, fill=1, stroke=0)
    draw_text(c, label.upper(), x + 12, y + h - 18, 7.4, MUTED, "DejaVu-Bold")
    draw_text(c, value, x + 12, y + 21, 16.5, accent, "DejaVu-Bold")
    draw_text(c, note, x + 12, y + 7, 6.8, MUTED)


def panel_title(c: canvas.Canvas, title: str, x: float, y: float, w: float) -> None:
    draw_text(c, title, x + 12, y - 20, 10, NAVY, "DejaVu-Bold")
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.line(x + 12, y - 27, x + w - 12, y - 27)


def line_chart(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    labels: list[str],
    series: list[tuple[str, list[float], object]],
    y_formatter=lambda v: f"{v:,.0f}",
    label_every: int = 6,
    fill_band: tuple[list[float], list[float], object] | None = None,
) -> None:
    left, right, bottom, top = 48, 12, 28, 14
    plot_x, plot_y = x + left, y + bottom
    plot_w, plot_h = w - left - right, h - bottom - top
    values = [value for _, vals, _ in series for value in vals if pd.notna(value)]
    if fill_band:
        values.extend(fill_band[0])
        values.extend(fill_band[1])
    y_min = 0
    y_max = max(values) * 1.12 if values else 1
    for tick in range(5):
        value = y_min + (y_max - y_min) * tick / 4
        py = plot_y + plot_h * tick / 4
        c.setStrokeColor(LINE)
        c.setLineWidth(0.5)
        c.line(plot_x, py, plot_x + plot_w, py)
        draw_text(c, y_formatter(value), plot_x - 6, py - 2, 6.8, MUTED, align="right")
    n = max(1, len(labels) - 1)

    def point(index: int, value: float) -> tuple[float, float]:
        return (
            plot_x + plot_w * index / n,
            plot_y + plot_h * (value - y_min) / (y_max - y_min),
        )

    if fill_band:
        lower, upper, color = fill_band
        path = c.beginPath()
        for idx, value in enumerate(upper):
            px, py = point(idx, value)
            if idx == 0:
                path.moveTo(px, py)
            else:
                path.lineTo(px, py)
        for idx in range(len(lower) - 1, -1, -1):
            px, py = point(idx, lower[idx])
            path.lineTo(px, py)
        path.close()
        c.setFillColor(color)
        c.setStrokeColor(color)
        c.drawPath(path, fill=1, stroke=0)

    for _, vals, color in series:
        path = c.beginPath()
        for idx, value in enumerate(vals):
            px, py = point(idx, value)
            if idx == 0:
                path.moveTo(px, py)
            else:
                path.lineTo(px, py)
        c.setStrokeColor(color)
        c.setLineWidth(2)
        c.drawPath(path, fill=0, stroke=1)

    for idx, label in enumerate(labels):
        if idx % label_every == 0 or idx == len(labels) - 1:
            px, _ = point(idx, 0)
            draw_text(c, label, px, y + 8, 6.2, MUTED, align="center")

    legend_x = x + 12
    for name, _, color in series:
        c.setStrokeColor(color)
        c.setLineWidth(2.5)
        c.line(legend_x, y + h - 7, legend_x + 15, y + h - 7)
        draw_text(c, name, legend_x + 20, y + h - 10, 7, MUTED)
        legend_x += 95


def bar_chart(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    labels: list[str],
    values: list[float],
    color=BLUE,
    value_formatter=lambda v: f"{v:,.0f}",
    horizontal: bool = False,
) -> None:
    if horizontal:
        left, right, bottom, top = 120, 48, 10, 12
        plot_x, plot_y = x + left, y + bottom
        plot_w, plot_h = w - left - right, h - bottom - top
        max_value = max(values) * 1.1 if values else 1
        gap = plot_h / max(1, len(labels))
        for idx, (label, value) in enumerate(zip(labels, values, strict=True)):
            by = plot_y + plot_h - (idx + 1) * gap + gap * 0.2
            bh = gap * 0.58
            bw = plot_w * value / max_value
            c.setFillColor(color)
            c.roundRect(plot_x, by, bw, bh, 3, fill=1, stroke=0)
            draw_text(c, label, plot_x - 7, by + bh / 2 - 2, 6.8, MUTED, align="right")
            draw_text(c, value_formatter(value), plot_x + bw + 5, by + bh / 2 - 2, 6.8, TEXT, "DejaVu-Bold")
    else:
        left, right, bottom, top = 40, 8, 36, 12
        plot_x, plot_y = x + left, y + bottom
        plot_w, plot_h = w - left - right, h - bottom - top
        max_value = max(values) * 1.12 if values else 1
        gap = plot_w / max(1, len(labels))
        bar_w = gap * 0.58
        for tick in range(5):
            value = max_value * tick / 4
            py = plot_y + plot_h * tick / 4
            c.setStrokeColor(LINE)
            c.setLineWidth(0.5)
            c.line(plot_x, py, plot_x + plot_w, py)
            draw_text(c, value_formatter(value), plot_x - 5, py - 2, 6.5, MUTED, align="right")
        for idx, (label, value) in enumerate(zip(labels, values, strict=True)):
            bx = plot_x + idx * gap + (gap - bar_w) / 2
            bh = plot_h * value / max_value
            c.setFillColor(color)
            c.roundRect(bx, plot_y, bar_w, bh, 3, fill=1, stroke=0)
            draw_text(c, label, bx + bar_w / 2, y + 13, 6.5, MUTED, align="center")
            draw_text(c, value_formatter(value), bx + bar_w / 2, plot_y + bh + 5, 6.5, TEXT, "DejaVu-Bold", "center")


def grouped_bars(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    labels: list[str],
    series: list[tuple[str, list[float], object]],
    value_formatter=lambda value: f"{value:,.0f}",
) -> None:
    left, right, bottom, top = 44, 10, 34, 18
    plot_x, plot_y = x + left, y + bottom
    plot_w, plot_h = w - left - right, h - bottom - top
    max_value = max(value for _, values, _ in series for value in values) * 1.12
    for tick in range(5):
        value = max_value * tick / 4
        py = plot_y + plot_h * tick / 4
        c.setStrokeColor(LINE)
        c.setLineWidth(0.5)
        c.line(plot_x, py, plot_x + plot_w, py)
        draw_text(c, value_formatter(value), plot_x - 5, py - 2, 6.3, MUTED, align="right")
    group_w = plot_w / len(labels)
    bar_w = group_w * 0.65 / len(series)
    for category_idx, label in enumerate(labels):
        start_x = plot_x + category_idx * group_w + group_w * 0.175
        for series_idx, (_, values, color) in enumerate(series):
            value = values[category_idx]
            bh = plot_h * value / max_value
            bx = start_x + series_idx * bar_w
            c.setFillColor(color)
            c.rect(bx, plot_y, bar_w * 0.86, bh, fill=1, stroke=0)
        draw_text(c, label, plot_x + category_idx * group_w + group_w / 2, y + 12, 6.2, MUTED, align="center")
    legend_x = x + 12
    for name, _, color in series:
        c.setFillColor(color)
        c.rect(legend_x, y + h - 10, 8, 8, fill=1, stroke=0)
        draw_text(c, name, legend_x + 12, y + h - 10, 7, MUTED)
        legend_x += 100


def data_table(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    row_h: float,
    headers: list[str],
    rows: list[list[str]],
    widths: list[float] | None = None,
    font_size: float = 7,
) -> None:
    widths = widths or [w / len(headers)] * len(headers)
    c.setFillColor(NAVY2)
    c.rect(x, y - row_h, w, row_h, fill=1, stroke=0)
    cursor = x
    for header_name, col_w in zip(headers, widths, strict=True):
        draw_text(c, header_name, cursor + 5, y - row_h + 6, font_size, WHITE, "DejaVu-Bold")
        cursor += col_w
    for row_idx, row in enumerate(rows):
        row_y = y - (row_idx + 2) * row_h
        c.setFillColor(WHITE if row_idx % 2 == 0 else LIGHT)
        c.rect(x, row_y, w, row_h, fill=1, stroke=0)
        cursor = x
        for value, col_w in zip(row, widths, strict=True):
            draw_text(c, str(value), cursor + 5, row_y + 6, font_size, TEXT)
            cursor += col_w
        c.setStrokeColor(LINE)
        c.line(x, row_y, x + w, row_y)


def callout(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    body: str,
    accent=BLUE,
    fill=PALE_BLUE,
) -> None:
    rounded_panel(c, x, y, w, h, fill=fill, stroke=accent)
    c.setFillColor(accent)
    c.rect(x, y, 5, h, fill=1, stroke=0)
    draw_text(c, title, x + 14, y + h - 22, 9, accent, "DejaVu-Bold")
    paragraph(c, body, x + 14, y + 10, w - 26, h - 38, 8, TEXT)


def load_data() -> dict[str, pd.DataFrame]:
    return {
        "monthly": pd.read_csv(DATA_DIR / "monthly_performance.csv"),
        "category": pd.read_csv(DATA_DIR / "category_performance.csv"),
        "sku": pd.read_csv(DATA_DIR / "sku_performance.csv"),
        "forecast": pd.read_csv(DATA_DIR / "forecast_results.csv", parse_dates=["WeekStart"]),
        "forecast_monthly": pd.read_csv(DATA_DIR / "forecast_monthly.csv"),
        "metrics": pd.read_csv(DATA_DIR / "model_comparison.csv"),
        "backtest": pd.read_csv(DATA_DIR / "forecast_backtest.csv", parse_dates=["WeekStart"]),
        "inventory": pd.read_csv(DATA_DIR / "fact_inventory_snapshot.csv", parse_dates=["WeekStart"]),
        "products": pd.read_csv(DATA_DIR / "dim_product.csv"),
        "replenishment": pd.read_csv(DATA_DIR / "replenishment_recommendations.csv"),
        "supplier": pd.read_csv(DATA_DIR / "supplier_scorecard.csv"),
        "scenario": pd.read_csv(DATA_DIR / "scenario_summary.csv"),
    }


def page_1(c: canvas.Canvas, d: dict[str, pd.DataFrame]) -> None:
    header(c, "Executive Overview", "From historical demand to inventory decisions", 1)
    monthly, category = d["monthly"], d["category"]
    metrics = d["metrics"][d["metrics"]["ChampionFlag"]]
    base = d["scenario"].set_index("Scenario").loc["Base"]
    historical_revenue = monthly["NetRevenueTRY"].sum()
    kpi_y, card_h = PAGE_H - 164, 66
    card_w = (PAGE_W - 2 * MARGIN - 24) / 4
    kpi_card(c, MARGIN, kpi_y, card_w, card_h, "Historical revenue", money_m(historical_revenue), "2023-2025 actual")
    kpi_card(c, MARGIN + card_w + 8, kpi_y, card_w, card_h, "2026 forecast revenue", money_m(base["ForecastRevenueTRY"]), "Base scenario", CYAN)
    kpi_card(c, MARGIN + 2 * (card_w + 8), kpi_y, card_w, card_h, "Champion WAPE", pct(metrics["WAPE"].mean()), "60 SKU backtest", GREEN)
    kpi_card(c, MARGIN + 3 * (card_w + 8), kpi_y, card_w, card_h, "Inventory investment", money_m(base["RecommendedInvestmentTRY"]), f"{int(base['SKUsToOrder'])} SKUs to order", AMBER)

    chart_y, chart_h = 126, 236
    left_w = 560
    rounded_panel(c, MARGIN, chart_y, left_w, chart_h)
    panel_title(c, "Monthly Net Revenue | 2023-2025", MARGIN, chart_y + chart_h, left_w)
    line_chart(
        c,
        MARGIN + 8,
        chart_y + 10,
        left_w - 16,
        chart_h - 42,
        monthly["YearMonth"].tolist(),
        [("Revenue", monthly["NetRevenueTRY"].tolist(), BLUE)],
        y_formatter=lambda value: f"{value / 1_000_000:.0f}M",
        label_every=6,
    )
    right_x = MARGIN + left_w + 10
    right_w = PAGE_W - MARGIN - right_x
    rounded_panel(c, right_x, chart_y, right_w, chart_h)
    panel_title(c, "Historical Revenue by Category", right_x, chart_y + chart_h, right_w)
    bar_chart(
        c,
        right_x + 8,
        chart_y + 12,
        right_w - 16,
        chart_h - 46,
        category["Category"].tolist(),
        category["NetRevenueTRY"].tolist(),
        color=CYAN,
        value_formatter=lambda value: f"{value / 1_000_000:.0f}M",
    )
    callout(
        c,
        MARGIN,
        42,
        PAGE_W - 2 * MARGIN,
        70,
        "Executive decision",
        f"The portfolio generated {money_m(historical_revenue)} in synthetic historical revenue. The base plan forecasts {money_m(base['ForecastRevenueTRY'])} for 2026 and requires {money_m(base['RecommendedInvestmentTRY'])}. Immediate replenishment is concentrated in {int(base['SKUsToOrder'])} SKUs, while the champion model portfolio averages {pct(metrics['WAPE'].mean())} WAPE.",
    )


def page_2(c: canvas.Canvas, d: dict[str, pd.DataFrame]) -> None:
    header(c, "Demand History & Fulfillment", "Where demand was captured and where it was lost", 2)
    monthly, category = d["monthly"], d["category"]
    total_demand = monthly["EstimatedDemandUnits"].sum()
    units_sold = monthly["UnitsSold"].sum()
    lost_sales = monthly["LostSalesUnits"].sum()
    fill_rate = units_sold / total_demand
    card_w = (PAGE_W - 2 * MARGIN - 16) / 3
    kpi_card(c, MARGIN, PAGE_H - 162, card_w, 64, "Estimated demand", f"{total_demand:,.0f} units", "Uncensored demand proxy")
    kpi_card(c, MARGIN + card_w + 8, PAGE_H - 162, card_w, 64, "Demand fulfillment", pct(fill_rate), f"{units_sold:,.0f} units sold", GREEN)
    kpi_card(c, MARGIN + 2 * (card_w + 8), PAGE_H - 162, card_w, 64, "Lost sales", f"{lost_sales:,.0f} units", pct(lost_sales / total_demand) + " of demand", RED)
    rounded_panel(c, MARGIN, 160, 600, 210)
    panel_title(c, "Demand, Units Sold, and Lost Sales", MARGIN, 370, 600)
    grouped_bars(
        c,
        MARGIN + 8,
        170,
        584,
        164,
        monthly["YearMonth"].tolist()[::3],
        [
            ("Demand", monthly["EstimatedDemandUnits"].tolist()[::3], CYAN),
            ("Sold", monthly["UnitsSold"].tolist()[::3], BLUE),
            ("Lost", monthly["LostSalesUnits"].tolist()[::3], RED),
        ],
        value_formatter=lambda value: f"{value / 1000:.0f}K",
    )
    table_x, table_y, table_w = 650, 370, PAGE_W - 650 - MARGIN
    rounded_panel(c, table_x, 160, table_w, 210)
    panel_title(c, "Category Fulfillment", table_x, table_y, table_w)
    rows = [
        [
            row.Category,
            f"{row.EstimatedDemandUnits:,.0f}",
            f"{row.UnitsSold:,.0f}",
            pct(row.DemandFulfillmentRate),
        ]
        for row in category.sort_values("DemandFulfillmentRate").itertuples()
    ]
    data_table(
        c,
        table_x + 10,
        table_y - 34,
        table_w - 20,
        24,
        ["Category", "Demand", "Sold", "Fill rate"],
        rows,
        [80, 60, 60, 58],
        6.6,
    )
    callout(c, MARGIN, 45, 450, 98, "Commercial opportunity", f"Estimated lost demand equals {lost_sales:,.0f} units. Outerwear and seasonal categories exhibit the largest fulfillment pressure, making lead-time planning and safety-stock calibration the highest-impact levers.", RED, PALE_RED)
    callout(c, 500, 45, PAGE_W - 500 - MARGIN, 98, "Interpretation", "Demand is intentionally modeled as units sold plus simulated lost sales. This reduces stockout censoring and gives the forecasting engine a stronger estimate of true customer demand rather than only fulfilled orders.", BLUE, PALE_BLUE)


def page_3(c: canvas.Canvas, d: dict[str, pd.DataFrame]) -> None:
    header(c, "2026 Demand Forecast", "Weekly SKU forecasts aggregated for executive planning", 3)
    forecast = d["forecast"].copy()
    monthly_total = (
        forecast.assign(YearMonth=forecast["WeekStart"].dt.strftime("%Y-%m"))
        .groupby("YearMonth", as_index=False)
        .agg(
            ForecastUnits=("ForecastUnits", "sum"),
            Lower80Units=("Lower80Units", "sum"),
            Upper80Units=("Upper80Units", "sum"),
            ForecastRevenueTRY=("ForecastRevenueTRY", "sum"),
        )
    )
    category_total = (
        forecast.groupby("Category", as_index=False)
        .agg(ForecastUnits=("ForecastUnits", "sum"), ForecastRevenueTRY=("ForecastRevenueTRY", "sum"))
        .sort_values("ForecastRevenueTRY", ascending=False)
    )
    total_units = monthly_total["ForecastUnits"].sum()
    total_revenue = monthly_total["ForecastRevenueTRY"].sum()
    interval_width = (monthly_total["Upper80Units"].sum() - monthly_total["Lower80Units"].sum())
    card_w = (PAGE_W - 2 * MARGIN - 16) / 3
    kpi_card(c, MARGIN, PAGE_H - 162, card_w, 64, "Forecast units", f"{total_units:,.0f}", "52 weeks | 60 SKUs")
    kpi_card(c, MARGIN + card_w + 8, PAGE_H - 162, card_w, 64, "Forecast revenue", money_m(total_revenue), "Expected selling price", CYAN)
    kpi_card(c, MARGIN + 2 * (card_w + 8), PAGE_H - 162, card_w, 64, "80% interval span", f"{interval_width:,.0f} units", "Portfolio uncertainty", PURPLE)
    rounded_panel(c, MARGIN, 156, 610, 214)
    panel_title(c, "Monthly Forecast with 80% Prediction Interval", MARGIN, 370, 610)
    line_chart(
        c,
        MARGIN + 8,
        166,
        594,
        170,
        monthly_total["YearMonth"].tolist(),
        [("Forecast", monthly_total["ForecastUnits"].tolist(), BLUE)],
        y_formatter=lambda value: f"{value / 1000:.0f}K",
        label_every=1,
        fill_band=(
            monthly_total["Lower80Units"].tolist(),
            monthly_total["Upper80Units"].tolist(),
            PALE_BLUE,
        ),
    )
    right_x = 652
    right_w = PAGE_W - right_x - MARGIN
    rounded_panel(c, right_x, 156, right_w, 214)
    panel_title(c, "2026 Forecast Revenue by Category", right_x, 370, right_w)
    bar_chart(
        c,
        right_x + 6,
        166,
        right_w - 12,
        170,
        category_total["Category"].tolist(),
        category_total["ForecastRevenueTRY"].tolist(),
        color=CYAN,
        value_formatter=lambda value: f"{value / 1_000_000:.0f}M",
    )
    callout(c, MARGIN, 45, 446, 84, "Planning signal", f"The 2026 baseline is {total_units:,.0f} units and {money_m(total_revenue)} revenue. Forecast uncertainty is explicitly carried into the safety-stock calculation through SKU-level residual standard deviations.", BLUE, PALE_BLUE)
    callout(c, 490, 45, PAGE_W - 490 - MARGIN, 84, "How to use", "Use the point forecast for purchasing and capacity planning; use the 80% interval to stress-test inventory investment, supplier capacity, and campaign exposure before committing budget.", PURPLE, HexColor("#F1ECFF"))


def page_4(c: canvas.Canvas, d: dict[str, pd.DataFrame]) -> None:
    header(c, "Forecast Model Performance", "Backtest governance and champion model selection", 4)
    metrics = d["metrics"]
    champions = metrics[metrics["ChampionFlag"]]
    model_summary = (
        metrics.groupby("Model", as_index=False)
        .agg(AverageWAPE=("WAPE", "mean"), AverageMAE=("MAE", "mean"))
        .sort_values("AverageWAPE")
    )
    champion_counts = champions["Model"].value_counts()
    representative = champions.sort_values("WAPE").iloc[len(champions) // 2]["SKU"]
    champion_model = champions.set_index("SKU").loc[representative, "Model"]
    backtest = d["backtest"]
    rep_test = backtest[(backtest["SKU"] == representative) & (backtest["Model"] == champion_model)].sort_values("WeekStart")
    card_w = (PAGE_W - 2 * MARGIN - 16) / 3
    kpi_card(c, MARGIN, PAGE_H - 162, card_w, 64, "Average champion WAPE", pct(champions["WAPE"].mean()), "Lower is better", GREEN)
    kpi_card(c, MARGIN + card_w + 8, PAGE_H - 162, card_w, 64, "Gradient Boosting winners", f"{int(champion_counts.get('Gradient Boosting', 0))} SKUs", "Portfolio majority", BLUE)
    kpi_card(c, MARGIN + 2 * (card_w + 8), PAGE_H - 162, card_w, 64, "Backtest horizon", "13 weeks", "MAE, RMSE, WAPE, Bias", PURPLE)
    rounded_panel(c, MARGIN, 158, 460, 212)
    panel_title(c, "Model Comparison | Average WAPE", MARGIN, 370, 460)
    bar_chart(
        c,
        MARGIN + 10,
        168,
        440,
        166,
        [name.replace("8-Week ", "8W ") for name in model_summary["Model"].tolist()],
        model_summary["AverageWAPE"].tolist(),
        color=BLUE,
        value_formatter=lambda value: pct(value),
    )
    chart_x = 506
    chart_w = PAGE_W - chart_x - MARGIN
    rounded_panel(c, chart_x, 158, chart_w, 212)
    panel_title(c, f"Representative SKU Backtest | {representative}", chart_x, 370, chart_w)
    line_chart(
        c,
        chart_x + 8,
        168,
        chart_w - 16,
        166,
        rep_test["WeekStart"].dt.strftime("%W").tolist(),
        [
            ("Actual", rep_test["ActualDemandUnits"].tolist(), NAVY),
            ("Champion", rep_test["PredictedDemandUnits"].tolist(), BLUE),
        ],
        y_formatter=lambda value: f"{value:.0f}",
        label_every=2,
    )
    table_rows = [
        [row.Model, pct(row.AverageWAPE), f"{row.AverageMAE:.1f}"]
        for row in model_summary.itertuples()
    ]
    data_table(c, MARGIN, 132, 460, 22, ["Model", "Avg WAPE", "Avg MAE"], table_rows, [240, 100, 100], 7)
    callout(c, 506, 44, PAGE_W - 506 - MARGIN, 86, "Governance rule", "Each SKU selects the model with the lowest WAPE on the most recent 13-week holdout. The champion label, residual variability, and bias are persisted so downstream inventory decisions remain auditable.", GREEN, PALE_GREEN)


def page_5(c: canvas.Canvas, d: dict[str, pd.DataFrame]) -> None:
    header(c, "Inventory Health", "Current coverage, action status, and stock exposure", 5)
    inventory = d["inventory"]
    products = d["products"]
    latest = inventory[inventory["WeekStart"] == inventory["WeekStart"].max()].merge(
        products[["SKU", "Category", "ProductName"]], on="SKU", how="left"
    )
    replenishment = d["replenishment"]
    action_counts = replenishment["Action"].value_counts()
    inventory_value = latest["InventoryValueTRY"].sum()
    avg_wos = replenishment["ProjectedWeeksOfSupply"].mean()
    stockout_skus = int(latest["StockoutFlag"].sum())
    card_w = (PAGE_W - 2 * MARGIN - 16) / 3
    kpi_card(c, MARGIN, PAGE_H - 162, card_w, 64, "Current inventory value", money_m(inventory_value), "Latest weekly snapshot")
    kpi_card(c, MARGIN + card_w + 8, PAGE_H - 162, card_w, 64, "Average weeks of supply", f"{avg_wos:.1f} weeks", "Base forecast", CYAN)
    kpi_card(c, MARGIN + 2 * (card_w + 8), PAGE_H - 162, card_w, 64, "Latest stockout SKUs", str(stockout_skus), "Simulated snapshot", RED)
    category_wos = (
        replenishment.groupby("Category", as_index=False)["ProjectedWeeksOfSupply"].mean()
        .sort_values("ProjectedWeeksOfSupply")
    )
    rounded_panel(c, MARGIN, 158, 520, 212)
    panel_title(c, "Projected Weeks of Supply by Category", MARGIN, 370, 520)
    bar_chart(
        c,
        MARGIN + 10,
        168,
        500,
        166,
        category_wos["Category"].tolist(),
        category_wos["ProjectedWeeksOfSupply"].tolist(),
        color=CYAN,
        value_formatter=lambda value: f"{value:.1f}",
    )
    action_x = 566
    action_w = PAGE_W - action_x - MARGIN
    rounded_panel(c, action_x, 158, action_w, 212)
    panel_title(c, "SKU Action Distribution", action_x, 370, action_w)
    labels = ["ORDER NOW", "MONITOR", "HEALTHY"]
    bar_chart(
        c,
        action_x + 8,
        168,
        action_w - 16,
        166,
        labels,
        [int(action_counts.get(label, 0)) for label in labels],
        color=BLUE,
        value_formatter=lambda value: f"{value:.0f}",
    )
    low_wos = replenishment.nsmallest(6, "ProjectedWeeksOfSupply")
    rows = [
        [
            row.SKU,
            row.ProductName[:22],
            row.Category,
            f"{row.ProjectedWeeksOfSupply:.1f}",
            row.Action,
        ]
        for row in low_wos.itertuples()
    ]
    data_table(
        c,
        MARGIN,
        154,
        PAGE_W - 2 * MARGIN,
        16,
        ["SKU", "Product", "Category", "WOS", "Action"],
        rows,
        [85, 270, 130, 70, 130],
        7,
    )


def page_6(c: canvas.Canvas, d: dict[str, pd.DataFrame]) -> None:
    header(c, "Replenishment Plan", "Pack-rounded purchase recommendations under the base scenario", 6)
    replenishment = d["replenishment"].copy()
    order_now = replenishment[replenishment["Action"] == "ORDER NOW"].sort_values(
        "RecommendedInvestmentTRY", ascending=False
    )
    investment = replenishment["RecommendedInvestmentTRY"].sum()
    order_units = replenishment["RecommendedOrderQty"].sum()
    suppliers = order_now["SupplierName"].nunique()
    card_w = (PAGE_W - 2 * MARGIN - 16) / 3
    kpi_card(c, MARGIN, PAGE_H - 162, card_w, 64, "Recommended investment", money_m(investment), "All base-scenario SKUs", AMBER)
    kpi_card(c, MARGIN + card_w + 8, PAGE_H - 162, card_w, 64, "Recommended order units", f"{order_units:,.0f}", "MOQ and case-pack compliant", BLUE)
    kpi_card(c, MARGIN + 2 * (card_w + 8), PAGE_H - 162, card_w, 64, "Immediate suppliers", str(suppliers), "Required for ORDER NOW SKUs", CYAN)
    rounded_panel(c, MARGIN, 160, 500, 210)
    panel_title(c, "Top Immediate Order Investments", MARGIN, 370, 500)
    top = order_now.head(8)
    bar_chart(
        c,
        MARGIN + 8,
        170,
        484,
        164,
        top["SKU"].tolist(),
        top["RecommendedInvestmentTRY"].tolist(),
        color=AMBER,
        value_formatter=lambda value: f"{value / 1000:.0f}K",
        horizontal=True,
    )
    table_x = 548
    table_w = PAGE_W - table_x - MARGIN
    rounded_panel(c, table_x, 160, table_w, 210)
    panel_title(c, "Immediate Purchase Orders", table_x, 370, table_w)
    rows = [
        [
            row.SKU,
            row.Category,
            f"{row.RecommendedOrderQty:,.0f}",
            money_m(row.RecommendedInvestmentTRY).replace("M", ""),
            f"{row.ProjectedWeeksOfSupply:.1f}",
        ]
        for row in top.itertuples()
    ]
    data_table(
        c,
        table_x + 8,
        336,
        table_w - 16,
        19,
        ["SKU", "Category", "Qty", "TRY M", "WOS"],
        rows,
        [60, 100, 55, 75, 60],
        6.5,
    )
    callout(c, MARGIN, 46, 438, 106, "Ordering logic", "Recommended quantity is the greater of cycle-stock need, EOQ, and MOQ, then rounded to the product case pack. Inventory position includes both current on-hand stock and open purchase orders.", BLUE, PALE_BLUE)
    callout(c, 480, 46, PAGE_W - 480 - MARGIN, 106, "Operational control", "Review ORDER NOW items first, validate supplier capacity, confirm promotion timing, then release purchase orders. MONITOR items should be reassessed weekly as demand and inbound dates update.", AMBER, PALE_AMBER)


def page_7(c: canvas.Canvas, d: dict[str, pd.DataFrame]) -> None:
    header(c, "Category & SKU Portfolio", "Revenue, margin, fulfillment, and concentration", 7)
    category = d["category"].sort_values("NetRevenueTRY", ascending=False)
    sku = d["sku"].sort_values("NetRevenueTRY", ascending=False)
    top5_share = sku.head(5)["NetRevenueTRY"].sum() / sku["NetRevenueTRY"].sum()
    avg_margin = category["GrossProfitTRY"].sum() / category["NetRevenueTRY"].sum()
    best_category = category.iloc[0]
    card_w = (PAGE_W - 2 * MARGIN - 16) / 3
    kpi_card(c, MARGIN, PAGE_H - 162, card_w, 64, "Top 5 SKU revenue share", pct(top5_share), "Concentration indicator", PURPLE)
    kpi_card(c, MARGIN + card_w + 8, PAGE_H - 162, card_w, 64, "Portfolio gross margin", pct(avg_margin), "Historical weighted margin", GREEN)
    kpi_card(c, MARGIN + 2 * (card_w + 8), PAGE_H - 162, card_w, 64, "Leading category", best_category["Category"], money_m(best_category["NetRevenueTRY"]), BLUE)
    rounded_panel(c, MARGIN, 158, 540, 212)
    panel_title(c, "Revenue and Gross Profit by Category", MARGIN, 370, 540)
    grouped_bars(
        c,
        MARGIN + 8,
        168,
        524,
        166,
        category["Category"].tolist(),
        [
            ("Revenue", category["NetRevenueTRY"].tolist(), BLUE),
            ("Gross Profit", category["GrossProfitTRY"].tolist(), GREEN),
        ],
        value_formatter=lambda value: f"{value / 1_000_000:.0f}M",
    )
    table_x = 586
    table_w = PAGE_W - table_x - MARGIN
    rounded_panel(c, table_x, 158, table_w, 212)
    panel_title(c, "Top Revenue SKUs", table_x, 370, table_w)
    rows = [
        [
            row.SKU,
            row.ProductName[:20],
            money_m(row.NetRevenueTRY),
            pct(row.GrossMarginPct),
        ]
        for row in sku.head(8).itertuples()
    ]
    data_table(
        c,
        table_x + 8,
        336,
        table_w - 16,
        19,
        ["SKU", "Product", "Revenue", "Margin"],
        rows,
        [60, 130, 80, 56],
        6.3,
    )
    callout(c, MARGIN, 48, PAGE_W - 2 * MARGIN, 98, "Portfolio implication", f"The top five SKUs contribute {pct(top5_share)} of historical revenue, indicating a diversified portfolio rather than a single-product dependency. Category margin and fulfillment should be reviewed together: high revenue with low fulfillment signals lost-sales opportunity; high stock with weak margin signals working-capital risk.", PURPLE, HexColor("#F1ECFF"))


def page_8(c: canvas.Canvas, d: dict[str, pd.DataFrame]) -> None:
    header(c, "Supplier Performance", "Lead-time reliability and purchasing exposure", 8)
    supplier = d["supplier"].sort_values("PurchaseValueTRY", ascending=False)
    weighted_on_time = np.average(
        supplier["OnTimeDeliveryRate"], weights=supplier["PurchaseOrders"]
    )
    avg_lead = np.average(
        supplier["AverageActualLeadTimeDays"], weights=supplier["PurchaseOrders"]
    )
    purchase_value = supplier["PurchaseValueTRY"].sum()
    card_w = (PAGE_W - 2 * MARGIN - 16) / 3
    kpi_card(c, MARGIN, PAGE_H - 162, card_w, 64, "Purchase value", money_m(purchase_value), "Historical simulated POs")
    kpi_card(c, MARGIN + card_w + 8, PAGE_H - 162, card_w, 64, "Weighted on-time rate", pct(weighted_on_time), "Delivery reliability", GREEN)
    kpi_card(c, MARGIN + 2 * (card_w + 8), PAGE_H - 162, card_w, 64, "Average actual lead time", f"{avg_lead:.1f} days", "PO-weighted", CYAN)
    rounded_panel(c, MARGIN, 160, 500, 210)
    panel_title(c, "Purchase Value by Supplier", MARGIN, 370, 500)
    bar_chart(
        c,
        MARGIN + 8,
        170,
        484,
        164,
        supplier["SupplierID"].tolist(),
        supplier["PurchaseValueTRY"].tolist(),
        color=BLUE,
        value_formatter=lambda value: f"{value / 1_000_000:.0f}M",
    )
    table_x = 548
    table_w = PAGE_W - table_x - MARGIN
    rounded_panel(c, table_x, 160, table_w, 210)
    panel_title(c, "Supplier Reliability Matrix", table_x, 370, table_w)
    rows = [
        [
            row.SupplierID,
            f"{int(row.PurchaseOrders)}",
            f"{row.AverageActualLeadTimeDays:.1f}",
            pct(row.OnTimeDeliveryRate),
            money_m(row.PurchaseValueTRY),
        ]
        for row in supplier.itertuples()
    ]
    data_table(
        c,
        table_x + 8,
        336,
        table_w - 16,
        19,
        ["Supplier", "POs", "Lead", "On-time", "Value"],
        rows,
        [80, 55, 60, 75, 90],
        6.7,
    )
    callout(c, MARGIN, 46, 440, 104, "Supplier risk", "Service-level protection depends on lead-time reliability. The Resilience scenario adds 14 days to supplier lead time, translating delivery uncertainty into higher safety stock and a larger capital requirement.", RED, PALE_RED)
    callout(c, 486, 46, PAGE_W - 486 - MARGIN, 104, "Procurement action", "Use on-time delivery, purchase exposure, and SKU criticality together when allocating supplier capacity. High-exposure suppliers with weaker reliability deserve earlier order release or secondary-source qualification.", BLUE, PALE_BLUE)


def page_9(c: canvas.Canvas, d: dict[str, pd.DataFrame]) -> None:
    header(c, "Scenario Analysis", "Trade-offs across Lean, Base, Growth, and Resilience plans", 9)
    scenario = d["scenario"].set_index("Scenario").loc[["Lean", "Base", "Growth", "Resilience"]].reset_index()
    base = scenario.set_index("Scenario").loc["Base"]
    card_w = (PAGE_W - 2 * MARGIN - 16) / 3
    growth = scenario.set_index("Scenario").loc["Growth"]
    resilience = scenario.set_index("Scenario").loc["Resilience"]
    kpi_card(c, MARGIN, PAGE_H - 162, card_w, 64, "Base investment", money_m(base["RecommendedInvestmentTRY"]), f"{int(base['SKUsToOrder'])} SKUs to order", BLUE)
    kpi_card(c, MARGIN + card_w + 8, PAGE_H - 162, card_w, 64, "Growth investment uplift", pct(growth["RecommendedInvestmentTRY"] / base["RecommendedInvestmentTRY"] - 1), money_m(growth["RecommendedInvestmentTRY"]), GREEN)
    kpi_card(c, MARGIN + 2 * (card_w + 8), PAGE_H - 162, card_w, 64, "Resilience premium", money_m(resilience["RecommendedInvestmentTRY"] - base["RecommendedInvestmentTRY"]), "14-day lead-time shock", RED)
    rounded_panel(c, MARGIN, 160, 480, 210)
    panel_title(c, "Forecast Revenue by Scenario", MARGIN, 370, 480)
    bar_chart(
        c,
        MARGIN + 8,
        170,
        464,
        164,
        scenario["Scenario"].tolist(),
        scenario["ForecastRevenueTRY"].tolist(),
        color=BLUE,
        value_formatter=lambda value: f"{value / 1_000_000:.0f}M",
    )
    second_x = 520
    second_w = PAGE_W - second_x - MARGIN
    rounded_panel(c, second_x, 160, second_w, 210)
    panel_title(c, "Inventory Investment by Scenario", second_x, 370, second_w)
    bar_chart(
        c,
        second_x + 8,
        170,
        second_w - 16,
        164,
        scenario["Scenario"].tolist(),
        scenario["RecommendedInvestmentTRY"].tolist(),
        color=AMBER,
        value_formatter=lambda value: f"{value / 1_000_000:.1f}M",
    )
    rows = [
        [
            row.Scenario,
            f"{row.ForecastUnits:,.0f}",
            money_m(row.RecommendedInvestmentTRY),
            f"{int(row.SKUsToOrder)}",
            f"{row.AverageWeeksOfSupply:.1f}",
        ]
        for row in scenario.itertuples()
    ]
    data_table(
        c,
        MARGIN,
        158,
        PAGE_W - 2 * MARGIN,
        12,
        ["Scenario", "Forecast Units", "Investment", "SKUs to Order", "Avg WOS"],
        rows,
        [150, 140, 140, 140, 120],
        6.2,
    )
    callout(c, MARGIN, 32, PAGE_W - 2 * MARGIN, 62, "Decision recommendation", "Use Base as the operating plan, Growth as the upside budget request, and Resilience only when supplier-disruption signals emerge.", GREEN, PALE_GREEN)


def page_10(c: canvas.Canvas, d: dict[str, pd.DataFrame]) -> None:
    header(c, "Executive Recommendations & Roadmap", "Turning the analytical model into a repeatable planning process", 10)
    x_positions = [MARGIN, 332, 632]
    widths = [280, 280, PAGE_W - 632 - MARGIN]
    titles = ["0-30 DAYS", "31-60 DAYS", "61-90 DAYS"]
    bodies = [
        "<b>Release immediate POs</b><br/>Validate the 10 ORDER NOW SKUs, supplier capacity, case packs, and promotion dates.<br/><br/><b>Protect critical stock</b><br/>Prioritize high-revenue SKUs with low projected weeks of supply.",
        "<b>Operationalize forecast review</b><br/>Refresh actual demand weekly, rerun the champion model, and compare bias by category.<br/><br/><b>Improve supplier controls</b><br/>Track on-time rate and actual lead-time variance by supplier.",
        "<b>Move to exception-based planning</b><br/>Automate alerts for reorder-point breaches, high WAPE, and budget overruns.<br/><br/><b>Govern scenarios</b><br/>Approve Base, Growth, or Resilience plans through a monthly S&OP cadence.",
    ]
    for x, w, title, body in zip(x_positions, widths, titles, bodies, strict=True):
        rounded_panel(c, x, 284, w, 166, WHITE, LINE)
        c.setFillColor(BLUE if title != "61-90 DAYS" else GREEN)
        c.roundRect(x, 420, w, 30, 8, fill=1, stroke=0)
        draw_text(c, title, x + 14, 430, 9, WHITE, "DejaVu-Bold")
        paragraph(c, body, x + 14, 298, w - 28, 112, 8.2, TEXT)

    rounded_panel(c, MARGIN, 128, PAGE_W - 2 * MARGIN, 130, LIGHT, LINE)
    draw_text(c, "END-TO-END ANALYTICS ARCHITECTURE", MARGIN + 16, 234, 9, NAVY, "DejaVu-Bold")
    steps = [
        ("Synthetic Data", "3 years"),
        ("SQL Model", "13 tables"),
        ("Python Forecast", "3 models"),
        ("Inventory Engine", "4 scenarios"),
        ("BI Delivery", "Power BI + Excel"),
    ]
    box_w = 150
    gap = (PAGE_W - 2 * MARGIN - 32 - len(steps) * box_w) / (len(steps) - 1)
    start_x = MARGIN + 16
    for idx, (title, note) in enumerate(steps):
        bx = start_x + idx * (box_w + gap)
        rounded_panel(c, bx, 154, box_w, 54, WHITE, BLUE)
        draw_text(c, title, bx + box_w / 2, 184, 8, NAVY, "DejaVu-Bold", "center")
        draw_text(c, note, bx + box_w / 2, 166, 7, MUTED, align="center")
        if idx < len(steps) - 1:
            c.setStrokeColor(CYAN)
            c.setLineWidth(2)
            c.line(bx + box_w + 4, 181, bx + box_w + gap - 4, 181)
    callout(c, MARGIN, 42, PAGE_W - 2 * MARGIN, 66, "Portfolio value", "This project demonstrates statistical forecasting, machine learning, SQL engineering, inventory mathematics, executive BI design, scenario planning, testing, and professional documentation within one coherent business decision system.", PURPLE, HexColor("#F1ECFF"))


def build_report() -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_data()
    c = canvas.Canvas(str(OUTPUT_PATH), pagesize=(PAGE_W, PAGE_H), pageCompression=1)
    c.setTitle("E-Commerce Demand Forecasting & Inventory Optimization Platform")
    c.setAuthor("Murat Miraç Gedik")
    c.setSubject("Professional portfolio executive report")
    pages = [page_1, page_2, page_3, page_4, page_5, page_6, page_7, page_8, page_9, page_10]
    for page in pages:
        page(c, data)
        c.showPage()
    c.save()
    return OUTPUT_PATH


if __name__ == "__main__":
    print(build_report())
