import requests
import unicodedata


# ============================================================
# TERRI+ - CONECTOR IGAC
# Servicio oficial de límites territoriales
# ============================================================

IGAC_LIMITES = (
    "https://mapas2.igac.gov.co/server/rest/services/"
    "limites/limites/MapServer"
)


def normalizar_texto(texto):
    """
    Convierte un texto a una forma comparable:
    Sesquilé -> sesquile
    Bogotá D.C. -> bogota d.c.
    """
    texto = str(texto).strip().lower()

    texto = unicodedata.normalize("NFD", texto)

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    return texto


# ============================================================
# CONSULTAR MUNICIPIOS DISPONIBLES EN IGAC
# ============================================================

def obtener_municipios():

    url = f"{IGAC_LIMITES}/1/query"

    parametros = {
        "where": "1=1",
        "outFields": "MpCodigo,MpNombre,Depto",
        "returnGeometry": "false",
        "f": "json"
    }

    respuesta = requests.get(
        url,
        params=parametros,
        timeout=30
    )

    respuesta.raise_for_status()

    datos = respuesta.json()

    return datos.get("features", [])


# ============================================================
# BUSCAR MUNICIPIO POR NOMBRE
# ============================================================

def buscar_municipio(nombre):

    nombre_normalizado = normalizar_texto(nombre)

    municipios = obtener_municipios()

    coincidencias = []

    for feature in municipios:

        atributos = feature.get("attributes", {})

        nombre_igac = atributos.get("MpNombre", "")

        if normalizar_texto(nombre_igac) == nombre_normalizado:

            coincidencias.append(atributos)

    return coincidencias


# ============================================================
# OBTENER LÍMITE MUNICIPAL POR CÓDIGO DANE
# ============================================================

def limite_municipio_codigo(codigo):

    url = f"{IGAC_LIMITES}/1/query"

    parametros = {
        "where": f"MpCodigo='{codigo}'",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson"
    }

    respuesta = requests.get(
        url,
        params=parametros,
        timeout=30
    )

    respuesta.raise_for_status()

    return respuesta.json()


# ============================================================
# OBTENER LÍMITE MUNICIPAL POR NOMBRE
# ============================================================

def limite_municipio(nombre):

    coincidencias = buscar_municipio(nombre)

    if not coincidencias:

        return {
            "tipo": "error",
            "mensaje": f"No encontré el municipio '{nombre}' en el servicio del IGAC."
        }

    # --------------------------------------------------------
    # Puede haber municipios con nombres repetidos
    # --------------------------------------------------------

    if len(coincidencias) > 1:

        opciones = []

        for municipio in coincidencias:

            opciones.append({
                "codigo": municipio.get("MpCodigo"),
                "municipio": municipio.get("MpNombre"),
                "departamento": municipio.get("Depto")
            })

        return {
            "tipo": "ambigua",
            "mensaje": (
                f"Encontré varios municipios llamados '{nombre}'. "
                "Es necesario indicar el departamento."
            ),
            "opciones": opciones
        }

    municipio = coincidencias[0]

    codigo = municipio.get("MpCodigo")

    geojson = limite_municipio_codigo(codigo)

    return {
        "tipo": "municipio",
        "fuente": "IGAC",
        "codigo": codigo,
        "municipio": municipio.get("MpNombre"),
        "departamento": municipio.get("Depto"),
        "geojson": geojson
    }


# ============================================================
# OBTENER DEPARTAMENTOS
# ============================================================

def obtener_departamentos():

    url = f"{IGAC_LIMITES}/2/query"

    parametros = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json"
    }

    respuesta = requests.get(
        url,
        params=parametros,
        timeout=30
    )

    respuesta.raise_for_status()

    datos = respuesta.json()

    return datos.get("features", [])


# ============================================================
# BUSCAR DEPARTAMENTO
# ============================================================

def buscar_departamento(nombre):

    nombre_normalizado = normalizar_texto(nombre)

    departamentos = obtener_departamentos()

    coincidencias = []

    for feature in departamentos:

        atributos = feature.get("attributes", {})

        # Buscamos automáticamente el campo que contenga
        # el nombre del departamento.
        for valor in atributos.values():

            if isinstance(valor, str):

                if normalizar_texto(valor) == nombre_normalizado:

                    coincidencias.append(atributos)
                    break

    return coincidencias


# ============================================================
# DIAGNÓSTICO DEL SERVICIO
# ============================================================

def estado_igac():

    try:

        respuesta = requests.get(
            IGAC_LIMITES,
            params={"f": "json"},
            timeout=15
        )

        respuesta.raise_for_status()

        datos = respuesta.json()

        return {
            "estado": "conectado",
            "servicio": datos.get("mapName", "Límites IGAC"),
            "fuente": "Instituto Geográfico Agustín Codazzi"
        }

    except Exception as error:

        return {
            "estado": "error",
            "detalle": str(error)
        }
