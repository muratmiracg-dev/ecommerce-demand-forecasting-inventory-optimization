# Synthetic Data Package

This folder contains the generated input, model output, inventory decision, and
reporting CSV files for the project.

- Historical data: 2023-01-02 through 2025-12-29
- Forecast horizon: 52 weeks beginning 2026-01-05
- Portfolio: 60 synthetic SKUs, 6 categories, 8 suppliers, 3 sales channels
- Currency: TRY
- Generator seed: 20260726

All records are synthetic. They are inspired by fashion e-commerce operating
patterns and do not contain real customer or company data.

Run `python -m ecom_opt.run_pipeline` with `PYTHONPATH=Python/src` to regenerate
the full data package.
