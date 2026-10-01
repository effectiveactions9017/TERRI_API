# ============================================================
# TERRI+
# GEOBOUNDARIES SERVICE
# Límites administrativos internacionales
# ============================================================

from typing import Any, Dict, List, Optional

import requests


# ============================================================
# CONFIGURACIÓN
# ============================================================

GEOBOUNDARIES_BASE_URL = (
    "https://www.geoboundaries.org/api/current/gbOpen"
)

GEOBOUNDARIES_TIMEOUT = 30


# ============================================================
# VALIDAR NIVEL ADMINISTRATIVO
# ============================================================

def normalizar_nivel(
    nivel: str
) -> str:

    nivel = str(
        nivel or "ADM0"
    ).strip().upper()

    niveles_validos = {
        "ADM0",
        "ADM1",
        "ADM2",
        "ADM3",
        "ADM4",
        "ADM5"
    }

    if nivel not in niveles_validos:

        raise ValueError(
            f"Nivel administrativo no válido: {nivel}"
        )

    return nivel


# ============================================================
# VALIDAR CÓDIGO ISO3
# ============================================================

def normalizar_iso3(
    codigo_iso3: str
) -> str:

    codigo = str(
        codigo_iso3 or ""
    ).strip().upper()

    if len(codigo) != 3:

        raise ValueError(
            "El código del país debe ser ISO3, "
            "por ejemplo COL, ECU, PER o ESP."
        )

    return codigo


# ============================================================
# VERIFICAR SERVICIO
# ============================================================

def verificar_geoboundaries() -> Dict[str, Any]:

    try:

        resultado = obtener_metadatos_geoboundaries(
            codigo_iso3="COL",
            nivel="ADM0"
        )

        if not resultado.get(
            "ok",
            False
        ):

            return resultado

        return {
            "ok": True,
            "fuente": "geoBoundaries",
            "mensaje": (
                "Servicio geoBoundaries disponible."
            )
        }

    except Exception as error:

        return {
            "ok": False,
            "fuente": "geoBoundaries",
            "error": str(error)
        }


# ============================================================
# OBTENER METADATOS
# ============================================================

def obtener_metadatos_geoboundaries(
    codigo_iso3: str,
    nivel: str = "ADM0"
) -> Dict[str, Any]:

    try:

        codigo = normalizar_iso3(
            codigo_iso3
        )

        nivel_normalizado = normalizar_nivel(
            nivel
        )

        url = (
            f"{GEOBOUNDARIES_BASE_URL}/"
            f"{codigo}/{nivel_normalizado}/"
        )

        respuesta = requests.get(
            url,
            timeout=GEOBOUNDARIES_TIMEOUT
        )

        # ----------------------------------------------------
        # NIVEL O PAÍS NO DISPONIBLE
        # ----------------------------------------------------

        if respuesta.status_code == 404:

            return {
                "ok": False,
                "tipo": "sin_resultado",
                "fuente": "geoBoundaries",
                "codigo_iso3": codigo,
                "nivel": nivel_normalizado,
                "mensaje": (
                    f"geoBoundaries no tiene disponible "
                    f"{nivel_normalizado} para {codigo}."
                )
            }

        respuesta.raise_for_status()

        datos = respuesta.json()

        if not isinstance(
            datos,
            dict
        ):

            return {
                "ok": False,
                "tipo": "respuesta_invalida",
                "fuente": "geoBoundaries",
                "mensaje": (
                    "geoBoundaries devolvió una "
                    "respuesta inesperada."
                )
            }

        return {
            "ok": True,
            "fuente": "geoBoundaries",
            "codigo_iso3": codigo,
            "nivel": nivel_normalizado,
            "metadatos": datos
        }

    except requests.exceptions.Timeout:

        return {
            "ok": False,
            "tipo": "timeout",
            "fuente": "geoBoundaries",
            "mensaje": (
                "geoBoundaries tardó demasiado "
                "en responder."
            )
        }

    except requests.exceptions.RequestException as error:

        return {
            "ok": False,
            "tipo": "conexion",
            "fuente": "geoBoundaries",
            "mensaje": (
                "No fue posible consultar "
                "geoBoundaries."
            ),
            "error": str(error)
        }

    except ValueError as error:

        return {
            "ok": False,
            "tipo": "consulta_invalida",
            "fuente": "geoBoundaries",
            "mensaje": str(error)
        }


# ============================================================
# RECORRER COORDENADAS GEOJSON
# ============================================================

