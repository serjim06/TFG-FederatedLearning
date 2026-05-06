import json
import os
from pathlib import Path
from sqlite3 import DatabaseError
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import uuid

from PIL import Image, ImageTk
from TkToolTip import ToolTip

from src.utils.icons import image_finder
from src.projects.projects import cargar_modulo, verificar_modulo
from src.gui.add_dataset import AddDatasetDialog
from src.gui.confirm_results import ConfirmResultsFrame
from src.utils import utils
from src.gui import dialogs
from src.application.use_cases.create_project import CreateProjectUseCase
from src.application.use_cases.update_project import UpdateProjectUseCase
from src.infrastructure.repositories.sqlite_node_repository import SQLiteNodeRepository
from src.infrastructure.repositories.sqlite_project_repository import SQLiteProjectRepository

_LOSS_OPTIONS_CLASSIFICATION = (
    "categorical_crossentropy",
    "sparse_categorical_crossentropy",
    "binary_crossentropy",
)
_LOSS_OPTIONS_REGRESSION = ("mean_squared_error",)


class ScrollableNodesFrame(ttk.Frame):
    def __init__(self, parent, height=150):
        super().__init__(parent)

        style = utils.get_style()

        self.canvas = tk.Canvas(
            self,
            height=height,
            width=300,
            highlightthickness=0,
            bg=utils.BG_COLOR
        )

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview, style="White.Vertical.TScrollbar")

        self.inner = ttk.Frame(self.canvas)
        self.inner.configure(style="TFrame", width=300)

        self.inner.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self._inner_win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _on_canvas_configure(self, event):
        if event.widget is not self.canvas:
            return
        w = self.canvas.winfo_width()
        if w > 1:
            self.canvas.itemconfigure(self._inner_win, width=w)


FORM_LABEL = "Form.TLabel"

