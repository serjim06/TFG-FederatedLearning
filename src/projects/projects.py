from src.db import dbcon
import uuid

default_parameters = {
    "optimizer": "adam",
    "learning_rate": 0.01,
    "epochs": 3,
    "validation_split": 0.2,
    "batch_size": 32,
    "fraction_fit": 0.8,
    "fraction_evaluate": 0.5
}

class Project:
    def __init__(self, id, uid, name, description, parameters, aggregation_strategy, initial_nodes,
                 metrics):
        """
        Project constructor.
        Args:
            id (str): project id (uuid4 format)
            uid (str): project owner's id (uuid4 format)
            name (str): project name
            description (str): project description
            parameters (dict): project parameters. Possible keys:
                - "optimizer" (str): optimizer. Default is "adam"
                - "learning_rate" (float): learning rate. Default is 0.01
                - "epochs" (int): number of epochs. Default is 3
                - "validation_split" (float): validation split. Default is 0.2
                - "batch_size" (int): batch size. Default is 32
                - "fraction_fit" (float): fraction of nodes used for training. Default is 0.8
                - "fraction_evaluate" (float): fraction of nodes used for evaluation. Default is 0.5
            aggregation_strategy (str): project aggregation strategy. Possible values:
                - "fed_avg": Federated Averaging
                - "fed_prox": Federated Proximal
            initial_nodes (list): project initial nodes
            metrics (string): project loss metrics. Possible values:
                    - "categorical_crossentropy". Default value.
                    - "sparse_categorical_crossentropy"
                    - "binary_crossentropy"
                    - "mean_squared_error"
        """
        self.id = id
        self.uid = uid
        self.name = name
        self.description = description
        parameters = default_parameters | parameters
        self.parameters = parameters
        self.aggregation_strategy = aggregation_strategy
        self.nodes = []
        for node in initial_nodes:
            self.add_node(node) 
        self.unconfirmed_results = []
        self.training_round = 0
        metrics = metrics if metrics else "categorical_crossentropy"
        self.metrics = metrics

    def to_dict(self):
        return {
            "id": self.id,
            "uid": self.uid,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "aggregation_strategy": self.aggregation_strategy,
            "nodes": self.nodes,
            "unconfirmed_results": self.unconfirmed_results,
            "training_round": self.training_round,
            "metrics": self.metrics
        }
        
    def add_node(self, node_id):
        """
        Adds a node to a project.
        
        Args:
            node_id (bytes): The id of the node to add.
        Raises:
            ValueError: If the node does not exist, is already in a project, is already in this project, or there is an error while communicating with the database.
            sqlite3.DatabaseError: If there is an error with the database connection.
            
        """
        result = dbcon.command("select", "nodes", {"id": node_id})
        
        if result == []:
            raise ValueError("Node does not exist")
        if result[0]["valid"]:
            raise ValueError("Node is already in a project")
        if node_id in self.nodes:
            raise ValueError("Node is already in the project")
        
        
        dbcon.command("update", "nodes", {"id": node_id, "valid": 1})
        self.nodes.append(node_id)
        
    def remove_node(self, node_id):
        """
        Removes a node from a project.
        
        Args:
            node_id (bytes): The id of the node to remove.
        Raises:
            ValueError: If the node is not in this project or there is an error while communicating with the database.
            sqlite3.DatabaseError: If there is an error with the database connection.
        """
        if node_id not in self.nodes:
            raise ValueError("Node is not in the project")
        
        dbcon.command("update", "nodes", {"id": node_id}, {"valid": False})
        self.nodes.remove(node_id)
        
    def __getitem__(self, item):
        return getattr(self, item)
    
    def __setitem__(self, key, value):
        setattr(self, key, value)