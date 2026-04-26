import json

from src.application.services.federated_training_service import FederatedTrainingService
from src.application.services.metrics_service import MetricsService
from src.application.use_cases.authenticate_user import AuthenticateUserUseCase
from src.application.use_cases.add_dataset_to_node import AddDatasetToNodeUseCase
from src.application.use_cases.create_project import CreateProjectUseCase
from src.application.use_cases.delete_user import DeleteUserUseCase
from src.application.use_cases.get_project_metrics import GetProjectMetricsUseCase
from src.application.use_cases.list_managed_users import ListManagedUsersUseCase
from src.application.use_cases.recover_password import RecoverPasswordUseCase
from src.application.use_cases.register_user import RegisterUserUseCase
from src.application.use_cases.run_federated_training import RunFederatedTrainingUseCase
from src.application.use_cases.update_project import UpdateProjectUseCase
from src.application.use_cases.update_user_profile import UpdateUserProfileUseCase
from src.security.passwords import hash_password


class InMemoryProjectRepository:
    def __init__(self):
        self.items = {}

    def get_by_id(self, project_id):
        return self.items.get(project_id)

    def list_by_user(self, user_id):
        return [v for v in self.items.values() if v["uid"] == user_id]

    def create(self, payload):
        row = dict(payload)
        row["id"] = b"project_id"
        self.items[row["id"]] = row
        return row

    def update(self, payload):
        row = self.items[payload["id"]]
        row.update(payload)
        return row

    def delete(self, project_id):
        self.items.pop(project_id, None)


class InMemoryNodeRepository:
    def __init__(self):
        self.updates = []

    def get_by_id(self, node_id):
        return None

    def update(self, payload):
        self.updates.append(dict(payload))


class InMemoryUserRepository:
    def __init__(self):
        self.items = {}
        self._counter = 0

    def list_all(self):
        return list(self.items.values())

    def get_by_id(self, user_id):
        return self.items.get(user_id)

    def get_by_username(self, username):
        for row in self.items.values():
            if row["username"] == username:
                return row
        return None

    def create(self, payload):
        self._counter += 1
        row = dict(payload)
        row["id"] = f"user_{self._counter}".encode("utf-8")
        self.items[row["id"]] = row
        return row

    def update(self, payload):
        row = self.items[payload["id"]]
        row.update(payload)
        return row

    def delete(self, user_id):
        self.items.pop(user_id, None)


class StubFederatedTrainingService(FederatedTrainingService):
    def run(self, project_row, num_rounds, on_progress=None):
        return {
            "training_results_entry": {
                "train_id": "fed_test",
                "config": {"total_clients": ["a"]},
                "results_per_round": [],
                "final_metrics": {"total_time_seconds": 1.0},
            },
            "total_time_seconds": 1.5,
        }


def _sample_form_data():
    return {
        "name": "p1",
        "description": "desc",
        "task_type": "classification",
        "parameters": {"epochs": 3},
        "aggregation_strategy": "fed_avg",
        "initial_nodes": ["00000000-0000-0000-0000-000000000001"],
        "metrics": "categorical_crossentropy",
        "model_path": "database/models/a.py",
        "input_features": ["a"],
        "output_features": ["b"],
    }


def test_create_and_update_project_use_cases():
    project_repo = InMemoryProjectRepository()
    node_repo = InMemoryNodeRepository()
    create_uc = CreateProjectUseCase(project_repo, node_repo)
    update_uc = UpdateProjectUseCase(project_repo, node_repo)

    created = create_uc.execute(b"user", _sample_form_data())
    assert created.ok is True
    assert created.data["name"] == "p1"
    assert len(node_repo.updates) == 1

    previous = dict(created.data)
    form_data = _sample_form_data()
    form_data["name"] = "p2"
    form_data["initial_nodes"] = []
    updated = update_uc.execute(previous["id"], previous, form_data)
    assert updated.ok is True
    assert updated.data["name"] == "p2"


