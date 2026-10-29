"""End-to-end: load -> baseline -> tune -> refit -> evaluate -> SHAP -> monitor -> model card.

    python -m src.pipeline --source bigquery
    python -m src.pipeline --source parquet --path data/synthetic_sales.parquet --synthetic
"""
import argparse
import json

import pandas as pd

from . import explain, model_card, monitor, train
from .config import (MONITOR_END, MONITOR_START, N_TRIALS, OUT, SLICES, TARGET, TRAIN_END,
                     TRAIN_START, VALID_END, VALID_START)
from .data import align_categories, load, window
from .metrics import score, sliced


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["bigquery", "parquet"], required=True)
    ap.add_argument("--path")
    ap.add_argument("--trials", type=int, default=N_TRIALS)
    ap.add_argument("--synthetic", action="store_true", help="label outputs as synthetic")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    df = load(a.source, a.path)
    tr = window(df, TRAIN_START, TRAIN_END)
    va = window(df, VALID_START, VALID_END)
    full = window(df, TRAIN_START, VALID_END)
    mon = window(df, MONITOR_START, MONITOR_END)
    align_categories(tr, va)
    print(f"train {len(tr):,} | valid {len(va):,} | monitor {len(mon):,}")

    # 1. Baseline + tuning, both judged on the same 2022 Q4 holdout
    base = train.MedianBaseline().fit(tr)
    va["pred_base"] = base.predict(va)
    best = train.tune(tr, va, a.trials)
    tuned = train.fit_final(tr, best)  # trained on Jan-Sep only, for honest holdout scoring
    va["pred_xgb"] = train.predict(tuned, va)
    holdout = {"baseline": score(va[TARGET], va["pred_base"]),
               "xgb": score(va[TARGET], va["pred_xgb"])}
    sl = sliced(va, "pred_xgb", SLICES)
    sl.to_csv(OUT / "holdout_sliced.csv", index=False)
    (OUT / "holdout_metrics.json").write_text(json.dumps(holdout, indent=2))
    print("holdout:", {k: round(v["mape"], 4) for k, v in holdout.items()})

    # 2. Production model: all of 2022, then frozen
    align_categories(full, mon)
    final = train.fit_final(full, best, round_scale=1.15)
    train.save(final, best)
    imp = explain.run(final, full)

    # 3. Monitoring 2023-24
    mon["pred_xgb"] = train.predict(final, mon)
    monthly = monitor.run(full, mon)
    by_region = monitor.run_by_region(mon)

    model_card.write(holdout, sl, monthly, by_region, imp,
                     {"n_trials": a.trials, "n_train": len(full), "n_monitor": len(mon),
                      "synthetic": a.synthetic})
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