def extraer_coordenadas(
    coordenadas: Any
) -> List[List[float]]:

    resultado: List[List[float]] = []

    if not isinstance(
        coordenadas,
        list
    ):

        return resultado

    # --------------------------------------------------------
    # PAR [LONGITUD, LATITUD]
    # --------------------------------------------------------

    if (
        len(coordenadas) >= 2
        and isinstance(
            coordenadas[0],
            (int, float)
        )
        and isinstance(
            coordenadas[1],
            (int, float)
        )
    ):

        resultado.append(
            [
                float(coordenadas[0]),
                float(coordenadas[1])
            ]
        )

        return resultado

    # --------------------------------------------------------
    # LISTAS ANIDADAS
    # --------------------------------------------------------

    for elemento in coordenadas:

        resultado.extend(
            extraer_coordenadas(
                elemento
            )
        )

    return resultado


# ============================================================
# CALCULAR BBOX FEATURE COLLECTION
# ============================================================

def calcular_bbox(
    geojson: Dict[str, Any]
) -> Optional[List[float]]:

    puntos: List[List[float]] = []

    features = geojson.get(
        "features",
        []
    )

    if not isinstance(
        features,
        list
    ):

        return None

    for feature in features:

        if not isinstance(
            feature,
            dict
        ):

            continue

        geometria = feature.get(
            "geometry"
        )

        if not isinstance(
            geometria,
            dict
        ):

            continue

        puntos.extend(
            extraer_coordenadas(
                geometria.get(
                    "coordinates"
                )
            )
        )

    if not puntos:

        return None

    longitudes = [
        punto[0]
        for punto in puntos
    ]

    latitudes = [
        punto[1]
        for punto in puntos
    ]

    return [
        min(longitudes),
        min(latitudes),
        max(longitudes),
        max(latitudes)
    ]


# ============================================================
# DESCARGAR GEOJSON
# ============================================================

