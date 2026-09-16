import json
import re
import mysql.connector
from mysql.connector import Error
from excepciones import ErrorRelacion, ErrorBaseDatos
from config import CONFIG_MYSQL

TABLA_META = "_entidades_meta"

# Códigos de error de MySQL relevantes (https://dev.mysql.com/doc/mysql-errors/8.0/en/server-error-reference.html)
ER_ROW_IS_REFERENCED_2 = 1451   # no se puede borrar/actualizar: algo lo referencia
ER_NO_REFERENCED_ROW_2 = 1452   # el valor de la FK no existe en la tabla referenciada
ER_DUP_ENTRY = 1062             # entrada duplicada para un campo UNIQUE


# Conexión
def _conectar(usar_bd: bool = True):
    
    config = dict(CONFIG_MYSQL)
    if not usar_bd:
        config.pop("database", None)
    try:
        return mysql.connector.connect(**config)
    except Error as error:
        raise ErrorBaseDatos(
            "No se pudo conectar con la base de datos MySQL. Verificá que el "
            "servidor esté encendido y que los datos de conexión en "
            "basedatos.py (CONFIG_MYSQL) sean correctos."
        ) from error


def _relanzar_como_error_base_datos(error: Error):

    raise ErrorBaseDatos(
        f"Ocurrió un problema al comunicarse con la base de datos: {error}"
    ) from error


