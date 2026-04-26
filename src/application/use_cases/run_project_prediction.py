import json
import uuid
from typing import Any

from src.application.dto.operation_result import OperationResult
from src.application.repositories.node_repository import NodeRepository
from src.application.repositories.project_repository import ProjectRepository
from src.application.services.prediction_service import PredictionService


class RunProjectPredictionUseCase:
    """Run one prediction and persist pending confirmation entry."""

    def __init__(
        self,
        project_repository: ProjectRepository,
        node_repository: NodeRepository,
        prediction_service: PredictionService,
    ):
        self.project_repository = project_repository
        self.node_repository = node_repository
        self.prediction_service = prediction_service

    def execute(
        self,
        project_id: bytes,
        node_id: str,
        input_values: list[float],
    ) -> OperationResult[dict[str, Any]]:
        """Run prediction and append pending result in project storage."""
        project_row = self.project_repository.get_by_id(project_id)
        if not project_row:
            return OperationResult(ok=False, error="No se encontró el proyecto.")
        node_row = self.node_repository.get_by_id(uuid.UUID(node_id).bytes)
        if not node_row:
            return OperationResult(ok=False, error="No se encontró el nodo en la base de datos.")
        prediction_result = self.prediction_service.run_prediction(node_row, input_values, project_row)
        pending_raw = project_row.get("unconfirmed_results") or "[]"
        pending = json.loads(pending_raw) if isinstance(pending_raw, str) else list(pending_raw)
        pending.append(self._build_pending_entry(project_row, node_id, input_values, prediction_result))
        self.project_repository.update(
            {
                "id": project_id,
                "unconfirmed_results": json.dumps(pending, ensure_ascii=False),
            }
        )
        return OperationResult(
            ok=True,
            data={"project_name": project_row["name"], "prediction_result": prediction_result},
        )

    def _build_pending_entry(
        self,
        project_row: dict[str, Any],
        node_id: str,
        input_values: list[float],
        prediction_result: Any,
    ) -> dict[str, Any]:
        """Create one pending confirmation payload from prediction output."""
        in_features = (
            json.loads(project_row["input_features"])
            if isinstance(project_row["input_features"], str)
            else project_row["input_features"]
        )
        out_features = (
            json.loads(project_row["output_features"])
            if isinstance(project_row["output_features"], str)
            else project_row["output_features"]
        )
        output_values = self._prediction_outputs_for_pending(prediction_result, out_features)
        pending_data: dict[str, Any] = {}
        for key, value in zip(in_features, input_values):
            pending_data[key] = value
        for key, value in zip(out_features, output_values):
            pending_data[key] = value
        return {"node": f"node_{node_id}", "data": pending_data}

    @staticmethod
    def _prediction_outputs_for_pending(
        prediction_result: Any,
        output_features: list[str],
    ) -> list[Any]:
        """Normalize prediction output shape to expected output features."""
        if not output_features:
            return []
        if isinstance(prediction_result, dict):
            if len(output_features) == 1 and "label" in prediction_result:
                return [prediction_result["label"]]
            raw_output = prediction_result.get("output")
        else:
            raw_output = prediction_result
        if isinstance(raw_output, tuple):
            values = list(raw_output)
        elif isinstance(raw_output, list):
            values = raw_output
        else:
            values = [raw_output]
        if len(values) < len(output_features):
            values = values + [""] * (len(output_features) - len(values))
        return values[: len(output_features)]
