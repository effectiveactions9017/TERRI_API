# ============================================================
# TERRI+ CORE
# Descubrimiento automático de capas PostGIS
# ============================================================

from typing import Any, Optional

from services.query_executor import ejecutar_consulta


# ============================================================
# Tablas internas que no deben tratarse como capas del visor
# ============================================================

TABLAS_EXCLUIDAS = {
    "spatial_ref_sys",
}


# ============================================================
# Descubrir tablas espaciales
# ============================================================

def descubrir_capas_espaciales() -> list[dict[str, Any]]:
    """
    Consulta geometry_columns y devuelve todas las tablas
    espaciales disponibles en el esquema public.
    """

    sql = """
        SELECT
            f_table_schema AS esquema,
            f_table_name AS tabla,
            f_geometry_column AS campo_geometria,
            type AS tipo_geometria,
            srid
        FROM geometry_columns
        WHERE f_table_schema = :esquema
        ORDER BY f_table_name;
    """

    resultado = ejecutar_consulta(
        sql,
        {
            "esquema": "public",
        }
    )

    return [
        capa
        for capa in resultado
        if capa.get("tabla") not in TABLAS_EXCLUIDAS
    ]


# ============================================================
# Obtener campos de una tabla
# ============================================================

def obtener_campos_capa(
    tabla: str,
    esquema: str = "public",
) -> list[dict[str, Any]]:
    """
    Devuelve los campos reales de una tabla PostgreSQL.
    """

    if not tabla:
        return []

    sql = """
        SELECT
            column_name AS campo,
            data_type AS tipo_dato,
            udt_name AS tipo_interno,
            is_nullable AS permite_nulos,
            ordinal_position AS posicion
        FROM information_schema.columns
        WHERE table_schema = :esquema
          AND table_name = :tabla
        ORDER BY ordinal_position;
    """

    return ejecutar_consulta(
        sql,
        {
            "esquema": esquema,
            "tabla": tabla,
        }
    )


# ============================================================
# Validar identificador PostgreSQL
# ============================================================

def validar_identificador(nombre: str) -> bool:
    """
    Valida que un nombre de tabla o esquema provenga de una
    lista segura de caracteres.

    Los identificadores no se parametrizan directamente en SQL,
    por lo que deben validarse antes de interpolarlos.
    """

    if not nombre:
        return False

    return all(
        caracter.isalnum() or caracter == "_"
        for caracter in nombre
    )


# ============================================================
# Obtener total de registros
# ============================================================

def obtener_total_capa(
    tabla: str,
    esquema: str = "public",
) -> Optional[int]:
    """
    Obtiene la cantidad de registros de una tabla espacial.
    """

    if not validar_identificador(tabla):
        return None

    if not validar_identificador(esquema):
        return None

    sql = f"""
        SELECT COUNT(*) AS total
        FROM "{esquema}"."{tabla}";
    """

    resultado = ejecutar_consulta(sql)

    if not resultado:
        return 0

    return int(
        resultado[0].get("total", 0)
    )


# ============================================================
# Construir identificador amigable
# ============================================================

def construir_layer_id(tabla: str) -> str:
    """
    Convierte el nombre físico de una tabla en un identificador
    interno sencillo para TERRI+.
    """

    layer_id = tabla.strip().lower()

    sufijos = [
        "_sesquile",
        "_ssk",
        "_municipio_sesquile",
    ]

    for sufijo in sufijos:
        if layer_id.endswith(sufijo):
            layer_id = layer_id[:-len(sufijo)]
            break

    return layer_id


# ============================================================
# Construir nombre amigable
# ============================================================

def construir_nombre_amigable(tabla: str) -> str:
    """
    Convierte un nombre de tabla en una etiqueta legible.
    """

    nombre = tabla.replace("_", " ").strip()

    return nombre.title()


# ============================================================
# Inspeccionar una capa
# ============================================================

def inspeccionar_capa_automatica(
    capa: dict[str, Any]
) -> dict[str, Any]:
    """
    Enriquece una capa detectada con sus campos y total
    de registros.
    """

    tabla = capa.get("tabla")
    esquema = capa.get("esquema", "public")

    campos = obtener_campos_capa(
        tabla=tabla,
        esquema=esquema,
    )

    total = obtener_total_capa(
        tabla=tabla,
        esquema=esquema,
    )

    return {
        "id": construir_layer_id(tabla),
        "nombre": construir_nombre_amigable(tabla),
        "tabla": tabla,
        "esquema": esquema,
        "campo_geometria": capa.get("campo_geometria"),
        "tipo_geometria": capa.get("tipo_geometria"),
        "srid": capa.get("srid"),
        "total_registros": total,
        "campos": campos,
        "disponible": True,
        "origen": "postgis",
    }


# ============================================================
# Construir catálogo automático completo
# ============================================================

def construir_catalogo_automatico() -> list[dict[str, Any]]:
    """
    Descubre e inspecciona todas las tablas espaciales
    disponibles en PostGIS.
    """

    capas = descubrir_capas_espaciales()
    catalogo: list[dict[str, Any]] = []

    for capa in capas:

        try:
            catalogo.append(
                inspeccionar_capa_automatica(capa)
            )

        except Exception as error:

            print(
                f"⚠️ No fue posible inspeccionar la capa "
                f"{capa.get('tabla')}: {error}"
            )

            catalogo.append({
                "id": construir_layer_id(
                    capa.get("tabla", "sin_nombre")
                ),
                "nombre": construir_nombre_amigable(
                    capa.get("tabla", "sin_nombre")
                ),
                **capa,
                "campos": [],
                "total_registros": None,
                "disponible": False,
                "origen": "postgis",
                "error": str(error),
            })

    return catalogo


# ============================================================
# Generar contexto compacto para GPT
# ============================================================

def generar_contexto_catalogo_automatico() -> str:
    """
    Genera un contexto compacto con las capas detectadas
    automáticamente en PostGIS.
    """

    catalogo = construir_catalogo_automatico()

    if not catalogo:
        return (
            "No se detectaron capas espaciales "
            "en el esquema public."
        )

    bloques: list[str] = []

    for capa in catalogo:

        campos = [
            campo.get("campo")
            for campo in capa.get("campos", [])
            if campo.get("campo")
        ]

        bloque = (
            f"CAPA: {capa.get('nombre')}\n"
            f"ID: {capa.get('id')}\n"
            f"TABLA: {capa.get('tabla')}\n"
            f"ESQUEMA: {capa.get('esquema')}\n"
            f"GEOMETRÍA: {capa.get('tipo_geometria')}\n"
            f"CAMPO GEOMÉTRICO: "
            f"{capa.get('campo_geometria')}\n"
            f"SRID: {capa.get('srid')}\n"
            f"TOTAL REGISTROS: "
            f"{capa.get('total_registros')}\n"
            f"CAMPOS: {', '.join(campos)}\n"
        )

        bloques.append(bloque)

    return "\n---\n".join(bloques)