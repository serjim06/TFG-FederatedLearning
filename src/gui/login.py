import json
import tkinter as tk
from tkinter import ttk, messagebox
from src.db import dbcon
from src.utils.user import User


class LoginPanel(tk.Frame):
    def __init__(self, parent, switch_frame):
        super().__init__(parent)
        self.configure(bg="#e0e0e0")  # fondo gris suave
        self.switch_frame = switch_frame

        # Estilo de botones
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"), foreground="#ffffff", background="#4a90e2")
        style.map("Accent.TButton",
                  background=[("active", "#357ABD")],
                  foreground=[("active", "#ffffff")])

        # Encabezado
        ttk.Label(self, text="Iniciar Sesión", font=("Segoe UI", 22, "bold"), background="#e0e0e0").pack(pady=20)

        # Usuario
        ttk.Label(self, text="Usuario:", font=("Segoe UI", 12), background="#e0e0e0").pack(pady=(5, 0))
        self.user_entry = ttk.Entry(self, font=("Segoe UI", 12))
        self.user_entry.pack(pady=5, ipadx=50, ipady=5)

        # Contraseña
        ttk.Label(self, text="Contraseña:", font=("Segoe UI", 12), background="#e0e0e0").pack(pady=(10, 0))
        self.password_entry = ttk.Entry(self, show="*", font=("Segoe UI", 12))
        self.password_entry.pack(pady=5, ipadx=50, ipady=5)

        # Botón Entrar
        ttk.Button(self, text="Entrar", style="Accent.TButton", command=self.login).pack(pady=20, ipadx=10, ipady=5)

        # Botones secundarios
        ttk.Button(self, text="No tengo cuenta", command=lambda: switch_frame("register")).pack(pady=(5, 2))
        ttk.Button(self, text="Olvidé mi contraseña", command=lambda: switch_frame("recover")).pack(pady=2)

    def login(self):
        user = self.user_entry.get()
        passwd = self.password_entry.get()

        if not(user or passwd):
            messagebox.showerror("Error", "Rellena los campos")

        try:
            obj_user = dbcon.select("users", {
                "username": user,
                "password": passwd
            })

            if not obj_user:
                messagebox.showerror("Error", "Usuario o contraseña incorrectos")
                return

            new_user = User(**obj_user[0])
            self.switch_frame("dashboard", new_user)

        except Exception as e:
            messagebox.showerror("Error", str(e))
            return