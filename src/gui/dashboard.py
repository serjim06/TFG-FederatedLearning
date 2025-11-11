import tkinter as tk
from tkinter import ttk
from src.gui.node_list import NodeListFrame
import src.utils.utils as utils

class DashboardFrame(tk.Frame):
    def __init__(self, parent, switch_frame, usuario):
        super().__init__(parent)
        self.configure(bg="#eef4fb")
        self.switch_frame = switch_frame
        self.usuario = usuario

        style = utils.get_style()

        # Texto general
        label_font = ("Segoe UI", 12)
        title_font = ("Segoe UI", 22, "bold")
        
        # Frame central para botones de opción
        self.content_frame = tk.Frame(self, bg="#eef4fb")
        self.content_frame.pack(fill="both", expand=True, pady=20)
        
    
        if usuario['role'] == 'admin':
            frame = NodeListFrame(self.content_frame, self.switch_frame, self.usuario)
            
        frame.pack(fill="both", expand=True)



    def _ver_proyectos(self):
        raise NotImplementedError()

    def _ver_nodos(self):
        self.switch_frame("nodes")

