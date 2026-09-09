from __future__ import annotations

import math
from collections import deque

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from .config import DATA_DIR, FORECAST_START, FORECAST_WEEKS, RANDOM_SEED
from .data_generation import _campaign_for


FEATURE_COLUMNS = [
    "SKUCode",
    "CategoryCode",
    "WeekIndex",
    "WeekOfYearSin",
    "WeekOfYearCos",
    "Month",
    "PromoFlag",
    "DiscountPct",
    "Lag1",
    "Lag4",
    "Lag13",
    "Lag52",
    "Roll4",
    "Roll13",
]


def _validate_metric_inputs(
    actual: np.ndarray, predicted: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Validate demand vectors before computing model-selection metrics."""
    actual_values = np.asarray(actual, dtype=float)
    predicted_values = np.asarray(predicted, dtype=float)
    if actual_values.ndim != 1 or predicted_values.ndim != 1:
        raise ValueError("Forecast metric inputs must be one-dimensional")
    if actual_values.size == 0 or actual_values.shape != predicted_values.shape:
        raise ValueError("Actual and predicted demand must be non-empty and aligned")
    if not np.isfinite(actual_values).all() or not np.isfinite(predicted_values).all():
        raise ValueError("Forecast metric inputs must be finite")
    if (actual_values < 0).any() or (predicted_values < 0).any():
        raise ValueError("Demand values must be non-negative")
    return actual_values, predicted_values


def _wape(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual_values, predicted_values = _validate_metric_inputs(actual, predicted)
    denominator = max(float(actual_values.sum()), 1.0)
    return float(np.abs(actual_values - predicted_values).sum() / denominator)


def _bias(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual_values, predicted_values = _validate_metric_inputs(actual, predicted)
    denominator = max(float(actual_values.sum()), 1.0)
    return float((predicted_values - actual_values).sum() / denominator)


def _metric_row(sku: str, model: str, actual: np.ndarray, predicted: np.ndarray) -> dict:
    return {
        "SKU": sku,
        "Model": model,
        "MAE": round(float(mean_absolute_error(actual, predicted)), 4),
        "RMSE": round(float(math.sqrt(mean_squared_error(actual, predicted))), 4),
        "WAPE": round(_wape(actual, predicted), 6),
        "Bias": round(_bias(actual, predicted), 6),
    }


def _prepare_history(sales: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    history = (
        sales.groupby(["WeekStart", "SKU"], as_index=False)
        .agg(
            Demand=("EstimatedDemandUnits", "sum"),
            UnitsSold=("UnitsSold", "sum"),
            NetRevenueTRY=("NetRevenueTRY", "sum"),
            DiscountPct=("DiscountPct", "mean"),
            PromoFlag=("PromotionFlag", "max"),
        )
    )
    history["WeekStart"] = pd.to_datetime(history["WeekStart"])
    product_cols = products[["SKU", "Category", "ListPriceTRY"]].copy()
    history = history.merge(product_cols, on="SKU", how="left")
    history = history.sort_values(["SKU", "WeekStart"]).reset_index(drop=True)
    sku_map = {sku: idx for idx, sku in enumerate(sorted(history["SKU"].unique()))}
    category_map = {
        category: idx for idx, category in enumerate(sorted(history["Category"].unique()))
    }
    history["SKUCode"] = history["SKU"].map(sku_map)
    history["CategoryCode"] = history["Category"].map(category_map)
    history["WeekIndex"] = history.groupby("SKU").cumcount() + 1
    iso_week = history["WeekStart"].dt.isocalendar().week.astype(int)
    history["WeekOfYearSin"] = np.sin(2 * np.pi * iso_week / 52.0)
    history["WeekOfYearCos"] = np.cos(2 * np.pi * iso_week / 52.0)
    history["Month"] = history["WeekStart"].dt.month
    history["PromoFlag"] = history["PromoFlag"].astype(int)
    for lag in (1, 4, 13, 52):
        history[f"Lag{lag}"] = history.groupby("SKU")["Demand"].shift(lag)
    history["Roll4"] = (
        history.groupby("SKU")["Demand"]
        .shift(1)
        .rolling(4)
        .mean()
        .reset_index(level=0, drop=True)
    )
    history["Roll13"] = (
        history.groupby("SKU")["Demand"]
        .shift(1)
        .rolling(13)
        .mean()
        .reset_index(level=0, drop=True)
    )
    return history


def _train_ml(history: pd.DataFrame, test_weeks: int = 13):
    max_week = history["WeekIndex"].max()
    train = history[(history["WeekIndex"] <= max_week - test_weeks)].dropna(
        subset=FEATURE_COLUMNS
    )
    model = HistGradientBoostingRegressor(
        loss="squared_error",
        learning_rate=0.06,
        max_iter=240,
        max_leaf_nodes=24,
        l2_regularization=0.35,
        random_state=RANDOM_SEED,
    )
    model.fit(train[FEATURE_COLUMNS], train["Demand"])
    return model


def run_forecasting() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sales = pd.read_csv(DATA_DIR / "fact_weekly_sales.csv", parse_dates=["WeekStart"])
    products = pd.read_csv(DATA_DIR / "dim_product.csv", parse_dates=["LaunchDate"])
    history = _prepare_history(sales, products)
    ml_model = _train_ml(history)
    max_week = int(history["WeekIndex"].max())
    test_start = max_week - 12
    test = history[history["WeekIndex"] >= test_start].dropna(subset=FEATURE_COLUMNS).copy()
    test["MLPrediction"] = np.maximum(0, ml_model.predict(test[FEATURE_COLUMNS]))

    metrics = []
    backtest_rows = []
    for sku, sku_test in test.groupby("SKU", sort=True):
        sku_test = sku_test.sort_values("WeekStart")
        actual = sku_test["Demand"].to_numpy(dtype=float)
        predictions = {
            "Seasonal Naive": sku_test["Lag52"].to_numpy(dtype=float),
            "8-Week Moving Average": sku_test["Roll4"].to_numpy(dtype=float) * 0.35
            + sku_test["Roll13"].to_numpy(dtype=float) * 0.65,
            "Gradient Boosting": sku_test["MLPrediction"].to_numpy(dtype=float),
        }
        for model_name, predicted in predictions.items():
            metrics.append(_metric_row(sku, model_name, actual, predicted))
            for week, actual_value, predicted_value in zip(
                sku_test["WeekStart"], actual, predicted, strict=True
            ):
                backtest_rows.append(
                    {
                        "WeekStart": week,
                        "SKU": sku,
                        "Model": model_name,
                        "ActualDemandUnits": round(float(actual_value), 4),
                        "PredictedDemandUnits": round(float(predicted_value), 4),
                        "AbsoluteErrorUnits": round(float(abs(actual_value - predicted_value)), 4),
                    }
                )

    metric_df = pd.DataFrame(metrics)
    metric_df["RankWithinSKU"] = metric_df.groupby("SKU")["WAPE"].rank(
        method="first", ascending=True
    )
    metric_df["ChampionFlag"] = metric_df["RankWithinSKU"] == 1
    champion_map = (
        metric_df[metric_df["ChampionFlag"]].set_index("SKU")["Model"].to_dict()
    )
    residual_std = (
        pd.DataFrame(backtest_rows)
        .merge(
            metric_df.loc[metric_df["ChampionFlag"], ["SKU", "Model"]],
            on=["SKU", "Model"],
            how="inner",
        )
        .groupby("SKU")
        .apply(
            lambda frame: float(
                np.std(
                    frame["ActualDemandUnits"].to_numpy()
                    - frame["PredictedDemandUnits"].to_numpy(),
                    ddof=1,
                )
            ),
            include_groups=False,
        )
        .to_dict()
    )

    future_weeks = pd.date_range(FORECAST_START, periods=FORECAST_WEEKS, freq="W-MON")
    product_lookup = products.set_index("SKU").to_dict("index")
    sku_codes = history.groupby("SKU")["SKUCode"].first().to_dict()
    category_codes = history.groupby("Category")["CategoryCode"].first().to_dict()
    histories = {
        sku: deque(
            history.loc[history["SKU"] == sku].sort_values("WeekStart")["Demand"].tolist(),
            maxlen=260,
        )
        for sku in sorted(history["SKU"].unique())
    }
    future_rows = []
    for future_index, week in enumerate(future_weeks, start=1):
        for sku in sorted(histories):
            product = product_lookup[sku]
            values = histories[sku]
            category = product["Category"]
            campaign, discount = _campaign_for(week, category)
            iso_week = int(week.isocalendar().week)
            features = {
                "SKUCode": sku_codes[sku],
                "CategoryCode": category_codes[category],
                "WeekIndex": max_week + future_index,
                "WeekOfYearSin": math.sin(2 * math.pi * iso_week / 52.0),
                "WeekOfYearCos": math.cos(2 * math.pi * iso_week / 52.0),
                "Month": week.month,
                "PromoFlag": int(discount > 0),
                "DiscountPct": discount,
                "Lag1": values[-1],
                "Lag4": values[-4],
                "Lag13": values[-13],
                "Lag52": values[-52],
                "Roll4": float(np.mean(list(values)[-4:])),
                "Roll13": float(np.mean(list(values)[-13:])),
            }
            model_name = champion_map[sku]
            if model_name == "Seasonal Naive":
                prediction = features["Lag52"]
            elif model_name == "8-Week Moving Average":
                prediction = features["Roll4"] * 0.35 + features["Roll13"] * 0.65
            else:
                prediction = float(
                    ml_model.predict(pd.DataFrame([features])[FEATURE_COLUMNS])[0]
                )
            prediction = max(0.0, prediction)
            histories[sku].append(prediction)
            std = max(2.0, residual_std.get(sku, prediction * 0.18))
            price = float(product["ListPriceTRY"]) * (1 - discount)
            future_rows.append(
                {
                    "WeekStart": week,
                    "SKU": sku,
                    "Category": category,
                    "ChampionModel": model_name,
                    "ForecastUnits": round(prediction, 3),
                    "Lower80Units": round(max(0, prediction - 1.282 * std), 3),
                    "Upper80Units": round(prediction + 1.282 * std, 3),
                    "ResidualStdUnits": round(std, 3),
                    "ExpectedPromoFlag": discount > 0,
                    "ExpectedCampaign": campaign,
                    "ExpectedDiscountPct": discount,
                    "ExpectedSellingPriceTRY": round(price, 2),
                    "ForecastRevenueTRY": round(prediction * price, 2),
                }
            )

    forecast_df = pd.DataFrame(future_rows)
    backtest_df = pd.DataFrame(backtest_rows)
    metric_df.to_csv(DATA_DIR / "model_comparison.csv", index=False)
    backtest_df.to_csv(DATA_DIR / "forecast_backtest.csv", index=False, date_format="%Y-%m-%d")
    forecast_df.to_csv(DATA_DIR / "forecast_results.csv", index=False, date_format="%Y-%m-%d")
    return forecast_df, metric_df, backtest_df


if __name__ == "__main__":
    forecast, comparison, backtest = run_forecasting()
    print(f"forecast_results: {len(forecast):,} rows")
    print(f"model_comparison: {len(comparison):,} rows")
    print(f"forecast_backtest: {len(backtest):,} rows")
