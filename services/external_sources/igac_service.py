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
# HACER PETICIÓN SEGURA AL IGAC
# ============================================================

def consultar_igac(
    url: str,
    parametros: Dict[str, Any],
    timeout: int = 30
) -> Dict[str, Any]:

    respuesta = requests.get(
        url,
        params=parametros,
        timeout=timeout
    )

    respuesta.raise_for_status()

    datos = respuesta.json()

    if isinstance(datos, dict) and datos.get("error"):

        error = datos.get(
            "error",
            {}
        )

        mensaje = (
            error.get("message")
            or "El servicio IGAC devolvió un error."
        )

        detalles = error.get("details")

        if detalles:

            mensaje += " " + " ".join(
                str(detalle)
                for detalle in detalles
            )

        raise RuntimeError(
            mensaje
        )

    return datos


# ============================================================
# ESTADO DEL SERVICIO IGAC
# ============================================================

def verificar_servicio_igac() -> Dict[str, Any]:

    try:

        datos = consultar_igac(
            IGAC_LIMITES_BASE,
            {
                "f": "json"
            },
            timeout=15
        )

        return {
            "estado": "disponible",
            "fuente": "IGAC",
            "servicio": datos.get(
                "mapName",
                "Límites territoriales"
            )
        }

    except Exception as error:

        return {
            "estado": "no_disponible",
            "fuente": "IGAC",
            "error": str(error)
        }


# ============================================================
# LISTAR MUNICIPIOS
# ============================================================

@lru_cache(maxsize=1)
def listar_municipios() -> List[Dict[str, Any]]:

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
) -> List[Dict[str, Any]]:

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

    if not coincidencias:

        return {
            "ok": False,
            "tipo": "sin_resultado",
            "fuente": "IGAC",
            "mensaje": (
                f"No se encontró el municipio "
                f"'{nombre}' en el servicio del IGAC."
            )
        }

    if len(coincidencias) > 1:

        return {
            "ok": False,
            "tipo": "ambiguo",
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

    features = geojson.get(
        "features",
        []
    )

    if not features:

        return {
            "ok": False,
            "tipo": "sin_geometria",
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
def listar_departamentos() -> List[Dict[str, Any]]:

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
) -> List[Dict[str, Any]]:

    nombre_normalizado = (
        normalizar_texto(nombre)
    )

    departamentos = listar_departamentos()

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

    if not coincidencias:

        return {
            "ok": False,
            "tipo": "sin_resultado",
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

    features = geojson.get(
        "features",
        []
    )

    if not features:

        return {
            "ok": False,
            "tipo": "sin_geometria",
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
) -> Optional[Dict[str, Any]]:

    texto = normalizar_texto(
        pregunta
    )

    municipios = listar_municipios()

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
) -> Optional[Dict[str, Any]]:

    texto = normalizar_texto(
        pregunta
    )

    departamentos = (
        listar_departamentos()
    )

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

    if not es_consulta_limites_igac(
        pregunta
    ):
        return None

    texto = normalizar_texto(
        pregunta
    )

    municipio = (
        detectar_municipio_en_pregunta(
            pregunta
        )
    )

    departamento = (
        detectar_departamento_en_pregunta(
            pregunta
        )
    )

    # --------------------------------------------------------
    # PRIORIZAR DEPARTAMENTO SI EL USUARIO LO INDICA
    # EXPLÍCITAMENTE
    # --------------------------------------------------------

    if (
        departamento
        and (
            "departamento" in texto
            or "departamental" in texto
        )
    ):

        return consultar_limite_departamento(
            departamento.get(
                "departamento"
            )
        )

    # --------------------------------------------------------
    # MUNICIPIO
    # --------------------------------------------------------

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
    # --------------------------------------------------------

    if departamento:

        return consultar_limite_departamento(
            departamento.get(
                "departamento"
            )
        )

    return {
        "ok": False,
        "tipo": "sin_resultado",
        "fuente": "IGAC",
        "mensaje": (
            "Entendí que deseas consultar un límite del IGAC, "
            "pero no pude identificar el municipio o departamento."
        )
    }
