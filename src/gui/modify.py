import tkinter as tk
from tkinter import ttk, messagebox
from src.db import dbcon
from src.utils.user import User


class ModifyPanel(tk.Frame):
    def __init__(self, parent, switch_frame, usuario):
        super().__init__(parent)
        self.configure(bg="#eef4fb")  # fondo gris suave
        self.switch_frame = switch_frame
        self.usuario = usuario

        self.columnconfigure(0, weight=1)

        # ----- Estilos -----
        style = ttk.Style()
        style.theme_use("clam")

        # Botón principal (azul brillante)
        style.configure(
            "Accent.TButton",
            font=("Segoe UI", 11, "bold"),
            foreground="#ffffff",
            background="#4a90e2",
            padding=6,
            borderwidth=0
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#357ABD"), ("pressed", "#2c5a92")],
            foreground=[("active", "#ffffff")]
        )

        style.configure(
            "Sec.TButton",
            foreground="#000000",
            background="#e0e4eb",
            padding=6,
            borderwidth=0
        )

        style.map("Sec.TButton",
                  background=[("active", "#d3d7df"),
                              ("pressed", "#c7cbd5")],
                  foreground=[("active", "black"),
                              ("pressed", "white")])

        # Entradas (campos de texto)
        style.configure(
            "Custom.TEntry",
            fieldbackground="#ffffff",
            background="#ffffff",
            foreground="#1d2d44",
            bordercolor="#d9d9d9",
            relief="flat",
            insertcolor="#1d2d44"
        )

        # Texto general
        label_font = ("Segoe UI", 17)
        title_font = ("Segoe UI", 22, "bold")

        # Encabezado
        ttk.Label(self, text="Modificar Perfil", font=title_font, background="#eef4fb").grid(
            row=0, column=0, pady=20)

        tk.Label(self, text="Usuario:", font=label_font, background="#eef4fb").grid(
            row=1, column=0, padx=5, pady=5)
        self.user_entry = ttk.Entry(self, style="Custom.TEntry", font=("Segoe UI", 12), width=20)
        self.user_entry.insert(0, self.usuario['username'])
        self.user_entry.grid(row=2, column=0, padx=5, pady=5)


        ttk.Label(self, text="Contraseña:", font=label_font, background="#eef4fb").grid(
            row=3, column=0, padx=5, pady=5)

        pw_frame = tk.Frame(self, background="#eef4fb")
        pw_frame.grid(row=4, column=0, pady=5)

        # Entry de contraseña
        self.password_entry = ttk.Entry(pw_frame, show="*", style="Custom.TEntry", font=("Segoe UI", 12), width=20)
        self.password_entry.insert(0, self.usuario['password'])
        self.password_entry.pack(side="left", fill="x", expand=True)

        # Botón del ojo
        self.show_pw = False
        self.eye_button = tk.Label(pw_frame, text="👁", bg="#ffffff", cursor="hand2")
        self.eye_button.place(relx=1.0, rely=0.5, x=-5, y=0, anchor="e")
        self.eye_button.bind("<Button-1>", lambda e: self.toggle_password())

        # Botón Entrar
        ttk.Button(self, text="Confirmar cambios", style="Accent.TButton", command=self.modify).grid(row=5,column=0,pady=20, ipadx=10, ipady=5)

        ttk.Button(self, text="Volver", style="Sec.TButton", command=lambda: self.switch_frame("profile",self.usuario)).grid(row=6,column=0, pady=(5, 10))

    def toggle_password(self):
        """Muestra o oculta la contraseña"""
        if self.show_pw:
            self.password_entry.config(show="*")
            self.show_pw = False
        else:
            self.password_entry.config(show="")
            self.show_pw = True


    def modify(self):
        user = self.user_entry.get()
        passwd = self.password_entry.get()

        usuario = {
            "id": self.usuario['id']
        }

        new_user = User(self.usuario['id'], self.usuario['username'], self.usuario['password'], self.usuario['role'])

        if not user and not passwd:
            self.switch_frame("profile",self.usuario)

        if user != self.usuario['username']:
            usuario['username'] = user
            new_user['username'] = user

        if passwd != self.usuario['password']:
            usuario['password'] = passwd
            new_user['password'] = passwd

        try:
            if dbcon.update("users", usuario):
                messagebox.showinfo("Success", "Los datos se han modificado correctamente")

                self.switch_frame("modified_profile", new_user)

        except Exception as e:
            messagebox.showerror("Error", str(e))
            return