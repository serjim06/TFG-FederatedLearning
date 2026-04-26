import tkinter as tk
import time
from tkinter import ttk
from src.application.use_cases.authenticate_user import AuthenticateUserUseCase
from src.infrastructure.repositories.sqlite_user_repository import SQLiteUserRepository
from src.utils.user import User
import src.utils.utils as utils
from src.gui import dialogs
import src.utils.icons.image_finder as image_finder
from PIL import ImageTk, Image
from src.security.auth_policy import MAX_LOGIN_ATTEMPTS, LOCK_SECONDS, get_lock_message

class LoginPanel(tk.Frame):
    def __init__(self, parent, switch_frame):
        super().__init__(parent)
        self.configure(bg="#eef4fb")
        self.switch_frame = switch_frame
        self.failed_attempts = 0
        self.locked_until = 0.0
        self._authenticate_user_use_case = AuthenticateUserUseCase(SQLiteUserRepository())

        style = utils.get_style()

        label_font = ("Segoe UI", 12)
        title_font = ("Segoe UI", 22, "bold")

        ttk.Label(
            self, text="Iniciar Sesión",
            font=title_font, background="#eef4fb", foreground="#1d2d44"
        ).pack(pady=20)

        ttk.Label(
            self, text="Usuario:",
            font=label_font, background="#eef4fb", foreground="#1d2d44"
        ).pack(pady=(5, 0))

        self.user_entry = ttk.Entry(self, font=("Segoe UI", 12), style="Custom.TEntry")
        self.user_entry.pack(pady=5, ipadx=50, ipady=5)

        ttk.Label(
            self, text="Contraseña:",
            font=label_font, background="#eef4fb", foreground="#1d2d44"
        ).pack(pady=(10, 0))

        self.password_entry = ttk.Entry(self, show="*", font=("Segoe UI", 12), style="Custom.TEntry")
        self.password_entry.pack(pady=5, ipadx=50, ipady=5)

        self.show_pw = False
        self.eye_button = tk.Label(
            self.password_entry, text="👁",
            bg="#ffffff", fg="#1d2d44", cursor="hand2"
        )
        self.eye_button.place(relx=1.0, rely=0.5, x=-5, y=0, anchor="e")
        self.eye_button.bind("<Button-1>", lambda e: self._toggle_password())

        ttk.Button(
            self, text="Iniciar sesión", style="Accent.TButton", command=self._login
        ).pack(pady=20, ipadx=10, ipady=5)

        self.password_entry.bind("<Return>", lambda e: self._login())

        ttk.Button(
            self, text="No tengo cuenta", style="Sec.TButton", command=lambda: switch_frame("register")).pack(pady=(5, 2))

        ttk.Button(
            self, text="Olvidé mi contraseña", style="Sec.TButton", command=lambda: switch_frame("recover")).pack(pady=2)
        

    def _toggle_password(self):
        if self.show_pw:
            self.password_entry.config(show="*")
            self.show_pw = False
        else:
            self.password_entry.config(show="")
            self.show_pw = True

    def _login(self):
        user = self.user_entry.get()
        passwd = self.password_entry.get()

        if not user or not passwd:
            dialogs.InfoDialog(self, "Error", "Rellena los campos", "error")
            return
        if time.time() < self.locked_until:
            dialogs.InfoDialog(self, "Error", get_lock_message(self.locked_until), "error")
            return

        try:
            result = self._authenticate_user_use_case.execute(user, passwd)
            if not result.ok:
                self._handle_failed_attempt()
                dialogs.InfoDialog(self, "Error", result.error or "Usuario o contraseña incorrectos", "error")
                return
            row = result.data
            self.failed_attempts = 0
            self.locked_until = 0.0
            new_user = User(
                id=row["id"],
                username=row["username"],
                role=row["role"],
                password_hash=row.get("password_hash"),
                recovery_phrase_hash=row.get("recovery_phrase_hash"),
            )
            self.switch_frame("dashboard", new_user)

        except ValueError as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")
            return

    def _handle_failed_attempt(self):
        self.failed_attempts += 1
        if self.failed_attempts >= MAX_LOGIN_ATTEMPTS:
            self.locked_until = time.time() + LOCK_SECONDS
            self.failed_attempts = 0