# ============================================================
# TERRI+ CORE
# Inteligencia dinámica de respuestas territoriales
# ============================================================

from typing import Any, Optional

from services.registry_manager import (
    obtener_capas_unificadas_disponibles,
    obtener_capa_unificada,
)


# ============================================================
# Punto principal de entrada
# ============================================================

def construir_inteligencia_respuesta(
    respuesta: dict[str, Any],
    pregunta: str = "",
    plan: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Interpreta una respuesta ya ejecutada y construye
    un mensaje útil para el usuario.

    No ejecuta SQL y no modifica el resultado original.
    """

    if not respuesta:
        return {
            "mensaje": (
                "No pude construir una respuesta con "
                "la información disponible."
            ),
            "sugerencias": [],
            "tipo_respuesta": "error",
            "layer_id": None,
        }

    modo = respuesta.get("modo")

    if modo == "mapa":
        return inteligencia_mapa(
            respuesta=respuesta,
            pregunta=pregunta,
            plan=plan,
        )

    if modo == "datos":
        return inteligencia_tabla(
            respuesta=respuesta,
            pregunta=pregunta,
            plan=plan,
        )

    return {
        "mensaje": "La consulta fue procesada correctamente.",
        "sugerencias": [],
        "tipo_respuesta": "generica",
        "layer_id": None,
    }

# ============================================================
# Interpretación de resultados espaciales
# ============================================================

def inteligencia_mapa(
    respuesta: dict[str, Any],
    pregunta: str = "",
    plan: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Interpreta respuestas espaciales representadas como GeoJSON.
    """

    total = int(
        respuesta.get("total_features", 0) or 0
    )

    geojson = respuesta.get("resultado", {}) or {}
    features = geojson.get("features", []) or []

    sql = respuesta.get("sql", "")
    layer_id = detectar_capa_desde_sql(sql)

    if total == 0 or not features:
        return {
            "mensaje": (
                "No encontré entidades espaciales que "
                "cumplan con la consulta."
            ),
            "sugerencias": [
                "Intenta ampliar el criterio de búsqueda.",
                "Prueba con otro atributo o categoría.",
                "Solicita un resumen general de la capa.",
            ],
            "tipo_respuesta": "mapa_vacio",
            "layer_id": layer_id,
        }

    propiedades = [
        feature.get("properties", {}) or {}
        for feature in features
    ]

    tipo_entidad = detectar_tipo_entidad(
        propiedades=propiedades,
        layer_id=layer_id,
    )

    if total == 1:
        mensaje = construir_mensaje_mapa_unico(
            propiedades=propiedades[0],
            tipo_entidad=tipo_entidad,
            layer_id=layer_id,
        )

        tipo_respuesta = "mapa_individual"

    else:
        mensaje = construir_mensaje_mapa_multiple(
            propiedades=propiedades,
            total=total,
            tipo_entidad=tipo_entidad,
            layer_id=layer_id,
            plan=plan,
        )

        tipo_respuesta = "mapa_multiple"

    return {
        "mensaje": mensaje,
        "sugerencias": sugerencias_mapa(
            tipo_entidad=tipo_entidad,
            layer_id=layer_id,
        ),
        "tipo_respuesta": tipo_respuesta,
        "layer_id": layer_id,
    }


# ============================================================
# Interpretación de resultados tabulares
# ============================================================

def inteligencia_tabla(
    respuesta: dict[str, Any],
    pregunta: str = "",
    plan: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Interpreta conteos, agregados, agrupaciones y listados.

    La estructura real del SQL y del resultado tiene prioridad
    sobre la clasificación preliminar enviada por el Planner.
    """

    registros = respuesta.get("resultado", []) or []

    total_registros = int(
        respuesta.get(
            "total_registros",
            len(registros),
        ) or 0
    )

    sql = respuesta.get("sql", "") or ""
    sql_normalizado = sql.lower()

    layer_id = detectar_capa_desde_sql(sql)

    if total_registros == 0 or not registros:
        return {
            "mensaje": "La consulta no devolvió resultados.",
            "sugerencias": [
                "Intenta ampliar el criterio de búsqueda.",
                "Prueba con otra categoría.",
                "Solicita un resumen general de la capa.",
            ],
            "tipo_respuesta": "tabla_vacia",
            "layer_id": layer_id,
        }

    # ========================================================
    # CLASIFICACIÓN BASADA EN LA ESTRUCTURA REAL
    # ========================================================

    tipo_detectado = clasificar_resultado_tabular(
        registros=registros,
        pregunta=pregunta,
        sql=sql,
    )

    tipo_plan = obtener_tipo_resultado_desde_plan(plan)

    tiene_group_by = "group by" in sql_normalizado

    tiene_funcion_agregada = any(
        funcion in sql_normalizado
        for funcion in [
            "count(",
            "sum(",
            "avg(",
            "min(",
            "max(",
        ]
    )

    campo_numerico_agregado = (
        detectar_campo_numerico_agregado(registros)
    )

    # Una consulta con GROUP BY y un campo agregado debe
    # interpretarse siempre como agrupación, aunque el Planner
    # haya indicado listado.
    if (
        tiene_group_by
        and len(registros) >= 1
        and (
            tiene_funcion_agregada
            or campo_numerico_agregado
        )
    ):
        tipo_resultado = "agrupacion"

    # Para resultados de una sola fila y una sola columna,
    # respetar conteos y agregados detectados realmente.
    elif tipo_detectado in {
        "conteo",
        "agregado",
    }:
        tipo_resultado = tipo_detectado

    # Para múltiples filas con campos agregados, utilizar
    # agrupación aunque GROUP BY no sea visible, por ejemplo
    # cuando la consulta proviene de una CTE.
    elif (
        len(registros) > 1
        and campo_numerico_agregado
    ):
        tipo_resultado = "agrupacion"

    # El Planner se utiliza cuando su clasificación coincide
    # razonablemente con la estructura del resultado.
    elif tipo_plan:
        tipo_resultado = tipo_plan

    else:
        tipo_resultado = tipo_detectado

    # ========================================================
    # CONSTRUIR MENSAJE SEGÚN EL TIPO REAL
    # ========================================================

    if tipo_resultado == "conteo":
        mensaje = construir_respuesta_conteo(
            registro=registros[0],
            pregunta=pregunta,
            layer_id=layer_id,
        )

    elif tipo_resultado == "agregado":
        mensaje = construir_respuesta_agregada(
            registro=registros[0],
            pregunta=pregunta,
            layer_id=layer_id,
        )

    elif tipo_resultado == "agrupacion":
        mensaje = construir_respuesta_agrupada(
            registros=registros,
            pregunta=pregunta,
            layer_id=layer_id,
        )

    elif tipo_resultado == "registro_unico":
        mensaje = construir_respuesta_registro_unico(
            registro=registros[0],
            layer_id=layer_id,
        )

    else:
        mensaje = construir_respuesta_listado(
            registros=registros,
            total=total_registros,
            layer_id=layer_id,
        )

    return {
        "mensaje": mensaje,
        "sugerencias": sugerencias_tabla(
            tipo_resultado=tipo_resultado,
            layer_id=layer_id,
        ),
        "tipo_respuesta": tipo_resultado,
        "layer_id": layer_id,
    }
# ============================================================
# OBTENER TIPO DE RESULTADO DESDE EL PLAN
# ============================================================

def obtener_tipo_resultado_desde_plan(
    plan: Optional[dict[str, Any]],
) -> Optional[str]:
    """
    Obtiene el tipo de respuesta tabular a partir del plan territorial.

    Si el plan no contiene un tipo compatible, devuelve None para
    permitir que se utilice la clasificación basada en el SQL
    y en la estructura real de los resultados.
    """

    if not isinstance(plan, dict):
        return None

    tipo_consulta = str(
        plan.get("tipo_consulta", "")
    ).strip().lower()

    equivalencias = {
        "conteo": "conteo",
        "agregado": "agregado",
        "agrupacion": "agrupacion",
        "agrupación": "agrupacion",
        "listado": "listado",
        "registro_unico": "registro_unico",
        "registro único": "registro_unico",
        "detalle": "registro_unico",
    }

    return equivalencias.get(tipo_consulta)

# ============================================================
# Clasificación del resultado tabular
# ============================================================

def clasificar_resultado_tabular(
    registros: list[dict[str, Any]],
    pregunta: str = "",
    sql: str = "",
) -> str:
    """
    Determina la naturaleza del resultado tabular.
    """

    if not registros:
        return "vacio"

    primer_registro = registros[0]
    campos = list(primer_registro.keys())

    if len(registros) == 1 and len(campos) == 1:

        campo = campos[0].lower()

        if es_campo_conteo(campo):
            return "conteo"

        if es_campo_agregado(campo):
            return "agregado"

    if (
        len(registros) > 1
        and detectar_campo_numerico_agregado(registros)
    ):
        return "agrupacion"

    if len(registros) == 1:
        return "registro_unico"

    return "listado"


def es_campo_conteo(campo: str) -> bool:
    """
    Detecta alias frecuentes de conteos.
    """

    terminos = [
        "count",
        "conteo",
        "cantidad",
        "total",
        "numero",
        "número",
    ]

    return any(
        termino in campo
        for termino in terminos
    )


def es_campo_agregado(campo: str) -> bool:
    """
    Detecta alias asociados con operaciones estadísticas.
    """

    terminos = [
        "promedio",
        "media",
        "avg",
        "suma",
        "sum",
        "maximo",
        "máximo",
        "minimo",
        "mínimo",
        "porcentaje",
        "total_avaluo",
        "total_area",
        "valor_acumulado",
    ]

    return any(
        termino in campo
        for termino in terminos
    )


def detectar_campo_numerico_agregado(
    registros: list[dict[str, Any]],
) -> Optional[str]:
    """
    Detecta el campo numérico principal de una agrupación.
    """

    if not registros:
        return None

    candidatos = [
        "cantidad",
        "conteo",
        "total",
        "numero",
        "número",
        "porcentaje",
        "promedio",
        "suma",
    ]

    for campo in registros[0].keys():

        campo_normalizado = campo.lower()

        if any(
            candidato in campo_normalizado
            for candidato in candidatos
        ):
            return campo

    return None


# ============================================================
# Respuestas de conteo
# ============================================================

def construir_respuesta_conteo(
    registro: dict[str, Any],
    pregunta: str,
    layer_id: Optional[str],
) -> str:
    """
    Construye una respuesta natural para un conteo.
    """

    _, valor = next(iter(registro.items()))

    numero = convertir_numero(valor)

    if numero is None:
        return (
            f"El resultado de la consulta es "
            f"<b>{valor}</b>."
        )

    numero_formateado = formatear_numero(numero)
    pregunta_normalizada = pregunta.lower()

    if layer_id == "predios":
        return (
            f"En Sesquilé hay "
            f"<b>{numero_formateado}</b> "
            f"{obtener_nombre_entidad(layer_id, numero)} "
            f"registrados en la base de datos catastral."
        )

    if layer_id == "construcciones":
        return (
            f"Se encontraron "
            f"<b>{numero_formateado}</b> "
            f"{obtener_nombre_entidad(layer_id, numero)} "
            f"registradas en la capa de construcciones."
        )

    if layer_id == "contribuyentes_ica":

        if (
            "persona natural" in pregunta_normalizada
            or "personas naturales" in pregunta_normalizada
        ):
            return (
                f"En Sesquilé hay "
                f"<b>{numero_formateado}</b> "
                f"contribuyentes ICA registrados como "
                f"personas naturales."
            )

        if (
            "persona jurídica" in pregunta_normalizada
            or "persona juridica" in pregunta_normalizada
            or "personas jurídicas" in pregunta_normalizada
            or "personas juridicas" in pregunta_normalizada
        ):
            return (
                f"En Sesquilé hay "
                f"<b>{numero_formateado}</b> "
                f"contribuyentes ICA registrados como "
                f"personas jurídicas."
            )

        if "activo" in pregunta_normalizada:
            return (
                f"Se encontraron "
                f"<b>{numero_formateado}</b> "
                f"contribuyentes ICA activos."
            )

        return (
            f"En Sesquilé hay "
            f"<b>{numero_formateado}</b> "
            f"contribuyentes ICA registrados."
        )

    entidad = obtener_nombre_entidad(
        layer_id=layer_id,
        cantidad=numero,
    )

    if "cuánt" in pregunta_normalizada or \
       "cuant" in pregunta_normalizada:

        return (
            f"Se encontraron "
            f"<b>{numero_formateado}</b> "
            f"{entidad}."
        )

    return (
        f"El total identificado es de "
        f"<b>{numero_formateado}</b> "
        f"{entidad}."
    )


# ============================================================
# Respuestas agregadas
# ============================================================

def construir_respuesta_agregada(
    registro: dict[str, Any],
    pregunta: str,
    layer_id: Optional[str],
) -> str:
    """
    Interpreta un único valor estadístico.
    """

    campo, valor = next(iter(registro.items()))
    numero = convertir_numero(valor)

    nombre_campo = humanizar_campo(campo)

    if numero is None:
        return (
            f"El resultado para "
            f"<b>{nombre_campo}</b> es "
            f"<b>{formatear_valor_generico(valor)}</b>."
        )

    tipo_formato = detectar_formato_valor(
        campo=campo,
        pregunta=pregunta,
        layer_id=layer_id,
    )

    valor_formateado = formatear_valor(
        numero,
        tipo_formato,
    )

    campo_normalizado = campo.lower()
    pregunta_normalizada = pregunta.lower()

    if (
        "promedio" in campo_normalizado
        or "avg" in campo_normalizado
        or "promedio" in pregunta_normalizada
    ):
        return (
            f"El promedio calculado es de "
            f"<b>{valor_formateado}</b>."
        )

    if (
        "suma" in campo_normalizado
        or "sum" in campo_normalizado
        or "acumulado" in campo_normalizado
    ):
        return (
            f"El valor acumulado es de "
            f"<b>{valor_formateado}</b>."
        )

    if (
        "max" in campo_normalizado
        or "mayor" in pregunta_normalizada
        or "máximo" in pregunta_normalizada
        or "maximo" in pregunta_normalizada
    ):
        return (
            f"El valor máximo identificado es "
            f"<b>{valor_formateado}</b>."
        )

    if (
        "min" in campo_normalizado
        or "menor" in pregunta_normalizada
        or "mínimo" in pregunta_normalizada
        or "minimo" in pregunta_normalizada
    ):
        return (
            f"El valor mínimo identificado es "
            f"<b>{valor_formateado}</b>."
        )

    return (
        f"El resultado de "
        f"<b>{nombre_campo}</b> es "
        f"<b>{valor_formateado}</b>."
    )


# ============================================================
# Respuestas agrupadas
# ============================================================

def construir_respuesta_agrupada(
    registros: list[dict[str, Any]],
    pregunta: str,
    layer_id: Optional[str],
) -> str:
    """
    Resume resultados producidos por GROUP BY.
    """

    if not registros:
        return "No se encontraron resultados agrupados."

    campo_cantidad = detectar_campo_numerico_agregado(
        registros
    )

    if not campo_cantidad:
        return construir_respuesta_listado(
            registros=registros,
            total=len(registros),
            layer_id=layer_id,
        )

    campos_categoria = [
        campo
        for campo in registros[0].keys()
        if campo != campo_cantidad
    ]

    campo_categoria = (
        campos_categoria[0]
        if campos_categoria
        else None
    )

    if not campo_categoria:
        return construir_respuesta_listado(
            registros=registros,
            total=len(registros),
            layer_id=layer_id,
        )

    registros_ordenados = sorted(
        registros,
        key=lambda item: (
            convertir_numero(
                item.get(campo_cantidad)
            ) or 0
        ),
        reverse=True,
    )

    principal = registros_ordenados[0]

    categoria_principal = principal.get(
        campo_categoria,
        "Sin categoría",
    )

    cantidad_principal = principal.get(
        campo_cantidad,
        0,
    )

    detalles: list[str] = []

    for registro in registros_ordenados[:5]:

        categoria = registro.get(
            campo_categoria,
            "Sin categoría",
        )

        cantidad = registro.get(
            campo_cantidad,
            0,
        )

        detalles.append(
            f"{categoria}: "
            f"{formatear_numero(cantidad)}"
        )

    entidad = obtener_nombre_entidad(
        layer_id=layer_id,
        cantidad=2,
    )

    return (
        f"Se identificaron "
        f"<b>{len(registros)}</b> categorías de "
        f"{entidad}. "
        f"La categoría con mayor participación es "
        f"<b>{categoria_principal}</b>, con "
        f"<b>{formatear_numero(cantidad_principal)}</b> "
        f"registros."
        f"<br><br><b>Principales resultados:</b> "
        f"{'; '.join(detalles)}."
    )


# ============================================================
# Respuestas de registros y listados
# ============================================================

def construir_respuesta_registro_unico(
    registro: dict[str, Any],
    layer_id: Optional[str],
) -> str:
    """
    Construye una ficha legible para un único registro.
    """

    tipo_entidad = detectar_tipo_entidad(
        propiedades=[registro],
        layer_id=layer_id,
    )

    if tipo_entidad == "predio":
        return construir_ficha_predio(registro)

    if tipo_entidad == "construccion":
        return construir_ficha_construccion(registro)

    if tipo_entidad == "contribuyente_ica":
        return construir_ficha_contribuyente_ica(
            registro
        )

    return construir_ficha_generica(registro)


def construir_respuesta_listado(
    registros: list[dict[str, Any]],
    total: int,
    layer_id: Optional[str],
) -> str:
    """
    Resume un listado tabular.
    """

    if not registros:
        return "No se encontraron registros."

    tipo_entidad = detectar_tipo_entidad(
        propiedades=registros,
        layer_id=layer_id,
    )

    nombre_entidad = obtener_nombre_entidad(
        layer_id=layer_id,
        cantidad=total,
    )

    mensaje = (
        f"Se encontraron <b>{formatear_numero(total)}</b> "
        f"{nombre_entidad}."
    )

    if tipo_entidad == "predio":
        return (
            f"{mensaje}"
            f"<br><br><b>Primer resultado:</b><br>"
            f"{construir_ficha_predio(registros[0])}"
        )

    if tipo_entidad == "construccion":
        return (
            f"{mensaje}"
            f"<br><br><b>Primera construcción:</b><br>"
            f"{construir_ficha_construccion(registros[0])}"
        )

    if tipo_entidad == "contribuyente_ica":
        return (
            f"{mensaje}"
            f"<br><br><b>Primer contribuyente:</b><br>"
            f"{construir_ficha_contribuyente_ica(registros[0])}"
        )

    return (
        f"{mensaje}"
        f"<br><br><b>Primer resultado:</b><br>"
        f"{construir_ficha_generica(registros[0])}"
    )


# ============================================================
# Mensajes para mapas
# ============================================================

def construir_mensaje_mapa_unico(
    propiedades: dict[str, Any],
    tipo_entidad: str,
    layer_id: Optional[str],
) -> str:
    """
    Construye un mensaje para un único elemento espacial.
    """

    if tipo_entidad == "predio":
        return (
            "Encontré un predio que cumple con la consulta."
            "<br><br>"
            f"{construir_ficha_predio(propiedades)}"
            "<br>Ya fue resaltado en el mapa activo."
        )

    if tipo_entidad == "construccion":
        return (
            "Encontré una construcción que cumple "
            "con la consulta."
            "<br><br>"
            f"{construir_ficha_construccion(propiedades)}"
            "<br>Ya fue resaltada en el mapa activo."
        )

    if tipo_entidad == "contribuyente_ica":
        return (
            "Encontré un contribuyente ICA que cumple "
            "con la consulta."
            "<br><br>"
            f"{construir_ficha_contribuyente_ica(propiedades)}"
            "<br>Ya fue ubicado en el mapa activo."
        )

    nombre = obtener_nombre_capa(layer_id)

    return (
        f"Encontré un elemento de la capa "
        f"<b>{nombre}</b> que cumple con la consulta "
        f"y ya fue enviado al mapa activo."
        f"<br><br>{construir_ficha_generica(propiedades)}"
    )


def construir_mensaje_mapa_multiple(
    propiedades: list[dict[str, Any]],
    total: int,
    tipo_entidad: str,
    layer_id: Optional[str],
    plan: Optional[dict[str, Any]] = None,
) -> str:
    """
    Construye un mensaje para múltiples elementos espaciales.
    """

    if tipo_entidad == "predio":
        return construir_resumen_mapa_predios(
            propiedades=propiedades,
            total=total,
            plan=plan,
        )

    if tipo_entidad == "construccion":
        return construir_resumen_mapa_construcciones(
            propiedades=propiedades,
            total=total,
        )

    if tipo_entidad == "contribuyente_ica":
        return construir_resumen_mapa_contribuyentes(
            propiedades=propiedades,
            total=total,
        )

    nombre = obtener_nombre_capa(layer_id)

    return (
        f"Se identificaron "
        f"<b>{formatear_numero(total)}</b> elementos de "
        f"la capa <b>{nombre}</b> y ya fueron enviados "
        f"al mapa."
    )


# ============================================================
# Categoría dinámica para mapas
# ============================================================

def normalizar_nombre_campo(campo: Any) -> str:
    """
    Normaliza un nombre de campo para comparaciones tolerantes
    a mayúsculas, espacios, guiones y tildes.
    """

    import unicodedata

    texto = str(campo or "").strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    return "".join(
        caracter
        for caracter in texto
        if caracter.isalnum()
    )


def resolver_campo_propiedades(
    propiedades: list[dict[str, Any]],
    campo_solicitado: Any,
) -> Optional[str]:
    """
    Resuelve el nombre real de una propiedad GeoJSON a partir
    del nombre entregado por el Planner.

    Primero intenta coincidencia exacta y luego una coincidencia
    normalizada, para soportar variantes como:

    - nivel_riesgo
    - NIVEL_RIESGO
    - Nivel de riesgo
    """

    if not propiedades or not campo_solicitado:
        return None

    campo_texto = str(campo_solicitado).strip()

    if not campo_texto:
        return None

    campos_disponibles: list[str] = []
    campos_vistos: set[str] = set()

    for registro in propiedades:
        for campo in registro.keys():
            campo_real = str(campo)

            if campo_real not in campos_vistos:
                campos_vistos.add(campo_real)
                campos_disponibles.append(campo_real)

    if campo_texto in campos_vistos:
        return campo_texto

    campo_normalizado = normalizar_nombre_campo(campo_texto)

    for campo_real in campos_disponibles:
        if normalizar_nombre_campo(campo_real) == campo_normalizado:
            return campo_real

    return None


def obtener_categoria_visualizacion(
    plan: Optional[dict[str, Any]],
    propiedades: list[dict[str, Any]],
) -> tuple[Optional[str], Optional[str]]:
    """
    Obtiene del plan el campo categórico y el título de leyenda,
    y resuelve el nombre real del atributo presente en el GeoJSON.
    """

    if not isinstance(plan, dict):
        return None, None

    visualizacion = plan.get("visualizacion")

    if not isinstance(visualizacion, dict):
        return None, None

    campo_solicitado = (
        visualizacion.get("campo_categoria")
        or visualizacion.get("campoCategoria")
        or visualizacion.get("campo")
    )

    if not campo_solicitado:
        return None, None

    campo_real = resolver_campo_propiedades(
        propiedades=propiedades,
        campo_solicitado=campo_solicitado,
    )

    if not campo_real:
        return None, None

    titulo = (
        visualizacion.get("titulo_leyenda")
        or visualizacion.get("tituloLeyenda")
        or humanizar_campo(str(campo_solicitado))
    )

    return campo_real, str(titulo).strip()


# ============================================================
# Resúmenes espaciales específicos
# ============================================================

def construir_resumen_mapa_predios(
    propiedades: list[dict[str, Any]],
    total: int,
    plan: Optional[dict[str, Any]] = None,
) -> str:
    """
    Resume múltiples predios.

    Cuando el Planner solicita una visualización categórica,
    utiliza el mismo campo y el mismo título de la leyenda para
    construir la distribución textual del chat.

    Si el plan no define una categoría válida, conserva como
    respaldo la distribución por destino.
    """

    campo_categoria, titulo_categoria = (
        obtener_categoria_visualizacion(
            plan=plan,
            propiedades=propiedades,
        )
    )

    conteo_categoria: dict[str, int] = {}

    if campo_categoria:
        conteo_categoria = contar_valores(
            propiedades,
            [campo_categoria],
        )

    # Compatibilidad con consultas prediales simples que no
    # solicitan expresamente una visualización categórica.
    if not conteo_categoria:
        campo_categoria = resolver_campo_propiedades(
            propiedades=propiedades,
            campo_solicitado="destino",
        )

        if campo_categoria:
            conteo_categoria = contar_valores(
                propiedades,
                [campo_categoria],
            )
            titulo_categoria = "Destino"

    area_promedio = promedio(
        propiedades,
        [
            "area_terreno",
            "AREA DE TERRENO",
            "Shape_Area",
        ],
    )

    avaluo_promedio = promedio(
        propiedades,
        [
            "avaluo_2026",
            "AVALUO 2026",
            "AVALUO_2026",
        ],
    )

    mensaje = (
        f"Se identificaron "
        f"<b>{formatear_numero(total)}</b> predios "
        f"que cumplen con la consulta y ya fueron "
        f"representados en el mapa."
    )

    if conteo_categoria:
        distribucion = ", ".join(
            f"{categoria}: {formatear_numero(cantidad)}"
            for categoria, cantidad
            in list(conteo_categoria.items())[:5]
        )

        titulo_visible = (
            titulo_categoria
            or humanizar_campo(campo_categoria or "categoría")
        )

        mensaje += (
            f"<br><br><b>Distribución por "
            f"{titulo_visible.lower()}:</b> "
            f"{distribucion}."
        )

    if area_promedio is not None:
        mensaje += (
            f"<br><b>Área promedio:</b> "
            f"{formatear_numero(area_promedio)} m²."
        )

    if avaluo_promedio is not None:
        mensaje += (
            f"<br><b>Avalúo promedio:</b> "
            f"${formatear_numero(avaluo_promedio)}."
        )

    return mensaje


def construir_resumen_mapa_construcciones(
    propiedades: list[dict[str, Any]],
    total: int,
) -> str:
    """
    Resume múltiples construcciones.
    """

    altura_promedio = promedio(
        propiedades,
        ["altura_metros", "altura_m"],
    )

    mensaje = (
        f"Se identificaron "
        f"<b>{formatear_numero(total)}</b> "
        f"construcciones y ya fueron representadas "
        f"en el mapa."
    )

    if altura_promedio is not None:
        mensaje += (
            f"<br><b>Altura promedio:</b> "
            f"{formatear_numero(altura_promedio)} m."
        )

    return mensaje


def construir_resumen_mapa_contribuyentes(
    propiedades: list[dict[str, Any]],
    total: int,
) -> str:
    """
    Resume múltiples contribuyentes ICA.
    """

    tipos = contar_valores(
        propiedades,
        ["tipo_contribuyente"],
    )

    estados = contar_valores_normalizados(
        propiedades,
        ["estado"],
    )

    mensaje = (
        f"Se identificaron "
        f"<b>{formatear_numero(total)}</b> "
        f"contribuyentes ICA y ya fueron ubicados "
        f"en el mapa."
    )

    if tipos:
        distribucion = ", ".join(
            f"{categoria}: {cantidad}"
            for categoria, cantidad
            in list(tipos.items())[:5]
        )

        mensaje += (
            f"<br><br><b>Tipo de contribuyente:</b> "
            f"{distribucion}."
        )

    if estados:
        distribucion_estado = ", ".join(
            f"{estado}: {cantidad}"
            for estado, cantidad
            in list(estados.items())[:5]
        )

        mensaje += (
            f"<br><b>Estado:</b> "
            f"{distribucion_estado}."
        )

    return mensaje


# ============================================================
# Fichas de entidades
# ============================================================

def construir_ficha_predio(
    propiedades: dict[str, Any],
) -> str:
    """
    Construye una ficha resumida de un predio.
    """

    codigo = obtener(
        propiedades,
        [
            "codigo",
            "numero_predial",
            "CODIGO",
            "NUMERO_PREDIAL",
        ],
    )

    destino = obtener(
        propiedades,
        ["destino", "DESTINO"],
    )

    nombre = obtener(
        propiedades,
        [
            "nombre",
            "NOMBRE",
            "propietario",
            "PROPIETARIO",
        ],
    )

    documento = obtener(
        propiedades,
        [
            "documento",
            "NUMERO_DOCUMENTO",
            "DOCUMENTO",
        ],
    )

    direccion = obtener(
        propiedades,
        ["direccion", "DIRECCION"],
    )

    area = obtener(
        propiedades,
        [
            "area_terreno",
            "AREA DE TERRENO",
            "Shape_Area",
        ],
        None,
    )

    avaluo = obtener(
        propiedades,
        [
            "avaluo_2026",
            "AVALUO 2026",
            "AVALUO_2026",
        ],
        None,
    )

    html = (
        f"<b>Código:</b> {codigo}"
        f"<br><b>Destino:</b> {destino}"
        f"<br><b>Nombre:</b> {nombre}"
        f"<br><b>Documento:</b> {documento}"
        f"<br><b>Dirección:</b> {direccion}"
    )

    if area is not None:
        html += (
            f"<br><b>Área:</b> "
            f"{formatear_numero(area)} m²"
        )

    if avaluo is not None:
        html += (
            f"<br><b>Avalúo 2026:</b> "
            f"${formatear_numero(avaluo)}"
        )

    return html


def construir_ficha_construccion(
    propiedades: dict[str, Any],
) -> str:
    """
    Construye una ficha resumida de una construcción.
    """

    identificador = obtener(
        propiedades,
        ["id", "id_registro", "id_0"],
    )

    anio = obtener(
        propiedades,
        [
            "anio_construccion",
            "const_year",
        ],
    )

    altura = obtener(
        propiedades,
        [
            "altura_metros",
            "altura_m",
        ],
        None,
    )

    area = obtener(
        propiedades,
        [
            "area_m2",
            "area_construccion_m2",
            "area_in_me",
        ],
        None,
    )

    html = (
        f"<b>Identificador:</b> {identificador}"
        f"<br><b>Año de construcción:</b> {anio}"
    )

    if altura is not None:
        html += (
            f"<br><b>Altura:</b> "
            f"{formatear_numero(altura)} m"
        )

    if area is not None:
        html += (
            f"<br><b>Área:</b> "
            f"{formatear_numero(area)} m²"
        )

    return html


def construir_ficha_contribuyente_ica(
    propiedades: dict[str, Any],
) -> str:
    """
    Construye una ficha resumida de un contribuyente ICA.
    """

    tipo = obtener(
        propiedades,
        ["tipo_contribuyente"],
    )

    nombre = obtener(
        propiedades,
        ["nombre_contribuyente"],
        None,
    )

    razon_social = obtener(
        propiedades,
        ["razon_social"],
        None,
    )

    tipo_documento = obtener(
        propiedades,
        ["tipo_documento"],
    )

    numero_documento = obtener(
        propiedades,
        ["numero_documento"],
    )

    direccion = obtener(
        propiedades,
        [
            "direccion",
            "direccion_formateada",
        ],
    )

    estado = obtener(
        propiedades,
        ["estado"],
    )

    nombre_visible = (
        nombre
        if nombre not in [None, "", "N/A"]
        else razon_social
    )

    if nombre_visible in [None, "", "N/A"]:
        nombre_visible = "N/A"

    html = (
        f"<b>Contribuyente:</b> {nombre_visible}"
        f"<br><b>Tipo:</b> {tipo}"
        f"<br><b>Tipo de documento:</b> {tipo_documento}"
        f"<br><b>Número de documento:</b> {numero_documento}"
        f"<br><b>Dirección:</b> {direccion}"
        f"<br><b>Estado:</b> {estado}"
    )

    if (
        razon_social not in [None, "", "N/A"]
        and razon_social != nombre_visible
    ):
        html += (
            f"<br><b>Razón social:</b> "
            f"{razon_social}"
        )

    return html


def construir_ficha_generica(
    registro: dict[str, Any],
    max_campos: int = 10,
) -> str:
    """
    Construye una ficha genérica para cualquier capa nueva.
    """

    html = ""

    campos_agregados = 0

    for clave, valor in registro.items():

        if clave.lower() in {
            "geom",
            "geometry",
            "geometria",
        }:
            continue

        html += (
            f"<b>{humanizar_campo(clave)}:</b> "
            f"{formatear_valor_generico(valor)}<br>"
        )

        campos_agregados += 1

        if campos_agregados >= max_campos:
            break

    return html or "Sin atributos descriptivos disponibles."


# ============================================================
# Detección dinámica de capa y entidad
# ============================================================

def detectar_capa_desde_sql(
    sql: str,
) -> Optional[str]:
    """
    Detecta dinámicamente la capa principal usando el catálogo
    unificado de TERRI+.

    No depende de una lista fija de tablas.
    """

    if not sql:
        return None

    sql_normalizado = sql.lower()

    try:
        capas = obtener_capas_unificadas_disponibles()

    except Exception as error:
        print(
            "⚠️ No fue posible consultar el catálogo "
            f"unificado para detectar la capa: {error}"
        )
        return None

    capas_ordenadas = sorted(
        capas,
        key=lambda capa: len(
            str(capa.get("tabla", ""))
        ),
        reverse=True,
    )

    for capa in capas_ordenadas:

        tabla = str(
            capa.get("tabla", "")
        ).strip()

        if not tabla:
            continue

        if tabla.lower() in sql_normalizado:
            return capa.get("id")

    return None


def detectar_tipo_entidad(
    propiedades: list[dict[str, Any]],
    layer_id: Optional[str] = None,
) -> str:
    """
    Identifica el tipo de entidad territorial.
    """

    if layer_id == "predios":
        return "predio"

    if layer_id == "construcciones":
        return "construccion"

    if layer_id == "contribuyentes_ica":
        return "contribuyente_ica"

    if not propiedades:
        return "entidad"

    campos: set[str] = set()

    for registro in propiedades:
        campos.update(
            str(campo).lower()
            for campo in registro.keys()
        )

    if {
        "numero_predial",
        "codigo",
        "destino",
        "avaluo_2026",
        "area_terreno",
    }.intersection(campos):
        return "predio"

    if {
        "const_year",
        "anio_construccion",
        "altura_m",
        "altura_metros",
        "area_in_me",
        "area_m2",
    }.intersection(campos):
        return "construccion"

    if {
        "tipo_contribuyente",
        "numero_documento",
        "nombre_contribuyente",
        "razon_social",
    }.intersection(campos):
        return "contribuyente_ica"

    return "entidad"


# ============================================================
# Información dinámica de capas
# ============================================================

def obtener_nombre_capa(
    layer_id: Optional[str],
) -> str:
    """
    Obtiene el nombre amigable de una capa.
    """

    if not layer_id:
        return "Capa territorial"

    try:
        capa = obtener_capa_unificada(layer_id)

    except Exception:
        capa = None

    if capa:
        return str(
            capa.get("nombre")
            or humanizar_campo(layer_id)
        )

    return humanizar_campo(layer_id)


def obtener_nombre_entidad(
    layer_id: Optional[str],
    cantidad: float,
) -> str:
    """
    Devuelve el nombre singular o plural de una entidad.
    """

    es_plural = cantidad != 1

    if layer_id == "predios":
        return "predios" if es_plural else "predio"

    if layer_id == "construcciones":
        return (
            "construcciones"
            if es_plural
            else "construcción"
        )

    if layer_id == "contribuyentes_ica":
        return (
            "contribuyentes ICA"
            if es_plural
            else "contribuyente ICA"
        )

    nombre_capa = obtener_nombre_capa(layer_id)

    if es_plural:
        return nombre_capa.lower()

    return f"registro de {nombre_capa.lower()}"


# ============================================================
# Sugerencias
# ============================================================

def sugerencias_mapa(
    tipo_entidad: str,
    layer_id: Optional[str],
) -> list[str]:
    """
    Genera preguntas sugeridas según la entidad.
    """

    if tipo_entidad == "predio":
        return [
            "¿Cuál tiene el mayor avalúo?",
            "Ordénalos por área.",
            "Muéstrame solo los mayores de 2.000 m².",
            "Calcula el avalúo promedio.",
        ]

    if tipo_entidad == "construccion":
        return [
            "¿Cuál es la construcción más alta?",
            "Ordénalas por año de construcción.",
            "Calcula la altura promedio.",
            "Muéstrame las construcciones más recientes.",
        ]

    if tipo_entidad == "contribuyente_ica":
        return [
            "Muéstrame solo las personas naturales.",
            "Muéstrame solo las personas jurídicas.",
            "¿Cuántos contribuyentes están activos?",
            "Agrúpalos por tipo de contribuyente.",
        ]

    nombre = obtener_nombre_capa(layer_id)

    return [
        f"Resume la capa {nombre}.",
        "Agrupa los resultados por una categoría.",
        "Muéstrame los primeros 20 registros.",
        "Limpia el mapa.",
    ]


def sugerencias_tabla(
    tipo_resultado: str,
    layer_id: Optional[str],
) -> list[str]:
    """
    Genera sugerencias según el resultado y la capa.
    """

    if layer_id == "contribuyentes_ica":

        if tipo_resultado == "conteo":
            return [
                "Muéstrame los contribuyentes en el mapa.",
                "Agrúpalos por tipo de contribuyente.",
                "Muéstrame solo las personas jurídicas.",
            ]

        if tipo_resultado == "agrupacion":
            return [
                "Muéstrame las personas naturales en el mapa.",
                "Muéstrame las personas jurídicas en el mapa.",
                "Calcula el porcentaje de cada tipo.",
            ]

    if tipo_resultado == "conteo":
        return [
            "Muéstrame estos elementos en el mapa.",
            "Agrúpalos por categoría.",
            "Genera un resumen.",
        ]

    if tipo_resultado == "agrupacion":
        return [
            "Ordénalos de mayor a menor.",
            "Muéstrame la categoría principal en el mapa.",
            "Calcula el porcentaje de cada categoría.",
        ]

    if tipo_resultado == "agregado":
        return [
            "Muéstrame los valores más altos.",
            "Genera un mapa temático.",
            "Compáralo con otra categoría.",
        ]

    return [
        "Muéstrame estos resultados en el mapa.",
        "Resume la consulta.",
        "Haz un ranking de los principales registros.",
    ]


# ============================================================
# Formatos y utilidades
# ============================================================

def detectar_formato_valor(
    campo: str,
    pregunta: str,
    layer_id: Optional[str],
) -> str:
    """
    Decide si el valor representa moneda, área, longitud,
    porcentaje o un número general.
    """

    texto = f"{campo} {pregunta}".lower()

    if any(
        termino in texto
        for termino in [
            "avaluo",
            "avalúo",
            "valor catastral",
            "pesos",
            "recaudo",
            "precio",
        ]
    ):
        return "moneda"

    if any(
        termino in texto
        for termino in [
            "area",
            "área",
            "superficie",
        ]
    ):
        return "area"

    if any(
        termino in texto
        for termino in [
            "altura",
            "distancia",
            "longitud",
        ]
    ):
        return "longitud"

    if "porcentaje" in texto or "%" in texto:
        return "porcentaje"

    return "numero"


def formatear_valor(
    valor: float,
    tipo_formato: str,
) -> str:
    """
    Formatea un valor según su significado.
    """

    numero = formatear_numero(valor)

    if tipo_formato == "moneda":
        return f"${numero}"

    if tipo_formato == "area":
        return f"{numero} m²"

    if tipo_formato == "longitud":
        return f"{numero} m"

    if tipo_formato == "porcentaje":
        return f"{numero}%"

    return numero


def formatear_valor_generico(
    valor: Any,
) -> str:
    """
    Formatea números, textos y valores vacíos.
    """

    if valor in [None, ""]:
        return "N/A"

    if isinstance(valor, bool):
        return "Sí" if valor else "No"

    numero = convertir_numero(valor)

    if numero is not None:
        return formatear_numero(numero)

    return str(valor)


def humanizar_campo(
    campo: str,
) -> str:
    """
    Convierte un alias técnico en un nombre legible.
    """

    texto = str(campo)
    texto = texto.replace("_", " ")
    texto = texto.replace(".", " ")
    texto = " ".join(texto.split()).strip()

    if not texto:
        return "Campo"

    return texto[:1].upper() + texto[1:]


def obtener(
    propiedades: dict[str, Any],
    posibles: list[str],
    defecto: Any = "N/A",
) -> Any:
    """
    Busca el primer campo no vacío dentro de una lista.
    """

    for campo in posibles:

        valor = propiedades.get(campo)

        if valor not in [None, ""]:
            return valor

    return defecto


def convertir_numero(
    valor: Any,
) -> Optional[float]:
    """
    Convierte valores numéricos a float.
    """

    if valor in [None, "", "N/A"]:
        return None

    if isinstance(valor, bool):
        return None

    if isinstance(valor, (int, float)):
        return float(valor)

    try:
        texto = str(valor).strip()

        if not texto:
            return None

        if "." in texto and "," not in texto:
            partes = texto.split(".")

            if (
                len(partes) > 1
                and all(
                    len(parte) == 3
                    for parte in partes[1:]
                )
            ):
                texto = "".join(partes)

        elif "." in texto and "," in texto:
            texto = texto.replace(".", "")
            texto = texto.replace(",", ".")

        elif "," in texto:
            texto = texto.replace(",", ".")

        return float(texto)

    except (TypeError, ValueError):
        return None


def formatear_numero(
    valor: Any,
) -> str:
    """
    Formatea números con separadores colombianos.
    """

    numero = convertir_numero(valor)

    if numero is None:
        return "N/A"

    if numero.is_integer():
        return (
            f"{numero:,.0f}"
            .replace(",", ".")
        )

    return (
        f"{numero:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def promedio(
    registros: list[dict[str, Any]],
    posibles_campos: list[str],
) -> Optional[float]:
    """
    Calcula el promedio de un campo.
    """

    valores: list[float] = []

    for registro in registros:

        valor = obtener(
            registro,
            posibles_campos,
            None,
        )

        numero = convertir_numero(valor)

        if numero is not None:
            valores.append(numero)

    if not valores:
        return None

    return sum(valores) / len(valores)


def contar_valores(
    registros: list[dict[str, Any]],
    posibles_campos: list[str],
) -> dict[str, int]:
    """
    Cuenta categorías conservando su escritura original.
    """

    conteo: dict[str, int] = {}

    for registro in registros:

        valor = obtener(
            registro,
            posibles_campos,
            None,
        )

        if valor in [None, "", "N/A"]:
            continue

        clave = str(valor).strip()

        conteo[clave] = conteo.get(
            clave,
            0,
        ) + 1

    return ordenar_conteo(conteo)


def contar_valores_normalizados(
    registros: list[dict[str, Any]],
    posibles_campos: list[str],
) -> dict[str, int]:
    """
    Cuenta categorías ignorando diferencias de mayúsculas.
    """

    conteo: dict[str, int] = {}

    for registro in registros:

        valor = obtener(
            registro,
            posibles_campos,
            None,
        )

        if valor in [None, "", "N/A"]:
            continue

        clave = str(valor).strip().upper()

        conteo[clave] = conteo.get(
            clave,
            0,
        ) + 1

    return ordenar_conteo(conteo)


def ordenar_conteo(
    conteo: dict[str, int],
) -> dict[str, int]:
    """
    Ordena un conteo de mayor a menor.
    """

    return dict(
        sorted(
            conteo.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )