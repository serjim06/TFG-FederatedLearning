import json
from sqlite3 import DatabaseError
import tkinter as tk
from tkinter import ttk, filedialog
from tkinter import filedialog
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
import src.db.dbcon as dbcon
import src.utils.icons.image_finder as image_finder
from PIL import ImageTk, Image
from TkToolTip import ToolTip
from src.gui.new_project import NewProjectDialog, SeeProjectDialog
from src.gui.base_list import SEC_BTN_STYLE, BaseListFrame
from src.gui import dialogs
from src.gui.project_metrics import ProjectMetricsDialog, get_metrics_per_round, get_time_per_round, get_datasets_changes
from src.projects.reports import generate_report
from src.projects.reports import generate_report
from collections import Counter
from math import sqrt

class ProjectListFrame(BaseListFrame):
    def __init__(self, parent, switch_frame, usuario):
            super().__init__(parent, switch_frame, usuario, columns={"id": 330, "name": 55, "description": 300, "pending": 15})
            
            self.winfo_toplevel().bind("<Configure>", self._reposition_suggestions)

            # Executor para tareas pesadas sin bloquear la UI
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ProjectListWorker")
            self._loading_reason = ""

            # Barra de estado inferior (siempre visible)
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

        # forzar render del estado antes de continuar
        try:
            self.update_idletasks()
        except Exception:
            pass

        # evitar interacción mientras carga
        try:
            self.metrics_button.state(["disabled"])
            self.config_button.state(["disabled"])
            self.play_button.state(["disabled"])
            self.report_button.state(["disabled"])
            self.tree.configure(selectmode="none")
        except Exception:
            pass

    def _hide_loading(self):
        self._loading_reason = ""
        try:
            self._status_label.configure(text="Listo.")
        except Exception:
            pass

        # restaurar interacción (botones según selección actual)
        try:
            self.tree.configure(selectmode="extended")
        except Exception:
            pass
        self._selected_item_changed()
    
    def _insert_extra_buttons(self):
            self.config_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("settings")).resize((24,24)))
            self.play_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("play")).resize((24,24)))
            self.metrics_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("metrics")).resize((24,24)))
            self.report_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("report")).resize((24,24)))

            self.play_button = ttk.Button(self.toolbox, image=self.play_image, text="", compound="left",
                       command=lambda e: print("no implementado"), width=2, style=SEC_BTN_STYLE)
            self.play_button.pack(side="left", padx=5, pady=5)
            self.play_button.state(["disabled"])
            
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
            ToolTip(self.play_button, text="Realizar una predicción en el proyecto seleccionado", delay=0.5)
            ToolTip(self.config_button, text="Configurar el proyecto seleccionado", delay=0.5)
            ToolTip(self.metrics_button, text="Ver las métricas del proyecto seleccionado", delay=0.5)
            ToolTip(self.report_button, text="Descargar el reporte del proyecto seleccionado", delay=0.5)
            
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
        self.suggestion_popup.overrideredirect(True)  # sin bordes
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

        self.tree.delete(*self.tree.get_children()) #Elimina los proyectos insertados
        
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
        
        sorted_suggestions = sorted(suggestions, reverse = True, key=lambda suggestion: suggestion[1]) #orders by similarity
            
        return [suggestion[0] for suggestion in sorted_suggestions[:max_suggestions]]

    def cosdis(self, v1, v2):
        common = v1[1].intersection(v2[1])
        return sum(v1[0][ch]*v2[0][ch] for ch in common)/v1[2]/v2[2]
       
       
    def _selected_item_changed(self):
        super()._selected_item_changed()
        self.config_button.state(["!disabled"]) if self.tree.selection() else self.config_button.state(["disabled"])
        self.play_button.state(["!disabled"]) if self.tree.selection() else self.play_button.state(["disabled"])
        self.metrics_button.state(["!disabled"]) if self.tree.selection() else self.metrics_button.state(["disabled"])
        self.report_button.state(["!disabled"]) if self.tree.selection() else self.report_button.state(["disabled"])
    
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
                        time_per_round = get_time_per_round(training_data)
                        nodes = json.loads(payload[0]["nodes"])
                        datasets_changes = get_datasets_changes(nodes)
                        return training_data, project_type, metrics, time_per_round, datasets_changes

                    future = self._executor.submit(_compute, project_data)

                    def _done_callback(f):
                        def _finish_on_ui_thread():
                            try:
                                training_data, project_type, metrics, time_per_round, datasets_changes = f.result()
                                project_data[0]["time_per_round"] = time_per_round
                                project_data[0]["datasets_changes"] = datasets_changes
                                project_data[0]["metrics"] = metrics
                                self._hide_loading()
                                ProjectMetricsDialog(self, training_data, project_data[0], title="Métricas del Proyecto")
                            except Exception as e:
                                self._hide_loading()
                                dialogs.InfoDialog(self, "Error", str(e), "error")

                        try:
                            self.after(0, _finish_on_ui_thread)
                        except Exception:
                            # si el frame ya no existe
                            pass

                    future.add_done_callback(_done_callback)
            except (ValueError, DatabaseError) as e:
                dialogs.InfoDialog(self, "Error", str(e) + "errorororejoriaior", "error")
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

        # Elegir destino del PDF
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

            # Informar al usuario y lanzar generación en segundo plano
            self._show_loading("Generando reporte…")

            def _compute(proj, output_path):
                # Se ejecuta en un hilo: no tocar la UI aquí
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
                        # Propagará cualquier excepción levantada en el hilo
                        f.result()
                        self._hide_loading()
                        dialogs.InfoDialog(self, "Éxito", "Reporte generado correctamente.", "info")
                    except Exception as e:
                        self._hide_loading()
                        dialogs.InfoDialog(self, "Error", f"No se pudo generar el reporte: {e}", "error")

                try:
                    self.after(0, _finish_on_ui_thread)
                except Exception:
                    # El frame puede haberse destruido
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
                    #return
                
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
        p_img = Image.open(image_finder.find_image("project"))

        self.project_image = ImageTk.PhotoImage(p_img)
        self.pend_image = ImageTk.PhotoImage(not_img)



        for project_data in projects:
            
            
            if str(uuid.UUID(bytes=project_data["id"])) not in self.layers:
                self.layers[str(uuid.UUID(bytes=project_data["id"]))] = self.tree.insert("", "end",
                                                                                text="Project:",
                                                                                values=(str(uuid.UUID(bytes=project_data["id"])), project_data["name"], project_data["description"], project_data["unconfirmed_results"]),
                                                                                image=self.project_image if not project_data["unconfirmed_results"] else self.pend_image)

        self.tree.update_idletasks()