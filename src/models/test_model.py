import torch.nn as nn

from src.models.base_model import BaseModel


class TestModel(BaseModel):
    def load_model(self, model_path):
        # Red mínima: 2 entradas → 2 clases (compatible con datasets de prueba tipo hola/adios)
        return nn.Sequential(
            nn.Linear(2, 16),
            nn.ReLU(),
            nn.Linear(16, 2),
        )

    def get_features(self):
        return {
            "input_features": ["feature1", "feature2"],
            "output_features": ["label"],
            "metadata": {
                "type": "classification",
                "labels": ["hola", "adios"],
            },
        }
