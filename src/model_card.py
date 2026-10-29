"""Writes outputs/MODEL_CARD.md from the run's own numbers.

Fixed sections describe the data and design. Tables and the headline
fairness facts are filled from results. The 'Interpretation' section is
deliberately left for the author to write after looking at the plots.
"""
import json
from datetime import date

import pandas as pd

from .config import FEATURES, MONITOR_END, MONITOR_START, OUT, TRAIN_START, VALID_END


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _table(df: pd.DataFrame, cols: list[str]) -> str:
    d = df[cols].copy()
    for c in ["mape", "median_ape", "median_pct_error", "within_10pct"]:
        if c in d:
            d[c] = d[c].map(_pct)
    if "mae" in d:
        d["mae"] = d["mae"].map(lambda v: f"£{v:,.0f}")
    return d.to_markdown(index=False)


def write(holdout: dict, sliced_xgb: pd.DataFrame, monthly: pd.DataFrame,
          region_monthly: pd.DataFrame, shap_imp: pd.DataFrame, meta: dict) -> None:
    reg = sliced_xgb[sliced_xgb["slice"] == "region"].sort_values("mape")
    pt = sliced_xgb[sliced_xgb["slice"] == "property_type"].sort_values("mape")
    best, worst = reg.iloc[0], reg.iloc[-1]
    last6 = region_monthly[region_monthly["month"] >= monthly["month"].iloc[-6]]
    bias_late = last6.groupby("region")["median_pct_error"].median().sort_values()
    m0, m1 = monthly.iloc[0], monthly.iloc[-1]
    cols = ["value", "n", "mae", "mape", "median_pct_error", "within_10pct"]

    synthetic_banner = (
        "> **SYNTHETIC DATA RUN - numbers below are pipeline test output, not results.**\n\n"
        if meta.get("synthetic") else "")

    md = f"""# Model card: England & Wales residential price estimator

{synthetic_banner}Generated {date.today().isoformat()} by `src/model_card.py`.

## Model details
- XGBoost regressor on log(price), objective = absolute error, native categorical handling.
- Hyperparameters tuned with Optuna ({meta['n_trials']} trials, TPE), selected on a
  time-based validation split (Oct-Dec 2022); refit on all of 2022.
- Baseline for comparison: median price by local authority x property type.

## Intended use
Portfolio demonstration of an end-to-end valuation model with monitoring.
Not for real valuations, lending, or any decision about a specific property.

## Data
- HM Land Registry Price Paid Data, standard-price sales (category A), England & Wales.
- Joined to the most recent EPC certificate lodged on or before the sale date,
  matched on postcode + normalised address.
- Training window {TRAIN_START} to {VALID_END}; monitoring window {MONITOR_START} to {MONITOR_END}.
- Rows: train {meta['n_train']:,} | monitor {meta['n_monitor']:,}.
- Features ({len(FEATURES)}): {", ".join(f"`{f}`" for f in FEATURES)}.

## Holdout performance (Oct-Dec 2022)
| model | MAE | MAPE | median APE | within 10% |
|---|---|---|---|---|
| Baseline (LA x type median) | £{holdout['baseline']['mae']:,.0f} | {_pct(holdout['baseline']['mape'])} | {_pct(holdout['baseline']['median_ape'])} | {_pct(holdout['baseline']['within_10pct'])} |
| XGBoost | £{holdout['xgb']['mae']:,.0f} | {_pct(holdout['xgb']['mape'])} | {_pct(holdout['xgb']['median_ape'])} | {_pct(holdout['xgb']['within_10pct'])} |

### By property type
{_table(pt, cols)}

### Top drivers (mean |SHAP|, log-price scale)
{shap_imp.head(8).to_markdown(index=False, floatfmt=".3f")}

## Fairness across regions
Error is not shared equally. On the 2022 holdout, MAPE ranges from
{_pct(best['mape'])} ({best['value']}) to {_pct(worst['mape'])} ({worst['value']}),
a ratio of {worst['mape'] / best['mape']:.2f}x.

{_table(reg, cols)}

Signed bias matters more than MAPE for harm: a model that systematically
over-values one region and under-values another shifts expectations for
sellers and buyers in a consistent direction. Median % error by region over the
last six monitored months:

{bias_late.map(_pct).rename("median % error").to_markdown()}

See `bias_by_region.png` for the full 2023-24 trajectory.

## Monitoring (model frozen at end-2022)
- MAPE moved from {_pct(m0['mape'])} ({m0['month']}) to {_pct(m1['mape'])} ({m1['month']}).
- Median signed error moved from {_pct(m0['median_pct_error'])} to {_pct(m1['median_pct_error'])}.
- Input-feature drift (Evidently, per-column tests vs 2022 reference): mean share of
  features flagged = {_pct(monthly['share_drifted'].mean())}; months with target drift flagged =
  {int(monthly['target_drifted'].fillna(False).sum())} of {len(monthly)}.
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
"""
    (OUT / "MODEL_CARD.md").write_text(md)
