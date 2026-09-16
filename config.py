# install mysql-connector-python para la conexión con MySQL
# install bcrypt para password hashing

CONFIG_MYSQL = {
    "host": "localhost",
    "user": "root",
    "password": "",          
    "database": "crud",
}

TIPOS_VISIBLES = {
    "Texto libre": "texto",
    "Número": "numero",
    "Email": "email",
    "Contraseña": "password",
    "Selección (lista desplegable)": "select",
    "Fecha": "fecha",
    "Relación con otra entidad": "relacion",
}