# ============================================================
# TERRI+ CORE
# Gestor unificado del catálogo de capas
# ============================================================

from typing import Any, Optional

from services.catalog_service import (
    construir_catalogo_automatico,
)
from services.layer_registry import (
    LAYER_REGISTRY,
)


# ============================================================
# Capacidades básicas para capas nuevas
# ============================================================

CAPACIDADES_POR_DEFECTO = [
    "conteo",
    "filtros",
    "listados",
    "mapa",
    "interseccion",
    "proximidad",
]


# ============================================================
# Construir capa automática básica
# ============================================================

def construir_capa_generica(
    capa_catalogo: dict[str, Any]
) -> dict[str, Any]:
    """
    Construye una configuración básica para una capa detectada
    automáticamente que todavía no tiene conocimiento manual.
    """

    campos_reales = [
        campo.get("campo")
        for campo in capa_catalogo.get("campos", [])
        if campo.get("campo")
    ]

    campo_geometria = capa_catalogo.get(
        "campo_geometria"
    )

    campos_principales = [
        campo
        for campo in campos_reales
        if campo != campo_geometria
    ][:12]

    if campo_geometria:
        campos_principales.append(
            campo_geometria
        )

    return {
        "id": capa_catalogo.get("id"),
        "nombre": capa_catalogo.get("nombre"),
        "tabla": capa_catalogo.get("tabla"),
        "esquema": capa_catalogo.get(
            "esquema",
            "public"
        ),
        "descripcion": (
            "Capa espacial detectada automáticamente "
            "en la base de datos PostGIS."
        ),
        "geometria": capa_catalogo.get(
            "tipo_geometria"
        ),
        "campo_geometria": campo_geometria,
        "srid": capa_catalogo.get("srid"),
        "categoria": "General",
        "campos_principales": campos_principales,
        "capacidades": CAPACIDADES_POR_DEFECTO.copy(),
        "ejemplos": [],
        "disponible": capa_catalogo.get(
            "disponible",
            True
        ),
        "campos_reales": capa_catalogo.get(
            "campos",
            []
        ),
        "geometria_real": {
            "campo_geometria": campo_geometria,
            "tipo_geometria": capa_catalogo.get(
                "tipo_geometria"
            ),
            "srid": capa_catalogo.get("srid"),
        },
        "total_registros": capa_catalogo.get(
            "total_registros"
        ),
        "origen": "automatico",
        "tiene_conocimiento": False,
    }


# ============================================================
# Enriquecer capa conocida
# ============================================================

def enriquecer_capa_conocida(
    capa_catalogo: dict[str, Any],
    capa_registrada: dict[str, Any],
) -> dict[str, Any]:
    """
    Combina la realidad física detectada en PostGIS con
    el conocimiento manual definido en layer_registry.py.
    """

    campo_geometria = capa_catalogo.get(
        "campo_geometria"
    )

    return {
        **capa_registrada,
        "esquema": capa_catalogo.get(
            "esquema",
            "public"
        ),
        "geometria": capa_catalogo.get(
            "tipo_geometria"
        ) or capa_registrada.get("geometria"),
        "campo_geometria": (
            campo_geometria
            or capa_registrada.get(
                "campo_geometria"
            )
        ),
        "srid": (
            capa_catalogo.get("srid")
            or capa_registrada.get("srid")
        ),
        "disponible": capa_catalogo.get(
            "disponible",
            True
        ),
        "campos_reales": capa_catalogo.get(
            "campos",
            []
        ),
        "geometria_real": {
            "campo_geometria": (
                campo_geometria
                or capa_registrada.get(
                    "campo_geometria"
                )
            ),
            "tipo_geometria": (
                capa_catalogo.get(
                    "tipo_geometria"
                )
                or capa_registrada.get(
                    "geometria"
                )
            ),
            "srid": (
                capa_catalogo.get("srid")
                or capa_registrada.get("srid")
            ),
        },
        "total_registros": capa_catalogo.get(
            "total_registros"
        ),
        "origen": "registrado",
        "tiene_conocimiento": True,
    }


# ============================================================
# Obtener catálogo unificado
# ============================================================

