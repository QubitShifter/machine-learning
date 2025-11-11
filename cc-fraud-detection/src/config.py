from pathlib import Path
from datetime import datetime


# project root location
root = Path(__file__).resolve().parents[1]

data_dir = root / "data"
raw_dir = data_dir / "raw"
interim_dir = data_dir / "interim"
processed_dir = data_dir / "processed"
models_dir = root / "models"
reports_dir = root / "reports"

# check if folders exists

for f in [raw_dir, interim_dir, processed_dir, models_dir, reports_dir]:
    f.mkdir(parents=True, exist_ok=True)

# data settings

n_employees = 50
start_date = datetime(2025, 1, 1)
end_date = datetime(2025, 3, 31)

random_seed = 0

synth_transactions_csv = raw_dir / "corp_card_synth.csv"
synth_transactions_v2_csv = raw_dir / "corp_card_synth_cv2.csv"
target_col = "is_misuse"  # modeling

