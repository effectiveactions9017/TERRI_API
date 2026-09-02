# ============================================================
# TERRI+
# Analysis Service
# Orquestador principal y memoria conversacional
# ============================================================

import json
import re
from typing import Any, Dict, Optional

from services.planner_service import construir_plan
from services.sql_generator import generar_sql
from services.sql_validator import validar_sql_seguro
from services.response_service import construir_respuesta
from services.response_intelligence import construir_inteligencia_respuesta

# ============================================================
# FUENTES EXTERNAS
# ============================================================

from services.external_sources.igac_service import (
    resolver_consulta_limites,
)

from services.result_engine import (
    guardar_resultado as guardar_resultado_engine,
    imprimir_resultado,
)

# ============================================================
# ACTION ENGINE
# ============================================================

from services.action_engine import (
    analizar_accion,
    imprimir_decision_accion,
)

# ============================================================
# ACTION EXECUTOR
# ============================================================

from services.action_executor import (
    ejecutar_accion,
    accion_genero_respuesta,
    obtener_respuesta_ejecutada,
    imprimir_ejecucion_accion,
)


# ============================================================
# MEMORIA CONVERSACIONAL TEMPORAL
# ============================================================

MEMORIA_CONVERSACION: Dict[str, Any] = {
    "pregunta": None,
    "pregunta_contextualizada": None,
    "plan": None,
    "sql": None,
    "respuesta": None,
    "inteligencia": None,
    "visualizacion": None,
    "tabla": None,
    "tipo": None,
}


# ============================================================
# DETECTAR TABLA UTILIZADA
# ============================================================

def detectar_tabla(sql: str) -> Optional[str]:
    """
    Detecta la tabla territorial principal utilizada
    dentro de una consulta SQL.
    """

    if not isinstance(sql, str):
        return None

    sql_normalizado = sql.lower()

    tablas = [
        "destino_economico_sesquile",
        "contribuyentes_ica_sesquile",
        "construcciones_sesquile",
        "placa_huellas_sesquile",
        "predios_sesquile",
    ]

    for tabla in tablas:
        patron = rf"\b{re.escape(tabla)}\b"

        if re.search(patron, sql_normalizado):
            return tabla

    return None


# ============================================================
# DETECTAR PREGUNTA DE SEGUIMIENTO
# ============================================================

def es_pregunta_seguimiento(pregunta: str) -> bool:
    """
    Determina si la pregunta depende del resultado anterior.
    """

    if not isinstance(pregunta, str):
        return False

    pregunta_normalizada = pregunta.strip().lower()

    if not pregunta_normalizada:
        return False

    expresiones_seguimiento = [
        r"^y\b",
        r"^ahora\b",
        r"^entonces\b",
        r"^de esos\b",
        r"^de esas\b",
        r"^entre esos\b",
        r"^entre esas\b",
        r"^el segundo\b",
        r"^el tercero\b",
        r"^el siguiente\b",
        r"^la segunda\b",
        r"^la tercera\b",
        r"^la siguiente\b",
        r"^muéstralo\b",
        r"^muestralo\b",
        r"^muéstralos\b",
        r"^muestralos\b",
        r"^dibújalo\b",
        r"^dibujalo\b",
        r"^dibújalos\b",
        r"^dibujalos\b",
        r"^ubícalo\b",
        r"^ubicalo\b",
        r"^ubícalos\b",
        r"^ubicalos\b",
        r"^solo\b",
        r"^solamente\b",
        r"^también\b",
        r"^tambien\b",
        r"^cuál de ellos\b",
        r"^cual de ellos\b",
        r"^cuál de esos\b",
        r"^cual de esos\b",
        r"^cuántos de esos\b",
        r"^cuantos de esos\b",
    ]

    for expresion in expresiones_seguimiento:
        if re.search(expresion, pregunta_normalizada):
            return True

    palabras_dependientes = [
        "ese",
        "esa",
        "esos",
        "esas",
        "ellos",
        "ellas",
        "anterior",
        "resultado anterior",
        "mismo",
        "misma",
        "segundo",
        "segunda",
        "tercero",
        "tercera",
        "siguiente",
    ]

    return any(
        palabra in pregunta_normalizada
        for palabra in palabras_dependientes
    )


