import tkinter.ttk as ttk

def get_style():
    """
        Creates a consistent style for every GUI

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
    
    style.configure("TFrame", background="#eef4fb")
    
    style.map(
    "TCombobox",
    fieldbackground=[("readonly", "white")],
    background=[("readonly", "white")]
    )
    
    style.configure(
    "Form.TLabel",
    background="#eef4fb"
    )
    
    style.configure(
    "White.Vertical.TScrollbar",
    background="white",
    troughcolor="white",
    bordercolor="black",
    arrowcolor="black",
    lightcolor="white",
    darkcolor="white"
)


    
    return style