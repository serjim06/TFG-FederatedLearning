import json
import os
from pathlib import Path
import shutil
import uuid
from typing import Any

from src.application.dto.operation_result import OperationResult
from src.application.repositories.node_repository import NodeRepository
from src.application.repositories.project_repository import ProjectRepository
from src.db.dbcon import sqlite_timestamp_now


class CreateProjectUseCase:
    """Create one project and synchronize selected nodes."""

    def __init__(
        self,
        project_repository: ProjectRepository,
        node_repository: NodeRepository,
    ):
        self.project_repository = project_repository
        self.node_repository = node_repository

    def execute(self, user_id: bytes, form_data: dict[str, Any]) -> OperationResult[dict[str, Any]]:
        """Persist a new project from normalized form data."""
        copied_model_path = self._copy_model(user_id, form_data["model_path"])
        payload = {
            "uid": user_id,
            "name": form_data["name"],
            "description": form_data["description"],
            "parameters": json.dumps(form_data["parameters"]),
            "aggregation_strategy": form_data["aggregation_strategy"],
            "metrics": form_data["metrics"],
            "model_path": Path(copied_model_path).as_posix(),
            "input_features": json.dumps(form_data["input_features"]),
            "output_features": json.dumps(form_data["output_features"]),
            "unconfirmed_results": json.dumps([]),
            "type": form_data["task_type"],
            "created_at": sqlite_timestamp_now(),
        }
        project_row = self.project_repository.create(payload)
        selected_nodes = form_data["initial_nodes"]
        for node_id in selected_nodes:
            self.node_repository.update(
                {
                    "id": uuid.UUID(node_id).bytes,
                    "valid": 1,
                    "project_id": project_row["id"],
                }
            )
        return OperationResult(ok=True, data=project_row)

    def inspect_model(self, model_class: type) -> dict[str, Any]:
        """Inspect selected model class and return normalized metadata for project creation."""
        input_features, output_features, suggested_task = self._load_features(model_class)
        return {
            "input_features": input_features,
            "output_features": output_features,
            "suggested_task": suggested_task,
        }

    def _copy_model(self, user_id: bytes, source_path: str) -> str:
        """Copy the selected model into the user model directory and return a relative path."""
        base_dir = os.path.join(os.getcwd(), "database", "models", str(uuid.UUID(bytes=user_id)))
        file_name = os.path.basename(source_path)
        destination = os.path.join(base_dir, file_name)
        os.makedirs(base_dir, exist_ok=True)
        try:
            shutil.copy2(source_path, destination)
            return os.path.relpath(destination, start=os.getcwd())
        except Exception as exc:
            raise OSError(f"No se pudo copiar el archivo: {str(exc)}") from exc

    def _load_features(self, model_class: type) -> tuple[list[Any], list[Any], str | None]:
        """Instantiate model_class and validate/get input-output features and suggested task type."""
        model = model_class()
        required_keys = {"input_features", "output_features"}
        features = model.get_features()
        is_valid = (
            isinstance(features, dict)
            and required_keys.issubset(features.keys())
            and all(isinstance(features[key], list) for key in required_keys)
        )
        if not is_valid:
            raise ValueError(
                "El método get_features() debe retornar un diccionario con las claves "
                "'input_features' y 'output_features', cuyos valores deben ser listas de nombres de características."
            )
        suggested = None
        metadata = features.get("metadata")
        if isinstance(metadata, dict):
            suggested = self._coerce_task_type(metadata.get("type"))
        if suggested is None:
            suggested = self._coerce_task_type(features.get("type"))
        return features["input_features"], features["output_features"], suggested

    @staticmethod
    def _coerce_task_type(raw: Any) -> str | None:
        """Normalize raw task type strings to supported values or None."""
        if not isinstance(raw, str) or not raw.strip():
            return None
        task_type = raw.strip().lower()
        if task_type in ("regression", "regresssion"):
            return "regression"
        if task_type == "classification":
            return "classification"
        return None
