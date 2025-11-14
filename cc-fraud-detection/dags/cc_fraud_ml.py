# dags/cc_fraud_ml.py
from __future__ import annotations

import os
from datetime import datetime, timedelta

# alias classes to lowercase for use below
from airflow import DAG as dag
from airflow.models import Variable as variable
from airflow.providers.standard.operators.bash import BashOperator as bash_operator

# -----------------------------
# config via airflow variables
# -----------------------------
# set these in the airflow ui (admin → variables):
#   cc_project_dir -> absolute path to your project root (where src/ lives)
#   cc_python_bin  -> path to python executable inside your venv (optional)

cc_project_dir = variable.get("CC_PROJECT_DIR", default_var="/opt/airflow/projects/cc-fraud")
cc_python_bin  = variable.get("CC_PYTHON_BIN",  default_var="python")

# common environment so `python -m src...` sees your code
common_env = {
    "PYTHONPATH": cc_project_dir,  # must remain uppercase as it's an env var
    "PROJECT_DIR": cc_project_dir,
}

# a short helper for bashoperator commands
def cmd(line: str) -> str:
    # cd to project, export PYTHONPATH, run command
    return f'cd "{cc_project_dir}" && export PYTHONPATH="{cc_project_dir}" && {line}'

# ==============================================
# dag 1: weekly training pipeline (full rebuild)
# ==============================================
with dag(
    dag_id="cc_fraud_train_weekly",
    description="generate data → split → train/evaluate model → save artifacts",
    start_date=datetime(2025, 1, 1),
    schedule_interval="0 3 * * 1",  # every monday at 03:00
    catchup=False,
    default_args={
        "owner": "ml-team",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["cc-fraud", "training"],
) as dag_train:

    # 1) generate/refresh the big csv (v2 generator; 2m rows assumed in your script)
    gen_data = bash_operator(
        task_id="generate_data",
        bash_command=cmd(f'{cc_python_bin} -m src.data_gen_v2'),
        env=common_env,
    )

    # 2) split into processed train/test (stratified 80/20)
    split_data = bash_operator(
        task_id="split_data",
        bash_command=cmd(f'{cc_python_bin} -m src.split_data_v2'),
        env=common_env,
    )

    # 3) train + evaluate (gradient boosting by default; configurable via args)
    train_gb = bash_operator(
        task_id="train_gb_v2",
        bash_command=cmd(
            f'{cc_python_bin} -m src.modeling_v2 '
            f'--model-name gb_v2 '
            f'--clf gb'
        ),
        env=common_env,
    )

    # 4) optional additional run (hist gradient boosting) so artifacts don’t overwrite
    train_hgb = bash_operator(
        task_id="train_hgb_v2",
        bash_command=cmd(
            f'{cc_python_bin} -m src.modeling_v2 '
            f'--model-name hgb_v2 '
            f'--clf hgb'
        ),
        env=common_env,
        trigger_rule="all_done",  # still run even if previous train failed (optional)
    )

    # 5) optional: archive reports to a dated folder
    archive_reports = bash_operator(
        task_id="archive_reports",
        bash_command=cmd(
            'ts=$(date +%Y%m%d_%H%M%S) && '
            'mkdir -p reports/archives/$ts && '
            'cp -r reports/*.json reports/*.txt reports/*feature_importances*.csv reports/archives/$ts/ || true && '
            'echo "archived reports to reports/archives/$ts"'
        ),
        env=common_env,
    )

    # pipeline order
    gen_data >> split_data >> train_gb >> train_hgb >> archive_reports

# =========================================
# dag 2: daily scoring pipeline (stub/demo)
# =========================================
with dag(
    dag_id="cc_fraud_score_daily",
    description="load latest model and score fresh transactions (stub)",
    start_date=datetime(2025, 1, 1),
    schedule_interval="0 4 * * *",  # every day at 04:00
    catchup=False,
    default_args={
        "owner": "ml-team",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["cc-fraud", "scoring"],
) as dag_score:

    # 1) (optional) ingest fresh transactions into data/landing/fresh.csv
    fetch_fresh = bash_operator(
        task_id="fetch_fresh_transactions",
        bash_command=cmd('echo "todo: implement ingestion to data/landing/fresh.csv"'),
        env=common_env,
    )

    # 2) score using the chosen model + same feature pipe (write to data/scored/)
    score = bash_operator(
        task_id="score_with_latest_model",
        bash_command=cmd(
            f'{cc_python_bin} -m src.scoring_v2 '
            '--model-name gb_v2 '
            '--input data/landing/fresh.csv '
            '--output data/scored/fresh_scored.csv'
        ),
        env=common_env,
    )

    # 3) ship scored output somewhere (db, s3, bi layer) — stub
    ship = bash_operator(
        task_id="publish_scores",
        bash_command=cmd('echo "todo: implement publishing of data/scored/fresh_scored.csv"'),
        env=common_env,
    )

    fetch_fresh >> score >> ship
