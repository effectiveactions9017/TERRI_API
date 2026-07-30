# ============================================================
# TERRI+ CORE
# Inferencia semántica automática de capas y atributos
# ============================================================

import re
from typing import Any, Optional

from services.query_executor import ejecutar_consulta
from services.registry_manager import (
    obtener_capa_unificada,
    obtener_catalogo_unificado,
)


# ============================================================
# Configuración
# ============================================================

MAX_VALORES_MUESTRA = 12
MAX_REGISTROS_ANALISIS = 5000


# ============================================================
# Validar identificadores PostgreSQL
# ============================================================

def validar_identificador(nombre: str) -> bool:
    """
    Valida nombres de esquemas, tablas y columnas antes
    de utilizarlos como identificadores SQL.
    """

    if not nombre:
        return False

    return bool(
        re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*",
            nombre,
        )
    )


def citar_identificador(nombre: str) -> str:
    """
    Devuelve un identificador PostgreSQL entre comillas dobles.

    El nombre debe provenir del catálogo real de PostgreSQL.
    """

    if not nombre:
        raise ValueError(
            "El identificador no puede estar vacío."
        )

    return '"' + nombre.replace('"', '""') + '"'


# ============================================================
# Normalización de nombres
# ============================================================

def normalizar_texto(texto: str) -> str:
    """
    Normaliza un nombre de campo para análisis semántico.
    """

    if not texto:
        return ""

    texto = texto.strip().lower()
    texto = texto.replace(".", "_")
    texto = texto.replace(" ", "_")

    return texto


# ============================================================
# Inferir tipo semántico por nombre y tipo físico
# ============================================================

def inferir_tipo_semantico(
    campo: str,
    tipo_dato: str = "",
    tipo_interno: str = "",
) -> str:
    """
    Infiere el significado básico de un campo usando:

    - nombre del atributo;
    - tipo de dato PostgreSQL;
    - tipo interno.
    """

    nombre = normalizar_texto(campo)
    tipo = f"{tipo_dato} {tipo_interno}".lower()
    tipo_interno_normalizado = tipo_interno.lower()

    # ========================================================
    # Geometría
    # ========================================================

    if (
        tipo_interno_normalizado == "geometry"
        or nombre in {
            "geom",
            "geometry",
            "geometria",
        }
    ):
        return "geometria"

    # ========================================================
    # Coordenadas
    # ========================================================

    if nombre in {
        "lat",
        "latitud",
        "latitude",
        "lon",
        "lng",
        "longitud",
        "longitude",
    }:
        return "coordenada"

    # ========================================================
    # Categorías explícitas
    # ========================================================

    if nombre in {
        "tipo_documento",
        "clase_documento",
        "tipo_contribuyente",
        "naturaleza_juridica",
        "regimen_tributario",
        "estado",
        "tipo_ubicacion",
        "estado_geocodificacion",
    }:
        return "categoria"

    # ========================================================
    # Identificadores personales
    # ========================================================

    if any(
        termino in nombre
        for termino in [
            "numero_documento",
            "nro_documento",
            "no_documento",
            "documento_identidad",
            "numero_identificacion",
            "identificacion",
            "cedula",
            "cédula",
            "nit",
        ]
    ):
        return "identificador_persona"

    # ========================================================
    # Identificadores generales
    # ========================================================

    if (
        nombre == "id"
        or nombre.startswith("id_")
        or nombre.endswith("_id")
        or any(
            termino in nombre
            for termino in [
                "codigo",
                "identificador",
                "numero_predial",
            ]
        )
    ):
        return "identificador"

    # ========================================================
    # Nombres de personas o entidades
    # ========================================================

    if any(
        termino in nombre
        for termino in [
            "nombre",
            "razon_social",
            "razón_social",
            "propietario",
            "titular",
        ]
    ):
        return "nombre"

    # ========================================================
    # Direcciones
    # ========================================================

    if any(
        termino in nombre
        for termino in [
            "direccion",
            "dirección",
            "address",
            "domicilio",
        ]
    ):
        return "direccion"

    # ========================================================
    # Categorías generales
    # ========================================================

    if any(
        termino in nombre
        for termino in [
            "estado",
            "tipo",
            "categoria",
            "categoría",
            "regimen",
            "régimen",
            "naturaleza",
            "destino",
            "uso",
            "clase",
        ]
    ):
        return "categoria"

    # ========================================================
    # Fechas
    # ========================================================

    if (
        any(
            termino in nombre
            for termino in [
                "fecha",
                "date",
                "timestamp",
            ]
        )
        or "date" in tipo
        or "timestamp" in tipo
    ):
        return "fecha"

    # ========================================================
    # Periodos
    # ========================================================

    if any(
        termino in nombre
        for termino in [
            "anio",
            "año",
            "year",
            "vigencia",
            "periodo",
        ]
    ):
        return "periodo"

    # ========================================================
    # Moneda
    # ========================================================

    if any(
        termino in nombre
        for termino in [
            "avaluo",
            "avalúo",
            "valor",
            "precio",
            "recaudo",
            "ingreso",
            "total_pago",
            "monto",
        ]
    ):
        return "moneda"

    # ========================================================
    # Área
    # ========================================================

    if any(
        termino in nombre
        for termino in [
            "area",
            "área",
            "superficie",
        ]
    ):
        return "area"

    # ========================================================
    # Longitud o distancia
    # ========================================================

    if any(
        termino in nombre
        for termino in [
            "altura",
            "distancia",
            "longitud_m",
            "largo",
        ]
    ):
        return "longitud"

    # ========================================================
    # Porcentaje
    # ========================================================

    if any(
        termino in nombre
        for termino in [
            "porcentaje",
            "percent",
            "tasa",
            "proporcion",
            "proporción",
        ]
    ):
        return "porcentaje"

    # ========================================================
    # Número
    # ========================================================

    if any(
        termino in tipo
        for termino in [
            "integer",
            "numeric",
            "double",
            "real",
            "decimal",
            "float",
            "bigint",
            "smallint",
        ]
    ):
        return "numero"

    # ========================================================
    # Texto
    # ========================================================

    if any(
        termino in tipo
        for termino in [
            "character",
            "varchar",
            "text",
        ]
    ):
        return "texto"

    return "desconocido"


