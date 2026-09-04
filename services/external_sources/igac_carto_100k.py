# ============================================================
# TERRI+
# IGAC CARTOGRAFÍA BÁSICA 1:100.000
#
# Consulta nacional de capas cartográficas oficiales del IGAC.
# Las consultas espaciales se envían por POST para evitar URLs
# excesivamente largas cuando se usa el límite municipal.
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
# CAPAS TERRITORIALES AUXILIARES
# ============================================================

CAPA_MUNICIPIOS = 1


# ============================================================
# CATÁLOGO CARTOGRÁFICO TERRI+
# ============================================================
#
# Se usan capas reales del servicio nacional 1:100.000.
#
# Para hidrografía se evita consultar simultáneamente las dos
# representaciones de "Drenaje Sencillo" (24 y 25) porque son
# representaciones de la misma temática a escalas distintas.
# TERRI+ usa 25 como drenaje lineal y 36 como drenaje doble.
# ============================================================

CAPAS_CARTO_100K = {

    "vias": {
        "nombre": "Vías",
        "ids": [15],
        "titulo": "Vías",
    },

    "via_ferrea": {
        "nombre": "Vía férrea",
        "ids": [16],
        "titulo": "Vías férreas",
    },

    "tuneles": {
        "nombre": "Túneles",
        "ids": [18],
        "titulo": "Túneles",
    },

    "puentes": {
        "nombre": "Puentes",
        "ids": [5, 11],
        "titulo": "Puentes",
    },

    "red_alta_tension": {
        "nombre": "Red de alta tensión",
        "ids": [12],
        "titulo": "Red de alta tensión",
    },

    "rios": {
        "nombre": "Ríos, quebradas y drenajes",
        "ids": [25, 36],
        "titulo": "Ríos y drenajes",
    },

    "canales": {
        "nombre": "Canales",
        "ids": [26, 37],
        "titulo": "Canales",
    },

    "lagunas": {
        "nombre": "Lagunas",
        "ids": [39],
        "titulo": "Lagunas",
    },

    "humedales": {
        "nombre": "Humedales",
        "ids": [41],
        "titulo": "Humedales",
    },

    "embalses": {
        "nombre": "Embalses",
        "ids": [42],
        "titulo": "Embalses",
    },

    "cienagas": {
        "nombre": "Ciénagas",
        "ids": [44],
        "titulo": "Ciénagas",
    },

    "pantanos": {
        "nombre": "Pantanos",
        "ids": [46],
        "titulo": "Pantanos",
    },

    "otros_cuerpos_agua": {
        "nombre": "Otros cuerpos de agua",
        "ids": [47],
        "titulo": "Otros cuerpos de agua",
    },

    "jagueyes": {
        "nombre": "Jagüeyes",
        "ids": [6, 40],
        "titulo": "Jagüeyes",
    },

    "madreviejas": {
        "nombre": "Madreviejas",
        "ids": [27, 38],
        "titulo": "Madreviejas",
    },

    "morichales": {
        "nombre": "Morichales",
        "ids": [43],
        "titulo": "Morichales",
    },

    "manglares": {
        "nombre": "Manglares",
        "ids": [45],
        "titulo": "Manglares",
    },

    "cuerpos_agua": {
        "nombre": "Cuerpos de agua",
        "ids": [39, 40, 41, 42, 43, 44, 46, 47],
        "titulo": "Cuerpos de agua",
    },

    "bosques": {
        "nombre": "Bosques",
        "ids": [49],
        "titulo": "Bosques",
    },

    "orografia": {
        "nombre": "Orografía",
        "ids": [8],
        "titulo": "Orografía",
    },

    "aeropuertos": {
        "nombre": "Aeropuertos",
        "ids": [9, 31, 32],
        "titulo": "Aeropuertos y pistas",
    },

    "puertos": {
        "nombre": "Puertos y muelles",
        "ids": [10, 22, 33],
        "titulo": "Puertos y muelles",
    },
}


# ============================================================
# CONFIGURACIÓN HTTP
# ============================================================

MAX_REGISTROS_POR_PAGINA = 1000
TIMEOUT_IGAC = 45
MAX_REINTENTOS_IGAC = 3
PAUSA_REINTENTO_SEGUNDOS = 1.5


def crear_sesion_igac() -> requests.Session:

    sesion = requests.Session()

    reintentos = Retry(
        total=MAX_REINTENTOS_IGAC,
        connect=MAX_REINTENTOS_IGAC,
        read=MAX_REINTENTOS_IGAC,
        status=MAX_REINTENTOS_IGAC,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )

    adaptador = HTTPAdapter(
        max_retries=reintentos,
        pool_connections=10,
        pool_maxsize=10,
    )

    sesion.mount("https://", adaptador)
    sesion.mount("http://", adaptador)

    sesion.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36 TERRI+/1.0"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    })

    return sesion


