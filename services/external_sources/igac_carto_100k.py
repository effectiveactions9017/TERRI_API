# ============================================================
# TERRI+
# IGAC CARTOGRAFÍA BÁSICA 1:100.000
#
# Fuente nacional de cartografía básica del IGAC.
#
# Primera integración:
# - Vías
#
# Diseñado para ampliarse posteriormente con:
# - hidrografía
# - cuerpos de agua
# - puentes
# - infraestructura
# ============================================================

import json
import requests
import unicodedata

from functools import lru_cache
from typing import Any, Dict, List, Optional


# ============================================================
# SERVICIOS REST IGAC
# ============================================================

IGAC_CARTO_100K_BASE = (
    "https://mapas2.igac.gov.co/server/rest/services/"
    "carto/carto100000colombia2019/MapServer"
)

IGAC_LIMITES_BASE = (
    "https://mapas2.igac.gov.co/server/rest/services/"
    "limites/limites/MapServer"
)


# ============================================================
# CAPAS
# ============================================================

CAPA_VIAS = 15

CAPA_MUNICIPIOS = 1


# ============================================================
# CONFIGURACIÓN
# ============================================================

MAX_REGISTROS_POR_PAGINA = 2000

TIMEOUT_IGAC = 40


# ============================================================
# NORMALIZAR TEXTO
# ============================================================

def normalizar_texto(
    valor: Any
) -> str:

    texto = str(
        valor or ""
    ).strip().lower()

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(
            caracter
        ) != "Mn"
    )

    return texto


# ============================================================
# PETICIÓN SEGURA
# ============================================================

def consultar_rest_igac(
    url: str,
    parametros: Dict[str, Any],
    timeout: int = TIMEOUT_IGAC
) -> Dict[str, Any]:

    respuesta = requests.get(
        url,
        params=parametros,
        timeout=timeout
    )

    respuesta.raise_for_status()

    datos = respuesta.json()

    if (
        isinstance(datos, dict)
        and datos.get("error")
    ):

        error = datos.get(
            "error",
            {}
        )

        mensaje = (
            error.get("message")
            or
            "El servicio REST del IGAC devolvió un error."
        )

        detalles = error.get(
            "details"
        )

        if detalles:

            mensaje += (
                " "
                + " ".join(
                    str(detalle)
                    for detalle in detalles
                )
            )

        raise RuntimeError(
            mensaje
        )

    return datos


# ============================================================
# VERIFICAR SERVICIO CARTOGRÁFICO
# ============================================================

def verificar_carto_100k() -> Dict[str, Any]:

    try:

        datos = consultar_rest_igac(
            IGAC_CARTO_100K_BASE,
            {
                "f": "json"
            },
            timeout=15
        )

        return {
            "estado": "disponible",
            "fuente": "IGAC",
            "escala": "1:100.000",
            "servicio": datos.get(
                "mapName",
                "Cartografía básica Colombia 1:100.000"
            )
        }

    except Exception as error:

        return {
            "estado": "no_disponible",
            "fuente": "IGAC",
            "escala": "1:100.000",
            "error": str(error)
        }


# ============================================================
# CATÁLOGO DE MUNICIPIOS
# ============================================================

@lru_cache(maxsize=1)
def listar_municipios_igac() -> List[Dict[str, Any]]:

    url = (
        f"{IGAC_LIMITES_BASE}/"
        f"{CAPA_MUNICIPIOS}/query"
    )

    datos = consultar_rest_igac(
        url,
        {
            "where": "1=1",
            "outFields": (
                "MpCodigo,"
                "MpNombre,"
                "Depto"
            ),
            "returnGeometry": "false",
            "f": "json"
        }
    )

    features = datos.get(
        "features",
        []
    )

    municipios = []

    for feature in features:

        atributos = feature.get(
            "attributes",
            {}
        )

        municipios.append(
            {
                "codigo": atributos.get(
                    "MpCodigo"
                ),
                "municipio": atributos.get(
                    "MpNombre"
                ),
                "departamento": atributos.get(
                    "Depto"
                )
            }
        )

    return municipios


# ============================================================
# BUSCAR MUNICIPIO
# ============================================================

