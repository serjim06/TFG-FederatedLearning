import json
from sqlite3 import DatabaseError
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import uuid
import src.db.dbcon as dbcon
import src.utils.icons.image_finder as image_finder
from PIL import ImageTk, Image
from TkToolTip import ToolTip
from src.gui.new_project import NewProjectDialog
from src.gui.base_list import SEC_BTN_STYLE, BaseListFrame


class ProjectListFrame(BaseListFrame):
    def __init__(self, parent, switch_frame, usuario):
            super().__init__(parent, switch_frame, usuario, columns={"id": 330, "name": 55, "description": 600})
    
    def _insert_extra_buttons(self):
            #TODO IMAGENES: VER?!?!?!?!
            self.config_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("settings")).resize((24,24)))
            self.play_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("play")).resize((24,24)))
            
            self.play_button = ttk.Button(self.toolbox, image=self.play_image, text="", compound="left",
                       command=lambda e: print("no implementado"), width=2, style=SEC_BTN_STYLE)
            self.play_button.pack(side="left", padx=5, pady=5)
            self.play_button.state(["disabled"])
            
            self.config_button = ttk.Button(self.toolbox, image=self.config_image, text="", compound="left",
                       command=lambda e: print("no implementado"), width=2, style="Sec.TButton")
            self.config_button.pack(side="left", padx=5, pady=5)
            self.config_button.state(["disabled"])
        
            ToolTip(self.add_button, text="Crear un proyecto nuevo", delay=0.5)
            ToolTip(self.delete_button, text="Eliminar proyecto seleccionado", delay=0.5)
            ToolTip(self.play_button, text="Realizar una predicción en el proyecto seleccionado", delay=0.5)
            ToolTip(self.config_button, text="Configurar el proyecto seleccionado", delay=0.5)
       
    def _selected_item_changed(self):
        super()._selected_item_changed()
        self.config_button.state(["!disabled"]) if self.tree.selection() else self.config_button.state(["disabled"])
        self.play_button.state(["!disabled"]) if self.tree.selection() else self.play_button.state(["disabled"])
    
    def _add_item(self):
        try: 
            NewProjectDialog(self, self.usuario["id"])
        except (ValueError, DatabaseError) as e:
            messagebox.showerror("Error", str(e))
            return
    
    def _delete_item(self):
        seleccionado = self.tree.selection()
        canceled = []

        if seleccionado:
            for item in seleccionado:
                item_id = item
                
                if not messagebox.askyesno("Confirmar eliminación", "¿Estás seguro de que deseas eliminar el proyecto seleccionado? Esta acción no se puede deshacer."):
                    canceled.append(item)
                    continue
                
                values = self.tree.item(item_id, "values")
                project_id = uuid.UUID(values[0]).bytes
                
                try:
                    self._invalidate_nodes(project_id)
                    
                    dbcon.command("delete", "projects", {"id": project_id})
                except (ValueError, DatabaseError) as e:
                    messagebox.showerror("Error", str(e))
                    #return
                
            self._update_tree_after_delete(seleccionado, canceled)
            messagebox.showinfo("Información", "Proyecto(s) eliminado(s) correctamente.")
        else:
            messagebox.showinfo("Información", "No hay ningún nodo seleccionado para eliminar.")

    def _invalidate_nodes(self, project_id):
        """
        Invalidates nodes associated with a project and removes their datasets, as they are unlikely to be used anymore.
        
        Args:
            project_id (bytes): The id of the project whose nodes are to be invalidated.
        """
        
        project_data = dbcon.command("select", "projects", {"id": project_id}) 
                    
        if project_data:
            project_nodes = json.loads(project_data[0]["nodes"])
                        
            for node_id in project_nodes:
                self._eliminate_dataset(uuid.UUID(node_id).bytes)
                            
                try:
                    dbcon.command("update", "nodes", {"id": uuid.UUID(node_id).bytes, "valid": 0})
                except (ValueError, DatabaseError) as e:
                    messagebox.showerror("Error", str(e))
                    
    
    def _initialize_tree(self):
        self.tree.delete(*self.tree.get_children())
        
        try:
            projects = dbcon.command("select", "projects", {"uid": self.usuario['id']})
        except (ValueError, DatabaseError) as e:
            messagebox.showerror("Error", str(e))

        self.layers = {}

        p_img = Image.open(image_finder.find_image("project"))

        self.project_image = ImageTk.PhotoImage(p_img)

        for project_data in projects:
            if str(uuid.UUID(bytes=project_data["id"])) not in self.layers:
                self.layers[str(uuid.UUID(bytes=project_data["id"]))] = self.tree.insert("", "end",
                                                                                text="Project:",
                                                                                values=(str(uuid.UUID(bytes=project_data["id"])), project_data["name"], project_data["description"]),
                                                                                image=self.project_image)
        self.tree.update_idletasks()
