"""Load the modelling table from BigQuery (dbt mart) or a local Parquet file."""
import os

import pandas as pd

from .config import CATEGORICAL, NUMERIC


def load(source: str, path: str | None = None) -> pd.DataFrame:
    if source == "bigquery":
        from google.cloud import bigquery

        project = os.environ["GCP_PROJECT"]
        dataset = os.environ.get("BQ_DATASET", "hp_analytics")
        sql = f"select * from `{project}.{dataset}.fct_sales_features`"
        df = bigquery.Client(project=project).query(sql).to_dataframe()
    elif source == "parquet":
        df = pd.read_parquet(path)
    else:
        raise ValueError(source)
    return clean_types(df)


def clean_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["sale_date"] = pd.to_datetime(df["sale_date"])
    df["sale_month"] = df["sale_date"].dt.to_period("M").dt.to_timestamp()
    for c in CATEGORICAL:
        df[c] = df[c].astype("string").fillna("MISSING").astype("category")
    for c in NUMERIC:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    return df


def window(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    m = (df["sale_date"] >= start) & (df["sale_date"] <= end)
    return df.loc[m].reset_index(drop=True)


def align_categories(train: pd.DataFrame, *others: pd.DataFrame) -> None:
    """Force every frame to use the training category set (unseen -> NaN),
    which is what a deployed model would actually see."""
    for c in CATEGORICAL:
        cats = train[c].cat.categories
        for o in others:
            o[c] = pd.Categorical(o[c].astype("string"), categories=cats)
