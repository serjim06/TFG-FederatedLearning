import tkinter as tk
from tkinter import ttk, messagebox

class DashboardFrame(tk.Frame):
    def __init__(self, parent, switch_frame, usuario):
        super().__init__(parent)
        self.configure(bg="#eef4fb")
        self.switch_frame = switch_frame
        self.usuario = usuario  # objeto o dict con info del usuario

        # ----- Estilos -----
        style = ttk.Style()
        style.theme_use("clam")

        # Botón principal (azul brillante)
        style.configure(
            "Accent.TButton",
            font=("Segoe UI", 11, "bold"),
            foreground="#ffffff",
            background="#4a90e2",
            padding=6,
            borderwidth=0
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#357ABD"), ("pressed", "#2c5a92")],
            foreground=[("active", "#ffffff")]
        )

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
                   command=self.ver_cuenta).pack(pady=15, ipadx=20, ipady=10)

        # Botón Ver Proyectos
        ttk.Button(self.content_frame, text="Ver mis proyectos", style="Accent.TButton",
                   command=self.ver_proyectos).pack(pady=15, ipadx=20, ipady=10)

    def ver_cuenta(self):
        self.switch_frame("profile", self.usuario)

    def ver_proyectos(self):
        # Aquí puedes mostrar un popup o abrir un frame con los proyectos del usuario
        # Ejemplo simple:
        proyectos = self.usuario.get("proyectos", ["Proyecto 1", "Proyecto 2"])
        proyectos_text = "\n".join(proyectos)
        messagebox.showinfo("Mis proyectos", proyectos_text)

