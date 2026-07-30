# ============================================================
# TERRI+ CORE
# Motor de conocimiento territorial
# ============================================================

from typing import Any, Optional

from services.layer_registry import (
    obtener_capa,
    obtener_capas_registradas,
    inspeccionar_capa,
)


# ============================================================
# Diccionario semántico de campos
# ============================================================

FIELD_KNOWLEDGE: dict[str, dict[str, dict[str, Any]]] = {

    # ========================================================
    # CAPA: PREDIOS
    # ========================================================

    "predios": {

        "id": {
            "nombre_amigable": "Identificador interno",
            "descripcion": (
                "Identificador único interno del registro "
                "en la base de datos."
            ),
            "tipo_semantico": "identificador",
            "unidad": None,
            "analisis": [
                "conteo",
            ],
            "sinonimos": [
                "id",
                "identificador",
                "registro",
            ],
        },

        "codigo": {
            "nombre_amigable": "Código del predio",
            "descripcion": (
                "Código interno utilizado para identificar "
                "el predio dentro del visor territorial."
            ),
            "tipo_semantico": "identificador",
            "unidad": None,
            "analisis": [
                "busqueda",
                "filtro",
                "agrupacion",
            ],
            "sinonimos": [
                "código",
                "codigo predial",
                "código del predio",
            ],
        },

        "NUMERO_PREDIAL": {
            "nombre_amigable": "Número predial",
            "descripcion": (
                "Número predial o código catastral utilizado "
                "para identificar oficialmente un inmueble."
            ),
            "tipo_semantico": "identificador_catastral",
            "unidad": None,
            "analisis": [
                "busqueda",
                "filtro",
                "agrupacion",
            ],
            "sinonimos": [
                "número predial",
                "numero predial",
                "código catastral",
                "codigo catastral",
                "ficha predial",
            ],
        },

        "NOMBRE": {
            "nombre_amigable": "Nombre del propietario",
            "descripcion": (
                "Nombre de la persona natural o jurídica "
                "relacionada con el registro predial."
            ),
            "tipo_semantico": "persona",
            "unidad": None,
            "analisis": [
                "busqueda",
                "filtro",
                "agrupacion",
            ],
            "sinonimos": [
                "nombre",
                "propietario",
                "dueño",
                "titular",
            ],
            "dato_sensible": True,
        },

        "NUMERO_DOCUMENTO": {
            "nombre_amigable": "Número de documento",
            "descripcion": (
                "Número de identificación de la persona "
                "relacionada con el predio."
            ),
            "tipo_semantico": "documento_identidad",
            "unidad": None,
            "analisis": [
                "busqueda",
                "filtro",
            ],
            "sinonimos": [
                "documento",
                "cédula",
                "cedula",
                "identificación",
                "identificacion",
                "nit",
            ],
            "dato_sensible": True,
        },

        "DIRECCION": {
            "nombre_amigable": "Dirección del predio",
            "descripcion": (
                "Dirección o referencia de ubicación "
                "registrada para el predio."
            ),
            "tipo_semantico": "direccion",
            "unidad": None,
            "analisis": [
                "busqueda",
                "filtro",
                "agrupacion",
            ],
            "sinonimos": [
                "dirección",
                "direccion",
                "ubicación",
                "ubicacion",
            ],
        },

        "DESTINO": {
            "nombre_amigable": "Destino económico",
            "descripcion": (
                "Clasificación del uso o destino económico "
                "asignado al predio."
            ),
            "tipo_semantico": "categoria",
            "unidad": None,
            "analisis": [
                "filtro",
                "agrupacion",
                "conteo",
                "porcentaje",
                "mapa_tematico",
            ],
            "sinonimos": [
                "destino",
                "destino económico",
                "uso del predio",
                "uso económico",
                "actividad del predio",
            ],
        },

        "AREA DE TERRENO": {
            "nombre_amigable": "Área de terreno",
            "descripcion": (
                "Superficie total del terreno asociada "
                "al predio."
            ),
            "tipo_semantico": "area",
            "tipo_fisico_actual": "texto",
            "tipo_requerido_sql": "numeric",
            "unidad": "metros cuadrados",
            "analisis": [
                "filtro",
                "suma",
                "promedio",
                "maximo",
                "minimo",
                "clasificacion",
                "mapa_tematico",
            ],
            "sinonimos": [
                "área",
                "area",
                "área del terreno",
                "area del terreno",
                "superficie",
                "tamaño del predio",
                "extension",
                "extensión",
                "hectáreas",
                "hectareas",
            ],
            "requiere_conversion": True,
            "expresion_sql": (
                'NULLIF(REGEXP_REPLACE("AREA DE TERRENO", '
                "'[^0-9,.-]', '', 'g'), '')"
                "::numeric"
            ),
        },

        "AREA CONSTRUIDA": {
            "nombre_amigable": "Área construida",
            "descripcion": (
                "Superficie construida registrada dentro "
                "del predio."
            ),
            "tipo_semantico": "area",
            "tipo_fisico_actual": "texto",
            "tipo_requerido_sql": "numeric",
            "unidad": "metros cuadrados",
            "analisis": [
                "filtro",
                "suma",
                "promedio",
                "maximo",
                "minimo",
                "clasificacion",
                "mapa_tematico",
            ],
            "sinonimos": [
                "área construida",
                "area construida",
                "construcción",
                "construccion",
                "superficie construida",
            ],
            "requiere_conversion": True,
            "expresion_sql": (
                'NULLIF(REGEXP_REPLACE("AREA CONSTRUIDA", '
                "'[^0-9,.-]', '', 'g'), '')"
                "::numeric"
            ),
        },

        "AVALUO 2025": {
            "nombre_amigable": "Avalúo catastral 2025",
            "descripcion": (
                "Valor catastral registrado para el predio "
                "durante la vigencia 2025."
            ),
            "tipo_semantico": "moneda",
            "tipo_fisico_actual": "texto",
            "tipo_requerido_sql": "numeric",
            "unidad": "pesos colombianos",
            "analisis": [
                "filtro",
                "suma",
                "promedio",
                "maximo",
                "minimo",
                "comparacion",
                "clasificacion",
                "mapa_tematico",
            ],
            "sinonimos": [
                "avalúo 2025",
                "avaluo 2025",
                "valor catastral 2025",
                "avalúo anterior",
                "avaluo anterior",
            ],

            "requiere_conversion": True,
            "expresion_sql": (
                'NULLIF(TRIM("AVALUO 2025"), \'\')'
                "::double precision"
             ),
          },

        "AVALUO 2026": {
    "nombre_amigable": "Avalúo catastral 2026",
    "descripcion": (
        "Valor catastral vigente registrado para "
        "el predio durante la vigencia 2026."
    ),
    "tipo_semantico": "moneda",
    "tipo_fisico_actual": "texto",
    "tipo_requerido_sql": "double precision",
    "unidad": "pesos colombianos",
    "analisis": [
        "filtro",
        "suma",
        "promedio",
        "maximo",
        "minimo",
        "comparacion",
        "clasificacion",
        "mapa_tematico",
    ],
    "sinonimos": [
        "avalúo",
        "avaluo",
        "avalúo actual",
        "avaluo actual",
        "avalúo 2026",
        "avaluo 2026",
        "valor catastral",
        "valor del predio",
        "predios más costosos",
        "predios de mayor valor",
    ],
    "requiere_conversion": True,
    "expresion_sql": (
        'NULLIF(TRIM("AVALUO 2026"), \'\')'
        "::double precision"
    ),
},

        "VIGENCIA": {
            "nombre_amigable": "Vigencia catastral",
            "descripcion": (
                "Año o periodo de vigencia de la "
                "información catastral."
            ),
            "tipo_semantico": "periodo",
            "unidad": "año",
            "analisis": [
                "filtro",
                "agrupacion",
                "comparacion",
            ],
            "sinonimos": [
                "vigencia",
                "año",
                "periodo",
            ],
        },

        "COMUNA": {
            "nombre_amigable": "Comuna o sector",
            "descripcion": (
                "Unidad territorial o sector asociado "
                "al predio."
            ),
            "tipo_semantico": "division_territorial",
            "unidad": None,
            "analisis": [
                "filtro",
                "agrupacion",
                "conteo",
                "estadisticas",
                "mapa_tematico",
            ],
            "sinonimos": [
                "comuna",
                "sector",
                "zona",
            ],
        },

        "vereda_cod": {
            "nombre_amigable": "Código de vereda",
            "descripcion": (
                "Código territorial de la vereda "
                "asociada al predio."
            ),
            "tipo_semantico": "division_territorial",
            "unidad": None,
            "analisis": [
                "filtro",
                "agrupacion",
                "conteo",
                "estadisticas",
                "mapa_tematico",
            ],
            "sinonimos": [
                "vereda",
                "código de vereda",
                "codigo de vereda",
            ],
        },

        "geom": {
            "nombre_amigable": "Geometría del predio",
            "descripcion": (
                "Representación espacial poligonal "
                "del predio."
            ),
            "tipo_semantico": "geometria",
            "unidad": None,
            "analisis": [
                "mapa",
                "interseccion",
                "proximidad",
                "buffer",
                "area_espacial",
                "centroide",
            ],
            "sinonimos": [
                "geometría",
                "geometria",
                "ubicación espacial",
                "mapa",
            ],
        },
    },

    # ========================================================
    # CAPA: CONSTRUCCIONES
    # ========================================================

    "construcciones": {

        "id": {
            "nombre_amigable": "Identificador interno",
            "descripcion": (
                "Identificador interno de la construcción."
            ),
            "tipo_semantico": "identificador",
            "unidad": None,
            "analisis": [
                "conteo",
            ],
            "sinonimos": [
                "id",
                "identificador",
            ],
        },

        "const_year": {
            "nombre_amigable": "Año de construcción",
            "descripcion": (
                "Año estimado o registrado en que fue "
                "realizada la construcción."
            ),
            "tipo_semantico": "año",
            "unidad": "año",
            "analisis": [
                "filtro",
                "agrupacion",
                "conteo",
                "comparacion",
                "analisis_temporal",
                "mapa_tematico",
            ],
            "sinonimos": [
                "año de construcción",
                "año construcción",
                "antigüedad",
                "construcciones recientes",
                "construcciones antiguas",
            ],
        },

        "altura_m": {
            "nombre_amigable": "Altura de la construcción",
            "descripcion": (
                "Altura estimada de la construcción."
            ),
            "tipo_semantico": "longitud",
            "unidad": "metros",
            "analisis": [
                "filtro",
                "promedio",
                "maximo",
                "minimo",
                "clasificacion",
                "mapa_tematico",
            ],
            "sinonimos": [
                "altura",
                "altura en metros",
                "construcciones más altas",
                "edificaciones altas",
            ],
        },

        "area_in_me": {
            "nombre_amigable": "Área de construcción",
            "descripcion": (
                "Superficie aproximada ocupada por "
                "la construcción."
            ),
            "tipo_semantico": "area",
            "unidad": "metros cuadrados",
            "analisis": [
                "filtro",
                "suma",
                "promedio",
                "maximo",
                "minimo",
                "clasificacion",
                "mapa_tematico",
            ],
            "sinonimos": [
                "área",
                "area",
                "área de construcción",
                "area de construccion",
                "superficie construida",
            ],
        },

        "longitude": {
            "nombre_amigable": "Longitud",
            "descripcion": (
                "Coordenada geográfica longitudinal "
                "de la construcción."
            ),
            "tipo_semantico": "coordenada",
            "unidad": "grados decimales",
            "analisis": [
                "ubicacion",
            ],
            "sinonimos": [
                "longitud",
                "coordenada x",
            ],
        },

        "latitude": {
            "nombre_amigable": "Latitud",
            "descripcion": (
                "Coordenada geográfica latitudinal "
                "de la construcción."
            ),
            "tipo_semantico": "coordenada",
            "unidad": "grados decimales",
            "analisis": [
                "ubicacion",
            ],
            "sinonimos": [
                "latitud",
                "coordenada y",
            ],
        },

        "geom": {
            "nombre_amigable": "Geometría de la construcción",
            "descripcion": (
                "Representación espacial poligonal "
                "de la construcción."
            ),
            "tipo_semantico": "geometria",
            "unidad": None,
            "analisis": [
                "mapa",
                "interseccion",
                "proximidad",
                "buffer",
                "area_espacial",
                "centroide",
                "densidad",
            ],
            "sinonimos": [
                "geometría",
                "geometria",
                "mapa",
                "ubicación espacial",
            ],
        },
    },
}


