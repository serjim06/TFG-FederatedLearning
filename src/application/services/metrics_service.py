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
            y_true_total, y_pred_total = _resolve_regression_scatter_series(training_data)
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


def _resolve_regression_scatter_series(
    training_data: list[dict[str, Any]],
) -> tuple[list[float], list[float]]:

    if training_data:
        latest = training_data[-1]
        final_metrics = latest.get("final_metrics") or {}
        yt_final = list(final_metrics.get("y_true_final") or [])
        yp_final = list(final_metrics.get("y_pred_final") or [])
        if yt_final and yp_final:
            return yt_final, yp_final

        rounds = latest.get("results_per_round") or []
        if rounds:
            last_round_stats = rounds[-1].get("client_stats") or []
            yt_last: list[float] = []
            yp_last: list[float] = []
            for client in last_round_stats:
                if isinstance(client, dict) and "y_true" in client and "y_pred" in client:
                    yt_last.extend(client["y_true"])
                    yp_last.extend(client["y_pred"])
            if yt_last and yp_last:
                return yt_last, yp_last

    _, y_true_total, y_pred_total = get_regression_metrics_bundle(training_data)
    return y_true_total, y_pred_total
