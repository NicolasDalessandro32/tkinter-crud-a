import re
import unicodedata
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, List, Optional

import tema
from campo import CampoDef
from config import TIPOS_VISIBLES


def _slugify(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = texto.lower().strip()
    texto = re.sub(r"[^a-z0-9]+", "_", texto).strip("_")
    return texto or "campo"


class ConstructorEntidad(tk.Frame):
    
    def __init__(
        self,
        master,
        on_crear_entidad: Callable[[str, List[CampoDef]], None],
        nombres_existentes: Callable[[], set],
    ):
        super().__init__(master, **tema.OPCIONES_FRAME)
        self.on_crear_entidad = on_crear_entidad
        self.nombres_existentes = nombres_existentes

        self.campos_temporales: List[CampoDef] = []

        self._construir_interfaz()

    def _construir_interfaz(self):
        tk.Label(
            self, text="Diseñar una nueva entidad", **tema.OPCIONES_LABEL_TITULO
        ).grid(row=0, column=0, columnspan=2, pady=(15, 10))

        # ---- Nombre de la entidad ----
        frame_nombre = tk.LabelFrame(
            self, text="1. Nombre de la entidad", padx=10, pady=10, **tema.OPCIONES_LABELFRAME
        )
        frame_nombre.grid(row=1, column=0, columnspan=2, padx=15, pady=5, sticky="ew")

        tk.Label(frame_nombre, text="Ej: Cliente, Vehículo, Reserva...", **tema.OPCIONES_LABEL).grid(
            row=0, column=0, sticky="w"
        )
        self.entrada_nombre_entidad = tk.Entry(frame_nombre, width=35, **tema.OPCIONES_ENTRY)
        self.entrada_nombre_entidad.grid(row=1, column=0, sticky="w", pady=4)

        # ---- Alta de un campo ----
        frame_campo = tk.LabelFrame(
            self, text="2. Agregar un campo", padx=10, pady=10, **tema.OPCIONES_LABELFRAME
        )
        frame_campo.grid(row=2, column=0, padx=15, pady=5, sticky="n")

        tk.Label(frame_campo, text="Etiqueta del campo:", **tema.OPCIONES_LABEL).grid(
            row=0, column=0, sticky="e", pady=3
        )
        self.entrada_etiqueta = tk.Entry(frame_campo, width=25, **tema.OPCIONES_ENTRY)
        self.entrada_etiqueta.grid(row=0, column=1, pady=3, padx=5)

        tk.Label(frame_campo, text="¿Cómo se carga?:", **tema.OPCIONES_LABEL).grid(
            row=1, column=0, sticky="e", pady=3
        )
        self.combo_tipo = ttk.Combobox(
            frame_campo, values=list(TIPOS_VISIBLES.keys()), width=27, state="readonly"
        )
        self.combo_tipo.current(0)
        self.combo_tipo.grid(row=1, column=1, pady=3, padx=5)
        self.combo_tipo.bind("<<ComboboxSelected>>", self._actualizar_estado_campos_extra)

        # "Opciones" (select) y "Entidad relacionada" (relacion) comparten
        # el mismo lugar en la grilla: solo se muestra uno de los dos.
        tk.Label(frame_campo, text="Opciones (separadas por coma):", **tema.OPCIONES_LABEL).grid(
            row=2, column=0, sticky="e", pady=3
        )
        self.entrada_opciones = tk.Entry(frame_campo, width=25, state="disabled", **tema.OPCIONES_ENTRY)
        self.entrada_opciones.grid(row=2, column=1, pady=3, padx=5)

        self.label_entidad_relacionada = tk.Label(frame_campo, text="Relacionar con:", **tema.OPCIONES_LABEL)
        self.combo_entidad_relacionada = ttk.Combobox(frame_campo, width=23, state="readonly")

        self.var_obligatorio = tk.BooleanVar(value=True)
        tk.Checkbutton(
            frame_campo, text="Campo obligatorio", variable=self.var_obligatorio, **tema.OPCIONES_CHECKBUTTON
        ).grid(row=3, column=0, columnspan=2, pady=3)

        self.var_unico = tk.BooleanVar(value=False)
        tk.Checkbutton(
            frame_campo,
            text="Valor único (no se puede repetir entre registros)",
            variable=self.var_unico,
            **tema.OPCIONES_CHECKBUTTON,
        ).grid(row=4, column=0, columnspan=2, pady=3)

        tk.Button(
            frame_campo, text="+ Agregar campo a la lista", command=self._agregar_campo, **tema.OPCIONES_BOTON
        ).grid(row=5, column=0, columnspan=2, pady=(8, 0))

        # ---- Lista de campos ya agregados ----
        frame_lista = tk.LabelFrame(
            self, text="3. Campos de la entidad", padx=10, pady=10, **tema.OPCIONES_LABELFRAME
        )
        frame_lista.grid(row=2, column=1, padx=15, pady=5, sticky="n")

        columnas = ("etiqueta", "tipo", "obligatorio", "unico", "detalle")
        self.tabla_campos = ttk.Treeview(
            frame_lista, columns=columnas, show="headings", height=8
        )
        for col, ancho in zip(columnas, (110, 120, 80, 60, 150)):
            self.tabla_campos.heading(col, text=col.capitalize())
            self.tabla_campos.column(col, width=ancho, anchor="center")
        self.tabla_campos.grid(row=0, column=0, columnspan=2)

        tk.Button(
            frame_lista, text="Quitar campo seleccionado", command=self._quitar_campo, **tema.OPCIONES_BOTON
        ).grid(row=1, column=0, pady=8)
        tk.Button(
            frame_lista, text="Vaciar todo", command=self._vaciar_campos, **tema.OPCIONES_BOTON
        ).grid(row=1, column=1, pady=8)

        # ---- Confirmar creación de la entidad ----
        tk.Button(
            self,
            text="Crear entidad",
            command=self._crear_entidad,
            **{**tema.OPCIONES_BOTON_EXITO, "font": tema.FUENTE_NEGRITA},
        ).grid(row=3, column=0, columnspan=2, pady=20)

    def _actualizar_estado_campos_extra(self, event=None):

        tipo = TIPOS_VISIBLES[self.combo_tipo.get()]
        self.entrada_opciones.grid_remove()
        self.label_entidad_relacionada.grid_remove()
        self.combo_entidad_relacionada.grid_remove()

        if tipo == "select":
            self.entrada_opciones.grid(row=2, column=1, pady=3, padx=5)
            self.entrada_opciones.config(state="normal")

        elif tipo == "relacion":
            entidades_disponibles = sorted(self.nombres_existentes())
            if not entidades_disponibles:
                messagebox.showwarning(
                    "Sin entidades para relacionar",
                    "Todavía no creaste ninguna otra entidad. Creá primero la "
                    "entidad a la que querés relacionar (por ejemplo 'Curso') "
                    "y después agregá este campo.",
                )
                self.combo_tipo.current(0)
                self._actualizar_estado_campos_extra()
                return
            self.label_entidad_relacionada.grid(row=2, column=0, sticky="e", pady=3)
            self.combo_entidad_relacionada.grid(row=2, column=1, pady=3, padx=5)
            self.combo_entidad_relacionada["values"] = entidades_disponibles
            self.combo_entidad_relacionada.set(entidades_disponibles[0])

        else:
            self.entrada_opciones.config(state="disabled")
            self.entrada_opciones.delete(0, tk.END)

    def _generar_nombre_interno(self, etiqueta: str) -> str:

        base = _slugify(etiqueta)
        nombre = base
        existentes = {c.nombre for c in self.campos_temporales}
        contador = 2
        while nombre in existentes:
            nombre = f"{base}_{contador}"
            contador += 1
        return nombre

    def _agregar_campo(self):

        etiqueta = self.entrada_etiqueta.get().strip()
        if not etiqueta:
            messagebox.showwarning("Falta la etiqueta", "Escribí un nombre para el campo.")
            return

        tipo_visible = self.combo_tipo.get()
        tipo = TIPOS_VISIBLES[tipo_visible]

        opciones = None
        entidad_relacionada = None
        detalle_mostrado = "-"

        if tipo == "select":
            texto_opciones = self.entrada_opciones.get().strip()
            if not texto_opciones:
                messagebox.showwarning(
                    "Faltan las opciones",
                    "Para un campo de tipo 'Selección' hay que escribir al menos una opción.",
                )
                return
            opciones = [o.strip() for o in texto_opciones.split(",") if o.strip()]
            detalle_mostrado = ", ".join(opciones)

        elif tipo == "relacion":
            entidad_relacionada = self.combo_entidad_relacionada.get().strip()
            if not entidad_relacionada:
                messagebox.showwarning(
                    "Falta la entidad", "Elegí con qué entidad se relaciona este campo."
                )
                return
            detalle_mostrado = f"→ {entidad_relacionada}"

        nombre_interno = self._generar_nombre_interno(etiqueta)
        campo = CampoDef(
            nombre=nombre_interno,
            etiqueta=etiqueta,
            tipo=tipo,
            obligatorio=self.var_obligatorio.get(),
            unico=self.var_unico.get(),
            opciones=opciones,
            entidad_relacionada=entidad_relacionada,
        )
        self.campos_temporales.append(campo)
        self.tabla_campos.insert(
            "",
            tk.END,
            values=(
                campo.etiqueta,
                tipo_visible,
                "Sí" if campo.obligatorio else "No",
                "Sí" if campo.unico else "No",
                detalle_mostrado,
            ),
        )

        self.entrada_etiqueta.delete(0, tk.END)
        self.entrada_opciones.delete(0, tk.END)
        self.combo_tipo.current(0)
        self._actualizar_estado_campos_extra()
        self.var_obligatorio.set(True)
        self.var_unico.set(False)
        self.entrada_etiqueta.focus_set()

    def _quitar_campo(self):
        seleccion = self.tabla_campos.selection()
        if not seleccion:
            messagebox.showwarning("Sin selección", "Seleccioná un campo de la lista para quitarlo.")
            return
        indice = self.tabla_campos.index(seleccion[0])
        self.tabla_campos.delete(seleccion[0])
        del self.campos_temporales[indice]

    def _vaciar_campos(self):
        self.campos_temporales = []
        for item in self.tabla_campos.get_children():
            self.tabla_campos.delete(item)

    def _crear_entidad(self):
        nombre_entidad = self.entrada_nombre_entidad.get().strip()

        if not nombre_entidad:
            messagebox.showwarning("Falta el nombre", "Escribí un nombre para la entidad.")
            return

        nombres_normalizados = {n.lower() for n in self.nombres_existentes()}
        if nombre_entidad.lower() in nombres_normalizados:
            messagebox.showwarning(
                "Nombre repetido",
                f"Ya existe una entidad llamada '{nombre_entidad}' "
                f"(no se distinguen mayúsculas de minúsculas).",
            )
            return

        if not self.campos_temporales:
            messagebox.showwarning(
                "Sin campos", "Agregá al menos un campo antes de crear la entidad."
            )
            return

        campos = list(self.campos_temporales)
        self.on_crear_entidad(nombre_entidad, campos)

        self.entrada_nombre_entidad.delete(0, tk.END)
        self._vaciar_campos()
        messagebox.showinfo(
            "Entidad creada", f"Se creó la entidad '{nombre_entidad}' con {len(campos)} campo(s)."
        )
