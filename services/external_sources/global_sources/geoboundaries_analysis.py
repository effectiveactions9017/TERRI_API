# ============================================================
# TERRI+
# GEOBOUNDARIES ANALYSIS
# Análisis geométrico de límites administrativos
# ============================================================

import copy
import math

from functools import lru_cache
from typing import Any, Dict, List, Optional

from services.external_sources.global_sources.geoboundaries_service import (
    obtener_geojson_geoboundaries,
    calcular_bbox,
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

# Radio medio de la Tierra en kilómetros.
RADIO_TIERRA_KM = 6371.0088


# ============================================================
# ÁREA DE UN ANILLO
# ============================================================

def calcular_area_anillo_km2(
    coordenadas: List[List[float]]
) -> float:
    """
    Calcula el área aproximada de un anillo GeoJSON
    sobre una esfera terrestre.

    Las coordenadas deben estar en formato:
    [longitud, latitud]

    Devuelve kilómetros cuadrados.
    """

    if not isinstance(
        coordenadas,
        list
    ):
        return 0.0

    if len(coordenadas) < 3:
        return 0.0

    total = 0.0

    cantidad = len(
        coordenadas
    )

    for indice in range(
        cantidad
    ):

        inferior = indice

        medio = (
            indice + 1
        ) % cantidad

        superior = (
            indice + 2
        ) % cantidad

        try:

            longitud_inferior = math.radians(
                float(
                    coordenadas[
                        inferior
                    ][0]
                )
            )

            longitud_superior = math.radians(
                float(
                    coordenadas[
                        superior
                    ][0]
                )
            )

            latitud_media = math.radians(
                float(
                    coordenadas[
                        medio
                    ][1]
                )
            )

        except (
            TypeError,
            ValueError,
            IndexError
        ):

            continue

        diferencia_longitud = (
            longitud_superior
            - longitud_inferior
        )

        # ----------------------------------------------------
        # NORMALIZAR SALTO DE LONGITUD
        #
        # Evita problemas en geometrías cercanas
        # al meridiano ±180°.
        # ----------------------------------------------------

        if diferencia_longitud > math.pi:

            diferencia_longitud -= (
                2 * math.pi
            )

        elif diferencia_longitud < -math.pi:

            diferencia_longitud += (
                2 * math.pi
            )

        total += (
            diferencia_longitud
            * math.sin(
                latitud_media
            )
        )

    area = (
        total
        * RADIO_TIERRA_KM
        * RADIO_TIERRA_KM
        / 2.0
    )

    return abs(
        area
    )


# ============================================================
# ÁREA DE POLÍGONO
# ============================================================

def calcular_area_poligono_km2(
    coordenadas: Any
) -> float:
    """
    Calcula área de Polygon GeoJSON.

    El primer anillo es exterior.
    Los anillos siguientes son huecos.
    """

    if not isinstance(
        coordenadas,
        list
    ):

        return 0.0

    if not coordenadas:

        return 0.0

    area_exterior = (
        calcular_area_anillo_km2(
            coordenadas[0]
        )
    )

    area_huecos = 0.0

    for anillo in coordenadas[
        1:
    ]:

        area_huecos += (
            calcular_area_anillo_km2(
                anillo
            )
        )

    return max(
        0.0,
        area_exterior
        - area_huecos
    )


# ============================================================
# ÁREA DE GEOMETRÍA
# ============================================================

def calcular_area_geometria_km2(
    geometria: Dict[str, Any]
) -> float:
    """
    Calcula el área de una geometría Polygon
    o MultiPolygon.
    """

    if not isinstance(
        geometria,
        dict
    ):

        return 0.0

    tipo = geometria.get(
        "type"
    )

    coordenadas = geometria.get(
        "coordinates"
    )

    # --------------------------------------------------------
    # POLYGON
    # --------------------------------------------------------

    if tipo == "Polygon":

        return (
            calcular_area_poligono_km2(
                coordenadas
            )
        )

    # --------------------------------------------------------
    # MULTIPOLYGON
    # --------------------------------------------------------

    if tipo == "MultiPolygon":

        if not isinstance(
            coordenadas,
            list
        ):

            return 0.0

        return sum(
            calcular_area_poligono_km2(
                poligono
            )
            for poligono
            in coordenadas
        )

    return 0.0


# ============================================================
# AGREGAR ÁREA A TODAS LAS FEATURES
# ============================================================

def agregar_area_features(
    geojson: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Añade area_km2_aprox a cada feature.
    """

    resultado = copy.deepcopy(
        geojson
    )

    features = resultado.get(
        "features",
        []
    )

    if not isinstance(
        features,
        list
    ):

        return resultado

    for feature in features:

        if not isinstance(
            feature,
            dict
        ):

            continue

        geometria = feature.get(
            "geometry"
        )

        area_km2 = (
            calcular_area_geometria_km2(
                geometria
            )
        )

        propiedades = feature.get(
            "properties"
        )

        if not isinstance(
            propiedades,
            dict
        ):

            propiedades = {}

            feature[
                "properties"
            ] = propiedades

        propiedades[
            "area_km2_aprox"
        ] = round(
            area_km2,
            2
        )

    return resultado


# ============================================================
# CACHÉ DE GEOBOUNDARIES + ÁREAS
# ============================================================

@lru_cache(
    maxsize=32
)
def _obtener_geojson_con_areas_cache(
    codigo_iso3: str,
    nivel: str
) -> Dict[str, Any]:
    """
    Descarga la geometría completa una sola vez
    por país + nivel dentro del proceso.
    """

    codigo = str(
        codigo_iso3 or ""
    ).strip().upper()

    nivel_admin = str(
        nivel or "ADM0"
    ).strip().upper()

    # --------------------------------------------------------
    # IMPORTANTE
    #
    # Para calcular áreas usamos la geometría COMPLETA,
    # no la versión simplificada del visor.
    # --------------------------------------------------------

    respuesta = (
        obtener_geojson_geoboundaries(
            codigo_iso3=codigo,
            nivel=nivel_admin,
            simplificado=False
        )
    )

    if not respuesta.get(
        "ok",
        False
    ):

        return respuesta

    geojson = respuesta.get(
        "resultado"
    )

    if not isinstance(
        geojson,
        dict
    ):

        return {
            "ok": False,
            "tipo": "respuesta_invalida",
            "fuente": "geoBoundaries",
            "mensaje": (
                "No fue posible obtener una geometría "
                "válida para calcular áreas."
            )
        }

    geojson_con_areas = (
        agregar_area_features(
            geojson
        )
    )

    respuesta_final = (
        copy.deepcopy(
            respuesta
        )
    )

    respuesta_final[
        "resultado"
    ] = geojson_con_areas

    respuesta_final[
        "total_features"
    ] = len(
        geojson_con_areas.get(
            "features",
            []
        )
    )

    respuesta_final[
        "analisis_area"
    ] = True

    return respuesta_final


# ============================================================
# OBTENER GEOJSON CON ÁREAS
# ============================================================

def obtener_geojson_con_areas(
    codigo_iso3: str,
    nivel: str = "ADM1"
) -> Dict[str, Any]:
    """
    Devuelve una copia segura del resultado
    almacenado en caché.
    """

    resultado = (
        _obtener_geojson_con_areas_cache(
            str(
                codigo_iso3
            ).upper(),
            str(
                nivel
            ).upper()
        )
    )

    return copy.deepcopy(
        resultado
    )


# ============================================================
# BUSCAR MAYOR O MENOR ÁREA
# ============================================================

def obtener_extremo_area_geoboundaries(
    codigo_iso3: str,
    nivel: str = "ADM1",
    criterio: str = "menor"
) -> Dict[str, Any]:
    """
    Obtiene la división administrativa de menor
    o mayor área.

    criterio:
    - menor
    - mayor
    """

    criterio_normalizado = str(
        criterio or "menor"
    ).strip().lower()

    if criterio_normalizado not in {
        "menor",
        "mayor"
    }:

        return {
            "ok": False,
            "tipo": "criterio_invalido",
            "fuente": "geoBoundaries",
            "mensaje": (
                "El criterio debe ser 'menor' "
                "o 'mayor'."
            )
        }

    respuesta = (
        obtener_geojson_con_areas(
            codigo_iso3=codigo_iso3,
            nivel=nivel
        )
    )

    if not respuesta.get(
        "ok",
        False
    ):

        return respuesta

    geojson = respuesta.get(
        "resultado",
        {}
    )

    features = geojson.get(
        "features",
        []
    )

    features_validas = []

    for feature in features:

        propiedades = feature.get(
            "properties",
            {}
        )

        area = propiedades.get(
            "area_km2_aprox"
        )

        try:

            area_numero = float(
                area
            )

        except (
            TypeError,
            ValueError
        ):

            continue

        if area_numero <= 0:

            continue

        features_validas.append(
            feature
        )

    if not features_validas:

        return {
            "ok": False,
            "tipo": "sin_resultado",
            "fuente": "geoBoundaries",
            "mensaje": (
                "No fue posible calcular áreas "
                "para las divisiones administrativas."
            )
        }

    if criterio_normalizado == "menor":

        seleccionada = min(
            features_validas,
            key=lambda feature: float(
                feature.get(
                    "properties",
                    {}
                ).get(
                    "area_km2_aprox",
                    0
                )
            )
        )

    else:

        seleccionada = max(
            features_validas,
            key=lambda feature: float(
                feature.get(
                    "properties",
                    {}
                ).get(
                    "area_km2_aprox",
                    0
                )
            )
        )

    propiedades = seleccionada.get(
        "properties",
        {}
    )

    nombre_division = (
        propiedades.get(
            "shapeName"
        )
        or "División administrativa"
    )

    area_km2 = propiedades.get(
        "area_km2_aprox"
    )

    nombre_pais = (
        respuesta.get(
            "nombre"
        )
        or str(
            codigo_iso3
        ).upper()
    )

    resultado_geojson = {
        "type": "FeatureCollection",
        "features": [
            seleccionada
        ]
    }

    # Mantener CRS cuando venga en la fuente.
    if geojson.get(
        "crs"
    ):

        resultado_geojson[
            "crs"
        ] = geojson.get(
            "crs"
        )

    bbox = calcular_bbox(
        resultado_geojson
    )

    codigo = str(
        codigo_iso3
    ).upper()

    nivel_admin = str(
        nivel
    ).upper()

    layer_id = (
        "geoboundaries_"
        + codigo.lower()
        + "_"
        + nivel_admin.lower()
        + "_area_"
        + criterio_normalizado
    )

    if criterio_normalizado == "menor":

        mensaje = (
            f"La división administrativa de menor área "
            f"de {nombre_pais} es {nombre_division}, "
            f"con aproximadamente "
            f"{area_km2:,.2f} km²."
        )

    else:

        mensaje = (
            f"La división administrativa de mayor área "
            f"de {nombre_pais} es {nombre_division}, "
            f"con aproximadamente "
            f"{area_km2:,.2f} km²."
        )

    return {
        "ok": True,
        "tipo": "geojson",
        "modo": "mapa",
        "fuente": "geoBoundaries",

        "codigo_iso3": codigo,
        "nombre": nombre_pais,
        "nivel": nivel_admin,

        "criterio_area": (
            criterio_normalizado
        ),

        "nombre_division": (
            nombre_division
        ),

        "area_km2_aprox": (
            area_km2
        ),

        "resultado": (
            resultado_geojson
        ),

        "total_features": 1,

        "bbox": bbox,

        "layer_id": layer_id,

        "visualizacion": {
            "modo": "simple",
            "campo_categoria": None,
            "campo_valor": (
                "area_km2_aprox"
            ),
            "mostrar_leyenda": True,
            "titulo_leyenda": (
                f"{nombre_division} — "
                f"{area_km2:,.2f} km²"
            )
        },

        "mensaje": mensaje,

        "inteligencia": {
            "tipo": (
                "analisis_geometrico"
            ),
            "fuente": (
                "geoBoundaries"
            ),
            "mensaje": mensaje
        },

        "ejecuto_sql": False,

        "reutilizado": False
    }
