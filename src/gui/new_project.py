import json
from sqlite3 import DatabaseError
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import uuid

from PIL import Image, ImageTk
from TkToolTip import ToolTip

from src.utils.icons import image_finder
from src.db import dbcon
from src.projects.projects import Project

class ScrollableNodesFrame(ttk.Frame):
    def __init__(self, parent, height=150):
        super().__init__(parent)

        style = ttk.Style()
        bg = style.lookup("TFrame", "background")

        self.canvas = tk.Canvas(
            self,
            height=height,
            width=300,
            highlightthickness=0,
            bg=bg
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

        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


FORM_LABEL = "Form.TLabel"

class NewProject(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.grid(sticky="nsew")
        self.configure(style="TFrame")

        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        self.columnconfigure(0, weight=1)

        self._build_ui()

    def _build_ui(self):
        row = 0
        
        self.scrollable_frame = ScrollableNodesFrame(self, height=600)
        self.scrollable_frame.grid(row=0, column=0, sticky="nsew")
        self.scrollable_frame.columnconfigure(0, weight=1)

        # ---------- Nombre ----------
        ttk.Label(self.scrollable_frame.inner, text="Nombre:", background="#eef4fb").grid(row=row, column=0, sticky="w")
        row += 1

        self.name_entry = tk.Text(self.scrollable_frame.inner, height=1, border=0.5, relief="solid")
        self.name_entry.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1

        # ---------- Descripción ----------
        ttk.Label(self.scrollable_frame.inner, text="Descripción:", background="#eef4fb").grid(row=row, column=0, sticky="w")
        row += 1

        self.description_text = tk.Text(self.scrollable_frame.inner, height=4, border=0.5, relief="solid")
        self.description_text.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1

       # ---------- Parámetros ----------
       
        self.params_button = tk.Label(
            self.scrollable_frame.inner, text="▶ Parámetros",
            bg="#eef4fb",
            fg="#000000", cursor="hand2"
        )
        
        #self.params_button.bind("<Button-1>", lambda e: self._toggle_params())
        self.params_button.grid(row=row, column=0, sticky="w", pady=(5, 5))
        row += 1

        # Fila RESERVADA para params_frame
        self.params_frame = ttk.Frame(self.scrollable_frame.inner)
        self.params_frame.columnconfigure(0, weight=1)
        self.params_frame.grid(row=row, column=0, sticky="ew", padx=15)
        #self.params_frame.grid_remove()   # empieza oculto
        row += 1

        # --- Optimizer ---

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

        # --- Aggregation Strategy ---

        self.agg_lb = ttk.Label(self.params_frame, text="Aggregation strategy:", style=FORM_LABEL, cursor="question_arrow")
        self.agg_lb.grid(
            row=2, column=0, sticky="w"
        )

        self.aggregation_cb = ttk.Combobox(self.params_frame, values=["fed_avg", "fed_sum", "fed_weighted"], state="readonly")
        self.aggregation_cb.grid(row=3, column=0, sticky="ew", pady=(0, 5))
        
        self.aggregation_cb.set("fed_avg")
        
        ToolTip(self.agg_lb, text="Selecciona la estrategia de agregación que se utilizará para combinar los modelos entrenados por los nodos.")
        
        # --- Epochs ---
        
        self.epochs_label = ttk.Label(self.params_frame, text="Epochs:", style=FORM_LABEL, cursor="question_arrow")
        self.epochs_label.grid(
            row=4, column=0, sticky="w"
        )
        
        epochs_var = tk.IntVar(value=3)
        self.epochs = tk.Spinbox(
            self.params_frame,
            from_=1,
            to=100,
            textvariable=epochs_var,
            width=5,
        )
        self.epochs.grid(row=5, column=0, sticky="ew", pady=(0, 5))

        ToolTip(self.epochs_label, text="Número de veces que el modelo verá todo el conjunto de datos durante el entrenamiento.")

        # --- Validation Split ---
        
        self.val_split_label = ttk.Label(self.params_frame, text="Validation split:", style=FORM_LABEL, cursor="question_arrow")
        self.val_split_label.grid(
            row=6, column=0, sticky="w"
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
    
        self.validation_split.grid(row=7, column=0, sticky="ew", pady=(0, 5))
        
        ToolTip(self.val_split_label, text="Proporción del conjunto de datos que se utilizará para la validación durante el entrenamiento.")
        
        # ---- Batch Size ----
        
        self.batch_frame = ttk.Frame(self.params_frame)
        self.batch_frame.grid(row=8, column=0, sticky="ew")
        
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

        self.batch_size.grid(row=9, column=0, sticky="ew", pady=(0, 5))
        
        ToolTip(self.batch_size_label, text="Número de muestras que se procesan antes de actualizar el modelo durante el entrenamiento.\nUn tamaño de batch más grande puede acelerar el entrenamiento, pero también requiere más memoria.")
        ToolTip(self.warning_label, text="Advertencia: Un tamaño de batch muy grande puede causar problemas de memoria en nodos con recursos limitados.")        
        # ---- Fraction Fit ----
        
        self.fraction_fit_label = ttk.Label(self.params_frame, text="Fraction fit:", style=FORM_LABEL, cursor="question_arrow")
        self.fraction_fit_label.grid(
            row=10, column=0, sticky="w")
        
        fit_var = tk.DoubleVar(value=0.8)
        self.fraction_fit = tk.Spinbox(
            self.params_frame,
            from_=0.1,
            to=1.0,
            increment=0.05,
            textvariable=fit_var,
            width=5,
        )
        self.fraction_fit.grid(row=11, column=0, sticky="ew", pady=(0, 5))
        
        ToolTip(self.fraction_fit_label, text="Proporción de nodos participantes que se utilizarán para el entrenamiento en cada ronda.")
        
        # ---- Fraction Evaluate ----
        
        self.fraction_evaluate_label = ttk.Label(self.params_frame, text="Fraction evaluate:", style=FORM_LABEL, cursor="question_arrow")
        self.fraction_evaluate_label.grid(
            row=12, column=0, sticky="w")
        
        evaluate_var = tk.DoubleVar(value=0.5)
        self.fraction_evaluate = tk.Spinbox(
            self.params_frame,
            from_=0.1,
            to=1.0,
            increment=0.05,
            textvariable=evaluate_var,
            width=5,
        )
        self.fraction_evaluate.grid(row=13, column=0, sticky="ew", pady=(0, 5))
        
        ToolTip(self.fraction_evaluate_label, text="Proporción de nodos participantes que se utilizarán para la evaluación en cada ronda.")
        
        # ---- Learning Rate ----

        self.learning_rate_label = ttk.Label(self.params_frame, text="Learning rate:", style=FORM_LABEL, cursor="question_arrow")
        self.learning_rate_label.grid(
            row=14, column=0, sticky="w")
        
        lr_var = tk.DoubleVar(value=0.01)
        self.learning_rate = tk.Spinbox(
            self.params_frame,
            from_=0.0001,
            to=1.0,
            increment=0.0001,
            textvariable=lr_var,
            width=7,
        )
        self.learning_rate.grid(row=15, column=0, sticky="ew", pady=(0, 5))
        
        ToolTip(self.learning_rate_label, text="Tasa de aprendizaje que determina el tamaño de los pasos que da el optimizador al actualizar los pesos del modelo durante el entrenamiento.")
        
        # ---------- Métricas ----------
        self.metrics_label = ttk.Label(self.scrollable_frame.inner, text="Métricas:", background="#eef4fb", cursor="question_arrow")
        self.metrics_label.grid(
            row=row, column=0, sticky="w", pady=(10, 0)
        )
        row += 1

        self.metrics_cb = ttk.Combobox(
            self.scrollable_frame.inner ,
            values=["categorical_crossentropy", "sparse_categorical_crossentropy", "binary_crossentropy", "mean_squared_error"],
            state="readonly"
        )
        self.metrics_cb.set("categorical_crossentropy")
        self.metrics_cb.grid(row=row, column=0, sticky="ew")
        row += 1
        
        ToolTip(self.metrics_label, text="Métrica que se utilizará para evaluar el rendimiento del modelo entrenado.")

       # ---------- Nodos ----------
        ttk.Label(self.scrollable_frame.inner, text="Nodos:", background="#eef4fb").grid(
            row=row, column=0, sticky="w", pady=(10, 0)
        )
        row += 1

        self.node_vars = {}

        #self.nodes_frame = ScrollableNodesFrame(self.scrollable_frame.inner, height=140)
        self.nodes_frame = tk.Frame(self.scrollable_frame.inner, background="#eef4fb", borderwidth=1, relief="solid")
        self.nodes_frame.grid(row=row, column=0, sticky="ews", pady=(5, 0))

        try:
            nodes = dbcon.command("select", "nodes", {"id": "*", "valid": 0})
        except (ValueError, DatabaseError) as e:
            messagebox.showerror("Error", str(e))
            
        for node_data in nodes:
            var = tk.BooleanVar()
            tk.Checkbutton(
                self.nodes_frame,
                text=str(uuid.UUID(bytes=node_data["id"])),
                variable=var,
                background="#eef4fb"
            ).grid(row=len(self.node_vars)+1, column=0, sticky="w", padx=5)
            self.node_vars[str(uuid.UUID(bytes=node_data["id"]))] = var


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
        
        return {
            "name": self.name_entry.get("1.0", "end-1c").strip(),
            "description": self.description_text.get("1.0", "end-1c").strip(),
            "parameters": {
                "optimizer": self.optimizer_cb.get(),
                "learning_rate": float(self.learning_rate.get()),
                "epochs": int(self.epochs.get()),
                "validation_split": float(self.validation_split.get()),
                "batch_size": int(self.batch_size.get()),
                "fraction_fit": float(self.fraction_fit.get()),
                "fraction_evaluate": float(self.fraction_evaluate.get())
            },
            "aggregation_strategy": self.aggregation_cb.get(),
            "initial_nodes": [node_id for node_id, var in self.node_vars.items() if var.get()],
            "metrics": self.metrics_cb.get(),
        }

class NewProjectDialog(tk.Toplevel):
    def __init__(self, parent, user_id):
        super().__init__(parent)
        
        self.user_id = user_id
        self.parent = parent

        self.title("Nuevo Proyecto")
        self.geometry("700x720")
        self.resizable(True, True)

        self.transient(parent)
        self.grab_set()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.form = NewProject(self)

        # ---------- Botones ----------
        btns = ttk.Frame(self, padding=10)
        btns.grid(row=1, column=0, sticky="ew")

        btns.columnconfigure(0, weight=1)

        inner = ttk.Frame(btns)
        inner.pack(anchor="center")

        ttk.Button(inner, text="Crear", command=self._on_ok, style="Accent.TButton").pack(side="left")
        ttk.Button(inner, text="Cancelar", command=self.destroy, style="Accent.TButton").pack(side="left", padx=(10, 0))


    def _on_ok(self):
        # aquí luego implementas get_data()
        try:
            data = self.form.get_data()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        
        params_str = json.dumps(data["parameters"])
        nodes_str = json.dumps(data["initial_nodes"])
        
        try:
            dbcon.command("insert", "projects", {
                "uid": self.user_id,
                "name": data["name"],
                "description": data["description"],
                "parameters": params_str,
                "aggregation_strategy": data["aggregation_strategy"],
                "metrics": data["metrics"],
                "nodes": nodes_str
            })
            project = dbcon.command("select", "projects", {"name": data["name"], "uid": self.user_id})
            
            nodes = json.loads(project[0]["nodes"])
            nodes_bytes = [uuid.UUID(node_id).bytes for node_id in nodes]
            
            project = Project(project[0]["id"], project[0]["uid"], project[0]["name"], project[0]["description"],
                              json.loads(project[0]["parameters"]), project[0]["aggregation_strategy"],
                              initial_nodes=nodes_bytes, metrics=project[0]["metrics"])
        except (ValueError, DatabaseError) as e:
            messagebox.showerror("Error", str(e))
            return
        
        self.parent._initialize_tree()
        messagebox.showinfo("Éxito", f"Proyecto '{data['name']}' creado correctamente.")
        
        self.destroy()
