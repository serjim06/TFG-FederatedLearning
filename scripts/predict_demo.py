"""
Demostración de predicción sin base de datos ni GUI (modelo Iris MLP por defecto).

Desde la raíz del repositorio:

    .venv\\Scripts\\python.exe scripts/predict_demo.py

Opcional: pasar cuatro números separados por comas (mismas columnas que Iris):

    .venv\\Scripts\\python.exe scripts/predict_demo.py 5.1,3.5,1.4,0.2
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.node import Node, predict  # noqa: E402


def _default_project_row() -> dict:
    model_py = ROOT / "src" / "models" / "iris_mlp_model.py"
    return {
        "model_path": str(model_py.resolve()),
        "input_features": json.dumps(
            ["sepal_length", "sepal_width", "petal_length", "petal_width"]
        ),
        "output_features": json.dumps(["species"]),
        "metrics": "categorical_crossentropy",
        "parameters": json.dumps({}),
    }


def main() -> None:
    line = "5.1,3.5,1.4,0.2"
    if len(sys.argv) > 1:
        line = sys.argv[1]
    parts = [p.strip() for p in line.split(",") if p.strip()]
    vals = [float(x) for x in parts]

    row = _default_project_row()
    n_in = len(json.loads(row["input_features"]))
    if len(vals) != n_in:
        print(
            f"Se esperaban {n_in} valores separados por comas; se obtuvieron {len(vals)}.",
            file=sys.stderr,
        )
        sys.exit(1)

    dummy_node = Node(uuid.uuid4().bytes, 1, uuid.uuid4().bytes)
    os.chdir(ROOT)
    out = predict(dummy_node, vals, project=row)
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