def obtener_catalogo_unificado() -> list[dict[str, Any]]:
    """
    Combina las capas detectadas automáticamente con
    las configuraciones manuales de TERRI+.
    """

    catalogo_automatico = (
        construir_catalogo_automatico()
    )

    catalogo_final: list[dict[str, Any]] = []

    tablas_registradas = {
        capa["tabla"].lower(): capa
        for capa in LAYER_REGISTRY.values()
    }

    tablas_detectadas: set[str] = set()

    for capa_catalogo in catalogo_automatico:

        tabla = capa_catalogo.get("tabla")

        if not tabla:
            continue

        tabla_normalizada = tabla.lower()
        tablas_detectadas.add(tabla_normalizada)

        capa_registrada = tablas_registradas.get(
            tabla_normalizada
        )

        if capa_registrada:

            capa_final = enriquecer_capa_conocida(
                capa_catalogo,
                capa_registrada,
            )

        else:

            capa_final = construir_capa_generica(
                capa_catalogo
            )

        catalogo_final.append(capa_final)

    # Incluir capas registradas manualmente cuya tabla
    # todavía no existe en PostGIS.
    for capa_registrada in LAYER_REGISTRY.values():

        tabla = capa_registrada.get("tabla", "")

        if tabla.lower() in tablas_detectadas:
            continue

        catalogo_final.append({
            **capa_registrada,
            "esquema": "public",
            "disponible": False,
            "campos_reales": [],
            "geometria_real": None,
            "total_registros": None,
            "origen": "registrado",
            "tiene_conocimiento": True,
            "error": (
                f"La tabla {tabla} no fue detectada "
                "en PostGIS."
            ),
        })

    return sorted(
        catalogo_final,
        key=lambda capa: (
            capa.get("nombre", "")
        )
    )


# ============================================================
# Consultar capa unificada por ID
# ============================================================

def obtener_capa_unificada(
    layer_id: str
) -> Optional[dict[str, Any]]:
    """
    Busca una capa dentro del catálogo unificado.
    """

    if not layer_id:
        return None

    layer_id_normalizado = (
        layer_id.strip().lower()
    )

    for capa in obtener_catalogo_unificado():

        if (
            str(capa.get("id", "")).lower()
            == layer_id_normalizado
        ):
            return capa

    return None


# ============================================================
# Consultar capa unificada por tabla
# ============================================================

def obtener_capa_unificada_por_tabla(
    tabla: str
) -> Optional[dict[str, Any]]:
    """
    Busca una capa por su nombre físico de tabla.
    """

    if not tabla:
        return None

    tabla_normalizada = tabla.strip().lower()

    for capa in obtener_catalogo_unificado():

        if (
            str(capa.get("tabla", "")).lower()
            == tabla_normalizada
        ):
            return capa

    return None


# ============================================================
# Obtener capas disponibles
# ============================================================

def obtener_capas_unificadas_disponibles(
) -> list[dict[str, Any]]:
    """
    Devuelve únicamente capas presentes en PostGIS.
    """

    return [
        capa
        for capa in obtener_catalogo_unificado()
        if capa.get("disponible") is True
    ]


# ============================================================
# Obtener capas nuevas sin conocimiento
# ============================================================

def obtener_capas_sin_conocimiento(
) -> list[dict[str, Any]]:
    """
    Devuelve las capas detectadas automáticamente que todavía
    no tienen configuración manual ni conocimiento semántico.
    """

    return [
        capa
        for capa in obtener_catalogo_unificado()
        if (
            capa.get("disponible") is True
            and capa.get("tiene_conocimiento") is False
        )
    ]


# ============================================================
# Generar contexto unificado para GPT
# ============================================================

def generar_contexto_catalogo_unificado() -> str:
    """
    Genera el contexto de todas las capas disponibles,
    conocidas o descubiertas automáticamente.
    """

    capas = obtener_capas_unificadas_disponibles()

    if not capas:
        return (
            "No hay capas espaciales disponibles "
            "en TERRI+."
        )

    bloques: list[str] = []

    for capa in capas:

        campos_principales = ", ".join(
            capa.get(
                "campos_principales",
                []
            )
        )

        capacidades = ", ".join(
            capa.get(
                "capacidades",
                []
            )
        )

        conocimiento = (
            "Sí"
            if capa.get("tiene_conocimiento")
            else "No"
        )

        bloque = (
            f"CAPA: {capa.get('nombre')}\n"
            f"ID: {capa.get('id')}\n"
            f"TABLA: {capa.get('tabla')}\n"
            f"ESQUEMA: {capa.get('esquema')}\n"
            f"DESCRIPCIÓN: "
            f"{capa.get('descripcion')}\n"
            f"CATEGORÍA: "
            f"{capa.get('categoria')}\n"
            f"GEOMETRÍA: "
            f"{capa.get('geometria')}\n"
            f"CAMPO GEOMÉTRICO: "
            f"{capa.get('campo_geometria')}\n"
            f"SRID: {capa.get('srid')}\n"
            f"TOTAL DE REGISTROS: "
            f"{capa.get('total_registros')}\n"
            f"CAMPOS PRINCIPALES: "
            f"{campos_principales}\n"
            f"CAPACIDADES: {capacidades}\n"
            f"CONOCIMIENTO SEMÁNTICO: "
            f"{conocimiento}\n"
            f"ORIGEN DEL REGISTRO: "
            f"{capa.get('origen')}\n"
        )

        bloques.append(bloque)

    return "\n---\n".join(bloques)