# ============================================================
# CONSTRUIR PREGUNTA CONTEXTUALIZADA
# ============================================================

def construir_pregunta_contextualizada(pregunta: str) -> str:
    """
    Integra la memoria anterior cuando la pregunta actual
    es una continuación de la conversación.
    """

    pregunta_anterior = MEMORIA_CONVERSACION.get("pregunta")
    sql_anterior = MEMORIA_CONVERSACION.get("sql")
    tabla_anterior = MEMORIA_CONVERSACION.get("tabla")
    plan_anterior = MEMORIA_CONVERSACION.get("plan")

    tiene_memoria = bool(
        pregunta_anterior
        and sql_anterior
    )

    if not tiene_memoria:
        return pregunta

    if not es_pregunta_seguimiento(pregunta):
        return pregunta

    plan_anterior_texto = (
        json.dumps(
            plan_anterior,
            ensure_ascii=False,
            indent=2,
        )
        if plan_anterior
        else "No disponible"
    )

    return f"""
La siguiente solicitud es una pregunta de seguimiento y depende
del resultado territorial inmediatamente anterior.

PREGUNTA ANTERIOR:
{pregunta_anterior}

TABLA PRINCIPAL UTILIZADA ANTERIORMENTE:
{tabla_anterior or "No identificada"}

PLAN TERRITORIAL ANTERIOR:
{plan_anterior_texto}

SQL ANTERIOR:
{sql_anterior}

PREGUNTA ACTUAL:
{pregunta}

INSTRUCCIONES OBLIGATORIAS:

1. Interpreta la pregunta actual utilizando la intención, filtros,
   tabla, campos, ordenamiento y categoría de la consulta anterior.

2. Genera una nueva consulta SQL completa y válida.

3. No devuelvas nuevamente la SQL anterior sin aplicar el cambio
   solicitado por el usuario.

4. No trates el texto anterior como nombres de tablas o columnas
   nuevas.

5. Conserva la capa temática anterior, salvo que la pregunta actual
   solicite claramente cambiar de tema o relacionar otra capa.

6. Si el usuario pide "el segundo", conserva el mismo filtro y
   ordenamiento de la consulta anterior y utiliza:

   LIMIT 1 OFFSET 1

7. Si pide "el tercero", utiliza:

   LIMIT 1 OFFSET 2

8. Si pide "el siguiente" después de un resultado individual,
   interpreta que solicita la posición inmediatamente posterior
   dentro del mismo ranking.

9. Si pide mostrar, dibujar, ubicar o ver el resultado, incluye la
   geometría real con el alias exacto geom.

10. Si pide una cantidad diferente, conserva el mismo criterio
    temático y modifica LIMIT según corresponda.

11. Devuelve únicamente SQL, de acuerdo con las reglas generales
    del generador.
""".strip()


# ============================================================
# MOSTRAR PLAN TERRITORIAL
# ============================================================

def imprimir_plan_territorial(plan: dict) -> None:
    """
    Muestra en la terminal el plan territorial construido
    antes de generar la consulta SQL.
    """

    print(
        "\n"
        "================ PLAN TERRITORIAL TERRI+ ================\n"
    )

    print(
        json.dumps(
            plan,
            ensure_ascii=False,
            indent=4,
        )
    )

    print(
        "\n"
        "=========================================================\n"
    )


# ============================================================
# NORMALIZAR VISUALIZACIÓN DEL PLAN
# ============================================================

