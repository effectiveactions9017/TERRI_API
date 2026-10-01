# ============================================================
# TERRI+
# GEOBOUNDARIES ROUTER
# Interpretación de consultas sobre límites administrativos
# internacionales y análisis geométrico de áreas
# ============================================================

import re
import unicodedata

from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import requests

from services.external_sources.global_sources.geoboundaries_service import (
    obtener_geojson_geoboundaries,
)

from services.external_sources.global_sources.geoboundaries_analysis import (
    obtener_extremo_area_geoboundaries,
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
# ============================================================

ALIAS_PAISES = {

    # --------------------------------------------------------
    # AMÉRICA DEL SUR
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

    # --------------------------------------------------------
    # CENTROAMÉRICA Y NORTEAMÉRICA
    # --------------------------------------------------------

    "mexico": "MEX",
    "panama": "PAN",
    "costa rica": "CRI",
    "nicaragua": "NIC",
    "honduras": "HND",
    "el salvador": "SLV",
    "guatemala": "GTM",
    "belice": "BLZ",
    "belize": "BLZ",

    "estados unidos de america": "USA",
    "estados unidos": "USA",
    "united states": "USA",
    "usa": "USA",

    "canada": "CAN",

    # --------------------------------------------------------
    # CARIBE
    # --------------------------------------------------------

    "cuba": "CUB",
    "haiti": "HTI",
    "jamaica": "JAM",
    "republica dominicana": "DOM",
    "dominican republic": "DOM",

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
# NORMALIZAR TEXTO
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
# COMPROBAR FRASE
# ============================================================

def contiene_frase(
    texto: str,
    frase: str
) -> bool:

    texto_normalizado = (
        f" {normalizar_texto(texto)} "
    )

    frase_normalizada = (
        f" {normalizar_texto(frase)} "
    )

    return (
        frase_normalizada
        in texto_normalizado
    )


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

    catalogo = obtener_catalogo_paises()

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

        if not nombre:

            continue

        if len(codigo) != 3:

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
# DETECTAR CONSULTA GEOBOUNDARIES
# ============================================================

def es_consulta_geoboundaries(
    pregunta: str
) -> bool:

    texto = normalizar_texto(
        pregunta
    )

    # ========================================================
    # 1. CONSULTAS EXPLÍCITAS
    # ========================================================

    palabras_clave = [

        # Límites
        "limite",
        "limites",
        "frontera",
        "fronteras",

        # ADM1
        "departamento",
        "departamentos",
        "provincia",
        "provincias",
        "estado",
        "estados",
        "region",
        "regiones",

        # ADM2
        "municipio",
        "municipios",
        "condado",
        "condados",
        "distrito",
        "distritos",
        "comuna",
        "comunas",

        # General
        "division administrativa",
        "divisiones administrativas",
    ]

    if any(
        contiene_frase(
            texto,
            palabra
        )
        for palabra
        in palabras_clave
    ):

        return True


    # ========================================================
    # 2. MOSTRAR DIRECTAMENTE UN PAÍS
    #
    # Ejemplos:
    #
    # Muéstrame España
    # Muestra Colombia
    # Enséñame México
    # Dibuja Ecuador
    # Muéstrame el mapa de Perú
    # ========================================================

    acciones_mapa = [
        "muestrame",
        "muestra",
        "mostrar",
        "ensename",
        "ensena",
        "dibuja",
        "dibujame",
        "ver",
    ]

    tiene_accion_mapa = any(
        texto == accion
        or texto.startswith(
            accion + " "
        )
        for accion
        in acciones_mapa
    )

    if not tiene_accion_mapa:

        return False

    pais = resolver_pais(
        pregunta
    )

    if pais is None:

        return False

    _, nombre_detectado = pais

    resto = texto

    for accion in sorted(
        acciones_mapa,
        key=len,
        reverse=True
    ):

        if resto.startswith(
            accion + " "
        ):

            resto = resto[
                len(accion):
            ].strip()

            break

    # --------------------------------------------------------
    # QUITAR ARTÍCULOS
    # --------------------------------------------------------

    resto = re.sub(
        r"^(el|la|los|las)\s+",
        "",
        resto
    )

    # --------------------------------------------------------
    # QUITAR EXPRESIONES CARTOGRÁFICAS
    # --------------------------------------------------------

    resto = re.sub(
        r"^(mapa\s+de|territorio\s+de|pais\s+de)\s+",
        "",
        resto
    )

    # --------------------------------------------------------
    # QUITAR "EN EL MAPA"
    # --------------------------------------------------------

    resto = re.sub(
        r"\s+en\s+el\s+mapa$",
        "",
        resto
    ).strip()

    nombre_normalizado = (
        normalizar_texto(
            nombre_detectado
        )
    )

    return (
        resto ==
        nombre_normalizado
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
        for palabra
        in palabras_adm2
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
        for palabra
        in palabras_adm1
    ):

        return "ADM1"

    # --------------------------------------------------------
    # POR DEFECTO: PAÍS
    # --------------------------------------------------------

    return "ADM0"


# ============================================================
# ETIQUETA HUMANA PLURAL
# ============================================================

def obtener_etiqueta_nivel(
    pregunta: str,
    nivel: str
) -> str:

    texto = normalizar_texto(
        pregunta
    )

    if nivel == "ADM1":

        if (
            contiene_frase(
                texto,
                "departamento"
            )
            or contiene_frase(
                texto,
                "departamentos"
            )
        ):

            return "departamentos"

        if (
            contiene_frase(
                texto,
                "provincia"
            )
            or contiene_frase(
                texto,
                "provincias"
            )
        ):

            return "provincias"

        if (
            contiene_frase(
                texto,
                "estado"
            )
            or contiene_frase(
                texto,
                "estados"
            )
        ):

            return "estados"

        if (
            contiene_frase(
                texto,
                "region"
            )
            or contiene_frase(
                texto,
                "regiones"
            )
        ):

            return "regiones"

        return (
            "divisiones administrativas "
            "de primer nivel"
        )

    if nivel == "ADM2":

        if (
            contiene_frase(
                texto,
                "municipio"
            )
            or contiene_frase(
                texto,
                "municipios"
            )
        ):

            return "municipios"

        if (
            contiene_frase(
                texto,
                "condado"
            )
            or contiene_frase(
                texto,
                "condados"
            )
        ):

            return "condados"

        if (
            contiene_frase(
                texto,
                "distrito"
            )
            or contiene_frase(
                texto,
                "distritos"
            )
        ):

            return "distritos"

        if (
            contiene_frase(
                texto,
                "comuna"
            )
            or contiene_frase(
                texto,
                "comunas"
            )
        ):

            return "comunas"

        return (
            "divisiones administrativas "
            "de segundo nivel"
        )

    return "límite nacional"


# ============================================================
# ETIQUETA HUMANA SINGULAR
# ============================================================

def obtener_etiqueta_singular(
    pregunta: str,
    nivel: str
) -> Tuple[str, str]:

    texto = normalizar_texto(
        pregunta
    )

    if nivel == "ADM1":

        if (
            contiene_frase(
                texto,
                "departamento"
            )
            or contiene_frase(
                texto,
                "departamentos"
            )
        ):

            return (
                "el",
                "departamento"
            )

        if (
            contiene_frase(
                texto,
                "provincia"
            )
            or contiene_frase(
                texto,
                "provincias"
            )
        ):

            return (
                "la",
                "provincia"
            )

        if (
            contiene_frase(
                texto,
                "estado"
            )
            or contiene_frase(
                texto,
                "estados"
            )
        ):

            return (
                "el",
                "estado"
            )

        if (
            contiene_frase(
                texto,
                "region"
            )
            or contiene_frase(
                texto,
                "regiones"
            )
        ):

            return (
                "la",
                "región"
            )

        return (
            "la",
            "división administrativa"
        )

    if nivel == "ADM2":

        if (
            contiene_frase(
                texto,
                "municipio"
            )
            or contiene_frase(
                texto,
                "municipios"
            )
        ):

            return (
                "el",
                "municipio"
            )

        if (
            contiene_frase(
                texto,
                "condado"
            )
            or contiene_frase(
                texto,
                "condados"
            )
        ):

            return (
                "el",
                "condado"
            )

        if (
            contiene_frase(
                texto,
                "distrito"
            )
            or contiene_frase(
                texto,
                "distritos"
            )
        ):

            return (
                "el",
                "distrito"
            )

        if (
            contiene_frase(
                texto,
                "comuna"
            )
            or contiene_frase(
                texto,
                "comunas"
            )
        ):

            return (
                "la",
                "comuna"
            )

        return (
            "la",
            "división administrativa"
        )

    return (
        "el",
        "país"
    )


# ============================================================
# DETECTAR CRITERIO DE ÁREA
# ============================================================

def detectar_criterio_area(
    pregunta: str
) -> Optional[str]:

    texto = normalizar_texto(
        pregunta
    )

    # --------------------------------------------------------
    # MENOR ÁREA
    # --------------------------------------------------------

    expresiones_menor = [
        "mas pequena",
        "mas pequeno",
        "menor area",
        "de menor area",
        "la menor",
        "el menor",
        "mas chica",
        "mas chico",
    ]

    if any(
        expresion in texto
        for expresion
        in expresiones_menor
    ):

        return "menor"

    # --------------------------------------------------------
    # MAYOR ÁREA
    # --------------------------------------------------------

    expresiones_mayor = [
        "mas grande",
        "mayor area",
        "de mayor area",
        "la mayor",
        "el mayor",
        "mas extensa",
        "mas extenso",
    ]

    if any(
        expresion in texto
        for expresion
        in expresiones_mayor
    ):

        return "mayor"

    return None


# ============================================================
# FORMATEAR ÁREA EN ESPAÑOL
# ============================================================

def formatear_area_km2(
    area: Any
) -> str:

    try:

        numero = float(
            area
        )

    except (
        TypeError,
        ValueError
    ):

        return str(
            area
        )

    texto = (
        f"{numero:,.2f}"
    )

    texto = texto.replace(
        ",",
        "_"
    )

    texto = texto.replace(
        ".",
        ","
    )

    texto = texto.replace(
        "_",
        "."
    )

    return texto


# ============================================================
# RESOLVER CONSULTA GEOBOUNDARIES
# ============================================================

def resolver_consulta_geoboundaries(
    pregunta: str
) -> Optional[Dict[str, Any]]:

    # --------------------------------------------------------
    # 1. VERIFICAR INTENCIÓN
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

    if pais is None:

        # No apropiarse de consultas
        # que puedan resolver otras fuentes.
        return None

    codigo_iso3, nombre_detectado = pais

    # --------------------------------------------------------
    # 3. DETERMINAR NIVEL
    # --------------------------------------------------------

    nivel = determinar_nivel(
        pregunta
    )

    # ========================================================
    # 4. ANÁLISIS GEOMÉTRICO DE ÁREA
    # ========================================================

    criterio_area = (
        detectar_criterio_area(
            pregunta
        )
    )

    if criterio_area is not None:

        # ----------------------------------------------------
        # No tiene sentido comparar subdivisiones si
        # el nivel detectado quedó en ADM0.
        # ----------------------------------------------------

        if nivel == "ADM0":

            return {
                "ok": False,
                "tipo": "nivel_insuficiente",
                "modo": "datos",
                "fuente": "geoBoundaries",
                "codigo_iso3": codigo_iso3,
                "nivel": nivel,
                "consulta": pregunta,
                "mensaje": (
                    "Para comparar áreas debes indicar "
                    "un nivel administrativo, por ejemplo "
                    "provincia, departamento, estado, "
                    "región o municipio."
                ),
                "ejecuto_sql": False,
                "reutilizado": False
            }

        resultado_area = (
            obtener_extremo_area_geoboundaries(
                codigo_iso3=codigo_iso3,
                nivel=nivel,
                criterio=criterio_area
            )
        )

        if not isinstance(
            resultado_area,
            dict
        ):

            return {
                "ok": False,
                "tipo": "respuesta_invalida",
                "modo": "datos",
                "fuente": "geoBoundaries",
                "codigo_iso3": codigo_iso3,
                "nivel": nivel,
                "consulta": pregunta,
                "mensaje": (
                    "El análisis geométrico de "
                    "geoBoundaries devolvió una "
                    "respuesta inválida."
                ),
                "ejecuto_sql": False,
                "reutilizado": False
            }

        resultado_area[
            "consulta"
        ] = pregunta

        resultado_area[
            "analisis_area"
        ] = True

        # ----------------------------------------------------
        # ERROR CONTROLADO
        # ----------------------------------------------------

        if not resultado_area.get(
            "ok",
            False
        ):

            resultado_area[
                "ejecuto_sql"
            ] = False

            resultado_area[
                "reutilizado"
            ] = False

            return resultado_area

        # ----------------------------------------------------
        # CONSTRUIR MENSAJE NATURAL
        # ----------------------------------------------------

        articulo, tipo_division = (
            obtener_etiqueta_singular(
                pregunta,
                nivel
            )
        )

        nombre_division = (
            resultado_area.get(
                "nombre_division"
            )
            or "división administrativa"
        )

        area_km2 = (
            resultado_area.get(
                "area_km2_aprox"
            )
        )

        nombre_pais = (
            resultado_area.get(
                "nombre"
            )
            or nombre_detectado
            or codigo_iso3
        )

        area_formateada = (
            formatear_area_km2(
                area_km2
            )
        )

        if criterio_area == "menor":

            mensaje = (
                f"{articulo.capitalize()} "
                f"{tipo_division} de menor área "
                f"de {nombre_pais} es "
                f"{nombre_division}, "
                f"con aproximadamente "
                f"{area_formateada} km²."
            )

        else:

            mensaje = (
                f"{articulo.capitalize()} "
                f"{tipo_division} de mayor área "
                f"de {nombre_pais} es "
                f"{nombre_division}, "
                f"con aproximadamente "
                f"{area_formateada} km²."
            )

        resultado_area[
            "mensaje"
        ] = mensaje

        resultado_area[
            "inteligencia"
        ] = {
            "tipo": "analisis_geometrico",
            "fuente": "geoBoundaries",
            "mensaje": mensaje
        }

        resultado_area[
            "ejecuto_sql"
        ] = False

        resultado_area[
            "reutilizado"
        ] = False

        # ----------------------------------------------------
        # MEJORAR TÍTULO DE VISUALIZACIÓN
        # ----------------------------------------------------

        visualizacion = (
            resultado_area.get(
                "visualizacion"
            )
        )

        if isinstance(
            visualizacion,
            dict
        ):

            visualizacion[
                "titulo_leyenda"
            ] = (
                f"{nombre_division} — "
                f"{area_formateada} km²"
            )

        return resultado_area

    # ========================================================
    # 5. CONSULTA NORMAL DE LÍMITES
    # ========================================================

    resultado = (
        obtener_geojson_geoboundaries(
            codigo_iso3=codigo_iso3,
            nivel=nivel,
            simplificado=True
        )
    )

    # --------------------------------------------------------
    # ERROR CONTROLADO
    # --------------------------------------------------------

    if not resultado.get(
        "ok",
        False
    ):

        resultado[
            "consulta"
        ] = pregunta

        resultado[
            "codigo_iso3"
        ] = codigo_iso3

        resultado[
            "nivel"
        ] = nivel

        resultado[
            "ejecuto_sql"
        ] = False

        resultado[
            "reutilizado"
        ] = False

        return resultado

    # --------------------------------------------------------
    # RESPUESTA NATURAL
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
            f"{nombre_oficial} "
            f"desde geoBoundaries."
        )

    else:

        mensaje = (
            f"Se obtuvieron {total} "
            f"{etiqueta} de "
            f"{nombre_oficial} "
            f"desde geoBoundaries."
        )

    # --------------------------------------------------------
    # COMPLETAR RESPUESTA TERRI+
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
