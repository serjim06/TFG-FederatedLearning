import json
from sqlite3 import DatabaseError
import tkinter as tk
from tkinter import ttk
import uuid

import src.db.dbcon as dbcon
from src.utils import utils
from src.gui import dialogs

class UserInfoDialog(tk.Toplevel):
    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.title("User Information")
        self.geometry("400x600")
        self.resizable(False, False)
        
        self.configure(bg="#eef4fb")
        
        utils.get_style()
        
        self.transient(parent)
        self.wait_visibility()
        self.grab_set()
        self.focus_set()
        
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        
        self.user_data = user_data
        print(user_data["id"])
        self.parent = parent
        
        self.top_frame = tk.Frame(self)
        self.top_frame.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(self.top_frame, borderwidth=0, background="#eef4fb")
        self.frame = tk.Frame(self.canvas, background="#eef4fb")
        self.vsb = tk.Scrollbar(self.top_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.frame.bind("<Configure>", self._on_frame_configure)


        self.inner_window = self.canvas.create_window((0,0), window=self.frame, anchor="nw")
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
                
        self.id_label = tk.Label(self.frame, text=f"User ID: {str(uuid.UUID(bytes=user_data['id']))}", font=("Arial", 10), bg="#eef4fb")
        self.id_label.pack(anchor="w", pady=5)
        
        self.name_label = tk.Label(self.frame, text=f"Nombre: {user_data['username']}", font=("Arial", 10), bg="#eef4fb")
        self.name_label.pack(anchor="w", pady=10)
        
        
        self.role_label = tk.Label(self.frame, text=f"Role: {user_data['role']}", font=("Arial", 10), bg="#eef4fb")
        self.role_label.pack(anchor="w", pady=5)
        
        self.user_projects = dbcon.command("select", "projects", {"uid": user_data["id"]})
        
        self.projects_label = tk.Label(self.frame, text="Projects:", font=("Arial", 10, "bold"), bg="#eef4fb")
        self.projects_label.pack(anchor="w", pady=10)
        
        for project in self.user_projects:
            project_frame = tk.Frame(self.frame, bg="#eef4fb", bd=1, relief="solid")
            project_label = tk.Label(project_frame, text=f"- {project['name']}", font=("Arial", 10), bg="#eef4fb")
            project_label.pack(anchor="w", padx=20)
            nodes_frame = tk.Frame(project_frame, bg="#eef4fb", bd=1, relief="solid")
            nodes = json.loads(project['nodes'])
            tk.Label(nodes_frame, text="  Nodes:", font=("Arial", 10, "bold"), bg="#eef4fb").pack(anchor="w", padx=30)
            for node in nodes:
                tk.Label(nodes_frame, text=f"  - {node}", font=("Arial", 10), bg="#eef4fb").pack(anchor="w", padx=40)
            nodes_frame.pack(fill="both", expand=True, padx=10, pady=5)
            project_frame.pack(fill="both", expand=True, padx=10, pady=5)
            
        self.buttons_frame = tk.Frame(self)
        self.buttons_frame.pack(pady=10)
        
        ttk.Button(self.buttons_frame, text="Volver", command=self.destroy, style="Sec.TButton").pack(side="left", padx=5)
        ttk.Button(self.buttons_frame, text="Eliminar Usuario", command=self.delete_user, style="Accent.TButton").pack(side="left", padx=5)
        
                
    def delete_user(self):
        if dialogs.OptionDialog.ask(self, "Confirmar Eliminación", "¿Estás seguro de que deseas eliminar este usuario? Esta acción no se puede deshacer. Se eliminarán todos los proyectos asociados a este usuario."):
            try:
                dbcon.command("delete", "projects", {"uid": self.user_data["id"]})
                dbcon.command("delete", "users", {"id": self.user_data["id"]})
            except (ValueError, DatabaseError) as e:
                dialogs.InfoDialog(self, "Error", str(e), "error")
                return
            
            dialogs.InfoDialog(self, "Usuario Eliminado", "El usuario ha sido eliminado correctamente.", "info")
            self.destroy()
            
            
    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))