# ============================================================
# Inferir capacidades
# ============================================================

def inferir_capacidades(
    tipo_semantico: str
) -> list[str]:
    """
    Define operaciones básicas según el tipo semántico.
    """

    capacidades = {
        "geometria": [
            "mapa",
            "interseccion",
            "proximidad",
            "buffer",
            "centroide",
        ],
        "identificador": [
            "busqueda",
            "filtro",
            "conteo",
        ],
        "identificador_persona": [
            "busqueda",
            "filtro",
        ],
        "nombre": [
            "busqueda",
            "filtro",
            "agrupacion",
        ],
        "direccion": [
            "busqueda",
            "filtro",
        ],
        "categoria": [
            "filtro",
            "agrupacion",
            "conteo",
            "porcentaje",
            "mapa_tematico",
        ],
        "fecha": [
            "filtro",
            "agrupacion",
            "analisis_temporal",
        ],
        "periodo": [
            "filtro",
            "agrupacion",
            "comparacion",
            "analisis_temporal",
        ],
        "moneda": [
            "filtro",
            "suma",
            "promedio",
            "maximo",
            "minimo",
            "comparacion",
            "mapa_tematico",
        ],
        "area": [
            "filtro",
            "suma",
            "promedio",
            "maximo",
            "minimo",
            "clasificacion",
            "mapa_tematico",
        ],
        "longitud": [
            "filtro",
            "promedio",
            "maximo",
            "minimo",
            "clasificacion",
        ],
        "porcentaje": [
            "filtro",
            "promedio",
            "maximo",
            "minimo",
        ],
        "numero": [
            "filtro",
            "suma",
            "promedio",
            "maximo",
            "minimo",
        ],
        "texto": [
            "busqueda",
            "filtro",
            "agrupacion",
        ],
        "coordenada": [
            "ubicacion",
        ],
    }

    return capacidades.get(
        tipo_semantico,
        ["filtro"],
    )


# ============================================================
# Obtener valores representativos
# ============================================================