def buscar_municipio_igac(
    nombre: str,
    departamento: Optional[str] = None
) -> List[Dict[str, Any]]:

    nombre_normalizado = (
        normalizar_texto(
            nombre
        )
    )

    departamento_normalizado = (
        normalizar_texto(
            departamento
        )
        if departamento
        else None
    )

    coincidencias = []

    for municipio in listar_municipios_igac():

        nombre_igac = (
            normalizar_texto(
                municipio.get(
                    "municipio"
                )
            )
        )

        departamento_igac = (
            normalizar_texto(
                municipio.get(
                    "departamento"
                )
            )
        )

        if (
            nombre_igac
            != nombre_normalizado
        ):
            continue

        if (
            departamento_normalizado
            and departamento_igac
            != departamento_normalizado
        ):
            continue

        coincidencias.append(
            municipio
        )

    return coincidencias


# ============================================================
# OBTENER LÍMITE MUNICIPAL
# ============================================================

def obtener_limite_municipal(
    codigo: str
) -> Dict[str, Any]:

    codigo = str(
        codigo
    ).strip()

    url = (
        f"{IGAC_LIMITES_BASE}/"
        f"{CAPA_MUNICIPIOS}/query"
    )

    return consultar_rest_igac(
        url,
        {
            "where": (
                f"MpCodigo='{codigo}'"
            ),
            "outFields": (
                "MpCodigo,"
                "MpNombre,"
                "Depto"
            ),
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson"
        }
    )


# ============================================================
# CONVERTIR GEOJSON A POLÍGONO ARCGIS
# ============================================================

def convertir_geojson_a_arcgis_polygon(
    geojson: Dict[str, Any]
) -> Dict[str, Any]:

    features = geojson.get(
        "features",
        []
    )

    if not features:

        raise ValueError(
            "El límite municipal no contiene geometría."
        )

    rings = []

    for feature in features:

        geometry = feature.get(
            "geometry"
        ) or {}

        tipo = geometry.get(
            "type"
        )

        coordenadas = geometry.get(
            "coordinates"
        )

        if not coordenadas:
            continue

        # ----------------------------------------------------
        # POLYGON
        # ----------------------------------------------------

        if tipo == "Polygon":

            for ring in coordenadas:

                rings.append(
                    ring
                )

        # ----------------------------------------------------
        # MULTIPOLYGON
        # ----------------------------------------------------

        elif tipo == "MultiPolygon":

            for polygon in coordenadas:

                for ring in polygon:

                    rings.append(
                        ring
                    )

    if not rings:

        raise ValueError(
            "No fue posible convertir el límite municipal "
            "a geometría ArcGIS."
        )

    return {
        "rings": rings,
        "spatialReference": {
            "wkid": 4326
        }
    }


# ============================================================
# UNIR FEATURECOLLECTIONS
# ============================================================

def unir_featurecollections(
    colecciones: List[Dict[str, Any]]
) -> Dict[str, Any]:

    features = []

    for coleccion in colecciones:

        if not isinstance(
            coleccion,
            dict
        ):
            continue

        entidades = coleccion.get(
            "features",
            []
        )

        if isinstance(
            entidades,
            list
        ):

            features.extend(
                entidades
            )

    return {
        "type": "FeatureCollection",
        "features": features
    }


# ============================================================
# CONSULTAR VÍAS POR GEOMETRÍA
# ============================================================

def consultar_vias_geometria(
    geometria_arcgis: Dict[str, Any]
) -> Dict[str, Any]:

    url = (
        f"{IGAC_CARTO_100K_BASE}/"
        f"{CAPA_VIAS}/query"
    )

    pagina = 0

    colecciones = []

    while True:

        parametros = {
            "where": "1=1",

            "geometry": json.dumps(
                geometria_arcgis
            ),

            "geometryType": (
                "esriGeometryPolygon"
            ),

            "inSR": "4326",

            "spatialRel": (
                "esriSpatialRelIntersects"
            ),

            "outFields": (
                "OBJECTID,"
                "TIPO_VIA,"
                "ESTADO_SUPERFICIE,"
                "NUMERO_CARRILES,"
                "ACCESIBILIDAD,"
                "NOMBRE_GEOGRAFICO,"
                "EJE_VIAL"
            ),

            "returnGeometry": "true",

            "outSR": "4326",

            "resultOffset": (
                pagina
                * MAX_REGISTROS_POR_PAGINA
            ),

            "resultRecordCount": (
                MAX_REGISTROS_POR_PAGINA
            ),

            "f": "geojson"
        }

        datos = consultar_rest_igac(
            url,
            parametros
        )

        colecciones.append(
            datos
        )

        features = datos.get(
            "features",
            []
        )

        if (
            len(features)
            < MAX_REGISTROS_POR_PAGINA
        ):
            break

        pagina += 1

        # ----------------------------------------------------
        # PROTECCIÓN CONTRA CICLOS INFINITOS
        # ----------------------------------------------------

        if pagina > 100:

            raise RuntimeError(
                "La consulta de vías superó "
                "el límite de paginación permitido."
            )

    return unir_featurecollections(
        colecciones
    )