class NewProject(ttk.Frame):
    _STRATEGY_EXTRA_FIELDS = {
        "fed_ssfed": [
            {
                "key": "ssfed_z_threshold",
                "label": "SSFed z-threshold:",
                "type": "float",
                "default": 1.96,
                "from_": 0.1,
                "to": 10.0,
                "increment": 0.05,
                "width": 7,
                "tooltip": "Umbral z para seleccionar actualizaciones significativas en SSFed.",
            }
        ]
    }

    def __init__(self, parent, project, user_id=None, create_project_use_case: CreateProjectUseCase | None = None, *, grid_row=0):
        super().__init__(parent, padding=10)
        self.configure(style="TFrame")
        
        self.user_id = user_id
        self._create_project_use_case = create_project_use_case
        self._node_repository = SQLiteNodeRepository()

        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(grid_row, weight=1)
        self.grid(row=grid_row, column=0, sticky="nsew")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.project = project
        self.ruta = None
        self.input_features = []
        self.output_features = []
        self._strategy_param_widgets = {}

        self._build_ui()

    def _build_ui(self):
        row = 0
        
        self.scrollable_frame = ScrollableNodesFrame(self, height=600)
        self.scrollable_frame.grid(row=0, column=0, sticky="nsew")
        self.scrollable_frame.columnconfigure(0, weight=1)

        ttk.Label(self.scrollable_frame.inner, text="Nombre:", background="#eef4fb").grid(row=row, column=0, sticky="w")
        row += 1

        self.name_entry = tk.Text(self.scrollable_frame.inner, height=1, border=0.5, relief="solid")
        self.name_entry.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1

        ttk.Label(self.scrollable_frame.inner, text="Descripción:", background="#eef4fb").grid(row=row, column=0, sticky="w")
        row += 1

        self.description_text = tk.Text(self.scrollable_frame.inner, height=4, border=0.5, relief="solid")
        self.description_text.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1

        self.model_frame = ttk.Frame(self.scrollable_frame.inner, height=2, border=0.5, relief="solid")
        self.model_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1
        
        self.model_name = tk.StringVar()
        self.model_name.set("Ningún modelo seleccionado")
        self.model_name_label = tk.Label(self.model_frame, textvariable=self.model_name, background="#eef4fb")
        self.model_name_label.pack(side="left", padx=10, pady=5)
        self.model_select_btn = ttk.Button(self.model_frame, text="Seleccionar", command=self._select_model, style="Sec.TButton")
        self.model_select_btn.pack(side="right", padx=10, pady=5)

        self.task_type_label = ttk.Label(
            self.scrollable_frame.inner,
            text="Tipo de tarea:",
            background="#eef4fb",
            cursor="question_arrow",
        )
        self.task_type_label.grid(row=row, column=0, sticky="w", pady=(0, 0))
        row += 1

        self.task_type_cb = ttk.Combobox(
            self.scrollable_frame.inner,
            values=["classification", "regression"],
            state="readonly",
        )
        self.task_type_cb.set("classification")
        self.task_type_cb.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        self.task_type_cb.bind("<<ComboboxSelected>>", self._on_task_type_selected)
        row += 1

        ToolTip(
            self.task_type_label,
            text="Clasificación: salida discreta (etiquetas). Regresión: salida numérica continua.\n"
            "Si el modelo declara el tipo en get_features() (metadata.type), se rellena solo.",
        )

        self.loss_label = ttk.Label(
            self.scrollable_frame.inner,
            text="Función de pérdida:",
            background="#eef4fb",
            cursor="question_arrow",
        )
        self.loss_label.grid(row=row, column=0, sticky="w", pady=(0, 0))
        row += 1

        self.metrics_cb = ttk.Combobox(
            self.scrollable_frame.inner,
            values=list(_LOSS_OPTIONS_CLASSIFICATION),
            state="readonly",
        )
        self.metrics_cb.set("categorical_crossentropy")
        self.metrics_cb.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1

        ToolTip(
            self.loss_label,
            text="Función de pérdida compatible con el tipo de tarea (implementación PyTorch en el nodo).",
        )

        self.params_button = tk.Label(
            self.scrollable_frame.inner, text="▶ Parámetros",
            bg="#eef4fb",
            fg="#000000", cursor="hand2"
        )
        
        self.params_button.grid(row=row, column=0, sticky="w", pady=(5, 5))
        row += 1

        self.params_frame = ttk.Frame(self.scrollable_frame.inner)
        self.params_frame.columnconfigure(0, weight=1)
        self.params_frame.grid(row=row, column=0, sticky="ew", padx=15)
        row += 1

        self.opt = ttk.Label(self.params_frame, text="Optimizer:", background="#eef4fb", cursor="question_arrow")
        self.opt.grid(
            row=0, column=0, sticky="w"
        )

        self.optimizer_cb = ttk.Combobox(
            self.params_frame,
            values=["Adam", "SGD", "RMSprop"],
            state="readonly",
        )
        self.optimizer_cb.set("Adam")
        self.optimizer_cb.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        
        ToolTip(self.opt, text="Selecciona el optimizador que se utilizará durante el entrenamiento del modelo.")

        self.agg_lb = ttk.Label(self.params_frame, text="Aggregation strategy:", style=FORM_LABEL, cursor="question_arrow")
        self.agg_lb.grid(
            row=2, column=0, sticky="w"
        )

        self.aggregation_cb = ttk.Combobox(
            self.params_frame,
            values=[
                "fed_avg",
                "fed_med",
                "fed_scaffold",
                "fed_ssfed",
                "fed_sum",
                "fed_weighted",
            ],
            state="readonly",
        )
        self.aggregation_cb.grid(row=3, column=0, sticky="ew", pady=(0, 5))
        self.aggregation_cb.bind("<<ComboboxSelected>>", self._on_aggregation_strategy_selected)
        self.aggregation_cb.set("fed_avg")
        
        ToolTip(self.agg_lb, text="Selecciona la estrategia de agregación que se utilizará para combinar los modelos entrenados por los nodos.")

        self.strategy_params_label = ttk.Label(
            self.params_frame, text="Strategy parameters:", style=FORM_LABEL
        )
        self.strategy_params_label.grid(row=4, column=0, sticky="w")
        self.strategy_params_frame = ttk.Frame(self.params_frame)
        self.strategy_params_frame.columnconfigure(0, weight=1)
        self.strategy_params_frame.grid(row=5, column=0, sticky="ew", pady=(0, 5))

        self.epochs_label = ttk.Label(self.params_frame, text="Epochs:", style=FORM_LABEL, cursor="question_arrow")
        self.epochs_label.grid(
            row=6, column=0, sticky="w"
        )
        
        epochs_var = tk.IntVar(value=3)
        self.epochs = tk.Spinbox(
            self.params_frame,
            from_=1,
            to=100,
            textvariable=epochs_var,
            width=5,
        )
        self.epochs.grid(row=7, column=0, sticky="ew", pady=(0, 5))

        ToolTip(self.epochs_label, text="Número de veces que el modelo verá todo el conjunto de datos durante el entrenamiento.")

        self.val_split_label = ttk.Label(self.params_frame, text="Validation split:", style=FORM_LABEL, cursor="question_arrow")
        self.val_split_label.grid(
            row=8, column=0, sticky="w"
        )

        val_split_var = tk.DoubleVar(value=0.2)
        self.validation_split = tk.Spinbox(
            self.params_frame,
            from_=0.1,
            to=1.0,
            increment=0.05,
            textvariable=val_split_var,
            width=5,
        )
    
        self.validation_split.grid(row=9, column=0, sticky="ew", pady=(0, 5))
        
        ToolTip(self.val_split_label, text="Proporción del conjunto de datos que se utilizará para la validación durante el entrenamiento.")

        self.batch_frame = ttk.Frame(self.params_frame)
        self.batch_frame.grid(row=10, column=0, sticky="ew")
        
        self.warning_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("risk")).resize((18,18))) 
        
        self.warning_label = tk.Label(
            self.batch_frame,
            image=self.warning_image,
            background="#eef4fb",
            cursor="question_arrow"
        )
        self.warning_label.grid(row=0, column=0, sticky="w", pady=(5, 0))
        
        self.batch_size_label = ttk.Label(self.batch_frame, text="Batch size:", background="#eef4fb", cursor="question_arrow")
        self.batch_size_label.grid(
            row=0, column=1, sticky="w")
        
        batch_var = tk.IntVar(value=32)
        
        self.batch_size = tk.Spinbox(
            self.params_frame,
            from_=8,
            to=512,
            textvariable=batch_var,
            width=5,
        )

        self.batch_size.grid(row=11, column=0, sticky="ew", pady=(0, 5))
        
        ToolTip(self.batch_size_label, text="Número de muestras que se procesan antes de actualizar el modelo durante el entrenamiento.\nUn tamaño de batch más grande puede acelerar el entrenamiento, pero también requiere más memoria.")
        ToolTip(self.warning_label, text="Advertencia: Un tamaño de batch muy grande puede causar problemas de memoria en nodos con recursos limitados.")

        self.fraction_fit_label = ttk.Label(self.params_frame, text="Fraction fit:", style=FORM_LABEL, cursor="question_arrow")
        self.fraction_fit_label.grid(
            row=12, column=0, sticky="w")
        
        fit_var = tk.DoubleVar(value=0.8)
        self.fraction_fit = tk.Spinbox(
            self.params_frame,
            from_=0.1,
            to=1.0,
            increment=0.05,
            textvariable=fit_var,
            width=5,
        )
        self.fraction_fit.grid(row=13, column=0, sticky="ew", pady=(0, 5))
        
        ToolTip(self.fraction_fit_label, text="Proporción de nodos participantes que se utilizarán para el entrenamiento en cada ronda.")

        self.fraction_evaluate_label = ttk.Label(self.params_frame, text="Fraction evaluate:", style=FORM_LABEL, cursor="question_arrow")
        self.fraction_evaluate_label.grid(
            row=14, column=0, sticky="w")
        
        evaluate_var = tk.DoubleVar(value=0.5)
        self.fraction_evaluate = tk.Spinbox(
            self.params_frame,
            from_=0.1,
            to=1.0,
            increment=0.05,
            textvariable=evaluate_var,
            width=5,
        )
        self.fraction_evaluate.grid(row=15, column=0, sticky="ew", pady=(0, 5))
        
        ToolTip(self.fraction_evaluate_label, text="Proporción de nodos participantes que se utilizarán para la evaluación en cada ronda.")

        self.learning_rate_label = ttk.Label(self.params_frame, text="Learning rate:", style=FORM_LABEL, cursor="question_arrow")
        self.learning_rate_label.grid(
            row=16, column=0, sticky="w")
        
        lr_var = tk.DoubleVar(value=0.01)
        self.learning_rate = tk.Spinbox(
            self.params_frame,
            from_=0.0001,
            to=1.0,
            increment=0.0001,
            textvariable=lr_var,
            width=7,
        )
        self.learning_rate.grid(row=17, column=0, sticky="ew", pady=(0, 5))
        
        ToolTip(self.learning_rate_label, text="Tasa de aprendizaje que determina el tamaño de los pasos que da el optimizador al actualizar los pesos del modelo durante el entrenamiento.")

        ttk.Label(self.scrollable_frame.inner, text="Nodos:", background="#eef4fb").grid(
            row=row, column=0, sticky="w", pady=(10, 0)
        )
        row += 1

        self.node_vars = {}

        self.nodes_frame = tk.Frame(self.scrollable_frame.inner, background="#eef4fb", borderwidth=1, relief="solid")
        self.nodes_frame.grid(row=row, column=0, sticky="ews", pady=(5, 0))

        try:
            nodes = self._node_repository.list_available()
        except (ValueError, DatabaseError) as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")
            return

        selected_node_ids = set()
        if self.project is not None:
            selected_nodes = self._node_repository.list_by_project_id(self.project["id"])
            selected_node_ids = {
                str(uuid.UUID(bytes=node_data["id"])) for node_data in selected_nodes
            }
            self._load_project_data()
            nodes = selected_nodes + nodes

        unique_nodes: list[dict[str, object]] = []
        seen_ids: set[bytes] = set()
        for node_data in nodes:
            node_id = node_data["id"]
            if node_id in seen_ids:
                continue
            seen_ids.add(node_id)
            unique_nodes.append(node_data)

        for node_data in unique_nodes:
            var = tk.BooleanVar()
            tk.Checkbutton(
                self.nodes_frame,
                text=str(uuid.UUID(bytes=node_data["id"])),
                variable=var,
                background="#eef4fb"
            ).grid(row=len(self.node_vars)+1, column=0, sticky="w", padx=5)
            node_id = str(uuid.UUID(bytes=node_data["id"]))
            self.node_vars[node_id] = var
            self.node_vars[node_id].set(node_id in selected_node_ids)

        self._render_strategy_param_fields()
            
        
    def _select_model(self):
        try:
            ruta_inicial = filedialog.askopenfilename(
                parent=self,
                filetypes=[("Python files", "*.py")]
            )
            
            
            if ruta_inicial:
                modulo = cargar_modulo(ruta_inicial)

                clase = verificar_modulo(modulo)
                
                if not clase:
                    dialogs.InfoDialog(self, "Error", "El módulo seleccionado no contiene una clase válida que herede de BaseModel.", "error")
                    return
                
                self.model_class_name = clase.__name__
                nombre_modulo = os.path.basename(ruta_inicial)
                self.model_name.set(nombre_modulo)
                
                if self._create_project_use_case is None:
                    raise ValueError("No hay caso de uso disponible para preparar el modelo.")
                model_data = self._create_project_use_case.inspect_model(clase)
                self.input_features = model_data["input_features"]
                self.output_features = model_data["output_features"]
                suggested_task = model_data["suggested_task"]
                if suggested_task:
                    self.task_type_cb.set(suggested_task)
                self._sync_loss_options_for_task()

                self.ruta = ruta_inicial
        except Exception as e:
            dialogs.InfoDialog(self, "Error", f"Ocurrió un error al cargar el modelo: {str(e)}", "error")
            return

    def _sync_loss_options_for_task(self) -> None:
        task = self.task_type_cb.get()
        opts = (
            list(_LOSS_OPTIONS_REGRESSION)
            if task == "regression"
            else list(_LOSS_OPTIONS_CLASSIFICATION)
        )
        self.metrics_cb.configure(values=opts)
        cur = self.metrics_cb.get()
        if cur not in opts:
            self.metrics_cb.set(opts[0])

    def _on_task_type_selected(self, _event=None) -> None:
        self._sync_loss_options_for_task()

    def _clear_strategy_param_fields(self) -> None:
        for widget in self.strategy_params_frame.winfo_children():
            widget.destroy()
        self._strategy_param_widgets = {}

    def _render_strategy_param_fields(self) -> None:
        self._clear_strategy_param_fields()
        strategy_key = (self.aggregation_cb.get() or "").strip().lower()
        fields = self._STRATEGY_EXTRA_FIELDS.get(strategy_key, [])

        if not fields:
            self.strategy_params_label.grid_remove()
            self.strategy_params_frame.grid_remove()
            return

        self.strategy_params_label.grid()
        self.strategy_params_frame.grid()

        for idx, spec in enumerate(fields):
            label = ttk.Label(
                self.strategy_params_frame,
                text=spec["label"],
                style=FORM_LABEL,
                cursor="question_arrow",
            )
            label.grid(row=idx * 2, column=0, sticky="w")

            default_val = spec["default"]
            var = tk.DoubleVar(value=float(default_val))
            spinbox = tk.Spinbox(
                self.strategy_params_frame,
                from_=float(spec["from_"]),
                to=float(spec["to"]),
                increment=float(spec["increment"]),
                textvariable=var,
                width=int(spec["width"]),
            )
            spinbox.grid(row=idx * 2 + 1, column=0, sticky="ew", pady=(0, 5))
            ToolTip(label, text=spec["tooltip"])
            self._strategy_param_widgets[spec["key"]] = (spec["type"], spinbox)

    def _on_aggregation_strategy_selected(self, _event=None) -> None:
        self._render_strategy_param_fields()

    def _load_project_data(self):
        mp = (self.project.get("model_path") or "").strip()
        self.ruta = Path(mp).as_posix() if mp else ""
        self.input_features = json.loads(self.project["input_features"])
        self.output_features = json.loads(self.project["output_features"])

        self.name_entry.insert("1.0", self.project["name"])
        self.description_text.insert("1.0", self.project["description"])
        
        parameters = json.loads(self.project["parameters"])
        
        self.optimizer_cb.set(parameters.get("optimizer", "Adam"))
        self.learning_rate.delete(0, "end")
        self.learning_rate.insert(0, str(parameters.get("learning_rate", 0.01)))
        self.epochs.delete(0, "end")
        self.epochs.insert(0, str(parameters.get("epochs", 3)))
        self.validation_split.delete(0, "end")
        self.validation_split.insert(0, str(parameters.get("validation_split", 0.2)))
        self.batch_size.delete(0, "end")
        self.batch_size.insert(0, str(parameters.get("batch_size", 32)))
        self.fraction_fit.delete(0, "end")
        self.fraction_fit.insert(0, str(parameters.get("fraction_fit", 0.8)))
        self.fraction_evaluate.delete(0, "end")
        self.fraction_evaluate.insert(0, str(parameters.get("fraction_evaluate", 0.5)))
        
        self.aggregation_cb.set(self.project.get("aggregation_strategy", "fed_avg"))
        self._render_strategy_param_fields()
        for key, (param_type, widget) in self._strategy_param_widgets.items():
            default_value = 0.0 if param_type == "float" else 0
            value = parameters.get(key, default_value)
            widget.delete(0, "end")
            widget.insert(0, str(value))

        metrics_col = self.project.get("metrics", "categorical_crossentropy")
        tt = parameters.get("task_type")
        if tt not in ("regression", "classification"):
            tt = "regression" if metrics_col == "mean_squared_error" else "classification"
        self.task_type_cb.set(tt)
        self._sync_loss_options_for_task()
        self.metrics_cb.set(metrics_col)
        opts = list(self.metrics_cb.cget("values"))
        if self.metrics_cb.get() not in opts and opts:
            self.metrics_cb.set(opts[0])

        self.model_select_btn.pack_forget()
        self.model_name.set(os.path.basename(self.project["model_path"]))


    def _toggle_params(self):
        if self.params_frame.winfo_ismapped():
            self.params_frame.grid_remove()
            self.params_button.config(text="▶ Parámetros")
        else:
            self.params_frame.grid()
            self.params_button.config(text="▼ Parámetros")


    def get_data(self):
        if not self.name_entry.get("1.0", "end-1c").strip():
            raise ValueError("El nombre del proyecto no puede estar vacío.")
        if not self.ruta:
            raise ValueError("Debes seleccionar un modelo (.py) antes de continuar.")

        parameters = {
            "optimizer": self.optimizer_cb.get(),
            "learning_rate": float(self.learning_rate.get()),
            "epochs": int(self.epochs.get()),
            "validation_split": float(self.validation_split.get()),
            "batch_size": int(self.batch_size.get()),
            "fraction_fit": float(self.fraction_fit.get()),
            "fraction_evaluate": float(self.fraction_evaluate.get()),
        }
        for key, (param_type, widget) in self._strategy_param_widgets.items():
            if param_type == "int":
                parameters[key] = int(widget.get())
            else:
                parameters[key] = float(widget.get())

        return {
            "name": self.name_entry.get("1.0", "end-1c").strip(),
            "description": self.description_text.get("1.0", "end-1c").strip(),
            "task_type": self.task_type_cb.get(),
            "parameters": parameters,
            "aggregation_strategy": self.aggregation_cb.get(),
            "initial_nodes": [node_id for node_id, var in self.node_vars.items() if var.get()],
            "metrics": self.metrics_cb.get(),
            "model_path": self.ruta,
            "input_features": self.input_features,
            "output_features": self.output_features
        }

