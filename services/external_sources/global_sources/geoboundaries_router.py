# ============================================================
# TERRI+
# GEOBOUNDARIES ROUTER
# Interpretación de consultas sobre límites administrativos
# internacionales
# ============================================================

import re
import unicodedata
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import requests

from services.external_sources.global_sources.geoboundaries_service import (
    obtener_geojson_geoboundaries,
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

GEOBOUNDARIES_CATALOGO_URL = (
    "https://www.geoboundaries.org/"
    "api/current/gbOpen/ALL/ADM0/"
)

GEOBOUNDARIES_TIMEOUT = 30


# ============================================================
# ALIAS DE PAÍSES
#
# Se usan para nombres en español que difieren bastante
# del nombre internacional usado por geoBoundaries.
#
# El resto de países se intentará resolver automáticamente
# mediante el catálogo de geoBoundaries.
# ============================================================

ALIAS_PAISES = {

    # --------------------------------------------------------
    # AMÉRICA
    # --------------------------------------------------------

    "colombia": "COL",
    "ecuador": "ECU",
    "peru": "PER",
    "brasil": "BRA",
    "brazil": "BRA",
    "venezuela": "VEN",
    "bolivia": "BOL",
    "chile": "CHL",
    "argentina": "ARG",
    "uruguay": "URY",
    "paraguay": "PRY",
    "guyana": "GUY",
    "surinam": "SUR",
    "suriname": "SUR",

    "mexico": "MEX",
    "panama": "PAN",
    "costa rica": "CRI",
    "nicaragua": "NIC",
    "honduras": "HND",
    "el salvador": "SLV",
    "guatemala": "GTM",
    "belice": "BLZ",
    "belize": "BLZ",

    "cuba": "CUB",
    "haiti": "HTI",
    "jamaica": "JAM",
    "republica dominicana": "DOM",
    "dominican republic": "DOM",

    "estados unidos": "USA",
    "estados unidos de america": "USA",
    "united states": "USA",
    "usa": "USA",

    "canada": "CAN",

    # --------------------------------------------------------
    # EUROPA
    # --------------------------------------------------------

    "espana": "ESP",
    "spain": "ESP",

    "francia": "FRA",
    "france": "FRA",

    "alemania": "DEU",
    "germany": "DEU",

    "italia": "ITA",
    "italy": "ITA",

    "portugal": "PRT",

    "reino unido": "GBR",
    "gran bretana": "GBR",
    "united kingdom": "GBR",

    "paises bajos": "NLD",
    "holanda": "NLD",
    "netherlands": "NLD",

    "belgica": "BEL",
    "belgium": "BEL",

    "suiza": "CHE",
    "switzerland": "CHE",

    "austria": "AUT",

    "irlanda": "IRL",
    "ireland": "IRL",

    "noruega": "NOR",
    "norway": "NOR",

    "suecia": "SWE",
    "sweden": "SWE",

    "finlandia": "FIN",
    "finland": "FIN",

    "dinamarca": "DNK",
    "denmark": "DNK",

    "polonia": "POL",
    "poland": "POL",

    "grecia": "GRC",
    "greece": "GRC",

    "ucrania": "UKR",
    "ukraine": "UKR",

    "rusia": "RUS",
    "russian federation": "RUS",

    # --------------------------------------------------------
    # ASIA
    # --------------------------------------------------------

    "china": "CHN",

    "japon": "JPN",
    "japan": "JPN",

    "india": "IND",

    "corea del sur": "KOR",
    "south korea": "KOR",
    "republic of korea": "KOR",

    "corea del norte": "PRK",
    "north korea": "PRK",

    "indonesia": "IDN",

    "filipinas": "PHL",
    "philippines": "PHL",

    "tailandia": "THA",
    "thailand": "THA",

    "vietnam": "VNM",

    "turquia": "TUR",
    "turkey": "TUR",

    "arabia saudita": "SAU",
    "saudi arabia": "SAU",

    "israel": "ISR",

    "iran": "IRN",

    "irak": "IRQ",
    "iraq": "IRQ",

    "pakistan": "PAK",

    "nepal": "NPL",

    # --------------------------------------------------------
    # ÁFRICA
    # --------------------------------------------------------

    "egipto": "EGY",
    "egypt": "EGY",

    "sudafrica": "ZAF",
    "south africa": "ZAF",

    "marruecos": "MAR",
    "morocco": "MAR",

    "argelia": "DZA",
    "algeria": "DZA",

    "kenia": "KEN",
    "kenya": "KEN",

    "etiopia": "ETH",
    "ethiopia": "ETH",

    "nigeria": "NGA",

    "ghana": "GHA",

    "tanzania": "TZA",

    # --------------------------------------------------------
    # OCEANÍA
    # --------------------------------------------------------

    "australia": "AUS",

    "nueva zelanda": "NZL",
    "new zealand": "NZL",
}


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalizar_texto(
    texto: str
) -> str:

    texto = str(
        texto or ""
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

    # --------------------------------------------------------
    # DEJAR SOLO LETRAS, NÚMEROS Y ESPACIOS
    # --------------------------------------------------------

    texto = re.sub(
        r"[^a-z0-9\s]",
        " ",
        texto
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


# ============================================================
# CATÁLOGO MUNDIAL GEOBOUNDARIES
#
# Se descarga una sola vez por proceso gracias a lru_cache.
# ============================================================

@lru_cache(maxsize=1)
def obtener_catalogo_paises() -> List[Dict[str, Any]]:

    try:

        respuesta = requests.get(
            GEOBOUNDARIES_CATALOGO_URL,
            timeout=GEOBOUNDARIES_TIMEOUT
        )

        respuesta.raise_for_status()

        datos = respuesta.json()

        if not isinstance(
            datos,
            list
        ):

            return []

        return datos

    except Exception:

        return []


# ============================================================
# COMPROBAR SI UNA FRASE ESTÁ PRESENTE
# ============================================================

def contiene_frase(
    texto: str,
    frase: str
) -> bool:

    texto = (
        f" {normalizar_texto(texto)} "
    )

    frase = (
        f" {normalizar_texto(frase)} "
    )

    return frase in texto


# ============================================================
# RESOLVER PAÍS
# ============================================================

def resolver_pais(
    pregunta: str
) -> Optional[Tuple[str, str]]:

    pregunta_normalizada = (
        normalizar_texto(
            pregunta
        )
    )

    # --------------------------------------------------------
    # 1. ALIAS CONOCIDOS
    #
    # Se ordenan por longitud para que:
    #
    # "estados unidos de america"
    #
    # se evalúe antes que:
    #
    # "estados unidos"
    # --------------------------------------------------------

    alias_ordenados = sorted(
        ALIAS_PAISES.items(),
        key=lambda elemento: len(
            elemento[0]
        ),
        reverse=True
    )

    for nombre, codigo in alias_ordenados:

        if contiene_frase(
            pregunta_normalizada,
            nombre
        ):

            return (
                codigo,
                nombre
            )

    # --------------------------------------------------------
    # 2. CATÁLOGO DINÁMICO GEOBOUNDARIES
    # --------------------------------------------------------

    catalogo = (
        obtener_catalogo_paises()
    )

    coincidencias = []

    for pais in catalogo:

        nombre = str(
            pais.get(
                "boundaryName",
                ""
            )
        ).strip()

        codigo = str(
            pais.get(
                "boundaryISO",
                ""
            )
        ).strip().upper()

        if not nombre or len(codigo) != 3:

            continue

        nombre_normalizado = (
            normalizar_texto(
                nombre
            )
        )

        if contiene_frase(
            pregunta_normalizada,
            nombre_normalizado
        ):

            coincidencias.append(
                (
                    len(
                        nombre_normalizado
                    ),
                    codigo,
                    nombre
                )
            )

    if not coincidencias:

        return None

    # --------------------------------------------------------
    # PRIORIZAR EL NOMBRE MÁS LARGO
    # --------------------------------------------------------

    coincidencias.sort(
        reverse=True
    )

    _, codigo, nombre = (
        coincidencias[0]
    )

    return (
        codigo,
        nombre
    )


# ============================================================
# DETECTAR SI ES CONSULTA GEOBOUNDARIES
# ============================================================

def es_consulta_geoboundaries(
    pregunta: str
) -> bool:

    texto = normalizar_texto(
        pregunta
    )

    palabras_clave = [

        # Límites nacionales
        "limite",
        "limites",
        "frontera",
        "fronteras",

        # Primer nivel administrativo
        "departamento",
        "departamentos",
        "provincia",
        "provincias",
        "estado",
        "estados",
        "region",
        "regiones",

        # Segundo nivel administrativo
        "municipio",
        "municipios",
        "condado",
        "condados",
        "distrito",
        "distritos",
        "comuna",
        "comunas",

        # Expresiones generales
        "division administrativa",
        "divisiones administrativas",
    ]

    return any(
        contiene_frase(
            texto,
            palabra
        )
        for palabra in palabras_clave
    )


# ============================================================
# DETERMINAR NIVEL ADMINISTRATIVO
# ============================================================

def determinar_nivel(
    pregunta: str
) -> str:

    texto = normalizar_texto(
        pregunta
    )

    # --------------------------------------------------------
    # ADM2
    # --------------------------------------------------------

    palabras_adm2 = [
        "municipio",
        "municipios",
        "condado",
        "condados",
        "distrito",
        "distritos",
        "comuna",
        "comunas",
    ]

    if any(
        contiene_frase(
            texto,
            palabra
        )
        for palabra in palabras_adm2
    ):

        return "ADM2"

    # --------------------------------------------------------
    # ADM1
    # --------------------------------------------------------

    palabras_adm1 = [
        "departamento",
        "departamentos",
        "provincia",
        "provincias",
        "estado",
        "estados",
        "region",
        "regiones",
    ]

    if any(
        contiene_frase(
            texto,
            palabra
        )
        for palabra in palabras_adm1
    ):

        return "ADM1"

    # --------------------------------------------------------
    # POR DEFECTO:
    # LÍMITE DEL PAÍS
    # --------------------------------------------------------

    return "ADM0"


# ============================================================
# ETIQUETA HUMANA
# ============================================================

def obtener_etiqueta_nivel(
    pregunta: str,
    nivel: str
) -> str:

    texto = normalizar_texto(
        pregunta
    )

    if nivel == "ADM1":

        if contiene_frase(
            texto,
            "departamento"
        ) or contiene_frase(
            texto,
            "departamentos"
        ):

            return "departamentos"

        if contiene_frase(
            texto,
            "provincia"
        ) or contiene_frase(
            texto,
            "provincias"
        ):

            return "provincias"

        if contiene_frase(
            texto,
            "estado"
        ) or contiene_frase(
            texto,
            "estados"
        ):

            return "estados"

        if contiene_frase(
            texto,
            "region"
        ) or contiene_frase(
            texto,
            "regiones"
        ):

            return "regiones"

        return (
            "divisiones administrativas "
            "de primer nivel"
        )

    if nivel == "ADM2":

        if contiene_frase(
            texto,
            "municipio"
        ) or contiene_frase(
            texto,
            "municipios"
        ):

            return "municipios"

        if contiene_frase(
            texto,
            "condado"
        ) or contiene_frase(
            texto,
            "condados"
        ):

            return "condados"

        if contiene_frase(
            texto,
            "distrito"
        ) or contiene_frase(
            texto,
            "distritos"
        ):

            return "distritos"

        if contiene_frase(
            texto,
            "comuna"
        ) or contiene_frase(
            texto,
            "comunas"
        ):

            return "comunas"

        return (
            "divisiones administrativas "
            "de segundo nivel"
        )

    return "límite nacional"


# ============================================================
# RESOLVER CONSULTA GEOBOUNDARIES
# ============================================================

def resolver_consulta_geoboundaries(
    pregunta: str
) -> Optional[Dict[str, Any]]:

    # --------------------------------------------------------
    # 1. ¿LA PREGUNTA HABLA DE LÍMITES ADMINISTRATIVOS?
    # --------------------------------------------------------

    if not es_consulta_geoboundaries(
        pregunta
    ):

        return None

    # --------------------------------------------------------
    # 2. IDENTIFICAR PAÍS
    # --------------------------------------------------------

    pais = resolver_pais(
        pregunta
    )

    # --------------------------------------------------------
    # Si no identificamos un país, este router no debe
    # apropiarse de la consulta.
    #
    # Así dejamos que IGAC, GeoNames, Planner o PostGIS
    # puedan resolverla.
    # --------------------------------------------------------

    if pais is None:

        return None

    codigo_iso3, nombre_detectado = pais

    # --------------------------------------------------------
    # 3. DETERMINAR NIVEL
    # --------------------------------------------------------

    nivel = determinar_nivel(
        pregunta
    )

    # --------------------------------------------------------
    # 4. CONSULTAR GEOBOUNDARIES
    # --------------------------------------------------------

    resultado = (
        obtener_geojson_geoboundaries(
            codigo_iso3=codigo_iso3,
            nivel=nivel,
            simplificado=True
        )
    )

    # --------------------------------------------------------
    # 5. ERROR CONTROLADO
    # --------------------------------------------------------

    if not resultado.get(
        "ok",
        False
    ):

        resultado["consulta"] = pregunta

        resultado[
            "codigo_iso3"
        ] = codigo_iso3

        resultado[
            "nivel"
        ] = nivel

        resultado[
            "ejecuto_sql"
        ] = False

        return resultado

    # --------------------------------------------------------
    # 6. RESPUESTA NATURAL
    # --------------------------------------------------------

    nombre_oficial = (
        resultado.get(
            "nombre"
        )
        or nombre_detectado
        or codigo_iso3
    )

    etiqueta = (
        obtener_etiqueta_nivel(
            pregunta,
            nivel
        )
    )

    total = resultado.get(
        "total_features",
        0
    )

    if nivel == "ADM0":

        mensaje = (
            f"Se obtuvo el límite nacional de "
            f"{nombre_oficial} desde geoBoundaries."
        )

    else:

        mensaje = (
            f"Se obtuvieron {total} "
            f"{etiqueta} de "
            f"{nombre_oficial} "
            f"desde geoBoundaries."
        )

    # --------------------------------------------------------
    # 7. COMPLETAR RESPUESTA TERRI+
    # --------------------------------------------------------

    resultado[
        "consulta"
    ] = pregunta

    resultado[
        "mensaje"
    ] = mensaje

    resultado[
        "ejecuto_sql"
    ] = False

    resultado[
        "reutilizado"
    ] = False

    resultado[
        "inteligencia"
    ] = {
        "tipo": "fuente_externa",
        "fuente": "geoBoundaries",
        "mensaje": mensaje
    }

    return resultado
