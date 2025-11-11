import pandas as pd


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    if "tx_datetime" in df.columns:
        df["tx_datetime"] = pd.to_datetime(df["tx_datetime"])
    if "hour" not in df.columns:
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
    ).reset_index()

    df = df.merge(stats, on="employee_id", how="left")
    df["emp_std_amount"] = df["emp_std_amount"].fillna(0.0)
    return df


def build_feature_matrix(df: pd.DataFrame, target_col: str):
    df = df.copy()
    df = add_time_features(df)
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

    # do NOT include is_whitelisted_merchant or has_business_trip
    num_features = [
        "amount",
        "hour",
        "weekday",
        "is_late",
        "is_weekend",
        "emp_tx_count",
        "emp_mean_amount",
        "emp_std_amount",
        "emp_late_ratio",
        "emp_weekend_ratio",
    ]

    X = df[cat_features + num_features]

    return X, y, cat_features, num_features