class NewProjectDialog(tk.Toplevel):
    def __init__(self, parent, user_id):
        super().__init__(parent)
        
        self.user_id = user_id
        self.parent = parent
        self._create_project_use_case = CreateProjectUseCase(
            SQLiteProjectRepository(),
            SQLiteNodeRepository(),
        )

        self.title("Nuevo Proyecto")
        self.geometry("700x720")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        self.form = NewProject(self, None, user_id, create_project_use_case=self._create_project_use_case)

        btns = ttk.Frame(self, padding=10)
        btns.grid(row=1, column=0, sticky="ew")

        btns.columnconfigure(0, weight=1)

        inner = ttk.Frame(btns)
        inner.pack(anchor="center")

        ttk.Button(inner, text="Crear", command=self._on_ok, style="Accent.TButton").pack(side="left")
        ttk.Button(inner, text="Cancelar", command=self.destroy, style="Accent.TButton").pack(side="left", padx=(10, 0))


    def _on_ok(self):
        try:
            data = self.form.get_data()
        except ValueError as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")
            return

        try:
            result = self._create_project_use_case.execute(self.user_id, data)
            if not result.ok:
                raise ValueError(result.error or "No se pudo crear el proyecto.")
        except (ValueError, DatabaseError) as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")
            return
        
        self.parent._initialize_tree()
        dialogs.InfoDialog(self, "Éxito", f"Proyecto '{data['name']}' creado correctamente.", "info")
        
        self.destroy()

