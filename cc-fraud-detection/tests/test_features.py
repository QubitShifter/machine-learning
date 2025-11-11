import pandas as pd
from src.features import build_feature_matrix


def test_build_feature_matrix_basic():
    df = pd.DataFrame({
        "transaction_id": [1, 2],
        "employee_id": ["e001", "e001"],
        "gender": ["m", "m"],
        "tx_datetime": ["2025-01-01 10:00", "2025-01-01 22:30"],
        "amount": [10.0, 20.0],
        "merchant_name": ["workcanteen", "workcanteen"],
        "mcc_category": ["restaurant", "restaurant"],
        "is_whitelisted_merchant": [1, 1],
        "has_business_trip": [0, 0],
        "is_misuse": [0, 0],
        "country": ["de", "de"],
        "city": ["berlin", "berlin"],
    })

    X, y, cat_features, num_features = build_feature_matrix(df, "is_misuse")
    assert X.shape[0] == 2
    assert "hour" in X.columns
    assert "emp_tx_count" in X.columns
    assert "gender" in X.columns
