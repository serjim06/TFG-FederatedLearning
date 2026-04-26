import tkinter as tk
import uuid
from tkinter import ttk
import src.utils.utils as utils
from src.gui import dialogs
from src.application.use_cases.get_profile_info import GetProfileInfoUseCase
from src.infrastructure.repositories.sqlite_project_repository import SQLiteProjectRepository
from src.infrastructure.repositories.sqlite_user_repository import SQLiteUserRepository


class ProfileFrame(tk.Frame):
    def __init__(self, parent, switch_frame, usuario):
        super().__init__(parent)
        self.configure(bg="#eef4fb")
        self.usuario = usuario
        self.switch_frame = switch_frame
        self._get_profile_info_use_case = GetProfileInfoUseCase(
            SQLiteUserRepository(),
            SQLiteProjectRepository(),
        )

        utils.get_style()

        label_font = ("Segoe UI", 12)
        title_font = ("Segoe UI", 22, "bold")
        profile_result = self._get_profile_info_use_case.execute(self.usuario["id"])
        profile = self.usuario if not profile_result.ok else profile_result.data

        ttk.Label(self, text="Mi Cuenta", font=title_font,
                  background="#eef4fb").pack(pady=(30, 20))

        self.info_frame = tk.Frame(self, bg="#eef4fb", bd=0, relief="ridge")
        self.info_frame.pack(padx=50, pady=10, fill="both", expand=True)

        ttk.Label(self.info_frame, text=f"ID: {uuid.UUID(bytes=profile['id'])}",
                  font=label_font, background="#eef4fb").pack(pady=10, anchor="w", padx=10)

        ttk.Label(self.info_frame, text=f"Usuario: {profile['username']}",
                  font=label_font, background="#eef4fb").pack(pady=10, anchor="w", padx=10)

        ttk.Label(
            self.info_frame,
            text="Contraseña: protegida",
            font=label_font,
            background="#eef4fb"
        ).pack(pady=(15, 10), anchor="w", padx=10)

        ttk.Label(self.info_frame, text=f"Rol: {profile['role']}",
                  font=label_font, background="#eef4fb").pack(pady=10, anchor="w", padx=10)

        project_count = profile.get("project_count", 0)
        ttk.Label(self.info_frame, text=f"Número de proyectos: {project_count}",
                  font=label_font, background="#eef4fb").pack(pady=10, anchor="w", padx=10)

        self.logout_button = ttk.Button(self, text="Cerrar sesión", style="Accent.TButton", command=self._cerrar_sesion)
        self.logout_button.pack(pady=15, ipadx=15, ipady=5)

        self.modify_button = ttk.Button(self, text="Modificar perfil", style="Accent.TButton", command=lambda: self.switch_frame("modify", self.usuario))
        self.modify_button.pack(pady=15, ipadx=15, ipady=5)

        ttk.Button(self, text="Volver", style="Sec.TButton", command=lambda: self.switch_frame("dashboard",self.usuario)).pack(side="bottom", pady=(5, 10))

    def _cerrar_sesion(self):
        confirmar = dialogs.OptionDialog.ask(self, "Cerrar sesión", "¿Seguro que quieres cerrar sesión?")
        if confirmar:
            self.switch_frame("login")
