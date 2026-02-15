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
        """
        Predicts using the model. The output should be a dictionary with the following structure:
        ```
        {
            "type": "classification" | "regression" | "multi_output",
            "output": raw_output,
            "labels": label_output (only for classification),
            "output_info": {
                "names": [...],   # optional, each output feature name
                "dtype": [...]    # optional, output data type
            }
        }
        ```
        
        One example of a valid output for a classification model could be:
        ```
        {
            "type": "classification",
            "output": 1, # The predicted class index (e.g., 1 out of [0.1, 0.7, 0.2])
            "labels": ["cat", "dog", "mouse"],
            "output_info": {
                "names": ["species"],
                "dtype": ["str"]
            }
        }
        ```
        """
        
        pass
    
    @abstractmethod
    def get_features(self) -> dict:
        """
        Returns a dictionary containing the input and output features of the model. The keys should be 'input_features' and 'output_features', and the values should be lists of feature names.
        """
        pass