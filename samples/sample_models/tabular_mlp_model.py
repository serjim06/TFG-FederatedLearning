"""Tabular MLP; constants must match the CSV and the project."""

from __future__ import annotations

from typing import Sequence

import torch
import torch.nn as nn

from src.models.base_model import BaseModel

INPUT_FEATURES: list[str] = [
    "sepal_length",
    "sepal_width",
    "petal_length",
    "petal_width",
]
OUTPUT_FEATURES: list[str] = ["species"]

# "classification" (CrossEntropy, etiquetas 0..K-1 en el CSV) o "regression" (MSE).
TASK: str = "classification"

# Solo clasificación: nombres de clases (K = len(CLASS_LABELS) = logits de salida).
CLASS_LABELS: list[str] = ["setosa", "versicolor", "virginica"]

# Capas ocultas: p. ej. (256, 128) o (128, 64, 32).
HIDDEN_SIZES: tuple[int, ...] = (128, 64)
DROPOUT: float = 0.0


def _n_out() -> int:
    if TASK == "regression":
        return max(1, len(OUTPUT_FEATURES))
    if TASK != "classification":
        raise ValueError("TASK debe ser 'classification' o 'regression'.")
    if not CLASS_LABELS:
        raise ValueError("CLASS_LABELS no puede estar vacío en clasificación.")
    return len(CLASS_LABELS)


class TabularMLP(nn.Module):
    def __init__(
        self,
        n_in: int,
        hidden: Sequence[int],
        n_out: int,
        dropout: float = 0.0,
    ) -> None:
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
        return self.net(x)


class TabularMlpModel(BaseModel):
    def load_model(self, model_path) -> nn.Module:
        n_in = len(INPUT_FEATURES)
        n_out = _n_out()
        return TabularMLP(
            n_in=n_in,
            hidden=HIDDEN_SIZES,
            n_out=n_out,
            dropout=DROPOUT,
        )

    def get_features(self) -> dict:
        meta: dict = {"type": TASK}
        if TASK == "classification":
            meta["labels"] = list(CLASS_LABELS)
        return {
            "input_features": list(INPUT_FEATURES),
            "output_features": list(OUTPUT_FEATURES),
            "metadata": meta,
        }