def obtener_valores_frecuentes(
    tabla: str,
    campo: str,
    esquema: str = "public",
    limite: int = MAX_VALORES_MUESTRA,
) -> list[dict[str, Any]]:
    """
    Obtiene los valores más frecuentes de un atributo.

    Solo debe llamarse con tablas y campos provenientes
    del catálogo real.
    """

    if not tabla or not campo:
        return []

    tabla_sql = citar_identificador(tabla)
    esquema_sql = citar_identificador(esquema)
    campo_sql = citar_identificador(campo)

    sql = f"""
        SELECT
            {campo_sql} AS valor,
            COUNT(*) AS cantidad
        FROM {esquema_sql}.{tabla_sql}
        WHERE {campo_sql} IS NOT NULL
          AND TRIM({campo_sql}::text) <> ''
        GROUP BY {campo_sql}
        ORDER BY cantidad DESC
        LIMIT :limite;
    """

    return ejecutar_consulta(
        sql,
        {"limite": limite},
    )


# ============================================================
# Analizar cardinalidad
# ============================================================

def obtener_estadisticas_campo(
    tabla: str,
    campo: str,
    esquema: str = "public",
) -> dict[str, Any]:
    """
    Obtiene total, nulos y valores distintos del campo.
    """

    tabla_sql = citar_identificador(tabla)
    esquema_sql = citar_identificador(esquema)
    campo_sql = citar_identificador(campo)

    sql = f"""
        SELECT
            COUNT(*) AS total,
            COUNT({campo_sql}) AS no_nulos,
            COUNT(DISTINCT {campo_sql}) AS distintos
        FROM {esquema_sql}.{tabla_sql};
    """

    resultado = ejecutar_consulta(sql)

    if not resultado:
        return {
            "total": 0,
            "no_nulos": 0,
            "nulos": 0,
            "distintos": 0,
        }

    datos = resultado[0]

    total = int(datos.get("total", 0))
    no_nulos = int(datos.get("no_nulos", 0))

    return {
        "total": total,
        "no_nulos": no_nulos,
        "nulos": total - no_nulos,
        "distintos": int(
            datos.get("distintos", 0)
        ),
    }


# ============================================================
# Determinar si conviene muestrear valores
# ============================================================

def debe_obtener_valores(
    tipo_semantico: str,
    estadisticas: dict[str, Any],
) -> bool:
    """
    Decide si un campo parece categórico y conviene
    incluir sus valores frecuentes.
    """

    if tipo_semantico == "categoria":
        return True

    distintos = estadisticas.get(
        "distintos",
        0,
    )

    total = estadisticas.get(
        "total",
        0,
    )

    if total == 0:
        return False

    return (
        tipo_semantico == "texto"
        and 0 < distintos <= 30
    )


# ============================================================
# Inferir conocimiento de un campo
# ============================================================

def inferir_conocimiento_campo(
    tabla: str,
    campo_info: dict[str, Any],
    esquema: str = "public",
) -> dict[str, Any]:
    """
    Construye conocimiento semántico básico para un atributo.
    """

    campo = campo_info.get("campo")
    tipo_dato = campo_info.get(
        "tipo_dato",
        "",
    )
    tipo_interno = campo_info.get(
        "tipo_interno",
        "",
    )

    tipo_semantico = inferir_tipo_semantico(
        campo=campo,
        tipo_dato=tipo_dato,
        tipo_interno=tipo_interno,
    )

    estadisticas = obtener_estadisticas_campo(
        tabla=tabla,
        campo=campo,
        esquema=esquema,
    )

    valores_frecuentes: list[dict[str, Any]] = []

    if debe_obtener_valores(
        tipo_semantico,
        estadisticas,
    ):
        valores_frecuentes = obtener_valores_frecuentes(
            tabla=tabla,
            campo=campo,
            esquema=esquema,
        )

    return {
        "campo": campo,
        "nombre_amigable": campo.replace(
            "_",
            " ",
        ).title(),
        "tipo_fisico": tipo_dato,
        "tipo_interno": tipo_interno,
        "tipo_semantico": tipo_semantico,
        "capacidades": inferir_capacidades(
            tipo_semantico
        ),
        "permite_nulos": (
            campo_info.get("permite_nulos")
            == "YES"
        ),
        "estadisticas": estadisticas,
        "valores_frecuentes": valores_frecuentes,
        "origen_conocimiento": "automatico",
    }


