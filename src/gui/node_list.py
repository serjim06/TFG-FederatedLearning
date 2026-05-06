from sqlite3 import DatabaseError
from tkinter import ttk
from src.gui import dialogs
import uuid
import src.utils.icons.image_finder as image_finder
from src.gui.base_list import SEC_BTN_STYLE, BaseListFrame
from PIL import ImageTk, Image
from TkToolTip import ToolTip
from src.application.use_cases.manage_nodes import ManageNodesUseCase
from src.infrastructure.repositories.sqlite_node_repository import SQLiteNodeRepository

class NodeListFrame(BaseListFrame):
    def __init__(self, parent, switch_frame, usuario):
            self._manage_nodes_use_case = ManageNodesUseCase(SQLiteNodeRepository())
            super().__init__(parent, switch_frame, usuario, columns={"id": 330, "valid": 55, "local_dataset_path": 600})

    def _insert_extra_buttons(self):
            self.user_group_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("user_group")).resize((24,24)))
           
            self.user_group_button = ttk.Button(self.toolbox, image=self.user_group_image, text="", compound="left",
                       command=self._user_management, width=2, style=SEC_BTN_STYLE)
            self.user_group_button.pack(side="left", padx=5, pady=5, before=self.buttons[1])
            self.buttons.insert(1, self.user_group_button)
            
            ToolTip(self.user_group_button, text="Gestión de usuarios", delay=0.5)
            ToolTip(self.add_button, text="Agregar un nuevo nodo a la base de datos", delay=0.5)
            ToolTip(self.delete_button, text="Eliminar el nodo seleccionado de la base de datos", delay=0.5)        

    def _user_management(self):
        self.switch_frame("user_management")
    
    def _add_item(self):
        try:
            result = self._manage_nodes_use_case.create()
            if not result.ok:
                dialogs.InfoDialog(self, "Error", result.error or "No se pudo crear el nodo", "error")
                return
            node_data = result.data
        except (ValueError, DatabaseError) as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")
            return
        
        self.tree.insert("", 0, values=(
            str(uuid.UUID(bytes=node_data["id"])),
            node_data["valid"],
            self._parse_path(node_data["local_dataset_path"])
        ), image=self.node_image)
        self.tree.update_idletasks()
        dialogs.InfoDialog(self, "Éxito", "Nodo agregado con éxito.", "info")  
    
    def _delete_item(self):
        seleccionado = self.tree.selection()
        canceled = []

        if seleccionado:
            for item in seleccionado:
                item_id = item
                if item_id in self.layers.values():
                    dialogs.InfoDialog(self, "Advertencia", "No se pueden eliminar proyectos.", "warning")
                    canceled.append(item)
                    continue
                layer_id = self.tree.parent(item_id)
                if layer_id and not dialogs.OptionDialog.ask(self, "Confirmar Eliminación", f"El nodo con id {self.tree.item(item_id, 'values')[0]} pertenece a un proyecto activo de un usuario. ¿Estás seguro de que deseas eliminar este nodo?"):
                    canceled.append(item)
                    continue
                    
                values = self.tree.item(item_id, "values")
                node_id = uuid.UUID(values[0]).bytes
                
                try:
                    result = self._manage_nodes_use_case.delete(node_id)
                    if not result.ok:
                        dialogs.InfoDialog(self, "Error", result.error or "No se pudo eliminar el nodo", "error")
                        canceled.append(item)
                except (ValueError, DatabaseError) as e:
                    dialogs.InfoDialog(self, "Error", str(e), "error")
                    canceled.append(item)
                
            self._update_tree_after_delete(seleccionado, canceled)
        else:
            dialogs.InfoDialog(self, "Información", "No hay ningún nodo seleccionado para eliminar.", "info")
            
    def _initialize_tree(self):
        try:
            result = self._manage_nodes_use_case.list_all()
            if not result.ok:
                dialogs.InfoDialog(self, "Error", result.error or "No se pudieron cargar nodos", "error")
                return
            nodes = result.data
        except (ValueError, DatabaseError) as e:
            dialogs.InfoDialog(self, "Error", str(e), "error")

        self.layers = {}

        n_img = Image.open(image_finder.find_image("node")).resize((16, 16))
        p_img = Image.open(image_finder.find_image("project")).resize((16, 16))

        self.project_image = ImageTk.PhotoImage(p_img)
        self.node_image = ImageTk.PhotoImage(n_img)

        for node_data in nodes:
            if node_data["valid"] == 1 and node_data["project_id"] and str(uuid.UUID(bytes=node_data["project_id"])) not in self.layers:
                self.layers[str(uuid.UUID(bytes=node_data["project_id"]))] = self.tree.insert("", "end",
                                                                                text="Project:",
                                                                                values=(str(uuid.UUID(bytes=node_data["project_id"])), "", ""),
                                                                                image=self.project_image, tags=('no-select',))

            local_dataset_path = self._parse_path(node_data["local_dataset_path"])
            self.tree.insert(self.layers[str(uuid.UUID(bytes=node_data["project_id"]))] if node_data["valid"] == 1 else "",0, values=(
                    str(uuid.UUID(bytes=node_data["id"])),
                    node_data["valid"],
                    local_dataset_path
                ), image=self.node_image)

        self.tree.update_idletasks()
        
    def _selected_item_changed(self):
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