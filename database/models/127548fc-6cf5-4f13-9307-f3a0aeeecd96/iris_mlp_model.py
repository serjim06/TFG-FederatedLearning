"""
Modelo pequeño (MLP) para datos tabulares tipo Iris: 4 características → 3 clases.
Pensado para pruebas locales y federadas; el archivo ``model_path`` del proyecto
apunta a este .py; los pesos opcionales pueden guardarse como ``.pth`` junto al mismo nombre base.
"""

from __future__ import annotations

import os

import torch
import torch.nn as nn

from src.models.base_model import BaseModel


class IrisMLP(nn.Module):
    """Red ligera: 4 → 32 → 3 logits (Iris / datos tabulares similares)."""

    def __init__(self, n_in: int = 4, n_hidden: int = 32, n_classes: int = 3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_in, n_hidden),
            nn.ReLU(),
            nn.Linear(n_hidden, n_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class IrisMlpModel(BaseModel):
    """
    Contrato ``BaseModel``: arquitectura fija acorde a ``get_features``.

    - Si existe ``<stem>.pth`` junto al ``model_path`` (.py), carga ``state_dict``.
    - Si no, pesos aleatorios (inicialización por defecto de PyTorch).
    """

    def load_model(self, model_path) -> nn.Module:
        model = IrisMLP(n_in=4, n_hidden=32, n_classes=3)
        base, _ = os.path.splitext(str(model_path))
        weights_path = base + ".pth"
        if os.path.isfile(weights_path):
            state = torch.load(weights_path, map_location="cpu")
            model.load_state_dict(state)
        return model

    def get_features(self) -> dict:
        return {
            "input_features": [
                "sepal_length",
                "sepal_width",
                "petal_length",
                "petal_width",
            ],
            "output_features": ["species"],
            "metadata": {
                "type": "classification",
                "labels": ["setosa", "versicolor", "virginica"],
            },
        }
