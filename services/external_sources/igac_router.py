# ============================================================
# TERRI+
# IGAC ROUTER
#
# Orquestador general de consultas a servicios oficiales IGAC.
#
# Decide qué módulo debe resolver una pregunta:
#
# - Límites administrativos
# - Cartografía básica 1:100.000
# - Futuras fuentes IGAC
# ============================================================

import re
import unicodedata

from typing import Any, Dict, Optional


# ============================================================
# LÍMITES
# ============================================================

from services.external_sources.igac_service import (
    resolver_consulta_limites,
    detectar_municipio_en_pregunta,
    detectar_departamento_en_pregunta,
)


# ============================================================
# CARTOGRAFÍA 1:100.000
# ============================================================

from services.external_sources.igac_carto_100k import (
    consultar_vias_municipio,
)


# ============================================================
# NORMALIZAR TEXTO
# ============================================================

def normalizar_texto_router(
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

    return texto


# ============================================================
# DETECTAR CONSULTA DE VÍAS
# ============================================================

def es_consulta_vias(
    pregunta: str
) -> bool:

    texto = normalizar_texto_router(
        pregunta
    )

    palabras_vias = [
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
        "infraestructura vial"
    ]

    return any(
        palabra in texto
        for palabra in palabras_vias
    )


# ============================================================
# RESOLVER MUNICIPIO PARA CARTOGRAFÍA
# ============================================================

def resolver_municipio_cartografia(
    pregunta: str
) -> Optional[Dict[str, Any]]:

    municipio = (
        detectar_municipio_en_pregunta(
            pregunta
        )
    )

    if municipio:

        return municipio

    return None


# ============================================================
# RESOLVER CONSULTA DE VÍAS
# ============================================================

def resolver_consulta_vias(
    pregunta: str
) -> Optional[Dict[str, Any]]:

    if not es_consulta_vias(
        pregunta
    ):

        return None


    municipio = (
        resolver_municipio_cartografia(
            pregunta
        )
    )


    if not municipio:

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
                "tema": "vias",
                "mensaje": (
                    "Entendí que deseas consultar vías del IGAC, "
                    "pero por ahora esta primera versión consulta "
                    "las vías por municipio. "
                    f"Identifiqué el departamento "
                    f"'{departamento.get('departamento')}', "
                    "pero necesito que indiques un municipio."
                ),
                "ejecuto_sql": False,
                "reutilizado": False
            }


        return {
            "ok": False,
            "tipo": "sin_resultado",
            "modo": "datos",
            "fuente": "IGAC",
            "tema": "vias",
            "mensaje": (
                "Entendí que deseas consultar vías del IGAC, "
                "pero no pude identificar el municipio."
            ),
            "ejecuto_sql": False,
            "reutilizado": False
        }


    nombre_municipio = (
        municipio.get(
            "municipio"
        )
    )

    departamento = (
        municipio.get(
            "departamento"
        )
    )


    return consultar_vias_municipio(
        nombre=nombre_municipio,
        departamento=departamento
    )


# ============================================================
# RESOLVER CONSULTA GENERAL IGAC
# ============================================================

def resolver_consulta_igac(
    pregunta: str
) -> Optional[Dict[str, Any]]:

    if not isinstance(
        pregunta,
        str
    ):

        return None


    pregunta = pregunta.strip()


    if not pregunta:

        return None


    # ========================================================
    # 1. VÍAS
    # ========================================================
    #
    # Se evalúan antes que los límites porque una pregunta como:
    #
    # "Muéstrame las vías de Sesquilé según el IGAC"
    #
    # contiene la palabra IGAC y el resolver antiguo de límites
    # podría interpretarla erróneamente como una consulta de límite.
    # ========================================================

    respuesta_vias = (
        resolver_consulta_vias(
            pregunta
        )
    )


    if respuesta_vias is not None:

        return respuesta_vias


    # ========================================================
    # 2. LÍMITES ADMINISTRATIVOS
    # ========================================================

    respuesta_limites = (
        resolver_consulta_limites(
            pregunta
        )
    )


    if respuesta_limites is not None:

        return respuesta_limites


    # ========================================================
    # 3. FUTURAS CAPAS IGAC
    # ========================================================
    #
    # Próximamente podremos agregar aquí:
    #
    # - ríos
    # - drenajes
    # - canales
    # - lagunas
    # - embalses
    # - humedales
    # - pantanos
    # - puentes
    # - centros poblados
    # - cabeceras
    # - cuencas
    #
    # sin modificar analysis_service.py.
    # ========================================================

    return None
