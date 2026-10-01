# ============================================================
# TERRI+
# NOMINATIM / OPENSTREETMAP SERVICE
#
# Búsqueda mundial de:
# - edificios
# - instituciones
# - monumentos
# - aeropuertos
# - hospitales
# - universidades
# - direcciones
# - POI
#
# Compatible con TERRI+ + MapLibre
# ============================================================

import re
import time
import threading
import unicodedata

from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

import requests


# ============================================================
# CONFIGURACIÓN
# ============================================================

NOMINATIM_BASE_URL = (
    "https://nominatim.openstreetmap.org"
)

NOMINATIM_SEARCH_URL = (
    f"{NOMINATIM_BASE_URL}/search"
)

NOMINATIM_TIMEOUT = 20


# ============================================================
# HEADERS
#
# Nominatim público exige identificar la aplicación.
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
# Usamos 1.5 segundos para mantenernos por debajo
# del límite del servicio público.
# ============================================================

INTERVALO_MINIMO_SEGUNDOS = 1.5

ULTIMA_CONSULTA = 0.0

LOCK_NOMINATIM = threading.Lock()


# ============================================================
# CACHE EN MEMORIA
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
# TEXTO COMPARABLE
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
# CONTROL DE FRECUENCIA
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
# CONVERTIR BOUNDING BOX
#
# Nominatim:
# [sur, norte, oeste, este]
#
# TERRI+:
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

        "importancia": (
            elemento.get(
                "importance"
            )
            or 0
        ),

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
# VERIFICAR SERVICIO
# ============================================================

def verificar_nominatim() -> Dict[str, Any]:

    # --------------------------------------------------------
    # IMPORTANTE:
    #
    # No hacemos una segunda consulta especial.
    # Utilizamos la misma función de búsqueda.
    # --------------------------------------------------------

    resultado = buscar_nominatim(
        consulta="Bogotá, Colombia",
        limite=1
    )

    if not resultado.get(
        "ok",
        False
    ):

        return resultado

    return {
        "ok": True,
        "fuente": (
            "OpenStreetMap/Nominatim"
        ),
        "mensaje": (
            "Servicio Nominatim disponible."
        )
    }


# ============================================================
# BUSCAR EN NOMINATIM
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


    # --------------------------------------------------------
    # VALIDAR CONSULTA
    # --------------------------------------------------------

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
            ),
            "ejecuto_sql": False
        }


    # --------------------------------------------------------
    # VALIDAR LÍMITE
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
    # PARÁMETROS
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
    # Debe recibirse como código ISO:
    # co, es, fr, etc.
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
        # 429 - DEMASIADAS SOLICITUDES
        #
        # No reintentamos automáticamente.
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


        resultados: List[
            Dict[str, Any]
        ] = []


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
        # CACHEAR SOLO RESPUESTAS CORRECTAS
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
            "error": str(
                error
            ),
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
            "error": str(
                error
            ),
            "ejecuto_sql": False
        }


# ============================================================
# CALCULAR SIMILITUD
# ============================================================

