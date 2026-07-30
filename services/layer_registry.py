# ============================================================
# TERRI+ CORE
# Catálogo inteligente de capas geográficas
# ============================================================

from typing import Any, Optional

from services.query_executor import ejecutar_consulta


# ============================================================
# Registro principal de capas
# ============================================================

LAYER_REGISTRY: dict[str, dict[str, Any]] = {

    "predios": {
        "id": "predios",
        "nombre": "Predios de Sesquilé",
        "tabla": "predios_sesquile",
        "descripcion": (
            "Información catastral y territorial de los predios "
            "del municipio de Sesquilé."
        ),
        "geometria": "MULTIPOLYGON",
        "campo_geometria": "geom",
        "srid": 4326,
        "categoria": "Catastro",
        "campos_principales": [
            "id",
            "codigo",
            "NUMERO_PREDIAL",
            "NOMBRE",
            "NUMERO_DOCUMENTO",
            "DIRECCION",
            "DESTINO",
            "AREA DE TERRENO",
            "AREA CONSTRUIDA",
            "AVALUO 2025",
            "AVALUO 2026",
            "geom",
        ],
        "capacidades": [
            "conteo",
            "filtros",
            "estadisticas",
            "sumatorias",
            "promedios",
            "clasificacion",
            "interseccion",
            "proximidad",
            "buffer",
            "mapa_tematico",
        ],
        "ejemplos": [
            "¿Cuántos predios existen en Sesquilé?",
            "Muéstrame los cinco predios con mayor avalúo.",
            "¿Cuántos predios tienen destino agropecuario?",
            "Dibuja los predios con área superior a una hectárea.",
        ],
    },

    "construcciones": {
        "id": "construcciones",
        "nombre": "Construcciones de Sesquilé",
        "tabla": "construcciones_sesquile",
        "descripcion": (
            "Información espacial de construcciones, incluyendo "
            "año de construcción, altura y área."
        ),
        "geometria": "GEOMETRY",
        "campo_geometria": "geom",
        "srid": 4326,
        "categoria": "Crecimiento urbano",
        "campos_principales": [
            "id",
            "id_0",
            "longitude",
            "latitude",
            "const_year",
            "altura_m",
            "area_in_me",
            "geom",
        ],
        "capacidades": [
            "conteo",
            "filtros",
            "estadisticas",
            "densidad",
            "clasificacion",
            "interseccion",
            "proximidad",
            "mapa_tematico",
            "analisis_temporal",
        ],
        "ejemplos": [
            "¿Cuántas construcciones están registradas?",
            "Muéstrame las construcciones más recientes.",
            "¿Dónde están las construcciones de mayor altura?",
            "Genera un mapa de crecimiento por año.",
        ],
    },

    "contribuyentes_ica": {
        "id": "contribuyentes_ica",
        "nombre": "Contribuyentes ICA de Sesquilé",
        "tabla": "contribuyentes_ica_sesquile",
        "descripcion": (
            "Información geográfica y tributaria de las personas "
            "naturales y jurídicas registradas como contribuyentes "
            "del impuesto de industria y comercio en Sesquilé."
        ),
        "geometria": "POINT",
        "campo_geometria": "geom",
        "srid": 4326,
        "categoria": "Hacienda e ICA",
        "campos_principales": [
            "id",
            "Tipo.Documento",
            "No.Documento",
            "Nombre.del.contribuyente",
            "Razon.Social",
            "Naturaleza.Juridica",
            "Regimen.tributario",
            "Direccion",
            "Estado",
            "TIPO_CONTRIBUYENTE",
            "FORMATTED_ADDRESS",
            "geom",
        ],
        "capacidades": [
            "conteo",
            "filtros",
            "listados",
            "agrupacion",
            "estadisticas",
            "clasificacion",
            "interseccion",
            "proximidad",
            "buffer",
            "mapa_tematico",
        ],
        "ejemplos": [
            "¿Cuántos contribuyentes ICA existen en Sesquilé?",
            "Muéstrame los contribuyentes que son personas jurídicas.",
            "¿Cuántas personas naturales están registradas?",
            "Agrupa los contribuyentes por régimen tributario.",
            "Muéstrame los contribuyentes activos en el mapa.",
        ],
    },

    "servicios_publicos": {
        "id": "servicios_publicos",
        "nombre": "Servicios Públicos de Sesquilé",
        "tabla": "servicios_publicos_sesquile",
        "descripcion": (
            "Información geográfica sobre la disponibilidad, cobertura "
            "y operadores de servicios públicos domiciliarios asociados "
            "a predios y viviendas del municipio de Sesquilé."
        ),
        "geometria": "POINT",
        "campo_geometria": "geom",
        "srid": 4326,
        "categoria": "Servicios públicos",
        "campos_principales": [
            "id",
            "numero_predial",
            "folio_matricula",
            "propietario",
            "tipo_predio",
            "subtipo_predio",
            "uso_actual",
            "acueducto",
            "operador_acueducto",
            "alcantarillado",
            "operador_alcantarillado",
            "recoleccion_residuos",
            "operador_recoleccion_residuos",
            "internet",
            "operador_internet",
            "gas",
            "operador_gas",
            "tipo_vivienda",
            "observaciones",
            "geom",
        ],
        "capacidades": [
            "conteo",
            "filtros",
            "listados",
            "agrupacion",
            "estadisticas",
            "clasificacion",
            "interseccion",
            "proximidad",
            "buffer",
            "mapa_tematico",
        ],
        "ejemplos": [
            "¿Cuántos predios tienen servicio de acueducto?",
            "Muéstrame las viviendas sin internet.",
            "Muéstrame los predios que no tienen alcantarillado.",
            "Agrupa los registros por tipo de vivienda.",
            "Categoriza los puntos por operador de internet y diferéncialos por colores.",
            "Muéstrame los predios que tienen gas.",
            "¿Qué operador de gas predomina?",
            "¿Cuántos registros tienen recolección de residuos?",
        ],
    },

}

# ============================================================
# Consultar todas las capas registradas
# ============================================================

def obtener_capas_registradas() -> list[dict[str, Any]]:
    """
    Devuelve todas las capas registradas en TERRI+.
    """

    return list(LAYER_REGISTRY.values())


# ============================================================
# Consultar una capa por ID
# ============================================================

def obtener_capa(layer_id: str) -> Optional[dict[str, Any]]:
    """
    Devuelve la configuración de una capa específica.
    """

    if not layer_id:
        return None

    return LAYER_REGISTRY.get(
        layer_id.strip().lower()
    )


# ============================================================
# Consultar una capa por nombre de tabla
# ============================================================

def obtener_capa_por_tabla(
    tabla: str
) -> Optional[dict[str, Any]]:
    """
    Busca una capa usando el nombre físico de la tabla PostGIS.
    """

    if not tabla:
        return None

    tabla_normalizada = tabla.strip().lower()

    for capa in LAYER_REGISTRY.values():

        if capa["tabla"].lower() == tabla_normalizada:
            return capa

    return None


# ============================================================
# Verificar que una tabla exista en PostgreSQL
# ============================================================

def tabla_existe(tabla: str) -> bool:
    """
    Verifica si una tabla registrada realmente existe
    en el esquema public de PostgreSQL.
    """

    if not tabla:
        return False

    sql = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = :esquema
              AND table_name = :tabla
        ) AS existe;
    """

    resultado = ejecutar_consulta(
        sql,
        {
            "esquema": "public",
            "tabla": tabla,
        }
    )

    if not resultado:
        return False

    return bool(
        resultado[0].get("existe")
    )


# ============================================================
# Obtener campos reales de una tabla
# ============================================================

def obtener_campos_tabla(
    tabla: str
) -> list[dict[str, Any]]:
    """
    Consulta PostgreSQL para conocer los campos reales
    de una tabla registrada.
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
            "esquema": "public",
            "tabla": tabla,
        }
    )


# ============================================================
# Obtener información de geometría
# ============================================================

def obtener_geometria_tabla(
    tabla: str
) -> Optional[dict[str, Any]]:
    """
    Consulta geometry_columns para conocer el campo geométrico,
    tipo de geometría y sistema de referencia.
    """

    if not tabla:
        return None

    sql = """
        SELECT
            f_geometry_column AS campo_geometria,
            type AS tipo_geometria,
            srid
        FROM geometry_columns
        WHERE f_table_schema = :esquema
          AND f_table_name = :tabla
        LIMIT 1;
    """

    resultado = ejecutar_consulta(
        sql,
        {
            "esquema": "public",
            "tabla": tabla,
        }
    )

    if not resultado:
        return None

    return resultado[0]


# ============================================================
# Obtener cantidad de registros
# ============================================================

def obtener_total_registros(
    tabla: str
) -> Optional[int]:
    """
    Obtiene la cantidad total de registros de una tabla.

    El nombre de la tabla no se recibe directamente del usuario.
    Antes de ejecutar la consulta se valida contra el registro
    interno de capas.
    """

    capa = obtener_capa_por_tabla(tabla)

    if not capa:
        return None

    tabla_segura = capa["tabla"]

    sql = f"""
        SELECT COUNT(*) AS total
        FROM "{tabla_segura}";
    """

    resultado = ejecutar_consulta(sql)

    if not resultado:
        return 0

    return int(
        resultado[0].get("total", 0)
    )