def construir_visualizacion_respuesta(
    plan: dict,
    inteligencia: Optional[dict] = None,
) -> dict:
    """
    Convierte la intención cartográfica del Planner en una
    instrucción estable para el frontend TERRI+.

    Formato esperado por el frontend:

    {
        "modo": "categorico",
        "campo_categoria": "nivel_riesgo",
        "campo_valor": None,
        "mostrar_leyenda": True,
        "titulo_leyenda": "Nivel de riesgo"
    }
    """

    visualizacion_base = {
        "modo": "simple",
        "campo_categoria": None,
        "campo_valor": None,
        "mostrar_leyenda": False,
        "titulo_leyenda": None,
    }

    if not isinstance(plan, dict):
        return visualizacion_base

    visualizacion_plan = plan.get("visualizacion")

    if not isinstance(visualizacion_plan, dict):
        visualizacion_plan = {}

    modo_original = str(
        visualizacion_plan.get("modo")
        or visualizacion_plan.get("tipo")
        or "simple"
    ).strip().lower()

    campo_categoria = (
        visualizacion_plan.get("campo_categoria")
        or visualizacion_plan.get("campoCategoria")
        or visualizacion_plan.get("campo")
    )

    campo_valor = (
        visualizacion_plan.get("campo_valor")
        or visualizacion_plan.get("campoValor")
    )

    titulo_leyenda = (
        visualizacion_plan.get("titulo_leyenda")
        or visualizacion_plan.get("tituloLeyenda")
    )

    mostrar_leyenda_valor = (
        visualizacion_plan.get("mostrar_leyenda")
    )

    if mostrar_leyenda_valor is None:
        mostrar_leyenda_valor = (
            visualizacion_plan.get("mostrarLeyenda")
        )

    mostrar_leyenda = bool(
        mostrar_leyenda_valor
        if mostrar_leyenda_valor is not None
        else campo_categoria or campo_valor
    )

    if (
        "categor" in modo_original
        or "color" in modo_original
        or campo_categoria
    ):
        modo = "categorico"

    elif (
        "gradu" in modo_original
        or "rango" in modo_original
        or (
            "valor" in modo_original
            and campo_valor
        )
    ):
        modo = "graduado"

    elif "heat" in modo_original or "calor" in modo_original:
        modo = "heatmap"

    elif "cluster" in modo_original or "agrup" in modo_original:
        modo = "cluster"

    else:
        modo = "simple"

    if not titulo_leyenda:
        campo_titulo = campo_categoria or campo_valor

        if campo_titulo:
            titulo_leyenda = (
                str(campo_titulo)
                .replace("_", " ")
                .strip()
                .title()
            )

    visualizacion = {
        "modo": modo,
        "campo_categoria": campo_categoria,
        "campo_valor": campo_valor,
        "mostrar_leyenda": mostrar_leyenda,
        "titulo_leyenda": titulo_leyenda,
    }

    # Permite que response_intelligence complete datos cartográficos
    # cuando el Planner todavía no los haya definido.
    if isinstance(inteligencia, dict):
        visualizacion_inteligencia = inteligencia.get("visualizacion")

        if isinstance(visualizacion_inteligencia, dict):
            for clave, valor in visualizacion_inteligencia.items():
                if (
                    clave not in visualizacion
                    or visualizacion.get(clave) in (None, "", False)
                ):
                    visualizacion[clave] = valor

    return visualizacion


# ============================================================
# GUARDAR MEMORIA
# ============================================================

def guardar_memoria(
    pregunta: str,
    pregunta_contextualizada: str,
    plan: dict,
    sql: str,
    respuesta: dict,
    inteligencia: Any,
) -> None:
    """
    Guarda el último estado válido de la conversación.
    """

    MEMORIA_CONVERSACION["pregunta"] = pregunta
    MEMORIA_CONVERSACION["pregunta_contextualizada"] = (
        pregunta_contextualizada
    )
    MEMORIA_CONVERSACION["plan"] = plan
    MEMORIA_CONVERSACION["sql"] = sql
    MEMORIA_CONVERSACION["respuesta"] = respuesta
    MEMORIA_CONVERSACION["inteligencia"] = inteligencia
    MEMORIA_CONVERSACION["visualizacion"] = (
        respuesta.get("visualizacion")
        if isinstance(respuesta, dict)
        else None
    )
    MEMORIA_CONVERSACION["tabla"] = detectar_tabla(sql)

    if isinstance(respuesta, dict):
        MEMORIA_CONVERSACION["tipo"] = respuesta.get("tipo")
    else:
        MEMORIA_CONVERSACION["tipo"] = None


