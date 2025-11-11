import json
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    confusion_matrix,
    classification_report,
    roc_auc_score,
)
import joblib

from .config import synth_transactions_csv, target_col, models_dir, reports_dir
from .features import build_feature_matrix


def train_and_evaluate():
    # 1) load data
    df = pd.read_csv(synth_transactions_csv, parse_dates=["tx_datetime"])

    # optional: uncomment to speed up experiments
    # df = df.sample(400_000, random_state=42).reset_index(drop=True)

    # 2) build X, y, and feature lists
    X, y, cat_features, num_features = build_feature_matrix(df, target_col)

    # 3) train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    # 4) shared preprocessor
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features),
            ("num", "passthrough", num_features),
        ]
    )

    # 5) define candidate models
    models = {
        "gb_small": GradientBoostingClassifier(
            random_state=42,
            n_estimators=200,
            learning_rate=0.1,
            max_depth=3,
        ),
        "gb_deeper": GradientBoostingClassifier(
            random_state=42,
            n_estimators=400,
            learning_rate=0.05,
            max_depth=5,
        ),
        "rf": RandomForestClassifier(
            random_state=42,
            n_estimators=300,
            max_depth=None,
            n_jobs=-1,
            class_weight="balanced_subsample",
        ),
        "logreg": LogisticRegression(
            random_state=42,
            max_iter=500,
            n_jobs=-1,
        ),
    }

    results = {}

    # 6) loop over models and compute PR-AUC
    for name, clf in models.items():
        pipe = Pipeline([
            ("prep", preprocessor),
            ("clf", clf),
        ])

        print(f"training {name} ...")
        pipe.fit(X_train, y_train)

        y_score = pipe.predict_proba(X_test)[:, 1]
        pr_auc = average_precision_score(y_test, y_score)
        roc = roc_auc_score(y_test, y_score)

        print(f"{name} pr-auc: {pr_auc:.4f}, roc-auc: {roc:.4f}")

        results[name] = {
            "model": pipe,
            "y_score": y_score,
            "pr_auc": float(pr_auc),
            "roc_auc": float(roc),
        }

    # 7) pick best by PR-AUC
    best_name = max(results.keys(), key=lambda n: results[n]["pr_auc"])
    best = results[best_name]
    best_model = best["model"]
    y_score = best["y_score"]

    print(f"\nbest model: {best_name} (pr-auc={best['pr_auc']:.4f})")

    # 8) detailed metrics for best model
    prec, rec, thr = precision_recall_curve(y_test, y_score)
    f1 = (2 * prec * rec) / (prec + rec + 1e-12)
    best_i = int(np.nanargmax(f1[:-1]))
    best_thr = float(thr[best_i])
    p_star = float(prec[best_i])
    r_star = float(rec[best_i])

    y_pred = (y_score >= best_thr).astype(int)

    cm = confusion_matrix(y_test, y_pred)
    print(f"test pr-auc: {best['pr_auc']:.4f}")
    print(f"best f1 threshold = {best_thr:.3f}")
    print(f"precision = {p_star:.3f}, recall = {r_star:.3f}")
    print("\nconfusion matrix:")
    print(cm)
    print("\nclassification report:")
    print(classification_report(y_test, y_pred, digits=3))

    # 9) ensure dirs exist (config already does, but safe)
    Path(models_dir).mkdir(parents=True, exist_ok=True)
    Path(reports_dir).mkdir(parents=True, exist_ok=True)

    # 10) save best model
    model_path = Path(models_dir) / f"{best_name}_fraud_model.pkl"
    joblib.dump(best_model, model_path)
    print(f"\nsaved best model to {model_path}")

    # 11) save metrics
    metrics = {
        "best_model": best_name,
        "test_pr_auc": best["pr_auc"],
        "test_roc_auc": best["roc_auc"],
        "best_threshold": best_thr,
        "precision_at_best_f1": p_star,
        "recall_at_best_f1": r_star,
        "confusion_matrix": cm.tolist(),
    }

    metrics_path = Path(reports_dir) / f"{best_name}_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"saved metrics to {metrics_path}")

    # 12) save feature importances or coefficients
    prep = best_model.named_steps["prep"]
    clf = best_model.named_steps["clf"]

    # get feature names after one-hot
    ohe = prep.named_transformers_["cat"]
    cat_out = ohe.get_feature_names_out(cat_features)
    num_out = np.array(num_features)
    all_features = np.concatenate([cat_out, num_out])

    # tree-based models: feature_importances_
    if hasattr(clf, "feature_importances_"):
        importances = clf.feature_importances_
        fi = (
            pd.DataFrame({"feature": all_features, "importance": importances})
            .sort_values("importance", ascending=False)
        )
        fi_path = Path(reports_dir) / f"{best_name}_feature_importances.csv"
        fi.to_csv(fi_path, index=False)
        print(f"saved feature importances to {fi_path}")

    # logistic regression: coef_
    elif hasattr(clf, "coef_"):
        coefs = clf.coef_.ravel()
        coef_df = (
            pd.DataFrame({"feature": all_features, "coef": coefs})
            .sort_values("coef", ascending=False)
        )
        coef_path = Path(reports_dir) / f"{best_name}_coefficients.csv"
        coef_df.to_csv(coef_path, index=False)
        print(f"saved coefficients to {coef_path}")

    else:
        print("no importances/coefficients available for this model type")

    return best_model


if __name__ == "__main__":
    train_and_evaluate()
