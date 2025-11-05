import tkinter as tk
from tkinter import ttk
import src.utils.utils as utils


class NodeListFrame(tk.Frame):
    def __init__(self, parent, switch_frame):
            super().__init__(parent)
            self.configure(bg="#eef4fb")  # fondo cohesivo
            self.switch_frame = switch_frame

            # ======= ESTILO GENERAL =======
            style = ttk.Style()
            style.theme_use("clam")

            style.configure("Treeview",
                            background="#ffffff",
                            foreground="#2b2b2b",
                            rowheight=26,
                            fieldbackground="#ffffff",
                            font=("Segoe UI", 11),
                            borderwidth=0)
            style.configure("Treeview.Heading",
                            background="#f3f6fa",
                            foreground="#444",
                            relief="flat",
                            font=("Segoe UI", 10))
            style.map("Treeview.Heading",
                      background=[("active", "#e5ebf3")])
            style.map("Treeview",
                      background=[("selected", "#e0e9f7")],
                      foreground=[("selected", "#000")])

            style.configure("Accent.TButton",
                            background="#0078d7",
                            foreground="white",
                            font=("Segoe UI", 10, "bold"),
                            padding=(10, 5))
            style.map("Accent.TButton",
                      background=[("active", "#005fa3")])

            style.configure("Sec.TButton",
                            background="#f2f2f2",
                            foreground="#333",
                            font=("Segoe UI", 10),
                            padding=(10, 5))
            style.map("Sec.TButton",
                      background=[("active", "#e0e0e0")])

            # ======= TÍTULO =======
            title = ttk.Label(self, text="Lista de Nodos", font=("Segoe UI", 22, "bold"),
                              background="#eef4fb", foreground="#2b2b2b")
            title.pack(pady=(20, 10))

            # ======= TABLA DE NODOS =======
            container = ttk.Frame(self)
            container.pack(fill="both", expand=True, padx=25, pady=10)

            scroll_y = ttk.Scrollbar(container, orient="vertical")
            scroll_x = ttk.Scrollbar(container, orient="horizontal")

            columnas = ("Node ID", "Valid", "Project ID", "Local Dataset Path")

            self.tree = ttk.Treeview(container,
                                     columns=columnas,
                                     show="headings",
                                     yscrollcommand=scroll_y.set,
                                     xscrollcommand=scroll_x.set)
            self.tree.grid(row=0, column=0, sticky="nsew")

            scroll_y.config(command=self.tree.yview)
            scroll_y.grid(row=0, column=1, sticky="ns")
            scroll_x.config(command=self.tree.xview)
            scroll_x.grid(row=1, column=0, sticky="ew")

            container.columnconfigure(0, weight=1)
            container.rowconfigure(0, weight=1)

            widths = [120, 80, 120, 300]
            for i, col in enumerate(columnas):
                self.tree.heading(col, text=col, anchor="w")
                self.tree.column(col, width=widths[i], anchor="w")


            # ======= PANEL INFERIOR =======
            bottom = tk.Frame(self, bg="#eef4fb")
            bottom.pack(pady=15)

            self.entries = {}
            for i, col in enumerate(columnas):
                ttk.Label(bottom, text=col, font=("Segoe UI", 10),
                          background="#eef4fb").grid(row=0, column=i, padx=5)
                entry = ttk.Entry(bottom, font=("Segoe UI", 10), width=18)
                entry.grid(row=1, column=i, padx=5, pady=5)
                self.entries[col] = entry

            # ======= BOTONES =======
            button_frame = tk.Frame(self, bg="#eef4fb")
            button_frame.pack(pady=10)

            ttk.Button(button_frame, text="Agregar Nodo",
                       style="Accent.TButton", command=self.agregar_nodo) \
                .grid(row=0, column=0, padx=5)
            ttk.Button(button_frame, text="Eliminar Seleccionado",
                       style="Sec.TButton", command=self.eliminar_nodo) \
                .grid(row=0, column=1, padx=5)
            ttk.Button(button_frame, text="Volver",
                       style="Sec.TButton",
                       command=lambda: self.switch_frame("dashboard")) \
                .grid(row=0, column=2, padx=5)

    def agregar_nodo(self):
        valores = [self.entries[col].get().strip() or "NULL" for col in self.entries]
        self.tree.insert("", tk.END, values=valores)
        for entry in self.entries.values():
            entry.delete(0, tk.END)

    def eliminar_nodo(self):
        seleccionado = self.tree.selection()
        for item in seleccionado:
            self.tree.delete(item)