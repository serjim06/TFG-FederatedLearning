import tkinter as tk
from tkinter import ttk, messagebox

from src.db import dbcon


class RegisterFrame(tk.Frame):
    def __init__(self, parent, switch_frame):
        super().__init__(parent)
        self.switch_frame = switch_frame
        self.configure(bg="#eef4fb")


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
            background="#c0bfff",
            padding=6,
            borderwidth=0
        )

        style.map("Sec.TButton",
                  background=[("active", "#a099ff"),
                              ("pressed", "#7f7fff")],
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
        ttk.Label(self, text="Crear Cuenta", font=title_font, background="#eef4fb").pack(pady=5)

        # Usuario
        ttk.Label(self, text="Usuario:", font=label_font, background="#eef4fb").pack(pady=(5, 0))
        self.user_entry = ttk.Entry(self, font=("Segoe UI", 12), style="Custom.TEntry")
        self.user_entry.pack(pady=5, ipadx=50, ipady=5)

        # Contraseña
        ttk.Label(self, text="Contraseña:", font=("Segoe UI", 12), background="#eef4fb").pack(pady=(10, 0))
        self.pass_entry = ttk.Entry(self, show="*", font=("Segoe UI", 12), style="Custom.TEntry")
        self.pass_entry.pack(pady=5, ipadx=50, ipady=5)

        # Confirmar contraseña
        ttk.Label(self, text="Confirmar Contraseña:", font=("Segoe UI", 12), background="#eef4fb").pack(pady=(10, 0))
        self.conf_entry = ttk.Entry(self, show="*", font=("Segoe UI", 12), style="Custom.TEntry")
        self.conf_entry.pack(pady=5, ipadx=50, ipady=5)
        
        self.conf_entry.bind("<Return>", lambda e: self.register())

        ttk.Button(self, text="Registrar", style="Accent.TButton", command=self.register).pack(pady=20, ipadx=10, ipady=5)
        ttk.Button(self, text="Volver", style="Sec.TButton", command=lambda: switch_frame("login")).pack(pady=(5, 10))


    def register(self):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()
        confirm = self.conf_entry.get().strip()

        if not username or not password or not confirm:
            messagebox.showerror("Error", "Rellena todos los campos")
            return

        if password != confirm:
            messagebox.showerror("Error", "Las contraseñas no coinciden")
            return

        try:
            dbcon.insert("users", {
                "username": username,
                "password": password,
                "role": "user"
            })

            messagebox.showinfo("Éxito","Usuario registrado correctamente")
            self.switch_frame("login")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return