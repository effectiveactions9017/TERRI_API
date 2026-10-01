# ============================================================
# TERRI+
# NOMINATIM / OPENSTREETMAP SERVICE
# Búsqueda mundial de POI, edificios, instituciones,
# monumentos, lugares y direcciones
# ============================================================

import re
import time
import threading
import unicodedata

from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

import requests


# ============================================================
# CONFIGURACIÓN NOMINATIM
# ============================================================

NOMINATIM_BASE_URL = (
    "https://nominatim.openstreetmap.org"
)

NOMINATIM_SEARCH_URL = (
    f"{NOMINATIM_BASE_URL}/search"
)

NOMINATIM_TIMEOUT = 20


# ============================================================
# IDENTIFICACIÓN DE TERRI+
#
# El servidor público de Nominatim requiere identificar
# correctamente la aplicación.
# ============================================================

NOMINATIM_HEADERS = {

    "User-Agent": (
        "TERRI-IA-Territorial/1.0 "
        "(https://terri-api.onrender.com)"
    ),

    "Accept": "application/json",

    "Accept-Language": (
        "es,en;q=0.8"
    )
}


# ============================================================
# CONTROL DE FRECUENCIA
#
# Se usa un intervalo algo superior a 1 segundo para evitar
# trabajar exactamente en el límite del servicio público.
# ============================================================

INTERVALO_MINIMO_SEGUNDOS = 1.5

ULTIMA_CONSULTA = 0.0

LOCK_NOMINATIM = threading.Lock()


# ============================================================
# CACHE SIMPLE EN MEMORIA
#
# Evita consultar nuevamente Nominatim cuando TERRI+
# ya resolvió exactamente la misma búsqueda.
# ============================================================