def obtener_geojson_geoboundaries(
    codigo_iso3: str,
    nivel: str = "ADM0",
    simplificado: bool = True
) -> Dict[str, Any]:

    # --------------------------------------------------------
    # NORMALIZAR PARÁMETROS
    # --------------------------------------------------------

    try:

        codigo = normalizar_iso3(
            codigo_iso3
        )

        nivel_normalizado = normalizar_nivel(
            nivel
        )

    except ValueError as error:

        return {
            "ok": False,
            "tipo": "consulta_invalida",
            "fuente": "geoBoundaries",
            "mensaje": str(error)
        }


    # --------------------------------------------------------
    # CONSULTAR METADATOS
    # --------------------------------------------------------

    metadata_response = (
        obtener_metadatos_geoboundaries(
            codigo_iso3=codigo,
            nivel=nivel_normalizado
        )
    )

    if not metadata_response.get(
        "ok",
        False
    ):

        return metadata_response


    metadata = metadata_response.get(
        "metadatos",
        {}
    )


    # --------------------------------------------------------
    # SELECCIONAR GEOJSON
    #
    # Para visualización usamos por defecto la versión
    # simplificada.
    #
    # Para análisis geométrico puede utilizarse:
    #
    # simplificado=False
    #
    # y así descargar la geometría completa.
    # --------------------------------------------------------

    if simplificado:

        geojson_url = (
            metadata.get(
                "simplifiedGeometryGeoJSON"
            )
            or metadata.get(
                "gjDownloadURL"
            )
        )

    else:

        geojson_url = metadata.get(
            "gjDownloadURL"
        )


    if not geojson_url:

        return {
            "ok": False,
            "tipo": "sin_geometria",
            "fuente": "geoBoundaries",
            "codigo_iso3": codigo,
            "nivel": nivel_normalizado,
            "mensaje": (
                "geoBoundaries no proporcionó "
                "un enlace GeoJSON."
            )
        }


    # --------------------------------------------------------
    # DESCARGAR GEOJSON
    # --------------------------------------------------------

    try:

        respuesta = requests.get(
            geojson_url,
            timeout=GEOBOUNDARIES_TIMEOUT
        )

        respuesta.raise_for_status()

        geojson = respuesta.json()

    except requests.exceptions.Timeout:

        return {
            "ok": False,
            "tipo": "timeout",
            "fuente": "geoBoundaries",
            "codigo_iso3": codigo,
            "nivel": nivel_normalizado,
            "mensaje": (
                "La geometría de geoBoundaries "
                "tardó demasiado en descargarse."
            )
        }

    except requests.exceptions.RequestException as error:

        return {
            "ok": False,
            "tipo": "conexion",
            "fuente": "geoBoundaries",
            "codigo_iso3": codigo,
            "nivel": nivel_normalizado,
            "mensaje": (
                "No fue posible descargar "
                "la geometría de geoBoundaries."
            ),
            "error": str(error)
        }

    except ValueError:

        return {
            "ok": False,
            "tipo": "respuesta_invalida",
            "fuente": "geoBoundaries",
            "codigo_iso3": codigo,
            "nivel": nivel_normalizado,
            "mensaje": (
                "El recurso descargado no contiene "
                "un GeoJSON válido."
            )
        }


    # --------------------------------------------------------
    # VALIDAR FEATURE COLLECTION
    # --------------------------------------------------------

    if not isinstance(
        geojson,
        dict
    ):

        return {
            "ok": False,
            "tipo": "respuesta_invalida",
            "fuente": "geoBoundaries",
            "codigo_iso3": codigo,
            "nivel": nivel_normalizado,
            "mensaje": (
                "La geometría descargada "
                "no es válida."
            )
        }


    if geojson.get(
        "type"
    ) != "FeatureCollection":

        return {
            "ok": False,
            "tipo": "respuesta_invalida",
            "fuente": "geoBoundaries",
            "codigo_iso3": codigo,
            "nivel": nivel_normalizado,
            "mensaje": (
                "El resultado no corresponde "
                "a un FeatureCollection."
            )
        }


    features = geojson.get(
        "features",
        []
    )


    if not isinstance(
        features,
        list
    ):

        return {
            "ok": False,
            "tipo": "respuesta_invalida",
            "fuente": "geoBoundaries",
            "codigo_iso3": codigo,
            "nivel": nivel_normalizado,
            "mensaje": (
                "El FeatureCollection no contiene "
                "una lista válida de entidades."
            )
        }


    if not features:

        return {
            "ok": False,
            "tipo": "sin_geometria",
            "fuente": "geoBoundaries",
            "codigo_iso3": codigo,
            "nivel": nivel_normalizado,
            "mensaje": (
                "geoBoundaries no devolvió "
                "geometrías."
            )
        }


    # --------------------------------------------------------
    # CALCULAR BBOX
    # --------------------------------------------------------

    bbox = calcular_bbox(
        geojson
    )


    # --------------------------------------------------------
    # DATOS DESCRIPTIVOS
    # --------------------------------------------------------

    nombre = (
        metadata.get(
            "boundaryName"
        )
        or codigo
    )

    nivel_respuesta = (
        metadata.get(
            "boundaryType"
        )
        or nivel_normalizado
    )

    anio = metadata.get(
        "boundaryYearRepresented"
    )

    licencia = metadata.get(
        "boundaryLicense"
    )

    boundary_canonical = metadata.get(
        "boundaryCanonical"
    )

    fuente_original = metadata.get(
        "boundarySource"
    )


    # --------------------------------------------------------
    # RESPUESTA TERRI+
    # --------------------------------------------------------

    return {
        "ok": True,
        "tipo": "geojson",
        "modo": "mapa",
        "fuente": "geoBoundaries",

        "codigo_iso3": codigo,

        "nombre": nombre,

        "nivel": nivel_respuesta,

        "anio": anio,

        "licencia": licencia,

        "boundary_canonical": (
            boundary_canonical
        ),

        "fuente_original": (
            fuente_original
        ),

        "resultado": geojson,

        "total_features": len(
            features
        ),

        "bbox": bbox,

        "layer_id": (
            "geoboundaries_"
            + codigo.lower()
            + "_"
            + str(
                nivel_respuesta
            ).lower()
        ),

        "visualizacion": {
            "modo": "simple",
            "campo_categoria": None,
            "campo_valor": None,
            "mostrar_leyenda": True,
            "titulo_leyenda": (
                f"{nombre} — "
                f"{nivel_respuesta}"
            )
        },

        "mensaje": (
            f"Se obtuvo "
            f"{nivel_respuesta} "
            f"de {nombre} "
            f"desde geoBoundaries."
        ),

        "inteligencia": {
            "tipo": "fuente_externa",
            "fuente": "geoBoundaries",
            "mensaje": (
                f"Se obtuvo "
                f"{nivel_respuesta} "
                f"de {nombre} "
                f"desde geoBoundaries."
            )
        },

        "ejecuto_sql": False,

        "reutilizado": False
    }
