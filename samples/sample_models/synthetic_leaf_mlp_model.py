"""MLP model for synthetic leaf tabular classification datasets."""

from __future__ import annotations

from typing import Sequence

import torch
import torch.nn as nn

from src.models.base_model import BaseModel

INPUT_FEATURES: list[str] = [f"Feature_{index}" for index in range(60)]
OUTPUT_FEATURES: list[str] = ["Target"]
TASK: str = "classification"
CLASS_LABELS: list[str] = ["0", "1", "2", "3", "4"]

HIDDEN_SIZES: tuple[int, ...] = (256, 128, 64)
DROPOUT: float = 0.1


def _n_out() -> int:
    """Return output neuron count according to task configuration."""
    if TASK == "regression":
        return max(1, len(OUTPUT_FEATURES))
    if TASK != "classification":
        raise ValueError("TASK debe ser 'classification' o 'regression'.")
    if not CLASS_LABELS:
        raise ValueError("CLASS_LABELS no puede estar vacío en clasificación.")
    return len(CLASS_LABELS)


class SyntheticLeafMLP(nn.Module):
    """Define a configurable multilayer perceptron for tabular inputs."""

    def __init__(
        self,
        n_in: int,
        hidden: Sequence[int],
        n_out: int,
        dropout: float = 0.0,
    ) -> None:
        """Build a feed-forward network with ReLU activations."""
        super().__init__()
        if n_in < 1 or n_out < 1:
            raise ValueError("n_in y n_out deben ser >= 1.")
        layers: list[nn.Module] = []
        prev = n_in
        for h in hidden:
            if h < 1:
                raise ValueError("Cada tamaño oculto debe ser >= 1.")
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU())
            if dropout and dropout > 0:
                layers.append(nn.Dropout(p=float(dropout)))
            prev = h
        layers.append(nn.Linear(prev, n_out))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Return logits from the network for a given input tensor."""
        return self.net(x)


class SyntheticLeafMlpModel(BaseModel):
    """Expose model and feature metadata for training/inference pipelines."""

    def load_model(self, model_path) -> nn.Module:
        """Instantiate the configured MLP architecture."""
        n_in = len(INPUT_FEATURES)
        n_out = _n_out()
        return SyntheticLeafMLP(
            n_in=n_in,
            hidden=HIDDEN_SIZES,
            n_out=n_out,
            dropout=DROPOUT,
        )

    def get_features(self) -> dict:
        """Return input/output feature names and task metadata."""
        return {
            "input_features": list(INPUT_FEATURES),
            "output_features": list(OUTPUT_FEATURES),
            "metadata": {"type": TASK, "labels": list(CLASS_LABELS)},
        }
