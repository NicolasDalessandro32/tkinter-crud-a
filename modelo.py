from typing import Dict, List, Optional
import bcrypt

import basedatos
from campo import CampoDef

class ModeloCRUD:
    def __init__(self, nombre_entidad: str, campos: List[CampoDef], nombre_tabla: str):
        self.nombre_entidad = nombre_entidad
        self.campos = campos
        self.nombre_tabla = nombre_tabla
        self._campos_por_nombre = {c.nombre: c for c in campos}


    def crear(self, datos: Dict) -> Dict:
        datos_sql = self._normalizar_para_guardar(datos, es_creacion=True)
        nuevo_id = basedatos.insertar_registro(self.nombre_tabla, datos_sql)
        return {"id": nuevo_id, **datos}

    def leer_todos(self) -> List[Dict]:
        filas = basedatos.listar_registros(self.nombre_tabla)
        return [self._formatear_para_mostrar(fila) for fila in filas]

    def obtener_por_id(self, id_registro: int) -> Optional[Dict]:
        for registro in self.leer_todos():
            if registro["id"] == id_registro:
                return registro
        return None

    def actualizar(self, id_registro: int, datos: Dict) -> None:
        datos_sql = self._normalizar_para_guardar(datos, es_creacion=False)
        if not datos_sql:
            return
        basedatos.actualizar_registro(self.nombre_tabla, id_registro, datos_sql)

    def eliminar(self, id_registro: int) -> None:
        basedatos.eliminar_registro(self.nombre_tabla, id_registro)


    @staticmethod
    def _hashear_password(texto_plano: str) -> str:
        return bcrypt.hashpw(texto_plano.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


    def _normalizar_para_guardar(self, datos: Dict, es_creacion: bool) -> Dict:
        normalizado = {}
        for clave, valor in datos.items():
            campo = self._campos_por_nombre.get(clave)

            if campo is not None and campo.tipo == "password":
                if valor == "":
                    if es_creacion:
                        normalizado[clave] = None
                else:
                    normalizado[clave] = self._hashear_password(valor)
                continue

            if valor == "":
                normalizado[clave] = None
            elif campo is not None and campo.tipo == "numero":
                normalizado[clave] = float(valor)
            else:
                normalizado[clave] = valor
        return normalizado

    def _formatear_para_mostrar(self, fila: Dict) -> Dict:
        formateado = {"id": fila["id"]}
        for clave, valor in fila.items():
            if clave == "id":
                continue

            campo = self._campos_por_nombre.get(clave)
            if campo is not None and campo.tipo == "password":
                formateado[clave] = "••••••" if valor else ""
                continue

            if valor is None:
                formateado[clave] = ""
            elif isinstance(valor, float) and valor.is_integer():
                formateado[clave] = str(int(valor))
            else:
                formateado[clave] = str(valor)
        return formateado
