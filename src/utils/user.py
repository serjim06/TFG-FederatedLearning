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
        Convierte los datos de un usuario en un formato legible para la comunicacion con la base de datos.
        :return: diccionario de los datos de un usuario
        """
        return {
            "id": self.id,
            "username": self.username,
            "password": self.password,
            "role": self.role,
        }