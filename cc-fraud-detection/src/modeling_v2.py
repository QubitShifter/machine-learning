import json
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    confusion_matrix,
    classification_report,
    roc_auc_score,
)
import joblib

from .config import processed_dir, models_dir, reports_dir, target_col
from .features import build_feature_matrix


def main():
    train_path = processed_dir / "corp_card_v2_train_raw.csv"
    test_path = processed_dir / "corp_card_v2_test_raw.csv"

    df_train = pd.read_csv(train_path, parse_dates=["tx_datetime"])
    df_test = pd.read_csv(test_path, parse_dates=["tx_datetime"])

    # build features separately (без leakage)
    X_train, y_train, cat_features, num_features = build_feature_matrix(df_train, target_col)
    X_test, y_test, _, _ = build_feature_matrix(df_test, target_col)

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features),
            ("num", "passthrough", num_features),
        ]
    )

    clf = GradientBoostingClassifier(
        random_state=42,
        n_estimators=250,
        learning_rate=0.08,
        max_depth=4,
    )

    model = Pipeline([
        ("prep", preprocessor),
        ("clf", clf),
    ])

    print("training gb_v2 model ...")
    model.fit(X_train, y_train)

    y_score = model.predict_proba(X_test)[:, 1]

    pr_auc = average_precision_score(y_test, y_score)
    roc = roc_auc_score(y_test, y_score)

    prec, rec, thr = precision_recall_curve(y_test, y_score)
    f1 = (2 * prec * rec) / (prec + rec + 1e-12)
    best_i = int(np.nanargmax(f1[:-1]))
    best_thr = float(thr[best_i])
    p_star = float(prec[best_i])
    r_star = float(rec[best_i])

    y_pred = (y_score >= best_thr).astype(int)
    cm = confusion_matrix(y_test, y_pred)

    print(f"v2 test pr-auc: {pr_auc:.4f}, roc-auc: {roc:.4f}")
    print(f"best f1 threshold = {best_thr:.3f}")
    print(f"precision = {p_star:.3f}, recall = {r_star:.3f}")
    print("\nconfusion matrix:")
    print(cm)
    print("\nclassification report:")
    print(classification_report(y_test, y_pred, digits=3))

    # save model
    models_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    model_path = models_dir / "gb_v2_fraud_model.pkl"
    joblib.dump(model, model_path)
    print(f"saved gb_v2 model to {model_path}")

    # save metrics
    metrics = {
        "model": "gb_v2",
        "test_pr_auc": float(pr_auc),
        "test_roc_auc": float(roc),
        "best_threshold": best_thr,
        "precision_at_best_f1": p_star,
        "recall_at_best_f1": r_star,
        "confusion_matrix": cm.tolist(),
    }

    metrics_path = reports_dir / "gb_v2_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"saved metrics to {metrics_path}")

    # feature importances
    prep = model.named_steps["prep"]
    clf_fitted = model.named_steps["clf"]

    ohe = prep.named_transformers_["cat"]
    cat_out = ohe.get_feature_names_out(cat_features)
    num_out = np.array(num_features)
    all_features = np.concatenate([cat_out, num_out])

    if hasattr(clf_fitted, "feature_importances_"):
        importances = clf_fitted.feature_importances_
        fi = (
            pd.DataFrame({"feature": all_features, "importance": importances})
            .sort_values("importance", ascending=False)
        )
        fi_path = reports_dir / "gb_v2_feature_importances.csv"
        fi.to_csv(fi_path, index=False)
        print(f"saved feature importances to {fi_path}")

    return model


if __name__ == "__main__":
    main()
