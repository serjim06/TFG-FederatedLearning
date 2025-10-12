import tkinter as tk
from tkinter import ttk, messagebox
from src.db import dbcon
from src.utils.user import User


class ModifyPanel(tk.Frame):
    def __init__(self, parent, switch_frame, usuario):
        super().__init__(parent)
        self.configure(bg="#e0e0e0")  # fondo gris suave
        self.switch_frame = switch_frame
        self.usuario = usuario

        self.columnconfigure(0, weight=1)

        # Estilo de botones
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"), foreground="#ffffff", background="#4a90e2")
        style.map("Accent.TButton",
                  background=[("active", "#357ABD")],
                  foreground=[("active", "#ffffff")])

        # Encabezado
        ttk.Label(self, text="Modificar Perfil", font=("Segoe UI", 22, "bold"), background="#e0e0e0").grid(
            row=0, column=0, pady=20)

        tk.Label(self, text="Usuario:", font=("Segoe UI", 17), background="#e0e0e0").grid(
            row=1, column=0, padx=5, pady=5)
        self.user_entry = tk.Entry(self, font=("Segoe UI", 12), width=20)
        self.user_entry.insert(0, self.usuario['username'])
        self.user_entry.grid(row=2, column=0, padx=5, pady=5)


        ttk.Label(self, text="Contraseña:", font=("Segoe UI", 17), background="#e0e0e0").grid(
            row=3, column=0, padx=5, pady=5)

        pw_frame = tk.Frame(self, background="#e0e0e0")
        pw_frame.grid(row=4, column=0, pady=5)

        # Entry de contraseña
        self.password_entry = ttk.Entry(pw_frame, show="*", font=("Segoe UI", 12), width=20)
        self.password_entry.insert(0, self.usuario['password'])
        self.password_entry.pack(side="left", fill="x", expand=True)

        # Botón del ojo usando place
        self.show_pw = False
        #self.eye_button = tk.Button(pw_frame, text="👁", bd=0, bg="#ffffff", cursor="hand2",
        #                            activebackground="#e0e0e0", command=self.toggle_password)
        # Colocamos el botón dentro del Entry, alineado a la derecha
        #self.eye_button.place(relx=1.0, rely=0.5, y=0, anchor="e")

        self.eye_button = tk.Label(pw_frame, text="👁", bg="#ffffff", cursor="hand2")
        self.eye_button.place(relx=1.0, rely=0.5, x=-5, y=0, anchor="e")
        self.eye_button.bind("<Button-1>", lambda e: self.toggle_password())

        # Botón Entrar
        ttk.Button(self, text="Confirmar cambios", style="Accent.TButton", command=self.modify).grid(row=5,column=0,pady=20, ipadx=10, ipady=5)

        ttk.Button(self, text="Volver", command=lambda: self.switch_frame("profile",self.usuario)).grid(row=6,column=0, pady=30, ipadx=15, ipady=5)

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