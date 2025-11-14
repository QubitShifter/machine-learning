# src/scoring_v2.py
import argparse
import joblib
import pandas as pd
from .config import models_dir

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model-name", required=True)
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    return p.parse_args()

def main():
    args = parse_args()
    model_path = models_dir / f"{args.model_name}_fraud_model.pkl"
    model = joblib.load(model_path)

    df = pd.read_csv(args.input, parse_dates=["tx_datetime"])

    # the model’s pipeline expects the columns used in training.
    # If the fresh CSV is raw, consider reusing  build_feature_matrix() OR
    # keep the pipeline as end-to-end (preprocessor inside Pipeline), so raw cols are enough.

    y_proba = model.predict_proba(df)[:, 1]   # if the pipeline starts at raw df
    out = df.copy()
    out["misuse_score"] = y_proba
    out.to_csv(args.output, index=False)
    print("scored:", len(out), "rows →", args.output)

if __name__ == "__main__":
    main()
