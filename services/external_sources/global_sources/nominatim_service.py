# ============================================================
# TERRI+
# NOMINATIM / OPENSTREETMAP SERVICE
# Búsqueda mundial de lugares, POI, edificios y direcciones
# ============================================================

import time
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

# El servidor público de Nominatim exige identificar
# claramente la aplicación.
NOMINATIM_HEADERS = {
    "User-Agent": (
        "TERRI-IA-Territorial/1.0 "
        "(https://terri-api.onrender.com)"
    ),
    "Accept-Language": "es,en;q=0.8"
}

NOMINATIM_TIMEOUT = 20

# Cache simple en memoria.
# Evita repetir innecesariamente la misma búsqueda.
CACHE_NOMINATIM: Dict[str, Dict[str, Any]] = {}

# Control básico de frecuencia.
# El servidor público exige como máximo 1 petición/segundo.
ULTIMA_CONSULTA = 0.0


# ============================================================
# CONTROL DE FRECUENCIA
# ============================================================

def respetar_limite_frecuencia() -> None:

    global ULTIMA_CONSULTA

    ahora = time.time()

    transcurrido = (
        ahora
        - ULTIMA_CONSULTA
    )

    if transcurrido < 1.0:

        time.sleep(
            1.0 - transcurrido
        )

    ULTIMA_CONSULTA = time.time()


# ============================================================
# CLAVE DE CACHE
# ============================================================

def construir_clave_cache(
    consulta: str,
    pais: Optional[str] = None
) -> str:

    return (
        f"{str(consulta).strip().lower()}|"
        f"{str(pais or '').strip().lower()}"
    )


# ============================================================
# VERIFICAR SERVICIO
# ============================================================

def verificar_nominatim() -> Dict[str, Any]:

    try:

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
            "fuente": "OpenStreetMap/Nominatim",
            "mensaje": (
                "Servicio Nominatim disponible."
            )
        }

    except Exception as error:

        return {
            "ok": False,
            "fuente": "OpenStreetMap/Nominatim",
            "error": str(error)
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

    if not consulta:

        return {
            "ok": False,
            "fuente": "OpenStreetMap/Nominatim",
            "mensaje": (
                "Debes indicar un lugar para buscar."
            )
        }

    limite = max(
        1,
        min(
            int(limite),
            10
        )
    )

    clave_cache = construir_clave_cache(
        consulta=consulta,
        pais=pais
    )

    # --------------------------------------------------------
    # CACHE
    # --------------------------------------------------------

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

    if incluir_geometria:

        parametros[
            "polygon_geojson"
        ] = 1


    # --------------------------------------------------------
    # FILTRO DE PAÍS
    #
    # Nominatim utiliza códigos ISO de dos letras.
    # Ej: co, es, fr.
    # --------------------------------------------------------

    if pais:

        codigo_pais = str(
            pais
        ).strip().lower()

        if len(codigo_pais) == 2:

            parametros[
                "countrycodes"
            ] = codigo_pais


    try:

        respetar_limite_frecuencia()

        response = requests.get(
            NOMINATIM_SEARCH_URL,
            params=parametros,
            headers=NOMINATIM_HEADERS,
            timeout=NOMINATIM_TIMEOUT
        )

        response.raise_for_status()

        datos = response.json()

        if not isinstance(
            datos,
            list
        ):

            return {
                "ok": False,
                "fuente": "OpenStreetMap/Nominatim",
                "mensaje": (
                    "Nominatim devolvió una "
                    "respuesta inesperada."
                )
            }


        # ----------------------------------------------------
        # NORMALIZAR RESULTADOS
        # ----------------------------------------------------

        resultados: List[
            Dict[str, Any]
        ] = []

        for elemento in datos:

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

                continue


            boundingbox_original = (
                elemento.get(
                    "boundingbox"
                )
                or []
            )

            bbox = None

            if (
                isinstance(
                    boundingbox_original,
                    list
                )
                and len(
                    boundingbox_original
                ) == 4
            ):

                try:

                    sur = float(
                        boundingbox_original[
                            0
                        ]
                    )

                    norte = float(
                        boundingbox_original[
                            1
                        ]
                    )

                    oeste = float(
                        boundingbox_original[
                            2
                        ]
                    )

                    este = float(
                        boundingbox_original[
                            3
                        ]
                    )

                    bbox = [
                        oeste,
                        sur,
                        este,
                        norte
                    ]

                except (
                    TypeError,
                    ValueError
                ):

                    bbox = None


            resultados.append({

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

                "bbox": bbox,

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

                "tipo_direccion": (
                    elemento.get(
                        "addresstype"
                    )
                ),

                "importancia": (
                    elemento.get(
                        "importance"
                    )
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
            })


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


        CACHE_NOMINATIM[
            clave_cache
        ] = respuesta

        return respuesta


    except requests.exceptions.Timeout:

        return {
            "ok": False,
            "fuente": "OpenStreetMap/Nominatim",
            "mensaje": (
                "Nominatim tardó demasiado "
                "en responder."
            )
        }


    except requests.exceptions.HTTPError as error:

        return {
            "ok": False,
            "fuente": "OpenStreetMap/Nominatim",
            "mensaje": (
                "Nominatim respondió con "
                f"un error HTTP: {error}"
            )
        }


    except requests.exceptions.RequestException as error:

        return {
            "ok": False,
            "fuente": "OpenStreetMap/Nominatim",
            "mensaje": (
                "No fue posible consultar "
                "Nominatim."
            ),
            "error": str(error)
        }


    except Exception as error:

        return {
            "ok": False,
            "fuente": "OpenStreetMap/Nominatim",
            "mensaje": (
                "Ocurrió un error al procesar "
                "la consulta de Nominatim."
            ),
            "error": str(error)
        }


# ============================================================
# CONVERTIR PRIMER RESULTADO A GEOJSON TERRI+
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

    if not respuesta.get(
        "ok",
        False
    ):

        return respuesta


    resultados = respuesta.get(
        "resultados",
        []
    )


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
            "ejecuto_sql": False
        }


    lugar = resultados[0]


    # --------------------------------------------------------
    # GEOJSON
    #
    # Inicialmente usamos Point para mantener compatibilidad
    # directa con el frontend actual de TERRI+.
    # --------------------------------------------------------

    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [
                lugar[
                    "longitud"
                ],
                lugar[
                    "latitud"
                ]
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

            "direccion": lugar.get(
                "direccion"
            ),

            "importancia": lugar.get(
                "importancia"
            ),

            "fuente": (
                "OpenStreetMap/Nominatim"
            )
        }
    }


    geojson = {
        "type": "FeatureCollection",
        "features": [
            feature
        ]
    }


    bbox = lugar.get(
        "bbox"
    )

    if not bbox:

        bbox = [
            lugar[
                "longitud"
            ],
            lugar[
                "latitud"
            ],
            lugar[
                "longitud"
            ],
            lugar[
                "latitud"
            ]
        ]


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

        "atribucion": (
            "© OpenStreetMap contributors"
        ),

        "ejecuto_sql": False,
        "reutilizado": False
    }
