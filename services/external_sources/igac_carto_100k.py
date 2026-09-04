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
import time
import requests
import unicodedata

from functools import lru_cache
from typing import Any, Dict, List, Optional

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


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

MAX_REGISTROS_POR_PAGINA = 1000

TIMEOUT_IGAC = 45

MAX_REINTENTOS_IGAC = 3

PAUSA_REINTENTO_SEGUNDOS = 1.5


# ============================================================
# SESIÓN HTTP ROBUSTA
# ============================================================

def crear_sesion_igac() -> requests.Session:

    sesion = requests.Session()

    reintentos = Retry(
        total=MAX_REINTENTOS_IGAC,
        connect=MAX_REINTENTOS_IGAC,
        read=MAX_REINTENTOS_IGAC,
        status=MAX_REINTENTOS_IGAC,
        backoff_factor=1.0,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504
        ],
        allowed_methods=[
            "GET"
        ],
        raise_on_status=False
    )

    adaptador = HTTPAdapter(
        max_retries=reintentos,
        pool_connections=10,
        pool_maxsize=10
    )

    sesion.mount(
        "https://",
        adaptador
    )

    sesion.mount(
        "http://",
        adaptador
    )

    sesion.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36 "
                "TERRI+/1.0"
            ),
            "Accept": (
                "application/json,"
                "text/plain,*/*"
            ),
            "Accept-Language": (
                "es-CO,es;q=0.9,en;q=0.8"
            ),
            "Connection": "keep-alive"
        }
    )

    return sesion


SESION_IGAC = crear_sesion_igac()


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

    ultimo_error = None

    for intento in range(
        1,
        MAX_REINTENTOS_IGAC + 1
    ):

        try:

            respuesta = SESION_IGAC.get(
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

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ContentDecodingError
        ) as error:

            ultimo_error = error

            if intento < MAX_REINTENTOS_IGAC:

                time.sleep(
                    PAUSA_REINTENTO_SEGUNDOS
                    * intento
                )

                continue

            break

        except requests.exceptions.HTTPError as error:

            ultimo_error = error

            if intento < MAX_REINTENTOS_IGAC:

                time.sleep(
                    PAUSA_REINTENTO_SEGUNDOS
                    * intento
                )

                continue

            break

        except ValueError as error:

            raise RuntimeError(
                "El servicio IGAC respondió, "
                "pero no devolvió JSON válido."
            ) from error

    raise RuntimeError(
        "No fue posible consultar temporalmente "
        "el servicio REST del IGAC. "
        f"Detalle técnico: {ultimo_error}"
    )


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
                geometria_arcgis,
                separators=(",", ":")
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

    try:

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
                "modo": "datos",
                "fuente": "IGAC",
                "servicio": "cartografia_100k",
                "tema": "vias",
                "mensaje": (
                    f"No se encontró un límite municipal "
                    f"para el código {codigo}."
                ),
                "ejecuto_sql": False,
                "reutilizado": False
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

        if total == 0:

            return {
                "ok": False,
                "tipo": "sin_resultado",
                "modo": "datos",
                "fuente": "IGAC",
                "servicio": (
                    "Cartografía básica 1:100.000"
                ),
                "tema": "vias",
                "municipio": municipio,
                "departamento": departamento,
                "codigo": codigo,
                "mensaje": (
                    f"El IGAC no devolvió elementos viales "
                    f"para {municipio or 'el municipio'} "
                    f"en la cartografía básica 1:100.000."
                ),
                "ejecuto_sql": False,
                "reutilizado": False
            }

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

    except Exception as error:

        return {
            "ok": False,
            "tipo": "error_fuente_externa",
            "modo": "datos",
            "fuente": "IGAC",
            "servicio": (
                "Cartografía básica 1:100.000"
            ),
            "tema": "vias",
            "codigo": codigo,
            "mensaje": (
                "El servicio cartográfico del IGAC "
                "no respondió correctamente en este momento. "
                "TERRI+ sigue disponible; puedes intentar "
                "nuevamente en unos segundos."
            ),
            "detalle_tecnico": str(error),
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
