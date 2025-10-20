import tkinter as tk
from tkinter import ttk, messagebox
from src.db import dbcon
from src.utils.user import User


class LoginPanel(tk.Frame):
    def __init__(self, parent, switch_frame):
        super().__init__(parent)
        self.configure(bg="#eef4fb")
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

        # ----- Interfaz -----
        ttk.Label(
            self, text="Iniciar Sesión",
            font=title_font, background="#eef4fb", foreground="#1d2d44"
        ).pack(pady=20)

        # Usuario
        ttk.Label(
            self, text="Usuario:",
            font=label_font, background="#eef4fb", foreground="#1d2d44"
        ).pack(pady=(5, 0))

        self.user_entry = ttk.Entry(self, font=("Segoe UI", 12), style="Custom.TEntry")
        self.user_entry.pack(pady=5, ipadx=50, ipady=5)

        # Contraseña
        ttk.Label(
            self, text="Contraseña:",
            font=label_font, background="#eef4fb", foreground="#1d2d44"
        ).pack(pady=(10, 0))

        self.password_entry = ttk.Entry(self, show="*", font=("Segoe UI", 12), style="Custom.TEntry")
        self.password_entry.pack(pady=5, ipadx=50, ipady=5)

        # Botón del ojo
        self.show_pw = False
        self.eye_button = tk.Label(
            self.password_entry, text="👁",
            bg="#ffffff", fg="#1d2d44", cursor="hand2"
        )
        self.eye_button.place(relx=1.0, rely=0.5, x=-5, y=0, anchor="e")
        self.eye_button.bind("<Button-1>", lambda e: self.toggle_password())

        # Botón Entrar
        ttk.Button(
            self, text="Entrar", style="Accent.TButton", command=self.login
        ).pack(pady=20, ipadx=10, ipady=5)

        self.password_entry.bind("<Return>", lambda e: self.login())

        # Botones secundarios
        ttk.Button(
            self, text="No tengo cuenta", style="Sec.TButton", command=lambda: switch_frame("register")).pack(pady=(5, 2))

        ttk.Button(
            self, text="Olvidé mi contraseña", style="Sec.TButton", command=lambda: switch_frame("recover")).pack(pady=2)

    def toggle_password(self):
        """Muestra o oculta la contraseña"""
        if self.show_pw:
            self.password_entry.config(show="*")
            self.show_pw = False
        else:
            self.password_entry.config(show="")
            self.show_pw = True

    def login(self):
        user = self.user_entry.get()
        passwd = self.password_entry.get()

        if not(user or passwd):
            messagebox.showerror("Error", "Rellena los campos")
            return

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