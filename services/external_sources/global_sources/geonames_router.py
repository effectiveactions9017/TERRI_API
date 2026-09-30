# ============================================================
# TERRI+
# GEONAMES ROUTER
# Detecta consultas de toponimia y localización internacional
# ============================================================

import re
import unicodedata
from typing import Optional

from services.external_sources.global_sources.geonames_service import (
    buscar_lugar_geojson,
)


# ============================================================
# NORMALIZAR TEXTO
# ============================================================

def normalizar_texto(texto: str) -> str:

    texto = str(texto or "").strip().lower()

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
# DETECTAR CONSULTA GEONAMES
# ============================================================

def es_consulta_geonames(
    pregunta: str
) -> bool:

    texto = normalizar_texto(
        pregunta
    )

    expresiones = [
        "ubica ",
        "ubicame ",
        "localiza ",
        "localizame ",
        "donde queda ",
        "donde esta ",
        "buscar lugar ",
        "busca el lugar ",
        "busca la ciudad ",
        "busca la poblacion ",
        "busca el pueblo ",
    ]

    return any(
        expresion in texto
        for expresion in expresiones
    )


# ============================================================
# EXTRAER NOMBRE DEL LUGAR
# ============================================================

def extraer_lugar(
    pregunta: str
) -> str:

    texto = str(
        pregunta or ""
    ).strip()

    patrones = [
        r"(?i)^ub[ií]came\s+",
        r"(?i)^ubica\s+",
        r"(?i)^local[ií]zame\s+",
        r"(?i)^localiza\s+",
        r"(?i)^d[oó]nde\s+queda\s+",
        r"(?i)^d[oó]nde\s+est[aá]\s+",
        r"(?i)^busca\s+el\s+lugar\s+",
        r"(?i)^busca\s+la\s+ciudad\s+",
        r"(?i)^busca\s+la\s+poblaci[oó]n\s+",
        r"(?i)^busca\s+el\s+pueblo\s+",
    ]

    for patron in patrones:

        texto = re.sub(
            patron,
            "",
            texto
        )

    return texto.strip(
        " .?!¿¡"
    )


# ============================================================
# RESOLVER CONSULTA GEONAMES
# ============================================================

def resolver_consulta_geonames(
    pregunta: str
) -> Optional[dict]:

    # --------------------------------------------------------
    # Si no parece una consulta GeoNames,
    # dejamos que TERRI+ continúe con las demás fuentes.
    # --------------------------------------------------------

    if not es_consulta_geonames(
        pregunta
    ):
        return None

    # --------------------------------------------------------
    # Extraer lugar
    # --------------------------------------------------------

    lugar = extraer_lugar(
        pregunta
    )

    if not lugar:

        return {
            "ok": False,
            "tipo": "datos",
            "modo": "datos",
            "fuente": "GeoNames",
            "mensaje": (
                "Indica el lugar que deseas localizar."
            )
        }

    # --------------------------------------------------------
    # Consultar GeoNames
    # --------------------------------------------------------

    respuesta = buscar_lugar_geojson(
        nombre=lugar
    )

    if not isinstance(
        respuesta,
        dict
    ):

        return {
            "ok": False,
            "tipo": "datos",
            "modo": "datos",
            "fuente": "GeoNames",
            "mensaje": (
                "GeoNames no devolvió una respuesta válida."
            )
        }

    if not respuesta.get(
        "ok",
        False
    ):
        return respuesta

    # --------------------------------------------------------
    # Validar GeoJSON
    # --------------------------------------------------------

    geojson = respuesta.get(
        "resultado"
    )

    if not isinstance(
        geojson,
        dict
    ):

        return {
            "ok": False,
            "tipo": "datos",
            "modo": "datos",
            "fuente": "GeoNames",
            "mensaje": (
                "GeoNames no devolvió geometría válida."
            )
        }

    features = geojson.get(
        "features",
        []
    )

    if not features:

        return {
            "ok": False,
            "tipo": "datos",
            "modo": "datos",
            "fuente": "GeoNames",
            "mensaje": (
                f"No encontré '{lugar}' en GeoNames."
            )
        }

    # --------------------------------------------------------
    # Obtener propiedades del primer resultado
    # --------------------------------------------------------

    properties = (
        features[0].get(
            "properties",
            {}
        )
    )

    nombre = (
        properties.get("nombre")
        or lugar
    )

    pais = (
        properties.get("pais")
        or ""
    )

    departamento_estado = (
        properties.get(
            "departamento_estado"
        )
        or ""
    )

    ubicacion = ", ".join(
        valor
        for valor in [
            nombre,
            departamento_estado,
            pais
        ]
        if valor
    )

    # --------------------------------------------------------
    # Completar respuesta TERRI+
    # --------------------------------------------------------

    respuesta["mensaje"] = (
        f"Localicé {ubicacion} "
        "utilizando GeoNames."
    )

    respuesta["lugar"] = nombre

    respuesta["pais"] = pais

    respuesta["tema"] = "toponimia"

    respuesta["layer_id"] = (
        "geonames_lugar"
    )

    respuesta["visualizacion"] = {
        "modo": "simple",
        "campo_categoria": None,
        "campo_valor": None,
        "mostrar_leyenda": False,
        "titulo_leyenda": (
            "Lugar — GeoNames"
        )
    }

    respuesta["inteligencia"] = {
        "tipo": "fuente_externa",
        "fuente": "GeoNames",
        "mensaje": respuesta[
            "mensaje"
        ]
    }

    return respuesta

