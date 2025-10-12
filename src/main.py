import tkinter as tk
from gui import login, recover, register, dashboard, profile, modify
from utils.user import User
from supabase import create_client
from src.db import dbcon

SUPABASE_URL = "https://eiwtbppjmzdqokwpofmf.supabase.co"
SUPABASE_KEY = "sb_publishable_BNvWjuceL4qlfDmt_bGZvg_45Iudw19"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("")
        self.geometry("400x400")
        self.resizable(False, False)

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
            self.geometry("400x400")
            frame = login.LoginPanel(self.container, self.show_frame)
        elif name == "register":
            frame = register.RegisterFrame(self.container, self.show_frame)
        elif name == "recover":
            frame = recover.RecoverFrame(self.container, self.show_frame)
        elif name == "dashboard":
            self.geometry("600x600")
            self.usuario_actual = usuario
            frame = dashboard.DashboardFrame(self.container, self.show_frame, self.usuario_actual)
        elif name == "profile":
            frame = profile.ProfileFrame(self.container, self.show_frame, usuario)
        elif name == "modify":
            frame = modify.ModifyPanel(self.container, self.show_frame, self.usuario_actual)
        elif name == "modified_profile":
            self.usuario_actual = usuario
            frame = profile.ProfileFrame(self.container, self.show_frame, usuario)


        self.frames[name] = frame
        frame.pack(fill="both", expand=True)

if __name__ == "__main__":
    user = None
    dbcon.connect("database.db")
    app = App()
    app.mainloop()

