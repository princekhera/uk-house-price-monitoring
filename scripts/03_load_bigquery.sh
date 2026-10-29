#!/usr/bin/env bash
# Loads raw files into BigQuery (works in the free sandbox; no billing needed).
# Requires: gcloud CLI authenticated, `bq` available.
# Sandbox note: tables expire after 60 days by default - re-run if they vanish.
set -euo pipefail
: "${GCP_PROJECT:?set GCP_PROJECT}"
DATASET="${BQ_RAW_DATASET:-hp_raw}"
LOC="${BQ_LOCATION:-EU}"

bq --location="$LOC" mk --dataset --force "$GCP_PROJECT:$DATASET"

PP_SCHEMA="transaction_id:STRING,price:INT64,date_of_transfer:STRING,postcode:STRING,\
property_type:STRING,old_new:STRING,duration:STRING,paon:STRING,saon:STRING,\
street:STRING,locality:STRING,town_city:STRING,district:STRING,county:STRING,\
ppd_category_type:STRING,record_status:STRING"

MODE="--replace"
for f in data/raw/price_paid/pp-*.csv; do
  bq load $MODE --source_format=CSV --allow_quoted_newlines \
    "$GCP_PROJECT:$DATASET.price_paid" "$f" "$PP_SCHEMA"
  MODE="--noreplace"
done

bq load --replace --source_format=PARQUET \
  "$GCP_PROJECT:$DATASET.epc" data/raw/epc/epc_slim.parquet

# ONS Local Authority District -> Region lookup (England). Download the CSV from
# the ONS Open Geography Portal (search "Local Authority District to Region lookup"),
# save as data/raw/lad_region.csv. Wales is handled in SQL (W06* codes).
bq load --replace --source_format=CSV --skip_leading_rows=1 --autodetect \
  "$GCP_PROJECT:$DATASET.lad_region_raw" data/raw/lad_region.csv

echo "Loaded. Next: cd dbt && dbt build"
