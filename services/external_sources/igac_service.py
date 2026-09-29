# ============================================================
# TERRI+
# IGAC External Service
# Consulta servicios REST oficiales del IGAC
# ============================================================

import re
import requests
import unicodedata

from functools import lru_cache
from typing import Any, Dict, List, Optional


# ============================================================
# SERVICIO BASE IGAC - LÍMITES
# ============================================================

IGAC_LIMITES_BASE = (
    "https://mapas2.igac.gov.co/server/rest/services/"
    "limites/limites/MapServer"
)


# ============================================================
# CAPAS DEL SERVICIO
# ============================================================

CAPA_LINEA_LIMITROFE = 0
CAPA_MUNICIPIOS = 1
CAPA_DEPARTAMENTOS = 2


# ============================================================
# NORMALIZAR TEXTO
# ============================================================

def normalizar_texto(valor: Any) -> str:

    texto = str(valor or "").strip().lower()

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    return texto


# ============================================================
# CONSTRUIR ERROR CONTROLADO DEL IGAC
# ============================================================

def construir_error_igac(
    mensaje: str,
    tipo_error: str
) -> Dict[str, Any]:

    return {
        "_terri_error": True,
        "ok": False,
        "tipo": "error_fuente_externa",
        "modo": "datos",
        "fuente": "IGAC",
        "tipo_error": tipo_error,
        "mensaje": mensaje
    }


# ============================================================
# DETECTAR ERROR CONTROLADO DEL IGAC
# ============================================================

def es_error_igac(
    datos: Any
) -> bool:

    return bool(
        isinstance(datos, dict)
        and datos.get("_terri_error") is True
    )


# ============================================================
# HACER PETICIÓN SEGURA AL IGAC
# ============================================================

def consultar_igac(
    url: str,
    parametros: Dict[str, Any],
    timeout: int = 30
) -> Dict[str, Any]:

    try:

        respuesta = requests.get(
            url,
            params=parametros,
            timeout=timeout
        )

        respuesta.raise_for_status()

        try:

            datos = respuesta.json()

        except ValueError:

            return construir_error_igac(
                (
                    "El servicio REST del IGAC devolvió una "
                    "respuesta que TERRI+ no pudo interpretar."
                ),
                "respuesta_invalida"
            )

        # ----------------------------------------------------
        # ERROR DEVUELTO POR ARCGIS REST
        # ----------------------------------------------------

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
                or "El servicio IGAC devolvió un error."
            )

            detalles = error.get(
                "details"
            )

            if detalles:

                mensaje += " " + " ".join(
                    str(detalle)
                    for detalle in detalles
                )

            return construir_error_igac(
                mensaje,
                "error_servicio"
            )

        return datos

    # --------------------------------------------------------
    # TIMEOUT
    # --------------------------------------------------------

    except requests.exceptions.Timeout:

        return construir_error_igac(
            (
                "El servicio REST del IGAC está tardando "
                "demasiado en responder. "
                "Intenta nuevamente en unos minutos."
            ),
            "timeout"
        )

    # --------------------------------------------------------
    # ERROR DE CONEXIÓN
    # --------------------------------------------------------

    except requests.exceptions.ConnectionError:

        return construir_error_igac(
            (
                "No fue posible establecer conexión con "
                "el servicio REST del IGAC."
            ),
            "conexion"
        )

    # --------------------------------------------------------
    # ERROR HTTP
    # --------------------------------------------------------

    except requests.exceptions.HTTPError as error:

        return construir_error_igac(
            (
                "El servicio REST del IGAC respondió con "
                f"un error HTTP: {error}"
            ),
            "http"
        )

    # --------------------------------------------------------
    # OTROS ERRORES REQUESTS
    # --------------------------------------------------------

    except requests.exceptions.RequestException as error:

        return construir_error_igac(
            (
                "Ocurrió un error al consultar el servicio "
                f"REST del IGAC: {error}"
            ),
            "request"
        )


