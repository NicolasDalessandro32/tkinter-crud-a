import tkinter as tk
from tkinter import ttk, messagebox

import basedatos
import tema
from campo import CampoDef
from excepciones import ErrorRelacion, ErrorBaseDatos
from modelo import ModeloCRUD
from vista_crud import VistaCRUD
from constructor_entidad import ConstructorEntidad


class AplicacionCRUD(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema CRUD-A")
        self.geometry("1100x680")

        tema.aplicar_tema(self)

        # Estado central: qué entidades existen y con qué datos.
        self.entidades = {}
        self.vistas = {}

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self._al_cambiar_pestaña)

        self._crear_pestaña_constructor()
        self._restaurar_entidades_guardadas()

    def _crear_pestaña_constructor(self):
        self.constructor = ConstructorEntidad(
            self.notebook,
            on_crear_entidad=self._crear_entidad,
            nombres_existentes=lambda: set(self.entidades.keys()),
        )
        self.notebook.add(self.constructor, text="Nueva entidad")

    def _obtener_modelo(self, nombre_entidad):
        return self.entidades[nombre_entidad]["modelo"]

    def _crear_entidad(self, nombre_entidad, campos, nombre_tabla=None):
        if nombre_tabla is None:
            try:
                nombre_tabla = basedatos.crear_tabla_entidad(
                    nombre_entidad, [c.to_dict() for c in campos]
                )
            except (ErrorBaseDatos, ValueError) as error:
                messagebox.showerror("No se pudo crear la entidad", str(error))
                return

        modelo = ModeloCRUD(nombre_entidad, campos, nombre_tabla)

        vista = VistaCRUD(
            self.notebook,
            nombre_entidad,
            campos,
            modelo,
            on_eliminar_entidad=self._eliminar_entidad,
            obtener_modelo_relacionado=self._obtener_modelo,
        )
        self.notebook.add(vista, text=nombre_entidad)
        self.notebook.select(vista)

        self.entidades[nombre_entidad] = {"campos": campos, "modelo": modelo}
        self.vistas[nombre_entidad] = vista

    def _eliminar_entidad(self, nombre_entidad):
        if not messagebox.askyesno(
            "Eliminar entidad",
            f"Esto borra la entidad '{nombre_entidad}' y TODOS sus registros "
            f"de la base de datos (se hace DROP TABLE). ¿Continuar?",
        ):
            return

        modelo = self.entidades[nombre_entidad]["modelo"]
        try:
            basedatos.eliminar_entidad(nombre_entidad, modelo.nombre_tabla)
        except ErrorRelacion as error:
            messagebox.showerror("No se puede eliminar la entidad", str(error))
            return
        except ErrorBaseDatos as error:
            messagebox.showerror("Error de base de datos", str(error))
            return

        vista = self.vistas.pop(nombre_entidad, None)
        if vista is not None:
            self.notebook.forget(vista)
        self.entidades.pop(nombre_entidad, None)

    def _al_cambiar_pestaña(self, event):
        pestaña_actual = self.notebook.nametowidget(self.notebook.select())
        if isinstance(pestaña_actual, VistaCRUD):
            pestaña_actual.actualizar_opciones_relacion()

    def _restaurar_entidades_guardadas(self):

        try:
            guardado = basedatos.listar_entidades()
        except ErrorBaseDatos as error:
            messagebox.showerror("Error de base de datos", str(error))
            return

        pendientes = dict(guardado)
        creadas = set()

        def dependencias(info):
            return {
                c.get("entidad_relacionada")
                for c in info["campos"]
                if c.get("tipo") == "relacion" and c.get("entidad_relacionada")
            }

        while pendientes:
            avanzo = False
            for nombre_entidad, info in list(pendientes.items()):
                if dependencias(info) <= creadas:
                    campos = [CampoDef.from_dict(c) for c in info["campos"]]
                    self._crear_entidad(nombre_entidad, campos, nombre_tabla=info["nombre_tabla"])
                    creadas.add(nombre_entidad)
                    del pendientes[nombre_entidad]
                    avanzo = True
            if not avanzo:
                for nombre_entidad, info in pendientes.items():
                    campos = [CampoDef.from_dict(c) for c in info["campos"]]
                    self._crear_entidad(nombre_entidad, campos, nombre_tabla=info["nombre_tabla"])
                break

        self.notebook.select(self.constructor)


def main():
    try:
        basedatos.inicializar_base_datos()
    except ErrorBaseDatos as error:
        raiz_error = tk.Tk()
        raiz_error.withdraw()
        messagebox.showerror("Error de conexión a MySQL", str(error))
        raiz_error.destroy()
        return

    app = AplicacionCRUD()
    app.mainloop()


if __name__ == "__main__":
    main()
