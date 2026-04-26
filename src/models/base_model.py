from abc import ABC, abstractmethod

import torch.nn as nn


class BaseModel(ABC):
    """
    User model contract: defines how to build/load the PyTorch network and which
    columns/features the project uses. Training, evaluation, and prediction
    are implemented in ``src.models.node``.
    """

    @abstractmethod
    def load_model(self, model_path) -> nn.Module:
        """Return the PyTorch module (architecture and, if applicable, weights loaded from ``model_path``)."""
        pass

    @abstractmethod
    def get_features(self) -> dict:
        """
        Dictionary with at least ``input_features`` and ``output_features`` (lists of names).
        Optionally ``metadata`` with ``type`` (``regression`` | ``classification``),
        ``categorical_columns`` (input column names with categorical text to encode),
        ``labels`` (classification), ``units``, etc., for reports and prediction formatting.
        """
        pass
