# src/modeling_v2.py
import json
import joblib
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

from .config import processed_dir, models_dir, reports_dir, target_col
from .features import build_feature_matrix

# ---- name your run once; artifacts will use this prefix ----
model_name = "gb_v2_no_empid"  # e.g. "gb_v2", "gb_v2_deeper700", "hgb_v2", ...

def main():
    # ---- load split data ----
    train_path = processed_dir / "corp_card_v2_train_raw.csv"
    test_path  = processed_dir / "corp_card_v2_test_raw.csv"

    df_train = pd.read_csv(train_path, parse_dates=["tx_datetime"])
    df_test  = pd.read_csv(test_path,  parse_dates=["tx_datetime"])

    # ---- build features (separately; avoids leakage) ----
    X_train, y_train, cat_features, num_features = build_feature_matrix(
        df_train, target_col, drop_employee_id=True
    )
    X_test,  y_test,  _,            _           = build_feature_matrix(
        df_test,  target_col, drop_employee_id=True
    )

    # ---- preprocessing ----
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features),
            ("num", "passthrough", num_features),
        ]
    )

    # ---- classifier ----
    clf = GradientBoostingClassifier(
        random_state=42,
        n_estimators=250,
        learning_rate=0.08,
        max_depth=4,
    )

    # ---- pipeline ----
    model = Pipeline([
        ("prep", preprocessor),
        ("clf",  clf),
    ])

    print(f"training {model_name} model ...")
    model.fit(X_train, y_train)

    # ---- predict proba on test ----
    y_score = model.predict_proba(X_test)[:, 1]

    # ---- metrics ----
    pr_auc = average_precision_score(y_test, y_score)
    roc    = roc_auc_score(y_test, y_score)

    prec, rec, thr = precision_recall_curve(y_test, y_score)
    f1 = (2 * prec * rec) / (prec + rec + 1e-12)
    best_i  = int(np.nanargmax(f1[:-1]))  # align with thr length
    best_thr = float(thr[best_i])
    p_star   = float(prec[best_i])
    r_star   = float(rec[best_i])

    y_pred = (y_score >= best_thr).astype(int)
    cm = confusion_matrix(y_test, y_pred)
    report_str = classification_report(y_test, y_pred, digits=3)

    print(f"{model_name} test pr-auc: {pr_auc:.4f}, roc-auc: {roc:.4f}")
    print(f"best f1 threshold = {best_thr:.3f}")
    print(f"precision = {p_star:.3f}, recall = {r_star:.3f}")
    print("\nconfusion matrix:")
    print(cm)
    print("\nclassification report:")
    print(report_str)

    # ---- ensure folders ----
    models_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    # ---- save model ----
    model_path = models_dir / f"{model_name}_fraud_model.pkl"
    joblib.dump(model, model_path)
    print(f"saved {model_name} model to {model_path}")

    # ---- metrics JSON ----
    tn, fp, fn, tp = cm.ravel().tolist()
    metrics = {
        "model": model_name,
        "test_pr_auc": float(pr_auc),
        "test_roc_auc": float(roc),
        "best_threshold": best_thr,
        "precision_at_best_f1": p_star,
        "recall_at_best_f1": r_star,
        "confusion_matrix": [[tn, fp], [fn, tp]],
        "n_test": int(len(y_test)),
        "positive_rate_test": float(np.mean(y_test)),
    }
    metrics_path = reports_dir / f"{model_name}_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))
    print(f"saved metrics to {metrics_path}")

    # ---- save classification report text ----
    (reports_dir / f"{model_name}_classification_report.txt").write_text(report_str)

    # ---- export feature importances / coefficients if available ----
    fi_path = reports_dir / f"{model_name}_feature_importances.csv"
    try:
        prep = model.named_steps["prep"]
        clf_fitted = model.named_steps["clf"]

        ohe = prep.named_transformers_["cat"]
        cat_out = ohe.get_feature_names_out(cat_features)
        num_out = np.array(num_features, dtype=object)
        all_features = np.concatenate([cat_out, num_out])

        if hasattr(clf_fitted, "feature_importances_"):
            fi_df = (
                pd.DataFrame({
                    "feature": all_features,
                    "importance": clf_fitted.feature_importances_
                })
                .sort_values("importance", ascending=False)
            )
            fi_df.to_csv(fi_path, index=False)
            print(f"saved feature importances to {fi_path}")

        elif hasattr(clf_fitted, "coef_"):
            coef = np.ravel(clf_fitted.coef_)
            fi_df = (
                pd.DataFrame({
                    "feature": all_features,
                    "coefficient": coef
                })
                .sort_values("coefficient", key=lambda s: np.abs(s), ascending=False)
            )
            fi_df.to_csv(fi_path, index=False)
            print(f"saved coefficients to {fi_path}")

        else:
            note_path = reports_dir / f"{model_name}_notes.txt"
            note_path.write_text(
                "Classifier does not expose feature_importances_ or coef_."
            )
            print(f"no importances/coef_; wrote note to {note_path}")

    except Exception as e:
        err_path = reports_dir / f"{model_name}_fi_error.txt"
        err_path.write_text(str(e))
        print(f"feature importance export failed; see {err_path}")

    return model


if __name__ == "__main__":
    main()
