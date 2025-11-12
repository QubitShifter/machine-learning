import json
from pathlib import Path

from sklearn.metrics import confusion_matrix

current_dir = Path(__file__).resolve()
root = current_dir.parents[2]
report_files_path = root / "reports" / "gb_v2_metrics.json"

with open(report_files_path, "r") as f:
    report_files_path = json.load(f)

print(report_files_path)

print(f"model: {report_files_path['model']}")
print(f"test_pr_auc: {report_files_path['test_pr_auc']}")
print(f"test_pr_auc: {report_files_path['test_pr_auc']:.4f}")
print(f"test_roc_auc: {report_files_path['test_roc_auc']}")
print(f"test_roc_auc: {report_files_path['test_roc_auc']:.4f}")
print(f"best_threshold: {report_files_path['best_threshold']}")
print(f"best_threshold: {report_files_path['best_threshold']:.4f}")
print(f"precision_at_best_f1: {report_files_path['precision_at_best_f1']}")
print(f"precision_at_best_f1: {report_files_path['precision_at_best_f1']:.4f}")
print(f"recall_at_best_f1: {report_files_path['recall_at_best_f1']}")
print(f"recall_at_best_f1: {report_files_path['recall_at_best_f1']:.4f}")

c_matrix = report_files_path["confusion_matrix"]
print("confusion_matrix:")
print(f"    TN={c_matrix[0] [0]}    FP={c_matrix[0] [1]}")
print(f"    FN={c_matrix[1] [0]}    TP={c_matrix[1] [1]}")

