import tkinter as tk
import uuid

from src.db import dbcon
from src.utils.user import User


class UserCard(tk.Frame):
    def __init__(self, parent, user_data):
        super().__init__(parent, bg="#eeeeee", bd=1, relief="solid", padx=10, pady=10)
        
        self.parent = parent
        
        self.user_data = user_data
        
        self.name_label = tk.Label(self, text=f"Nombre: {user_data['username']}", bg="#eeeeee", font=("Arial", 12, "bold"))
        self.name_label.pack(anchor="w")
        
        self.id_label = tk.Label(self, text=f"User ID: {str(uuid.UUID(bytes=user_data['id']))}", bg="#eeeeee", font=("Arial", 10))
        self.id_label.pack(anchor="w")
        
        n_projects = len(dbcon.command("select", "projects", {"uid": user_data["id"]}))
        
        self.n_projects_label = tk.Label(self, text=f"Amount of projects: {n_projects}", bg="#eeeeee", font=("Arial", 10))
        self.n_projects_label.pack(anchor="w")
        
        self.role_label = tk.Label(self, text=f"Role: {user_data['role']}", bg="#eeeeee", font=("Arial", 10))
        self.role_label.pack(anchor="w")
        
        self.bind_all()
        
    def bind_all(self):
        self.bind("<Enter>", self._hover_on)
        self.bind("<Leave>", self._hover_off)
        self.bind("<Button-1>", self._on_click)
        for w in self.winfo_children():
            w.bind("<Enter>", self._hover_on)
            w.bind("<Leave>", self._hover_off)
            w.bind("<Button-1>", self._on_click)
            
    def _hover_on(self, event):
        self.configure(bg="#dddddd")
        for w in self.winfo_children():
            w.configure(bg="#dddddd")
            
    def _hover_off(self, event):
        self.configure(bg="#eeeeee")
        for w in self.winfo_children():
            w.configure(bg="#eeeeee")
            
    def _on_click(self, event):
        UserInfoDialog(self.parent, self.user_data)
        
class UserInfoDialog(tk.Toplevel):
    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.title("User Information")
        self.geometry("300x200")
        self.resizable(False, False)
        
        
        tk.Button(self, text="Close", command=self.destroy).pack(pady=10)
        
        
class UserListFrame(tk.Frame):
    def __init__(self, parent, switch_frame, usuario : User):
        super().__init__(parent)
        self.switch_frame = switch_frame
        self.user = usuario.to_dict()

        self.users = dbcon.command("select", "users", {"id": "*"})
        
        self.canvas = tk.Canvas(self, borderwidth=0, background="#f0f0f0")
        self.frame = tk.Frame(self.canvas, background="#f0f0f0")
        self.vsb = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.inner_window = self.canvas.create_window((0,0), window=self.frame, anchor="nw")
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.frame.bind("<Configure>", self.onFrameConfigure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)


        self.populate()
        
    def populate(self):
        for user in self.users:
            real_user = User(**user)
            if real_user.id == self.user["id"]:
                continue
            card = UserCard(self.frame, real_user.to_dict())
            card.pack(fill="x", pady=5, expand=True)
            
    def onFrameConfigure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def _on_canvas_configure(self, event):
        scrollbar_width = self.vsb.winfo_width()
        self.canvas.itemconfigure(
            self.inner_window,
            width=event.width - scrollbar_width
        )

