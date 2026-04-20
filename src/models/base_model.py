from abc import ABC, abstractmethod

import torch.nn as nn


class BaseModel(ABC):
    """
    Contrato del modelo de usuario: define cómo construir/cargar la red PyTorch y qué
    columnas/features usa el proyecto. El entrenamiento, la evaluación y la predicción
    se implementan en ``src.models.node``.
    """

    @abstractmethod
    def load_model(self, model_path) -> nn.Module:
        """Devuelve el módulo PyTorch (arquitectura y, si aplica, pesos cargados desde ``model_path``)."""
        pass

    @abstractmethod
    def get_features(self) -> dict:
        """
        Diccionario con al menos ``input_features`` y ``output_features`` (listas de nombres).
        Opcionalmente ``metadata`` con ``type`` (``regression`` | ``classification``),
        ``categorical_columns`` (nombres de columnas de entrada con texto categórico a codificar),
        ``labels`` (clasificación), ``units``, etc., para informes y para formatear predicciones.
        """
        pass
