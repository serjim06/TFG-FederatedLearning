import tkinter as tk
import uuid
from tkinter import ttk, messagebox
from src.db import dbcon


class ProfileFrame(tk.Frame):
    def __init__(self, parent, switch_frame, usuario):
        super().__init__(parent)
        self.configure(bg="#e0e0e0")
        self.usuario = usuario
        self.switch_frame = switch_frame

        # Estilo de botones
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Segoe UI", 12, "bold"),
                        foreground="#ffffff", background="#4a90e2")
        style.map("Accent.TButton",
                  background=[("active", "#357ABD")],
                  foreground=[("active", "#ffffff")])

        # Encabezado
        ttk.Label(self, text="Mi Cuenta", font=("Segoe UI", 22, "bold"),
                  background="#e0e0e0").pack(pady=(30, 20))

        # Frame para la información
        self.info_frame = tk.Frame(self, bg="#f5f5f5", bd=1, relief=tk.RIDGE)
        self.info_frame.pack(padx=50, pady=20, fill=tk.BOTH, expand=True)

        # ID
        ttk.Label(self.info_frame, text=f"ID: {uuid.UUID(bytes=self.usuario['id'])}",
                  font=("Segoe UI", 14), background="#f5f5f5").pack(pady=10, anchor="w", padx=10)

        # Usuario
        ttk.Label(self.info_frame, text=f"Usuario: {self.usuario['username']}",
                  font=("Segoe UI", 14), background="#f5f5f5").pack(pady=10, anchor="w", padx=10)

        # Contraseña con ocultación y botón de ojo
        ttk.Label(
            self.info_frame,
            text="Contraseña:",
            font=("Segoe UI", 14),
            background="#f5f5f5"
        ).pack(pady=(15, 5), anchor="w", padx=10)

        pw_frame = tk.Frame(self.info_frame, bg="#f5f5f5")
        pw_frame.pack(padx=10, pady=(0, 10), fill="x")

        # Campo de entrada (rellenado automáticamente)
        self.password_entry = ttk.Entry(pw_frame, show="*", font=("Segoe UI", 12), state="readonly")
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
                  font=("Segoe UI", 14), background="#f5f5f5").pack(pady=10, anchor="w", padx=10)

        # Proyectos
        ttk.Label(self.info_frame, text=f"Número de proyectos: {len(dbcon.select("projects", {"uid":self.usuario['id']}))}",
                  font=("Segoe UI", 14), background="#f5f5f5").pack(pady=10, anchor="w", padx=10)

        # Botón Cerrar sesión abajo
        self.logout_button = ttk.Button(self, text="Cerrar sesión", style="Accent.TButton", command=self.cerrar_sesion)
        self.logout_button.pack(side="bottom", pady=30, ipadx=15, ipady=5)

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
