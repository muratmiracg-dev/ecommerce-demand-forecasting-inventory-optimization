import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ecom_opt.forecasting import forecast_error_scale

DATA = Path(__file__).resolve().parents[2] / "Data"


def test_constant_under_forecast_is_not_zero_risk():
    # Every week 10 units short: zero spread, but the safety stock must cover the shortfall.
    actual = np.array([50.0, 60.0, 70.0, 80.0])
    assert forecast_error_scale(actual, actual - 10) == pytest.approx(10.0)


def test_scale_combines_bias_and_spread():
    actual = np.full(4, 100.0)
    predicted = np.array([97.0, 93.0, 97.0, 93.0])  # bias 5, spread 2
    assert forecast_error_scale(actual, predicted) == pytest.approx(math.sqrt(29))


@pytest.mark.parametrize(
    ("actual", "predicted"),
    [([], []), ([1.0, 2.0], [1.0]), ([np.nan], [1.0]), ([[1.0]], [[1.0]])],
)
def test_rejects_invalid_inputs(actual, predicted):
    with pytest.raises(ValueError):
        forecast_error_scale(np.array(actual), np.array(predicted))


def test_committed_forecast_uses_champion_backtest_rmse():
    forecast = pd.read_csv(DATA / "forecast_results.csv")
    backtest = pd.read_csv(DATA / "forecast_backtest.csv")
    champions = pd.read_csv(DATA / "model_comparison.csv").query("ChampionFlag")
    errors = backtest.merge(champions[["SKU", "Model"]], on=["SKU", "Model"])
    errors["Error"] = errors["ActualDemandUnits"] - errors["PredictedDemandUnits"]
    rmse = errors.groupby("SKU")["Error"].apply(lambda e: math.sqrt((e**2).mean()))
    published = forecast.groupby("SKU")["ResidualStdUnits"].first()
    expected = rmse.clip(lower=2.0).round(3)
    assert (published.reindex(expected.index) - expected).abs().max() <= 0.0011
