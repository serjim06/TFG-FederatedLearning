import tkinter.ttk as ttk

def get_style():
    """
        Creates and configures custom styles for Tkinter GUI widgets using the `ttk` module.

        This function defines styles for main buttons,
        secondary buttons, and entry fields, for the program.

        Returns
        -------
        style : ttk.Style
            A configured `ttk.Style` object that can be applied to ttk widgets in the GUI.
            The predefined styles include:

            - **"Accent.TButton"**: Style for primary buttons.
            - **"Sec.TButton"**: Style for secondary buttons.
            - **"Custom.TEntry"**: Style for entry fields.
    """
    # ----- Estilos -----
    style = ttk.Style()
    style.theme_use("clam")

    # Botón principal
    style.configure(
        "Accent.TButton",
        font=("Segoe UI", 11, "bold"),
        foreground="#ffffff",
        background="#4a90e2",
        padding=6,
        borderwidth=0
    )
    style.map(
        "Accent.TButton",
        background=[("active", "#357ABD"), ("pressed", "#2c5a92")],
        foreground=[("active", "#ffffff")]
    )

    style.configure(
        "Sec.TButton",
        foreground="#000000",
        background="#e0e4eb",
        padding=6,
        borderwidth=0
    )

    style.map("Sec.TButton",
              background=[("active", "#d3d7df"),
                          ("pressed", "#c7cbd5")],
              foreground=[("active", "black"),
                          ("pressed", "white")])

    # Entradas
    style.configure(
        "Custom.TEntry",
        fieldbackground="#ffffff",
        background="#ffffff",
        foreground="#1d2d44",
        bordercolor="#d9d9d9",
        relief="flat",
        insertcolor="#1d2d44"
    )
    return style