from __future__ import annotations

import json

from .data_generation import generate_all
from .database import build_database
from .forecasting import run_forecasting
from .inventory import optimize_inventory
from .reporting import build_reporting_tables
from .validation import validate_project


def main() -> None:
    datasets = generate_all()
    forecast, model_comparison, backtest = run_forecasting()
    recommendations, scenarios, summary = optimize_inventory()
    reporting_tables = build_reporting_tables()
    database_path = build_database()
    validation = validate_project()
    payload = {
        "generated_tables": {name: len(frame) for name, frame in datasets.items()},
        "forecast_rows": len(forecast),
        "model_comparison_rows": len(model_comparison),
        "backtest_rows": len(backtest),
        "recommendation_rows": len(recommendations),
        "scenario_rows": len(scenarios),
        "scenario_summary_rows": len(summary),
        "reporting_tables": {
            name: len(frame) for name, frame in reporting_tables.items()
        },
        "database": str(database_path),
        "validation_passed": validation["all_passed"],
    }
    print(json.dumps(payload, indent=2))
    if not validation["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
