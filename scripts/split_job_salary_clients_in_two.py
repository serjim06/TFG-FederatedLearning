"""
Parte ``job_salary_client_a.csv`` y ``job_salary_client_b.csv`` en dos mitades cada uno
(cuatro CSV en total), con la misma cabecera.

Ejecución desde la raíz del repo:

    .venv\\Scripts\\python.exe scripts/split_job_salary_clients_in_two.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "database" / "sample_datasets"


def _split_file(
    inp: Path,
    out1: Path,
    out2: Path,
    seed: int,
) -> tuple[int, int]:
    if not inp.is_file():
        raise FileNotFoundError(str(inp))
    with open(inp, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    n = len(rows)
    if n < 2:
        raise ValueError(f"Muy pocas filas en {inp}")
    rng = np.random.RandomState(seed)
    order = rng.permutation(n)
    half = n // 2
    idx1 = order[:half]
    idx2 = order[half:]

    def write(path: Path, indices: np.ndarray) -> None:
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            for i in indices:
                w.writerow(rows[i])

    write(out1, idx1)
    write(out2, idx2)
    return len(idx1), len(idx2)


def main() -> None:
    pairs = [
        (
            SRC / "job_salary_client_a.csv",
            SRC / "job_salary_client_a1.csv",
            SRC / "job_salary_client_a2.csv",
            201,
        ),
        (
            SRC / "job_salary_client_b.csv",
            SRC / "job_salary_client_b1.csv",
            SRC / "job_salary_client_b2.csv",
            202,
        ),
    ]
    for inp, o1, o2, seed in pairs:
        n1, n2 = _split_file(inp, o1, o2, seed)
        print(f"{inp.name} -> {o1.name} ({n1} filas), {o2.name} ({n2} filas)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