def calcular_similitud(
    consulta: str,
    candidato: str
) -> float:

    consulta_limpia = (
        texto_comparable(
            consulta
        )
    )

    candidato_limpio = (
        texto_comparable(
            candidato
        )
    )


    if (
        not consulta_limpia
        or not candidato_limpio
    ):

        return 0.0


    return SequenceMatcher(
        None,
        consulta_limpia,
        candidato_limpio
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
    # NOMBRE CONTENIDO
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
    # CATEGORÍA Y TIPO
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


    # --------------------------------------------------------
    # PENALIZAR COMERCIOS DE BAJA COINCIDENCIA
    #
    # Ejemplo:
    # Palacio de Nariño
    # -> Palacio del Granizado / ice_cream
    # --------------------------------------------------------

    tipos_comerciales = {

        "ice_cream",
        "fast_food",
        "cafe",
        "restaurant",
        "bar",
        "pub",
        "supermarket",
        "convenience",
        "clothes",
        "beauty",
        "hairdresser"
    }


    if (
        tipo in tipos_comerciales
        and similitud_nombre < 0.75
    ):

        puntuacion -= 80


    # --------------------------------------------------------
    # BONIFICAR POI TERRITORIALES IMPORTANTES
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
        # --------------------------------------------------------
    # BONIFICACIÓN POR TIPO RELEVANTE
    # --------------------------------------------------------

    if tipo in tipos_relevantes:
        puntuacion += 20


    # --------------------------------------------------------
    # BONIFICACIÓN POR CATEGORÍA
    # --------------------------------------------------------

    categorias_relevantes = {
        "amenity",
        "tourism",
        "historic",
        "aeroway",
        "office",
        "building",
        "leisure",
        "natural",
        "place"
    }


    if categoria in categorias_relevantes:
        puntuacion += 5


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
    resultados: List[Dict[str, Any]]
) -> Dict[str, Any]:

    # --------------------------------------------------------
    # SIN RESULTADOS
    # --------------------------------------------------------

    if not resultados:

        return {
            "estado": "sin_resultado",
            "resultado": None,
            "opciones": []
        }


    # --------------------------------------------------------
    # PUNTUAR TODOS LOS CANDIDATOS
    # --------------------------------------------------------

    evaluados = []

    for lugar in resultados:

        evaluado = puntuar_candidato(
            consulta=consulta,
            lugar=lugar
        )

        evaluados.append(
            evaluado
        )


    # --------------------------------------------------------
    # ORDENAR DE MAYOR A MENOR PUNTUACIÓN
    # --------------------------------------------------------

    evaluados.sort(
        key=lambda lugar: lugar.get(
            "_puntuacion",
            0
        ),
        reverse=True
    )


    mejor = evaluados[0]


    # --------------------------------------------------------
    # VALIDAR CONFIANZA DEL MEJOR RESULTADO
    #
    # Evita aceptar resultados poco relacionados.
    #
    # Ejemplo:
    #
    # Palacio de Nariño
    # ->
    # Palacio del Granizado
    # --------------------------------------------------------

    similitud = mejor.get(
        "_similitud_nombre",
        0
    )

    puntuacion = mejor.get(
        "_puntuacion",
        0
    )


    if (
        similitud < 0.45
        and puntuacion < 70
    ):

        return {
            "estado": "baja_confianza",
            "resultado": None,
            "opciones": evaluados[:5]
        }


    # --------------------------------------------------------
    # COMPROBAR SI LOS DOS MEJORES SON EL MISMO LUGAR
    #
    # Nominatim puede devolver un mismo sitio varias veces:
    #
    # - como WAY
    # - como NODE
    # - con nombre español
    # - con nombre inglés
    #
    # Ejemplo:
    #
    # Casa de Nariño (Presidencia de la República)
    #
    # Casa de Nariño (Presidential Palace)
    #
    # Ambos pueden representar exactamente el mismo lugar.
    # --------------------------------------------------------

    if len(evaluados) >= 2:

        segundo = evaluados[1]

        mismo_lugar = False


        # ----------------------------------------------------
        # MÉTODO 1
        # MISMO IDENTIFICADOR WIKIDATA
        #
        # Es la señal más fuerte.
        # ----------------------------------------------------

        extras_mejor = (
            mejor.get(
                "extras"
            )
            or {}
        )

        extras_segundo = (
            segundo.get(
                "extras"
            )
            or {}
        )


        wikidata_mejor = (
            extras_mejor.get(
                "wikidata"
            )
        )

        wikidata_segundo = (
            extras_segundo.get(
                "wikidata"
            )
        )


        if (
            wikidata_mejor
            and wikidata_segundo
            and wikidata_mejor
            == wikidata_segundo
        ):

            mismo_lugar = True


        # ----------------------------------------------------
        # MÉTODO 2
        # COORDENADAS MUY CERCANAS
        #
        # Solo se utiliza si Wikidata no permitió
        # identificar el duplicado.
        # ----------------------------------------------------

        if not mismo_lugar:

            try:

                latitud_mejor = float(
                    mejor.get(
                        "latitud"
                    )
                )

                longitud_mejor = float(
                    mejor.get(
                        "longitud"
                    )
                )

                latitud_segundo = float(
                    segundo.get(
                        "latitud"
                    )
                )

                longitud_segundo = float(
                    segundo.get(
                        "longitud"
                    )
                )


                diferencia_latitud = abs(
                    latitud_mejor
                    - latitud_segundo
                )

                diferencia_longitud = abs(
                    longitud_mejor
                    - longitud_segundo
                )


                # --------------------------------------------
                # Además de estar cerca, deben compartir
                # tipo o categoría.
                #
                # Esto evita fusionar dos POI diferentes
                # simplemente porque están uno al lado
                # del otro.
                # --------------------------------------------

                mismo_tipo = (
                    mejor.get(
                        "tipo"
                    )
                    == segundo.get(
                        "tipo"
                    )
                )

                misma_categoria = (
                    mejor.get(
                        "categoria"
                    )
                    == segundo.get(
                        "categoria"
                    )
                )


                if (
                    diferencia_latitud < 0.002
                    and diferencia_longitud < 0.002
                    and (
                        mismo_tipo
                        or misma_categoria
                    )
                ):

                    mismo_lugar = True


            except (
                TypeError,
                ValueError
            ):

                pass


        # ----------------------------------------------------
        # SI SON EL MISMO LUGAR
        #
        # Conservamos el resultado con mayor puntuación.
        #
        # No lo consideramos una ambigüedad real.
        # ----------------------------------------------------

        if mismo_lugar:

            return {
                "estado": "encontrado",
                "resultado": mejor,
                "opciones": evaluados[:5],
                "duplicados_detectados": True
            }


    # --------------------------------------------------------
    # VALIDAR AMBIGÜEDAD REAL
    #
    # Si los dos mejores resultados son diferentes y tienen
    # puntuaciones muy similares, TERRI+ no debe escoger
    # arbitrariamente.
    # --------------------------------------------------------

    if len(evaluados) >= 2:

        segundo = evaluados[1]


        diferencia = (
            mejor.get(
                "_puntuacion",
                0
            )
            -
            segundo.get(
                "_puntuacion",
                0
            )
        )


        if (
            diferencia < 5
            and similitud < 0.80
        ):

            return {
                "estado": "ambiguo",
                "resultado": None,
                "opciones": evaluados[:5]
            }


    # --------------------------------------------------------
    # RESULTADO FINAL
    # --------------------------------------------------------

    return {
        "estado": "encontrado",
        "resultado": mejor,
        "opciones": evaluados[:5],
        "duplicados_detectados": False
    }
    # ============================================================
