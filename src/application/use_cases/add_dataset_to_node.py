from pathlib import Path

from src.application.dto.operation_result import OperationResult
from src.application.services.dataset_service import DatasetService


class AddDatasetToNodeUseCase:
    """Append validated CSV rows into node dataset for current round."""

    def __init__(self, dataset_service: DatasetService):
        self.dataset_service = dataset_service

    def execute(
        self,
        node_uuid: str,
        csv_path: str,
        in_features: list,
        out_features: list,
        cur_round: int,
    ) -> OperationResult[None]:
        """Validate source CSV and append rows to destination dataset."""
        src = (csv_path or "").strip()
        if not src:
            return OperationResult(ok=False, error="Selecciona un archivo CSV.")
        if not src.lower().endswith(".csv"):
            return OperationResult(ok=False, error="El archivo debe tener extensión .csv.")
        src_path = Path(src)
        if not src_path.is_file():
            return OperationResult(ok=False, error="No se encontró el archivo indicado.")
        data_rows, err = self.dataset_service.validate_csv_for_project(src_path, in_features, out_features)
        if err:
            return OperationResult(ok=False, error=err)
        try:
            dest_path = self.dataset_service.get_last_dataset_path(
                node_uuid,
                cur_round,
                in_features,
                out_features,
            )
            self.dataset_service.append_data_rows(dest_path, data_rows or [])
        except OSError as e:
            return OperationResult(ok=False, error=f"No se pudo escribir el dataset: {e}")
        return OperationResult(ok=True)
