"""
Split ``job_salary_prediction_dataset.csv`` into two numeric CSVs (clients A/B).

Encode categorical columns with OrdinalEncoder (fit on the full dataset)
to match ``job_salary_mlp_model.py`` and ``node._load_xy_from_csv``.

The application can also load ``job_salary_prediction_dataset.csv`` directly
(flexible column order and categorical text) thanks to ``metadata.categorical_columns``
in the model; for federated learning with multiple nodes and **different subsets**
of categories, this script remains the most consistent option (a single global OrdinalEncoder).

Run from the repository root:

    .venv\\Scripts\\python.exe scripts/build_job_salary_splits.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
from sklearn.preprocessing import OrdinalEncoder

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "database" / "sample_datasets"
INPUT_CSV = SRC / "job_salary_prediction_dataset.csv"
OUT_A = SRC / "job_salary_client_a.csv"
OUT_B = SRC / "job_salary_client_b.csv"

CATEGORICAL = [
    "job_title",
    "education_level",
    "industry",
    "company_size",
    "location",
    "remote_work",
]
NUMERIC = ["experience_years", "skills_count", "certifications"]
TARGET = "salary"
COLUMNS = CATEGORICAL + NUMERIC + [TARGET]


def main() -> None:
    if not INPUT_CSV.is_file():
        print(f"No existe {INPUT_CSV}", file=sys.stderr)
        sys.exit(1)

    rows: list[dict[str, str]] = []
    with open(INPUT_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise SystemExit("CSV sin cabecera")
        missing = [c for c in COLUMNS if c not in reader.fieldnames]
        if missing:
            raise SystemExit(f"Faltan columnas en el CSV: {missing}")
        for row in reader:
            rows.append({k: (row.get(k) or "").strip() for k in COLUMNS})

    n = len(rows)
    if n < 4:
        raise SystemExit("Muy pocas filas para partir")

    X_cat = np.array([[r[c] for c in CATEGORICAL] for r in rows], dtype=object)
    enc = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    X_cat_f = enc.fit_transform(X_cat).astype(np.float64)

    X_num = np.array(
        [[float(r[c]) for c in NUMERIC] for r in rows],
        dtype=np.float64,
    )
    y = np.array([float(r[TARGET]) for r in rows], dtype=np.float64)

    # Bloque: [cat codificadas | numéricas | salary]
    X_all = np.hstack([X_cat_f, X_num, y.reshape(-1, 1)])

    rng = np.random.RandomState(42)
    order = rng.permutation(n)
    half = n // 2
    idx_a = order[:half]
    idx_b = order[half:]

    def write(path: Path, indices: np.ndarray) -> None:
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLUMNS)
            for i in indices:
                w.writerow([f"{v:g}" if isinstance(v, float) else str(v) for v in X_all[i]])

    write(OUT_A, idx_a)
    write(OUT_B, idx_b)
    print(f"Filas totales: {n}")
    print(f"Cliente A: {len(idx_a)} -> {OUT_A}")
    print(f"Cliente B: {len(idx_b)} -> {OUT_B}")


if __name__ == "__main__":
    main()
