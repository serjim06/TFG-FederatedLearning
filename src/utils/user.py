class User:
    def __init__(self, id, username, password, role):
        self.id = id
        self.username = username
        self.password = password
        self.role = role

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(item)

    def __setitem__(self, key, value):
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            raise KeyError(key)

    def modify(self, username=None, password=None):
        if username:
            self.username = username
        if password:
            self.password = password

    def to_dict(self):
        """
        Converts a user's data into a dictionary format suitable for communication
        with the database.

        Returns
        -------
        dict
            A dictionary containing the user's data, where keys are the database
            field names and values are the corresponding user attributes.

        """
        return {
            "id": self.id,
            "username": self.username,
            "password": self.password,
            "role": self.role,
        }