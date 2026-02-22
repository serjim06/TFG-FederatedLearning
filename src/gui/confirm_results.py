import json
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from tkinter import messagebox
import re
import shutil

from src.utils import utils

class CorrectResultDialog(tk.Toplevel):
    def __init__(self, parent, row, out_features):
        super().__init__(parent)

        self.title("Corregir resultado")
        self.geometry("400x300")
        self.configure(bg=utils.BG_COLOR)
        self.resizable(False, False)

        self.parent = parent
        self.row = row
        self.out_features = dict.fromkeys(out_features, "")
        
        tk.Label(
            self,
            text="Introduce los datos correctos para el nodo",
            background=utils.BG_COLOR
        ).pack(pady=10)
        
        ttk.Button(
            self,
            text="Guardar",
            style=utils.SEC_TBUTTON_STYLE,
            command=self._save
        ).pack(side="bottom",pady=10)

        container = tk.Frame(self, bg=utils.BG_COLOR)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, bg=utils.BG_COLOR, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True, padx=15, pady=15)

        self.scroll_y = ttk.Scrollbar(
            container,
            orient="vertical",
            command=self.canvas.yview,
            style="White.Vertical.TScrollbar"
        )

        self.canvas.configure(yscrollcommand=self.scroll_y.set)

        inner_frame = tk.Frame(self.canvas, bg=utils.BG_COLOR)
        self.canvas.create_window((0, 0), window=inner_frame, anchor="nw")

        self.entries = {}

        row_index = 0
        for key in out_features:
            tk.Label(inner_frame, text=key, background=utils.BG_COLOR).grid(row=row_index, column=0, padx=5, pady=5)

            entry = ttk.Entry(inner_frame)
            entry.grid(row=row_index, column=1, padx=5, pady=5)

            self.entries[key] = entry
            row_index += 1

        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        content_height = self.canvas.bbox("all")[3]
        canvas_height = self.canvas.winfo_height()

        if content_height > canvas_height:
            self.scroll_y.pack(side="right", fill="y")


    def _save(self):
        for key, entry in self.entries.items():
            self.out_features[key] = entry.get()
        
        
        self.parent.correct_result(self.row, self.out_features)
        self.destroy()
        

class ConfirmResultsFrame (tk.Frame):
    def __init__(self, parent, pending, labels, cur_round):
        super().__init__(parent)
        
        self.parent = parent
        self.pending = pending
        self.labels = labels
        self.cur_round = cur_round
        
        self.configure(bg=utils.BG_COLOR)
        utils.get_style()
        
        container = tk.Frame(self, bg=utils.BG_COLOR)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, bg=utils.BG_COLOR, highlightthickness=0)
        scroll_y = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview, style="White.Vertical.TScrollbar")
        scroll_x = ttk.Scrollbar(container, orient="horizontal", command=self.canvas.xview, style="White.Horizontal.TScrollbar")
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True, padx=15, pady=15)


        self.canvas.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.table_frame = tk.Frame(self.canvas, bg=utils.BG_COLOR)
        self.table_frame.bind("<Configure>", self._on_configure)
        
        self.canvas.create_window((0,0), window=self.table_frame, anchor="nw")
    

        
        self._build_ui()
        
    def _build_ui(self):
        col = 0
        for in_f in json.loads(self.labels["in_features"]):
            tk.Label(self.table_frame, text=in_f, background=utils.BG_COLOR).grid(row=0, column=col, padx=5, pady=5)
            col+=1
            
        for out_f in json.loads(self.labels["out_features"]):
            tk.Label(self.table_frame, text=out_f, background=utils.BG_COLOR).grid(row=0, column=col, padx=5, pady=5)
            col+=1
            
        tk.Label(self.table_frame, text="Acciones", background=utils.BG_COLOR).grid(row=0, column=col, padx=5, pady=5)
        
        col = 0
        row = 1
        
        for pend in self.pending:
            for _, value in pend["data"].items():
                tk.Label(self.table_frame, text=value, background=utils.BG_COLOR).grid(row=row, column=col, padx=5, pady=5)
                col+=1
            self._inner_buttons(row, col)
            col=0
            row+=1
            
                
    def _inner_buttons(self, row, col):
        buttons_frame = tk.Frame(self.table_frame, bg=utils.BG_COLOR)
        buttons_frame.grid(row=row, column=col, padx=5, pady=5, sticky="e")
        ttk.Button(buttons_frame, text="Correcto", style=utils.SEC_TBUTTON_STYLE, command=lambda: self._confirm_result(row)).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(buttons_frame, text="Incorrecto", style=utils.SEC_TBUTTON_STYLE, command=lambda: self._wrong_result(row)).grid(row=0, column=1, padx=5, pady=5)


    def _confirm_result(self, row):
        ### Recupera el último dataset. Si el correspondiente a la ronda actual no existe, lo crea.
        path = self._get_last_dataset(row)
                
        with open(path, "a") as f:
            for _, feature in self.pending[row-1]["data"].items():
                f.write(feature)    
                f.write(",")
            f.write("\n")
        
        messagebox.showinfo("Confirmación", f"Resultado confirmado para el nodo {self.pending[row-1]['node']}", parent=self)
        del self.pending[row-1]
        
        for widget in self.table_frame.winfo_children():
            widget.destroy()
            
        self._build_ui()
        
    
    def _wrong_result(self, row):
        correct_dialog = CorrectResultDialog(self, row, json.loads(self.labels["out_features"]))
        correct_dialog.transient(self)
        correct_dialog.wait_visibility()
        correct_dialog.grab_set()
        correct_dialog.focus_set()
        
    def _get_last_dataset(self, row):
        path = Path(__file__).parent.parent.parent / "database" / "datasets" / self.pending[row-1]["node"]
        pattern = re.compile(r"dataset_(\d+)\.csv")
        
        found_files = []
        
        for f in path.glob('dataset_*.csv'):
            coincidence = pattern.search(f.name)
            if coincidence:
                round_number = int(coincidence.group(1))
                found_files.append((round_number, f))
                
        if found_files:
            last_dataset, file_path = max(found_files, key=lambda x: x[0])
            if last_dataset != self.cur_round:
                dest = Path(__file__).parent.parent.parent / "database" / "datasets" / self.pending[row-1]["node"] / f"dataset_{self.cur_round}.csv"
                shutil.copy2(file_path, dest)
                file_path = dest
        else:
            file_path = self._create_new_dataset(row)        
        
        return file_path
        
    def _create_new_dataset(self, row):
        path = Path(__file__).parent.parent.parent / "database" / "datasets" / self.pending[row-1]["node"] / f"dataset_{self.cur_round}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w") as f:
            for labels in json.loads(self.labels["in_features"]):
                f.write(labels)
                f.write(",")
            for labels in json.loads(self.labels["out_features"]):
                f.write(labels)
                f.write(",")
            f.write("\n")
            
        return path
        
    def correct_result(self, row, out_features):
        path = self._get_last_dataset(row)
        
        with open(path, "a") as f:
            for key, feature in self.pending[row-1]["data"].items():
                if key in json.loads(self.labels["in_features"]):
                    f.write(feature)
                    f.write(",")
            for key, value in out_features.items():
                f.write(value)
                f.write(",")
            f.write("\n")
        
        messagebox.showinfo("Confirmación", f"Resultado corregido para el nodo {self.pending[row-1]['node']}", parent=self)
        del self.pending[row-1]
        
        for widget in self.table_frame.winfo_children():
            widget.destroy()
            
        self._build_ui()
    
    def _on_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