# ============================================================
# ESTADO DEL SERVICIO IGAC
# ============================================================

def verificar_servicio_igac() -> Dict[str, Any]:

    datos = consultar_igac(
        IGAC_LIMITES_BASE,
        {
            "f": "json"
        },
        timeout=15
    )

    if es_error_igac(datos):

        return {
            "estado": "no_disponible",
            "fuente": "IGAC",
            "error": datos.get(
                "mensaje"
            )
        }

    return {
        "estado": "disponible",
        "fuente": "IGAC",
        "servicio": datos.get(
            "mapName",
            "Límites territoriales"
        )
    }


# ============================================================
# LISTAR MUNICIPIOS
# ============================================================

@lru_cache(maxsize=1)
def listar_municipios() -> Any:

    url = (
        f"{IGAC_LIMITES_BASE}/"
        f"{CAPA_MUNICIPIOS}/query"
    )

    datos = consultar_igac(
        url,
        {
            "where": "1=1",
            "outFields": (
                "MpCodigo,MpNombre,Depto"
            ),
            "returnGeometry": "false",
            "f": "json"
        }
    )

    if es_error_igac(datos):
        return datos

    features = datos.get(
        "features",
        []
    )

    resultado = []

    for feature in features:

        atributos = feature.get(
            "attributes",
            {}
        )

        resultado.append(
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

    return resultado


# ============================================================
# BUSCAR MUNICIPIO
# ============================================================

def buscar_municipio(
    nombre: str,
    departamento: Optional[str] = None
) -> Any:

    nombre_normalizado = (
        normalizar_texto(nombre)
    )

    departamento_normalizado = (
        normalizar_texto(
            departamento
        )
        if departamento
        else None
    )

    municipios = listar_municipios()

    if es_error_igac(municipios):
        return municipios

    coincidencias = []

    for municipio in municipios:

        nombre_igac = normalizar_texto(
            municipio.get(
                "municipio"
            )
        )

        departamento_igac = normalizar_texto(
            municipio.get(
                "departamento"
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
# LÍMITE MUNICIPAL POR CÓDIGO
# ============================================================

def consultar_limite_municipio_codigo(
    codigo: str
) -> Dict[str, Any]:

    codigo = str(
        codigo
    ).strip()

    url = (
        f"{IGAC_LIMITES_BASE}/"
        f"{CAPA_MUNICIPIOS}/query"
    )

    parametros = {
        "where": (
            f"MpCodigo='{codigo}'"
        ),
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson"
    }

    return consultar_igac(
        url,
        parametros
    )


# ============================================================
# LÍMITE MUNICIPAL POR NOMBRE
# ============================================================

def consultar_limite_municipio(
    nombre: str,
    departamento: Optional[str] = None
) -> Dict[str, Any]:

    coincidencias = buscar_municipio(
        nombre=nombre,
        departamento=departamento
    )

    # --------------------------------------------------------
    # ERROR REAL DEL SERVICIO
    # --------------------------------------------------------

    if es_error_igac(coincidencias):
        return coincidencias

    # --------------------------------------------------------
    # MUNICIPIO NO ENCONTRADO
    # --------------------------------------------------------

    if not coincidencias:

        return {
            "ok": False,
            "tipo": "sin_resultado",
            "modo": "datos",
            "fuente": "IGAC",
            "mensaje": (
                f"No se encontró el municipio "
                f"'{nombre}' en el servicio del IGAC."
            )
        }

    # --------------------------------------------------------
    # MUNICIPIO AMBIGUO
    # --------------------------------------------------------

    if len(coincidencias) > 1:

        return {
            "ok": False,
            "tipo": "ambiguo",
            "modo": "datos",
            "fuente": "IGAC",
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

    geojson = (
        consultar_limite_municipio_codigo(
            codigo
        )
    )

    # --------------------------------------------------------
    # ERROR AL OBTENER GEOMETRÍA
    # --------------------------------------------------------

    if es_error_igac(geojson):
        return geojson

    features = geojson.get(
        "features",
        []
    )

    if not features:

        return {
            "ok": False,
            "tipo": "sin_geometria",
            "modo": "datos",
            "fuente": "IGAC",
            "mensaje": (
                "El municipio fue encontrado, "
                "pero el servicio no devolvió geometría."
            )
        }

    nombre_municipio = municipio.get(
        "municipio"
    )

    nombre_departamento = municipio.get(
        "departamento"
    )

    return {
        "ok": True,
        "tipo": "geojson",
        "modo": "mapa",
        "fuente": "IGAC",

        "municipio": nombre_municipio,
        "departamento": nombre_departamento,
        "codigo": codigo,

        "resultado": geojson,

        "layer_id": (
            "igac_limite_municipio_"
            + str(codigo)
        ),

        "visualizacion": {
            "modo": "simple",
            "campo_categoria": None,
            "campo_valor": None,
            "mostrar_leyenda": True,
            "titulo_leyenda": (
                f"Límite de {nombre_municipio}"
            )
        },

        "inteligencia": {
            "tipo": "fuente_externa",
            "fuente": "IGAC",
            "mensaje": (
                f"Se consultó el límite oficial de "
                f"{nombre_municipio}, "
                f"{nombre_departamento}, "
                f"en el servicio REST del IGAC."
            )
        },

        "ejecuto_sql": False,
        "reutilizado": False
    }


# ============================================================
# LISTAR DEPARTAMENTOS
# ============================================================

@lru_cache(maxsize=1)
def listar_departamentos() -> Any:

    url = (
        f"{IGAC_LIMITES_BASE}/"
        f"{CAPA_DEPARTAMENTOS}/query"
    )

    datos = consultar_igac(
        url,
        {
            "where": "1=1",
            "outFields": (
                "DeCodigo,DeNombre,DeArea,DeNorma"
            ),
            "returnGeometry": "false",
            "f": "json"
        }
    )

    if es_error_igac(datos):
        return datos

    features = datos.get(
        "features",
        []
    )

    resultado = []

    for feature in features:

        atributos = feature.get(
            "attributes",
            {}
        )

        resultado.append(
            {
                "codigo": atributos.get(
                    "DeCodigo"
                ),
                "departamento": atributos.get(
                    "DeNombre"
                ),
                "area_km2": atributos.get(
                    "DeArea"
                ),
                "norma": atributos.get(
                    "DeNorma"
                )
            }
        )

    return resultado


# ============================================================
# BUSCAR DEPARTAMENTO
# ============================================================

def buscar_departamento(
    nombre: str
) -> Any:

    nombre_normalizado = (
        normalizar_texto(nombre)
    )

    departamentos = listar_departamentos()

    if es_error_igac(departamentos):
        return departamentos

    coincidencias = []

    for departamento in departamentos:

        nombre_igac = normalizar_texto(
            departamento.get(
                "departamento"
            )
        )

        if (
            nombre_igac
            == nombre_normalizado
        ):

            coincidencias.append(
                departamento
            )

    return coincidencias


# ============================================================
# LÍMITE DEPARTAMENTAL POR CÓDIGO
# ============================================================

def consultar_limite_departamento_codigo(
    codigo: str
) -> Dict[str, Any]:

    codigo = str(
        codigo
    ).strip()

    url = (
        f"{IGAC_LIMITES_BASE}/"
        f"{CAPA_DEPARTAMENTOS}/query"
    )

    parametros = {
        "where": (
            f"DeCodigo='{codigo}'"
        ),
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson"
    }

    return consultar_igac(
        url,
        parametros
    )


# ============================================================
# LÍMITE DEPARTAMENTAL POR NOMBRE
# ============================================================

def consultar_limite_departamento(
    nombre: str
) -> Dict[str, Any]:

    coincidencias = (
        buscar_departamento(
            nombre
        )
    )

    if es_error_igac(coincidencias):
        return coincidencias

    if not coincidencias:

        return {
            "ok": False,
            "tipo": "sin_resultado",
            "modo": "datos",
            "fuente": "IGAC",
            "mensaje": (
                f"No se encontró el departamento "
                f"'{nombre}' en el servicio del IGAC."
            )
        }

    departamento = coincidencias[0]

    codigo = departamento.get(
        "codigo"
    )

    geojson = (
        consultar_limite_departamento_codigo(
            codigo
        )
    )

    if es_error_igac(geojson):
        return geojson

    features = geojson.get(
        "features",
        []
    )

    if not features:

        return {
            "ok": False,
            "tipo": "sin_geometria",
            "modo": "datos",
            "fuente": "IGAC",
            "mensaje": (
                "El departamento fue encontrado, "
                "pero el servicio no devolvió geometría."
            )
        }

    nombre_departamento = departamento.get(
        "departamento"
    )

    return {
        "ok": True,
        "tipo": "geojson",
        "modo": "mapa",
        "fuente": "IGAC",

        "departamento": nombre_departamento,
        "codigo": codigo,

        "resultado": geojson,

        "layer_id": (
            "igac_limite_departamento_"
            + str(codigo)
        ),

        "visualizacion": {
            "modo": "simple",
            "campo_categoria": None,
            "campo_valor": None,
            "mostrar_leyenda": True,
            "titulo_leyenda": (
                f"Límite de {nombre_departamento}"
            )
        },

        "inteligencia": {
            "tipo": "fuente_externa",
            "fuente": "IGAC",
            "mensaje": (
                f"Se consultó el límite oficial del "
                f"departamento de {nombre_departamento} "
                f"en el servicio REST del IGAC."
            )
        },

        "ejecuto_sql": False,
        "reutilizado": False
    }
    # ============================================================
# DETECTAR CONSULTA DE LÍMITES IGAC
# ============================================================

def es_consulta_limites_igac(
    pregunta: str
) -> bool:

    texto = normalizar_texto(
        pregunta
    )

    palabras_limite = [
        "limite",
        "limites",
        "delimitacion",
        "delimitaciones"
    ]

    menciona_limite = any(
        palabra in texto
        for palabra in palabras_limite
    )

    menciona_igac = (
        "igac" in texto
    )

    return bool(
        menciona_limite
        or menciona_igac
    )


# ============================================================
# ENCONTRAR MUNICIPIO MENCIONADO EN LA PREGUNTA
# ============================================================

def detectar_municipio_en_pregunta(
    pregunta: str
) -> Any:

    texto = normalizar_texto(
        pregunta
    )

    municipios = listar_municipios()

    # --------------------------------------------------------
    # PROPAGAR ERROR REAL DEL SERVICIO IGAC
    # --------------------------------------------------------

    if es_error_igac(municipios):
        return municipios

    coincidencias = []

    for municipio in municipios:

        nombre = municipio.get(
            "municipio"
        )

        nombre_normalizado = (
            normalizar_texto(
                nombre
            )
        )

        if not nombre_normalizado:
            continue

        patron = (
            r"\b"
            + re.escape(
                nombre_normalizado
            )
            + r"\b"
        )

        if re.search(
            patron,
            texto
        ):

            coincidencias.append(
                municipio
            )

    if not coincidencias:
        return None

    coincidencias.sort(
        key=lambda item: len(
            normalizar_texto(
                item.get(
                    "municipio"
                )
            )
        ),
        reverse=True
    )

    return coincidencias[0]


# ============================================================
# ENCONTRAR DEPARTAMENTO MENCIONADO EN LA PREGUNTA
# ============================================================

def detectar_departamento_en_pregunta(
    pregunta: str
) -> Any:

    texto = normalizar_texto(
        pregunta
    )

    departamentos = (
        listar_departamentos()
    )

    # --------------------------------------------------------
    # PROPAGAR ERROR REAL DEL SERVICIO IGAC
    # --------------------------------------------------------

    if es_error_igac(departamentos):
        return departamentos

    coincidencias = []

    for departamento in departamentos:

        nombre = departamento.get(
            "departamento"
        )

        nombre_normalizado = (
            normalizar_texto(
                nombre
            )
        )

        if not nombre_normalizado:
            continue

        patron = (
            r"\b"
            + re.escape(
                nombre_normalizado
            )
            + r"\b"
        )

        if re.search(
            patron,
            texto
        ):

            coincidencias.append(
                departamento
            )

    if not coincidencias:
        return None

    coincidencias.sort(
        key=lambda item: len(
            normalizar_texto(
                item.get(
                    "departamento"
                )
            )
        ),
        reverse=True
    )

    return coincidencias[0]


# ============================================================
# RESOLVER CONSULTA NATURAL DE LÍMITES
# ============================================================

def resolver_consulta_limites(
    pregunta: str
) -> Optional[Dict[str, Any]]:

    # --------------------------------------------------------
    # VERIFICAR SI LA PREGUNTA CORRESPONDE AL IGAC
    # --------------------------------------------------------

    if not es_consulta_limites_igac(
        pregunta
    ):
        return None

    texto = normalizar_texto(
        pregunta
    )

    # --------------------------------------------------------
    # PRIORIZAR DEPARTAMENTO SOLO SI EL USUARIO LO SOLICITA
    # EXPLÍCITAMENTE
    # --------------------------------------------------------

    solicita_departamento = (
        "departamento" in texto
        or "departamental" in texto
    )

    if solicita_departamento:

        departamento = (
            detectar_departamento_en_pregunta(
                pregunta
            )
        )

        # ----------------------------------------------------
        # SI EL IGAC FALLÓ, PROPAGAR EL ERROR
        # ----------------------------------------------------

        if es_error_igac(departamento):
            return departamento

        if departamento:

            return consultar_limite_departamento(
                departamento.get(
                    "departamento"
                )
            )

    # --------------------------------------------------------
    # MUNICIPIO
    #
    # IMPORTANTE:
    # Si encontramos un municipio, TERRI+ no consulta
    # innecesariamente el catálogo de departamentos.
    # --------------------------------------------------------

    municipio = (
        detectar_municipio_en_pregunta(
            pregunta
        )
    )

    # --------------------------------------------------------
    # SI EL IGAC FALLÓ AL LISTAR MUNICIPIOS,
    # DEVOLVER EL ERROR REAL
    # --------------------------------------------------------

    if es_error_igac(municipio):
        return municipio

    if municipio:

        return consultar_limite_municipio(
            nombre=municipio.get(
                "municipio"
            ),
            departamento=municipio.get(
                "departamento"
            )
        )

    # --------------------------------------------------------
    # DEPARTAMENTO
    #
    # Solo llegamos aquí si anteriormente no se identificó
    # ningún municipio.
    # --------------------------------------------------------

    departamento = (
        detectar_departamento_en_pregunta(
            pregunta
        )
    )

    # --------------------------------------------------------
    # SI EL IGAC FALLÓ AL LISTAR DEPARTAMENTOS,
    # DEVOLVER EL ERROR REAL
    # --------------------------------------------------------

    if es_error_igac(departamento):
        return departamento

    if departamento:

        return consultar_limite_departamento(
            departamento.get(
                "departamento"
            )
        )

    # --------------------------------------------------------
    # NO SE IDENTIFICÓ MUNICIPIO NI DEPARTAMENTO
    # --------------------------------------------------------

    return {
        "ok": False,
        "tipo": "sin_resultado",
        "modo": "datos",
        "fuente": "IGAC",
        "mensaje": (
            "Entendí que deseas consultar un límite del IGAC, "
            "pero no pude identificar el municipio o departamento."
        )
    }
