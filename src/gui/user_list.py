import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import uuid

from src.application.use_cases.list_managed_users import ListManagedUsersUseCase
from src.infrastructure.repositories.sqlite_project_repository import SQLiteProjectRepository
from src.infrastructure.repositories.sqlite_user_repository import SQLiteUserRepository
from src.utils.icons import image_finder
from src.utils.user import User
from src.utils import utils
from src.gui.user_info import UserInfoDialog

class UserListFrame(tk.Frame):
    def __init__(self, parent, switch_frame, usuario : User):
        super().__init__(parent)
        self.switch_frame = switch_frame
        self.user = usuario.to_dict()
        self._list_managed_users_use_case = ListManagedUsersUseCase(
            SQLiteUserRepository(),
            SQLiteProjectRepository(),
        )
        
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
        result = self._list_managed_users_use_case.execute(self.user["id"])
        users = result.data or []
        for user in users:
            real_user = User(
                id=user["id"],
                username=user["username"],
                role=user["role"],
                password_hash=user.get("password_hash"),
                recovery_phrase_hash=user.get("recovery_phrase_hash"),
                creation_date=user.get("creation_date"),
                last_login=user.get("last_login"),
                last_train=user.get("last_train"),
            )
            payload = real_user.to_dict()
            payload["project_count"] = user["project_count"]
            card = UserCard(self.frame, payload, self)
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
        
        n_projects = user_data.get("project_count", 0)
        
        self.n_projects_label = tk.Label(self, text=f"Amount of projects: {n_projects}", bg="#eeeeee", font=("Arial", 10))
        self.n_projects_label.pack(anchor="w")
        
        self.role_label = tk.Label(self, text=f"Role: {user_data['role']}", bg="#eeeeee", font=("Arial", 10))
        self.role_label.pack(anchor="w")

        self.creation_date_label = tk.Label(
            self,
            text=f"Creation date: {user_data.get('creation_date') or '-'}",
            bg="#eeeeee",
            font=("Arial", 10),
        )
        self.creation_date_label.pack(anchor="w")

        self.last_login_label = tk.Label(
            self,
            text=f"Last login: {user_data.get('last_login') or '-'}",
            bg="#eeeeee",
            font=("Arial", 10),
        )
        self.last_login_label.pack(anchor="w")

        self.last_train_label = tk.Label(
            self,
            text=f"Last train: {user_data.get('last_train') or '-'}",
            bg="#eeeeee",
            font=("Arial", 10),
        )
        self.last_train_label.pack(anchor="w")
        
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
    
        

