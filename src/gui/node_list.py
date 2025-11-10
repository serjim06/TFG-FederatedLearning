import os
from sqlite3 import DatabaseError
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import uuid
import src.utils.utils as utils
from src.models.node import Node
import src.db.dbcon as dbcon
import src.utils.icons.image_finder as image_finder
from pathlib import Path
from PIL import ImageTk, Image
from TkToolTip import ToolTip

class NodeListFrame(tk.Frame):
    def __init__(self, parent, switch_frame):
            super().__init__(parent)
            self.configure(bg="#eef4fb")  # fondo cohesivo
            self.switch_frame = switch_frame

            # ======= ESTILO GENERAL =======
            style = utils.get_style()
            
            # ======= TÍTULO =======
            #title = ttk.Label(self, text="Lista de Nodos", font=("Segoe UI", 22, "bold"),
            #                  background="#eef4fb", foreground="#2b2b2b")
            #title.pack(pady=(20, 10))
            
            # ======= TOOLBOX =======
            toolbox = tk.Frame(self, bg="#eef4fb", relief="raised", bd=2)
            toolbox.pack(side="top", fill="x")
            
            self.add_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("add")).resize((24,24)))
            self.delete_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("delete")).resize((24,24)))

            self.add_button = ttk.Button(toolbox, image=self.add_image, text="", compound="left",
                       command=self._agregar_nodo, width=2, style="Sec.TButton")
            self.add_button.pack(side="left", padx=5, pady=5)
            self.delete_button = ttk.Button(toolbox, image=self.delete_image, text="", compound="left",
                       command=self._eliminar_nodo, width=2, style="Sec.TButton")
            self.delete_button.pack(side="left", padx=5, pady=5)
            self.delete_button.state(["disabled"])
            
            ToolTip(self.add_button, text="Agregar un nuevo nodo a la base de datos", delay=0.5)
            ToolTip(self.delete_button, text="Eliminar el nodo seleccionado de la base de datos", delay=0.5)

            # ======= TABLA DE NODOS =======
            container = ttk.Frame(self)
            container.pack(fill="both", expand=True, padx=25, pady=10)

            scroll_y = ttk.Scrollbar(container, orient="vertical")
            scroll_x = ttk.Scrollbar(container, orient="horizontal")

            columnas = ("ID", "Valid", "Local Dataset Path")

            self.tree = ttk.Treeview(container,
                                     columns=columnas,
                                     show=("tree","headings"),
                                     yscrollcommand=scroll_y.set,
                                     xscrollcommand=scroll_x.set,
                                     style="Treeview")
            self.tree.column("#0", width=100, stretch=tk.NO)
            self.tree.update_idletasks()
            self.tree.grid(row=0, column=0, sticky="nsew")
            
            self.tree.bind("<<TreeviewSelect>>", lambda event: 
                self.delete_button.state(["!disabled"]) if self.tree.selection() else self.delete_button.state(["disabled"]))

            scroll_y.config(command=self.tree.yview)
            scroll_y.grid(row=0, column=1, sticky="ns")
            scroll_x.config(command=self.tree.xview)
            scroll_x.grid(row=1, column=0, sticky="ew")

            container.columnconfigure(0, weight=1)
            container.rowconfigure(0, weight=1)
        

            widths = [330, 55, 600]
            for i, col in enumerate(columnas):
                self.tree.heading(col, text=col, anchor="w")
                self.tree.column(col, width=widths[i], anchor="w", stretch=tk.YES)

            # Cargar datos iniciales                
            self._initialize_node_list()

    
    def _agregar_nodo(self):
        try:
            node_data = dbcon.command("insert", "nodes", {"valid": 0, "project_id": "", "local_dataset_path": ""})
            
            node = Node(node_data[0], node_data[1], node_data[2])
            
            dbcon.command("update", "nodes", {"id":node.id, "local_dataset_path": node.local_dataset_path})
        except (ValueError, DatabaseError) as e:
            messagebox.showerror("Error", str(e))
            return
        
        self.tree.insert("", 0, values=(
            str(uuid.UUID(bytes=node.id)),
            node.valid,
            self._parse_path(node.local_dataset_path)
        ), image=self.node_image)
        self.tree.update_idletasks()
        messagebox.showinfo("Éxito", "Nodo agregado con éxito.")  
    
    
    

    def _eliminar_nodo(self):
        seleccionado = self.tree.selection()
        canceled = []
        if seleccionado:
            for item in seleccionado:
                item_id = item
                layer_id = self.tree.parent(item_id)
                if layer_id and not messagebox.askyesno("Confirmar Eliminación", f"El nodo con id {self.tree.item(item_id, 'values')[0]         } pertenece a un proyecto activo de un usuario. ¿Estás seguro de que deseas eliminar este nodo?"):
                    canceled.append(item)
                    continue
            
                values = self.tree.item(item_id, "values")
                node_id = uuid.UUID(values[0]).bytes
                try:
                    dbcon.command("delete", "nodes", {"id": node_id})
                except (ValueError, DatabaseError) as e:
                    messagebox.showerror("Error", str(e))
                    #return
                
            self._update_tree_after_delete(seleccionado, canceled)
        else:
            messagebox.showinfo("Información", "No hay ningún nodo seleccionado para eliminar.")
            
    def _initialize_node_list(self):
        try:
            nodes = dbcon.command("select", "nodes", {"id": "*"})
        except (ValueError, DatabaseError) as e:
            messagebox.showerror("Error", str(e))

        self.layers = {}

        n_img = Image.open(image_finder.find_image("node"))
        p_img = Image.open(image_finder.find_image("project"))

        self.project_image = ImageTk.PhotoImage(p_img)
        self.node_image = ImageTk.PhotoImage(n_img)

        for node_data in nodes:
            if node_data["project_id"] and str(uuid.UUID(bytes=node_data["project_id"])) not in self.layers:
                self.layers[str(uuid.UUID(bytes=node_data["project_id"]))] = self.tree.insert("", "end",
                                                                                text="Project:",
                                                                                values=(str(uuid.UUID(bytes=node_data["project_id"])), "", ""),
                                                                                image=self.project_image)

            local_dataset_path = self._parse_path(node_data["local_dataset_path"])
            self.tree.insert(self.layers[str(uuid.UUID(bytes=node_data["project_id"]))] if node_data["project_id"] else "",0, values=(
                    str(uuid.UUID(bytes=node_data["id"])),
                    node_data["valid"],
                    local_dataset_path
                ), image=self.node_image)

        self.tree.update_idletasks()
            
    def _update_tree_after_delete(self, seleccionado, canceled):
        for item in seleccionado:
                if item in canceled:
                    continue
                layer_id = self.tree.parent(item)
                self.tree.delete(item)
                if layer_id and len(self.tree.get_children(layer_id)) == 0:
                    self.tree.delete(layer_id)
                    
    def _parse_path(self, path: str) -> str:
        # Normaliza el path del dataset local
        normalized_path = Path(path).resolve()
        path = str(normalized_path)
        indice_dataset = path.index("database/")
        path = path[indice_dataset:]
        path = "./" + path
        return path