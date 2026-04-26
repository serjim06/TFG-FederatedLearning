from collections import Counter
from pathlib import Path
import re

import numpy as np
from sklearn.metrics import f1_score, r2_score


def get_metrics_per_round(training_data, project_type):
    """Return round metrics for classification or regression projects."""
    if project_type == "classification":
        return _get_classification_metrics(training_data)
    metrics, _, _ = _get_regression_metrics(training_data)
    return metrics


def get_regression_metrics_bundle(training_data):
    """Return regression metrics plus flattened y_true/y_pred series."""
    return _get_regression_metrics(training_data)


def round_indices_for_metrics(metrics: list) -> list[int]:
    """Return one-based round indices for plotted metrics."""
    return list(range(1, len(metrics) + 1))


def get_datasets_changes(nodes):
    """Collect dataset additions per node and composed by round."""
    datasets_changes = {}
    composed_changes = {}
    for node in nodes:
        path = Path(__file__).resolve().parent.parent.parent.parent / "database" / "datasets" / node
        pattern = re.compile(r"dataset_(\d+)\.csv")
        found_files = []
        if not path.exists():
            continue
        for file_path in path.glob("dataset_*.csv"):
            match = pattern.search(file_path.name)
            if match:
                found_files.append((int(match.group(1)), file_path))
        if found_files:
            datasets_changes[node] = _get_files_changes(found_files)
            for change in datasets_changes[node].values():
                if not isinstance(change, dict):
                    continue
                if change["round"] not in composed_changes:
                    composed_changes[change["round"]] = {"added": [], "length": 0}
                composed_changes[change["round"]]["added"].extend(change["added"])
                composed_changes[change["round"]]["length"] += change["length"]
    return {"datasets_changes": datasets_changes, "composed_changes": composed_changes}


def get_time_per_round(training_data):
    """Return elapsed seconds per round."""
    time_per_round = []
    for training in training_data:
        for round_data in training["results_per_round"]:
            time_per_round.append(round_data["time"])
    return time_per_round


def _get_classification_metrics(training_data):
    metrics = []
    for training in training_data:
        total_clients = max(len(training["config"]["total_clients"]), 1)
        for round_data in training["results_per_round"]:
            loss = round_data["global_loss"]
            acc = round_data.get("global_accuracy", 0.0)
            cs = round_data.get("client_stats") or []
            part = float(round_data.get("participating_clients", len(cs))) / total_clients
            has_cm = bool(cs and isinstance(cs[0], dict) and "confusion_matrix" in cs[0])
            if has_cm:
                y_true: list[int] = []
                y_pred: list[int] = []
                for client in cs:
                    matrix = np.array(client["confusion_matrix"])
                    for i in range(matrix.shape[0]):
                        for j in range(matrix.shape[1]):
                            amount = matrix[i, j]
                            y_true.extend([i] * amount)
                            y_pred.extend([j] * amount)
                f1 = float(f1_score(y_true, y_pred, average="weighted"))
            else:
                f1 = float("nan")
            metrics.append({"loss": loss, "accuracy": acc, "f1": f1, "participation": part})
    return metrics


def _get_files_changes(files):
    changes = {}
    sorted_files = sorted(files, key=lambda x: x[0])
    file_0 = sorted_files[0][1]
    with open(file_0, "r", encoding="utf-8") as file_obj:
        lines_prev = file_obj.readlines()
        changes[0] = {"round": sorted_files[0][0], "added": [], "length": len(lines_prev) - 1}
        for line in lines_prev[1:]:
            changes[0]["added"].append(line.strip().split(","))
    for i in range(1, len(sorted_files)):
        file_i = sorted_files[i][1]
        with open(file_i, "r", encoding="utf-8") as file_obj:
            lines_curr = file_obj.readlines()
            changes[i] = {"round": sorted_files[i][0], "added": [], "length": len(lines_curr) - 1}
            prev_counter = Counter(line.strip() for line in lines_prev[1:])
            curr_counter = Counter(line.strip() for line in lines_curr[1:])
            for row_text, curr_count in curr_counter.items():
                added_count = curr_count - prev_counter.get(row_text, 0)
                if added_count > 0:
                    for _ in range(added_count):
                        changes[i]["added"].append(row_text.split(","))
            lines_prev = lines_curr
    return changes


def _get_regression_metrics(training_data):
    metrics = []
    y_true_total: list[float] = []
    y_pred_total: list[float] = []
    for training in training_data:
        total_clients = max(len(training["config"]["total_clients"]), 1)
        for round_data in training["results_per_round"]:
            loss = round_data["global_loss"]
            cs = round_data.get("client_stats") or []
            part = float(round_data.get("participating_clients", len(cs))) / total_clients
            persisted_r2 = round_data.get("global_r2")
            if persisted_r2 is not None:
                try:
                    r2 = float(persisted_r2)
                except (TypeError, ValueError):
                    r2 = float("nan")
                metrics.append({"loss": loss, "r2": r2, "participation": part})
                continue
            has_y = bool(cs and isinstance(cs[0], dict) and "y_true" in cs[0])
            if has_y:
                y_true: list[float] = []
                y_pred: list[float] = []
                for client in cs:
                    y_true.extend(client["y_true"])
                    y_pred.extend(client["y_pred"])
                y_true_total.extend(y_true)
                y_pred_total.extend(y_pred)
                r2 = float(r2_score(y_true, y_pred))
            else:
                r2 = float("nan")
            metrics.append({"loss": loss, "r2": r2, "participation": part})
    return metrics, y_true_total, y_pred_total
