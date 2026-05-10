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
    """Collect dataset snapshots per node and composed totals by round.
    """
    datasets_root = Path(__file__).resolve().parents[3] / "database" / "datasets"
    pattern = re.compile(r"dataset_(\d+)\.csv")
    datasets_changes: dict[str, dict[int, dict]] = {}
    for node in nodes:
        node_dir = datasets_root / f"node_{node}"
        if not node_dir.exists():
            continue
        found_files: list[tuple[int, Path]] = []
        for file_path in node_dir.glob("dataset_*.csv"):
            match = pattern.search(file_path.name)
            if match:
                found_files.append((int(match.group(1)), file_path))
        if found_files:
            datasets_changes[node] = _per_node_snapshots(found_files)
    composed_changes = _compose_dataset_snapshots(datasets_changes)
    return {"datasets_changes": datasets_changes, "composed_changes": composed_changes}


def _per_node_snapshots(files: list[tuple[int, Path]]) -> dict[int, dict]:
    snapshots: dict[int, dict] = {}
    sorted_files = sorted(files, key=lambda x: x[0])
    first_round, first_path = sorted_files[0]
    with open(first_path, "r", encoding="utf-8") as file_obj:
        prev_lines = file_obj.readlines()
    snapshots[first_round] = {
        "length": max(0, len(prev_lines) - 1),
        "added": [line.strip().split(",") for line in prev_lines[1:]],
    }
    for cur_round, cur_path in sorted_files[1:]:
        with open(cur_path, "r", encoding="utf-8") as file_obj:
            cur_lines = file_obj.readlines()
        prev_counter = Counter(line.strip() for line in prev_lines[1:])
        cur_counter = Counter(line.strip() for line in cur_lines[1:])
        added: list[list[str]] = []
        for row_text, cur_count in cur_counter.items():
            diff = cur_count - prev_counter.get(row_text, 0)
            if diff > 0:
                added.extend(row_text.split(",") for _ in range(diff))
        snapshots[cur_round] = {
            "length": max(0, len(cur_lines) - 1),
            "added": added,
        }
        prev_lines = cur_lines
    return snapshots


def _compose_dataset_snapshots(
    per_node_snapshots: dict[str, dict[int, dict]],
) -> dict[int, dict]:
    """Aggregate per-node snapshots so each round reports total project volume."""
    composed: dict[int, dict] = {}
    if not per_node_snapshots:
        return composed
    all_rounds = sorted({rnd for snaps in per_node_snapshots.values() for rnd in snaps})
    for rnd in all_rounds:
        total_length = 0
        total_added: list[list[str]] = []
        for node_snaps in per_node_snapshots.values():
            previous_rounds = [r for r in node_snaps if r <= rnd]
            if previous_rounds:
                total_length += node_snaps[max(previous_rounds)]["length"]
            if rnd in node_snaps:
                total_added.extend(node_snaps[rnd]["added"])
        composed[rnd] = {"length": total_length, "added": total_added}
    return composed


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
            has_y = bool(cs and isinstance(cs[0], dict) and "y_true" in cs[0])
            round_y_true: list[float] = []
            round_y_pred: list[float] = []
            if has_y:
                for client in cs:
                    round_y_true.extend(client["y_true"])
                    round_y_pred.extend(client["y_pred"])
                y_true_total.extend(round_y_true)
                y_pred_total.extend(round_y_pred)
            persisted_r2 = round_data.get("global_r2")
            if persisted_r2 is not None:
                try:
                    r2 = float(persisted_r2)
                except (TypeError, ValueError):
                    r2 = float("nan")
            elif has_y:
                r2 = float(r2_score(round_y_true, round_y_pred))
            else:
                r2 = float("nan")
            metrics.append({"loss": loss, "r2": r2, "participation": part})
    return metrics, y_true_total, y_pred_total
