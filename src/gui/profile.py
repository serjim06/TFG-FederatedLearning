import tkinter as tk
import uuid
from tkinter import ttk
from src.db import dbcon
import src.utils.utils as utils
from src.gui import dialogs


class ProfileFrame(tk.Frame):
    def __init__(self, parent, switch_frame, usuario):
        super().__init__(parent)
        self.configure(bg="#eef4fb")
        self.usuario = usuario
        self.switch_frame = switch_frame

        utils.get_style()

        label_font = ("Segoe UI", 12)
        title_font = ("Segoe UI", 22, "bold")

        ttk.Label(self, text="Mi Cuenta", font=title_font,
                  background="#eef4fb").pack(pady=(30, 20))

        self.info_frame = tk.Frame(self, bg="#eef4fb", bd=0, relief="ridge")
        self.info_frame.pack(padx=50, pady=10, fill="both", expand=True)

        ttk.Label(self.info_frame, text=f"ID: {uuid.UUID(bytes=self.usuario['id'])}",
                  font=label_font, background="#eef4fb").pack(pady=10, anchor="w", padx=10)

        ttk.Label(self.info_frame, text=f"Usuario: {self.usuario['username']}",
                  font=label_font, background="#eef4fb").pack(pady=10, anchor="w", padx=10)

        ttk.Label(
            self.info_frame,
            text="Contraseña:",
            font=label_font,
            background="#eef4fb"
        ).pack(pady=(15, 5), anchor="w", padx=10)

        pw_frame = tk.Frame(self.info_frame, bg="#eef4fb")
        pw_frame.pack(padx=10, pady=(0, 10), fill="x")

        self.password_entry = ttk.Entry(pw_frame, show="*", style="Custom.TEntry", font=label_font, state="readonly")
        self.password_entry.pack(side="left", fill="x", expand=True)
        self.password_entry.config(state="normal")
        self.password_entry.insert(0, self.usuario['password'])
        self.password_entry.config(state="readonly")

        self.show_pw = False
        self.eye_button = ttk.Button(pw_frame, text="👁", width=3, command=self._toggle_password)
        self.eye_button.pack(side="left", padx=5)

        ttk.Label(self.info_frame, text=f"Rol: {self.usuario['role']}",
                  font=label_font, background="#eef4fb").pack(pady=10, anchor="w", padx=10)

        ttk.Label(self.info_frame, text=f"Número de proyectos: {len(dbcon.command("select","projects", {"uid":self.usuario['id']}))}",
                  font=label_font, background="#eef4fb").pack(pady=10, anchor="w", padx=10)

        self.logout_button = ttk.Button(self, text="Cerrar sesión", style="Accent.TButton", command=self._cerrar_sesion)
        self.logout_button.pack(pady=15, ipadx=15, ipady=5)

        self.modify_button = ttk.Button(self, text="Modificar perfil", style="Accent.TButton", command=lambda: self.switch_frame("modify", self.usuario))
        self.modify_button.pack(pady=15, ipadx=15, ipady=5)

        ttk.Button(self, text="Volver", style="Sec.TButton", command=lambda: self.switch_frame("dashboard",self.usuario)).pack(side="bottom", pady=(5, 10))

    def _toggle_password(self):
        if self.show_pw:
            self.password_entry.config(show="*")
            self.show_pw = False
        else:
            self.password_entry.config(show="")
            self.show_pw = True

    def _cerrar_sesion(self):
        confirmar = dialogs.OptionDialog.ask(self, "Cerrar sesión", "¿Seguro que quieres cerrar sesión?")
        if confirmar:
            self.switch_frame("login")
