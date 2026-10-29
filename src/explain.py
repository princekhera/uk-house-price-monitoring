"""SHAP values via XGBoost's native TreeSHAP (pred_contribs), which handles
categorical features directly - no one-hot expansion needed."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import xgboost as xgb

from .config import FEATURES, OUT, RANDOM_STATE


def run(bst: xgb.Booster, df: pd.DataFrame, n: int = 5000) -> pd.DataFrame:
    s = df.sample(min(n, len(df)), random_state=RANDOM_STATE)
    contribs = bst.predict(xgb.DMatrix(s[FEATURES], enable_categorical=True), pred_contribs=True)
    vals, base = contribs[:, :-1], contribs[:, -1]

    # shap plots need numeric data for colouring; use category codes for display.
    disp = s[FEATURES].copy()
    for c in disp.select_dtypes("category"):
        disp[c] = disp[c].cat.codes.replace(-1, np.nan)
    exp = shap.Explanation(values=vals, base_values=base, data=disp.to_numpy(),
                           feature_names=FEATURES)

    plt.figure()
    shap.plots.beeswarm(exp, max_display=14, show=False)
    plt.title("SHAP (log-price scale), 2022 holdout sample")
    plt.tight_layout(); plt.savefig(OUT / "shap_beeswarm.png", dpi=150); plt.close("all")

    plt.figure()
    shap.plots.scatter(exp[:, "floor_area_m2"], show=False)
    plt.tight_layout(); plt.savefig(OUT / "shap_floor_area.png", dpi=150); plt.close("all")

    imp = (pd.DataFrame({"feature": FEATURES, "mean_abs_shap": np.abs(vals).mean(0)})
           .sort_values("mean_abs_shap", ascending=False))
    imp.to_csv(OUT / "shap_importance.csv", index=False)
    return imp