# CONSTRUIR OPCIONES SIMPLIFICADAS
# ============================================================

def construir_opciones(
    opciones: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    resultado = []

    for lugar in opciones:

        resultado.append({

            "nombre": lugar.get(
                "nombre"
            ),

            "nombre_completo": lugar.get(
                "nombre_completo"
            ),

            "categoria": lugar.get(
                "categoria"
            ),

            "tipo": lugar.get(
                "tipo"
            ),

            "latitud": lugar.get(
                "latitud"
            ),

            "longitud": lugar.get(
                "longitud"
            ),

            "importancia": lugar.get(
                "importancia"
            ),

            "puntuacion": lugar.get(
                "_puntuacion"
            )
        })

    return resultado


# ============================================================
# BUSCAR LUGAR Y CONVERTIR A GEOJSON TERRI+
# ============================================================

def buscar_lugar_nominatim_geojson(
    consulta: str,
    pais: Optional[str] = None
) -> Dict[str, Any]:

    respuesta = buscar_nominatim(
        consulta=consulta,
        pais=pais,
        limite=5,
        incluir_geometria=False
    )

    # --------------------------------------------------------
    # ERROR DE SERVICIO
    # --------------------------------------------------------

    if not respuesta.get(
        "ok",
        False
    ):

        return respuesta


    resultados = respuesta.get(
        "resultados",
        []
    )


    # --------------------------------------------------------
    # SIN RESULTADOS
    # --------------------------------------------------------

    if not resultados:

        return {
            "ok": False,
            "tipo": "sin_resultado",
            "modo": "datos",
            "fuente": (
                "OpenStreetMap/Nominatim"
            ),
            "consulta": consulta,
            "mensaje": (
                f"No encontré '{consulta}' "
                "en OpenStreetMap."
            ),
            "ejecuto_sql": False,
            "reutilizado": False
        }


    # --------------------------------------------------------
    # SELECCIONAR MEJOR RESULTADO
    # --------------------------------------------------------

    seleccion = (
        seleccionar_mejor_resultado(
            consulta=consulta,
            resultados=resultados
        )
    )


    estado = seleccion.get(
        "estado"
    )


    # --------------------------------------------------------
    # BAJA CONFIANZA
    # --------------------------------------------------------

    if estado == "baja_confianza":

        return {
            "ok": False,
            "tipo": "baja_confianza",
            "modo": "datos",
            "fuente": (
                "OpenStreetMap/Nominatim"
            ),
            "consulta": consulta,
            "mensaje": (
                "OpenStreetMap encontró resultados, "
                "pero ninguno coincide con suficiente "
                "confianza con el lugar solicitado."
            ),
            "opciones": construir_opciones(
                seleccion.get(
                    "opciones",
                    []
                )
            ),
            "ejecuto_sql": False,
            "reutilizado": False
        }


    # --------------------------------------------------------
    # AMBIGÜEDAD
    # --------------------------------------------------------

    if estado == "ambiguo":

        return {
            "ok": False,
            "tipo": "ambiguo",
            "modo": "datos",
            "fuente": (
                "OpenStreetMap/Nominatim"
            ),
            "consulta": consulta,
            "mensaje": (
                "Encontré varios lugares posibles "
                "en OpenStreetMap. "
                "Indica más información para precisar "
                "la ubicación."
            ),
            "opciones": construir_opciones(
                seleccion.get(
                    "opciones",
                    []
                )
            ),
            "ejecuto_sql": False,
            "reutilizado": False
        }


    # --------------------------------------------------------
    # RESULTADO SELECCIONADO
    # --------------------------------------------------------

    lugar = seleccion.get(
        "resultado"
    )


    if not isinstance(
        lugar,
        dict
    ):

        return {
            "ok": False,
            "tipo": "sin_resultado",
            "modo": "datos",
            "fuente": (
                "OpenStreetMap/Nominatim"
            ),
            "consulta": consulta,
            "mensaje": (
                "No fue posible seleccionar "
                "una ubicación válida."
            ),
            "ejecuto_sql": False,
            "reutilizado": False
        }


    # --------------------------------------------------------
    # CREAR FEATURE GEOJSON
    # --------------------------------------------------------

    feature = {

        "type": "Feature",

        "geometry": {

            "type": "Point",

            "coordinates": [
                lugar.get(
                    "longitud"
                ),
                lugar.get(
                    "latitud"
                )
            ]
        },

        "properties": {

            "place_id": lugar.get(
                "place_id"
            ),

            "osm_type": lugar.get(
                "osm_type"
            ),

            "osm_id": lugar.get(
                "osm_id"
            ),

            "nombre": lugar.get(
                "nombre"
            ),

            "nombre_completo": lugar.get(
                "nombre_completo"
            ),

            "categoria": lugar.get(
                "categoria"
            ),

            "tipo": lugar.get(
                "tipo"
            ),

            "tipo_direccion": lugar.get(
                "tipo_direccion"
            ),

            "direccion": lugar.get(
                "direccion"
            ),

            "extras": lugar.get(
                "extras"
            ),

            "nombres": lugar.get(
                "nombres"
            ),

            "importancia": lugar.get(
                "importancia"
            ),

            "puntuacion_terri": lugar.get(
                "_puntuacion"
            ),

            "fuente": (
                "OpenStreetMap/Nominatim"
            )
        }
    }


    # --------------------------------------------------------
    # FEATURE COLLECTION
    # --------------------------------------------------------

    geojson = {

        "type": "FeatureCollection",

        "features": [
            feature
        ]
    }


    # --------------------------------------------------------
    # BBOX
    # --------------------------------------------------------

    bbox = lugar.get(
        "bbox"
    )


    if not bbox:

        longitud = lugar.get(
            "longitud"
        )

        latitud = lugar.get(
            "latitud"
        )

        bbox = [
            longitud,
            latitud,
            longitud,
            latitud
        ]


    # --------------------------------------------------------
    # MENSAJE
    # --------------------------------------------------------

    nombre = (
        lugar.get(
            "nombre"
        )
        or consulta
    )


    direccion = (
        lugar.get(
            "direccion"
        )
        or {}
    )


    ciudad = (
        direccion.get("city")
        or direccion.get("town")
        or direccion.get("municipality")
        or direccion.get("village")
        or ""
    )


    pais_nombre = (
        direccion.get(
            "country"
        )
        or ""
    )


    ubicacion = ", ".join(
        valor
        for valor in [
            nombre,
            ciudad,
            pais_nombre
        ]
        if valor
    )


    mensaje = (
        f"Localicé {ubicacion} "
        "utilizando OpenStreetMap."
    )


    # --------------------------------------------------------
    # RESPUESTA TERRI+
    # --------------------------------------------------------

    return {

        "ok": True,

        "tipo": "geojson",

        "modo": "mapa",

        "fuente": (
            "OpenStreetMap/Nominatim"
        ),

        "consulta": consulta,

        "resultado": geojson,

        "total_features": 1,

        "bbox": bbox,

        "layer_id": (
            "nominatim_lugar"
        ),

        "visualizacion": {

            "modo": "simple",

            "campo_categoria": None,

            "campo_valor": None,

            "mostrar_leyenda": False,

            "titulo_leyenda": (
                "Lugar — OpenStreetMap"
            )
        },

        "mensaje": mensaje,

        "atribucion": (
            "© OpenStreetMap contributors"
        ),

        "ejecuto_sql": False,

        "reutilizado": False,

        "inteligencia": {

            "tipo": (
                "fuente_externa"
            ),

            "fuente": (
                "OpenStreetMap/Nominatim"
            ),

            "mensaje": mensaje
        }
    }
