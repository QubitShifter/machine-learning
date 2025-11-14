import pandas as pd

# ---------- time features ----------
def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "tx_datetime" in df.columns:
        df["tx_datetime"] = pd.to_datetime(df["tx_datetime"])
    if "hour" not in df.columns:
        df["hour"] = df["tx_datetime"].dt.hour
    df["weekday"]    = df["tx_datetime"].dt.weekday
    df["is_weekend"] = (df["weekday"] >= 5).astype(int)
    df["is_late"]    = ((df["hour"] >= 21) | (df["hour"] < 6)).astype(int)
    return df

# ---------- per-employee aggregates (ONE place, consistent names) ----------
def add_behavioral_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # assumes add_time_features() already ran (so is_late / is_weekend exist)
    emp_stats = (
        df.groupby("employee_id").agg(
            emp_tx_count      = ("transaction_id", "count"),
            emp_amount_mean   = ("amount", "mean"),
            emp_amount_std    = ("amount", "std"),
            emp_late_ratio    = ("is_late", "mean"),
            emp_weekend_ratio = ("is_weekend", "mean"),
        )
        .reset_index()
    )
    # std can be NaN for single-transaction employees
    emp_stats["emp_amount_std"] = emp_stats["emp_amount_std"].fillna(0.0)

    df = df.merge(emp_stats, on="employee_id", how="left")
    # fill any residual NaNs (e.g., if employee_id was missing)
    df[[
        "emp_tx_count",
        "emp_amount_mean",
        "emp_amount_std",
        "emp_late_ratio",
        "emp_weekend_ratio",
    ]] = df[[
        "emp_tx_count",
        "emp_amount_mean",
        "emp_amount_std",
        "emp_late_ratio",
        "emp_weekend_ratio",
    ]].fillna(
        {"emp_tx_count": 0, "emp_amount_mean": 0.0, "emp_amount_std": 0.0,
         "emp_late_ratio": 0.0, "emp_weekend_ratio": 0.0}
    )

    # enforce numeric dtypes
    df["emp_tx_count"]       = df["emp_tx_count"].astype(int)
    df["emp_amount_mean"]    = df["emp_amount_mean"].astype(float)
    df["emp_amount_std"]     = df["emp_amount_std"].astype(float)
    df["emp_late_ratio"]     = df["emp_late_ratio"].astype(float)
    df["emp_weekend_ratio"]  = df["emp_weekend_ratio"].astype(float)
    return df

# ---------- main builder ----------
def build_feature_matrix(
    df: pd.DataFrame,
    target_col: str,
    drop_employee_id: bool = False,
    drop_emp_aggregates: bool = False,
):
    df = df.copy()

    # time features first
    df = add_time_features(df)

    # optional per-employee aggregates
    if not drop_emp_aggregates:
        df = add_behavioral_features(df)

    # target
    y = df[target_col].astype(int)

    # categorical features
    cat_features = [
        "gender",
        "merchant_name",
        "mcc_category",
        "country",
        "city",
    ]
    if not drop_employee_id:
        cat_features = ["employee_id"] + cat_features

    # numeric features
    base_num = ["amount", "hour", "weekday", "is_late", "is_weekend"]
    agg_num  = ["emp_tx_count", "emp_amount_mean", "emp_amount_std",
                "emp_late_ratio", "emp_weekend_ratio"]

    if drop_emp_aggregates:
        num_features = base_num
    else:
        num_features = base_num + agg_num

    # final X
    X = df[cat_features + num_features]

    return X, y, cat_features, num_features
