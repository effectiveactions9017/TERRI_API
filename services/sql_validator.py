def validar_sql_seguro(sql: str) -> tuple[bool, str]:
    """
    Valida que el SQL generado por la IA sea seguro para ejecutarse.
    Por ahora solo permite consultas SELECT.
    """

    if not sql or not sql.strip():
        return False, "SQL vacío."

    sql_limpio = sql.strip().lower()

    palabras_bloqueadas = [
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "truncate",
        "create",
        "replace",
        "grant",
        "revoke",
        "execute",
        "copy"
    ]

    if not sql_limpio.startswith("select"):
        return False, "Solo se permiten consultas SELECT."

    for palabra in palabras_bloqueadas:
        if palabra in sql_limpio:
            return False, f"Consulta bloqueada por contener la palabra prohibida: {palabra}"

    return True, "SQL seguro."