# ============================================================
# Obtener conocimiento de una capa
# ============================================================

def obtener_conocimiento_capa(
    layer_id: str
) -> dict[str, dict[str, Any]]:
    """
    Devuelve el conocimiento semántico registrado
    para una capa.
    """

    if not layer_id:
        return {}

    return FIELD_KNOWLEDGE.get(
        layer_id.strip().lower(),
        {}
    )


# ============================================================
# Obtener conocimiento de un campo
# ============================================================

def obtener_conocimiento_campo(
    layer_id: str,
    campo: str
) -> Optional[dict[str, Any]]:
    """
    Devuelve el conocimiento semántico de un campo.
    La búsqueda ignora mayúsculas y minúsculas.
    """

    if not layer_id or not campo:
        return None

    conocimiento_capa = obtener_conocimiento_capa(
        layer_id
    )

    campo_normalizado = campo.strip().lower()

    for nombre_campo, conocimiento in conocimiento_capa.items():

        if nombre_campo.lower() == campo_normalizado:
            return {
                "campo": nombre_campo,
                **conocimiento,
            }

    return None


# ============================================================
# Buscar campo mediante texto natural
# ============================================================

def buscar_campo_por_significado(
    layer_id: str,
    texto: str
) -> list[dict[str, Any]]:
    """
    Busca campos cuyos nombres o sinónimos aparezcan
    dentro de una pregunta en lenguaje natural.
    """

    if not layer_id or not texto:
        return []

    texto_normalizado = texto.strip().lower()

    coincidencias: list[dict[str, Any]] = []

    conocimiento_capa = obtener_conocimiento_capa(
        layer_id
    )

    for campo, conocimiento in conocimiento_capa.items():

        terminos = [
            campo.lower(),
            conocimiento
            .get("nombre_amigable", "")
            .lower(),
            *[
                sinonimo.lower()
                for sinonimo in conocimiento.get(
                    "sinonimos",
                    []
                )
            ],
        ]

        terminos_encontrados = [
            termino
            for termino in terminos
            if termino and termino in texto_normalizado
        ]

        if terminos_encontrados:

            coincidencias.append({
                "campo": campo,
                "nombre_amigable": conocimiento.get(
                    "nombre_amigable"
                ),
                "tipo_semantico": conocimiento.get(
                    "tipo_semantico"
                ),
                "coincidencias": terminos_encontrados,
                "conocimiento": conocimiento,
            })

    coincidencias.sort(
        key=lambda item: len(
            max(
                item["coincidencias"],
                key=len
            )
        ),
        reverse=True
    )

    return coincidencias