# ============================================================
# CONSULTAR VÍAS POR CÓDIGO MUNICIPAL
# ============================================================

def consultar_vias_municipio_codigo(
    codigo: str
) -> Dict[str, Any]:

    codigo = str(
        codigo
    ).strip()

    limite = obtener_limite_municipal(
        codigo
    )

    features_limite = limite.get(
        "features",
        []
    )

    if not features_limite:

        return {
            "ok": False,
            "tipo": "sin_resultado",
            "fuente": "IGAC",
            "servicio": "cartografia_100k",
            "mensaje": (
                f"No se encontró un límite municipal "
                f"para el código {codigo}."
            )
        }

    propiedades = (
        features_limite[0].get(
            "properties",
            {}
        )
    )

    municipio = (
        propiedades.get(
            "MpNombre"
        )
    )

    departamento = (
        propiedades.get(
            "Depto"
        )
    )

    geometria_arcgis = (
        convertir_geojson_a_arcgis_polygon(
            limite
        )
    )

    vias = consultar_vias_geometria(
        geometria_arcgis
    )

    total = len(
        vias.get(
            "features",
            []
        )
    )

    return {
        "ok": True,

        "tipo": "geojson",

        "modo": "mapa",

        "fuente": "IGAC",

        "servicio": (
            "Cartografía básica 1:100.000"
        ),

        "tema": "vias",

        "municipio": municipio,

        "departamento": departamento,

        "codigo": codigo,

        "total_features": total,

        "resultado": vias,

        "layer_id": (
            "igac_carto100k_vias_"
            + codigo
        ),

        "visualizacion": {
            "modo": "simple",
            "mostrar_leyenda": True,
            "titulo_leyenda": (
                f"Vías de {municipio}"
                if municipio
                else "Vías IGAC"
            )
        },

        "inteligencia": {
            "tipo": "fuente_externa",
            "fuente": "IGAC",
            "tema": "vias",
            "mensaje": (
                f"Se consultaron "
                f"{total} elementos viales "
                f"de {municipio or 'el municipio'} "
                f"en la cartografía básica "
                f"1:100.000 del IGAC."
            )
        },

        "ejecuto_sql": False,

        "reutilizado": False
    }


# ============================================================
# CONSULTAR VÍAS POR NOMBRE DE MUNICIPIO
# ============================================================

def consultar_vias_municipio(
    nombre: str,
    departamento: Optional[str] = None
) -> Dict[str, Any]:

    coincidencias = (
        buscar_municipio_igac(
            nombre=nombre,
            departamento=departamento
        )
    )

    if not coincidencias:

        return {
            "ok": False,

            "tipo": "sin_resultado",

            "fuente": "IGAC",

            "servicio": (
                "Cartografía básica 1:100.000"
            ),

            "tema": "vias",

            "mensaje": (
                f"No se encontró el municipio "
                f"'{nombre}' en el catálogo "
                f"territorial del IGAC."
            )
        }

    if len(
        coincidencias
    ) > 1:

        return {
            "ok": False,

            "tipo": "ambiguo",

            "fuente": "IGAC",

            "servicio": (
                "Cartografía básica 1:100.000"
            ),

            "tema": "vias",

            "mensaje": (
                f"Se encontraron varios municipios "
                f"llamados '{nombre}'. "
                f"Indica también el departamento."
            ),

            "opciones": coincidencias
        }

    municipio = coincidencias[0]

    codigo = municipio.get(
        "codigo"
    )

    return (
        consultar_vias_municipio_codigo(
            codigo
        )
    )