def test_run_federated_training_use_case_updates_training_results():
    project_repo = InMemoryProjectRepository()
    node_repo = InMemoryNodeRepository()
    create_uc = CreateProjectUseCase(project_repo, node_repo)
    created = create_uc.execute(b"user", _sample_form_data())
    project_id = created.data["id"]
    project_repo.update(
        {
            "id": project_id,
            "training_results": "[]",
            "training_round": 0,
            "type": "classification",
        }
    )
    use_case = RunFederatedTrainingUseCase(project_repo, StubFederatedTrainingService())
    result = use_case.execute(project_id, 2)
    assert result.ok is True
    updated = project_repo.get_by_id(project_id)
    entries = json.loads(updated["training_results"])
    assert len(entries) == 1
    assert updated["training_round"] == 3


def test_get_project_metrics_use_case_returns_payload():
    project_repo = InMemoryProjectRepository()
    metrics_service = MetricsService()
    training_results = json.dumps(
        [
            {
                "config": {"total_clients": ["node1"]},
                "results_per_round": [
                    {
                        "global_loss": 1.0,
                        "global_accuracy": 0.5,
                        "participating_clients": 1,
                        "client_stats": [],
                        "time": 0.1,
                    }
                ],
            }
        ]
    )
    project_repo.items[b"id1"] = {
        "id": b"id1",
        "uid": b"u",
        "name": "p",
        "description": "",
        "type": "classification",
        "training_results": training_results,
        "nodes": "[]",
    }
    use_case = GetProjectMetricsUseCase(project_repo, metrics_service)
    result = use_case.execute(b"id1")
    assert result.ok is True
    assert "metrics" in result.data


def test_user_management_use_cases():
    user_repo = InMemoryUserRepository()
    project_repo = InMemoryProjectRepository()
    user_repo.items[b"u1"] = {"id": b"u1", "username": "admin", "role": "admin"}
    user_repo.items[b"u2"] = {"id": b"u2", "username": "john", "role": "user"}
    project_repo.items[b"p1"] = {"id": b"p1", "uid": b"u2", "name": "p", "description": ""}

    list_uc = ListManagedUsersUseCase(user_repo, project_repo)
    out = list_uc.execute(b"u1")
    assert out.ok is True
    assert len(out.data) == 1
    assert out.data[0]["project_count"] == 1

    delete_uc = DeleteUserUseCase(user_repo, project_repo)
    deleted = delete_uc.execute(b"u2")
    assert deleted.ok is True
    assert user_repo.get_by_id(b"u2") is None


def test_register_and_authenticate_user_use_cases():
    user_repo = InMemoryUserRepository()
    register_uc = RegisterUserUseCase(user_repo)
    auth_uc = AuthenticateUserUseCase(user_repo)

    created = register_uc.execute("alice", "abc12345", "abc12345", "frase_1", "frase_1")
    assert created.ok is True
    assert created.data["username"] == "alice"
    assert created.data["password_hash"]
    assert created.data["recovery_phrase_hash"]

    ok_login = auth_uc.execute("alice", "abc12345")
    assert ok_login.ok is True
    bad_login = auth_uc.execute("alice", "bad-pass")
    assert bad_login.ok is False


def test_recover_and_update_profile_use_cases():
    user_repo = InMemoryUserRepository()
    created = user_repo.create(
        {
            "username": "alice",
            "role": "user",
            "password_hash": hash_password("abc12345"),
            "recovery_phrase_hash": hash_password("frase_1"),
        }
    )
    recover_uc = RecoverPasswordUseCase(user_repo)
    update_uc = UpdateUserProfileUseCase(user_repo)

    loaded = recover_uc.load_recoverable_user("alice")
    assert loaded.ok is True
    reset = recover_uc.execute(created["id"], "frase_1", "new12345", "new12345")
    assert reset.ok is True

    updated = update_uc.execute(created["id"], "alice2", "", "", "", "")
    assert updated.ok is True
    assert updated.data["username"] == "alice2"


def test_add_dataset_use_case_validates_csv_path():
    use_case = AddDatasetToNodeUseCase(None)
    result = use_case.execute("node_test", "", ["f1"], ["label"], 0)
    assert result.ok is False
