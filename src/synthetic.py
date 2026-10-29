"""SYNTHETIC data shaped like fct_sales_features - for testing the pipeline only.

Do NOT report any metric produced from this file. It exists so the code can be
run end-to-end before the real BigQuery mart is built.
"""
import numpy as np
import pandas as pd

REGIONS = {  # region: (price multiplier, 2023-24 monthly drift)
    "London": (2.3, -0.006), "South East": (1.5, -0.004), "East of England": (1.3, -0.003),
    "South West": (1.25, -0.002), "West Midlands": (0.95, 0.001), "East Midlands": (0.9, 0.001),
    "North West": (0.8, 0.003), "Yorkshire and The Humber": (0.78, 0.002),
    "North East": (0.6, 0.002), "Wales": (0.75, 0.0),
}
PTYPE = {"D": 1.45, "S": 1.0, "T": 0.85, "F": 0.75}


def make(n: int = 60_000, seed: int = 0) -> pd.DataFrame:
    r = np.random.default_rng(seed)
    dates = pd.to_datetime("2022-01-01") + pd.to_timedelta(r.integers(0, 1096, n), unit="D")
    region = r.choice(list(REGIONS), n, p=[.14, .16, .11, .1, .09, .08, .11, .08, .04, .09])
    ptype = r.choice(list(PTYPE), n, p=[.25, .28, .27, .20])
    area = np.clip(r.lognormal(np.log(np.where(ptype == "F", 60, 95)), 0.3), 20, 600)
    eff = np.clip(r.normal(68, 10, n), 1, 100).round()
    months_after = np.maximum((dates.year - 2023) * 12 + dates.month - 1, -1) + 1
    drift = np.array([REGIONS[x][1] for x in region]) * months_after
    # 2023 rate shock: flats and the South soften more; floor area mix shifts up.
    area = area * np.where(dates.year >= 2023, 1.05, 1.0)
    mult = np.array([REGIONS[x][0] for x in region]) * np.array([PTYPE[x] for x in ptype])
    logp = np.log(2400 * area) + np.log(mult) + 0.004 * (eff - 68) + drift + r.normal(0, 0.22, n)
    lad = np.array([f"{x[:3].upper()}{r.integers(1, 15)}" for x in region])
    df = pd.DataFrame({
        "transaction_id": [f"SYN{i:08d}" for i in range(n)],
        "sale_date": dates, "price": np.exp(logp).round(-3).astype(int),
        "property_type": ptype, "old_new": r.choice(["N", "Y"], n, p=[.9, .1]),
        "tenure": np.where(ptype == "F", "L", r.choice(["F", "L"], n, p=[.95, .05])),
        "region": region, "lad_code": lad, "postcode_area": lad,
        "current_energy_rating": pd.cut(eff, [0, 38, 54, 68, 80, 91, 101],
                                        labels=list("FEDCBA")).astype(str),
        "construction_age_band": r.choice(["pre-1900", "1930-1949", "1967-1975", "2007 onwards"], n),
        "built_form": r.choice(["Detached", "Semi-Detached", "Mid-Terrace", "End-Terrace"], n),
        "main_fuel": r.choice(["mains gas", "electricity"], n, p=[.85, .15]),
        "floor_area_m2": area.round(1), "habitable_rooms": np.clip((area / 22).round(), 1, 15),
        "energy_efficiency": eff, "epc_age_days": r.integers(0, 3650, n),
    })
    return df


if __name__ == "__main__":
    from .config import ROOT
    p = ROOT / "data" / "synthetic_sales.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    make().to_parquet(p, index=False)
    print(f"SYNTHETIC test data -> {p}")
