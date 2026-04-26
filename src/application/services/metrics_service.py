import json
import uuid
from typing import Any

from src.application.services.project_metrics_calculations import (
    get_datasets_changes,
    get_metrics_per_round,
    get_regression_metrics_bundle,
    get_time_per_round,
)


class MetricsService:
    """Compute project metrics for the metrics view."""

    def build_project_metrics_payload(
        self,
        project_row: dict[str, Any],
        nodes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Return computed metrics and derived values for one project."""
        training_data = json.loads(project_row["training_results"])
        project_type = project_row["type"]
        metrics = get_metrics_per_round(training_data, project_type)
        if project_type == "regression":
            _, y_true_total, y_pred_total = get_regression_metrics_bundle(training_data)
        else:
            y_true_total, y_pred_total = [], []
        time_per_round = get_time_per_round(training_data)
        node_ids = [str(uuid.UUID(bytes=node["id"])) for node in nodes]
        datasets_changes = get_datasets_changes(node_ids)
        return {
            "training_data": training_data,
            "project_type": project_type,
            "metrics": metrics,
            "time_per_round": time_per_round,
            "datasets_changes": datasets_changes,
            "y_true_total": y_true_total,
            "y_pred_total": y_pred_total,
        }
