import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import uuid

from src.db import dbcon
from src.utils.icons import image_finder
from src.utils.user import User
from src.utils import utils
from src.gui.user_info import UserInfoDialog

class UserListFrame(tk.Frame):
    def __init__(self, parent, switch_frame, usuario : User):
        super().__init__(parent)
        self.switch_frame = switch_frame
        self.user = usuario.to_dict()
        
        self._setup_toolbox()
        
        self.canvas = tk.Canvas(self, borderwidth=0, background=utils.BG_COLOR)
        self.frame = tk.Frame(self.canvas, background=utils.BG_COLOR)
        self.vsb = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.inner_window = self.canvas.create_window((0,0), window=self.frame, anchor="nw")
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.frame.bind("<Configure>", self.onFrameConfigure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)


        self.populate()
        
    def _setup_toolbox(self):
        self.toolbox = tk.Frame(self, bg=utils.BG_COLOR, relief="raised", bd=2)
        self.toolbox.pack(side="top", fill="x")
        
        self.return_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("return")).resize((24,24)))

        self.return_button = ttk.Button(self.toolbox, image=self.return_image, text="", compound="left",
                       command=self._return, width=2, style=utils.SEC_TBUTTON_STYLE)
        self.return_button.pack(side="left", padx=5, pady=5)
        
    def _return(self):
        self.switch_frame("dashboard")    
    
    def populate(self):
        self.clear_users()
        self.users = dbcon.command("select", "users", {"id": "*"})
        for user in self.users:
            real_user = User(**user)
            if real_user.id == self.user["id"]:
                continue
            card = UserCard(self.frame, real_user.to_dict(), self)
            card.pack(fill="x", pady=5, expand=True)
            
            
    def clear_users(self):
        for w in self.frame.winfo_children():
            w.destroy()
        
    def onFrameConfigure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def _on_canvas_configure(self, event):
        scrollbar_width = self.vsb.winfo_width()
        self.canvas.itemconfigure(
            self.inner_window,
            width=event.width - scrollbar_width
        )

class UserCard(tk.Frame):
    def __init__(self, parent : UserListFrame, user_data, user_list_frame):
        super().__init__(parent, bg=utils.BG_COLOR, bd=1, relief="solid", padx=10, pady=10)
        
        self.user_list_frame = user_list_frame
        
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
        self.configure(bg=utils.BG_COLOR)
        for w in self.winfo_children():
            w.configure(bg=utils.BG_COLOR)
            
    def _on_click(self, event):
        UserInfoDialog(self.user_list_frame, self.user_data)
    
        

