import json
import tkinter as tk
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.gui.project_metrics import (
    ProjectMetricsDialog,
    get_metrics_per_round,
    get_regression_metrics_bundle,
    get_datasets_changes,
    get_time_per_round,
)

def test_classification():
    filepath = Path(__file__).parent / "sample_results.json"
    with open(filepath, "r", encoding="utf-8") as f:
        training_data = json.load(f)

    metrics = get_metrics_per_round(training_data, "classification")
    time_per_round = get_time_per_round(training_data)
    datasets_changes = get_datasets_changes(["node1", "node2"])

    project_data = {
        "type": "classification",
        "name": "Dummy Classification",
        "metrics": metrics,
        "time_per_round": time_per_round,
        "datasets_changes": datasets_changes,
        "loss": [m.get("loss", 0) for m in metrics]
    }

    root = tk.Tk()
    
    print("Showing Classification Metrics Dialog...")
    dialog = ProjectMetricsDialog(root, training_data, project_data, title="Métricas de Clasificación")
    dialog.wait_window()
    print("Classification Dialog closed.\n")
    root.destroy()

def test_regression():
    filepath = Path(__file__).parent / "sample_regression.json"
    with open(filepath, "r", encoding="utf-8") as f:
        training_data = json.load(f)

    metrics = get_metrics_per_round(training_data, "regression")
    _, y_true_total, y_pred_total = get_regression_metrics_bundle(training_data)
    time_per_round = get_time_per_round(training_data)
    datasets_changes = get_datasets_changes(["node1", "node2"])

    project_data = {
        "type": "regression",
        "name": "Dummy Regression",
        "metrics": metrics,
        "time_per_round": time_per_round,
        "datasets_changes": datasets_changes,
        "y_true": y_true_total,
        "y_pred": y_pred_total,
        "loss": [m.get("loss", 0) for m in metrics]
    }

    root = tk.Tk()

    print("Showing Regression Metrics Dialog...")
    dialog = ProjectMetricsDialog(root, training_data, project_data, title="Métricas de Regresión")
    dialog.wait_window()
    print("Regression Dialog closed.\n")
    root.destroy()

if __name__ == "__main__":
    print("--- Testing Classification ---")
    test_classification()
    print("--- Testing Regression ---")
    test_regression()
