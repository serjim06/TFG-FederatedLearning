import tkinter as tk
from tkinter import ttk

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from src.application.services.project_metrics_calculations import round_indices_for_metrics
from src.utils import utils
from src.gui.dialogs import InfoDialog


class ProjectMetricsDialog(tk.Toplevel):

    def __init__(self, parent, training_data, project_data, title="Métricas del Proyecto"):
        super().__init__(parent)
        self.title(title)
        self.geometry("875x700")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(bg=utils.BG_COLOR)
        utils.get_style()

        if len(training_data) > 0:
            self.training_data = training_data
        else:
            InfoDialog(parent, "Error", "No hay datos de entrenamiento", kind="error")
            self.destroy()
            return

        self.project_data = project_data
        self.create_widgets()


    def create_widgets(self):

        container = tk.Frame(self, bg=utils.BG_COLOR)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, bg=utils.BG_COLOR, highlightthickness=0)
        scroll_y = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview, style="White.Vertical.TScrollbar")
        scroll_y.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True, padx=15, pady=15)
        self.canvas.configure(yscrollcommand=scroll_y.set)

        self.info_frame = tk.Frame(self.canvas, bg=utils.BG_COLOR)
        self.info_frame.bind("<Configure>", self._on_configure)
        self.canvas.create_window((0,0), window=self.info_frame, anchor="nw")
    
        self.params_frame = tk.Frame(self.info_frame, bg=utils.BG_COLOR)
        self.params_frame.pack(fill="both", expand=True)

        ttk.Separator(self.info_frame, orient="horizontal").pack(fill="x", pady=10)

        self.metrics_frame = tk.Frame(self.info_frame, bg=utils.BG_COLOR)
        self.metrics_frame.pack(fill="both", expand=True)
        
        self._build_params()
        self._build_metrics()
        
    def _on_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _build_params(self):
        for widget in self.params_frame.winfo_children():
            widget.destroy()

        params = self.training_data[0]["config"]
        project_type = self.project_data.get("type", "")

        card_bg = "#ffffff"
        row_bg_a = "#f7f9fc"
        row_bg_b = "#ffffff"
        border_color = "#d7e5f7"

        card = tk.Frame(
            self.params_frame,
            bg=card_bg,
            highlightbackground=border_color,
            highlightthickness=1,
            padx=14,
            pady=12,
        )
        card.pack(fill="both", expand=True, padx=15, pady=(10, 15))

        header = tk.Frame(card, bg=card_bg)
        header.pack(fill="x")

        tk.Label(
            header,
            text="Parámetros de entrenamiento",
            bg=card_bg,
            fg="#1d2d44",
            font=(utils.FONT, 13, "bold"),
        ).pack(side="left")

        badge_text = "Clasificación" if project_type == "classification" else "Regresión"
        tk.Label(
            header,
            text=badge_text,
            bg=card_bg,
            fg="#3498DB",
            font=(utils.FONT, 11, "bold"),
            padx=10,
        ).pack(side="right")

        ttk.Separator(card, orient="horizontal").pack(fill="x", pady=(10, 12))

        grid = tk.Frame(card, bg=card_bg)
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(0, weight=0)
        grid.columnconfigure(1, weight=1)

        for i, (key, value) in enumerate(params.items()):
            row_bg = row_bg_a if (i % 2 == 0) else row_bg_b

            tk.Label(
                grid,
                text=str(key),
                bg=row_bg,
                fg="#2c3e50",
                font=(utils.FONT, 10, "bold"),
                anchor="w",
            ).grid(row=i, column=0, sticky="w", padx=(6, 10), pady=4)

            tk.Label(
                grid,
                text=str(value),
                bg=row_bg,
                fg="#1d2d44",
                font=(utils.FONT, 10),
                anchor="w",
                justify="left",
                wraplength=520,
            ).grid(row=i, column=1, sticky="w", padx=(0, 6), pady=4)
        
    def _build_metrics(self):
        if self.project_data["type"] == "classification":
            self._build_classification_metrics()
        else:
            self._build_regression_metrics()
    

    def _build_classification_metrics(self):
        grid_frame = tk.Frame(self.metrics_frame, bg=utils.BG_COLOR)
        grid_frame.pack(fill="both", expand=True, pady=5)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)

        frame1 = tk.Frame(grid_frame, bg=utils.BG_COLOR)
        frame1.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self._metrics_per_round_graphic(self.project_data["metrics"], frame1)

        frame2 = tk.Frame(grid_frame, bg=utils.BG_COLOR)
        frame2.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self._build_data_efficiency_graphic(frame2)

        frame3 = tk.Frame(grid_frame, bg=utils.BG_COLOR)
        frame3.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self._time_per_round_graphic(frame3)

        frame4 = tk.Frame(grid_frame, bg=utils.BG_COLOR)
        frame4.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        self._build_changes_histogram(self.project_data.get("datasets_changes", {"composed_changes":{}}), frame4)

    def _build_regression_metrics(self):
        grid_frame = tk.Frame(self.metrics_frame, bg=utils.BG_COLOR)
        grid_frame.pack(fill="both", expand=True, pady=5)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)

        frame1 = tk.Frame(grid_frame, bg=utils.BG_COLOR)
        frame1.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self._metrics_per_round_graphic(self.project_data["metrics"], frame1)

        frame2 = tk.Frame(grid_frame, bg=utils.BG_COLOR)
        frame2.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self._build_data_efficiency_graphic(frame2)

        frame3 = tk.Frame(grid_frame, bg=utils.BG_COLOR)
        frame3.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self._time_per_round_graphic(frame3)

        frame4 = tk.Frame(grid_frame, bg=utils.BG_COLOR)
        frame4.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        self._build_changes_histogram(self.project_data.get("datasets_changes", {"composed_changes":{}}), frame4)

        frame_scatter = tk.Frame(grid_frame, bg=utils.BG_COLOR)
        frame_scatter.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self._build_scatter_plot(frame_scatter)

    def _build_changes_histogram(self, datasets_changes, frame):
        color_added = "#2ECC71"
        color_normal = "#3498DB"

        for widget in frame.winfo_children():
            widget.destroy()

        composed_changes = datasets_changes.get("composed_changes", {})
        if not composed_changes:
            tk.Label(frame, text="No hay cambios de datasets para graficar", bg=utils.BG_COLOR).pack()
            return

        rounds = sorted(composed_changes.keys())
        x = np.array(rounds, dtype=float)
        freq = np.array([composed_changes[rnd]["length"] for rnd in rounds], dtype=float)
        added = np.array([len(composed_changes[rnd]["added"]) for rnd in rounds], dtype=float)

        added_capped = np.minimum(added, freq)
        normal_part = np.maximum(0, freq - added_capped)
        
        fig, ax = plt.subplots(figsize=(4,3), dpi=100)

        if len(x) > 1:
            min_step = np.min(np.diff(x))
            bar_width = max(0.4, min(0.8, float(min_step) * 0.7))
        else:
            bar_width = 0.6

        ax.bar(x, normal_part, width=bar_width, color=color_normal, edgecolor='black', alpha=0.8, label="Datos sin modificar")
        ax.bar(x, added_capped, width=bar_width, bottom=normal_part, color=color_added, edgecolor='black', alpha=0.8, label="Datos añadidos")

        if len(added) > 0:
            ax.step(x, added, where="mid", color="#2C3E50", linestyle="--", linewidth=2, label="Añadidos por ronda")

        ax.set_xticks(x)
        ax.set_xlabel("Rondas")
        ax.set_ylabel("Datos en datasets")
        ax.set_title("Cambios en los datasets")
        ax.legend()

        ax.grid(axis='x', linestyle=':', alpha=0.3)
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        plt.close(fig)
        

    def _metrics_per_round_graphic(self, metrics, frame):
        is_classification = self.project_data.get("type") == "classification"
        mtr_key = "f1" if is_classification else "r2"

        rondas = round_indices_for_metrics(metrics)
        lista_loss = [m.get("loss", 0) for m in metrics]

        if is_classification:
            mtr_label = "F1 / Accuracy"
            lista_metricas = []
            for m in metrics:
                f1v = m.get("f1")
                if f1v is not None and not (isinstance(f1v, float) and np.isnan(f1v)):
                    lista_metricas.append(float(f1v))
                else:
                    lista_metricas.append(float(m.get("accuracy", 0.0)))
        else:
            mtr_label = "$R^2$ Score"
            lista_metricas = [float(m.get(mtr_key, float("nan"))) for m in metrics]

        fig, ax1 = plt.subplots(figsize=(4,3), dpi=100)
        
        color_loss = '#E74C3C'
        ax1.set_xlabel('Ronda Federada')
        ax1.set_ylabel('Loss (Pérdida)', color=color_loss, fontsize=12)
        ax1.plot(rondas, lista_loss, color=color_loss, marker='o', label='Loss')
        ax1.tick_params(axis='y', labelcolor=color_loss)
        ax1.grid(True, linestyle=':', alpha=0.5)

        ax2 = ax1.twinx()
        color_metric = '#3498DB'
        ax2.set_ylabel(mtr_label, color=color_metric, fontsize=12)
        ax2.plot(rondas, lista_metricas, color=color_metric, marker='x', label=mtr_label)
        ax2.tick_params(axis='y', labelcolor=color_metric)

        if is_classification:
            ax2.set_ylim(0, 1.05)
        else:
            finite = [x for x in lista_metricas if not np.isnan(x)]
            min_val = min(finite) if finite else 0.0
            ax2.set_ylim(min(min_val - 0.1, -0.1), 1.05)

        plt.title(f'Evolución del entrenamiento', pad=15)

        lines, labels = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax2.legend(lines + lines2, labels + labels2, loc='lower center', ncol=2)

        fig.tight_layout()

        for widget in frame.winfo_children():
            widget.destroy()

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

        plt.close(fig)

    def _build_scatter_plot(self, frame):

        for widget in frame.winfo_children():
            widget.destroy()

        y_true = self.project_data["y_true"]
        y_pred = self.project_data["y_pred"]
        if not y_true or not y_pred:
            tk.Label(
                frame,
                text="No hay y_true/y_pred persistidos para mostrar dispersión.",
                bg=utils.BG_COLOR,
            ).pack()
            return

        fig, ax = plt.subplots(figsize=(4,3), dpi=100)
        ax.scatter(y_true, y_pred)

        lims = [
            min(min(y_true), min(y_pred)),
            max(max(y_true), max(y_pred)),
        ]
        ax.plot(lims, lims, color='#FF6B6B', linestyle='--', linewidth=2, label='Ideal ($y=x$)')
    
        ax.set_aspect('equal')
        ax.set_xlim(lims)
        ax.set_ylim(lims)
    
        ax.set_xlabel('Valores Reales')
        ax.set_ylabel('Predicciones del Modelo')
        ax.set_title('Gráfico de Dispersión: Real vs. Predicho')
        ax.legend()
        ax.grid(True, linestyle=':', alpha=0.6)
 
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

        plt.close(fig)

    def _build_data_efficiency_graphic(self, frame):
        metrics = self.project_data.get("metrics", [])
        loss = [m.get("loss", 0) for m in metrics]
        participation = [m.get("participation", 0) for m in metrics]
        rounds_metrics = round_indices_for_metrics(metrics)
        
        datasets_changes = self.project_data.get("datasets_changes", {})
        composed_changes = datasets_changes.get("composed_changes", {})
        
        if not composed_changes:
            tk.Label(frame, text="No hay cambios de datasets para graficar", bg=utils.BG_COLOR).pack()
            return

        rounds_data = sorted(composed_changes.keys())
        freq = np.array([composed_changes[rnd]['length'] for rnd in rounds_data], dtype=float)
        
        fig, ax1 = plt.subplots(figsize=(4,3), dpi=100)
        color_data = '#D1E8FF'
        color_data_line = '#1F77B4'
        color_part = '#7F8C8D'
        ax1.set_xlabel('Ronda Federada')
        ax1.set_ylabel('Datos en datasets', color=color_data_line)

        ax1.fill_between(rounds_data, freq, color=color_data, alpha=0.35, label='Volumen Datos', zorder=1)
        ax1.plot(rounds_data, freq, color=color_data_line, linewidth=1.8, marker='o', zorder=2)
        ax1.tick_params(axis='y', labelcolor=color_data_line)
        ax1.grid(True, linestyle=':', alpha=0.3)

        ax2 = ax1.twinx()
        color_loss = '#E67E22'
        ax2.set_ylabel('Loss', color=color_loss)
        ax2.plot(rounds_metrics, loss, color=color_loss, marker='o', label='Loss', linewidth=2.5, zorder=10)
        ax2.tick_params(axis='y', labelcolor=color_loss)

        ax3 = ax1.twinx()
        ax3.spines['right'].set_position(('outward', 42))
        ax3.set_ylim(0, 1)
        ax3.set_ylabel('Participación', color=color_part)
        ax3.tick_params(axis='y', labelcolor=color_part)
        ax3.bar(rounds_metrics, participation, color=color_part, alpha=0.22, width=0.45, label='Participación', zorder=3)

        all_rounds = sorted(set(rounds_data) | set(rounds_metrics))
        if all_rounds:
            ax1.set_xticks(all_rounds)
            ax1.set_xlim(min(all_rounds) - 0.5, max(all_rounds) + 0.5)

        plt.title(f'Impacto del volumen de datos y participación en la pérdida', pad=15)

        legend_elements = [
            Patch(facecolor=color_data, alpha=0.4, label='Volumen Datos'),
            Line2D([0], [0], color=color_loss, marker='o', label='Loss'),
            Patch(facecolor=color_part, alpha=0.25, label='Participación (%)')
        ]
        ax1.legend(handles=legend_elements, loc='lower center', ncol=1, fontsize='small')
        fig.tight_layout()

        for widget in frame.winfo_children():
            widget.destroy()

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        plt.close(fig)

    def _time_per_round_graphic(self, frame):

        for widget in frame.winfo_children():
            widget.destroy()

        time_per_round = self.project_data["time_per_round"]

        fig, ax = plt.subplots(figsize=(4,3), dpi=100)
        ax.plot(range(1, len(time_per_round)+1), time_per_round, color='#3498DB', marker='o', linewidth=2)
        ax.set_xlabel("Ronda Federada")
        ax.set_ylabel("Tiempo por ronda (segundos)")
        ax.set_title("Tiempo por ronda")
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

        plt.close(fig)
            