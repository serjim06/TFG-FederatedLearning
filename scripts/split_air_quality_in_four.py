"""Split the air quality dataset into four client CSV files."""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "database" / "sample_datasets" / "air_quality"
INPUT = SRC / "air_quality.csv"
OUTPUTS = [
    SRC / "air_quality_client_a.csv",
    SRC / "air_quality_client_b.csv",
    SRC / "air_quality_client_c.csv",
    SRC / "air_quality_client_d.csv",
]
SEED = 42


def _read_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    """Read header and non-empty rows from a CSV file."""
    if not path.is_file():
        raise FileNotFoundError(str(path))
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            raise ValueError("CSV file is empty.")
        rows = [row for row in reader if any((cell or "").strip() for cell in row)]
    if not rows:
        raise ValueError("CSV has no data rows.")
    return header, rows


def _split_indices(n_rows: int, n_parts: int, seed: int) -> list[list[int]]:
    """Shuffle row indices and split them into n_parts balanced chunks."""
    if n_parts < 2:
        raise ValueError("n_parts must be at least two.")
    indices = list(range(n_rows))
    rng = random.Random(seed)
    rng.shuffle(indices)
    base = n_rows // n_parts
    extra = n_rows % n_parts
    chunks: list[list[int]] = []
    start = 0
    for i in range(n_parts):
        size = base + (1 if i < extra else 0)
        end = start + size
        chunks.append(indices[start:end])
        start = end
    return chunks


def _write_split(path: Path, header: list[str], rows: list[list[str]], idx: list[int]) -> None:
    """Write a split CSV preserving the input header."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for i in idx:
            writer.writerow(rows[i])


def main() -> None:
    """Generate four deterministic air quality client datasets."""
    header, rows = _read_rows(INPUT)
    chunks = _split_indices(len(rows), len(OUTPUTS), SEED)
    for output, idx in zip(OUTPUTS, chunks, strict=True):
        _write_split(output, header, rows, idx)
        print(f"{output.name}: {len(idx)} rows")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
