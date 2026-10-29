"""Single place for dates, features and paths."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"

TARGET = "price"

# Training window and its internal validation split (time-based, no shuffling:
# random splits leak same-month market conditions into validation).
TRAIN_START, TRAIN_END = "2022-01-01", "2022-09-30"
VALID_START, VALID_END = "2022-10-01", "2022-12-31"
# Post-deployment window scored month by month.
MONITOR_START, MONITOR_END = "2023-01-01", "2024-12-31"

CATEGORICAL = [
    "property_type", "old_new", "tenure", "region", "lad_code",
    "postcode_area", "current_energy_rating", "construction_age_band",
    "built_form", "main_fuel",
]
NUMERIC = ["floor_area_m2", "habitable_rooms", "energy_efficiency", "epc_age_days"]
FEATURES = CATEGORICAL + NUMERIC

# Groups used for sliced evaluation and the fairness section of the model card.
SLICES = ["region", "property_type"]

RANDOM_STATE = 42
N_TRIALS = 50
