class User:
    def __init__(
        self,
        id,
        username,
        role,
        password_hash=None,
        recovery_phrase_hash=None,
    ):
        self.id = id
        self.username = username
        self.role = role
        self.password_hash = password_hash
        self.recovery_phrase_hash = recovery_phrase_hash

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(item)

    def __setitem__(self, key, value):
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            raise KeyError(key)

    def modify(self, username=None, password_hash=None, recovery_phrase_hash=None):
        if username:
            self.username = username
        if password_hash:
            self.password_hash = password_hash
        if recovery_phrase_hash:
            self.recovery_phrase_hash = recovery_phrase_hash

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
            "role": self.role,
            "password_hash": self.password_hash,
            "recovery_phrase_hash": self.recovery_phrase_hash,
        }