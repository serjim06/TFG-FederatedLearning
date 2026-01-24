import tkinter as tk
from PIL import Image, ImageTk
import uuid
from src.gui import login, recover, register, dashboard, profile, modify, node_list, user_list
from src.utils.user import User
from src.db import dbcon
from src.models.node import Node
import src.utils.icons.image_finder as image_finder

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("")
        self.geometry("400x400")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", lambda: self.close())

        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.usuario_actual = None
        self.frames = {}
        self.show_frame("login")

    def show_frame(self, name, usuario : User = None):
        # Limpia el contenedor actual
        for widget in self.container.winfo_children():
            widget.destroy()

        # Crea la vista solicitada
        if name == "login":
            self.geometry("400x425")
            frame = login.LoginPanel(self.container, self.show_frame)
        elif name == "register":
            frame = register.RegisterFrame(self.container, self.show_frame)
        elif name == "recover":
            frame = recover.RecoverFrame(self.container, self.show_frame)
        elif name == "dashboard":
            self.geometry("1000x600")
            if usuario is not None:
                self.usuario_actual = usuario
            frame = dashboard.DashboardFrame(self.container, self.show_frame, self.usuario_actual)
        elif name == "profile":
            self.geometry("600x600")
            frame = profile.ProfileFrame(self.container, self.show_frame, usuario)
        elif name == "modify":
            frame = modify.ModifyPanel(self.container, self.show_frame, self.usuario_actual)
        elif name == "modified_profile":
            self.usuario_actual = usuario
            frame = profile.ProfileFrame(self.container, self.show_frame, usuario)
        elif name == "nodes":
            self.geometry("1000x600")
            frame = node_list.NodeListFrame(self.container, self.show_frame)
        elif name == "user_management":
            self.geometry("1000x600")
            frame = user_list.UserListFrame(self.container, self.show_frame, self.usuario_actual)

        self.frames[name] = frame
        frame.pack(fill="both", expand=True)

    def close(self):
        dbcon.disconnect()
        print("Desconectado de la DB")
        self.destroy()

def _create_test_project():
    prj = {
        "name": "proyecto",
        "description": "Descripción del proyecto de prueba",
        "uid": uuid.uuid4().bytes,
        "parameters": "{afds: 1234, test: true}",
        "metrics": "{accuracy: 0.95, loss: 0.05}",  
        "aggregation_strategy": "mean"
    }
    
    try:
        dbcon.command("insert", "projects", prj)
        print("Proyecto de prueba creado.")
        proyecto = dbcon.command("select", "projects", {"name": "proyecto"})
    except Exception as e:
        print(f"No se pudo crear el proyecto de prueba: {e}")
        
    nodo = {
        "valid": 1,
        "project_id": proyecto[0]["id"],
        "local_dataset_path": "/database/dataset/path/to/dataset"
    }
    
    try:
        dbcon.command("insert", "nodes", nodo)
        dbcon.command("insert", "nodes", nodo)
    except Exception as e:
        print(f"No se pudo crear el nodo de prueba: {e}")

if __name__ == "__main__":
    user = None
    dbcon.connect("database.db")
    app = App()
    app.mainloop()