# ============================================================
# Escanear una capa
# ============================================================

def escanear_capa_semanticamente(
    layer_id: str
) -> Optional[dict[str, Any]]:
    """
    Analiza automáticamente una capa registrada o descubierta.
    """

    capa = obtener_capa_unificada(layer_id)

    if not capa:
        return None

    if capa.get("disponible") is not True:
        return {
            "layer_id": layer_id,
            "disponible": False,
            "error": "La capa no está disponible en PostGIS.",
        }

    tabla = capa.get("tabla")
    esquema = capa.get(
        "esquema",
        "public",
    )

    campos = capa.get(
        "campos_reales",
        [],
    )

    conocimiento_campos: list[dict[str, Any]] = []

    for campo_info in campos:

        try:
            conocimiento_campos.append(
                inferir_conocimiento_campo(
                    tabla=tabla,
                    campo_info=campo_info,
                    esquema=esquema,
                )
            )

        except Exception as error:

            conocimiento_campos.append({
                "campo": campo_info.get("campo"),
                "tipo_semantico": "desconocido",
                "capacidades": [],
                "origen_conocimiento": "automatico",
                "error": str(error),
            })

    return {
        "layer_id": capa.get("id"),
        "nombre": capa.get("nombre"),
        "tabla": tabla,
        "esquema": esquema,
        "geometria": capa.get("geometria"),
        "campo_geometria": capa.get(
            "campo_geometria"
        ),
        "total_registros": capa.get(
            "total_registros"
        ),
        "campos": conocimiento_campos,
        "origen_conocimiento": "automatico",
    }


# ============================================================
# Escanear todas las capas
# ============================================================

def escanear_catalogo_semanticamente(
) -> list[dict[str, Any]]:
    """
    Genera conocimiento automático para todas las capas.
    """

    resultados: list[dict[str, Any]] = []

    for capa in obtener_catalogo_unificado():

        if capa.get("disponible") is not True:
            continue

        resultado = escanear_capa_semanticamente(
            capa.get("id")
        )

        if resultado:
            resultados.append(resultado)

    return resultados


# ============================================================
# Generar contexto automático para GPT
# ============================================================

def generar_contexto_semantico_automatico(
    layer_id: Optional[str] = None
) -> str:
    """
    Genera un contexto compacto basado en la inferencia
    automática de atributos y valores.
    """

    if layer_id:

        capa = escanear_capa_semanticamente(
            layer_id
        )

        capas = [capa] if capa else []

    else:
        capas = escanear_catalogo_semanticamente()

    if not capas:
        return (
            "No fue posible generar conocimiento "
            "semántico automático."
        )

    bloques: list[str] = []

    for capa in capas:

        lineas_campos: list[str] = []

        for campo in capa.get(
            "campos",
            [],
        ):

            valores = campo.get(
                "valores_frecuentes",
                [],
            )

            valores_texto = ", ".join(
                f"{item.get('valor')} "
                f"({item.get('cantidad')})"
                for item in valores[:8]
            )

            linea = (
                f"- CAMPO: {campo.get('campo')}\n"
                f"  TIPO FÍSICO: "
                f"{campo.get('tipo_fisico')}\n"
                f"  TIPO SEMÁNTICO INFERIDO: "
                f"{campo.get('tipo_semantico')}\n"
                f"  CAPACIDADES: "
                f"{', '.join(campo.get('capacidades', []))}\n"
                f"  VALORES DISTINTOS: "
                f"{campo.get('estadisticas', {}).get('distintos')}\n"
            )

            if valores_texto:
                linea += (
                    f"  VALORES FRECUENTES: "
                    f"{valores_texto}\n"
                )

            lineas_campos.append(linea)

        bloques.append(
            f"CAPA: {capa.get('nombre')}\n"
            f"ID: {capa.get('layer_id')}\n"
            f"TABLA: {capa.get('tabla')}\n"
            f"GEOMETRÍA: {capa.get('geometria')}\n"
            f"TOTAL REGISTROS: "
            f"{capa.get('total_registros')}\n"
            f"CONOCIMIENTO AUTOMÁTICO:\n"
            + "\n".join(lineas_campos)
        )

    return "\n---\n".join(bloques)