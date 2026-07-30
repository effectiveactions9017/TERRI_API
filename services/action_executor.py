# ============================================================
# TERRI+
# Action Executor
# Ejecutor de acciones sobre el resultado operativo
# ============================================================

from copy import deepcopy
from typing import Any, Optional

from services.result_engine import obtener_resultado


# ============================================================
# TIPOS DE ACCIÓN COMPATIBLES
# ============================================================

ACCION_REUTILIZAR_RESULTADO = "reutilizar_resultado"
ACCION_REQUIERE_SQL = "requiere_sql"
ACCION_NUEVA_CONSULTA = "nueva_consulta"
ACCION_SIN_RESULTADO = "sin_resultado"


# ============================================================
# ESTADOS DE EJECUCIÓN
# ============================================================

ESTADO_EJECUTADO = "ejecutado"
ESTADO_NO_APLICA = "no_aplica"
ESTADO_ERROR = "error"


# ============================================================
# VALIDAR DECISIÓN
# ============================================================

def validar_decision(
    decision: Any
) -> dict[str, Any]:
    """
    Valida la estructura mínima de una decisión generada
    por el Action Engine.
    """

    if not isinstance(decision, dict):

        raise ValueError(
            "La decisión del Action Engine debe ser un diccionario."
        )

    accion = decision.get("accion")

    if not isinstance(accion, str) or not accion.strip():

        raise ValueError(
            "La decisión no contiene una acción válida."
        )

    return decision


# ============================================================
# CONSTRUIR RESPUESTA DE EJECUCIÓN
# ============================================================

def construir_resultado_ejecucion(
    estado: str,
    accion: str,
    ejecutada: bool,
    respuesta: Optional[dict[str, Any]] = None,
    motivo: Optional[str] = None,
    error: Optional[str] = None
) -> dict[str, Any]:
    """
    Construye la respuesta estándar del Action Executor.
    """

    return {
        "estado": estado,
        "accion": accion,
        "ejecutada": ejecutada,
        "respuesta": deepcopy(respuesta),
        "motivo": motivo,
        "error": error
    }


# ============================================================
# VALIDAR RESULTADO OPERATIVO
# ============================================================

def validar_resultado_operativo(
    resultado_guardado: Any
) -> dict[str, Any]:
    """
    Comprueba que el Result Engine contiene un resultado
    reutilizable.
    """

    if not isinstance(resultado_guardado, dict):

        raise ValueError(
            "El Result Engine no devolvió una estructura válida."
        )

    resultado = resultado_guardado.get("resultado")

    if resultado is None:

        raise ValueError(
            "No existe un resultado operativo almacenado."
        )

    tipo = resultado_guardado.get("tipo")

    if tipo not in {"tabla", "geojson"}:

        raise ValueError(
            f"El tipo de resultado '{tipo}' no puede reutilizarse."
        )

    return resultado_guardado


# ============================================================
# CONSTRUIR RESPUESTA REUTILIZADA
# ============================================================

def construir_respuesta_reutilizada(
    resultado_guardado: dict[str, Any],
    decision: dict[str, Any],
    pregunta: str
) -> dict[str, Any]:
    """
    Reconstruye la respuesta que espera el frontend utilizando
    únicamente la información almacenada en el Result Engine.
    """

    tipo = resultado_guardado.get("tipo")
    resultado = deepcopy(
        resultado_guardado.get("resultado")
    )

    memoria_original = deepcopy(
        resultado_guardado.get("memoria")
    )

    layer_id = resultado_guardado.get("layer_id")
    tabla = resultado_guardado.get("tabla")
    sql = resultado_guardado.get("sql")
    fecha = resultado_guardado.get("fecha")

    inteligencia = {
        "tipo": "resultado_reutilizado",
        "mensaje": (
            "Se reutilizó el resultado territorial anterior "
            "sin ejecutar una nueva consulta SQL."
        ),
        "layer_id": layer_id,
        "tabla": tabla,
        "accion": decision.get("accion"),
        "motivo": decision.get("motivo")
    }

    respuesta = {
        "tipo": tipo,
        "modo": (
            "mapa"
            if tipo == "geojson"
            else "datos"
        ),
        "resultado": resultado,
        "inteligencia": inteligencia,
        "seguimiento": True,
        "reutilizado": True,
        "ejecuto_sql": False,
        "pregunta": pregunta,
        "tabla": tabla,
        "layer_id": layer_id,
        "sql_origen": sql,
        "fecha_resultado_origen": fecha
    }

    if memoria_original is not None:

        respuesta["memoria"] = memoria_original

    return respuesta


# ============================================================
# REUTILIZAR RESULTADO
# ============================================================

def ejecutar_reutilizacion(
    decision: dict[str, Any],
    pregunta: str
) -> dict[str, Any]:
    """
    Recupera el último resultado operativo y lo devuelve
    directamente al frontend.
    """

    resultado_guardado = obtener_resultado()

    resultado_guardado = validar_resultado_operativo(
        resultado_guardado
    )

    respuesta = construir_respuesta_reutilizada(
        resultado_guardado=resultado_guardado,
        decision=decision,
        pregunta=pregunta
    )

    return construir_resultado_ejecucion(
        estado=ESTADO_EJECUTADO,
        accion=ACCION_REUTILIZAR_RESULTADO,
        ejecutada=True,
        respuesta=respuesta,
        motivo=(
            "El resultado fue recuperado desde el Result Engine."
        )
    )


