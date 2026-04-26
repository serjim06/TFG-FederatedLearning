import json
from pathlib import Path

from src.application.dto.operation_result import OperationResult
from src.application.repositories.project_repository import ProjectRepository
from src.application.services.dataset_service import DatasetService


class ConfirmPendingResultUseCase:
    """Persist confirmed or corrected pending rows into node datasets."""

    def __init__(
        self,
        project_repository: ProjectRepository,
        dataset_service: DatasetService,
    ):
        self.project_repository = project_repository
        self.dataset_service = dataset_service

    def persist_unconfirmed(self, project_id: bytes, pending: list[dict]) -> OperationResult[None]:
        """Persist pending confirmation list into project storage."""
        self.project_repository.update(
            {
                "id": project_id,
                "unconfirmed_results": json.dumps(pending, ensure_ascii=False),
            }
        )
        return OperationResult(ok=True)

    def append_confirmed_row(
        self,
        pending_item: dict,
        cur_round: int,
        in_labels: list[str],
        out_labels: list[str],
    ) -> OperationResult[None]:
        """Append one confirmed pending row as-is to node dataset."""
        node = pending_item["node"]
        node_uuid = node.replace("node_", "")
        path = self.dataset_service.get_last_dataset_path(node_uuid, cur_round, in_labels, out_labels)
        with open(path, "a", encoding="utf-8") as file_obj:
            line = ",".join(str(feature) for _, feature in pending_item["data"].items())
            file_obj.write(line + "\n")
        return OperationResult(ok=True)

    def append_corrected_row(
        self,
        pending_item: dict,
        corrected_out_features: dict,
        cur_round: int,
        in_labels: list[str],
        out_labels: list[str],
    ) -> OperationResult[None]:
        """Append one corrected row preserving input labels plus corrected outputs."""
        node_uuid = pending_item["node"].replace("node_", "")
        path = self.dataset_service.get_last_dataset_path(node_uuid, cur_round, in_labels, out_labels)
        parts = []
        for key, feature in pending_item["data"].items():
            if key in in_labels:
                parts.append(str(feature))
        for _, value in corrected_out_features.items():
            parts.append(str(value))
        with open(path, "a", encoding="utf-8") as file_obj:
            file_obj.write(",".join(parts) + "\n")
        return OperationResult(ok=True)

    @staticmethod
    def parse_label_json(raw: str) -> list[str]:
        """Parse JSON labels from project storage."""
        return json.loads(raw)
