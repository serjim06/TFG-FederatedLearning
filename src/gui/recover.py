import tkinter as tk
from tkinter import ttk
from src.db import dbcon
from src.gui import dialogs
from src.utils.user import User
import src.utils.utils as utils
from src.security.auth_policy import validate_password_strength, validate_recovery_phrase
from src.security.passwords import hash_password, verify_password

class RecoverFrame(tk.Frame):
    def __init__(self, parent, switch_frame):
        super().__init__(parent)
        self.configure(bg="#eef4fb")

        self.parent = parent

        style = utils.get_style()

        label_font = ("Segoe UI", 12)
        title_font = ("Segoe UI", 22, "bold")

        self.switch_frame = switch_frame
        self.new_user : User = None

        self.content_frame = tk.Frame(self, bg="#eef4fb")
        self.content_frame.pack(fill="x", pady=20)

        ttk.Label(self.content_frame, text="Recuperar contraseña", font=title_font, background="#eef4fb").pack(pady=(0, 30))

        self.user_label = ttk.Label(self.content_frame, text="Introduce tu usuario:", font=label_font, background="#eef4fb")
        self.user_label.pack(pady=5)
        self.user_entry = ttk.Entry(self.content_frame, style="Custom.TEntry", font=("Segoe UI", 12))
        self.user_entry.pack(pady=5, ipadx=50, ipady=5)

        self.user_entry.bind("<Return>", lambda e: self._verify_user())

        self.verify_button = ttk.Button(self.content_frame, text="Verificar usuario", style="Accent.TButton", command=self._verify_user)
        self.verify_button.pack(pady=20, ipadx=10, ipady=5)

        self.recovery_label = ttk.Label(self.content_frame, text="Frase de recuperación:", font=label_font, background="#eef4fb")
        self.recovery_entry = ttk.Entry(self.content_frame, show="*", style="Custom.TEntry", font=("Segoe UI", 12))
        self.new_password_label = ttk.Label(self.content_frame, text="Nueva contraseña:", font=label_font, background="#eef4fb")
        self.new_password_entry = ttk.Entry(self.content_frame, show="*", style="Custom.TEntry", font=("Segoe UI", 12))
        self.conf_new_password_label = ttk.Label(self.content_frame, text="Confirmar nueva contraseña:", font=label_font, background="#eef4fb")
        self.conf_new_password_entry = ttk.Entry(self.content_frame, show="*", style="Custom.TEntry", font=("Segoe UI", 12))
        self.reset_button = ttk.Button(self.content_frame, text="Recuperar contraseña", style="Accent.TButton", command=self._reset_password)

        self.conf_new_password_entry.bind("<Return>", lambda e: self._reset_password())

        self.back_button = ttk.Button(self.content_frame, text="Volver", style="Sec.TButton", command=lambda: switch_frame("login"))
        self.back_button.pack(side="bottom", pady=(5, 10))

    def _verify_user(self):
        user = self.user_entry.get().strip()
        if not user:
            dialogs.InfoDialog(self, "Error", "Introduce un usuario", "error")
            return

        try:
            result = dbcon.command("select","users", {"username": user})
            if not result:
                dialogs.InfoDialog(self, "Error", "Usuario o credenciales de recuperación incorrectos", "error")
                return

            row = result[0]
            self.new_user = User(
                id=row["id"],
                username=row["username"],
                role=row["role"],
                password_hash=row.get("password_hash"),
                recovery_phrase_hash=row.get("recovery_phrase_hash"),
            )
            if not self.new_user["recovery_phrase_hash"]:
                dialogs.InfoDialog(
                    self,
                    "Error",
                    "Esta cuenta no tiene frase de recuperación configurada. Contacta con administración.",
                    "error",
                )
                return

            self.user_label.pack_forget()
            self.user_entry.pack_forget()
            self.verify_button.pack_forget()

            self.recovery_label.pack(pady=(10, 5))
            self.recovery_entry.pack(pady=5, ipadx=50, ipady=5)
            self.new_password_label.pack(pady=(10, 5))
            self.new_password_entry.pack(pady=5, ipadx=50, ipady=5)
            self.conf_new_password_label.pack(pady=(15, 5))
            self.conf_new_password_entry.pack(pady=5, ipadx=50, ipady=5)
            self.reset_button.pack(pady=20, ipadx=10, ipady=5)
            root = self.winfo_toplevel()
            root.geometry(f"{int(400)}x{int(500)}")

        except Exception as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")
            return



    def _reset_password(self):
        recovery_phrase = self.recovery_entry.get().strip()
        new_pass = self.new_password_entry.get()
        conf_pass = self.conf_new_password_entry.get()

        if not recovery_phrase or not new_pass or not conf_pass:
            dialogs.InfoDialog(self, "Error", "Rellena todos los campos", "error")
            return
        if new_pass != conf_pass:
            dialogs.InfoDialog(self, "Error", "Las contraseñas no coinciden", "error")
            return

        try:
            validate_password_strength(new_pass)
            validate_recovery_phrase(recovery_phrase)
            if not verify_password(recovery_phrase, self.new_user["recovery_phrase_hash"]):
                dialogs.InfoDialog(self, "Error", "Usuario o credenciales de recuperación incorrectos", "error")
                return
            dbcon.command("update","users", {
                "id": self.new_user["id"],
                "password_hash": hash_password(new_pass),
            })

            dialogs.InfoDialog(self, "Éxito", "Contraseña actualizada correctamente", "info")
            self.switch_frame("login")

        except Exception as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")
            return