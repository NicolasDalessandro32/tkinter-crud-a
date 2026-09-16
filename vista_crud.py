import csv
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Dict, List, Optional

import tema
from campo import CampoDef
from excepciones import ErrorRelacion, ErrorBaseDatos

PATRON_FECHA = re.compile(r"^([0-2]\d|3[01])/(0\d|1[0-2])/\d{4}$")


class VistaCRUD(tk.Frame):
  
    VALOR_FILTRO_TODOS = "(Todos)"

    def __init__(
        self,
        master,
        nombre_entidad: str,
        campos: List[CampoDef],
        modelo,
        on_cambio=None,
        on_eliminar_entidad=None,
        obtener_modelo_relacionado: Optional[Callable[[str], object]] = None,
    ):
        super().__init__(master, **tema.OPCIONES_FRAME)
        self.nombre_entidad = nombre_entidad
        self.campos = campos
        self.modelo = modelo
        self.on_cambio = on_cambio
        self.on_eliminar_entidad = on_eliminar_entidad
        self.obtener_modelo_relacionado = obtener_modelo_relacionado

        self.entradas: Dict[str, tk.Widget] = {}
        self.id_seleccionado: Optional[int] = None

        self._mapa_relacion: Dict[str, Dict[str, int]] = {}
        self._mapa_relacion_inversa: Dict[str, Dict[int, str]] = {}
        self._filtros_relacion: Dict[str, ttk.Combobox] = {}

        self._construir_interfaz()
        self._refrescar_tabla()

    # Construcción dinámica de la interfaz
    def _construir_interfaz(self):
        frame_titulo = tk.Frame(self, **tema.OPCIONES_FRAME)
        frame_titulo.grid(row=0, column=0, columnspan=2, pady=(10, 15), sticky="ew")

        titulo = tk.Label(
            frame_titulo, text=f"ABM de {self.nombre_entidad}", **tema.OPCIONES_LABEL_TITULO
        )
        titulo.pack(side="left", padx=(10, 0))

        if self.on_eliminar_entidad is not None:
            tk.Button(
                frame_titulo,
                text="Eliminar esta entidad",
                command=lambda: self.on_eliminar_entidad(self.nombre_entidad),
                **tema.OPCIONES_BOTON_PELIGRO,
            ).pack(side="right", padx=10)

        tk.Button(
            frame_titulo,
            text="Exportar a CSV",
            command=self._exportar_csv,
            **tema.OPCIONES_BOTON,
        ).pack(side="right", padx=4)

        frame_form = tk.LabelFrame(self, text="Datos del registro", padx=10, pady=10, **tema.OPCIONES_LABELFRAME)
        frame_form.grid(row=1, column=0, padx=10, pady=10, sticky="n")

        # --- Bucle obligatorio: genera Label + widget para cada campo ---
        for fila, campo in enumerate(self.campos):
            texto_label = campo.etiqueta + (" *" if campo.obligatorio else "")
            tk.Label(frame_form, text=texto_label, **tema.OPCIONES_LABEL).grid(
                row=fila, column=0, sticky="e", padx=5, pady=4
            )

            widget = self._crear_widget(frame_form, campo)
            widget.grid(row=fila, column=1, padx=5, pady=4, sticky="w")
            self.entradas[campo.nombre] = widget

        fila_botones = len(self.campos)
        frame_botones = tk.Frame(frame_form, **tema.OPCIONES_FRAME)
        frame_botones.grid(row=fila_botones, column=0, columnspan=2, pady=(15, 0))

        tk.Button(frame_botones, text="Crear", width=10, command=self._crear, **tema.OPCIONES_BOTON_EXITO).grid(
            row=0, column=0, padx=3
        )
        tk.Button(
            frame_botones, text="Actualizar", width=10, command=self._actualizar, **tema.OPCIONES_BOTON
        ).grid(row=0, column=1, padx=3)
        tk.Button(
            frame_botones, text="Eliminar", width=10, command=self._eliminar, **tema.OPCIONES_BOTON_PELIGRO
        ).grid(row=0, column=2, padx=3)
        tk.Button(frame_botones, text="Limpiar", width=10, command=self._limpiar, **tema.OPCIONES_BOTON).grid(
            row=0, column=3, padx=3
        )

        # --- Columna derecha: filtro (si corresponde) + tabla ---
        frame_columna_derecha = tk.Frame(self, **tema.OPCIONES_FRAME)
        frame_columna_derecha.grid(row=1, column=1, padx=10, pady=10, sticky="n")

        campos_relacion = [c for c in self.campos if c.tipo == "relacion"]
        if campos_relacion:
            frame_filtros = tk.LabelFrame(
                frame_columna_derecha, text="Filtrar por relación", padx=8, pady=6, **tema.OPCIONES_LABELFRAME
            )
            frame_filtros.grid(row=0, column=0, sticky="ew", pady=(0, 8))

            for i, campo in enumerate(campos_relacion):
                tk.Label(frame_filtros, text=f"{campo.etiqueta}:", **tema.OPCIONES_LABEL).grid(
                    row=0, column=i * 2, padx=(0 if i == 0 else 10, 4)
                )
                combo_filtro = ttk.Combobox(frame_filtros, width=22, state="readonly")
                combo_filtro.grid(row=0, column=i * 2 + 1)
                combo_filtro.bind(
                    "<<ComboboxSelected>>", lambda e: self._refrescar_tabla()
                )
                self._filtros_relacion[campo.nombre] = combo_filtro
                self._poblar_filtro_relacion(combo_filtro, campo)

        # --- Tabla (Treeview) con columnas también generadas por bucle ---
        columnas = ["id"] + [c.nombre for c in self.campos]
        self.tabla = ttk.Treeview(
            frame_columna_derecha, columns=columnas, show="headings", height=12
        )
        for col in columnas:
            self.tabla.heading(col, text=col.capitalize())
            self.tabla.column(col, width=100, anchor="center")
        self.tabla.grid(row=1, column=0)
        self.tabla.bind("<<TreeviewSelect>>", self._seleccionar_fila)

    def _crear_widget(self, parent, campo: CampoDef) -> tk.Widget:
   
        if campo.tipo == "select":
            widget = ttk.Combobox(
                parent, values=campo.opciones, width=campo.ancho - 2, state="readonly"
            )
        elif campo.tipo == "relacion":
            widget = ttk.Combobox(parent, width=campo.ancho - 2, state="readonly")
            self._poblar_combo_relacion(widget, campo)
        elif campo.tipo == "password":
            widget = tk.Entry(parent, width=campo.ancho, show="*", **tema.OPCIONES_ENTRY)
        else:
            # texto, numero, email, fecha -> Entry simple
            widget = tk.Entry(parent, width=campo.ancho, **tema.OPCIONES_ENTRY)
        return widget

    # Campos de relación
    def _construir_opciones_relacion(self, campo: CampoDef):
  
        try:
            modelo_relacionado = self.obtener_modelo_relacionado(campo.entidad_relacionada)
            registros = modelo_relacionado.leer_todos()
        except ErrorBaseDatos as error:
            messagebox.showerror("Error de base de datos", str(error))
            return [], {}, {}

        texto_a_id, id_a_texto, valores = {}, {}, []
        for registro in registros:
            primer_valor = next((v for k, v in registro.items() if k != "id"), "")
            texto = f"{primer_valor} (#{registro['id']})"
            texto_a_id[texto] = registro["id"]
            id_a_texto[registro["id"]] = texto
            valores.append(texto)
        return valores, texto_a_id, id_a_texto

    def _poblar_combo_relacion(self, combo: ttk.Combobox, campo: CampoDef):
        valores, texto_a_id, id_a_texto = self._construir_opciones_relacion(campo)
        combo["values"] = valores
        self._mapa_relacion[campo.nombre] = texto_a_id
        self._mapa_relacion_inversa[campo.nombre] = id_a_texto

    def _poblar_filtro_relacion(self, combo: ttk.Combobox, campo: CampoDef):
        valores, _, _ = self._construir_opciones_relacion(campo)
        seleccion_actual = combo.get()
        combo["values"] = [self.VALOR_FILTRO_TODOS] + valores
        combo.set(
            seleccion_actual if seleccion_actual in combo["values"] else self.VALOR_FILTRO_TODOS
        )

    def actualizar_opciones_relacion(self):
        hubo_campos_relacion = False
        for campo in self.campos:
            if campo.tipo == "relacion":
                hubo_campos_relacion = True
                combo = self.entradas[campo.nombre]
                seleccion_actual = combo.get()
                self._poblar_combo_relacion(combo, campo)
                if seleccion_actual in combo["values"]:
                    combo.set(seleccion_actual)

                if campo.nombre in self._filtros_relacion:
                    self._poblar_filtro_relacion(self._filtros_relacion[campo.nombre], campo)
        if hubo_campos_relacion:
            self._refrescar_tabla()

    # Lectura / limpieza del formulario
    def _leer_formulario(self) -> Dict[str, object]:
        datos = {}
        for campo in self.campos:
            widget = self.entradas[campo.nombre]
            valor = widget.get().strip()
            if campo.tipo == "relacion" and valor:
                valor = self._mapa_relacion.get(campo.nombre, {}).get(valor, valor)
            datos[campo.nombre] = valor
        return datos

    def _limpiar(self):
        for widget in self.entradas.values():
            if isinstance(widget, ttk.Combobox):
                widget.set("")
            else:
                widget.delete(0, tk.END)
        self.id_seleccionado = None
        self.tabla.selection_remove(self.tabla.selection())

    # Validación
    def _validar(self, datos: Dict[str, object], es_creacion: bool = True) -> bool:
        for campo in self.campos:
            valor = datos.get(campo.nombre, "")

            if campo.tipo == "password" and not es_creacion and valor == "":
                continue

            if campo.obligatorio and not valor:
                messagebox.showwarning(
                    "Campo obligatorio",
                    f"El campo '{campo.etiqueta}' no puede quedar vacío.",
                )
                return False

            if valor and campo.tipo == "numero":
                try:
                    float(valor)
                except ValueError:
                    messagebox.showwarning(
                        "Dato inválido",
                        f"El campo '{campo.etiqueta}' debe ser numérico.",
                    )
                    return False

            if valor and campo.tipo == "email" and "@" not in valor:
                messagebox.showwarning(
                    "Dato inválido",
                    f"El campo '{campo.etiqueta}' debe ser un email válido.",
                )
                return False

            if valor and campo.tipo == "fecha" and not PATRON_FECHA.match(valor):
                messagebox.showwarning(
                    "Dato inválido",
                    f"El campo '{campo.etiqueta}' debe tener el formato dd/mm/aaaa (ej: 15/09/2026).",
                )
                return False
        return True

    # Operaciones CRUD
    def _crear(self):
        datos = self._leer_formulario()
        if not self._validar(datos, es_creacion=True):
            return
        try:
            self.modelo.crear(datos)
        except ErrorRelacion as error:
            messagebox.showerror("No se puede guardar", str(error))
            return
        except ErrorBaseDatos as error:
            messagebox.showerror("Error de base de datos", str(error))
            return
        self._refrescar_tabla()
        self._limpiar()
        self._notificar_cambio()

    def _actualizar(self):
        if self.id_seleccionado is None:
            messagebox.showwarning(
                "Sin selección",
                "Debe seleccionar un registro de la tabla antes de actualizar.",
            )
            return
        datos = self._leer_formulario()
        if not self._validar(datos, es_creacion=False):
            return
        try:
            self.modelo.actualizar(self.id_seleccionado, datos)
        except ErrorRelacion as error:
            messagebox.showerror("No se puede guardar", str(error))
            return
        except ErrorBaseDatos as error:
            messagebox.showerror("Error de base de datos", str(error))
            return
        self._refrescar_tabla()
        self._limpiar()
        self._notificar_cambio()

    def _eliminar(self):
        if self.id_seleccionado is None:
            messagebox.showwarning(
                "Sin selección",
                "Debe seleccionar un registro de la tabla antes de eliminar.",
            )
            return
        if not messagebox.askyesno("Confirmar", "¿Eliminar el registro seleccionado?"):
            return
        try:
            self.modelo.eliminar(self.id_seleccionado)
        except ErrorRelacion as error:
            messagebox.showerror("No se puede eliminar", str(error))
            return
        except ErrorBaseDatos as error:
            messagebox.showerror("Error de base de datos", str(error))
            return
        self._refrescar_tabla()
        self._limpiar()
        self._notificar_cambio()

    def _notificar_cambio(self):
        if self.on_cambio is not None:
            self.on_cambio()

    # Tabla (con filtro por relación aplicado, si corresponde)
    def _pasa_filtros(self, registro: Dict) -> bool:
        for nombre_campo, combo_filtro in self._filtros_relacion.items():
            seleccion = combo_filtro.get()
            if not seleccion or seleccion == self.VALOR_FILTRO_TODOS:
                continue
            id_filtrado = self._mapa_relacion.get(nombre_campo, {}).get(seleccion)
            valor_registro = registro.get(nombre_campo, "")
            if valor_registro == "" or id_filtrado is None:
                return False
            if int(valor_registro) != id_filtrado:
                return False
        return True

    def _refrescar_tabla(self):
        for item in self.tabla.get_children():
            self.tabla.delete(item)
        try:
            registros = self.modelo.leer_todos()
        except ErrorBaseDatos as error:
            messagebox.showerror("Error de base de datos", str(error))
            return
        for registro in registros:
            if not self._pasa_filtros(registro):
                continue
            fila = [registro["id"]]
            for campo in self.campos:
                valor = registro.get(campo.nombre, "")
                if campo.tipo == "relacion" and valor != "":
                    mapa_inverso = self._mapa_relacion_inversa.get(campo.nombre, {})
                    valor = mapa_inverso.get(int(valor), f"(#{valor})")
                fila.append(valor)
            self.tabla.insert("", tk.END, values=fila)

    def _seleccionar_fila(self, event):
        seleccion = self.tabla.selection()
        if not seleccion:
            return
        valores = self.tabla.item(seleccion[0], "values")
        self.id_seleccionado = int(valores[0])

        for i, campo in enumerate(self.campos, start=1):
            widget = self.entradas[campo.nombre]
            if campo.tipo == "password":
                widget.delete(0, tk.END)
                continue
            if isinstance(widget, ttk.Combobox):
                widget.set(valores[i])
            else:
                widget.delete(0, tk.END)
                widget.insert(0, valores[i])

    # Exportar a CSV
    def _exportar_csv(self):
        ruta = filedialog.asksaveasfilename(
            title=f"Exportar {self.nombre_entidad} a CSV",
            defaultextension=".csv",
            filetypes=[("Archivo CSV", "*.csv")],
            initialfile=f"{self.nombre_entidad.lower()}.csv",
        )
        if not ruta:
            return

        try:
            registros = self.modelo.leer_todos()
        except ErrorBaseDatos as error:
            messagebox.showerror("Error de base de datos", str(error))
            return

        encabezados = ["id"] + [c.etiqueta for c in self.campos]
        try:
            with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
                escritor = csv.writer(archivo)
                escritor.writerow(encabezados)
                for registro in registros:
                    fila = [registro["id"]]
                    for campo in self.campos:
                        valor = registro.get(campo.nombre, "")
                        if campo.tipo == "relacion" and valor != "":
                            valor = self._mapa_relacion_inversa.get(campo.nombre, {}).get(
                                int(valor), valor
                            )
                        if campo.tipo == "password":
                            valor = ""  # nunca exportar, ni siquiera el hash
                        fila.append(valor)
                    escritor.writerow(fila)
        except OSError as error:
            messagebox.showerror("No se pudo exportar", str(error))
            return

        messagebox.showinfo(
            "Exportación completa", f"Se exportaron {len(registros)} registro(s) a:\n{ruta}"
        )