class SeeProjectDialog(tk.Toplevel):
    def __init__(self, parent, project_id):
        super().__init__(parent)
        
        self.project_id = project_id
        self.parent = parent
        self._update_project_use_case = UpdateProjectUseCase(
            SQLiteProjectRepository(),
            SQLiteNodeRepository(),
        )
        self._project_repository = SQLiteProjectRepository()
        self._node_repository = SQLiteNodeRepository()
        
        self.geometry("700x720")
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()
        
        self.configure(bg=utils.BG_COLOR)

        self.columnconfigure(0, weight=1)

        self._build_modify_ui(project_id)
        
        
    
    def _build_modify_ui(self, project_id):
        for widget in self.winfo_children():
            widget.destroy()
        for r in range(20):
            self.rowconfigure(r, weight=0)
        self.project = self._project_repository.get_by_id(project_id)

        self.title(f"Modificar Proyecto: {self.project['name']}")

        raw_pending = self.project.get("unconfirmed_results") or "[]"
        self.unconfirmed = json.loads(raw_pending) if isinstance(raw_pending, str) else raw_pending

        grid_row = 0
        if self.unconfirmed:
            ttk.Button(self, text="Confirmar Resultados Pendientes", command=self._confirm_results, style="Accent.TButton", width=self.winfo_width() - 20).grid(row=grid_row, column=0, sticky="ew", padx=10, pady=5)
            grid_row += 1

        ttk.Button(self, text="Añadir dataset", command=self._add_dataset, style="Accent.TButton", width=self.winfo_width() - 20).grid(row=grid_row, column=0, sticky="ew", padx=10, pady=5)
        grid_row += 1

        self.form = NewProject(self, self.project, grid_row=grid_row)
        grid_row += 1

        btns = ttk.Frame(self, padding=10, style="TFrame")
        btns.grid(row=grid_row, column=0, sticky="ew")

        btns.columnconfigure(0, weight=1)

        inner = ttk.Frame(btns, style="TFrame")
        inner.pack(anchor="center")

        ttk.Button(inner, text="Guardar Cambios", command=self._on_mod, style="Accent.TButton").pack(side="left")
        ttk.Button(inner, text="Cancelar", command=self.destroy, style="Accent.TButton").pack(side="left", padx=(10, 0))
    
    def _add_dataset(self):
        assigned_nodes = self._node_repository.list_by_project_id(self.project["id"])
        nodes = [str(uuid.UUID(bytes=node["id"])) for node in assigned_nodes]
        if not nodes:
            dialogs.InfoDialog(self, "Información", "El proyecto no tiene nodos asignados.", "warning")
            return
        AddDatasetDialog(self, nodes, self.project)
        
    def _on_unconfirmed_persisted(self) -> None:
        self.project["unconfirmed_results"] = json.dumps(self.unconfirmed, ensure_ascii=False)
        self.parent._initialize_tree()

    def _confirm_results(self):
        for widget in self.winfo_children():
            widget.destroy()
        confirm = ConfirmResultsFrame(
            self,
            self.unconfirmed,
            {"in_features": self.project["input_features"], "out_features": self.project["output_features"]},
            self.project["training_round"],
            project_id=self.project_id,
            on_unconfirmed_persisted=self._on_unconfirmed_persisted,
        )
        confirm.pack(fill="both", expand=True)
        
        buttons = ttk.Frame(self, padding=10, style="TFrame")
        buttons.pack(fill="x", side="bottom")
        
        ttk.Button(buttons, text="Volver", command=lambda: self._build_modify_ui(self.project_id), style="Accent.TButton").pack(expand=True)
        
        
        
        
    def _on_mod(self):
        try:
            data = self.form.get_data()
        except ValueError as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")
            return

        try:
            result = self._update_project_use_case.execute(
                self.project_id,
                self.project,
                data,
                on_node_removed=self.parent._eliminate_dataset,
            )
            if not result.ok:
                raise ValueError(result.error or "No se pudo actualizar el proyecto.")
        except (ValueError, DatabaseError) as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")
            return
            
        self.parent._initialize_tree()
        dialogs.InfoDialog(self, "Éxito", f"Proyecto '{data['name']}' modificado correctamente.", "info")
            
        self.destroy()