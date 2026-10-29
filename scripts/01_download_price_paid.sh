#!/usr/bin/env bash
# Downloads HM Land Registry Price Paid Data yearly files (OGL v3.0).
# If a URL 404s, get the current link from:
# https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads
set -euo pipefail
mkdir -p data/raw/price_paid
BASE="http://prod.publicdata.landregistry.gov.uk.s3-website-eu-west-1.amazonaws.com"
for y in 2022 2023 2024; do
  curl -fSL "$BASE/pp-$y.csv" -o "data/raw/price_paid/pp-$y.csv"
done
# Files have no header row; column names are supplied at load time.
wc -l data/raw/price_paid/*.csv
