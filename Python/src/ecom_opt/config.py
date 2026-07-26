from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "Data"
SQL_DIR = PROJECT_ROOT / "SQL"
REPORTS_DIR = PROJECT_ROOT / "Reports"
IMAGES_DIR = PROJECT_ROOT / "Images"

HISTORY_START = "2023-01-02"
HISTORY_END = "2025-12-29"
FORECAST_START = "2026-01-05"
FORECAST_WEEKS = 52
RANDOM_SEED = 20260726

CURRENCY = "TRY"
CHANNELS = ("Website", "Marketplace", "Social Shop")
CATEGORIES = (
    "Dresses",
    "Knitwear",
    "Outerwear",
    "Tops",
    "Bottoms",
    "Accessories",
)

SCENARIOS = {
    "Lean": {
        "demand_multiplier": 0.90,
        "service_level_delta": -0.02,
        "lead_time_days_delta": 0,
    },
    "Base": {
        "demand_multiplier": 1.00,
        "service_level_delta": 0.00,
        "lead_time_days_delta": 0,
    },
    "Growth": {
        "demand_multiplier": 1.15,
        "service_level_delta": 0.01,
        "lead_time_days_delta": 0,
    },
    "Resilience": {
        "demand_multiplier": 1.05,
        "service_level_delta": 0.02,
        "lead_time_days_delta": 14,
    },
}

