"""MLP model for tabular air quality regression with NOx as target."""

from __future__ import annotations

from typing import Sequence

import torch
import torch.nn as nn

from src.models.base_model import BaseModel

INPUT_FEATURES: list[str] = [
    "CO(GT)",
    "PT08.S1(CO)",
    "NMHC(GT)",
    "C6H6(GT)",
    "PT08.S2(NMHC)",
    "PT08.S3(NOx)",
    "NO2(GT)",
    "PT08.S4(NO2)",
    "PT08.S5(O3)",
    "T",
    "RH",
    "AH",
]
OUTPUT_FEATURES: list[str] = ["NOx"]
TASK: str = "regression"
HIDDEN_SIZES: tuple[int, ...] = (256, 128, 64)
DROPOUT: float = 0.1


def _n_out() -> int:
    """Return output size for regression or classification tasks."""
    if TASK == "regression":
        return max(1, len(OUTPUT_FEATURES))
    raise ValueError("TASK must be 'regression' for this model.")


class AirQualityMLP(nn.Module):
    """Multilayer perceptron for air quality tabular features."""

    def __init__(
        self,
        n_in: int,
        hidden: Sequence[int],
        n_out: int,
        dropout: float = 0.0,
    ) -> None:
        """Build the feed-forward network architecture."""
        super().__init__()
        if n_in < 1 or n_out < 1:
            raise ValueError("n_in and n_out must be greater than zero.")
        layers: list[nn.Module] = []
        prev = n_in
        for h in hidden:
            if h < 1:
                raise ValueError("Each hidden size must be greater than zero.")
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU())
            if dropout and dropout > 0:
                layers.append(nn.Dropout(p=float(dropout)))
            prev = h
        layers.append(nn.Linear(prev, n_out))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Run a forward pass on input tensor x."""
        return self.net(x)


class AirQualityMlpModel(BaseModel):
    """Project model wrapper used by the training pipeline."""

    def load_model(self, model_path) -> nn.Module:
        """Create and return a fresh neural network instance."""
        n_in = len(INPUT_FEATURES)
        n_out = _n_out()
        return AirQualityMLP(
            n_in=n_in,
            hidden=HIDDEN_SIZES,
            n_out=n_out,
            dropout=DROPOUT,
        )

    def get_features(self) -> dict:
        """Return model feature configuration and task metadata."""
        return {
            "input_features": list(INPUT_FEATURES),
            "output_features": list(OUTPUT_FEATURES),
            "metadata": {
                "type": "regression",
                "categorical_columns": list(CATEGORICAL_FEATURES),
            },
        }