CACHE_NOMINATIM: Dict[
    str,
    Dict[str, Any]
] = {}


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

    texto = re.sub(
        r"[^\w\s]",
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
# PALABRAS POCO INFORMATIVAS
#
# No queremos que palabras como "de", "la", "el" aumenten
# artificialmente la similitud entre dos lugares.
# ============================================================

PALABRAS_VACIAS = {
    "de",
    "del",
    "la",
    "las",
    "el",
    "los",
    "en",
    "y",
    "a"
}


# ============================================================
# LIMPIAR TEXTO PARA COMPARACIÓN
# ============================================================

def texto_comparable(
    valor: Any
) -> str:

    texto = normalizar_texto(
        valor
    )

    palabras = [
        palabra
        for palabra in texto.split()
        if palabra not in PALABRAS_VACIAS
    ]

    return " ".join(
        palabras
    )


# ============================================================
# CONSTRUIR CLAVE CACHE
# ============================================================

def construir_clave_cache(
    consulta: str,
    pais: Optional[str],
    limite: int,
    incluir_geometria: bool
) -> str:

    return "|".join(
        [
            normalizar_texto(
                consulta
            ),
            normalizar_texto(
                pais
            ),
            str(limite),
            str(
                incluir_geometria
            )
        ]
    )


# ============================================================
# CONTROLAR FRECUENCIA
# ============================================================

def respetar_limite_frecuencia() -> None:

    global ULTIMA_CONSULTA

    with LOCK_NOMINATIM:

        ahora = time.monotonic()

        transcurrido = (
            ahora
            - ULTIMA_CONSULTA
        )

        espera = (
            INTERVALO_MINIMO_SEGUNDOS
            - transcurrido
        )

        if espera > 0:

            time.sleep(
                espera
            )

        ULTIMA_CONSULTA = (
            time.monotonic()
        )


# ============================================================
# EXTRAER BBOX
#
# Nominatim devuelve:
# [sur, norte, oeste, este]
#
# TERRI+ utiliza:
# [xmin, ymin, xmax, ymax]
# ============================================================

def convertir_bbox(
    boundingbox: Any
) -> Optional[List[float]]:

    if not isinstance(
        boundingbox,
        list
    ):

        return None

    if len(
        boundingbox
    ) != 4:

        return None

    try:

        sur = float(
            boundingbox[0]
        )

        norte = float(
            boundingbox[1]
        )

        oeste = float(
            boundingbox[2]
        )

        este = float(
            boundingbox[3]
        )

        return [
            oeste,
            sur,
            este,
            norte
        ]

    except (
        TypeError,
        ValueError
    ):

        return None


# ============================================================
# NORMALIZAR RESULTADO NOMINATIM
# ============================================================

def normalizar_resultado(
    elemento: Dict[str, Any]
) -> Optional[Dict[str, Any]]:

    try:

        latitud = float(
            elemento.get(
                "lat"
            )
        )

        longitud = float(
            elemento.get(
                "lon"
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return None


    return {

        "place_id": elemento.get(
            "place_id"
        ),

        "osm_type": elemento.get(
            "osm_type"
        ),

        "osm_id": elemento.get(
            "osm_id"
        ),

        "nombre": elemento.get(
            "name"
        ),

        "nombre_completo": elemento.get(
            "display_name"
        ),

        "latitud": latitud,

        "longitud": longitud,

        "bbox": convertir_bbox(
            elemento.get(
                "boundingbox"
            )
        ),

        "categoria": (
            elemento.get(
                "category"
            )
            or elemento.get(
                "class"
            )
        ),

        "tipo": elemento.get(
            "type"
        ),

        "tipo_direccion": elemento.get(
            "addresstype"
        ),

        "importancia": elemento.get(
            "importance"
        ) or 0,

        "direccion": (
            elemento.get(
                "address"
            )
            or {}
        ),

        "extras": (
            elemento.get(
                "extratags"
            )
            or {}
        ),

        "nombres": (
            elemento.get(
                "namedetails"
            )
            or {}
        ),

        "geojson": elemento.get(
            "geojson"
        ),

        "fuente": (
            "OpenStreetMap/Nominatim"
        )
    }


# ============================================================
# BUSCAR NOMINATIM
# ============================================================

def buscar_nominatim(
    consulta: str,
    pais: Optional[str] = None,
    limite: int = 5,
    incluir_geometria: bool = False
) -> Dict[str, Any]:

    consulta = str(
        consulta or ""
    ).strip()

    if not consulta:

        return {
            "ok": False,
            "tipo": "consulta_invalida",
            "fuente": (
                "OpenStreetMap/Nominatim"
            ),
            "mensaje": (
                "Debes indicar un lugar "
                "para buscar."
            )
        }


    # --------------------------------------------------------
    # LIMITAR CANTIDAD DE RESULTADOS
    # --------------------------------------------------------

    try:

        limite = int(
            limite
        )

    except (
        TypeError,
        ValueError
    ):

        limite = 5


    limite = max(
        1,
        min(
            limite,
            10
        )
    )


    # --------------------------------------------------------
    # CACHE
    # --------------------------------------------------------

    clave_cache = construir_clave_cache(
        consulta=consulta,
        pais=pais,
        limite=limite,
        incluir_geometria=(
            incluir_geometria
        )
    )


    if clave_cache in CACHE_NOMINATIM:

        respuesta_cache = dict(
            CACHE_NOMINATIM[
                clave_cache
            ]
        )

        respuesta_cache[
            "cache"
        ] = True

        return respuesta_cache


    # --------------------------------------------------------
    # PARÁMETROS NOMINATIM
    # --------------------------------------------------------

    parametros = {

        "q": consulta,

        "format": "jsonv2",

        "addressdetails": 1,

        "extratags": 1,

        "namedetails": 1,

        "limit": limite,

        "dedupe": 1
    }


    # --------------------------------------------------------
    # FILTRO PAÍS
    #
    # Debe ser código ISO de dos letras:
    # co, es, fr...
    # --------------------------------------------------------

    if pais:

        codigo_pais = str(
            pais
        ).strip().lower()

        if len(
            codigo_pais
        ) == 2:

            parametros[
                "countrycodes"
            ] = codigo_pais


    # --------------------------------------------------------
    # GEOMETRÍA COMPLETA
    # --------------------------------------------------------

    if incluir_geometria:

        parametros[
            "polygon_geojson"
        ] = 1


    try:

        respetar_limite_frecuencia()


        response = requests.get(
            NOMINATIM_SEARCH_URL,
            params=parametros,
            headers=NOMINATIM_HEADERS,
            timeout=NOMINATIM_TIMEOUT
        )


        # ----------------------------------------------------
        # HTTP 429
        #
        # NO reintentamos automáticamente.
        # ----------------------------------------------------

        if response.status_code == 429:

            return {
                "ok": False,
                "tipo": "limite_solicitudes",
                "fuente": (
                    "OpenStreetMap/Nominatim"
                ),
                "codigo_http": 429,
                "mensaje": (
                    "El servicio público de "
                    "OpenStreetMap/Nominatim ha "
                    "limitado temporalmente las consultas. "
                    "Intenta nuevamente más tarde."
                ),
                "ejecuto_sql": False
            }


        response.raise_for_status()


        datos = response.json()


        if not isinstance(
            datos,
            list
        ):

            return {
                "ok": False,
                "tipo": "respuesta_invalida",
                "fuente": (
                    "OpenStreetMap/Nominatim"
                ),
                "mensaje": (
                    "Nominatim devolvió una "
                    "respuesta inesperada."
                ),
                "ejecuto_sql": False
            }


        resultados = []


        for elemento in datos:

            if not isinstance(
                elemento,
                dict
            ):

                continue


            resultado = (
                normalizar_resultado(
                    elemento
                )
            )


            if resultado:

                resultados.append(
                    resultado
                )


        respuesta = {

            "ok": True,

            "fuente": (
                "OpenStreetMap/Nominatim"
            ),

            "consulta": consulta,

            "total": len(
                resultados
            ),

            "resultados": resultados,

            "cache": False,

            "atribucion": (
                "© OpenStreetMap contributors"
            )
        }


        # ----------------------------------------------------
        # SOLO CACHEAR RESPUESTAS CORRECTAS
        # ----------------------------------------------------

        CACHE_NOMINATIM[
            clave_cache
        ] = respuesta


        return respuesta


    except requests.exceptions.Timeout:

        return {
            "ok": False,
            "tipo": "timeout",
            "fuente": (
                "OpenStreetMap/Nominatim"
            ),
            "mensaje": (
                "Nominatim tardó demasiado "
                "en responder."
            ),
            "ejecuto_sql": False
        }


    except requests.exceptions.HTTPError as error:

        return {
            "ok": False,
            "tipo": "error_http",
            "fuente": (
                "OpenStreetMap/Nominatim"
            ),
            "mensaje": (
                "Nominatim respondió con "
                f"un error HTTP: {error}"
            ),
            "ejecuto_sql": False
        }


    except requests.exceptions.RequestException as error:

        return {
            "ok": False,
            "tipo": "conexion",
            "fuente": (
                "OpenStreetMap/Nominatim"
            ),
            "mensaje": (
                "No fue posible consultar "
                "Nominatim."
            ),
            "error": str(error),
            "ejecuto_sql": False
        }


    except Exception as error:

        return {
            "ok": False,
            "tipo": "error",
            "fuente": (
                "OpenStreetMap/Nominatim"
            ),
            "mensaje": (
                "Ocurrió un error al procesar "
                "la consulta de Nominatim."
            ),
            "error": str(error),
            "ejecuto_sql": False
        }


# ============================================================
# CALCULAR SIMILITUD
# ============================================================

def calcular_similitud(
    consulta: str,
    candidato: str
) -> float:

    consulta = texto_comparable(
        consulta
    )

    candidato = texto_comparable(
        candidato
    )


    if (
        not consulta
        or not candidato
    ):

        return 0.0


    return SequenceMatcher(
        None,
        consulta,
        candidato
    ).ratio()


# ============================================================
# PUNTUAR CANDIDATO
# ============================================================

def puntuar_candidato(
    consulta: str,
    lugar: Dict[str, Any]
) -> Dict[str, Any]:

    puntuacion = 0.0


    consulta_normalizada = (
        texto_comparable(
            consulta
        )
    )


    nombre = (
        lugar.get(
            "nombre"
        )
        or ""
    )


    nombre_completo = (
        lugar.get(
            "nombre_completo"
        )
        or ""
    )


    nombre_normalizado = (
        texto_comparable(
            nombre
        )
    )


    # --------------------------------------------------------
    # SIMILITUD DEL NOMBRE PRINCIPAL
    # --------------------------------------------------------

    similitud_nombre = (
        calcular_similitud(
            consulta,
            nombre
        )
    )


    puntuacion += (
        similitud_nombre
        * 100
    )


    # --------------------------------------------------------
    # COINCIDENCIA EXACTA
    # --------------------------------------------------------

    if (
        nombre_normalizado
        and nombre_normalizado
        == consulta_normalizada
    ):

        puntuacion += 80


    # --------------------------------------------------------
    # NOMBRE CONTENIDO EN LA CONSULTA
    # --------------------------------------------------------

    elif (
        nombre_normalizado
        and (
            nombre_normalizado
            in consulta_normalizada
            or consulta_normalizada
            in nombre_normalizado
        )
    ):

        puntuacion += 35


    # --------------------------------------------------------
    # SIMILITUD CON DISPLAY NAME
    # --------------------------------------------------------

    similitud_completa = (
        calcular_similitud(
            consulta,
            nombre_completo
        )
    )


    puntuacion += (
        similitud_completa
        * 25
    )


    # --------------------------------------------------------
    # IMPORTANCIA NOMINATIM
    #
    # Se usa como complemento, nunca como criterio principal.
    # --------------------------------------------------------

    try:

        importancia = float(
            lugar.get(
                "importancia"
            )
            or 0
        )

    except (
        TypeError,
        ValueError
    ):

        importancia = 0.0


    puntuacion += (
        importancia
        * 20
    )


    # --------------------------------------------------------
    # PENALIZAR RESULTADOS COMERCIALES DE BAJA RELEVANCIA
    #
    # Esto ayuda con casos como:
    # Palacio de Nariño
    # -> Palacio del Granizado (ice_cream)
    # --------------------------------------------------------

    categoria = normalizar_texto(
        lugar.get(
            "categoria"
        )
    )


    tipo = normalizar_texto(
        lugar.get(
            "tipo"
        )
    )


    tipos_comerciales_baja_confianza = {
        "ice_cream",
        "fast_food",
        "cafe",
        "restaurant",
        "bar",
        "pub",
        "shop"
    }


    if (
        tipo
        in tipos_comerciales_baja_confianza
        and similitud_nombre < 0.75
    ):

        puntuacion -= 80


    # --------------------------------------------------------
    # BONIFICAR ALGUNOS TIPOS DE POI RELEVANTES
    # --------------------------------------------------------

    tipos_relevantes = {

        "government",
        "townhall",
        "public_building",
        "university",
        "college",
        "school",
        "hospital",
        "museum",
        "monument",
        "memorial",
        "castle",
        "palace",
        "airport",
        "aerodrome",
        "attraction",
        "place_of_worship"
    }


    if tipo in tipos_relevantes:

        puntuacion += 15


    return {

        **lugar,

        "_similitud_nombre": round(
            similitud_nombre,
            4
        ),

        "_similitud_completa": round(
            similitud_completa,
            4
        ),

        "_puntuacion": round(
            puntuacion,
            4
        )
    }


# ============================================================
# SELECCIONAR MEJOR RESULTADO
# ============================================================

def seleccionar_mejor_resultado(
    consulta: str,
    resultados: List[
        Dict[str, Any]
    ]
) -> Dict[str, Any]:

    if not resultados:

        return {
            "estado": "sin_resultado",
            "resultado": None,
            "opciones": []
        }


    evaluados = [

        puntuar_candidato(
            consulta=consulta,
            lugar=lugar
        )

        for lugar in resultados
    ]


    evaluados.sort(
        key=lambda lugar: (
            lugar.get(
                "_puntuacion",
                0
