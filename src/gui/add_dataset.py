import csv
import json
import re
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from src.gui import dialogs
from src.gui.dialogs import BaseDialog
from src.utils import utils


DATASETS_ROOT = Path(__file__).resolve().parent.parent.parent / "database" / "datasets"


def _node_dir_name(node_uuid: str) -> str:
    return f"node_{node_uuid}"


def _create_new_dataset(
    dataset_dir: Path, cur_round: int, in_features: list, out_features: list
) -> Path:
    path = dataset_dir / f"dataset_{cur_round}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(",".join(list(in_features) + list(out_features)) + "\n")
    return path


def _get_last_dataset_path(
    node_uuid: str, cur_round: int, in_features: list, out_features: list
) -> Path:
    node_dir = DATASETS_ROOT / _node_dir_name(node_uuid)
    pattern = re.compile(r"dataset_(\d+)\.csv")
    found_files = []

    if node_dir.exists():
        for f in node_dir.glob("dataset_*.csv"):
            coincidence = pattern.search(f.name)
            if coincidence:
                round_number = int(coincidence.group(1))
                found_files.append((round_number, f))

    if found_files:
        last_dataset, file_path = max(found_files, key=lambda x: x[0])
        if last_dataset != cur_round:
            dest = node_dir / f"dataset_{cur_round}.csv"
            shutil.copy2(file_path, dest)
            file_path = dest
    else:
        file_path = _create_new_dataset(node_dir, cur_round, in_features, out_features)

    return file_path


def _labels_match_row(row: list, expected_labels: list) -> bool:
    if len(row) != len(expected_labels):
        return False
    return all((a or "").strip() == (b or "").strip() for a, b in zip(row, expected_labels))


def _same_labels_wrong_order(row: list, expected_labels: list) -> bool:
    if len(row) != len(expected_labels):
        return False
    got = [(x or "").strip() for x in row]
    exp = [(x or "").strip() for x in expected_labels]
    return sorted(got) == sorted(exp) and got != exp


def validate_csv_for_project(
    src_path: Path, in_features: list, out_features: list
) -> tuple[list[list[str]] | None, str | None]:
    """
    Comprueba que el CSV sea coherente con el proyecto: cabecera opcional igual a las
    etiquetas definidas, mismo número de columnas en cada fila de datos y sin celdas vacías.

    Returns
    -------
    (data_rows, None) si es válido, o (None, mensaje de error).
    """
    expected = list(in_features) + list(out_features)
    n = len(expected)

    try:
        with open(src_path, encoding="utf-8", errors="replace", newline="") as f:
            rows = list(csv.reader(f))
    except OSError as e:
        return None, f"No se pudo leer el archivo: {e}"

    if not rows:
        return None, "El archivo CSV está vacío."

    for ri, row in enumerate(rows):
        if not any((c or "").strip() for c in row):
            return None, f"La fila {ri + 1} del archivo está vacía; elimínala o rellénala."

    while rows and not any((c or "").strip() for c in rows[-1]):
        rows.pop()

    if not rows:
        return None, "El archivo no contiene ninguna fila con datos."

    if _labels_match_row(rows[0], expected):
        data_rows = rows[1:]
        if not data_rows:
            return None, "El archivo solo contiene la cabecera; no hay filas de datos."
        header_note = True
    elif _same_labels_wrong_order(rows[0], expected):
        return None, (
            "La cabecera contiene las mismas etiquetas que el proyecto pero en distinto orden. "
            f"Orden requerido: {', '.join(expected)}"
        )
    else:
        data_rows = rows
        header_note = False

    for i, row in enumerate(data_rows, start=1):
        if len(row) != n:
            esperado = ", ".join(expected)
            fila_ctx = f" (fila de datos {i}" + (" tras la cabecera)" if header_note else ")")
            return None, (
                f"Número de columnas incorrecto{fila_ctx}: se esperaban {n} "
                f"({esperado}), hay {len(row)}."
            )
        for j, cell in enumerate(row):
            if not (cell or "").strip():
                col = expected[j]
                fila_ctx = f"Fila de datos {i}" + (" (tras la cabecera)" if header_note else "")
                return None, f"{fila_ctx}: la columna «{col}» está vacía."

    return data_rows, None


def _append_data_rows(dest_path: Path, data_rows: list[list[str]]) -> None:
    with open(dest_path, "a", encoding="utf-8", newline="") as out:
        for row in data_rows:
            out.write(",".join(str(c) for c in row) + "\n")


