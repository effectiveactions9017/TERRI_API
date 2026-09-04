# ============================================================
# TERRI+
# IGAC ROUTER
#
# Orquestador general de consultas a servicios oficiales IGAC.
# ============================================================

import unicodedata

from typing import Any, Dict, Optional

from services.external_sources.igac_service import (
    resolver_consulta_limites,
    detectar_municipio_en_pregunta,
    detectar_departamento_en_pregunta,
)

from services.external_sources.igac_carto_100k import (
    consultar_tema_municipio,
)

from services.external_sources.igac_ocupacion import (
    consultar_ocupacion_municipio,
)


def normalizar_texto_router(
    valor: Any,
) -> str:

    texto = str(
        valor or ""
    ).strip().lower()

    texto = unicodedata.normalize(
        "NFD",
        texto,
    )

    return "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )


# ============================================================
# CATÁLOGO DE INTENCIONES
# ============================================================

INTENCIONES_CARTO = [

    (
        "cuerpos_agua",
        [
            "cuerpos de agua",
            "cuerpo de agua",
            "aguas superficiales",
        ],
    ),

    (
        "rios",
        [
            "rio",
            "rios",
            "quebrada",
            "quebradas",
            "drenaje",
            "drenajes",
            "hidrografia",
            "corrientes de agua",
            "corriente de agua",
        ],
    ),

    (
        "canales",
        [
            "canal",
            "canales",
        ],
    ),

    (
        "lagunas",
        [
            "laguna",
            "lagunas",
        ],
    ),

    (
        "humedales",
        [
            "humedal",
            "humedales",
        ],
    ),

    (
        "embalses",
        [
            "embalse",
            "embalses",
        ],
    ),

    (
        "cienagas",
        [
            "cienaga",
            "cienagas",
        ],
    ),

    (
        "pantanos",
        [
            "pantano",
            "pantanos",
        ],
    ),

    (
        "jagueyes",
        [
            "jaguey",
            "jagueyes",
        ],
    ),

    (
        "madreviejas",
        [
            "madrevieja",
            "madreviejas",
        ],
    ),

    (
        "morichales",
        [
            "morichal",
            "morichales",
        ],
    ),

    (
        "manglares",
        [
            "manglar",
            "manglares",
        ],
    ),

    (
        "puentes",
        [
            "puente",
            "puentes",
        ],
    ),

    (
        "via_ferrea",
        [
            "via ferrea",
            "vias ferreas",
            "ferrocarril",
            "ferrocarriles",
        ],
    ),

    (
        "tuneles",
        [
            "tunel",
            "tuneles",
        ],
    ),

    (
        "red_alta_tension",
        [
            "alta tension",
            "red electrica",
            "redes electricas",
            "lineas electricas",
        ],
    ),

    (
        "bosques",
        [
            "bosque",
            "bosques",
        ],
    ),

    (
        "orografia",
        [
            "orografia",
            "relieve",
        ],
    ),

    (
        "aeropuertos",
        [
            "aeropuerto",
            "aeropuertos",
            "pista de aterrizaje",
            "pistas de aterrizaje",
        ],
    ),

    (
        "puertos",
        [
            "puerto",
            "puertos",
            "muelle",
            "muelles",
            "embarcadero",
            "embarcaderos",
        ],
    ),

    (
        "vias",
        [
            "via",
            "vias",
            "carretera",
            "carreteras",
            "camino",
            "caminos",
            "sendero",
            "senderos",
            "red vial",
            "malla vial",
            "eje vial",
            "ejes viales",
            "infraestructura vial",
        ],
    ),
]


INTENCIONES_OCUPACION = [

    (
        "centros_poblados",
        [
            "centro poblado",
            "centros poblados",
            "poblados",
            "asentamientos",
        ],
    ),

    (
        "cabeceras",
        [
            "cabecera municipal",
            "cabeceras municipales",
            "cabecera",
            "cabeceras",
            "area urbana",
            "areas urbanas",
        ],
    ),
]


def detectar_intencion(
    pregunta: str,
    catalogo,
) -> Optional[str]:

    texto = normalizar_texto_router(
        pregunta
    )

    for tema, expresiones in catalogo:

        for expresion in expresiones:

            if expresion in texto:
                return tema

    return None


def obtener_municipio_pregunta(
    pregunta: str,
) -> Optional[Dict[str, Any]]:

    return detectar_municipio_en_pregunta(
        pregunta
    )


def respuesta_sin_municipio(
    tema: str,
    pregunta: str,
) -> Dict[str, Any]:

    departamento = (
        detectar_departamento_en_pregunta(
            pregunta
        )
    )

    if departamento:

        return {
            "ok": False,
            "tipo": "sin_resultado",
            "modo": "datos",
            "fuente": "IGAC",
            "tema": tema,
            "mensaje": (
                "Identifiqué el departamento "
                f"'{departamento.get('departamento')}', "
                "pero esta consulta cartográfica se realiza "
                "por municipio. Indica también el municipio."
            ),
            "ejecuto_sql": False,
            "reutilizado": False,
        }

    return {
        "ok": False,
        "tipo": "sin_resultado",
        "modo": "datos",
        "fuente": "IGAC",
        "tema": tema,
        "mensaje": (
            "Entendí la capa que deseas consultar, "
            "pero no pude identificar el municipio."
        ),
        "ejecuto_sql": False,
        "reutilizado": False,
    }


def resolver_tema_cartografia(
    pregunta: str,
    tema: str,
) -> Dict[str, Any]:

    municipio = obtener_municipio_pregunta(
        pregunta
    )

    if not municipio:

        return respuesta_sin_municipio(
            tema,
            pregunta,
        )

    return consultar_tema_municipio(
        tema=tema,
        nombre=municipio.get("municipio"),
        departamento=municipio.get("departamento"),
    )


def resolver_tema_ocupacion(
    pregunta: str,
    tema: str,
) -> Dict[str, Any]:

    municipio = obtener_municipio_pregunta(
        pregunta
    )

    if not municipio:

        return respuesta_sin_municipio(
            tema,
            pregunta,
        )

    return consultar_ocupacion_municipio(
        tema=tema,
        nombre=municipio.get("municipio"),
        departamento=municipio.get("departamento"),
    )


def resolver_consulta_igac(
    pregunta: str,
) -> Optional[Dict[str, Any]]:

    if not isinstance(pregunta, str):
        return None

    pregunta = pregunta.strip()

    if not pregunta:
        return None

    # --------------------------------------------------------
    # 1. CENTROS POBLADOS Y CABECERAS
    # --------------------------------------------------------

    tema_ocupacion = detectar_intencion(
        pregunta,
        INTENCIONES_OCUPACION,
    )

    if tema_ocupacion:

        return resolver_tema_ocupacion(
            pregunta,
            tema_ocupacion,
        )

    # --------------------------------------------------------
    # 2. CARTOGRAFÍA BÁSICA
    # --------------------------------------------------------

    tema_carto = detectar_intencion(
        pregunta,
        INTENCIONES_CARTO,
    )

    if tema_carto:

        return resolver_tema_cartografia(
            pregunta,
            tema_carto,
        )

    # --------------------------------------------------------
    # 3. LÍMITES ADMINISTRATIVOS
    # --------------------------------------------------------

    respuesta_limites = (
        resolver_consulta_limites(
            pregunta
        )
    )

    if respuesta_limites is not None:
        return respuesta_limites

    return None
