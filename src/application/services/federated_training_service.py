from typing import Any, Callable

from src.federated import run_federated_training


ProgressCallback = Callable[[int, int, str, float | None], None]


class FederatedTrainingService:
    """Encapsulate federated server execution details."""

    def run(
        self,
        project_row: dict[str, Any],
        num_rounds: int,
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """Run federated training for one project row."""
        return run_federated_training(project_row, num_rounds, on_progress=on_progress)