class AddDatasetDialog(BaseDialog):
    """Diálogo para elegir un nodo del proyecto y añadir filas desde un archivo .csv."""

    def __init__(self, parent, nodes: list, project: dict):
        super().__init__(parent, "Añadir dataset")
        utils.get_style()
        self.nodes = list(nodes)
        self.project = project

        self._in_features = json.loads(project["input_features"])
        self._out_features = json.loads(project["output_features"])
        self._cur_round = int(project.get("training_round") or 0)

        self._csv_path = tk.StringVar(value="")

        tk.Label(
            self,
            text=(
                "Selecciona el nodo y un archivo CSV para añadir sus filas al dataset de la ronda actual. "
                "Las columnas deben coincidir con las características del proyecto (cabecera opcional); "
                "no se permiten filas vacías ni celdas vacías."
            ),
            background=utils.BG_COLOR,
            wraplength=420,
            justify="left",
        ).pack(pady=(12, 8), padx=16)

        form = tk.Frame(self, bg=utils.BG_COLOR)
        form.pack(fill="x", padx=16, pady=4)

        tk.Label(form, text="Nodo:", background=utils.BG_COLOR).grid(row=0, column=0, sticky="w", pady=4)
        self._node_var = tk.StringVar(value=self.nodes[0] if self.nodes else "")
        self._combo = ttk.Combobox(
            form,
            textvariable=self._node_var,
            values=self.nodes,
            state="readonly" if self.nodes else "disabled",
            width=44,
        )
        self._combo.grid(row=0, column=1, sticky="ew", pady=4)
        form.columnconfigure(1, weight=1)

        tk.Label(form, text="Archivo CSV:", background=utils.BG_COLOR).grid(row=1, column=0, sticky="nw", pady=4)
        file_row = tk.Frame(form, bg=utils.BG_COLOR)
        file_row.grid(row=1, column=1, sticky="ew", pady=4)
        file_row.columnconfigure(0, weight=1)

        self._path_label = tk.Label(
            file_row,
            textvariable=self._csv_path,
            background=utils.BG_COLOR,
            anchor="w",
            wraplength=320,
            justify="left",
        )
        self._path_label.grid(row=0, column=0, sticky="ew")

        ttk.Button(
            file_row,
            text="Examinar…",
            style=utils.SEC_TBUTTON_STYLE,
            command=self._browse_csv,
        ).grid(row=0, column=1, padx=(8, 0))

        btn_row = tk.Frame(self, bg=utils.BG_COLOR)
        btn_row.pack(pady=16)
        ttk.Button(
            btn_row,
            text="Añadir",
            style=utils.SEC_TBUTTON_STYLE,
            command=self._on_add,
        ).pack(side="left", padx=6)
        ttk.Button(
            btn_row,
            text="Cancelar",
            style=utils.SEC_TBUTTON_STYLE,
            command=self.destroy,
        ).pack(side="left", padx=6)

        self.center_dialog()

    def _browse_csv(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Seleccionar CSV",
            filetypes=[("CSV", "*.csv"), ("Todos los archivos", "*.*")],
        )
        if path:
            self._csv_path.set(path)

    def _on_add(self):
        if not self.nodes:
            dialogs.InfoDialog(self, "Información", "No hay nodos en el proyecto.", "warning")
            return

        node = self._node_var.get().strip()
        if not node:
            dialogs.InfoDialog(self, "Información", "Selecciona un nodo.", "warning")
            return

        src = self._csv_path.get().strip()
        if not src:
            dialogs.InfoDialog(self, "Información", "Selecciona un archivo CSV.", "warning")
            return

        if not src.lower().endswith(".csv"):
            dialogs.InfoDialog(self, "Error", "El archivo debe tener extensión .csv.", "error")
            return

        src_path = Path(src)
        if not src_path.is_file():
            dialogs.InfoDialog(self, "Error", "No se encontró el archivo indicado.", "error")
            return

        data_rows, err = validate_csv_for_project(
            src_path, self._in_features, self._out_features
        )
        if err:
            dialogs.InfoDialog(self, "Dataset no válido", err, "error")
            return

        try:
            dest_path = _get_last_dataset_path(
                node, self._cur_round, self._in_features, self._out_features
            )
            _append_data_rows(dest_path, data_rows)
        except OSError as e:
            dialogs.InfoDialog(self, "Error", f"No se pudo escribir el dataset: {e}", "error")
            return

        dialogs.InfoDialog(
            self.master,
            "Confirmación",
            f"Datos añadidos al dataset del nodo {node}.",
            "info",
        )
        self.destroy()
