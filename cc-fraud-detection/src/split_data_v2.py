import pandas as pd
from sklearn.model_selection import train_test_split

from .config import (
    synth_transactions_v2_csv,
    processed_dir,
    target_col,
)

def main():
    df = pd.read_csv(synth_transactions_v2_csv, parse_dates=["tx_datetime"])
    y = df[target_col].astype(int)

    train_df, test_df = train_test_split(
        df,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    train_path = processed_dir / "corp_card_v2_train_raw.csv"
    test_path = processed_dir / "corp_card_v2_test_raw.csv"

    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    print(f"saved train to {train_path} shape={train_df.shape}")
    print(f"saved test to {test_path} shape={test_df.shape}")


if __name__ == "__main__":
    main()
