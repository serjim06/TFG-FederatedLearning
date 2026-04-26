import tkinter as tk
from tkinter import ttk
from src.application.use_cases.register_user import RegisterUserUseCase
from src.infrastructure.repositories.sqlite_user_repository import SQLiteUserRepository
import src.utils.utils as utils
from src.gui import dialogs


class RegisterFrame(tk.Frame):
    def __init__(self, parent, switch_frame):
        super().__init__(parent)
        self.switch_frame = switch_frame
        self.configure(bg="#eef4fb")
        self._register_user_use_case = RegisterUserUseCase(SQLiteUserRepository())


        style = utils.get_style()

        label_font = ("Segoe UI", 12)
        title_font = ("Segoe UI", 22, "bold")

        ttk.Label(self, text="Crear Cuenta", font=title_font, background="#eef4fb").pack(pady=5)

        ttk.Label(self, text="Usuario:", font=label_font, background="#eef4fb").pack(pady=(5, 0))
        self.user_entry = ttk.Entry(self, font=("Segoe UI", 12), style="Custom.TEntry")
        self.user_entry.pack(pady=5, ipadx=50, ipady=5)

        ttk.Label(self, text="Contraseña:", font=("Segoe UI", 12), background="#eef4fb").pack(pady=(10, 0))
        self.pass_entry = ttk.Entry(self, show="*", font=("Segoe UI", 12), style="Custom.TEntry")
        self.pass_entry.pack(pady=5, ipadx=50, ipady=5)

        ttk.Label(self, text="Confirmar Contraseña:", font=("Segoe UI", 12), background="#eef4fb").pack(pady=(10, 0))
        self.conf_entry = ttk.Entry(self, show="*", font=("Segoe UI", 12), style="Custom.TEntry")
        self.conf_entry.pack(pady=5, ipadx=50, ipady=5)

        ttk.Label(self, text="Frase de recuperación:", font=("Segoe UI", 12), background="#eef4fb").pack(pady=(10, 0))
        self.recovery_entry = ttk.Entry(self, show="*", font=("Segoe UI", 12), style="Custom.TEntry")
        self.recovery_entry.pack(pady=5, ipadx=50, ipady=5)

        ttk.Label(self, text="Confirmar frase:", font=("Segoe UI", 12), background="#eef4fb").pack(pady=(10, 0))
        self.recovery_conf_entry = ttk.Entry(self, show="*", font=("Segoe UI", 12), style="Custom.TEntry")
        self.recovery_conf_entry.pack(pady=5, ipadx=50, ipady=5)
        
        self.recovery_conf_entry.bind("<Return>", lambda e: self._register())

        ttk.Button(self, text="Registrar", style="Accent.TButton", command=self._register).pack(pady=20, ipadx=10, ipady=5)
        ttk.Button(self, text="Volver", style="Sec.TButton", command=lambda: switch_frame("login")).pack(pady=(5, 10))


    def _register(self):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()
        confirm = self.conf_entry.get().strip()
        recovery = self.recovery_entry.get().strip()
        recovery_confirm = self.recovery_conf_entry.get().strip()

        if not username or not password or not confirm or not recovery or not recovery_confirm:
            dialogs.InfoDialog(self, "Error", "Rellena todos los campos", "error")
            return

        if password != confirm:
            dialogs.InfoDialog(self, "Error", "Las contraseñas no coinciden", "error")
            return
        if recovery != recovery_confirm:
            dialogs.InfoDialog(self, "Error", "Las frases de recuperación no coinciden", "error")
            return

        try:
            result = self._register_user_use_case.execute(
                username,
                password,
                confirm,
                recovery,
                recovery_confirm,
            )
            if not result.ok:
                dialogs.InfoDialog(self, "Error", result.error or "No se pudo registrar el usuario", "error")
                return
            dialogs.InfoDialog(self, "Éxito","Usuario registrado correctamente", "info")
            self.switch_frame("login")
        except ValueError as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")
            return