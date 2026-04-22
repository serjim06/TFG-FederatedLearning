import json
import queue
from sqlite3 import DatabaseError
import tkinter as tk
from tkinter import ttk, filedialog
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any
import src.db.dbcon as dbcon
import src.utils.icons.image_finder as image_finder
from PIL import ImageTk, Image
from TkToolTip import ToolTip
from src.gui.new_project import NewProjectDialog, SeeProjectDialog
from src.gui.base_list import SEC_BTN_STYLE, BaseListFrame
from src.gui import dialogs
from src.gui.dialogs import FederatedRoundsDialog, PredictDialog
from src.models.node import Node, predict
from src.gui.project_metrics import (
    ProjectMetricsDialog,
    get_metrics_per_round,
    get_regression_metrics_bundle,
    get_time_per_round,
    get_datasets_changes,
)
from src.projects.reports import generate_report
from src.federated import run_federated_training
from src.models.node import merge_project_training_results
from collections import Counter
from math import sqrt

class ProjectListFrame(BaseListFrame):
    def __init__(self, parent, switch_frame, usuario):
            super().__init__(parent, switch_frame, usuario, columns={"id": 330, "name": 55, "description": 300, "pending": 15})
            
            self.winfo_toplevel().bind("<Configure>", self._reposition_suggestions)

            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ProjectListWorker")
            self._loading_reason = ""

            self._status_frame = tk.Frame(self, bg="#e6edf7", bd=1, relief="solid")
            self._status_frame.pack(side="bottom", fill="x")

            self._status_label = tk.Label(
                self._status_frame,
                text="Listo.",
                anchor="w",
                bg="#e6edf7",
                fg="#1d2d44",
                font=("Segoe UI", 10)
            )
            self._status_label.pack(side="left", fill="x", expand=True, padx=10, pady=6)

            self._federated_running = False
            self._fed_queue: queue.Queue = queue.Queue()

    def destroy(self):
        try:
            if hasattr(self, "_executor") and self._executor is not None:
                self._executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
        super().destroy()

    def _show_loading(self, reason: str = "Cargando…"):
        self._loading_reason = reason

        try:
            self._status_label.configure(text=reason)
        except Exception:
            pass

        try:
            self.update_idletasks()
        except Exception:
            pass

        try:
            self.metrics_button.state(["disabled"])
            self.config_button.state(["disabled"])
            self.train_button.state(["disabled"])
            self.report_button.state(["disabled"])
            self.predict_button.state(["disabled"])
            self.tree.configure(selectmode="none")
        except Exception:
            pass

    def _hide_loading(self):
        self._loading_reason = ""
        try:
            self._status_label.configure(text="Listo.")
        except Exception:
            pass

        try:
            self.tree.configure(selectmode="extended")
        except Exception:
            pass
        self._selected_item_changed()

    @staticmethod
    def _format_eta_seconds(seconds: float | None) -> str:
        if seconds is None or seconds < 0:
            return "—"
        s = int(round(seconds))
        m, s = divmod(s, 60)
        if m:
            return f"{m}m {s}s"
        return f"{s}s"

    def _set_federated_status(
        self,
        current_round: int,
        total_rounds: int,
        message: str,
        eta_seconds: float | None,
    ) -> None:
        eta_txt = ""
        if eta_seconds is not None:
            eta_txt = f" — ETA ~ {self._format_eta_seconds(eta_seconds)}"
        try:
            self._status_label.configure(
                text=(
                    f"Entrenamiento federado — Ronda {current_round}/{total_rounds}{eta_txt} — {message}"
                )
            )
        except (tk.TclError, AttributeError):
            pass

    def _poll_federated_queue(self) -> None:
        if not self._federated_running:
            return
        try:
            while True:
                item = self._fed_queue.get_nowait()
                kind = item[0]
                if kind == "progress":
                    _, cur, total, msg, eta = item
                    self._set_federated_status(cur, total, msg, eta)
                elif kind == "success":
                    _, merged, total_sec, prev, project_id_b, fed_rounds = item
                    self._federated_running = False
                    upd: dict = {"id": project_id_b, "training_results": merged}
                    if not prev.get("type"):
                        upd["type"] = (
                            "regression"
                            if (prev.get("metrics") or "") == "mean_squared_error"
                            else "classification"
                        )
                    cur_data_round = int(prev.get("training_round") or 0)
                    upd["training_round"] = cur_data_round + int(fed_rounds) + 1
                    dbcon.command("update", "projects", upd)
                    self._hide_loading()
                    dialogs.InfoDialog(
                        self,
                        "Entrenamiento federado",
                        f"Completado en {total_sec:.1f} s. Resultados guardados en el proyecto.",
                        "info",
                    )
                    return
                elif kind == "error":
                    _, err = item
                    self._federated_running = False
                    self._hide_loading()
                    dialogs.InfoDialog(
                        self,
                        "Error",
                        f"Falló el entrenamiento federado: {err}",
                        "error",
                    )
                    return
        except queue.Empty:
            pass
        self.after(50, self._poll_federated_queue)

    def _predict(self) -> None:
        seleccionado = self.tree.selection()
        if not seleccionado:
            dialogs.InfoDialog(
                self,
                "Información",
                "Selecciona un proyecto para predecir.",
                "info",
            )
            return

        item_id = seleccionado[0]
        values = self.tree.item(item_id, "values")
        project_id = uuid.UUID(values[0]).bytes

        try:
            project_data = dbcon.command("select", "projects", {"id": project_id})
        except (ValueError, DatabaseError) as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")
            return

        if not project_data:
            dialogs.InfoDialog(self, "Error", "No se encontró el proyecto.", "error")
            return

        row = project_data[0]
        nodes = json.loads(row["nodes"]) if row.get("nodes") else []
        if not nodes:
            dialogs.InfoDialog(
                self,
                "Sin nodos",
                "El proyecto no tiene nodos asignados. Añade nodos en la configuración del proyecto.",
                "warning",
            )
            return

        in_features = (
            json.loads(row["input_features"])
            if isinstance(row["input_features"], str)
            else row["input_features"]
        )
        def on_confirm(vals: list[float], node_id: str) -> None:
            self._start_prediction_job(project_id, node_id, vals)

        PredictDialog(
            self,
            feature_names=in_features,
            node_ids=nodes,
            default_line="",
            on_confirm=on_confirm,
        )

    def _prediction_outputs_for_pending(
        self, prediction_result: Any, output_features: list[str]
    ) -> list[Any]:
        if not output_features:
            return []

        if isinstance(prediction_result, dict):
            if len(output_features) == 1 and "label" in prediction_result:
                return [prediction_result["label"]]
            raw_output = prediction_result.get("output")
        else:
            raw_output = prediction_result

        if isinstance(raw_output, tuple):
            values = list(raw_output)
        elif isinstance(raw_output, list):
            values = raw_output
        else:
            values = [raw_output]

        if len(values) < len(output_features):
            values = values + [""] * (len(output_features) - len(values))
        return values[: len(output_features)]

    def _build_prediction_pending_entry(
        self,
        project_row: dict[str, Any],
        node_id: str,
        input_values: list[float],
        prediction_result: Any,
    ) -> dict[str, Any]:
        in_features = (
            json.loads(project_row["input_features"])
            if isinstance(project_row["input_features"], str)
            else project_row["input_features"]
        )
        out_features = (
            json.loads(project_row["output_features"])
            if isinstance(project_row["output_features"], str)
            else project_row["output_features"]
        )
        output_values = self._prediction_outputs_for_pending(prediction_result, out_features)

        pending_data: dict[str, Any] = {}
        for key, value in zip(in_features, input_values):
            pending_data[key] = value
        for key, value in zip(out_features, output_values):
            pending_data[key] = value

        return {
            "node": f"node_{node_id}",
            "data": pending_data,
        }

    def _start_prediction_job(
        self, project_id: bytes, node_id: str, values: list[float]
    ) -> None:
        try:
            project_data = dbcon.command("select", "projects", {"id": project_id})
        except (ValueError, DatabaseError) as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")
            return

        if not project_data:
            dialogs.InfoDialog(self, "Error", "No se encontró el proyecto.", "error")
            return
        row = project_data[0]

        try:
            node_rows = dbcon.command("select", "nodes", {"id": uuid.UUID(node_id).bytes})
        except (ValueError, DatabaseError) as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")
            return

        if not node_rows:
            dialogs.InfoDialog(self, "Error", "No se encontró el nodo en la base de datos.", "error")
            return
        nd = node_rows[0]
        node = Node(nd["id"], nd["valid"], nd["project_id"])

        self._show_loading("Realizando predicción…")

        def _compute(node_obj: Node, vals: list[float], project_row: dict[str, Any]) -> Any:
            return predict(node_obj, vals, project=dict(project_row))

        future = self._executor.submit(_compute, node, values, row)

        def _done_callback(f):
            def _finish_on_ui_thread():
                try:
                    out = f.result()
                    pending_raw = row.get("unconfirmed_results") or "[]"
                    pending = json.loads(pending_raw) if isinstance(pending_raw, str) else list(pending_raw)
                    pending.append(self._build_prediction_pending_entry(row, node_id, values, out))
                    dbcon.command(
                        "update",
                        "projects",
                        {"id": project_id, "unconfirmed_results": json.dumps(pending, ensure_ascii=False)},
                    )
                    self._hide_loading()
                    self._initialize_tree()
                    dialogs.InfoDialog(
                        self,
                        "Predicción completada",
                        (
                            "Predicción añadida a 'Confirmar Resultados Pendientes' "
                            f"del proyecto '{row['name']}'."
                        ),
                        "info",
                    )
                except Exception as e:
                    self._hide_loading()
                    dialogs.InfoDialog(self, "Error en predicción", str(e), "error")

            try:
                self.after(0, _finish_on_ui_thread)
            except Exception:
                pass

        future.add_done_callback(_done_callback)

    def _play_federated_training(self) -> None:
        if self._federated_running:
            return
        seleccionado = self.tree.selection()
        if not seleccionado:
            dialogs.InfoDialog(
                self,
                "Información",
                "Selecciona un proyecto para entrenar.",
                "info",
            )
            return

        item_id = seleccionado[0]
        values = self.tree.item(item_id, "values")
        project_id = uuid.UUID(values[0]).bytes

        def on_confirm(num_rounds: int) -> None:
            self._start_federated_job(project_id, num_rounds)

        FederatedRoundsDialog(self, default_rounds=5, on_confirm=on_confirm)

    def _start_federated_job(self, project_id: bytes, num_rounds: int) -> None:
        if self._federated_running:
            return
        try:
            project_data = dbcon.command("select", "projects", {"id": project_id})
        except (ValueError, DatabaseError) as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")
            return

        if not project_data:
            dialogs.InfoDialog(self, "Error", "No se encontró el proyecto.", "error")
            return

        row = project_data[0]
        nodes = json.loads(row["nodes"]) if row.get("nodes") else []
        if not nodes:
            dialogs.InfoDialog(
                self,
                "Sin nodos",
                "El proyecto no tiene nodos asignados. Añade nodos en la configuración del proyecto.",
                "warning",
            )
            return

        self._federated_running = True
        self._show_loading("Preparando servidor federado…")

        def _work(payload: list, rounds: int, pid: bytes) -> None:
            def on_progress(
                cur: int,
                total: int,
                msg: str,
                eta: float | None,
            ) -> None:
                try:
                    self._fed_queue.put(("progress", cur, total, msg, eta))
                except Exception:
                    pass

            try:
                out = run_federated_training(payload[0], rounds, on_progress=on_progress)
                merged = merge_project_training_results(
                    payload[0].get("training_results"),
                    out["training_results_entry"],
                )
                self._fed_queue.put(
                    (
                        "success",
                        merged,
                        out["total_time_seconds"],
                        payload[0],
                        pid,
                        rounds,
                    )
                )
            except Exception as e:
                self._fed_queue.put(("error", e))

        self._executor.submit(_work, project_data, num_rounds, project_id)
        self.after(0, self._poll_federated_queue)

    def _insert_extra_buttons(self):
            self.config_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("settings")).resize((24,24)))
            self.play_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("play")).resize((24,24)))
            self.train_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("train")).resize((24,24)))
            self.metrics_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("metrics")).resize((24,24)))
            self.report_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("report")).resize((24,24)))

            self.predict_button = ttk.Button(
                self.toolbox,
                image=self.play_image,
                text="",
                compound="left",
                command=self._predict,
                width=2,
                style=SEC_BTN_STYLE,
            )
            self.predict_button.pack(side="left", padx=5, pady=5)
            self.predict_button.state(["disabled"])

            self.train_button = ttk.Button(self.toolbox, image=self.train_image, text="", compound="left",
                       command=self._play_federated_training, width=2, style=SEC_BTN_STYLE)
            self.train_button.pack(side="left", padx=5, pady=5)
            self.train_button.state(["disabled"])
            
            self.config_button = ttk.Button(self.toolbox, image=self.config_image, text="", compound="left",
                       command=self._config_project, width=2, style="Sec.TButton")
            self.config_button.pack(side="left", padx=5, pady=5)
            self.config_button.state(["disabled"])

            self.metrics_button = ttk.Button(self.toolbox, image=self.metrics_image, text="", compound="left",
                       command=self._view_metrics, width=2, style=SEC_BTN_STYLE)
            self.metrics_button.pack(side="left", padx=5, pady=5)
            self.metrics_button.state(["disabled"])

            self.report_button = ttk.Button(self.toolbox, image=self.report_image, text="", compound="left",
                       command=self._download_report, width=2, style=SEC_BTN_STYLE)
            self.report_button.pack(side="left", padx=5, pady=5)
            self.report_button.state(["disabled"])

            ToolTip(self.add_button, text="Crear un proyecto nuevo", delay=0.5)
            ToolTip(self.delete_button, text="Eliminar proyecto seleccionado", delay=0.5)
            ToolTip(self.train_button, text="Iniciar entrenamiento federado (servidor Flower)", delay=0.5)
            ToolTip(self.config_button, text="Configurar el proyecto seleccionado", delay=0.5)
            ToolTip(self.metrics_button, text="Ver las métricas del proyecto seleccionado", delay=0.5)
            ToolTip(self.report_button, text="Descargar el reporte del proyecto seleccionado", delay=0.5)
            ToolTip(
                self.predict_button,
                text="Realizar predicción para el proyecto seleccionado",
                delay=0.5,
            )
            
            self._insert_search_bar()
       
    def _insert_search_bar(self):
        self.search_var = tk.StringVar()
        
        search_frame = ttk.Frame(self.toolbox)
        search_frame.pack(side="right", padx=5, pady=5)
        
        entry_frame = ttk.Frame(search_frame)
        entry_frame.pack(side="left")
        
        self.search_entry = ttk.Entry(entry_frame, textvariable=self.search_var, width=20)
        self.search_entry.pack()
        
        self.search_var.trace("w", self._update_suggestions)
        self.search_entry.bind("<FocusOut>", self._hide_suggestions)
        self.search_entry.bind("<Return>", lambda event: self._perform_search())
                    
        search_button = ttk.Button(search_frame, text="Buscar", command=self._perform_search, width=6, style=SEC_BTN_STYLE)
        search_button.pack(side="right", padx=5)
        
        self._create_suggestion_popup()
       
    def _create_suggestion_popup(self):
        self.suggestion_popup = tk.Toplevel(self)
        self.suggestion_popup.withdraw()
        self.suggestion_popup.overrideredirect(True)
        self.suggestion_popup.attributes("-topmost", True)

        self.suggestion_list = tk.Listbox(
            self.suggestion_popup,
            height=4,
            borderwidth=1,
            relief="solid"
        )
        self.suggestion_list.pack(fill="both", expand=True)
        
        self.suggestion_list.bind("<<ListboxSelect>>", self._select_suggestion)
    
    def _hide_suggestions(self, event=None):
        self.suggestion_popup.withdraw()
    
    def _show_suggestions(self):
        if not self.suggestion_list.size():
            self.suggestion_popup.withdraw()
            return

        x = self.search_entry.winfo_rootx()
        y = self.search_entry.winfo_rooty() + self.search_entry.winfo_height()
        w = self.search_entry.winfo_width()

        self.suggestion_popup.geometry(f"{w}x80+{x}+{y}")
        self.suggestion_popup.deiconify()
        
    def _update_suggestions(self, *args):
        search_term = self.search_var.get().lower()
        if not search_term:
            self._hide_suggestions()
            return
        suggestions = self._get_suggestions_vector(search_term)
        
        self.suggestion_list.delete(0, tk.END)
        
        for s in suggestions:
            self.suggestion_list.insert(tk.END, s)
            
        self._show_suggestions()
    
    def _select_suggestion(self, event):
        selected_suggestion = self.suggestion_list.get(self.suggestion_list.curselection())
        self.search_var.set(selected_suggestion)
        self._perform_search()
        
    def _perform_search(self):
        search_term = self.search_var.get()
        
        if not search_term:
            return
        
        projects = []

        for item_id in self.tree.get_children():    
            values = self.tree.item(item_id, "values")

            project = {
                "id": uuid.UUID(values[0]).bytes,
                "name": values[1],
                "description": values[2],
                "unconfirmed_results": values[3] == "True"
            }
            projects.append(project)

        if not projects:
            return

        self.tree.delete(*self.tree.get_children())
        
        suggestions = []
        
        v1 = self.word2vec(search_term)
        
        for project in projects:
            v2 = self.word2vec(project["name"])
            
            similarity = self.cosdis(v1, v2)
            
            suggestions.append((project, similarity))
        
        sorted_suggestions = sorted(suggestions, reverse = True, key=lambda suggestion: suggestion[1])
        
        projects_ordered = [sugg[0] for sugg in sorted_suggestions]
        
        self._insert_tree(projects_ordered)
        self._hide_suggestions()
        
    
    def _reposition_suggestions(self, event=None):
        try:
            if not self.winfo_exists():
                return
        except (tk.TclError, AttributeError):
            return

        if event and event.widget != self.winfo_toplevel():
            return

        x = self.search_entry.winfo_rootx()
        y = self.search_entry.winfo_rooty() + self.search_entry.winfo_height()
        w = self.search_entry.winfo_width()

        self.suggestion_popup.geometry(f"{w}x80+{x}+{y}")
        
    def word2vec(self, word):
        cw = Counter(word)
        sw = set(cw)
        lw = sqrt(sum(c*c for c in cw.values()))

        return cw, sw, lw
    
    def _get_suggestions_vector(self, search_term, max_suggestions=5):
        
        names = [name.lower() for name in self.project_names]
        
        suggestions = []
        
        v1 = self.word2vec(search_term)
        
        for word in names:
            v2 = self.word2vec(word)
            
            similarity = self.cosdis(v1, v2)
            
            if word not in suggestions:
                suggestions.append((word, similarity))
        
        sorted_suggestions = sorted(suggestions, reverse = True, key=lambda suggestion: suggestion[1])
            
        return [suggestion[0] for suggestion in sorted_suggestions[:max_suggestions]]

    def cosdis(self, v1, v2):
        common = v1[1].intersection(v2[1])
        return sum(v1[0][ch]*v2[0][ch] for ch in common)/v1[2]/v2[2]
       
       
    def _selected_item_changed(self):
        super()._selected_item_changed()
        self.config_button.state(["!disabled"]) if self.tree.selection() else self.config_button.state(["disabled"])
        if self._federated_running:
            self.train_button.state(["disabled"])
        else:
            self.train_button.state(["!disabled"]) if self.tree.selection() else self.train_button.state(["disabled"])
        self.metrics_button.state(["!disabled"]) if self.tree.selection() else self.metrics_button.state(["disabled"])
        self.report_button.state(["!disabled"]) if self.tree.selection() else self.report_button.state(["disabled"])
        self.predict_button.state(["!disabled"]) if self.tree.selection() else self.predict_button.state(["disabled"])
    
    def _config_project(self):
        seleccionado = self.tree.selection()
        
        if seleccionado:
            item_id = seleccionado[0]
            values = self.tree.item(item_id, "values") 
            project_id = uuid.UUID(values[0]).bytes
            
            try:
                project_data = dbcon.command("select", "projects", {"id": project_id})
                if project_data:
                    SeeProjectDialog(self, project_id)
            except (ValueError, DatabaseError) as e:
                dialogs.InfoDialog(self, "Error", str(e), "error")
        else:
            dialogs.InfoDialog(self, "Información", "No hay ningún proyecto seleccionado para configurar.", "info")
    
    def _view_metrics(self):
        seleccionado = self.tree.selection()
        if seleccionado:
            item_id = seleccionado[0]
            values = self.tree.item(item_id, "values")
            project_id = uuid.UUID(values[0]).bytes
            try:
                project_data = dbcon.command("select", "projects", {"id": project_id})
                if project_data:
                    self._show_loading("Calculando métricas…")

                    def _compute(payload):
                        training_data = json.loads(payload[0]["training_results"])
                        project_type = payload[0]["type"]
                        metrics = get_metrics_per_round(training_data, project_type)
                        if project_type == "regression":
                            _, y_true_total, y_pred_total = get_regression_metrics_bundle(
                                training_data
                            )
                        else:
                            y_true_total, y_pred_total = [], []
                        time_per_round = get_time_per_round(training_data)
                        nodes = json.loads(payload[0]["nodes"])
                        datasets_changes = get_datasets_changes(nodes)
                        return (
                            training_data,
                            project_type,
                            metrics,
                            time_per_round,
                            datasets_changes,
                            y_true_total,
                            y_pred_total,
                        )

                    future = self._executor.submit(_compute, project_data)

                    def _done_callback(f):
                        def _finish_on_ui_thread():
                            try:
                                (
                                    training_data,
                                    project_type,
                                    metrics,
                                    time_per_round,
                                    datasets_changes,
                                    y_true_total,
                                    y_pred_total,
                                ) = f.result()
                                project_data[0]["time_per_round"] = time_per_round
                                project_data[0]["datasets_changes"] = datasets_changes
                                project_data[0]["metrics"] = metrics
                                project_data[0]["y_true"] = y_true_total
                                project_data[0]["y_pred"] = y_pred_total
                                self._hide_loading()
                                ProjectMetricsDialog(self, training_data, project_data[0], title="Métricas del Proyecto")
                            except Exception as e:
                                self._hide_loading()
                                dialogs.InfoDialog(self, "Error", str(e), "error")

                        try:
                            self.after(0, _finish_on_ui_thread)
                        except Exception:
                            pass

                    future.add_done_callback(_done_callback)
            except (ValueError, DatabaseError) as e:
                dialogs.InfoDialog(self, "Error", str(e), "error")
        else:
            dialogs.InfoDialog(self, "Información", "No hay ningún proyecto seleccionado para ver las métricas.", "info")
    
    def _download_report(self):
        seleccionado = self.tree.selection()
        if not seleccionado:
            dialogs.InfoDialog(self, "Información", "No hay ningún proyecto seleccionado para generar el reporte.", "info")
            return

        item_id = seleccionado[0]
        values = self.tree.item(item_id, "values")
        project_id = uuid.UUID(values[0]).bytes

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Guardar reporte",
            confirmoverwrite=True,
        )
        if not path:
            return

        try:
            project_data = dbcon.command("select", "projects", {"id": project_id})
            if not project_data:
                dialogs.InfoDialog(self, "Error", "No se han encontrado datos del proyecto para generar el reporte.", "error")
                return

            self._show_loading("Generando reporte…")

            def _compute(proj, output_path):
                training_data = proj[0]["training_results"]
                project_type = proj[0]["type"]
                num_rounds = proj[0]["training_round"]
                generate_report(
                    str(uuid.UUID(bytes=proj[0]["id"])),
                    proj[0]["name"],
                    proj[0]["description"],
                    num_rounds,
                    project_type,
                    training_data,
                    output_path,
                )

            future = self._executor.submit(_compute, project_data, path)

            def _done_callback(f):
                def _finish_on_ui_thread():
                    try:
                        f.result()
                        self._hide_loading()
                        dialogs.InfoDialog(self, "Éxito", "Reporte generado correctamente.", "info")
                    except Exception as e:
                        self._hide_loading()
                        dialogs.InfoDialog(self, "Error", f"No se pudo generar el reporte: {e}", "error")

                try:
                    self.after(0, _finish_on_ui_thread)
                except Exception:
                    pass

            future.add_done_callback(_done_callback)

        except (ValueError, DatabaseError) as e:
            self._hide_loading()
            dialogs.InfoDialog(self, "Error", f"No se pudo generar el reporte: {e}", "error")

    def _add_item(self):
        try: 
            NewProjectDialog(self, self.usuario["id"])
        except (ValueError, DatabaseError) as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")
            return
    
    def _delete_item(self):
        seleccionado = self.tree.selection()
        canceled = []

        if seleccionado:
            for item in seleccionado:
                item_id = item
                
                if not dialogs.OptionDialog.ask(self, "Confirmar eliminación", "¿Estás seguro de que deseas eliminar el proyecto seleccionado? Esta acción no se puede deshacer."):
                    canceled.append(item)
                    continue
                
                values = self.tree.item(item_id, "values")
                project_id = uuid.UUID(values[0]).bytes
                
                try:
                    self._invalidate_nodes(project_id)
                    
                    dbcon.command("delete", "projects", {"id": project_id})
                except (ValueError, DatabaseError) as e:
                    dialogs.InfoDialog(self, "Error", str(e), "error")

            self._update_tree_after_delete(seleccionado, canceled)
            dialogs.InfoDialog(self, "Información", "Proyecto(s) eliminado(s) correctamente.", "info")
        else:
            dialogs.InfoDialog(self, "Información", "No hay ningún nodo seleccionado para eliminar.", "info")

    def _invalidate_nodes(self, project_id):
        """
        Invalidates nodes associated with a project and removes their datasets, as they are unlikely to be used anymore.
        
        Args:
            project_id (bytes): The id of the project whose nodes are to be invalidated.
        """
        
        project_data = dbcon.command("select", "projects", {"id": project_id}) 
                    
        if project_data:
            project_nodes = json.loads(project_data[0]["nodes"])
                        
            for node_id in project_nodes:
                self._eliminate_dataset(uuid.UUID(node_id).bytes)
                            
                try:
                    dbcon.command("update", "nodes", {"id": uuid.UUID(node_id).bytes, "valid": 0})
                except (ValueError, DatabaseError) as e:
                    dialogs.InfoDialog(self, "Error", str(e), "error")
                    
    
    def _initialize_tree(self):
        self.tree.delete(*self.tree.get_children())
        
        try:
            projects = dbcon.command("select", "projects", {"uid": self.usuario['id']})

            formatted_projects = []

            for p in projects:
                pend = False if not json.loads(p["unconfirmed_results"]) else True
                
                p["unconfirmed_results"] = pend
                formatted_projects.append(p)
                
                
                
                
                
        except (ValueError, DatabaseError) as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")

        self.project_names = [project_data["name"] for project_data in projects]

        self._insert_tree(formatted_projects)

    def _insert_tree(self, projects):
        self.layers = {}

        not_img = Image.open(image_finder.find_image("pend_not")).resize((24,24))
        p_img = Image.open(image_finder.find_image("project")).resize((24,24))

        self.project_image = ImageTk.PhotoImage(p_img)
        self.pend_image = ImageTk.PhotoImage(not_img)



        for project_data in projects:
            
            
            if str(uuid.UUID(bytes=project_data["id"])) not in self.layers:
                self.layers[str(uuid.UUID(bytes=project_data["id"]))] = self.tree.insert("", "end",
                                                                                text="Project:",
                                                                                values=(str(uuid.UUID(bytes=project_data["id"])), project_data["name"], project_data["description"], project_data["unconfirmed_results"]),
                                                                                image=self.project_image if not project_data["unconfirmed_results"] else self.pend_image)

        self.tree.update_idletasks()