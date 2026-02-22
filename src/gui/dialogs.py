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
        # Apply the global style configuration
        utils.get_style()
        self.configure(bg=utils.BG_COLOR)
        self.resizable(False, False)
        # Make the dialog modal
        self.transient(parent)
        self.grab_set()
        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        # Center the dialog over the parent window
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _add_ok_button(self, command=None):
        """Add a single OK button using the secondary button style.

        If *command* is None the dialog will simply be destroyed.
        """
        if command is None:
            command = self.destroy
        ttk.Button(self, text="OK", style=utils.SEC_TBUTTON_STYLE, command=command).pack(pady=10)


class InfoDialog(BaseDialog):
    """Simple informational dialog (info, warning, error).

    Parameters
    ----------
    parent: tk widget – the parent window.
    title: str – window title.
    message: str – text to display.
    kind: str – one of "info", "warning", "error". Determines the icon.
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


class OptionDialog(BaseDialog):
    """Dialog that asks a yes/no question and returns a boolean.

    Usage
    -----
    result = OptionDialog.ask(parent, "Confirm", "Do you want to continue?")
    """

    @staticmethod
    def ask(parent, title: str, message: str) -> bool:
        """Show a modal yes/no dialog.

        Returns ``True`` if the user clicks *Yes*, ``False`` otherwise.
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
        tk.Label(frame, text=message, font=("Arial", 11), bg=utils.BG_COLOR, wraplength=300, justify="left").grid(row=0, column=0, columnspan=2, pady=(0, 10))
        ttk.Button(frame, text="Yes", style=utils.SEC_TBUTTON_STYLE, command=set_yes).grid(row=1, column=0, padx=5)
        ttk.Button(frame, text="No", style=utils.SEC_TBUTTON_STYLE, command=set_no).grid(row=1, column=1, padx=5)
        dialog.wait_window()
        return answer.get()

    def __init__(self, parent, title: str, message: str):
        # The actual UI is built in the static ``ask`` method, but we keep the
        # constructor for completeness and possible future extensions.
        super().__init__(parent, title)
        # No default widgets – ``ask`` creates its own layout.
        self.withdraw()  # hide the base window; ``ask`` will manage its own Toplevel.