SESION_IGAC = crear_sesion_igac()


# ============================================================
# UTILIDADES
# ============================================================

def normalizar_texto(valor: Any) -> str:

    texto = str(valor or "").strip().lower()
    texto = unicodedata.normalize("NFD", texto)

    return "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )


def consultar_rest_igac(
    url: str,
    parametros: Dict[str, Any],
    timeout: int = TIMEOUT_IGAC,
    metodo: str = "get",
) -> Dict[str, Any]:

    ultimo_error = None

    for intento in range(1, MAX_REINTENTOS_IGAC + 1):

        try:

            metodo_normalizado = str(
                metodo or "get"
            ).strip().lower()

            if metodo_normalizado == "post":

                respuesta = SESION_IGAC.post(
                    url,
                    data=parametros,
                    timeout=timeout,
                )

            else:

                respuesta = SESION_IGAC.get(
                    url,
                    params=parametros,
                    timeout=timeout,
                )

            respuesta.raise_for_status()
            datos = respuesta.json()

            if isinstance(datos, dict) and datos.get("error"):

                error = datos.get("error", {})

                mensaje = (
                    error.get("message")
                    or "El servicio REST del IGAC devolvió un error."
                )

                detalles = error.get("details")

                if detalles:
                    mensaje += " " + " ".join(
                        str(detalle)
                        for detalle in detalles
                    )

                raise RuntimeError(mensaje)

            return datos

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ContentDecodingError,
        ) as error:

            ultimo_error = error

            if intento < MAX_REINTENTOS_IGAC:
                time.sleep(
                    PAUSA_REINTENTO_SEGUNDOS * intento
                )
                continue

            break

        except requests.exceptions.HTTPError as error:

            ultimo_error = error

            if intento < MAX_REINTENTOS_IGAC:
                time.sleep(
                    PAUSA_REINTENTO_SEGUNDOS * intento
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
# VERIFICAR SERVICIO
# ============================================================

def verificar_carto_100k() -> Dict[str, Any]:

    try:

        datos = consultar_rest_igac(
            IGAC_CARTO_100K_BASE,
            {"f": "json"},
            timeout=15,
        )

        return {
            "estado": "disponible",
            "fuente": "IGAC",
            "escala": "1:100.000",
            "servicio": datos.get(
                "mapName",
                "Cartografía básica Colombia 1:100.000",
            ),
        }

    except Exception as error:

        return {
            "estado": "no_disponible",
            "fuente": "IGAC",
            "escala": "1:100.000",
            "error": str(error),
        }


# ============================================================
# MUNICIPIOS
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
            "outFields": "MpCodigo,MpNombre,Depto",
            "returnGeometry": "false",
            "f": "json",
        },
    )

    resultado = []

    for feature in datos.get("features", []):

        atributos = feature.get("attributes", {})

        resultado.append({
            "codigo": atributos.get("MpCodigo"),
            "municipio": atributos.get("MpNombre"),
            "departamento": atributos.get("Depto"),
        })

    return resultado


def buscar_municipio_igac(
    nombre: str,
    departamento: Optional[str] = None,
) -> List[Dict[str, Any]]:

    nombre_normalizado = normalizar_texto(nombre)

    departamento_normalizado = (
        normalizar_texto(departamento)
        if departamento
        else None
    )

    coincidencias = []

    for municipio in listar_municipios_igac():

        nombre_igac = normalizar_texto(
            municipio.get("municipio")
        )

        departamento_igac = normalizar_texto(
            municipio.get("departamento")
        )

        if nombre_igac != nombre_normalizado:
            continue

        if (
            departamento_normalizado
            and departamento_igac != departamento_normalizado
        ):
            continue

        coincidencias.append(municipio)

    return coincidencias


def obtener_limite_municipal(
    codigo: str,
) -> Dict[str, Any]:

    codigo = str(codigo).strip()

    url = (
        f"{IGAC_LIMITES_BASE}/"
        f"{CAPA_MUNICIPIOS}/query"
    )

    return consultar_rest_igac(
        url,
        {
            "where": f"MpCodigo='{codigo}'",
            "outFields": "MpCodigo,MpNombre,Depto",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        },
    )


