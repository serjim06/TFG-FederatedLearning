import tkinter as tk
from tkinter import ttk
from src.application.use_cases.update_user_profile import UpdateUserProfileUseCase
from src.infrastructure.repositories.sqlite_user_repository import SQLiteUserRepository
from src.utils.user import User
import src.utils.utils as utils
from src.gui import dialogs

class ModifyPanel(tk.Frame):
    def __init__(self, parent, switch_frame, usuario):
        super().__init__(parent)
        self.configure(bg="#eef4fb")
        self.switch_frame = switch_frame
        self.usuario = usuario
        self._update_user_profile_use_case = UpdateUserProfileUseCase(SQLiteUserRepository())

        self.columnconfigure(0, weight=1)

        style = utils.get_style()

        label_font = ("Segoe UI", 17)
        title_font = ("Segoe UI", 22, "bold")

        ttk.Label(self, text="Modificar Perfil", font=title_font, background="#eef4fb").grid(
            row=0, column=0, pady=20)

        tk.Label(self, text="Usuario:", font=label_font, background="#eef4fb").grid(
            row=1, column=0, padx=5, pady=5)
        self.user_entry = ttk.Entry(self, style="Custom.TEntry", font=("Segoe UI", 12), width=20)
        self.user_entry.insert(0, self.usuario['username'])
        self.user_entry.grid(row=2, column=0, padx=5, pady=5)

        self.user_entry.bind("<Return>", lambda e: self._modify())

        ttk.Label(self, text="Contraseña:", font=label_font, background="#eef4fb").grid(
            row=3, column=0, padx=5, pady=5)

        pw_frame = tk.Frame(self, background="#eef4fb")
        pw_frame.grid(row=4, column=0, pady=5)

        self.password_entry = ttk.Entry(pw_frame, show="*", style="Custom.TEntry", font=("Segoe UI", 12), width=20)
        self.password_entry.pack(side="left", fill="x", expand=True)

        self.password_entry.bind("<Return>", lambda e: self._modify())

        self.show_pw = False
        self.eye_button = tk.Label(pw_frame, text="👁", bg="#ffffff", cursor="hand2")
        self.eye_button.place(relx=1.0, rely=0.5, x=-5, y=0, anchor="e")
        self.eye_button.bind("<Button-1>", lambda e: self._toggle_password())

        ttk.Label(self, text="Confirmar Contraseña:", font=label_font, background="#eef4fb").grid(
            row=5, column=0, padx=5, pady=5)
        self.password_confirm_entry = ttk.Entry(self, show="*", style="Custom.TEntry", font=("Segoe UI", 12), width=20)
        self.password_confirm_entry.grid(row=6, column=0, padx=5, pady=5)

        ttk.Label(self, text="Nueva frase recuperación:", font=label_font, background="#eef4fb").grid(
            row=7, column=0, padx=5, pady=5)
        self.recovery_entry = ttk.Entry(self, show="*", style="Custom.TEntry", font=("Segoe UI", 12), width=20)
        self.recovery_entry.grid(row=8, column=0, padx=5, pady=5)

        ttk.Label(self, text="Confirmar frase:", font=label_font, background="#eef4fb").grid(
            row=9, column=0, padx=5, pady=5)
        self.recovery_confirm_entry = ttk.Entry(self, show="*", style="Custom.TEntry", font=("Segoe UI", 12), width=20)
        self.recovery_confirm_entry.grid(row=10, column=0, padx=5, pady=5)

        ttk.Button(self, text="Confirmar cambios", style="Accent.TButton", command=self._modify).grid(row=11,column=0,pady=20, ipadx=10, ipady=5)

        ttk.Button(self, text="Volver", style="Sec.TButton", command=lambda: self.switch_frame("profile",self.usuario)).grid(row=12,column=0, pady=(5, 10))

    def _toggle_password(self):
        """Shows or hides the password field."""
        if self.show_pw:
            self.password_entry.config(show="*")
            self.show_pw = False
        else:
            self.password_entry.config(show="")
            self.show_pw = True


    def _modify(self):
        user = self.user_entry.get().strip()
        passwd = self.password_entry.get().strip()
        passwd_confirm = self.password_confirm_entry.get().strip()
        recovery_phrase = self.recovery_entry.get().strip()
        recovery_confirm = self.recovery_confirm_entry.get().strip()

        try:
            result = self._update_user_profile_use_case.execute(
                self.usuario["id"],
                user,
                passwd,
                passwd_confirm,
                recovery_phrase,
                recovery_confirm,
            )
            if not result.ok:
                dialogs.InfoDialog(self, "Error", result.error or "No se pudo actualizar el perfil", "error")
                return
            updated = result.data
            new_user = User(
                updated["id"],
                updated["username"],
                updated["role"],
                updated.get("password_hash"),
                updated.get("recovery_phrase_hash"),
            )
            dialogs.InfoDialog(self, "Success", "Los datos se han modificado correctamente", "info")
            self.switch_frame("modified_profile", new_user)

        except ValueError as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")
            return