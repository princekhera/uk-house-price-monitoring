"""Score 2023-24 month by month against a model frozen at end-2022.

Two signals, kept separate on purpose:
  * performance (needs ground-truth prices, which arrive with a lag in reality)
  * input drift via Evidently (available immediately, no labels needed)
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from evidently import DataDefinition, Dataset, Report
from evidently.presets import DataDriftPreset

from .config import CATEGORICAL, NUMERIC, OUT, RANDOM_STATE, TARGET
from .metrics import score

DRIFT_SAMPLE = 20_000  # cap rows per side: drift tests on huge n flag everything
HTML_MONTHS = {"2023-01", "2023-07", "2024-01", "2024-12"}


def _dataset(df: pd.DataFrame) -> Dataset:
    cols = CATEGORICAL + NUMERIC + ["log_price"]
    d = df.assign(log_price=np.log(df[TARGET].astype(float)))[cols].copy()
    for c in CATEGORICAL:
        d[c] = d[c].astype("string").fillna("UNSEEN")
    defn = DataDefinition(numerical_columns=NUMERIC + ["log_price"], categorical_columns=CATEGORICAL)
    return Dataset.from_pandas(d, data_definition=defn)


def _drift_summary(snapshot) -> dict:
    """Input-feature drift share (excludes the target), plus target drift flag.
    Evidently picks the test per column; p-value tests drift when score < threshold,
    distance metrics (e.g. Wasserstein, Jensen-Shannon) when score >= threshold."""
    per_col = {}
    for m in snapshot.dict()["metrics"]:
        cfg, val = m["config"], m["value"]
        if cfg["type"].endswith("ValueDrift"):
            pval = "p_value" in cfg["method"]
            drifted = (val < cfg["threshold"]) if pval else (val >= cfg["threshold"])
            per_col[cfg["column"]] = {"method": cfg["method"], "score": val,
                                      "threshold": cfg["threshold"], "drifted": bool(drifted)}
    feats = {k: v for k, v in per_col.items() if k != "log_price"}
    n = sum(v["drifted"] for v in feats.values())
    return {"n_drifted": n, "share_drifted": n / max(len(feats), 1),
            "target_drifted": per_col.get("log_price", {}).get("drifted"),
            "drifted_features": sorted(k for k, v in feats.items() if v["drifted"]),
            "per_column": per_col}


def run(reference: pd.DataFrame, monitor: pd.DataFrame, pred_col: str = "pred_xgb") -> pd.DataFrame:
    ref = reference.sample(min(DRIFT_SAMPLE, len(reference)), random_state=RANDOM_STATE)
    ref_ds = _dataset(ref)
    (OUT / "drift").mkdir(exist_ok=True)

    rows, drift_detail = [], {}
    for month, g in monitor.groupby(monitor["sale_month"].dt.strftime("%Y-%m")):
        perf = score(g[TARGET], g[pred_col])
        cur = g.sample(min(DRIFT_SAMPLE, len(g)), random_state=RANDOM_STATE)
        snap = Report([DataDriftPreset()]).run(_dataset(cur), ref_ds)
        d = _drift_summary(snap)
        drift_detail[month] = d
        if month in HTML_MONTHS:
            snap.save_html(str(OUT / "drift" / f"drift_{month}.html"))
        rows.append({"month": month, **perf, "share_drifted": d["share_drifted"],
                     "n_drifted": d["n_drifted"], "target_drifted": d["target_drifted"],
                     "drifted_features": ";".join(d["drifted_features"])})

    res = pd.DataFrame(rows)
    res.to_csv(OUT / "monitoring_monthly.csv", index=False)
    (OUT / "drift" / "drift_detail.json").write_text(json.dumps(drift_detail, indent=2, default=str))
    _plot(res)
    return res


def run_by_region(monitor: pd.DataFrame, pred_col: str = "pred_xgb") -> pd.DataFrame:
    rows = [{"month": m, "region": str(r), **score(g[TARGET], g[pred_col])}
            for (m, r), g in monitor.groupby([monitor["sale_month"].dt.strftime("%Y-%m"), "region"],
                                             observed=True)]
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "monitoring_by_region.csv", index=False)
    piv = res.pivot(index="month", columns="region", values="median_pct_error")
    ax = piv.plot(figsize=(11, 5), lw=1.4)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_ylabel("median % error (pred - actual) / actual")
    ax.set_title("Valuation bias by region after deployment (model frozen Dec 2022)")
    ax.legend(fontsize=7, ncol=2); plt.xticks(rotation=45); plt.tight_layout()
    plt.savefig(OUT / "bias_by_region.png", dpi=150); plt.close("all")
    return res


def _plot(res: pd.DataFrame) -> None:
    fig, ax1 = plt.subplots(figsize=(11, 5))
    ax1.plot(res["month"], res["mape"], marker="o", label="MAPE")
    ax1.plot(res["month"], res["median_pct_error"], marker="s", label="median % error (bias)")
    ax1.axhline(0, color="k", lw=0.8); ax1.set_ylabel("error")
    ax2 = ax1.twinx()
    ax2.bar(res["month"], res["share_drifted"], alpha=0.2, color="grey", label="share of input features drifted")
    ax2.set_ylim(0, 1); ax2.set_ylabel("share of input features drifted")
    h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8)
    ax1.set_title("Monthly performance and input drift, 2023-24")
    plt.setp(ax1.get_xticklabels(), rotation=45); plt.tight_layout()
    plt.savefig(OUT / "monitoring.png", dpi=150); plt.close("all")
