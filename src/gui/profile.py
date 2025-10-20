import tkinter as tk
import uuid
from tkinter import ttk, messagebox
from src.db import dbcon


class ProfileFrame(tk.Frame):
    def __init__(self, parent, switch_frame, usuario):
        super().__init__(parent)
        self.configure(bg="#eef4fb")
        self.usuario = usuario
        self.switch_frame = switch_frame

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

        style.configure(
            "Sec.TButton",
            foreground="#000000",
            background="#e0e4eb",
            padding=6,
            borderwidth=0
        )

        style.map("Sec.TButton",
                  background=[("active", "#d3d7df"),
                              ("pressed", "#c7cbd5")],
                  foreground=[("active", "black"),
                              ("pressed", "white")])

        # Entradas (campos de texto)
        style.configure(
            "Custom.TEntry",
            fieldbackground="#ffffff",
            background="#ffffff",
            foreground="#1d2d44",
            bordercolor="#d9d9d9",
            relief="flat",
            insertcolor="#1d2d44"
        )

        # Texto general
        label_font = ("Segoe UI", 12)
        title_font = ("Segoe UI", 22, "bold")

        # Encabezado
        ttk.Label(self, text="Mi Cuenta", font=title_font,
                  background="#eef4fb").pack(pady=(30, 20))

        # Frame para la información
        self.info_frame = tk.Frame(self, bg="#eef4fb", bd=0, relief=tk.RIDGE)
        self.info_frame.pack(padx=50, pady=10, fill=tk.BOTH, expand=True)

        # ID
        ttk.Label(self.info_frame, text=f"ID: {uuid.UUID(bytes=self.usuario['id'])}",
                  font=label_font, background="#eef4fb").pack(pady=10, anchor="w", padx=10)

        # Usuario
        ttk.Label(self.info_frame, text=f"Usuario: {self.usuario['username']}",
                  font=label_font, background="#eef4fb").pack(pady=10, anchor="w", padx=10)

        # Contraseña con ocultación y botón de ojo
        ttk.Label(
            self.info_frame,
            text="Contraseña:",
            font=label_font,
            background="#eef4fb"
        ).pack(pady=(15, 5), anchor="w", padx=10)

        pw_frame = tk.Frame(self.info_frame, bg="#eef4fb")
        pw_frame.pack(padx=10, pady=(0, 10), fill="x")

        # Campo de entrada (rellenado automáticamente)
        self.password_entry = ttk.Entry(pw_frame, show="*", style="Custom.TEntry", font=label_font, state="readonly")
        self.password_entry.pack(side="left", fill="x", expand=True)
        self.password_entry.config(state="normal")
        self.password_entry.insert(0, self.usuario['password'])
        self.password_entry.config(state="readonly")


        # Botón de ojo
        self.show_pw = False
        self.eye_button = ttk.Button(pw_frame, text="👁", width=3, command=self.toggle_password)
        self.eye_button.pack(side="left", padx=5)

        # Rol
        ttk.Label(self.info_frame, text=f"Rol: {self.usuario['role']}",
                  font=label_font, background="#eef4fb").pack(pady=10, anchor="w", padx=10)

        # Proyectos
        ttk.Label(self.info_frame, text=f"Número de proyectos: {len(dbcon.select("projects", {"uid":self.usuario['id']}))}",
                  font=label_font, background="#eef4fb").pack(pady=10, anchor="w", padx=10)

        # Botón Cerrar sesión abajo
        self.logout_button = ttk.Button(self, text="Cerrar sesión", style="Accent.TButton", command=self.cerrar_sesion)
        self.logout_button.pack(pady=15, ipadx=15, ipady=5)

        self.logout_button = ttk.Button(self, text="Modificar perfil", style="Accent.TButton", command=lambda: self.switch_frame("modify", self.usuario))
        self.logout_button.pack(pady=15, ipadx=15, ipady=5)

        ttk.Button(self, text="Volver", style="Sec.TButton", command=lambda: self.switch_frame("dashboard",self.usuario)).pack(side="bottom", pady=(5, 10))

    def toggle_password(self):
        """Muestra o oculta la contraseña"""
        if self.show_pw:
            self.password_entry.config(show="*")
            self.show_pw = False
        else:
            self.password_entry.config(show="")
            self.show_pw = True

    def cerrar_sesion(self):
        confirmar = messagebox.askyesno(
            "Cerrar sesión",
            "¿Seguro que quieres cerrar sesión?"
        )
        if confirmar:
            self.switch_frame("login")
