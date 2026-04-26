import csv
import re
import shutil
from collections import Counter
from pathlib import Path


DATASETS_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "database" / "datasets"


class DatasetService:
    """Handle dataset files for project nodes."""

    @staticmethod
    def node_dir_name(node_uuid: str) -> str:
        """Return canonical dataset folder name for one node."""
        return f"node_{node_uuid}"

    def get_last_dataset_path(
        self,
        node_uuid: str,
        cur_round: int,
        in_features: list,
        out_features: list,
    ) -> Path:
        """Return or create dataset file for the current round."""
        node_dir = DATASETS_ROOT / self.node_dir_name(node_uuid)
        pattern = re.compile(r"dataset_(\d+)\.csv")
        found_files = []
        if node_dir.exists():
            for file_path in node_dir.glob("dataset_*.csv"):
                match = pattern.search(file_path.name)
                if match:
                    found_files.append((int(match.group(1)), file_path))
        if found_files:
            last_dataset, file_path = max(found_files, key=lambda x: x[0])
            if last_dataset != cur_round:
                dest = node_dir / f"dataset_{cur_round}.csv"
                shutil.copy2(file_path, dest)
                file_path = dest
        else:
            file_path = self.create_new_dataset(node_dir, cur_round, in_features, out_features)
        return file_path

    @staticmethod
    def create_new_dataset(
        dataset_dir: Path,
        cur_round: int,
        in_features: list,
        out_features: list,
    ) -> Path:
        """Create one dataset CSV with header."""
        path = dataset_dir / f"dataset_{cur_round}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as file_obj:
            file_obj.write(",".join(list(in_features) + list(out_features)) + "\n")
        return path

    @staticmethod
    def append_data_rows(dest_path: Path, data_rows: list[list[str]]) -> None:
        """Append multiple CSV rows to destination dataset file."""
        with open(dest_path, "a", encoding="utf-8", newline="") as out:
            for row in data_rows:
                out.write(",".join(str(c) for c in row) + "\n")

    @staticmethod
    def labels_match_row(row: list, expected_labels: list) -> bool:
        """Return True when row labels exactly match expected list."""
        if len(row) != len(expected_labels):
            return False
        return all((a or "").strip() == (b or "").strip() for a, b in zip(row, expected_labels))

    @staticmethod
    def same_labels_wrong_order(row: list, expected_labels: list) -> bool:
        """Return True when labels are equal as sets but in different order."""
        if len(row) != len(expected_labels):
            return False
        got = [(x or "").strip() for x in row]
        expected = [(x or "").strip() for x in expected_labels]
        return sorted(got) == sorted(expected) and got != expected

    def validate_csv_for_project(
        self,
        src_path: Path,
        in_features: list,
        out_features: list,
    ) -> tuple[list[list[str]] | None, str | None]:
        """Validate uploaded CSV against project feature contract."""
        expected = list(in_features) + list(out_features)
        n_cols = len(expected)
        try:
            with open(src_path, encoding="utf-8", errors="replace", newline="") as file_obj:
                rows = list(csv.reader(file_obj))
        except OSError as e:
            return None, f"No se pudo leer el archivo: {e}"
        if not rows:
            return None, "El archivo CSV está vacío."
        for row_idx, row in enumerate(rows):
            if not any((c or "").strip() for c in row):
                return None, f"La fila {row_idx + 1} del archivo está vacía; elimínala o rellénala."
        while rows and not any((c or "").strip() for c in rows[-1]):
            rows.pop()
        if not rows:
            return None, "El archivo no contiene ninguna fila con datos."
        if self.labels_match_row(rows[0], expected):
            data_rows = rows[1:]
            if not data_rows:
                return None, "El archivo solo contiene la cabecera; no hay filas de datos."
            header_note = True
        elif self.same_labels_wrong_order(rows[0], expected):
            return None, (
                "La cabecera contiene las mismas etiquetas que el proyecto pero en distinto orden. "
                f"Orden requerido: {', '.join(expected)}"
            )
        else:
            data_rows = rows
            header_note = False
        for idx, row in enumerate(data_rows, start=1):
            if len(row) != n_cols:
                expected_text = ", ".join(expected)
                row_context = f" (fila de datos {idx}" + (" tras la cabecera)" if header_note else ")")
                return None, (
                    f"Número de columnas incorrecto{row_context}: se esperaban {n_cols} "
                    f"({expected_text}), hay {len(row)}."
                )
            for col_idx, cell in enumerate(row):
                if not (cell or "").strip():
                    col = expected[col_idx]
                    row_context = f"Fila de datos {idx}" + (" (tras la cabecera)" if header_note else "")
                    return None, f"{row_context}: la columna «{col}» está vacía."
        return data_rows, None

    @staticmethod
    def files_changes(files: list[tuple[int, Path]]) -> dict:
        """Calculate row additions between ordered dataset snapshots."""
        changes = {}
        sorted_files = sorted(files, key=lambda x: x[0])
        file_0 = sorted_files[0][1]
        with open(file_0, "r", encoding="utf-8") as file_obj:
            lines_prev = file_obj.readlines()
            changes[0] = {"round": sorted_files[0][0], "added": [], "length": len(lines_prev) - 1}
            for line in lines_prev[1:]:
                changes[0]["added"].append(line.strip().split(","))
        for idx in range(1, len(sorted_files)):
            file_i = sorted_files[idx][1]
            with open(file_i, "r", encoding="utf-8") as file_obj:
                lines_curr = file_obj.readlines()
                changes[idx] = {"round": sorted_files[idx][0], "added": [], "length": len(lines_curr) - 1}
                prev_counter = Counter(line.strip() for line in lines_prev[1:])
                curr_counter = Counter(line.strip() for line in lines_curr[1:])
                for row_text, curr_count in curr_counter.items():
                    added_count = curr_count - prev_counter.get(row_text, 0)
                    if added_count > 0:
                        for _ in range(added_count):
                            changes[idx]["added"].append(row_text.split(","))
                lines_prev = lines_curr
        return changes
