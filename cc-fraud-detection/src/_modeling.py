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
)

from .config import synth_transactions_csv
from .features import build_feature_matrix


def main():
    # 1) load data
    df = pd.read_csv(synth_transactions_csv, parse_dates=["tx_datetime"])

    # 2) build features and target
    #    (_features.py already adds time + behavioral features)
    X, y, cat_features, num_features = build_feature_matrix(df, "is_misuse")

    # 3) split into train/test (80/20), stratified by misuse
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    # 4) preprocessing: one-hot categorical, passthrough numerics
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features),
            ("num", "passthrough", num_features),
        ]
    )

    # 5) classifier: gradient boosting (good tabular baseline)
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
            max_iter=200,
            n_jobs=-1,
        ),
    }

    # 6) full pipeline: preprocessing + model
    for name, clf in models.items():
        model = Pipeline([
            ("prep", preprocessor),
            ("clf", clf),
        ])
        model.fit(X_train, y_train)
        y_score = model.predict_proba(X_test)[:, 1]
        pr_auc = average_precision_score(y_test, y_score)
        print(name, "pr-auc:", round(pr_auc, 4))

    # 7) fit on train only
    model.fit(X_train, y_train)

    # 8) evaluate on test
    y_score = model.predict_proba(X_test)[:, 1]

    # precision-recall / pr-auc (very relevant for fraud)
    pr_auc = average_precision_score(y_test, y_score)
    print(f"test pr-auc: {pr_auc:.4f}")

    # find threshold with best F1 for illustration
    prec, rec, thr = precision_recall_curve(y_test, y_score)
    f1 = (2 * prec * rec) / (prec + rec + 1e-12)
    best_i = int(np.nanargmax(f1[:-1]))
    best_thr = thr[best_i]

    print(f"best f1 threshold = {best_thr:.3f}")
    print(f"precision = {prec[best_i]:.3f}, recall = {rec[best_i]:.3f}")

    # predictions at chosen threshold
    y_pred = (y_score >= best_thr).astype(int)

    print("\nconfusion matrix:")
    print(confusion_matrix(y_test, y_pred))

    print("\nclassification report:")
    print(classification_report(y_test, y_pred, digits=3))


if __name__ == "__main__":
    main()
