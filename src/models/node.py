import os
import shutil

class Node:
    def __init__(self, id, valid, project_id, local_dataset_path):
        self.id = id
        self.valid = valid
        self.project_id = project_id
        self.local_dataset_path = local_dataset_path

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

    def add_dataset(self, dataset : str):
        """
        Adds a dataset to the node
        :param dataset: path to the dataset to add (.csv or dir)
        :raises ValueError: if the files in dataset are not CSV
        :raises TypeError: if the dataset is not a file or a directory
        :returns: True if the dataset was successfully added, False otherwise
        """
        os.makedirs(self.local_dataset_path, exist_ok=True)

        if os.path.isfile(dataset):
            if dataset.endswith(".csv"):
                shutil.copy2(dataset, os.path.join(self.local_dataset_path, dataset))
                return True
            else:
                raise ValueError(f"{dataset} is not a CSV file")
        if os.path.isdir(dataset):
            for filename in os.listdir(dataset):
                origen = os.path.join(dataset, filename)
                dest = os.path.join(self.local_dataset_path, filename)
                if os.path.isfile(origen):
                    if filename.endswith(".csv"):
                        shutil.copy2(origen, dest)
                    else:
                        raise ValueError(f"{origen} is not a CSV file")

                elif os.path.isdir(origen):
                    for files in self.get_files_in_dir(origen):
                        shutil.copy2(files, dest)
            return True

        raise TypeError(f"{dataset} is not a directory or CSV file")

    def get_files_in_dir(self, directory):
        """
        Walk through directory and return all files' paths in it
        :param directory: directory to look for files
        :return: list of file paths of each file in the directory and subdirectories
        :raises ValueError: if one of the files is not CSV or directory
        """
        list_of_files = []
        for filename in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, filename)):
                if filename.endswith(".csv"):
                    list_of_files.append(os.path.join(directory, filename))
                else:
                    raise ValueError(f"{filename} is not a CSV file")
            if os.path.isdir(os.path.join(directory, filename)):
                list_of_files.extend(self.get_files_in_dir(os.path.join(directory, filename)))


        return list_of_files