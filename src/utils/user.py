class User:
    def __init__(self, id, username, password, role, projects):
        self.id = id
        self.username = username
        self.password = password
        self.projects = projects
        self.role = role

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(item)


    def modify(self, username=None, password=None):
        if username:
            self.username = username
        if password:
            self.password = password

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "password": self.password,
            "role": self.role,
            "projects": self.projects,
        }