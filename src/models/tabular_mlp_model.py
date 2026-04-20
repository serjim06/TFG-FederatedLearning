"""
MLP tabular configurable: las **constantes de configuración** deben coincidir con el CSV
y con lo que definas al crear el proyecto (``input_features`` / ``output_features``).

Uso típico
---------
1. Copia este archivo si quieres varias variantes, o edítalo in situ.
2. Ajusta ``INPUT_FEATURES``, ``OUTPUT_FEATURES``, ``TASK`` y (si clasificas) ``CLASS_LABELS``.
3. Opcional: ``HIDDEN_SIZES`` y ``DROPOUT`` para más capacidad / regularización.
4. En la GUI, al crear el proyecto, elige este ``.py`` como modelo: se llamará a
   ``get_features()`` y las columnas quedarán alineadas con el CSV.

Los pesos entrenados opcionales van en ``<mismo_nombre_base>.pth`` junto al ``.py``.
"""

from __future__ import annotations

import os
from typing import Sequence

import torch
import torch.nn as nn

from src.models.base_model import BaseModel

# ---------------------------------------------------------------------------
# Configuración: debe coincidir con las columnas del CSV (cabecera = nombres).
# ---------------------------------------------------------------------------

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
    """MLP: n_in → capas ocultas (ReLU, Dropout opcional) → n_out."""

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
    """Contrato ``BaseModel``: dimensiones derivadas de la configuración del módulo."""

    def load_model(self, model_path) -> nn.Module:
        n_in = len(INPUT_FEATURES)
        n_out = _n_out()
        model = TabularMLP(
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
        meta: dict = {"type": TASK}
        if TASK == "classification":
            meta["labels"] = list(CLASS_LABELS)
        return {
            "input_features": list(INPUT_FEATURES),
            "output_features": list(OUTPUT_FEATURES),
            "metadata": meta,
        }
