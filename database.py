# =====================================================
# 🗄️ CONEXIÓN POSTGIS - TERRI+
# =====================================================

import os
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


# =====================================================
# Variables de entorno
# =====================================================

load_dotenv()


DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


# =====================================================
# Validación básica de configuración
# =====================================================

VARIABLES_REQUERIDAS = {
    "DB_HOST": DB_HOST,
    "DB_PORT": DB_PORT,
    "DB_NAME": DB_NAME,
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
}


variables_faltantes = [
    nombre
    for nombre, valor in VARIABLES_REQUERIDAS.items()
    if not valor
]


if variables_faltantes:
    raise RuntimeError(
        "Faltan variables de entorno requeridas: "
        + ", ".join(variables_faltantes)
    )


# =====================================================
# URL de conexión
# =====================================================

DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


# =====================================================
# Motor SQLAlchemy
# =====================================================

engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
)


# =====================================================
# Ejecutar consulta SQL
# =====================================================

def ejecutar_sql(
    sql: str,
    parametros: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """
    Ejecuta una consulta SQL y devuelve el resultado
    como una lista de diccionarios.

    Es compatible con:

    ejecutar_sql("SELECT * FROM predios_sesquile")

    y con consultas parametrizadas:

    ejecutar_sql(
        "SELECT * FROM predios_sesquile WHERE codigo = :codigo",
        {"codigo": "123"}
    )
    """

    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("La consulta SQL no puede estar vacía.")

    parametros = parametros or {}

    try:
        with engine.connect() as conexion:

            resultado = conexion.execute(
                text(sql),
                parametros
            )

            if not resultado.returns_rows:
                return []

            filas = resultado.fetchall()

            return [
                dict(fila._mapping)
                for fila in filas
            ]

    except Exception as error:

        print(f"❌ Error ejecutando SQL: {error}")

        raise