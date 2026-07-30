# =====================================================
# TERRI+ - EJECUTOR DE CONSULTAS
# =====================================================

from typing import Any

from database import ejecutar_sql


def ejecutar_consulta(
    sql: str,
    parametros: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """
    Ejecuta una consulta SQL previamente validada
    y devuelve una lista de registros.
    """

    return ejecutar_sql(
        sql=sql,
        parametros=parametros
    )