import json
import tkinter as tk
from tkinter import ttk

from src.utils import utils

class ConfirmResultsFrame (tk.Frame):
    def __init__(self, parent, pending, labels):
        super().__init__(parent)
        
        self.parent = parent
        self.pending = pending
        self.labels = labels
        
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
            for _, value in pend.items():
                tk.Label(self.table_frame, text=value, background=utils.BG_COLOR).grid(row=row, column=col, padx=5, pady=5)
                col+=1
            self._inner_buttons(row, col)
            col=0
            row+=1
                
    def _inner_buttons(self, row, col):
        buttons_frame = tk.Frame(self.table_frame, bg=utils.BG_COLOR)
        buttons_frame.grid(row=row, column=col, padx=5, pady=5, sticky="e")
        ttk.Button(buttons_frame, text="Correcto", style=utils.SEC_TBUTTON_STYLE, command=lambda e: self._confirm_result(row)).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(buttons_frame, text="Incorrecto", style=utils.SEC_TBUTTON_STYLE, command=lambda e: self._wrong_result(row)).grid(row=0, column=1, padx=5, pady=5)

    def _confirm_result(self, row):
        pass
    
    def _wrong_result(self, row):
        pass
        
    def _on_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

