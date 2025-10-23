import tkinter as tk
from sqlite3 import DatabaseError
from tkinter import ttk, messagebox
from src.db import dbcon
from src.utils.user import User
import src.utils.utils as utils


class LoginPanel(tk.Frame):
    def __init__(self, parent, switch_frame):
        super().__init__(parent)
        self.configure(bg="#eef4fb")
        self.switch_frame = switch_frame

        style = utils.get_style()

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
        self.eye_button.bind("<Button-1>", lambda e: self._toggle_password())

        # Botón Entrar
        ttk.Button(
            self, text="Iniciar sesión", style="Accent.TButton", command=self._login
        ).pack(pady=20, ipadx=10, ipady=5)

        self.password_entry.bind("<Return>", lambda e: self._login())

        # Botones secundarios
        ttk.Button(
            self, text="No tengo cuenta", style="Sec.TButton", command=lambda: switch_frame("register")).pack(pady=(5, 2))

        ttk.Button(
            self, text="Olvidé mi contraseña", style="Sec.TButton", command=lambda: switch_frame("recover")).pack(pady=2)

    def _toggle_password(self):
        """Shows or hides the password."""
        if self.show_pw:
            self.password_entry.config(show="*")
            self.show_pw = False
        else:
            self.password_entry.config(show="")
            self.show_pw = True

    def _login(self):
        user = self.user_entry.get()
        passwd = self.password_entry.get()

        if not(user or passwd):
            messagebox.showerror("Error", "Rellena los campos")
            return

        try:
            obj_user = dbcon.command("select","users", {"username": user, "password": passwd})

            if not obj_user:
                messagebox.showerror("Error", "Usuario o contraseña incorrectos")
                return

            new_user = User(**obj_user[0])
            self.switch_frame("dashboard", new_user)

        except ValueError or DatabaseError as e:
            messagebox.showerror("Error", str(e))
            return