def inicializar_base_datos() -> None:

    conexion = _conectar(usar_bd=False)
    cursor = conexion.cursor()
    try:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{CONFIG_MYSQL['database']}` "
            f"CHARACTER SET utf8mb4"
        )
    except Error as error:
        _relanzar_como_error_base_datos(error)
    finally:
        cursor.close()
        conexion.close()

    conexion = _conectar()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLA_META} (
                nombre_entidad VARCHAR(150) PRIMARY KEY,
                nombre_tabla   VARCHAR(150) NOT NULL,
                campos_json    LONGTEXT NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        conexion.commit()
    except Error as error:
        _relanzar_como_error_base_datos(error)
    finally:
        cursor.close()
        conexion.close()


# Utilidades internas de seguridad para nombres dinámicos
_PATRON_IDENTIFICADOR = re.compile(r"^[a-z0-9_]+$")


def _slug_tabla(nombre_entidad: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9_]+", "_", nombre_entidad.strip().lower()).strip("_")
    return f"ent_{base or 'entidad'}"


def _validar_identificador(nombre: str) -> str:
    if not _PATRON_IDENTIFICADOR.fullmatch(nombre):
        raise ValueError(f"Nombre no permitido para SQL: '{nombre}'")
    return nombre


def _tipo_columna_sql(tipo_logico: str) -> str:
    """Traduce el tipo lógico de CampoDef a un tipo de columna MySQL."""
    if tipo_logico == "numero":
        return "DOUBLE"
    if tipo_logico == "relacion":
        return "INT"   # guarda el id del registro relacionado
    return "VARCHAR(500)"


# Definición de entidades (metadatos)
def listar_entidades() -> dict:

    conexion = _conectar()
    cursor = conexion.cursor()
    try:
        cursor.execute(f"SELECT nombre_entidad, nombre_tabla, campos_json FROM {TABLA_META}")
        filas = cursor.fetchall()
    except Error as error:
        _relanzar_como_error_base_datos(error)
    finally:
        cursor.close()
        conexion.close()

    resultado = {}
    for nombre_entidad, nombre_tabla, campos_json in filas:
        resultado[nombre_entidad] = {
            "nombre_tabla": nombre_tabla,
            "campos": json.loads(campos_json),
        }
    return resultado


def _tabla_de_entidad(nombre_entidad: str) -> str:

    conexion = _conectar()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            f"SELECT nombre_tabla FROM {TABLA_META} WHERE nombre_entidad = %s",
            (nombre_entidad,),
        )
        fila = cursor.fetchone()
    except Error as error:
        _relanzar_como_error_base_datos(error)
    finally:
        cursor.close()
        conexion.close()
    if fila is None:
        raise ValueError(f"La entidad relacionada '{nombre_entidad}' no existe.")
    return fila[0]


def entidades_que_dependen_de(nombre_entidad: str) -> list:

    info = listar_entidades()
    if nombre_entidad not in info:
        return []
    tabla_objetivo = info[nombre_entidad]["nombre_tabla"]

    conexion = _conectar()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            """
            SELECT DISTINCT TABLE_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE REFERENCED_TABLE_SCHEMA = %s
              AND REFERENCED_TABLE_NAME = %s
            """,
            (CONFIG_MYSQL["database"], tabla_objetivo),
        )
        tablas_dependientes = {fila[0] for fila in cursor.fetchall()}
    except Error as error:
        _relanzar_como_error_base_datos(error)
    finally:
        cursor.close()
        conexion.close()

    tabla_a_entidad = {v["nombre_tabla"]: k for k, v in info.items()}
    return [
        tabla_a_entidad[tabla] for tabla in tablas_dependientes if tabla in tabla_a_entidad
    ]


def crear_tabla_entidad(nombre_entidad: str, campos: list) -> str:
 
    nombre_tabla = _validar_identificador(_slug_tabla(nombre_entidad))

    columnas_sql = ["id INT AUTO_INCREMENT PRIMARY KEY"]
    claves_foraneas_sql = []

    for campo in campos:
        nombre_columna = _validar_identificador(campo["nombre"])
        definicion_columna = f"`{nombre_columna}` {_tipo_columna_sql(campo['tipo'])}"
        if campo.get("unico"):
            definicion_columna += " UNIQUE"
        definicion_columna += " NULL"
        columnas_sql.append(definicion_columna)

        if campo["tipo"] == "relacion":
            tabla_relacionada = _tabla_de_entidad(campo["entidad_relacionada"])
            claves_foraneas_sql.append(
                f"FOREIGN KEY (`{nombre_columna}`) REFERENCES `{tabla_relacionada}`(id) "
                f"ON DELETE RESTRICT ON UPDATE CASCADE"
            )

    definicion_sql = columnas_sql + claves_foraneas_sql

    conexion = _conectar()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            f"CREATE TABLE `{nombre_tabla}` ({', '.join(definicion_sql)}) "
            f"ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        )
        cursor.execute(
            f"INSERT INTO {TABLA_META} (nombre_entidad, nombre_tabla, campos_json) "
            f"VALUES (%s, %s, %s)",
            (nombre_entidad, nombre_tabla, json.dumps(campos, ensure_ascii=False)),
        )
        conexion.commit()
    except Error as error:
        conexion.rollback()
        _relanzar_como_error_base_datos(error)
    finally:
        cursor.close()
        conexion.close()

    return nombre_tabla


def eliminar_entidad(nombre_entidad: str, nombre_tabla: str) -> None:

    dependientes = entidades_que_dependen_de(nombre_entidad)
    if dependientes:
        raise ErrorRelacion(
            f"No se puede eliminar '{nombre_entidad}' porque la(s) entidad(es) "
            f"{', '.join(dependientes)} tienen un campo que la referencia. "
            f"Eliminá primero esa relación (o esa entidad)."
        )

    nombre_tabla = _validar_identificador(nombre_tabla)
    conexion = _conectar()
    cursor = conexion.cursor()
    try:
        cursor.execute(f"DROP TABLE IF EXISTS `{nombre_tabla}`")
        cursor.execute(f"DELETE FROM {TABLA_META} WHERE nombre_entidad = %s", (nombre_entidad,))
        conexion.commit()
    except Error as error:
        conexion.rollback()
        _relanzar_como_error_base_datos(error)
    finally:
        cursor.close()
        conexion.close()


# CRUD sobre los registros de una entidad puntual
def insertar_registro(nombre_tabla: str, datos: dict) -> int:
    nombre_tabla = _validar_identificador(nombre_tabla)
    columnas = [_validar_identificador(c) for c in datos.keys()]
    marcadores = ", ".join(["%s"] * len(columnas))
    columnas_sql = ", ".join(f"`{c}`" for c in columnas)
    valores = [datos[c] for c in columnas]

    conexion = _conectar()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            f"INSERT INTO `{nombre_tabla}` ({columnas_sql}) VALUES ({marcadores})",
            valores,
        )
        conexion.commit()
        return cursor.lastrowid
    except Error as error:
        conexion.rollback()
        if error.errno == ER_NO_REFERENCED_ROW_2:
            raise ErrorRelacion(
                "El valor seleccionado en un campo de relación ya no es válido "
                "(puede que ese registro se haya eliminado). Actualizá la lista "
                "e intentá de nuevo."
            ) from error
        if error.errno == ER_DUP_ENTRY:
            raise ErrorRelacion(
                "Ya existe un registro con ese mismo valor en un campo marcado "
                "como único. Elegí un valor distinto."
            ) from error
        _relanzar_como_error_base_datos(error)
    finally:
        cursor.close()
        conexion.close()


def listar_registros(nombre_tabla: str) -> list:

    nombre_tabla = _validar_identificador(nombre_tabla)
    conexion = _conectar()
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute(f"SELECT * FROM `{nombre_tabla}` ORDER BY id")
        return cursor.fetchall()
    except Error as error:
        _relanzar_como_error_base_datos(error)
    finally:
        cursor.close()
        conexion.close()


def actualizar_registro(nombre_tabla: str, id_registro: int, datos: dict) -> None:

    nombre_tabla = _validar_identificador(nombre_tabla)
    columnas = [_validar_identificador(c) for c in datos.keys()]
    set_sql = ", ".join(f"`{c}` = %s" for c in columnas)
    valores = [datos[c] for c in columnas] + [id_registro]

    conexion = _conectar()
    cursor = conexion.cursor()
    try:
        cursor.execute(f"UPDATE `{nombre_tabla}` SET {set_sql} WHERE id = %s", valores)
        conexion.commit()
    except Error as error:
        conexion.rollback()
        if error.errno == ER_NO_REFERENCED_ROW_2:
            raise ErrorRelacion(
                "El valor seleccionado en un campo de relación ya no es válido "
                "(puede que ese registro se haya eliminado). Actualizá la lista "
                "e intentá de nuevo."
            ) from error
        if error.errno == ER_DUP_ENTRY:
            raise ErrorRelacion(
                "Ya existe un registro con ese mismo valor en un campo marcado "
                "como único. Elegí un valor distinto."
            ) from error
        _relanzar_como_error_base_datos(error)
    finally:
        cursor.close()
        conexion.close()


def eliminar_registro(nombre_tabla: str, id_registro: int) -> None:

    nombre_tabla = _validar_identificador(nombre_tabla)
    conexion = _conectar()
    cursor = conexion.cursor()
    try:
        cursor.execute(f"DELETE FROM `{nombre_tabla}` WHERE id = %s", (id_registro,))
        conexion.commit()
    except Error as error:
        conexion.rollback()
        if error.errno == ER_ROW_IS_REFERENCED_2:
            raise ErrorRelacion(
                "No se puede eliminar este registro porque otro registro lo está "
                "usando en una relación. Eliminá primero esos registros "
                "dependientes, o cambiales la relación."
            ) from error
        _relanzar_como_error_base_datos(error)
    finally:
        cursor.close()
        conexion.close()
