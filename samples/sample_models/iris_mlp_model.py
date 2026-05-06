"""
Small (MLP) model for Iris-like tabular data: 4 features → 3 classes.
Designed for local and federated tests; the project ``model_path`` file
points to this .py. Trained weights are managed by ``src.models.node`` (``.pth`` per ``train_id``).
"""

from __future__ import annotations

import torch
import torch.nn as nn

from src.models.base_model import BaseModel


class IrisMLP(nn.Module):
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
    def load_model(self, model_path) -> nn.Module:
        return IrisMLP(n_in=4, n_hidden=32, n_classes=3)

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
