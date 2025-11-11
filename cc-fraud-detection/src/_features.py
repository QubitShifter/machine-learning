import pandas as pd


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    if "tx_datetime" in df.columns:
        df["tx_datetime"] = pd.to_datetime(df["tx_datetime"])
        df["hour"] = df["tx_datetime"].dt.hour
        df["weekday"] = df["tx_datetime"].dt.weekday
        df["is_weekend"] = (df["weekday"] >= 5).astype(int)
        df["is_late"] = ((df["hour"] >= 21) | (df["hour"] < 6)).astype(int)
    return df


def add_behavioral_features(df: pd.DataFrame) -> pd.DataFrame:
    grp = df.groupby("employee_id")

    stats = grp.agg(
        emp_tx_count=("transaction_id", "count"),
        emp_mean_amount=("amount", "mean"),
        emp_std_amount=("amount", "std"),
        emp_late_ratio=("is_late", "mean"),
        emp_weekend_ratio=("is_weekend", "mean"),
        emp_whitelist_ratio=("is_whitelisted_merchant", "mean"),
    ).reset_index()

    df = df.merge(stats, on="employee_id", how="left")
    df["emp_std_amount"] = df["emp_std_amount"].fillna(0.0)
    return df


def build_feature_matrix(df: pd.DataFrame, target_col: str):
    df = add_time_features(df.copy())
    df = add_behavioral_features(df)

    y = df[target_col].astype(int)

    cat_features = [
        "employee_id",
        "gender",
        "merchant_name",
        "mcc_category",
        "country",
        "city",
    ]

    num_features = [
        "amount",
        "hour",
        "weekday",
        "is_late",
        "is_weekend",
        "is_whitelisted_merchant",
        "has_business_trip",
        "emp_tx_count",
        "emp_mean_amount",
        "emp_std_amount",
        "emp_late_ratio",
        "emp_weekend_ratio",
        "emp_whitelist_ratio",
    ]

    X = df[cat_features + num_features]

    return X, y, cat_features, num_features
