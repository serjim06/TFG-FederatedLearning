from typing import Any

from src.models.node import Node, predict


class PredictionService:
    """Execute node-level predictions for one project."""

    def run_prediction(
        self,
        node_row: dict[str, Any],
        input_values: list[float],
        project_row: dict[str, Any],
    ) -> Any:
        """Predict one sample using one node and one project."""
        node = Node(node_row["id"], node_row["valid"], node_row["project_id"])
        return predict(node, input_values, project=dict(project_row))
