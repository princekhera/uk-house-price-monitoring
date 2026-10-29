# Model card: England & Wales residential price estimator

Generated 2026-10-27 by `src/model_card.py`.

## Model details
- XGBoost regressor on log(price), objective = absolute error, native categorical handling.
- Hyperparameters tuned with Optuna (50 trials, TPE), selected on a
  time-based validation split (Oct-Dec 2022); refit on all of 2022.
- Baseline for comparison: median price by local authority x property type.

## Intended use
Portfolio demonstration of an end-to-end valuation model with monitoring.
Not for real valuations, lending, or any decision about a specific property.

## Data
- HM Land Registry Price Paid Data, standard-price sales (category A), England & Wales.
- Joined to the most recent EPC certificate lodged on or before the sale date,
  matched on postcode + normalised address.
- Training window 2022-01-01 to 2022-12-31; monitoring window 2023-01-01 to 2024-12-31.
- Rows: train 837,287 | monitor 1,366,540.
- Features (14): `property_type`, `old_new`, `tenure`, `region`, `lad_code`, `postcode_area`, `current_energy_rating`, `construction_age_band`, `built_form`, `main_fuel`, `floor_area_m2`, `habitable_rooms`, `energy_efficiency`, `epc_age_days`.

## Holdout performance (Oct-Dec 2022)
| model | MAE | MAPE | median APE | within 10% |
|---|---|---|---|---|
| Baseline (LA x type median) | £98,414 | 25.9% | 19.1% | 28.1% |
| XGBoost | £56,364 | 16.3% | 11.2% | 45.8% |

### By property type
| value   |     n | mae     | mape   | median_pct_error   | within_10pct   |
|:--------|------:|:--------|:-------|:-------------------|:---------------|
| D       | 57582 | £78,498 | 14.4%  | -3.4%              | 49.4%          |
| S       | 66876 | £47,290 | 15.3%  | -3.8%              | 46.9%          |
| T       | 61135 | £47,047 | 17.3%  | -4.1%              | 43.4%          |
| F       | 34617 | £53,531 | 19.9%  | -3.1%              | 41.8%          |

### Top drivers (mean |SHAP|, log-price scale)
| feature               |   mean_abs_shap |
|:----------------------|----------------:|
| floor_area_m2         |           0.190 |
| lad_code              |           0.182 |
| postcode_area         |           0.119 |
| property_type         |           0.066 |
| built_form            |           0.053 |
| habitable_rooms       |           0.041 |
| tenure                |           0.037 |
| construction_age_band |           0.029 |

## Fairness across regions
Error is not shared equally. On the 2022 holdout, MAPE ranges from
13.0% (East of England) to 21.6% (North East),
a ratio of 1.66x.

| value                    |     n | mae      | mape   | median_pct_error   | within_10pct   |
|:-------------------------|------:|:---------|:-------|:-------------------|:---------------|
| East of England          | 25886 | £53,923  | 13.0%  | -3.4%              | 54.5%          |
| South East               | 37666 | £65,434  | 13.7%  | -3.2%              | 52.5%          |
| East Midlands            | 19854 | £38,994  | 14.1%  | -3.9%              | 50.0%          |
| South West               | 24157 | £62,078  | 15.9%  | -3.9%              | 45.9%          |
| West Midlands            | 20331 | £44,619  | 16.2%  | -4.3%              | 45.2%          |
| London                   | 20821 | £107,766 | 16.8%  | -2.5%              | 46.4%          |
| Wales                    | 11411 | £44,251  | 19.0%  | -4.4%              | 37.9%          |
| Yorkshire and The Humber | 21145 | £44,003  | 19.0%  | -3.9%              | 38.3%          |
| North West               | 28018 | £45,361  | 19.3%  | -4.6%              | 38.5%          |
| North East               | 10921 | £38,497  | 21.6%  | -3.6%              | 36.1%          |

Signed bias matters more than MAPE for harm: a model that systematically
over-values one region and under-values another shifts expectations for
sellers and buyers in a consistent direction. Median % error by region over the
last six monitored months:

| region                   | median % error   |
|:-------------------------|:-----------------|
| North West               | -4.9%            |
| North East               | -3.9%            |
| Yorkshire and The Humber | -3.7%            |
| Wales                    | -3.3%            |
| West Midlands            | -3.1%            |
| East Midlands            | -1.2%            |
| London                   | -0.5%            |
| South West               | 0.5%             |
| South East               | 1.0%             |
| East of England          | 1.0%             |

See `bias_by_region.png` for the full 2023-24 trajectory.

## Monitoring (model frozen at end-2022)
- MAPE moved from 17.3% (2023-01) to 16.5% (2024-12).
- Median signed error moved from -1.9% to -1.5%.
- Input-feature drift (Evidently, per-column tests vs 2022 reference): mean share of
  features flagged = 0.6%; months with target drift flagged =
  0 of 24.
- Plots: `monitoring.png`, `bias_by_region.png`. Reports: `drift/*.html`.

## Limitations and known risks
- **Selection bias from the EPC join.** Sales without a matchable EPC are dropped.
  Match rate varies by property type and region (`rpt_match_rate` in dbt); if
  unmatched homes differ systematically (e.g. older stock never re-certified), the
  model is evaluated on an unrepresentative slice of the market.
- **No condition or interior data.** Two identical-on-paper homes can differ a lot.
- **EPC staleness.** Certificates can be years old (`epc_age_days`); renovations since
  are invisible.
- **Time.** No date feature by design: the model cannot extrapolate market moves, which
  is exactly what monitoring is meant to catch. In production this would trigger retraining.
- **Coverage.** England & Wales only. Category B sales excluded.

## Interpretation (author)
_Write after reviewing the plots: which regions drift first, whether drift
signals led or lagged the performance drop, and what retraining policy you'd set._
