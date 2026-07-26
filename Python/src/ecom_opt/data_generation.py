from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import (
    CATEGORIES,
    CHANNELS,
    DATA_DIR,
    HISTORY_END,
    HISTORY_START,
    RANDOM_SEED,
)


@dataclass(frozen=True)
class CategoryProfile:
    base_demand: float
    price_low: float
    price_high: float
    cost_ratio: float
    seasonality: str


CATEGORY_PROFILES = {
    "Dresses": CategoryProfile(56, 1_200, 3_200, 0.39, "summer"),
    "Knitwear": CategoryProfile(44, 950, 2_500, 0.41, "winter"),
    "Outerwear": CategoryProfile(30, 1_800, 5_200, 0.45, "winter"),
    "Tops": CategoryProfile(70, 650, 1_900, 0.36, "summer"),
    "Bottoms": CategoryProfile(48, 900, 2_400, 0.40, "steady"),
    "Accessories": CategoryProfile(62, 450, 1_600, 0.34, "holiday"),
}

PRODUCT_WORDS = {
    "Dresses": ("Satin", "Midi", "Wrap", "Linen", "Evening", "Ribbed", "Floral", "Minimal", "Pleated", "Signature"),
    "Knitwear": ("Merino", "Cable", "Soft", "Ribbed", "Mockneck", "Cardigan", "Fine", "Oversized", "Crew", "Essential"),
    "Outerwear": ("Trench", "Wool", "Puffer", "Tailored", "Cropped", "Belted", "Quilted", "Classic", "Urban", "Storm"),
    "Tops": ("Silk", "Cotton", "Linen", "Draped", "Bodysuit", "Oxford", "Essential", "Relaxed", "Studio", "Signature"),
    "Bottoms": ("Tailored", "Wide-Leg", "Straight", "Satin", "Pleated", "Cargo", "Cropped", "Relaxed", "Classic", "Studio"),
    "Accessories": ("Leather", "Silk", "Chain", "Minimal", "Signature", "Structured", "Everyday", "Statement", "Classic", "Luxe"),
}

SUPPLIER_NAMES = (
    "Anatolia Textiles",
    "Marmara Apparel",
    "Aegean Atelier",
    "Bosporus Accessories",
    "Central Knitworks",
    "Thrace Manufacturing",
    "Istanbul Leather",
    "Mediterranean Fashion Supply",
)

CHANNEL_SHARES = {
    "Website": 0.56,
    "Marketplace": 0.29,
    "Social Shop": 0.15,
}


def _ensure_dirs() -> None:
    for path in (DATA_DIR,):
        path.mkdir(parents=True, exist_ok=True)


def _seasonality(category: str, week_of_year: int, month: int) -> float:
    profile = CATEGORY_PROFILES[category]
    angle = 2 * math.pi * (week_of_year - 1) / 52.0
    if profile.seasonality == "summer":
        seasonal = 1.0 + 0.28 * math.sin(angle - math.pi / 2)
    elif profile.seasonality == "winter":
        seasonal = 1.0 + 0.34 * math.cos(angle)
    elif profile.seasonality == "holiday":
        seasonal = 1.0 + 0.12 * math.cos(angle)
        if month in (11, 12):
            seasonal *= 1.30
    else:
        seasonal = 1.0 + 0.08 * math.sin(angle)
    return max(0.58, seasonal)


def _campaign_for(week: pd.Timestamp, category: str) -> tuple[str, float]:
    iso_week = int(week.isocalendar().week)
    month = week.month
    if iso_week in (2, 3):
        return "Winter Edit", 0.18 if category in ("Knitwear", "Outerwear") else 0.10
    if month == 3 and iso_week % 2 == 0:
        return "Spring Launch", 0.12
    if month in (6, 7) and iso_week % 3 == 0:
        return "Summer Selects", 0.20 if category in ("Dresses", "Tops") else 0.12
    if month == 9 and iso_week % 2 == 1:
        return "New Season", 0.10
    if iso_week == 45:
        return "Singles Week", 0.18
    if iso_week in (47, 48):
        return "Black Friday", 0.28
    if month == 12 and iso_week >= 50:
        return "Holiday Gifting", 0.15
    return "Always On", 0.00


