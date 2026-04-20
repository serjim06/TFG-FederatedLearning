"""
Modelo MLP para regresión de salario (dataset job salary, CSV numérico tras
``scripts/build_job_salary_splits.py``).

Columnas del CSV (cabecera): mismas que ``INPUT_FEATURES`` + ``salary`` al final.
En la GUI, métrica del proyecto: ``mean_squared_error`` (regresión).
"""

from __future__ import annotations

import os
from typing import Sequence

import torch
import torch.nn as nn

from src.models.base_model import BaseModel

# Coinciden con la salida de ``build_job_salary_splits.py`` (orden de columnas).
INPUT_FEATURES: list[str] = [
    "job_title",
    "education_level",
    "industry",
    "company_size",
    "location",
    "remote_work",
    "experience_years",
    "skills_count",
    "certifications",
]
OUTPUT_FEATURES: list[str] = ["salary"]
TASK: str = "regression"
CLASS_LABELS: list[str] = []  # no usado en regresión

HIDDEN_SIZES: tuple[int, ...] = (256, 128, 64)
DROPOUT: float = 0.1


def _n_out() -> int:
    if TASK == "regression":
        return max(1, len(OUTPUT_FEATURES))
    if TASK != "classification":
        raise ValueError("TASK debe ser 'classification' o 'regression'.")
    if not CLASS_LABELS:
        raise ValueError("CLASS_LABELS no puede estar vacío en clasificación.")
    return len(CLASS_LABELS)


class JobSalaryMLP(nn.Module):
    def __init__(
        self,
        n_in: int,
        hidden: Sequence[int],
        n_out: int,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        prev = n_in
        for h in hidden:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU())
            if dropout and dropout > 0:
                layers.append(nn.Dropout(p=float(dropout)))
            prev = h
        layers.append(nn.Linear(prev, n_out))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class JobSalaryMlpModel(BaseModel):
    def load_model(self, model_path) -> nn.Module:
        n_in = len(INPUT_FEATURES)
        n_out = _n_out()
        model = JobSalaryMLP(
            n_in=n_in,
            hidden=HIDDEN_SIZES,
            n_out=n_out,
            dropout=DROPOUT,
        )
        base, _ = os.path.splitext(str(model_path))
        weights_path = base + ".pth"
        if os.path.isfile(weights_path):
            state = torch.load(weights_path, map_location="cpu")
            model.load_state_dict(state)
        return model

    def get_features(self) -> dict:
        return {
            "input_features": list(INPUT_FEATURES),
            "output_features": list(OUTPUT_FEATURES),
            "metadata": {"type": "regression"},
        }
