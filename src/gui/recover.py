import tkinter as tk
from tkinter import ttk, messagebox
import json

class RecoverFrame(tk.Frame):
    def __init__(self, parent, switch_frame):
        super().__init__(parent)
        self.configure(bg="#e0e0e0")  # fondo gris claro
        self.switch_frame = switch_frame

        # Estilo para botones
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"), foreground="#ffffff", background="#4a90e2")
        style.map("Accent.TButton",
                  background=[("active", "#357ABD")],
                  foreground=[("active", "#ffffff")])

        # Frame de contenido central
        self.content_frame = tk.Frame(self, bg="#e0e0e0")
        self.content_frame.pack(fill=tk.BOTH, expand=True, pady=40)

        # Encabezado
        ttk.Label(self.content_frame, text="Recuperar contraseña", font=("Segoe UI", 22, "bold"), background="#e0e0e0").pack(pady=(0, 30))

        # Paso 1: usuario o email
        self.user_label = ttk.Label(self.content_frame, text="Introduce tu usuario o email:", font=("Segoe UI", 12), background="#e0e0e0")
        self.user_label.pack(pady=5)
        self.user_entry = ttk.Entry(self.content_frame, font=("Segoe UI", 12))
        self.user_entry.pack(pady=5, ipadx=50, ipady=5)

        self.verify_button = ttk.Button(self.content_frame, text="Verificar usuario", style="Accent.TButton", command=self.verify_user)
        self.verify_button.pack(pady=20, ipadx=10, ipady=5)

        # Campos de nueva contraseña (ocultos hasta verificar)
        self.new_password_label = ttk.Label(self.content_frame, text="Nueva contraseña:", font=("Segoe UI", 12), background="#e0e0e0")
        self.new_password_entry = ttk.Entry(self.content_frame, show="*", font=("Segoe UI", 12))
        self.conf_new_password_label = ttk.Label(self.content_frame, text="Confirmar nueva contraseña:", font=("Segoe UI", 12), background="#e0e0e0")
        self.conf_new_password_entry = ttk.Entry(self.content_frame, show="*", font=("Segoe UI", 12))
        self.reset_button = ttk.Button(self.content_frame, text="Recuperar contraseña", style="Accent.TButton", command=self.reset_password)

        # Botón de volver siempre abajo
        self.back_button = ttk.Button(self, text="Volver", command=lambda: switch_frame("login"))
        self.back_button.pack(side=tk.BOTTOM, pady=20, ipadx=10, ipady=5)

    def verify_user(self):
        username = self.user_entry.get().strip()
        if not username:
            messagebox.showerror("Error", "Introduce un usuario o email")
            return

        # Comprobar si el usuario existe
        with open("../database/users.json", "r") as f:
            data = json.load(f)

        self.user_data = next((u for u in data if u["username"] == username), None)
        if not self.user_data:
            messagebox.showerror("Error", "Usuario no encontrado")
            return

        messagebox.showinfo("Usuario encontrado", f"Usuario {username} verificado")

        # Ocultar widgets del paso 1
        self.user_label.pack_forget()
        self.user_entry.pack_forget()
        self.verify_button.pack_forget()

        # Mostrar campos de nueva contraseña
        self.new_password_label.pack(pady=(10, 5))
        self.new_password_entry.pack(pady=5, ipadx=50, ipady=5)
        self.conf_new_password_label.pack(pady=(15, 5))
        self.conf_new_password_entry.pack(pady=5, ipadx=50, ipady=5)
        self.reset_button.pack(pady=20, ipadx=10, ipady=5)

    def reset_password(self):
        new_pass = self.new_password_entry.get()
        conf_pass = self.conf_new_password_entry.get()

        if not new_pass or not conf_pass:
            messagebox.showerror("Error", "Rellena todos los campos")
            return
        if new_pass != conf_pass:
            messagebox.showerror("Error", "Las contraseñas no coinciden")
            return

        # Actualizar en JSON
        with open("../database/users.json", "r") as f:
            data = json.load(f)
        for u in data:
            if u["username"] == self.user_data["username"]:
                u["password"] = new_pass
                break
        with open("../database/users.json", "w") as f:
            json.dump(data, f, indent=4)

        messagebox.showinfo("Éxito", "Contraseña actualizada correctamente")
        self.switch_frame("login")