# ============================================================
# Obtener expresión SQL segura de un campo
# ============================================================

def obtener_expresion_sql(
    layer_id: str,
    campo: str
) -> Optional[str]:
    """
    Devuelve la expresión SQL recomendada para consultar
    un campo.

    Si el campo requiere conversión numérica devuelve
    la expresión configurada. De lo contrario devuelve
    el nombre correctamente entre comillas dobles.
    """

    conocimiento = obtener_conocimiento_campo(
        layer_id,
        campo
    )

    if not conocimiento:
        return None

    expresion = conocimiento.get(
        "expresion_sql"
    )

    if expresion:
        return expresion

    nombre_real = conocimiento["campo"]

    return f'"{nombre_real}"'


# ============================================================
# Validar conocimiento contra la tabla real
# ============================================================

def validar_conocimiento_capa(
    layer_id: str
) -> dict[str, Any]:
    """
    Compara los campos definidos en FIELD_KNOWLEDGE
    con los campos reales existentes en PostgreSQL.
    """

    capa = inspeccionar_capa(layer_id)

    if not capa:
        return {
            "layer_id": layer_id,
            "valida": False,
            "error": "La capa no está registrada.",
            "campos_validos": [],
            "campos_inexistentes": [],
            "campos_sin_conocimiento": [],
        }

    campos_reales = {
        campo["campo"]
        for campo in capa.get(
            "campos_reales",
            []
        )
    }

    campos_conocimiento = set(
        obtener_conocimiento_capa(layer_id).keys()
    )

    campos_validos = sorted(
        campos_reales.intersection(
            campos_conocimiento
        )
    )

    campos_inexistentes = sorted(
        campos_conocimiento.difference(
            campos_reales
        )
    )

    campos_sin_conocimiento = sorted(
        campos_reales.difference(
            campos_conocimiento
        )
    )

    return {
        "layer_id": layer_id,
        "nombre": capa.get("nombre"),
        "tabla": capa.get("tabla"),
        "disponible": capa.get("disponible"),
        "valida": (
            capa.get("disponible") is True
            and not campos_inexistentes
        ),
        "campos_validos": campos_validos,
        "campos_inexistentes": campos_inexistentes,
        "campos_sin_conocimiento": campos_sin_conocimiento,
    }