# ============================================================
# ACCIÓN QUE REQUIERE SQL
# ============================================================

def ejecutar_requiere_sql(
    decision: dict[str, Any]
) -> dict[str, Any]:
    """
    Informa que la acción debe continuar por el flujo normal
    de planificación, generación y ejecución SQL.
    """

    return construir_resultado_ejecucion(
        estado=ESTADO_NO_APLICA,
        accion=decision.get("accion"),
        ejecutada=False,
        respuesta=None,
        motivo=(
            "La acción requiere continuar por el flujo SQL."
        )
    )


# ============================================================
# EJECUTAR ACCIÓN
# ============================================================

def ejecutar_accion(
    decision: dict[str, Any],
    pregunta: str
) -> dict[str, Any]:
    """
    Ejecuta la acción seleccionada por el Action Engine.

    En esta primera versión:

    - reutilizar_resultado:
      devuelve el resultado almacenado sin SQL.

    - nueva_consulta:
      permite continuar al flujo normal.

    - requiere_sql:
      permite continuar al flujo normal.

    - sin_resultado:
      permite continuar al flujo normal.
    """

    try:

        decision = validar_decision(decision)

        accion = decision.get("accion")

        # ====================================================
        # REUTILIZAR RESULTADO
        # ====================================================

        if accion == ACCION_REUTILIZAR_RESULTADO:

            return ejecutar_reutilizacion(
                decision=decision,
                pregunta=pregunta
            )

        # ====================================================
        # CONTINUAR POR SQL
        # ====================================================

        if accion in {
            ACCION_REQUIERE_SQL,
            ACCION_NUEVA_CONSULTA,
            ACCION_SIN_RESULTADO
        }:

            return ejecutar_requiere_sql(
                decision=decision
            )

        # ====================================================
        # ACCIÓN NO SOPORTADA
        # ====================================================

        return construir_resultado_ejecucion(
            estado=ESTADO_NO_APLICA,
            accion=accion,
            ejecutada=False,
            respuesta=None,
            motivo=(
                "La acción todavía no está implementada "
                "en el Action Executor."
            )
        )

    except Exception as error:

        return construir_resultado_ejecucion(
            estado=ESTADO_ERROR,
            accion=(
                decision.get("accion")
                if isinstance(decision, dict)
                else "desconocida"
            ),
            ejecutada=False,
            respuesta=None,
            motivo=(
                "No fue posible ejecutar la acción."
            ),
            error=str(error)
        )


# ============================================================
# DETERMINAR SI SE GENERÓ RESPUESTA
# ============================================================

def accion_genero_respuesta(
    ejecucion: Any
) -> bool:
    """
    Determina si el Action Executor produjo una respuesta
    lista para devolver al frontend.
    """

    if not isinstance(ejecucion, dict):

        return False

    return bool(
        ejecucion.get("ejecutada")
        and isinstance(
            ejecucion.get("respuesta"),
            dict
        )
    )


# ============================================================
# OBTENER RESPUESTA EJECUTADA
# ============================================================

def obtener_respuesta_ejecutada(
    ejecucion: dict[str, Any]
) -> Optional[dict[str, Any]]:
    """
    Devuelve la respuesta producida por el Action Executor.
    """

    if not accion_genero_respuesta(ejecucion):

        return None

    return deepcopy(
        ejecucion.get("respuesta")
    )


# ============================================================
# IMPRIMIR EJECUCIÓN
# ============================================================

def imprimir_ejecucion_accion(
    ejecucion: dict[str, Any]
) -> None:
    """
    Muestra en la terminal el resultado de la ejecución.
    """

    print(
        "\n"
        "=============== ACTION EXECUTOR ===============\n"
    )

    print(
        "Estado:",
        ejecucion.get("estado")
    )

    print(
        "Acción:",
        ejecucion.get("accion")
    )

    print(
        "¿Acción ejecutada?:",
        ejecucion.get("ejecutada")
    )

    print(
        "Motivo:",
        ejecucion.get("motivo")
    )

    if ejecucion.get("error"):

        print(
            "Error:",
            ejecucion.get("error")
        )

    respuesta = ejecucion.get("respuesta")

    if isinstance(respuesta, dict):

        print(
            "Tipo de respuesta:",
            respuesta.get("tipo")
        )

        print(
            "¿Resultado reutilizado?:",
            respuesta.get("reutilizado")
        )

        print(
            "¿Ejecutó SQL?:",
            respuesta.get("ejecuto_sql")
        )

        print(
            "Tabla:",
            respuesta.get("tabla")
        )

        print(
            "Layer:",
            respuesta.get("layer_id")
        )

    print(
        "\n"
        "===============================================\n"
    )