def convertir_geojson_a_arcgis_polygon(
    geojson: Dict[str, Any],
) -> Dict[str, Any]:

    features = geojson.get("features", [])

    if not features:
        raise ValueError(
            "El límite municipal no contiene geometría."
        )

    rings = []

    for feature in features:

        geometry = feature.get("geometry") or {}
        tipo = geometry.get("type")
        coordenadas = geometry.get("coordinates")

        if not coordenadas:
            continue

        if tipo == "Polygon":

            for ring in coordenadas:
                rings.append(ring)

        elif tipo == "MultiPolygon":

            for polygon in coordenadas:
                for ring in polygon:
                    rings.append(ring)

    if not rings:
        raise ValueError(
            "No fue posible convertir el límite municipal "
            "a geometría ArcGIS."
        )

    return {
        "rings": rings,
        "spatialReference": {
            "wkid": 4326,
        },
    }


# ============================================================
# METADATOS DE CAPA
# ============================================================

@lru_cache(maxsize=128)
def obtener_campos_capa(
    layer_id: int,
) -> str:

    url = (
        f"{IGAC_CARTO_100K_BASE}/"
        f"{layer_id}"
    )

    try:

        datos = consultar_rest_igac(
            url,
            {"f": "json"},
            timeout=20,
        )

        campos = []

        for campo in datos.get("fields", []):

            nombre = campo.get("name")
            tipo = campo.get("type")

            if not nombre:
                continue

            if tipo in {
                "esriFieldTypeBlob",
                "esriFieldTypeRaster",
                "esriFieldTypeGeometry",
            }:
                continue

            campos.append(nombre)

        if campos:
            return ",".join(campos)

    except Exception:
        pass

    return "OBJECTID"


# ============================================================
# FEATURECOLLECTION
# ============================================================

def unir_featurecollections(
    colecciones: List[Dict[str, Any]],
) -> Dict[str, Any]:

    features = []

    for coleccion in colecciones:

        if not isinstance(coleccion, dict):
            continue

        entidades = coleccion.get("features", [])

        if isinstance(entidades, list):
            features.extend(entidades)

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def etiquetar_features(
    geojson: Dict[str, Any],
    tema: str,
    capa_id: int,
) -> Dict[str, Any]:

    for feature in geojson.get("features", []):

        propiedades = feature.setdefault(
            "properties",
            {},
        )

        propiedades["_terri_tema"] = tema
        propiedades["_terri_capa_igac"] = capa_id

    return geojson


# ============================================================
# CONSULTA GENÉRICA DE UNA CAPA
# ============================================================

def consultar_capa_geometria(
    layer_id: int,
    geometria_arcgis: Dict[str, Any],
    tema: str,
) -> Dict[str, Any]:

    url = (
        f"{IGAC_CARTO_100K_BASE}/"
        f"{layer_id}/query"
    )

    pagina = 0
    colecciones = []

    while True:

        parametros = {
            "where": "1=1",
            "geometry": json.dumps(
                geometria_arcgis,
                separators=(",", ":"),
            ),
            "geometryType": "esriGeometryPolygon",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": obtener_campos_capa(layer_id),
            "returnGeometry": "true",
            "outSR": "4326",
            "resultOffset": (
                pagina * MAX_REGISTROS_POR_PAGINA
            ),
            "resultRecordCount": (
                MAX_REGISTROS_POR_PAGINA
            ),
            "f": "geojson",
        }

        datos = consultar_rest_igac(
            url,
            parametros,
            metodo="post",
        )

        etiquetar_features(
            datos,
            tema=tema,
            capa_id=layer_id,
        )

        colecciones.append(datos)

        features = datos.get("features", [])

        if len(features) < MAX_REGISTROS_POR_PAGINA:
            break

        pagina += 1

        if pagina > 100:
            raise RuntimeError(
                "La consulta cartográfica superó "
                "el límite de paginación permitido."
            )

    return unir_featurecollections(
        colecciones
    )


# ============================================================
# CONSULTA GENÉRICA POR CÓDIGO MUNICIPAL
# ============================================================

