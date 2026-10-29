# UK house price model with drift monitoring

Predicts sale prices for England & Wales homes from HM Land Registry Price Paid
Data joined to EPC certificates, then freezes the model at end-2022 and monitors
it through the 2023-24 rate shock: monthly error, regional valuation bias, and
input drift (Evidently).

```
Price Paid CSVs ─┐                      dbt (BigQuery)
EPC bulk zip ────┼─> BigQuery raw ──> stg_* ─> int_sales_epc_matched ─> fct_sales_features
ONS LAD→region ──┘                                         └─> rpt_match_rate
fct_sales_features ─> baseline · XGBoost+Optuna · SHAP · monthly monitoring ─> MODEL_CARD.md
```

## Design decisions
- **Time-based splits only.** Tune on Jan-Sep 2022, validate Oct-Dec 2022, monitor 2023-24.
- **No leakage from EPCs.** Each sale uses the latest certificate lodged on or before the sale date.
- **No date feature.** The model can't extrapolate the market, so degradation shows up in monitoring rather than being hidden.
- **Signed bias by region**, not just MAPE. Systematic over/under-valuation is the fairness harm.
- **Drift and performance tracked separately.** Drift needs no labels; performance needs prices that arrive with a lag.

## Run it
```bash
pip install -r requirements.txt -r requirements-dbt.txt

# 1. Data
./scripts/01_download_price_paid.sh
#    EPC: register (free) for the domestic bulk download, unzip, then:
python scripts/02_prepare_epc.py --src ~/Downloads/all-domestic-certificates --out data/raw/epc/epc_slim.parquet
#    ONS LAD->Region lookup CSV -> data/raw/lad_region.csv
#    (set lad_code_col / region_name_col in dbt/dbt_project.yml to match its headers)

# 2. Warehouse (BigQuery sandbox, no billing)
gcloud auth application-default login
GCP_PROJECT=your-project ./scripts/03_load_bigquery.sh
cd dbt && cp profiles.yml.example profiles.yml  # edit project
dbt build && cd ..

# 3. Model + monitoring
GCP_PROJECT=your-project python -m src.pipeline --source bigquery
```
Outputs land in `outputs/`: `MODEL_CARD.md`, SHAP plots, `monitoring.png`,
`bias_by_region.png`, `drift/*.html`.

To test without any data: `python -m src.synthetic && python -m src.pipeline --source parquet --path data/synthetic_sales.parquet --trials 5 --synthetic`
(synthetic numbers are meaningless; the card is stamped accordingly).

## Results
_Fill from your run: holdout MAPE vs baseline, EPC match rate, worst/best region, when drift was first flagged vs when bias crossed ±5%._

## Data licences
Price Paid Data: HM Land Registry, OGL v3.0. EPC data: DLUHC/MHCLG open data licence
(check current terms at download, including address-data restrictions). ONS lookups: OGL.
