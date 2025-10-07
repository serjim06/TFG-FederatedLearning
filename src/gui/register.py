import tkinter as tk
from tkinter import ttk, messagebox
import uuid
import json



class RegisterFrame(tk.Frame):
    def __init__(self, parent, switch_frame):
        super().__init__(parent)
        self.switch_frame = switch_frame
        self.configure(bg="#e0e0e0")  # mismo fondo que LoginPanel

        # Estilo de botones principal
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"), foreground="#ffffff", background="#4a90e2")
        style.map("Accent.TButton",
                  background=[("active", "#357ABD")],
                  foreground=[("active", "#ffffff")])

        # Encabezado
        ttk.Label(self, text="Crear Cuenta", font=("Segoe UI", 22, "bold"), background="#e0e0e0").pack(pady=5)

        # Usuario
        ttk.Label(self, text="Usuario:", font=("Segoe UI", 12), background="#e0e0e0").pack(pady=(5, 0))
        self.user_entry = ttk.Entry(self, font=("Segoe UI", 12))
        self.user_entry.pack(pady=5, ipadx=50, ipady=5)

        # Contraseña
        ttk.Label(self, text="Contraseña:", font=("Segoe UI", 12), background="#e0e0e0").pack(pady=(10, 0))
        self.pass_entry = ttk.Entry(self, show="*", font=("Segoe UI", 12))
        self.pass_entry.pack(pady=5, ipadx=50, ipady=5)

        # Confirmar contraseña
        ttk.Label(self, text="Confirmar Contraseña:", font=("Segoe UI", 12), background="#e0e0e0").pack(pady=(10, 0))
        self.conf_entry = ttk.Entry(self, show="*", font=("Segoe UI", 12))
        self.conf_entry.pack(pady=5, ipadx=50, ipady=5)

        # Botón principal
        ttk.Button(self, text="Registrar", style="Accent.TButton", command=self.register).pack(pady=20, ipadx=10, ipady=5)

        # Botón secundario
        ttk.Button(self, text="Volver", command=lambda: switch_frame("login")).pack(pady=(5, 10))

    def register(self):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get()
        confirm = self.conf_entry.get()

        if not username or not password or not confirm:
            messagebox.showerror("Error", "Rellena todos los campos")
            return

        if password != confirm:
            messagebox.showerror("Error", "Las contraseñas no coinciden")
            return

        with open("../database/users.json") as users:
            data = json.load(users)

            if any(u["username"] == username for u in data):
                messagebox.showerror("Error", "Usuario ya existente")
                return

            id = str(uuid.uuid4())
            data.append({
                "id": id,
                "username": username,
                "password": password,
                "role": "user",
                "projects": []
            })
        with open("../database/users.json", "w") as users:
            json.dump(data, users, indent=4)

        messagebox.showinfo("Éxito", "El usuario se ha registrado correctamente")
        self.switch_frame("login")
