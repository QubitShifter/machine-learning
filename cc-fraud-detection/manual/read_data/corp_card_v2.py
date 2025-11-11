import pandas as pd
from pathlib import Path

here = Path(__file__).resolve()
root = here.parents[2]
csv_path = root / "data" / "raw" / "corp_card_synth_cv2.csv"  # или v2, ако така се казва файла

print("Loading:", csv_path)
df = pd.read_csv(csv_path, parse_dates=["tx_datetime"])

# 1) размер
print("shape:", df.shape)

# 2) типове
print("\nDtypes:")
print(df.dtypes)

# 3) null-и
print("\nMissing values per column:")
print(df.isna().sum())

# 4) target distribution
print("\nTarget distribution (is_misuse):")
print(df["is_misuse"].value_counts(normalize=True).rename("proportion"))

# 5) няколко ключови колони
print("\nGender:")
print(df["gender"].value_counts())

print("\nMCC categories (top 10):")
print(df["mcc_category"].value_counts().head(10))

print("\nMerchants (top 10):")
print(df["merchant_name"].value_counts().head(10))