# ============================================================
# Generar contexto semántico para GPT
# ============================================================

def generar_contexto_conocimiento(
    layer_id: Optional[str] = None
) -> str:
    """
    Genera el contexto semántico que se enviará a GPT.

    Puede generar el contexto de una capa específica
    o de todas las capas registradas.
    """

    if layer_id:

        capa = obtener_capa(layer_id)

        if not capa:
            return (
                f"La capa '{layer_id}' no está registrada."
            )

        capas = [capa]

    else:
        capas = obtener_capas_registradas()

    bloques: list[str] = []

    for capa in capas:

        conocimiento = obtener_conocimiento_capa(
            capa["id"]
        )

        if not conocimiento:
            continue

        lineas_campos: list[str] = []

        for campo, datos in conocimiento.items():

            analisis = ", ".join(
                datos.get("analisis", [])
            )

            sinonimos = ", ".join(
                datos.get("sinonimos", [])
            )

            linea = (
                f"- CAMPO REAL: \"{campo}\"\n"
                f"  NOMBRE: {datos.get('nombre_amigable')}\n"
                f"  SIGNIFICADO: {datos.get('descripcion')}\n"
                f"  TIPO SEMÁNTICO: "
                f"{datos.get('tipo_semantico')}\n"
                f"  UNIDAD: "
                f"{datos.get('unidad') or 'No aplica'}\n"
                f"  ANÁLISIS PERMITIDOS: {analisis}\n"
                f"  SINÓNIMOS: {sinonimos}\n"
            )

            if datos.get("requiere_conversion"):

                linea += (
                    "  REQUIERE CONVERSIÓN NUMÉRICA: Sí\n"
                    f"  EXPRESIÓN SQL: "
                    f"{datos.get('expresion_sql')}\n"
                )

            lineas_campos.append(linea)

        bloque = (
            f"CAPA: {capa['nombre']}\n"
            f"ID DE CAPA: {capa['id']}\n"
            f"TABLA: {capa['tabla']}\n"
            f"CAMPOS Y SIGNIFICADOS:\n"
            + "\n".join(lineas_campos)
        )

        bloques.append(bloque)

    if not bloques:
        return (
            "No existe conocimiento semántico "
            "configurado para las capas solicitadas."
        )

    return "\n\n---\n\n".join(bloques)