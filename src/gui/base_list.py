import os
from pathlib import Path
import shutil
import tkinter as tk
import tkinter.ttk as ttk
import uuid
from PIL import Image, ImageTk
from abc import ABC, abstractmethod
from TkToolTip import ToolTip

from src.utils import utils
from src.utils.icons import image_finder


SEC_BTN_STYLE = "Sec.TButton"

class BaseListFrame(tk.Frame, ABC):
    def __init__(self, parent, switch_frame, usuario, columns: dict[str, int]):
        super().__init__(parent)
        self.switch_frame = switch_frame
        self.usuario = usuario
        self.configure(bg="#eef4fb")
        utils.get_style()
        self._setup_toolbox()
        self._setup_treeview(columns)
        
    def _setup_toolbox(self):
        # botones comunes: user, add, delete
        self.toolbox = tk.Frame(self, bg="#eef4fb", relief="raised", bd=2)
        self.toolbox.pack(side="top", fill="x")
        
        self.buttons = []
        
        self.user_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("user")).resize((24,24)))
        self.add_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("add")).resize((24,24)))
        self.delete_image = ImageTk.PhotoImage(Image.open(image_finder.find_image("delete")).resize((24,24))) 
        
        # ---- USER ----
        self.user_button = ttk.Button(self.toolbox, image=self.user_image, text="", compound="left",
                       command=self._see_account, width=2, style=SEC_BTN_STYLE)
        self.user_button.pack(side="left", padx=5, pady=5)
        self.buttons.append(self.user_button)
        
        # ---- ADD ----
        self.add_button = ttk.Button(self.toolbox, image=self.add_image, text="", compound="left",
                       command=self._add_item, width=2, style=SEC_BTN_STYLE)
        self.add_button.pack(side="left", padx=5, pady=5)
        self.buttons.append(self.add_button)
        
        # ---- DELETE ----
        self.delete_button = ttk.Button(self.toolbox, image=self.delete_image, text="", compound="left",
                       command=self._delete_item, width=2, style=SEC_BTN_STYLE)
        self.delete_button.pack(side="left", padx=5, pady=5)
        self.buttons.append(self.delete_button)
        self.delete_button.state(["disabled"])
        
        ToolTip(self.user_button, text="Ver cuenta", delay=0.5)
        
        self._insert_extra_buttons()
    
    def _setup_treeview(self, columns):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=25, pady=10)

        scroll_y = ttk.Scrollbar(container, orient="vertical")
        scroll_x = ttk.Scrollbar(container, orient="horizontal")
        
        col_names = tuple(columns.keys())
        
        self.tree = ttk.Treeview(container,
                                     columns=col_names,
                                     show=("tree","headings"),
                                     yscrollcommand=scroll_y.set,
                                     xscrollcommand=scroll_x.set,
                                     style="Treeview")
        
        self.tree.column("#0", width=100, stretch=tk.NO)
        self.tree.update_idletasks()
        self.tree.grid(row=0, column=0, sticky="nsew")
            
        self.tree.bind("<<TreeviewSelect>>", lambda event: 
            self._selected_item_changed())
            #self.delete_button.state(["!disabled"]) if self.tree.selection() else self.delete_button.state(["disabled"]))

        scroll_y.config(command=self.tree.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.config(command=self.tree.xview)
        scroll_x.grid(row=1, column=0, sticky="ew")

        container.rowconfigure(1, weight=0)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)
        
        for col_name, col_width in columns.items():
            self.tree.heading(col_name, text=col_name, anchor="center")
            self.tree.column(col_name, width=col_width, anchor="center", stretch=tk.YES)
            
        self._initialize_tree()
    
    def _see_account(self):
        self.switch_frame("profile", self.usuario)
    
    def _eliminate_dataset(self, node_id):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        local_dataset_path = os.path.join(BASE_DIR, "..", "..", "database", "datasets" , "node_" + str(uuid.UUID(bytes=node_id)))
        
        if os.path.exists(local_dataset_path):
            shutil.rmtree(local_dataset_path)
    
    def _update_tree_after_delete(self, seleccionado, canceled):
        for item in seleccionado:
                if item in canceled:
                    continue
                layer_id = self.tree.parent(item)
                self.tree.delete(item)
                if layer_id and len(self.tree.get_children(layer_id)) == 0:
                    self.tree.delete(layer_id)
    
    def _parse_path(self, path: str) -> str:
        normalized_path = Path(path).resolve()
        parts = normalized_path.parts
        if "database" in parts:
            idx = parts.index("database")
            relative_path = Path(*parts[idx:])
            return f"./{relative_path.as_posix()}"
        else:
            # Ruta no contiene 'database', devuelve normalizada
            return str(normalized_path)

    def _selected_item_changed(self):
        self.delete_button.state(["!disabled"]) if self.tree.selection() else self.delete_button.state(["disabled"])

    @abstractmethod
    def _insert_extra_buttons(self):
        pass
    
    @abstractmethod
    def _add_item(self):
        pass
    
    @abstractmethod
    def _delete_item(self):
        pass
    
    @abstractmethod
    def _initialize_tree(self):
        pass
