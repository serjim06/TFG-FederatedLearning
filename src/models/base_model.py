from abc import ABC, abstractmethod
import torch.nn as nn
from torch.utils.data import DataLoader

class BaseModel(ABC):
    
    @abstractmethod
    def load_model(self, model_path) -> nn.Module:
        pass
    
    @abstractmethod
    def train(self, train_loader: DataLoader, val_loader: DataLoader, epochs: int, learning_rate: float):
        pass
    
    @abstractmethod
    def evaluate(self, test_loader: DataLoader): 
        pass
    
    @abstractmethod
    def predict(self, input_data):
        pass
    
    @abstractmethod
    def get_features(self) -> dict:
        """
        Returns a dictionary containing the input and output features of the model. The keys should be 'input_features' and 'output_features', and the values should be lists of feature names.
        """
        pass