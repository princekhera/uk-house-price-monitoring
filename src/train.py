"""Baseline + XGBoost tuned with Optuna on a time-based validation split."""
import json

import numpy as np
import optuna
import pandas as pd
import xgboost as xgb

from .config import FEATURES, N_TRIALS, OUT, RANDOM_STATE, TARGET
from .metrics import score


class MedianBaseline:
    """Median price by (local authority, property type), falling back to
    property type, then global. The bar any model has to clear."""

    def fit(self, df: pd.DataFrame) -> "MedianBaseline":
        self.fine = df.groupby(["lad_code", "property_type"], observed=True)[TARGET].median()
        self.coarse = df.groupby("property_type", observed=True)[TARGET].median()
        self.glob = df[TARGET].median()
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        keys = pd.MultiIndex.from_arrays([df["lad_code"].astype(str), df["property_type"].astype(str)])
        fine = self.fine.copy()
        fine.index = pd.MultiIndex.from_arrays(
            [fine.index.get_level_values(0).astype(str), fine.index.get_level_values(1).astype(str)])
        p = fine.reindex(keys).to_numpy()
        coarse = self.coarse.copy(); coarse.index = coarse.index.astype(str)
        fb = coarse.reindex(df["property_type"].astype(str)).to_numpy()
        p = np.where(np.isnan(p), fb, p)
        return np.where(np.isnan(p), self.glob, p)


def _dm(df: pd.DataFrame, with_label: bool = True) -> xgb.DMatrix:
    y = np.log(df[TARGET].to_numpy()) if with_label else None
    return xgb.DMatrix(df[FEATURES], label=y, enable_categorical=True)


def _params(trial: optuna.Trial) -> dict:
    return {
        "objective": "reg:absoluteerror",   # MAE in log space ~ robust relative error
        "eval_metric": "mae",
        "tree_method": "hist",
        "max_cat_to_onehot": 1,
        "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.2, log=True),
        "max_depth": trial.suggest_int("max_depth", 4, 10),
        "min_child_weight": trial.suggest_float("min_child_weight", 1, 50, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10, log=True),
        "max_cat_threshold": trial.suggest_int("max_cat_threshold", 16, 128),
        "seed": RANDOM_STATE,
    }


def tune(train: pd.DataFrame, valid: pd.DataFrame, n_trials: int = N_TRIALS) -> dict:
    dtr, dva = _dm(train), _dm(valid)

    def objective(trial):
        params = _params(trial)
        bst = xgb.train(params, dtr, num_boost_round=3000, evals=[(dva, "valid")],
                        early_stopping_rounds=100, verbose_eval=False)
        trial.set_user_attr("best_iteration", bst.best_iteration)
        pred = np.exp(bst.predict(dva, iteration_range=(0, bst.best_iteration + 1)))
        return score(valid[TARGET], pred)["mape"]

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="minimize",
                                sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    best = {**_params(optuna.trial.FixedTrial(study.best_params)),
            "n_rounds": study.best_trial.user_attrs["best_iteration"] + 1}
    study.trials_dataframe().to_csv(OUT / "optuna_trials.csv", index=False)
    return best


def fit_final(df: pd.DataFrame, best: dict, round_scale: float = 1.0) -> xgb.Booster:
    params = {k: v for k, v in best.items() if k != "n_rounds"}
    # round_scale > 1 when refitting on more data than tuning used.
    rounds = max(1, int(best["n_rounds"] * round_scale))
    return xgb.train(params, _dm(df), num_boost_round=rounds)


def predict(bst: xgb.Booster, df: pd.DataFrame) -> np.ndarray:
    return np.exp(bst.predict(_dm(df, with_label=False)))


def save(bst: xgb.Booster, best: dict) -> None:
    bst.save_model(OUT / "model.json")
    (OUT / "best_params.json").write_text(json.dumps(best, indent=2))