# ============================================================
# OBTENER MEMORIA
# ============================================================

def obtener_memoria() -> dict:
    """
    Devuelve una copia superficial de la memoria conversacional.
    """

    return MEMORIA_CONVERSACION.copy()


# ============================================================
# LIMPIAR MEMORIA
# ============================================================

def limpiar_memoria() -> None:
    """
    Elimina el contexto conversacional almacenado.
    """

    MEMORIA_CONVERSACION.update({
        "pregunta": None,
        "pregunta_contextualizada": None,
        "plan": None,
        "sql": None,
        "respuesta": None,
        "inteligencia": None,
        "visualizacion": None,
        "tabla": None,
        "tipo": None,
    })


# ============================================================
# MOSTRAR RESUMEN DE MEMORIA
# ============================================================

def imprimir_resumen_memoria() -> None:
    """
    Muestra un resumen legible sin imprimir toda la respuesta
    GeoJSON en la terminal.
    """

    plan_memoria = MEMORIA_CONVERSACION.get("plan")

    tipo_consulta = (
        plan_memoria.get("tipo_consulta")
        if isinstance(plan_memoria, dict)
        else None
    )

    visualizacion = MEMORIA_CONVERSACION.get("visualizacion")

    print(
        "\n"
        "================ MEMORIA TERRI+ =================\n"
    )

    print(
        "Pregunta:",
        MEMORIA_CONVERSACION.get("pregunta"),
    )

    print(
        "Tipo de consulta:",
        tipo_consulta,
    )

    print(
        "Tabla:",
        MEMORIA_CONVERSACION.get("tabla"),
    )

    print(
        "Tipo de respuesta:",
        MEMORIA_CONVERSACION.get("tipo"),
    )

    print(
        "Visualización:",
        json.dumps(
            visualizacion,
            ensure_ascii=False,
        )
        if visualizacion
        else None,
    )

    print(
        "SQL:",
        MEMORIA_CONVERSACION.get("sql"),
    )

    print(
        "\n"
        "=================================================\n"
    )


# ============================================================
# ANALIZAR PREGUNTA
# ============================================================

