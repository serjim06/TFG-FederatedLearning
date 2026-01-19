from sqlite3 import DatabaseError
from tkinter import ttk
from tkinter import messagebox
import uuid
from src.models.node import Node
import src.db.dbcon as dbcon
import src.utils.icons.image_finder as image_finder
from src.gui.base_list import SEC_BTN_STYLE, BaseListFrame
from PIL import ImageTk, Image
from TkToolTip import ToolTip

class NodeListFrame(BaseListFrame):
    def __init__(self, parent, switch_frame, usuario):
            super().__init__(parent, switch_frame, usuario, columns={"id": 330, "valid": 55, "local_dataset_path": 600})

    def _insert_extra_buttons(self):
            self.user_group_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("user_group")).resize((24,24)))
           
            self.user_group_button = ttk.Button(self.toolbox, image=self.user_group_image, text="", compound="left",
                       command=self._user_management, width=2, style=SEC_BTN_STYLE)
            self.user_group_button.pack(side="left", padx=5, pady=5)
            
            ToolTip(self.user_group_button, text="Gestión de usuarios", delay=0.5)
            ToolTip(self.add_button, text="Agregar un nuevo nodo a la base de datos", delay=0.5)
            ToolTip(self.delete_button, text="Eliminar el nodo seleccionado de la base de datos", delay=0.5)        

    def _user_management(self):
        raise NotImplementedError()
    
    def _add_item(self):
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
    
    def _delete_item(self):
        seleccionado = self.tree.selection()
        canceled = []

        if seleccionado:
            for item in seleccionado:
                item_id = item
                if item_id in self.layers.values():
                    messagebox.showwarning("Advertencia", "No se pueden eliminar proyectos.")
                    canceled.append(item)
                    continue
                layer_id = self.tree.parent(item_id)
                if layer_id and not messagebox.askyesno("Confirmar Eliminación", f"El nodo con id {self.tree.item(item_id, 'values')[0]} pertenece a un proyecto activo de un usuario. ¿Estás seguro de que deseas eliminar este nodo?"):
                    canceled.append(item)
                    continue
                    
                values = self.tree.item(item_id, "values")
                node_id = uuid.UUID(values[0]).bytes
                
                try:
                    self._eliminate_dataset(node_id)
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo eliminar el dataset asociado al nodo: {e}")
                    canceled.append(item)
                    continue
            
                try:
                    dbcon.command("delete", "nodes", {"id": node_id})
                except (ValueError, DatabaseError) as e:
                    messagebox.showerror("Error", str(e))
                
            self._update_tree_after_delete(seleccionado, canceled)
        else:
            messagebox.showinfo("Información", "No hay ningún nodo seleccionado para eliminar.")
            
    def _initialize_tree(self):
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
                                                                                image=self.project_image, tags=('no-select',))

            local_dataset_path = self._parse_path(node_data["local_dataset_path"])
            self.tree.insert(self.layers[str(uuid.UUID(bytes=node_data["project_id"]))] if node_data["project_id"] else "",0, values=(
                    str(uuid.UUID(bytes=node_data["id"])),
                    node_data["valid"],
                    local_dataset_path
                ), image=self.node_image)

        self.tree.update_idletasks()
        
    def _select_item_changed(self, event):
        try:
            item_id = self.tree.selection()[0] 
        except IndexError:
            return

        tags = self.tree.item(item_id, 'tags')
        
        if 'no-select' in tags:
            self.tree.selection_remove(item_id)
            
            is_open = self.tree.item(item_id, 'open')
            self.tree.item(item_id, open=not is_open)
        else:
            self.delete_button.state(["!disabled"]) if self.tree.selection() else self.delete_button.state(["disabled"])