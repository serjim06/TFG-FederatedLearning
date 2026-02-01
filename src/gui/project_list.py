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
from src.gui.new_project import NewProjectDialog, SeeProjectDialog
from src.gui.base_list import SEC_BTN_STYLE, BaseListFrame
from collections import Counter
from math import sqrt

class ProjectListFrame(BaseListFrame):
    def __init__(self, parent, switch_frame, usuario):
            super().__init__(parent, switch_frame, usuario, columns={"id": 330, "name": 55, "description": 600})
            
            self.winfo_toplevel().bind("<Configure>", self._reposition_suggestions)
    
    def _insert_extra_buttons(self):
            self.config_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("settings")).resize((24,24)))
            self.play_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("play")).resize((24,24)))
            
            self.play_button = ttk.Button(self.toolbox, image=self.play_image, text="", compound="left",
                       command=lambda e: print("no implementado"), width=2, style=SEC_BTN_STYLE)
            self.play_button.pack(side="left", padx=5, pady=5)
            self.play_button.state(["disabled"])
            
            self.config_button = ttk.Button(self.toolbox, image=self.config_image, text="", compound="left",
                       command=self._config_project, width=2, style="Sec.TButton")
            self.config_button.pack(side="left", padx=5, pady=5)
            self.config_button.state(["disabled"])
        
            ToolTip(self.add_button, text="Crear un proyecto nuevo", delay=0.5)
            ToolTip(self.delete_button, text="Eliminar proyecto seleccionado", delay=0.5)
            ToolTip(self.play_button, text="Realizar una predicción en el proyecto seleccionado", delay=0.5)
            ToolTip(self.config_button, text="Configurar el proyecto seleccionado", delay=0.5)
            
            self._insert_search_bar()
       
    def _insert_search_bar(self):
        self.search_var = tk.StringVar()
        
        search_frame = ttk.Frame(self.toolbox)
        search_frame.pack(side="right", padx=5, pady=5)
        
        entry_frame = ttk.Frame(search_frame)
        entry_frame.pack(side="left")
        
        self.search_entry = ttk.Entry(entry_frame, textvariable=self.search_var, width=20)
        self.search_entry.pack()
        
        self.search_var.trace("w", self._update_suggestions)
        self.search_entry.bind("<FocusOut>", self._hide_suggestions)
        self.search_entry.bind("<Return>", lambda event: self._perform_search())
                    
        search_button = ttk.Button(search_frame, text="Buscar", command=self._perform_search, width=6, style=SEC_BTN_STYLE)
        search_button.pack(side="right", padx=5)
        
        self._create_suggestion_popup()
       
    def _create_suggestion_popup(self):
        self.suggestion_popup = tk.Toplevel(self)
        self.suggestion_popup.withdraw()
        self.suggestion_popup.overrideredirect(True)  # sin bordes
        self.suggestion_popup.attributes("-topmost", True)

        self.suggestion_list = tk.Listbox(
            self.suggestion_popup,
            height=4,
            borderwidth=1,
            relief="solid"
        )
        self.suggestion_list.pack(fill="both", expand=True)
        
        self.suggestion_list.bind("<<ListboxSelect>>", self._select_suggestion)
    
    def _hide_suggestions(self, event=None):
        self.suggestion_popup.withdraw()
    
    def _show_suggestions(self):
        if not self.suggestion_list.size():
            self.suggestion_popup.withdraw()
            return

        x = self.search_entry.winfo_rootx()
        y = self.search_entry.winfo_rooty() + self.search_entry.winfo_height()
        w = self.search_entry.winfo_width()

        self.suggestion_popup.geometry(f"{w}x80+{x}+{y}")
        self.suggestion_popup.deiconify()
        
    def _update_suggestions(self, *args):
        search_term = self.search_var.get().lower()
        if not search_term:
            self._hide_suggestions()
            return
        suggestions = self._get_suggestions_vector(search_term)
        
        self.suggestion_list.delete(0, tk.END)
        
        for s in suggestions:
            self.suggestion_list.insert(tk.END, s)
            
        self._show_suggestions()
    
    def _select_suggestion(self, event):
        selected_suggestion = self.suggestion_list.get(self.suggestion_list.curselection())
        self.search_var.set(selected_suggestion)
        self._perform_search()
        
    def _perform_search(self):
        search_term = self.search_var.get()
        
        if not search_term:
            return
        
        projects = []

        for item_id in self.tree.get_children():    
            values = self.tree.item(item_id, "values")

            project = {
                "id": uuid.UUID(values[0]).bytes,
                "name": values[1],
                "description": values[2],
            }
            projects.append(project)

        if not projects:
            return

        self.tree.delete(*self.tree.get_children()) #Elimina los proyectos insertados
        
        suggestions = []
        
        v1 = self.word2vec(search_term)
        
        for project in projects:
            v2 = self.word2vec(project["name"])
            
            similarity = self.cosdis(v1, v2)
            
            suggestions.append((project, similarity))
        
        sorted_suggestions = sorted(suggestions, reverse = True, key=lambda suggestion: suggestion[1]) #orders by similarity
        
        projects_ordered = [sugg[0] for sugg in sorted_suggestions]
        
        self._insert_tree(projects_ordered)
        self._hide_suggestions()
        
    
    def _reposition_suggestions(self, event=None):
        if not self.suggestion_popup.winfo_viewable():
            return

        x = self.search_entry.winfo_rootx()
        y = self.search_entry.winfo_rooty() + self.search_entry.winfo_height()
        w = self.search_entry.winfo_width()

        self.suggestion_popup.geometry(f"{w}x80+{x}+{y}")
        
    def word2vec(self, word):
        cw = Counter(word)
        sw = set(cw)
        lw = sqrt(sum(c*c for c in cw.values()))

        return cw, sw, lw
    
    def _get_suggestions_vector(self, search_term, max_suggestions=5):
        
        names = [name.lower() for name in self.project_names]
        
        suggestions = []
        
        v1 = self.word2vec(search_term)
        
        for word in names:
            v2 = self.word2vec(word)
            
            similarity = self.cosdis(v1, v2)
            
            if word not in suggestions:
                suggestions.append((word, similarity))
        
        sorted_suggestions = sorted(suggestions, reverse = True, key=lambda suggestion: suggestion[1]) #orders by similarity
            
        return [suggestion[0] for suggestion in sorted_suggestions[:max_suggestions]]

    def cosdis(self, v1, v2):
        # which characters are common to the two words?
        common = v1[1].intersection(v2[1])
        # by definition of cosine distance we have
        return sum(v1[0][ch]*v2[0][ch] for ch in common)/v1[2]/v2[2]
       
       
    def _selected_item_changed(self):
        super()._selected_item_changed()
        self.config_button.state(["!disabled"]) if self.tree.selection() else self.config_button.state(["disabled"])
        self.play_button.state(["!disabled"]) if self.tree.selection() else self.play_button.state(["disabled"])
    
    def _config_project(self):
        seleccionado = self.tree.selection()
        
        if seleccionado:
            item_id = seleccionado[0]
            values = self.tree.item(item_id, "values") 
            project_id = uuid.UUID(values[0]).bytes
            
            try:
                project_data = dbcon.command("select", "projects", {"id": project_id})
                if project_data:
                    SeeProjectDialog(self, project_id)
            except (ValueError, DatabaseError) as e:
                messagebox.showerror("Error", str(e))
        else:
            messagebox.showinfo("Información", "No hay ningún proyecto seleccionado para configurar.")
    
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

        self.project_names = [project_data["name"] for project_data in projects]

        self._insert_tree(projects)

    def _insert_tree(self, projects):
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