def analizar_pregunta(pregunta: str) -> dict:
    """
    Orquesta el flujo principal de TERRI+:

    pregunta
    -> detección de seguimiento
    -> contextualización
    -> Action Engine
    -> Action Executor
    -> reutilización del resultado, cuando sea posible
    -> planificación territorial, cuando se requiera
    -> generación de SQL
    -> validación
    -> ejecución
    -> inteligencia
    -> visualización
    -> Result Engine
    -> memoria conversacional.
    """

    # ========================================================
    # VALIDAR PREGUNTA
    # ========================================================

    if not isinstance(pregunta, str):
        raise ValueError(
            "La pregunta debe ser una cadena de texto."
        )

    pregunta = pregunta.strip()

    if not pregunta:
        raise ValueError(
            "La pregunta no puede estar vacía."
        )

    # ========================================================
    # FUENTE EXTERNA IGAC - LÍMITES
    # ========================================================

    respuesta_igac = resolver_consulta_limites(
        pregunta
    )

    if respuesta_igac is not None:

        if not isinstance(
            respuesta_igac,
            dict
        ):
            raise ValueError(
                "El servicio IGAC no devolvió una respuesta válida."
            )

        # ----------------------------------------------------
        # CONSULTA IGAC SIN RESULTADO O AMBIGUA
        # ----------------------------------------------------

        if not respuesta_igac.get(
            "ok",
            False
        ):

            respuesta_igac["pregunta"] = pregunta
            respuesta_igac["seguimiento"] = False
            respuesta_igac["reutilizado"] = False
            respuesta_igac["ejecuto_sql"] = False

            respuesta_igac.setdefault(
                "modo",
                "datos"
            )

            respuesta_igac.setdefault(
                "inteligencia",
                {
                    "tipo": "fuente_externa",
                    "fuente": "IGAC",
                    "mensaje": respuesta_igac.get(
                        "mensaje",
                        "No fue posible resolver la consulta en el IGAC."
                    )
                }
            )

            respuesta_igac["decision_accion"] = {
                "accion": "fuente_externa_igac",
                "motivo": (
                    "La pregunta corresponde a una consulta de "
                    "límites administrativos en el servicio REST del IGAC."
                ),
                "reutilizar_resultado": False,
                "ejecutar_sql": False,
                "resultado_disponible": False,
                "tipo_resultado": respuesta_igac.get("tipo"),
                "tabla": None,
                "layer_id": None
            }

            return respuesta_igac

        # ----------------------------------------------------
        # CONSULTA IGAC CON GEOJSON
        # ----------------------------------------------------

        resultado_igac = respuesta_igac.get(
            "resultado"
        )

        if not isinstance(
            resultado_igac,
            dict
        ):
            raise ValueError(
                "El servicio IGAC no devolvió un GeoJSON válido."
            )

        if resultado_igac.get(
            "type"
        ) != "FeatureCollection":
            raise ValueError(
                "El resultado IGAC no corresponde a un FeatureCollection."
            )

        inteligencia_igac = respuesta_igac.get(
            "inteligencia"
        )

        if not isinstance(
            inteligencia_igac,
            dict
        ):
            inteligencia_igac = {
                "tipo": "fuente_externa",
                "fuente": "IGAC",
                "mensaje": (
                    "Se obtuvo información geográfica desde "
                    "el servicio REST del IGAC."
                )
            }

        visualizacion_igac = respuesta_igac.get(
            "visualizacion"
        )

        if not isinstance(
            visualizacion_igac,
            dict
        ):
            visualizacion_igac = {
                "modo": "simple",
                "campo_categoria": None,
                "campo_valor": None,
                "mostrar_leyenda": True,
                "titulo_leyenda": "Límite IGAC"
            }

        layer_id_igac = respuesta_igac.get(
            "layer_id"
        )

        plan_igac = {
            "tipo_consulta": "fuente_externa",
            "fuente": "IGAC",
            "servicio": "limites",
            "visualizacion": visualizacion_igac
        }

        sql_igac = "FUENTE_EXTERNA:IGAC"

        respuesta_igac["pregunta"] = pregunta
        respuesta_igac["seguimiento"] = False
        respuesta_igac["plan"] = plan_igac
        respuesta_igac["visualizacion"] = visualizacion_igac
        respuesta_igac["inteligencia"] = inteligencia_igac
        respuesta_igac["reutilizado"] = False
        respuesta_igac["ejecuto_sql"] = False

        respuesta_igac["decision_accion"] = {
            "accion": "fuente_externa_igac",
            "motivo": (
                "La pregunta corresponde a una consulta de "
                "límites administrativos en el servicio REST del IGAC."
            ),
            "reutilizar_resultado": False,
            "ejecutar_sql": False,
            "resultado_disponible": True,
            "tipo_resultado": "geojson",
            "tabla": None,
            "layer_id": layer_id_igac
        }

        # ----------------------------------------------------
        # GUARDAR RESULTADO OPERATIVO IGAC
        # Permite reutilizarlo en preguntas de seguimiento
        # como: "muéstralo en el mapa".
        # ----------------------------------------------------

        guardar_resultado_engine(
            tipo="geojson",
            tabla=None,
            layer_id=layer_id_igac,
            sql=sql_igac,
            resultado=resultado_igac,
            memoria={
                "fuente": "IGAC",
                "servicio": "limites",
                "municipio": respuesta_igac.get(
                    "municipio"
                ),
                "departamento": respuesta_igac.get(
                    "departamento"
                ),
                "codigo": respuesta_igac.get(
                    "codigo"
                )
            },
        )

        imprimir_resultado()

        # ----------------------------------------------------
        # GUARDAR MEMORIA CONVERSACIONAL IGAC
        # ----------------------------------------------------

        guardar_memoria(
            pregunta=pregunta,
            pregunta_contextualizada=pregunta,
            plan=plan_igac,
            sql=sql_igac,
            respuesta=respuesta_igac,
            inteligencia=inteligencia_igac,
        )

        imprimir_resumen_memoria()

        return respuesta_igac

    # ========================================================
    # CONSTRUIR CONTEXTO CONVERSACIONAL
    # ========================================================

    pregunta_contextualizada = (
        construir_pregunta_contextualizada(pregunta)
    )

    es_seguimiento = (
        pregunta_contextualizada != pregunta
    )

    # ========================================================
    # ACTION ENGINE
    # ========================================================

    decision_accion = analizar_accion(
        pregunta=pregunta,
        es_seguimiento=es_seguimiento,
    )

    imprimir_decision_accion(decision_accion)

    # ========================================================
    # ACTION EXECUTOR
    # ========================================================

    ejecucion_accion = ejecutar_accion(
        decision=decision_accion,
        pregunta=pregunta,
    )

    imprimir_ejecucion_accion(ejecucion_accion)

    # ========================================================
    # DEVOLVER RESULTADO REUTILIZADO
    # ========================================================

    if accion_genero_respuesta(ejecucion_accion):
        respuesta_reutilizada = obtener_respuesta_ejecutada(
            ejecucion_accion
        )

        if not isinstance(respuesta_reutilizada, dict):
            raise ValueError(
                "El Action Executor no devolvió una respuesta válida."
            )

        plan_anterior = MEMORIA_CONVERSACION.get("plan")
        inteligencia_reutilizada = respuesta_reutilizada.get(
            "inteligencia"
        )

        if plan_anterior is not None:
            respuesta_reutilizada["plan"] = plan_anterior

            respuesta_reutilizada["visualizacion"] = (
                construir_visualizacion_respuesta(
                    plan=plan_anterior,
                    inteligencia=inteligencia_reutilizada,
                )
            )

        elif MEMORIA_CONVERSACION.get("visualizacion"):
            respuesta_reutilizada["visualizacion"] = (
                MEMORIA_CONVERSACION.get("visualizacion")
            )

        respuesta_reutilizada["seguimiento"] = es_seguimiento
        respuesta_reutilizada["decision_accion"] = decision_accion
        respuesta_reutilizada["reutilizado"] = True

        if "ejecuto_sql" not in respuesta_reutilizada:
            respuesta_reutilizada["ejecuto_sql"] = False

        # ====================================================
        # ACTUALIZAR MEMORIA SIN REEMPLAZAR SQL NI TABLA
        # ====================================================

        MEMORIA_CONVERSACION["pregunta"] = pregunta
        MEMORIA_CONVERSACION["pregunta_contextualizada"] = (
            pregunta_contextualizada
        )
        MEMORIA_CONVERSACION["respuesta"] = respuesta_reutilizada
        MEMORIA_CONVERSACION["inteligencia"] = (
            inteligencia_reutilizada
        )
        MEMORIA_CONVERSACION["visualizacion"] = (
            respuesta_reutilizada.get("visualizacion")
        )
        MEMORIA_CONVERSACION["tipo"] = (
            respuesta_reutilizada.get("tipo")
        )

        print(
            "\n"
            "=========== RESULTADO REUTILIZADO TERRI+ ===========\n"
        )

        print(
            "Pregunta:",
            pregunta,
        )

        print(
            "Tipo de respuesta:",
            respuesta_reutilizada.get("tipo"),
        )

        print(
            "Tabla:",
            respuesta_reutilizada.get("tabla")
            or MEMORIA_CONVERSACION.get("tabla"),
        )

        print(
            "Layer:",
            respuesta_reutilizada.get("layer_id"),
        )

        print(
            "Visualización:",
            json.dumps(
                respuesta_reutilizada.get("visualizacion"),
                ensure_ascii=False,
            ),
        )

        print(
            "¿Ejecutó SQL?:",
            respuesta_reutilizada.get("ejecuto_sql"),
        )

        print(
            "\n"
            "====================================================\n"
        )

        imprimir_resumen_memoria()

        return respuesta_reutilizada

    # ========================================================
    # ANÁLISIS CONVERSACIONAL
    # ========================================================

    print(
        "\n"
        "=========== ANÁLISIS CONVERSACIONAL TERRI+ ===========\n"
    )

    print(
        "Pregunta original:",
        pregunta,
    )

    print(
        "¿Es seguimiento?:",
        es_seguimiento,
    )

    if es_seguimiento:
        print(
            "Tabla anterior:",
            MEMORIA_CONVERSACION.get("tabla"),
        )

    print(
        "\n"
        "=======================================================\n"
    )

    # ========================================================
    # CONSTRUIR PLAN TERRITORIAL
    # ========================================================

    plan = construir_plan(pregunta)

    if not isinstance(plan, dict):
        raise ValueError(
            "El Planner no devolvió un plan territorial válido."
        )

    imprimir_plan_territorial(plan)

    # ========================================================
    # GENERAR SQL
    # ========================================================

    sql = generar_sql(
        pregunta=pregunta_contextualizada,
        plan=plan,
    )

    if not isinstance(sql, str) or not sql.strip():
        raise ValueError(
            "El generador SQL no devolvió una consulta válida."
        )

    sql = sql.strip()

    print(
        "\n"
        "================ SQL GENERADO TERRI+ ================\n"
    )

    print(sql)

    print(
        "\n"
        "=====================================================\n"
    )

    # ========================================================
    # VALIDAR SQL
    # ========================================================

    validar_sql_seguro(sql)

    # ========================================================
    # EJECUTAR Y CONSTRUIR RESPUESTA
    # ========================================================

    respuesta = construir_respuesta(sql)

    if not isinstance(respuesta, dict):
        raise ValueError(
            "Response Service no devolvió una respuesta válida."
        )

    # ========================================================
    # CONSTRUIR INTELIGENCIA DE RESPUESTA
    # ========================================================

    inteligencia = construir_inteligencia_respuesta(
        respuesta=respuesta,
        pregunta=pregunta,
        plan=plan,
    )

    if not isinstance(inteligencia, dict):
        inteligencia = {}

    # ========================================================
    # CONSTRUIR INSTRUCCIÓN DE VISUALIZACIÓN
    # ========================================================

    visualizacion = construir_visualizacion_respuesta(
        plan=plan,
        inteligencia=inteligencia,
    )

    # ========================================================
    # COMPLETAR RESPUESTA FINAL
    # ========================================================

    respuesta["inteligencia"] = inteligencia
    respuesta["seguimiento"] = es_seguimiento
    respuesta["plan"] = plan
    respuesta["visualizacion"] = visualizacion
    respuesta["decision_accion"] = decision_accion
    respuesta["reutilizado"] = False
    respuesta["ejecuto_sql"] = True

    # Facilita el acceso directo desde el frontend y otros
    # componentes sin tener que inspeccionar inteligencia.
    if inteligencia.get("layer_id") is not None:
        respuesta["layer_id"] = inteligencia.get("layer_id")

    tabla_detectada = detectar_tabla(sql)

    if tabla_detectada is not None:
        respuesta["tabla"] = tabla_detectada

    print(
        "\n"
        "============== VISUALIZACIÓN TERRI+ ==============\n"
    )

    print(
        json.dumps(
            visualizacion,
            ensure_ascii=False,
            indent=4,
        )
    )

    print(
        "\n"
        "==================================================\n"
    )

    # ========================================================
    # GUARDAR RESULTADO OPERATIVO
    # ========================================================

    guardar_resultado_engine(
        tipo=respuesta.get("tipo"),
        tabla=tabla_detectada,
        layer_id=inteligencia.get("layer_id"),
        sql=sql,
        resultado=respuesta.get("resultado"),
        memoria=respuesta.get("memoria"),
    )

    imprimir_resultado()

    # ========================================================
    # GUARDAR MEMORIA
    # ========================================================

    guardar_memoria(
        pregunta=pregunta,
        pregunta_contextualizada=pregunta_contextualizada,
        plan=plan,
        sql=sql,
        respuesta=respuesta,
        inteligencia=inteligencia,
    )

    imprimir_resumen_memoria()

    return respuesta
