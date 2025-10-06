import tkinter as tk
from tkinter import ttk

class LoginPanel(tk.Frame):
    def __init__(self, parent, switch_frame):
        super().__init__(parent)
        self.configure(bg="#f4f4f4")

        ttk.Label(self, text="Iniciar Sesión", font=("Segoe UI", 20, "bold")).pack(pady=20)
        #Usuario
        ttk.Label(self, text="Usuario:").pack()
        self.user_entry = ttk.Entry(self)
        self.user_entry.pack(pady=5)
        #Contraseña
        ttk.Label(self, text="Contraseña:").pack()
        self.password_entry = ttk.Entry(self, show="*")
        self.password_entry.pack(pady=5)

        ttk.Button(self, text="Entrar").pack(pady=15)
        ttk.Button(self, text="No tengo cuenta", command=lambda: switch_frame("register")).pack()
        ttk.Button(self, text="Olvidé mi contraseña", command= switch_frame("recover")).pack()
