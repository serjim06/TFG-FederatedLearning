import json
import tkinter as tk
from tkinter import filedialog, ttk

from src.gui import dialogs
from src.gui.dialogs import BaseDialog
from src.utils import utils
from src.application.services.dataset_service import DatasetService
from src.application.use_cases.add_dataset_to_node import AddDatasetToNodeUseCase

class AddDatasetDialog(BaseDialog):
    def __init__(self, parent, nodes: list, project: dict):
        super().__init__(parent, "Añadir dataset")
        utils.get_style()
        self.nodes = list(nodes)
        self.project = project

        self._in_features = json.loads(project["input_features"])
        self._out_features = json.loads(project["output_features"])
        self._cur_round = int(project.get("training_round") or 0)
        self._add_dataset_use_case = AddDatasetToNodeUseCase(DatasetService())

        self._csv_path = tk.StringVar(value="")

        btn_row = tk.Frame(self, bg=utils.BG_COLOR)
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
        btn_row.pack(side="bottom", pady=16)

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
        ).pack(pady=(12, 8), padx=16, fill="x")

        form = tk.Frame(self, bg=utils.BG_COLOR)
        form.pack(fill="both", expand=True, padx=16, pady=4)

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
        self._file_row = tk.Frame(form, bg=utils.BG_COLOR)
        self._file_row.grid(row=1, column=1, sticky="ew", pady=4)
        self._file_row.columnconfigure(0, weight=1)
        self._file_row.columnconfigure(1, weight=0)

        self._path_label = tk.Label(
            self._file_row,
            textvariable=self._csv_path,
            background=utils.BG_COLOR,
            anchor="w",
            wraplength=1,
            justify="left",
        )
        self._path_label.grid(row=0, column=0, sticky="nsew")

        self._browse_btn = ttk.Button(
            self._file_row,
            text="Examinar…",
            style=utils.SEC_TBUTTON_STYLE,
            command=self._browse_csv,
        )
        self._browse_btn.grid(row=0, column=1, padx=(8, 0), sticky="ns")

        self._file_row.bind("<Configure>", self._update_path_wraplength)
        self._csv_path.trace_add("write", lambda *_: self.after_idle(self._update_path_wraplength))

        self.center_dialog()
        self.after_idle(self._update_path_wraplength)

    def _update_path_wraplength(self, _event=None):
        self.update_idletasks()
        try:
            fw = self._file_row.winfo_width()
            if fw <= 1:
                return
            bw = self._browse_btn.winfo_width() or 90
            pad = 16
            wl = max(48, fw - bw - pad)
            if wl != self._path_label.cget("wraplength"):
                self._path_label.configure(wraplength=wl)
        except tk.TclError:
            pass

    def _browse_csv(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Seleccionar CSV",
            filetypes=[("CSV", "*.csv"), ("Todos los archivos", "*.*")],
        )
        if path:
            self._csv_path.set(path)

    def _on_add(self):
        parent = self.master
        prev_self = self.cget("cursor") or ""
        prev_parent = (parent.cget("cursor") or "") if parent is not None else ""
        self.configure(cursor="watch")
        if parent is not None:
            parent.configure(cursor="watch")
        self.update()
        try:
            if not self.nodes:
                dialogs.InfoDialog(self, "Información", "No hay nodos en el proyecto.", "warning")
                return

            node = self._node_var.get().strip()
            if not node:
                dialogs.InfoDialog(self, "Información", "Selecciona un nodo.", "warning")
                return

            result = self._add_dataset_use_case.execute(
                node,
                self._csv_path.get(),
                self._in_features,
                self._out_features,
                self._cur_round,
            )
            if not result.ok:
                dialogs.InfoDialog(self, "Error", result.error or "No se pudo añadir el dataset", "error")
                return

            dialogs.InfoDialog(
                self.master,
                "Confirmación",
                f"Datos añadidos al dataset del nodo {node}.",
                "info",
            )
            self.destroy()
        finally:
            try:
                if self.winfo_exists():
                    self.configure(cursor=prev_self)
            except tk.TclError:
                pass
            try:
                if parent is not None and parent.winfo_exists():
                    parent.configure(cursor=prev_parent)
            except tk.TclError:
                pass
