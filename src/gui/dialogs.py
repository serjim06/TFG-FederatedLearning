from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from src.utils import utils
from src.utils.icons import image_finder


class BaseDialog(tk.Toplevel):
    """Base class for custom dialogs with consistent styling.

    Provides common setup: background color, style initialization, modal behavior.
    """

    def __init__(self, parent, title: str = "Dialog"):
        super().__init__(parent)
        self.title(title)
        utils.get_style()
        self.configure(bg=utils.BG_COLOR)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def center_dialog(self):
        self.update_idletasks()
        w = max(self.winfo_width(), 350) 
        h = self.winfo_height()
        
        parent = self.master
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (h // 2)
        
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _add_ok_button(self, command=None):
        """Add a single OK button using the secondary button style.

        If *command* is None the dialog will simply be destroyed.
        """
        if command is None:
            command = self.destroy
        ok_button = ttk.Button(self, text="OK", style=utils.SEC_TBUTTON_STYLE, command=command)
        ok_button.pack(pady=10)
        ok_button.focus_set()
        self.bind("<Return>", lambda _event: command())
        self.bind("<KP_Enter>", lambda _event: command())


class InfoDialog(BaseDialog):
    """Simple informational dialog (info, warning, error).

    Blocks until the user closes the dialog (same pattern as ``OptionDialog.ask``),
    so callers can safely show a message and then continue (e.g. ``switch_frame``).

    Parameters
    ----------
    parent: tk widget - the parent window.

    title: str - window title.

    message: str - text to display.

    kind: str - one of "info", "warning", "error". Determines the icon.
    """

    def __init__(self, parent, title: str, message: str, kind: str = "info"):
        self.icons = {
            "info": ImageTk.PhotoImage(Image.open(image_finder.find_image("info")).resize((24,24))),
            "warning": ImageTk.PhotoImage(Image.open(image_finder.find_image("warning")).resize((24,24))),
            "error": ImageTk.PhotoImage(Image.open(image_finder.find_image("error")).resize((24,24))),
        }
        super().__init__(parent, title)
        self.icon = self.icons.get(kind, self.icons["info"])
        frame = tk.Frame(self, bg=utils.BG_COLOR)
        frame.pack(padx=20, pady=20)
        tk.Label(frame, image=self.icon, bg=utils.BG_COLOR).grid(row=0, column=0, padx=(0, 10))
        tk.Label(frame, text=message, font=(utils.FONT, 12, "bold"), bg=utils.BG_COLOR, wraplength=300, justify="left").grid(row=0, column=1)
        self._add_ok_button()
        self.center_dialog()
        self.update_idletasks()
        master = self.master
        if master is not None:
            master.wait_window(self)


class OptionDialog(BaseDialog):
    """Dialog that asks a yes/no question and returns a boolean.

    Parameters
    ----------
    parent: tk widget - the parent window.

    title: str - window title.

    message: str - text to display.

    Usage
    -----
    result = OptionDialog.ask(parent, "Confirm", "Do you want to continue?")
    """

    @staticmethod
    def ask(parent, title: str, message: str) -> bool:
        """Show a modal yes/no dialog.

        Returns `True` if the user clicks *Yes*, `False` otherwise.
        """
        dialog = OptionDialog(parent, title, message)
        answer = tk.BooleanVar(value=False)

        def set_yes():
            answer.set(True)
            dialog.destroy()

        def set_no():
            answer.set(False)
            dialog.destroy()

        frame = tk.Frame(dialog, bg=utils.BG_COLOR)
        frame.pack(padx=20, pady=20)
        tk.Label(frame, text=message, font=(utils.FONT, 12, "bold"  ), bg=utils.BG_COLOR, wraplength=300, justify="left").grid(row=0, column=0, columnspan=2, pady=(0, 10))
        ttk.Button(frame, text="Yes", style=utils.SEC_TBUTTON_STYLE, command=set_yes).grid(row=1, column=0, padx=5)
        ttk.Button(frame, text="No", style=utils.SEC_TBUTTON_STYLE, command=set_no).grid(row=1, column=1, padx=5)
        dialog.center_dialog()
        dialog.wait_window()
        return answer.get()

    def __init__(self, parent, title: str, message: str):
        super().__init__(parent, title)


class FederatedRoundsDialog(BaseDialog):
    """
    Ask for the number of federated rounds for the federated training dialog.
    """

    def __init__(
        self,
        parent,
        default_rounds: int = 5,
        on_confirm=None,
    ):
        super().__init__(parent, "Entrenamiento federado")
        self.result = None
        self._on_confirm = on_confirm

        tk.Label(
            self,
            text=(
                "Indica cuántas rondas federadas ejecutará el servidor Flower.\n"
                "En cada ronda se entrenan todos los nodos del proyecto y se agregan los pesos."
            ),
            bg=utils.BG_COLOR,
            wraplength=400,
            justify="left",
        ).pack(padx=16, pady=(16, 8))

        row = tk.Frame(self, bg=utils.BG_COLOR)
        row.pack(pady=8)
        tk.Label(row, text="Rondas:", bg=utils.BG_COLOR).pack(side="left", padx=(0, 8))
        self._rounds_var = tk.IntVar(value=max(1, default_rounds))
        tk.Spinbox(
            row,
            from_=1,
            to=500,
            textvariable=self._rounds_var,
            width=8,
        ).pack(side="left")

        btn_row = tk.Frame(self, bg=utils.BG_COLOR)
        btn_row.pack(pady=16)

        def _ok():
            try:
                v = int(self._rounds_var.get())
            except (tk.TclError, ValueError):
                v = 1
            v = max(1, min(500, v))
            self.result = v
            self.destroy()
            if self._on_confirm is not None:
                root = parent.winfo_toplevel()
                root.after(0, lambda n=v: self._on_confirm(n))

        def _cancel():
            self.result = None
            self.destroy()

        ttk.Button(btn_row, text="Iniciar", style=utils.SEC_TBUTTON_STYLE, command=_ok).pack(
            side="left", padx=6
        )
        ttk.Button(btn_row, text="Cancelar", style=utils.SEC_TBUTTON_STYLE, command=_cancel).pack(
            side="left", padx=6
        )
        self.center_dialog()


class PredictDialog(BaseDialog):
    def __init__(
        self,
        parent,
        feature_names: list[str],
        node_ids: list[str],
        default_line: str = "",
        on_confirm=None,
    ):
        super().__init__(parent, "Realizar predicción")
        self._on_confirm = on_confirm
        self._feature_names = feature_names
        self._node_ids = node_ids or []

        hint = (
            "Introduce los valores de entrada en el mismo orden que las columnas del proyecto, "
            "separados por comas (números decimales con punto)."
        )
        if feature_names:
            hint += "\n\nColumnas: " + ", ".join(feature_names)

        tk.Label(
            self,
            text=hint,
            bg=utils.BG_COLOR,
            wraplength=420,
            justify="left",
        ).pack(padx=16, pady=(16, 8))

        node_row = tk.Frame(self, bg=utils.BG_COLOR)
        node_row.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(node_row, text="Nodo:", bg=utils.BG_COLOR).pack(side="left", padx=(0, 8))
        self._selected_node = tk.StringVar(value=self._node_ids[0] if self._node_ids else "")
        self._node_combo = ttk.Combobox(
            node_row,
            textvariable=self._selected_node,
            values=self._node_ids,
            state="readonly",
            width=40,
        )
        self._node_combo.pack(side="left", fill="x", expand=True)

        self._var = tk.StringVar(value=default_line or "")
        entry = ttk.Entry(self, textvariable=self._var, width=52)
        entry.pack(padx=16, pady=8)
        entry.focus_set()

        btn_row = tk.Frame(self, bg=utils.BG_COLOR)
        btn_row.pack(pady=16)

        def _ok():
            raw = self._var.get().strip()
            if not raw:
                InfoDialog(self, "Entrada vacía", "Escribe al menos un valor.", "warning")
                return
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            try:
                vals = [float(p) for p in parts]
            except ValueError:
                InfoDialog(
                    self,
                    "Formato inválido",
                    "Cada valor debe ser un número (usa el punto decimal).",
                    "error",
                )
                return
            if self._feature_names and len(vals) != len(self._feature_names):
                InfoDialog(
                    self,
                    "Cantidad incorrecta",
                    f"Se esperaban {len(self._feature_names)} valores; hay {len(vals)}.",
                    "warning",
                )
                return
            chosen_node = self._selected_node.get().strip()
            if not chosen_node:
                InfoDialog(
                    self,
                    "Nodo requerido",
                    "Selecciona un nodo para realizar la predicción.",
                    "warning",
                )
                return
            self.destroy()
            if self._on_confirm is not None:
                root = parent.winfo_toplevel()
                root.after(0, lambda v=list(vals), n=chosen_node: self._on_confirm(v, n))

        def _cancel():
            self.destroy()

        ttk.Button(btn_row, text="Predecir", style=utils.SEC_TBUTTON_STYLE, command=_ok).pack(
            side="left", padx=6
        )
        ttk.Button(btn_row, text="Cancelar", style=utils.SEC_TBUTTON_STYLE, command=_cancel).pack(
            side="left", padx=6
        )
        self.center_dialog()
