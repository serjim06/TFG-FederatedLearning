import argparse
from pathlib import Path
from typing import Iterable

from src.db import dbcon
from src.infrastructure.repositories.sqlite_node_repository import SQLiteNodeRepository
from src.infrastructure.repositories.sqlite_user_repository import SQLiteUserRepository
from src.models.node import Node
from src.security.passwords import hash_password


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"
DATABASE_DIR = ROOT_DIR / "database"


CREATE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users
(
    id                   TEXT PRIMARY KEY,
    username             TEXT UNIQUE,
    role                 TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    password_hash        TEXT,
    recovery_phrase_hash TEXT,
    last_login           TIMESTAMP,
    last_train           TIMESTAMP,
    creation_date        TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects
(
    id                   TEXT PRIMARY KEY,
    uid                  TEXT NOT NULL,
    name                 TEXT NOT NULL,
    description          VARCHAR(100),
    parameters           JSON1 NOT NULL,
    aggregation_strategy TEXT NOT NULL,
    unconfirmed_results  JSON1,
    training_round       INTEGER DEFAULT 0,
    metrics              TEXT NOT NULL DEFAULT 'categorical_crossentropy',
    model_path           TEXT,
    input_features       JSON1,
    output_features      JSON1,
    training_results     JSON1 DEFAULT '[]',
    type                 VARCHAR(20) CHECK (type IN ('classification', 'regression')) DEFAULT 'classification',
    updated_at           TIMESTAMP,
    created_at           TIMESTAMP,
    FOREIGN KEY (uid) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS nodes
(
    id                 TEXT PRIMARY KEY,
    valid              BOOLEAN NOT NULL DEFAULT FALSE,
    project_id         TEXT NOT NULL,
    local_dataset_path TEXT,
    FOREIGN KEY (project_id) REFERENCES projects (id)
);
"""


def parse_env_file(path: Path) -> dict[str, str]:
    """Read key-value entries from a .env file path."""
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero .env en: {path}")
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1]
        values[key] = value
    return values


def pick_env_value(env_values: dict[str, str], keys: Iterable[str], label: str) -> str:
    """Return the first non-empty value found for accepted keys."""
    for key in keys:
        value = (env_values.get(key) or "").strip()
        if value:
            return value
    valid_keys = ", ".join(keys)
    raise ValueError(f"Falta valor para {label} en .env. Claves admitidas: {valid_keys}")


def ensure_schema() -> None:
    """Create required database tables when they do not exist."""
    if dbcon.database is None:
        raise RuntimeError("No hay conexión abierta contra SQLite.")
    dbcon.database.executescript(CREATE_SCHEMA_SQL)
    dbcon.database.commit()


def upsert_admin(username: str, password: str, recovery_phrase: str) -> dict:
    """Create or update admin user with credentials from .env."""
    user_repository = SQLiteUserRepository()
    now = dbcon.sqlite_timestamp_now()
    existing = user_repository.get_by_username(username)
    payload = {
        "username": username,
        "role": "admin",
        "password_hash": hash_password(password),
        "recovery_phrase_hash": hash_password(recovery_phrase),
        "creation_date": now,
    }
    if existing:
        payload["id"] = existing["id"]
        payload["last_login"] = existing.get("last_login")
        payload["last_train"] = existing.get("last_train")
        updated = user_repository.update(payload)
        return updated
    return user_repository.create(payload)


def create_nodes(node_count: int) -> list[dict]:
    """Create nodes and persist each computed local dataset path."""
    if node_count < 0:
        raise ValueError("El número de nodos no puede ser negativo.")
    node_repository = SQLiteNodeRepository()
    created: list[dict] = []
    for _ in range(node_count):
        node_row = node_repository.create({"valid": 0, "project_id": "", "local_dataset_path": ""})
        node = Node(node_row["id"], node_row["valid"], node_row["local_dataset_path"])
        node_repository.update({"id": node.id, "local_dataset_path": node.local_dataset_path})
        created.append(node_repository.get_by_id(node.id))
    return created


def main() -> None:
    """Initialize database folder, admin user, and sample nodes."""
    parser = argparse.ArgumentParser(description="Inicializa DB local con admin y nodos.")
    parser.add_argument("--nodes", type=int, default=3, help="Número de nodos a crear.")
    parser.add_argument(
        "--env",
        type=Path,
        default=ENV_PATH,
        help="Ruta al archivo .env que contiene los datos de admin.",
    )
    args = parser.parse_args()

    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    env_values = parse_env_file(args.env)
    admin_username = pick_env_value(env_values, ("ADMIN_USERNAME",), "nombre de admin")
    admin_password = pick_env_value(env_values, ("ADMIN_PASSWORD",), "contraseña de admin")
    admin_recovery_phrase = pick_env_value(
        env_values,
        ("ADMIN_RECOVER_PHRASE",),
        "recover_phrase de admin",
    )

    dbcon.connect("database.db")
    try:
        ensure_schema()
        admin = upsert_admin(admin_username, admin_password, admin_recovery_phrase)
        created_nodes = create_nodes(args.nodes)
    finally:
        dbcon.disconnect()

    print(f"Admin inicializado: {admin_username} ({admin['role']})")
    print(f"Nodos creados: {len(created_nodes)}")


if __name__ == "__main__":
    main()