def consultar_tema_municipio_codigo(
    tema: str,
    codigo: str,
) -> Dict[str, Any]:

    codigo = str(codigo).strip()

    configuracion = CAPAS_CARTO_100K.get(
        tema
    )

    if not configuracion:

        return {
            "ok": False,
            "tipo": "tema_no_soportado",
            "modo": "datos",
            "fuente": "IGAC",
            "tema": tema,
            "mensaje": (
                f"El tema cartográfico '{tema}' "
                "no está registrado en TERRI+."
            ),
            "ejecuto_sql": False,
            "reutilizado": False,
        }

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
                "tema": tema,
                "mensaje": (
                    f"No se encontró un límite municipal "
                    f"para el código {codigo}."
                ),
                "ejecuto_sql": False,
                "reutilizado": False,
            }

        propiedades = (
            features_limite[0].get(
                "properties",
                {},
            )
        )

        municipio = propiedades.get(
            "MpNombre"
        )

        departamento = propiedades.get(
            "Depto"
        )

        geometria_arcgis = (
            convertir_geojson_a_arcgis_polygon(
                limite
            )
        )

        colecciones = []

        for layer_id in configuracion["ids"]:

            resultado_capa = consultar_capa_geometria(
                layer_id=layer_id,
                geometria_arcgis=geometria_arcgis,
                tema=tema,
            )

            colecciones.append(
                resultado_capa
            )

        resultado = unir_featurecollections(
            colecciones
        )

        total = len(
            resultado.get(
                "features",
                [],
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
                "tema": tema,
                "municipio": municipio,
                "departamento": departamento,
                "codigo": codigo,
                "mensaje": (
                    f"El IGAC no devolvió elementos de "
                    f"{configuracion['nombre'].lower()} "
                    f"para {municipio or 'el municipio'}."
                ),
                "ejecuto_sql": False,
                "reutilizado": False,
            }

        return {
            "ok": True,
            "tipo": "geojson",
            "modo": "mapa",
            "fuente": "IGAC",
            "servicio": (
                "Cartografía básica 1:100.000"
            ),
            "escala": "1:100.000",
            "tema": tema,
            "municipio": municipio,
            "departamento": departamento,
            "codigo": codigo,
            "total_features": total,
            "resultado": resultado,
            "layer_id": (
                f"igac_carto100k_{tema}_{codigo}"
            ),
            "visualizacion": {
                "modo": "simple",
                "mostrar_leyenda": True,
                "titulo_leyenda": (
                    f"{configuracion['titulo']} "
                    f"de {municipio}"
                    if municipio
                    else configuracion["titulo"]
                ),
            },
            "inteligencia": {
                "tipo": "fuente_externa",
                "fuente": "IGAC",
                "tema": tema,
                "mensaje": (
                    f"Se consultaron {total} elementos de "
                    f"{configuracion['nombre'].lower()} "
                    f"de {municipio or 'el municipio'} "
                    f"en la cartografía básica "
                    f"1:100.000 del IGAC."
                ),
            },
            "ejecuto_sql": False,
            "reutilizado": False,
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
            "tema": tema,
            "codigo": codigo,
            "mensaje": (
                "El servicio cartográfico del IGAC "
                "no respondió correctamente en este momento. "
                "TERRI+ sigue disponible; puedes intentar "
                "nuevamente en unos segundos."
            ),
            "detalle_tecnico": str(error),
            "ejecuto_sql": False,
            "reutilizado": False,
        }


# ============================================================
# CONSULTA GENÉRICA POR MUNICIPIO
# ============================================================

def consultar_tema_municipio(
    tema: str,
    nombre: str,
    departamento: Optional[str] = None,
) -> Dict[str, Any]:

    coincidencias = buscar_municipio_igac(
        nombre=nombre,
        departamento=departamento,
    )

    if not coincidencias:

        return {
            "ok": False,
            "tipo": "sin_resultado",
            "modo": "datos",
            "fuente": "IGAC",
            "tema": tema,
            "mensaje": (
                f"No se encontró el municipio "
                f"'{nombre}' en el catálogo "
                "territorial del IGAC."
            ),
            "ejecuto_sql": False,
            "reutilizado": False,
        }

    if len(coincidencias) > 1:

        return {
            "ok": False,
            "tipo": "ambiguo",
            "modo": "datos",
            "fuente": "IGAC",
            "tema": tema,
            "mensaje": (
                f"Se encontraron varios municipios "
                f"llamados '{nombre}'. "
                "Indica también el departamento."
            ),
            "opciones": coincidencias,
            "ejecuto_sql": False,
            "reutilizado": False,
        }

    codigo = coincidencias[0].get(
        "codigo"
    )

    return consultar_tema_municipio_codigo(
        tema=tema,
        codigo=codigo,
    )


# ============================================================
# COMPATIBILIDAD CON LA FUNCIÓN DE VÍAS YA EXISTENTE
# ============================================================

def consultar_vias_municipio_codigo(
    codigo: str,
) -> Dict[str, Any]:

    return consultar_tema_municipio_codigo(
        tema="vias",
        codigo=codigo,
    )


def consultar_vias_municipio(
    nombre: str,
    departamento: Optional[str] = None,
) -> Dict[str, Any]:

    return consultar_tema_municipio(
        tema="vias",
        nombre=nombre,
        departamento=departamento,
    )