def build_suppliers(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for idx, name in enumerate(SUPPLIER_NAMES, start=1):
        lead_time = int(rng.choice([7, 10, 14, 18, 21, 28, 35]))
        rows.append(
            {
                "SupplierID": f"SUP-{idx:03d}",
                "SupplierName": name,
                "Country": "Türkiye",
                "Region": rng.choice(["Istanbul", "Marmara", "Aegean", "Central Anatolia"]),
                "StandardLeadTimeDays": lead_time,
                "OnTimeDeliveryRate": round(float(rng.uniform(0.84, 0.97)), 4),
                "QualityAcceptanceRate": round(float(rng.uniform(0.965, 0.997)), 4),
                "OrderCostTRY": int(rng.integers(1_100, 3_100)),
                "PaymentTermsDays": int(rng.choice([15, 30, 45, 60])),
            }
        )
    return pd.DataFrame(rows)


def build_products(rng: np.random.Generator, suppliers: pd.DataFrame) -> pd.DataFrame:
    rows = []
    supplier_ids = suppliers["SupplierID"].tolist()
    for category_index, category in enumerate(CATEGORIES, start=1):
        profile = CATEGORY_PROFILES[category]
        for product_index in range(1, 11):
            sku = f"{category[:3].upper()}-{product_index:03d}"
            list_price = round(float(rng.uniform(profile.price_low, profile.price_high)) / 10) * 10
            unit_cost = round(list_price * float(rng.normal(profile.cost_ratio, 0.025)), 2)
            case_pack = int(rng.choice([4, 6, 8, 10, 12]))
            moq = int(case_pack * rng.choice([3, 4, 5, 6]))
            service = float(rng.choice([0.93, 0.95, 0.97, 0.98], p=[0.10, 0.38, 0.38, 0.14]))
            supplier_id = supplier_ids[(category_index * 2 + product_index) % len(supplier_ids)]
            supplier_lead = int(
                suppliers.loc[suppliers["SupplierID"] == supplier_id, "StandardLeadTimeDays"].iloc[0]
            )
            rows.append(
                {
                    "SKU": sku,
                    "ProductName": f"{PRODUCT_WORDS[category][product_index - 1]} {category[:-1] if category.endswith('s') else category}",
                    "Category": category,
                    "Segment": rng.choice(["Core", "Premium", "Trend"], p=[0.48, 0.27, 0.25]),
                    "Collection": rng.choice(["Permanent", "Spring/Summer", "Autumn/Winter"], p=[0.35, 0.33, 0.32]),
                    "SupplierID": supplier_id,
                    "UnitCostTRY": unit_cost,
                    "ListPriceTRY": list_price,
                    "GrossMarginPct": round(1 - unit_cost / list_price, 4),
                    "LeadTimeDays": supplier_lead,
                    "MOQ": moq,
                    "CasePack": case_pack,
                    "TargetServiceLevel": service,
                    "BaseWeeklyDemand": round(profile.base_demand * float(rng.uniform(0.68, 1.34)), 2),
                    "LaunchDate": pd.Timestamp("2022-01-03") + pd.Timedelta(days=int(rng.integers(0, 660))),
                    "LifecycleStage": rng.choice(["Growth", "Mature", "Core"], p=[0.25, 0.40, 0.35]),
                }
            )
    return pd.DataFrame(rows)


def build_calendar() -> pd.DataFrame:
    history_weeks = pd.date_range(HISTORY_START, HISTORY_END, freq="W-MON")
    forecast_weeks = pd.date_range(history_weeks[-1] + pd.Timedelta(days=7), periods=52, freq="W-MON")
    weeks = history_weeks.append(forecast_weeks)
    rows = []
    for idx, week in enumerate(weeks):
        iso = week.isocalendar()
        rows.append(
            {
                "WeekStart": week,
                "Year": week.year,
                "Quarter": f"Q{week.quarter}",
                "MonthNo": week.month,
                "Month": week.strftime("%B"),
                "YearMonth": week.strftime("%Y-%m"),
                "ISOWeek": int(iso.week),
                "WeekLabel": f"{int(iso.year)}-W{int(iso.week):02d}",
                "WeekIndex": idx + 1,
                "IsForecast": week > pd.Timestamp(HISTORY_END),
            }
        )
    return pd.DataFrame(rows)


def build_promotions(calendar: pd.DataFrame) -> pd.DataFrame:
    rows = []
    history = calendar[~calendar["IsForecast"]]
    for _, week_row in history.iterrows():
        week = pd.Timestamp(week_row["WeekStart"])
        for category in CATEGORIES:
            campaign, discount = _campaign_for(week, category)
            if discount > 0:
                rows.append(
                    {
                        "PromotionID": f"PROMO-{week.strftime('%Y%m%d')}-{category[:3].upper()}",
                        "CampaignName": campaign,
                        "WeekStart": week,
                        "Category": category,
                        "DiscountPct": discount,
                        "MarketingSpendTRY": round(
                            18_000 * (1 + discount * 3) * (1.25 if campaign == "Black Friday" else 1),
                            2,
                        ),
                    }
                )
    return pd.DataFrame(rows)


def build_sales_inventory_and_orders(
    rng: np.random.Generator,
    products: pd.DataFrame,
    suppliers: pd.DataFrame,
    calendar: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    history_weeks = calendar.loc[~calendar["IsForecast"], "WeekStart"].tolist()
    supplier_lookup = suppliers.set_index("SupplierID").to_dict("index")
    sales_rows: list[dict] = []
    inventory_rows: list[dict] = []
    po_rows: list[dict] = []
    po_counter = 1

    for product_idx, product in products.reset_index(drop=True).iterrows():
        sku = product["SKU"]
        category = product["Category"]
        lead_time_weeks = max(1, math.ceil(int(product["LeadTimeDays"]) / 7))
        base_demand = float(product["BaseWeeklyDemand"])
        on_hand = int(round(base_demand * rng.uniform(8.0, 12.0)))
        pending_receipts: dict[int, list[tuple[str, int, pd.Timestamp]]] = defaultdict(list)

        for week_idx, week in enumerate(history_weeks):
            week = pd.Timestamp(week)
            beginning_on_hand = on_hand
            receipt_qty = 0
            received_po_ids = []
            for po_id, qty, order_date in pending_receipts.pop(week_idx, []):
                supplier = supplier_lookup[product["SupplierID"]]
                on_time = rng.random() < float(supplier["OnTimeDeliveryRate"])
                actual_qty = max(0, int(round(qty * rng.uniform(0.97, 1.0))))
                receipt_qty += actual_qty
                received_po_ids.append((po_id, actual_qty, order_date, on_time))
            on_hand += receipt_qty

            campaign, discount_pct = _campaign_for(week, category)
            trend = 1.0 + 0.00215 * week_idx
            seasonal = _seasonality(category, int(week.isocalendar().week), week.month)
            macro = 1.0 + 0.025 * math.sin(week_idx / 11.5) + 0.015 * math.cos(week_idx / 6.0)
            promo_uplift = 1.0 + discount_pct * (1.35 if category == "Outerwear" else 1.75)
            black_friday = 1.25 if campaign == "Black Friday" else 1.0
            noise = float(rng.lognormal(mean=-0.015, sigma=0.13))
            latent_demand = max(
                0,
                int(
                    rng.poisson(
                        base_demand * trend * seasonal * macro * promo_uplift * black_friday * noise
                    )
                ),
            )
            units_sold = min(latent_demand, on_hand)
            lost_sales = latent_demand - units_sold
            on_hand -= units_sold

            annualized = max(base_demand * 52, 1)
            weekly_std = max(2.0, base_demand * 0.24)
            safety_stock_reference = 1.65 * weekly_std * math.sqrt(lead_time_weeks)
            reorder_point_reference = math.ceil(base_demand * lead_time_weeks + safety_stock_reference)
            target_stock = math.ceil(base_demand * (lead_time_weeks + 8) + safety_stock_reference)
            on_order = sum(qty for receipts in pending_receipts.values() for _, qty, _ in receipts)
            reorder_triggered = on_hand + on_order <= reorder_point_reference

            if reorder_triggered:
                supplier = supplier_lookup[product["SupplierID"]]
                holding_cost = max(float(product["UnitCostTRY"]) * 0.24, 1)
                eoq = math.sqrt(2 * annualized * float(supplier["OrderCostTRY"]) / holding_cost)
                raw_qty = max(float(product["MOQ"]), target_stock - on_hand - on_order, eoq)
                case_pack = int(product["CasePack"])
                ordered_qty = int(math.ceil(raw_qty / case_pack) * case_pack)
                variability = int(rng.choice([-1, 0, 0, 0, 1], p=[0.05, 0.24, 0.42, 0.24, 0.05]))
                receipt_week_idx = min(len(history_weeks) - 1, week_idx + lead_time_weeks + variability)
                po_id = f"PO-{po_counter:06d}"
                po_counter += 1
                pending_receipts[receipt_week_idx].append((po_id, ordered_qty, week))
                expected_receipt = week + pd.Timedelta(days=int(product["LeadTimeDays"]))
                actual_receipt = pd.Timestamp(history_weeks[receipt_week_idx])
                po_rows.append(
                    {
                        "POID": po_id,
                        "OrderDate": week,
                        "ExpectedReceiptDate": expected_receipt,
                        "ActualReceiptDate": actual_receipt,
                        "SKU": sku,
                        "SupplierID": product["SupplierID"],
                        "OrderedQty": ordered_qty,
                        "ReceivedQty": np.nan,
                        "UnitCostTRY": float(product["UnitCostTRY"]),
                        "POValueTRY": round(ordered_qty * float(product["UnitCostTRY"]), 2),
                        "PlannedLeadTimeDays": int(product["LeadTimeDays"]),
                        "ActualLeadTimeDays": (actual_receipt - week).days,
                        "OnTimeFlag": actual_receipt <= expected_receipt + pd.Timedelta(days=3),
                        "Status": "Open" if actual_receipt > pd.Timestamp(HISTORY_END) else "Received",
                    }
                )

            channel_units = rng.multinomial(
                units_sold,
                [CHANNEL_SHARES[channel] for channel in CHANNELS],
            )
            for channel, channel_qty in zip(CHANNELS, channel_units, strict=True):
                if channel_qty == 0 and units_sold > 0:
                    continue
                channel_discount = min(
                    0.36,
                    max(0.0, discount_pct + (0.02 if channel == "Marketplace" else 0.0)),
                )
                selling_price = float(product["ListPriceTRY"]) * (1 - channel_discount)
                gross_sales = channel_qty * float(product["ListPriceTRY"])
                net_revenue = channel_qty * selling_price
                cogs = channel_qty * float(product["UnitCostTRY"])
                channel_share = channel_qty / units_sold if units_sold else CHANNEL_SHARES[channel]
                sales_rows.append(
                    {
                        "WeekStart": week,
                        "SKU": sku,
                        "Channel": channel,
                        "CampaignName": campaign,
                        "PromotionFlag": discount_pct > 0,
                        "DiscountPct": round(channel_discount, 4),
                        "UnitsSold": int(channel_qty),
                        "EstimatedDemandUnits": round(latent_demand * channel_share, 2),
                        "LostSalesUnits": round(lost_sales * channel_share, 2),
                        "GrossSalesTRY": round(gross_sales, 2),
                        "DiscountTRY": round(gross_sales - net_revenue, 2),
                        "NetRevenueTRY": round(net_revenue, 2),
                        "COGSTRY": round(cogs, 2),
                        "GrossProfitTRY": round(net_revenue - cogs, 2),
                        "AverageSellingPriceTRY": round(selling_price, 2),
                        "StockoutFlag": lost_sales > 0,
                    }
                )

            open_order_units = sum(
                qty for receipts in pending_receipts.values() for _, qty, _ in receipts
            )
            weeks_of_supply = on_hand / max(base_demand * trend, 1)
            inventory_rows.append(
                {
                    "WeekStart": week,
                    "SKU": sku,
                    "BeginningOnHand": beginning_on_hand,
                    "Receipts": receipt_qty,
                    "EstimatedDemandUnits": latent_demand,
                    "UnitsSold": units_sold,
                    "LostSalesUnits": lost_sales,
                    "EndingOnHand": on_hand,
                    "OnOrderUnits": open_order_units,
                    "InventoryValueTRY": round(on_hand * float(product["UnitCostTRY"]), 2),
                    "WeeksOfSupply": round(weeks_of_supply, 3),
                    "StockoutFlag": lost_sales > 0,
                    "ReorderPointReference": reorder_point_reference,
                    "ReorderTriggered": reorder_triggered,
                }
            )

    purchase_orders = pd.DataFrame(po_rows)
    if not purchase_orders.empty:
        received_lookup = (
            pd.DataFrame(inventory_rows)
            .groupby(["WeekStart", "SKU"], as_index=False)["Receipts"]
            .sum()
        )
        for idx, row in purchase_orders.iterrows():
            if row["Status"] == "Received":
                matching = received_lookup[
                    (received_lookup["WeekStart"] == row["ActualReceiptDate"])
                    & (received_lookup["SKU"] == row["SKU"])
                ]
                if not matching.empty:
                    purchase_orders.at[idx, "ReceivedQty"] = min(
                        row["OrderedQty"], int(matching["Receipts"].iloc[0])
                    )
    return pd.DataFrame(sales_rows), pd.DataFrame(inventory_rows), purchase_orders


def generate_all() -> dict[str, pd.DataFrame]:
    _ensure_dirs()
    rng = np.random.default_rng(RANDOM_SEED)
    suppliers = build_suppliers(rng)
    products = build_products(rng, suppliers)
    calendar = build_calendar()
    promotions = build_promotions(calendar)
    sales, inventory, purchase_orders = build_sales_inventory_and_orders(
        rng, products, suppliers, calendar
    )

    datasets = {
        "dim_calendar": calendar,
        "dim_product": products,
        "dim_supplier": suppliers,
        "fact_weekly_sales": sales,
        "fact_inventory_snapshot": inventory,
        "fact_purchase_orders": purchase_orders,
        "fact_promotions": promotions,
    }
    for name, frame in datasets.items():
        frame.to_csv(DATA_DIR / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    return datasets


if __name__ == "__main__":
    generated = generate_all()
    for dataset_name, dataset in generated.items():
        print(f"{dataset_name}: {len(dataset):,} rows")

