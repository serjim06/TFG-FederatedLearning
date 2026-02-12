from src.models.base_model import BaseModel

class TestModel(BaseModel):
    def load_model(self, model_path): print(f"Loading model from {model_path}")
    
    def train(self, train_loader, val_loader, epochs, learning_rate): print(f"Training for {epochs} epochs with learning rate {learning_rate}")
    
    def evaluate(self, test_loader): print("Evaluating model")
    
    def predict(self, input_data): print("Predicting with model")
    
    def get_features(self):
        return { "input_features": ["feature1", "feature2"], "output_features": ["label"] }
    
    