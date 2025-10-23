import tkinter as tk
from tkinter import ttk, messagebox
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

        # Encabezado
        ttk.Label(self, text=f"Bienvenido, {self.usuario['username']}", font=title_font,
                  background="#eef4fb").pack(pady=(30, 20))

        # Frame central para botones de opción
        self.content_frame = tk.Frame(self, bg="#eef4fb")
        self.content_frame.pack(pady=20)

        # Botón Ver Cuenta
        ttk.Button(self.content_frame, text="Ver mi cuenta", style="Accent.TButton",
                   command=self._ver_cuenta).pack(pady=15, ipadx=20, ipady=10)

        # Botón Ver Proyectos
        ttk.Button(self.content_frame, text="Ver mis proyectos", style="Accent.TButton",
                   command=self._ver_proyectos).pack(pady=15, ipadx=20, ipady=10)

    def _ver_cuenta(self):
        self.switch_frame("profile", self.usuario)

    def _ver_proyectos(self):
        raise NotImplementedError()

