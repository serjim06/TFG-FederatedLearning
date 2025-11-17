import os
import shutil
import uuid

class Node:
    def __init__(self, id, valid, project_id):
        self.id = id
        self.valid = valid
        self.project_id = project_id
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.local_dataset_path = os.path.join(BASE_DIR, "..", "..", "database", "datasets" , "node_" + str(uuid.UUID(bytes=id)))
        

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        else:
            raise KeyError(item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def to_dict(self):
        return {
            "id": self.id,
            "valid": self.valid,
            "project_id": self.project_id,
            "local_dataset_path": self.local_dataset_path,
        }