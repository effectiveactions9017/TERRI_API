# ============================================================
# TERRI+
# Action Engine
# Motor de decisiones sobre el último resultado operativo
# ============================================================

import re
from typing import Any, Optional

from services.result_engine import obtener_resultado


# ============================================================
# TIPOS DE ACCIÓN
# ============================================================

ACCION_NUEVA_CONSULTA = "nueva_consulta"

ACCION_REUTILIZAR_RESULTADO = "reutilizar_resultado"

ACCION_REQUIERE_SQL = "requiere_sql"

ACCION_SIN_RESULTADO = "sin_resultado"


# ============================================================
# NORMALIZAR TEXTO
# ============================================================

def normalizar_texto(valor: Any) -> str:
    """
    Convierte un valor en texto normalizado para análisis.
    """

    return (
        str(valor or "")
        .strip()
        .lower()
    )


# ============================================================
# DETECTAR SOLICITUD DE MAPA
# ============================================================

def solicita_mapa(pregunta: str) -> bool:
    """
    Determina si el usuario solicita visualizar el resultado
    en el mapa.
    """

    texto = normalizar_texto(pregunta)

    expresiones = [
        "muéstralo en el mapa",
        "muestralo en el mapa",
        "muéstralos en el mapa",
        "muestralos en el mapa",
        "mostrar en el mapa",
        "ver en el mapa",
        "dibújalo",
        "dibujalo",
        "dibújalos",
        "dibujalos",
        "ubícalo",
        "ubicalo",
        "ubícalos",
        "ubicalos",
        "representa en el mapa",
        "representarlos en el mapa"
    ]

    return any(
        expresion in texto
        for expresion in expresiones
    )


# ============================================================
# DETECTAR SOLICITUD DE ORDENAMIENTO
# ============================================================

def solicita_ordenamiento(pregunta: str) -> bool:
    """
    Determina si el usuario solicita ordenar el resultado.
    """

    texto = normalizar_texto(pregunta)

    expresiones = [
        "ordénalo",
        "ordenalo",
        "ordénalos",
        "ordenalos",
        "ordenar",
        "de mayor a menor",
        "de menor a mayor",
        "ascendente",
        "descendente"
    ]

    return any(
        expresion in texto
        for expresion in expresiones
    )


# ============================================================
# DETECTAR SOLICITUD DE FILTRO
# ============================================================

def solicita_filtrado(pregunta: str) -> bool:
    """
    Determina si el usuario solicita filtrar o reducir
    el conjunto de resultados.
    """

    texto = normalizar_texto(pregunta)

    expresiones = [
        "quédate solo",
        "quedate solo",
        "solo los",
        "solo las",
        "filtra",
        "filtrar",
        "excluye",
        "elimina los",
        "elimina las",
        "de esos",
        "de esas"
    ]

    return any(
        expresion in texto
        for expresion in expresiones
    )


# ============================================================
# DETECTAR SOLICITUD DE CANTIDAD
# ============================================================

def solicita_limite(pregunta: str) -> bool:
    """
    Determina si el usuario solicita limitar la cantidad
    de registros mostrados.
    """

    texto = normalizar_texto(pregunta)

    patrones = [
        r"\bprimeros?\s+\d+\b",
        r"\bprimeras?\s+\d+\b",
        r"\búltimos?\s+\d+\b",
        r"\bultimos?\s+\d+\b",
        r"\búltimas?\s+\d+\b",
        r"\bultimas?\s+\d+\b",
        r"\bsolo\s+\d+\b",
        r"\blimit[aá]?[rl]?\s+\d+\b"
    ]

    return any(
        re.search(patron, texto)
        for patron in patrones
    )


# ============================================================
# DETECTAR SOLICITUD DE EXPORTACIÓN
# ============================================================

def solicita_exportacion(pregunta: str) -> bool:
    """
    Determina si el usuario solicita exportar el resultado.
    """

    texto = normalizar_texto(pregunta)

    expresiones = [
        "exporta",
        "exportar",
        "descarga",
        "descargar",
        "genera un csv",
        "genera el csv",
        "en excel",
        "archivo csv",
        "archivo geojson"
    ]

    return any(
        expresion in texto
        for expresion in expresiones
    )


# ============================================================
# DETECTAR SOLICITUD DE RESUMEN
# ============================================================

def solicita_resumen(pregunta: str) -> bool:
    """
    Determina si el usuario solicita resumir el resultado.
    """

    texto = normalizar_texto(pregunta)

    expresiones = [
        "resúmelo",
        "resumelo",
        "resúmelos",
        "resumelos",
        "haz un resumen",
        "dame un resumen",
        "resume el resultado"
    ]

    return any(
        expresion in texto
        for expresion in expresiones
    )


# ============================================================
# DETERMINAR SI EL RESULTADO TIENE GEOMETRÍA
# ============================================================

def resultado_tiene_geometria(
    resultado_guardado: Optional[dict[str, Any]]
) -> bool:
    """
    Determina si el resultado almacenado puede representarse
    directamente en el mapa.
    """

    if not isinstance(resultado_guardado, dict):
        return False

    tipo = resultado_guardado.get("tipo")
    resultado = resultado_guardado.get("resultado")

    if tipo != "geojson":
        return False

    if not isinstance(resultado, dict):
        return False

    if resultado.get("type") != "FeatureCollection":
        return False

    features = resultado.get("features")

    return isinstance(features, list)


# ============================================================
# DETERMINAR SI EL RESULTADO ES TABULAR
# ============================================================

def resultado_es_tabular(
    resultado_guardado: Optional[dict[str, Any]]
) -> bool:
    """
    Determina si el resultado almacenado corresponde
    a una tabla reutilizable.
    """

    if not isinstance(resultado_guardado, dict):
        return False

    if resultado_guardado.get("tipo") != "tabla":
        return False

    resultado = resultado_guardado.get("resultado")

    return isinstance(resultado, list)


# ============================================================
# CONSTRUIR DECISIÓN
# ============================================================

def construir_decision(
    accion: str,
    motivo: str,
    reutilizar_resultado: bool = False,
    ejecutar_sql: bool = False,
    resultado_guardado: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    Construye una respuesta estandarizada del Action Engine.
    """

    return {
        "accion": accion,
        "motivo": motivo,
        "reutilizar_resultado": reutilizar_resultado,
        "ejecutar_sql": ejecutar_sql,
        "resultado_disponible": bool(
            resultado_guardado
            and resultado_guardado.get("resultado") is not None
        ),
        "tipo_resultado": (
            resultado_guardado.get("tipo")
            if isinstance(resultado_guardado, dict)
            else None
        ),
        "tabla": (
            resultado_guardado.get("tabla")
            if isinstance(resultado_guardado, dict)
            else None
        ),
        "layer_id": (
            resultado_guardado.get("layer_id")
            if isinstance(resultado_guardado, dict)
            else None
        )
    }


# ============================================================
# ANALIZAR ACCIÓN
# ============================================================

def analizar_accion(
    pregunta: str,
    es_seguimiento: bool = False
) -> dict[str, Any]:
    """
    Determina cómo debe atenderse la solicitud actual.

    Posibles decisiones:

    - nueva_consulta
    - reutilizar_resultado
    - requiere_sql
    - sin_resultado
    """

    resultado_guardado = obtener_resultado()

    hay_resultado = bool(
        resultado_guardado
        and resultado_guardado.get("resultado") is not None
    )

    # ========================================================
    # CONSULTA COMPLETAMENTE NUEVA
    # ========================================================

    if not es_seguimiento:

        return construir_decision(
            accion=ACCION_NUEVA_CONSULTA,
            motivo=(
                "La solicitud no fue identificada como una "
                "pregunta de seguimiento."
            ),
            reutilizar_resultado=False,
            ejecutar_sql=True,
            resultado_guardado=resultado_guardado
        )

    # ========================================================
    # SEGUIMIENTO SIN RESULTADO ANTERIOR
    # ========================================================

    if not hay_resultado:

        return construir_decision(
            accion=ACCION_SIN_RESULTADO,
            motivo=(
                "La solicitud depende de un resultado anterior, "
                "pero no existe un resultado operativo almacenado."
            ),
            reutilizar_resultado=False,
            ejecutar_sql=True,
            resultado_guardado=resultado_guardado
        )

    # ========================================================
    # MOSTRAR EN EL MAPA
    # ========================================================

    if solicita_mapa(pregunta):

        if resultado_tiene_geometria(resultado_guardado):

            return construir_decision(
                accion=ACCION_REUTILIZAR_RESULTADO,
                motivo=(
                    "El resultado anterior ya contiene geometría "
                    "y puede mostrarse directamente en el mapa."
                ),
                reutilizar_resultado=True,
                ejecutar_sql=False,
                resultado_guardado=resultado_guardado
            )

        return construir_decision(
            accion=ACCION_REQUIERE_SQL,
            motivo=(
                "El resultado anterior no contiene geometría. "
                "Se requiere una nueva consulta SQL conservando "
                "el contexto territorial anterior."
            ),
            reutilizar_resultado=False,
            ejecutar_sql=True,
            resultado_guardado=resultado_guardado
        )

    # ========================================================
    # ORDENAR RESULTADO
    # ========================================================

    if solicita_ordenamiento(pregunta):

        if (
            resultado_es_tabular(resultado_guardado)
            or resultado_tiene_geometria(resultado_guardado)
        ):

            return construir_decision(
                accion=ACCION_REUTILIZAR_RESULTADO,
                motivo=(
                    "El resultado anterior contiene registros "
                    "que pueden ordenarse localmente."
                ),
                reutilizar_resultado=True,
                ejecutar_sql=False,
                resultado_guardado=resultado_guardado
            )

    # ========================================================
    # LIMITAR RESULTADO
    # ========================================================

    if solicita_limite(pregunta):

        if (
            resultado_es_tabular(resultado_guardado)
            or resultado_tiene_geometria(resultado_guardado)
        ):

            return construir_decision(
                accion=ACCION_REUTILIZAR_RESULTADO,
                motivo=(
                    "El resultado anterior puede limitarse "
                    "sin ejecutar nuevamente la consulta SQL."
                ),
                reutilizar_resultado=True,
                ejecutar_sql=False,
                resultado_guardado=resultado_guardado
            )

    # ========================================================
    # RESUMIR RESULTADO
    # ========================================================

    if solicita_resumen(pregunta):

        return construir_decision(
            accion=ACCION_REUTILIZAR_RESULTADO,
            motivo=(
                "El resultado anterior puede resumirse "
                "directamente desde la memoria operativa."
            ),
            reutilizar_resultado=True,
            ejecutar_sql=False,
            resultado_guardado=resultado_guardado
        )

    # ========================================================
    # EXPORTAR RESULTADO
    # ========================================================

    if solicita_exportacion(pregunta):

        return construir_decision(
            accion=ACCION_REUTILIZAR_RESULTADO,
            motivo=(
                "El resultado anterior puede utilizarse "
                "como fuente para una exportación."
            ),
            reutilizar_resultado=True,
            ejecutar_sql=False,
            resultado_guardado=resultado_guardado
        )

    # ========================================================
    # FILTRAR RESULTADO
    # ========================================================

    if solicita_filtrado(pregunta):

        return construir_decision(
            accion=ACCION_REQUIERE_SQL,
            motivo=(
                "La solicitud modifica los filtros del conjunto "
                "anterior. Por seguridad y consistencia se "
                "generará una nueva consulta SQL contextualizada."
            ),
            reutilizar_resultado=False,
            ejecutar_sql=True,
            resultado_guardado=resultado_guardado
        )

    # ========================================================
    # SEGUIMIENTO NO CLASIFICADO
    # ========================================================

    return construir_decision(
        accion=ACCION_REQUIERE_SQL,
        motivo=(
            "La solicitud es un seguimiento, pero no corresponde "
            "a una transformación local reconocida. Se generará "
            "una nueva consulta SQL utilizando el contexto anterior."
        ),
        reutilizar_resultado=False,
        ejecutar_sql=True,
        resultado_guardado=resultado_guardado
    )


# ============================================================
# IMPRIMIR DECISIÓN
# ============================================================

def imprimir_decision_accion(
    decision: dict[str, Any]
) -> None:
    """
    Muestra en la terminal la decisión tomada por el Action Engine.
    """

    print(
        "\n"
        "================ ACTION ENGINE =================\n"
    )

    print(
        "Acción:",
        decision.get("accion")
    )

    print(
        "Motivo:",
        decision.get("motivo")
    )

    print(
        "¿Reutilizar resultado?:",
        decision.get("reutilizar_resultado")
    )

    print(
        "¿Ejecutar SQL?:",
        decision.get("ejecutar_sql")
    )

    print(
        "Tipo de resultado anterior:",
        decision.get("tipo_resultado")
    )

    print(
        "Tabla anterior:",
        decision.get("tabla")
    )

    print(
        "Layer anterior:",
        decision.get("layer_id")
    )

    print(
        "\n"
        "================================================\n"
    )