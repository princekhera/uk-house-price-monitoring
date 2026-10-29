import numpy as np
import pandas as pd


def score(y: np.ndarray, p: np.ndarray) -> dict:
    y, p = np.asarray(y, float), np.asarray(p, float)
    ape = np.abs(p - y) / y
    return {
        "n": int(len(y)),
        "mae": float(np.mean(np.abs(p - y))),
        "mape": float(np.mean(ape)),
        "median_ape": float(np.median(ape)),
        # Signed bias: >0 means the model over-values. This is the number that
        # matters for fairness - a consistent over/under-valuation for a region.
        "median_pct_error": float(np.median((p - y) / y)),
        "within_10pct": float(np.mean(ape <= 0.10)),
    }


def sliced(df: pd.DataFrame, pred_col: str, by: list[str], target: str = "price") -> pd.DataFrame:
    rows = []
    for col in by:
        for val, g in df.groupby(col, observed=True):
            rows.append({"slice": col, "value": str(val), **score(g[target], g[pred_col])})
    return pd.DataFrame(rows)
