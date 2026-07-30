from database import ejecutar_sql


def obtener_esquema_base() -> str:
    """
    Lee automáticamente las tablas y columnas del esquema público de PostGIS.
    Excluye tablas internas de PostGIS como spatial_ref_sys.
    """

    sql = """
        SELECT
            table_name,
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name NOT IN ('spatial_ref_sys', 'geometry_columns', 'geography_columns')
        ORDER BY table_name, ordinal_position;
    """

    filas = ejecutar_sql(sql)

    esquema = "ESQUEMA DISPONIBLE EN POSTGIS:\n"

    tabla_actual = None

    for fila in filas:
        tabla = fila["table_name"]
        columna = fila["column_name"]
        tipo = fila["data_type"]

        if tabla != tabla_actual:
            esquema += f"\nTABLA: {tabla}\n"
            tabla_actual = tabla

        esquema += f"- {columna}: {tipo}\n"

    return esquema