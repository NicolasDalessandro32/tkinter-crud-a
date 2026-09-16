import tkinter as tk
from tkinter import ttk

# Paleta
FONDO = "#1e1e1e"            # fondo general de la ventana
FONDO_PANEL = "#2a2a2a"      # fondo de tablas y cabeceras de pestaña
FONDO_ENTRADA = "#3c3c3c"    # fondo de Entry / Combobox / botones neutros
TEXTO = "#e6e6e6"            # texto principal
TEXTO_SECUNDARIO = "#a0a0a0"
BORDE = "#4a4a4a"
ACENTO = "#3b82f6"           
ACENTO_TEXTO = "#ffffff"
PELIGRO = "#b03a2e"
PELIGRO_TEXTO = "#ffffff"
EXITO = "#2e7d32"
EXITO_TEXTO = "#ffffff"

FUENTE = ("Segoe UI", 10)
FUENTE_NEGRITA = ("Segoe UI", 10, "bold")
FUENTE_TITULO = ("Segoe UI", 14, "bold")


def aplicar_tema(root: tk.Tk) -> None:
    root.configure(bg=FONDO)

    style = ttk.Style(root)
    style.theme_use("clam")

    # --- Pestañas (Notebook) ---
    style.configure("TNotebook", background=FONDO, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=FONDO_PANEL,
        foreground=TEXTO,
        padding=(14, 7),
        font=FUENTE,
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", ACENTO)],
        foreground=[("selected", ACENTO_TEXTO)],
    )

    # --- Combobox ---
    style.configure(
        "TCombobox",
        fieldbackground=FONDO_ENTRADA,
        background=FONDO_ENTRADA,
        foreground=TEXTO,
        arrowcolor=TEXTO,
        borderwidth=0,
        padding=4,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", FONDO_ENTRADA), ("disabled", FONDO_PANEL)],
        foreground=[("readonly", TEXTO), ("disabled", TEXTO_SECUNDARIO)],
        selectbackground=[("readonly", FONDO_ENTRADA)],
        selectforeground=[("readonly", TEXTO)],
    )

    root.option_add("*TCombobox*Listbox.background", FONDO_ENTRADA)
    root.option_add("*TCombobox*Listbox.foreground", TEXTO)
    root.option_add("*TCombobox*Listbox.selectBackground", ACENTO)
    root.option_add("*TCombobox*Listbox.selectForeground", ACENTO_TEXTO)

    # Treeview
    style.configure(
        "Treeview",
        background=FONDO_PANEL,
        fieldbackground=FONDO_PANEL,
        foreground=TEXTO,
        borderwidth=0,
        rowheight=26,
        font=FUENTE,
    )
    style.configure(
        "Treeview.Heading",
        background=FONDO_ENTRADA,
        foreground=TEXTO,
        font=FUENTE_NEGRITA,
        borderwidth=0,
        relief="flat",
    )
    style.map(
        "Treeview.Heading",
        background=[("active", BORDE)],
    )
    style.map(
        "Treeview",
        background=[("selected", ACENTO)],
        foreground=[("selected", ACENTO_TEXTO)],
    )
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])  # sin borde exterior


OPCIONES_FRAME = {"bg": FONDO}
OPCIONES_PANEL = {"bg": FONDO_PANEL}

OPCIONES_LABEL = {"bg": FONDO, "fg": TEXTO, "font": FUENTE}
OPCIONES_LABEL_TITULO = {"bg": FONDO, "fg": TEXTO, "font": FUENTE_TITULO}

OPCIONES_LABELFRAME = {
    "bg": FONDO,
    "fg": TEXTO,
    "font": FUENTE_NEGRITA,
    "highlightbackground": BORDE,
    "highlightthickness": 1,
    "bd": 0,
}

OPCIONES_ENTRY = {
    "bg": FONDO_ENTRADA,
    "fg": TEXTO,
    "insertbackground": TEXTO,   
    "relief": "flat",
    "highlightthickness": 1,
    "highlightbackground": BORDE,
    "highlightcolor": ACENTO,
    "font": FUENTE,
}

OPCIONES_BOTON = {
    "bg": FONDO_ENTRADA,
    "fg": TEXTO,
    "activebackground": ACENTO,
    "activeforeground": ACENTO_TEXTO,
    "relief": "flat",
    "font": FUENTE,
    "borderwidth": 0,
    "cursor": "hand2",
    "padx": 8,
    "pady": 4,
}
OPCIONES_BOTON_PELIGRO = {**OPCIONES_BOTON, "bg": PELIGRO, "fg": PELIGRO_TEXTO}
OPCIONES_BOTON_EXITO = {**OPCIONES_BOTON, "bg": EXITO, "fg": EXITO_TEXTO}

OPCIONES_CHECKBUTTON = {
    "bg": FONDO,
    "fg": TEXTO,
    "selectcolor": FONDO_ENTRADA,
    "activebackground": FONDO,
    "activeforeground": TEXTO,
    "font": FUENTE,
}
