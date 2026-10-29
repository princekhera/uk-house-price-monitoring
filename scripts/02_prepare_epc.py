"""Slim the EPC data straight from the zip, no extraction.
Usage: python scripts/02_prepare_epc.py --src certificates.csv.zip --out data/raw/epc/epc_slim.parquet
"""
import argparse, zipfile
from pathlib import Path
import pandas as pd, pyarrow as pa, pyarrow.parquet as pq

KEEP = ["LMK_KEY","ADDRESS1","ADDRESS2","ADDRESS3","POSTCODE","LODGEMENT_DATE",
        "LOCAL_AUTHORITY","PROPERTY_TYPE","BUILT_FORM","CURRENT_ENERGY_RATING",
        "CURRENT_ENERGY_EFFICIENCY","TOTAL_FLOOR_AREA","NUMBER_HABITABLE_ROOMS",
        "CONSTRUCTION_AGE_BAND","MAIN_FUEL"]
schema = pa.schema([(c, pa.string()) for c in KEEP])

ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True, type=Path)
ap.add_argument("--out", required=True, type=Path)
a = ap.parse_args()
a.out.parent.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(a.src) as z, pq.ParquetWriter(a.out, schema, compression="zstd") as w:
    members = [m for m in z.namelist()
           if Path(m).name.lower().startswith("certificates") and m.lower().endswith(".csv")]
    print(f"{len(members)} CSV(s) inside: {members[:3]}")
    total = 0
    for m in members:
        with z.open(m) as fh:
            for chunk in pd.read_csv(fh, dtype=str, chunksize=500_000,
                                     usecols=lambda c: c.upper() in KEEP or c == "certificate_number"):   # CHANGE 1
                chunk.columns = [c.upper() for c in chunk.columns]
                chunk = chunk.rename(columns={"CERTIFICATE_NUMBER": "LMK_KEY"})                           # CHANGE 2
                chunk = chunk.reindex(columns=KEEP)
                w.write_table(pa.Table.from_pandas(chunk, schema=schema, preserve_index=False))
                total += len(chunk)
                print(f"{m}: {total:,} rows so far")

print(f"Done: {total:,} rows -> {a.out}")