# ============================================================
# TERRI+
# IGAC External Service
# Consulta servicios REST oficiales del IGAC
# ============================================================

import requests
import unicodedata
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

        error = datos.get("error", {})

        mensaje = (
            error.get("message")
            or "El servicio IGAC devolvió un error."
        )

        detalles = error.get("details")

        if detalles:
            mensaje += " " + " ".join(
                str(x)
                for x in detalles
            )

        raise RuntimeError(mensaje)

    return datos


# ============================================================
# ESTADO DEL SERVICIO
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
# OBTENER MUNICIPIOS SIN GEOMETRÍA
# ============================================================

def listar_municipios() -> List[Dict[str, Any]]:

    url = (
        f"{IGAC_LIMITES_BASE}/"
        f"{CAPA_MUNICIPIOS}/query"
    )

    datos = consultar_igac(
        url,
        {
            "where": "1=1",
            "outFields": "MpCodigo,MpNombre,Depto",
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
# BUSCAR MUNICIPIO POR NOMBRE
# ============================================================

def buscar_municipio(
    nombre: str,
    departamento: Optional[str] = None
) -> List[Dict[str, Any]]:

    nombre_normalizado = normalizar_texto(
        nombre
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

        if nombre_igac != nombre_normalizado:
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
# CONSULTAR LÍMITE MUNICIPAL POR CÓDIGO
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

    geojson = consultar_igac(
        url,
        parametros
    )

    return geojson


# ============================================================
# CONSULTAR LÍMITE MUNICIPAL POR NOMBRE
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
                f"llamados '{nombre}'."
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

    return {
        "ok": True,
        "tipo": "geojson",
        "modo": "mapa",

        "fuente": "IGAC",

        "municipio": municipio.get(
            "municipio"
        ),

        "departamento": municipio.get(
            "departamento"
        ),

        "codigo": codigo,

        "resultado": geojson,

        "layer_id": (
            "igac_limite_municipio_"
            + str(codigo)
        ),

        "visualizacion": {
            "modo": "simple",
            "mostrar_leyenda": False,
            "titulo_leyenda": (
                "Límite municipal IGAC"
            )
        },

        "inteligencia": {
            "tipo": "fuente_externa",
            "fuente": "IGAC",
            "mensaje": (
                f"Se consultó el límite oficial de "
                f"{municipio.get('municipio')} "
                f"en el servicio REST del IGAC."
            )
        },

        "ejecuto_sql": False,

        "reutilizado": False
    }


# ============================================================
# LISTAR DEPARTAMENTOS
# ============================================================

def listar_departamentos() -> List[Dict[str, Any]]:

    url = (
        f"{IGAC_LIMITES_BASE}/"
        f"{CAPA_DEPARTAMENTOS}/query"
    )

    datos = consultar_igac(
        url,
        {
            "where": "1=1",
            "outFields": "*",
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
            atributos
        )

    return resultado
