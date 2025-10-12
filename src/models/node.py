from flwr.clientapp import ClientApp
from flwr import client

class Node:
    def __init__(self, id, valid, project_id, local_dataset_path):
        self.id = id
        self.valid = valid
        self.project_id = project_id
        self.local_dataset_path = local_dataset_path
        self.app = ClientApp()