# ============================================================
# Inspeccionar una capa registrada
# ============================================================

def inspeccionar_capa(
    layer_id: str
) -> Optional[dict[str, Any]]:
    """
    Combina la configuración registrada con la información
    real disponible en PostgreSQL/PostGIS.
    """

    capa = obtener_capa(layer_id)

    if not capa:
        return None

    tabla = capa["tabla"]

    try:

        existe = tabla_existe(tabla)

        if not existe:
            return {
                **capa,
                "disponible": False,
                "campos_reales": [],
                "geometria_real": None,
                "total_registros": None,
                "error": (
                    f"La tabla {tabla} no existe "
                    "en el esquema public."
                ),
            }

        campos_reales = obtener_campos_tabla(tabla)
        geometria_real = obtener_geometria_tabla(tabla)
        total_registros = obtener_total_registros(tabla)

        return {
            **capa,
            "disponible": True,
            "campos_reales": campos_reales,
            "geometria_real": geometria_real,
            "total_registros": total_registros,
            "error": None,
        }

    except Exception as error:

        print(
            f"⚠️ Error inspeccionando la capa "
            f"{layer_id}: {error}"
        )

        return {
            **capa,
            "disponible": False,
            "campos_reales": [],
            "geometria_real": None,
            "total_registros": None,
            "error": str(error),
        }


# ============================================================
# Construir catálogo enriquecido
# ============================================================

def obtener_catalogo_enriquecido() -> list[dict[str, Any]]:
    """
    Devuelve todas las capas registradas enriquecidas con
    información real de PostgreSQL/PostGIS.
    """

    catalogo: list[dict[str, Any]] = []

    for layer_id in LAYER_REGISTRY:

        capa_inspeccionada = inspeccionar_capa(
            layer_id
        )

        if capa_inspeccionada:
            catalogo.append(
                capa_inspeccionada
            )

    return catalogo


# ============================================================
# Obtener solamente capas disponibles
# ============================================================

def obtener_capas_disponibles() -> list[dict[str, Any]]:
    """
    Devuelve únicamente las capas cuya tabla existe
    actualmente en PostgreSQL.
    """

    catalogo = obtener_catalogo_enriquecido()

    return [
        capa
        for capa in catalogo
        if capa.get("disponible") is True
    ]


# ============================================================
# Construir contexto compacto para GPT
# ============================================================

def generar_contexto_capas(
    solo_disponibles: bool = True
) -> str:
    """
    Genera un contexto compacto para que GPT conozca las capas,
    tablas, campos y capacidades disponibles en TERRI+.
    """

    capas = (
        obtener_capas_disponibles()
        if solo_disponibles
        else obtener_capas_registradas()
    )

    if not capas:
        return (
            "No hay capas geográficas disponibles "
            "en el catálogo de TERRI+."
        )

    lineas: list[str] = []

    for capa in capas:

        campos = ", ".join(
            capa["campos_principales"]
        )

        capacidades = ", ".join(
            capa["capacidades"]
        )

        ejemplos = " | ".join(
            capa.get("ejemplos", [])
        )

        geometria_real = capa.get(
            "geometria_real"
        )

        tipo_geometria = (
            geometria_real.get("tipo_geometria")
            if geometria_real
            else capa.get("geometria")
        )

        campo_geometria = (
            geometria_real.get("campo_geometria")
            if geometria_real
            else capa.get("campo_geometria")
        )

        srid = (
            geometria_real.get("srid")
            if geometria_real
            else capa.get("srid")
        )

        bloque = (
            f"CAPA: {capa['nombre']}\n"
            f"ID: {capa['id']}\n"
            f"CATEGORÍA: {capa['categoria']}\n"
            f"TABLA: {capa['tabla']}\n"
            f"DESCRIPCIÓN: {capa['descripcion']}\n"
            f"TIPO DE GEOMETRÍA: {tipo_geometria}\n"
            f"CAMPO GEOMÉTRICO: {campo_geometria}\n"
            f"SRID: {srid}\n"
            f"CAMPOS PRINCIPALES: {campos}\n"
            f"CAPACIDADES: {capacidades}\n"
            f"EJEMPLOS DE CONSULTA: {ejemplos}\n"
        )

        if "total_registros" in capa:
            bloque += (
                f"TOTAL DE REGISTROS: "
                f"{capa.get('total_registros')}\n"
            )

        lineas.append(bloque)

    return "\n---\n".join(lineas)