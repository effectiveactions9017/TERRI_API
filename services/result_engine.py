# ============================================================
# TERRI+
# Result Engine
# Memoria operativa del último resultado ejecutado
# ============================================================

from copy import deepcopy
from datetime import datetime


# ============================================================
# RESULTADO ACTUAL
# ============================================================

RESULTADO_ACTUAL = {
    "tipo": None,
    "tabla": None,
    "layer_id": None,
    "sql": None,
    "resultado": None,
    "memoria": None,
    "fecha": None
}


# ============================================================
# GUARDAR RESULTADO
# ============================================================

def guardar_resultado(
    tipo,
    tabla,
    layer_id,
    sql,
    resultado,
    memoria=None
):
    """
    Guarda el último resultado generado por TERRI+.
    """

    RESULTADO_ACTUAL["tipo"] = tipo
    RESULTADO_ACTUAL["tabla"] = tabla
    RESULTADO_ACTUAL["layer_id"] = layer_id
    RESULTADO_ACTUAL["sql"] = sql
    RESULTADO_ACTUAL["resultado"] = deepcopy(resultado)
    RESULTADO_ACTUAL["memoria"] = deepcopy(memoria)
    RESULTADO_ACTUAL["fecha"] = datetime.now().isoformat()


# ============================================================
# OBTENER RESULTADO
# ============================================================

def obtener_resultado():
    """
    Devuelve una copia segura del resultado actual.
    """

    return deepcopy(RESULTADO_ACTUAL)


# ============================================================
# LIMPIAR RESULTADO
# ============================================================

def limpiar_resultado():
    """
    Elimina completamente el resultado almacenado.
    """

    for clave in RESULTADO_ACTUAL:
        RESULTADO_ACTUAL[clave] = None


# ============================================================
# EXISTE RESULTADO
# ============================================================

def hay_resultado():

    return RESULTADO_ACTUAL["resultado"] is not None


# ============================================================
# TIPO TABLA
# ============================================================

def es_tabla():

    return RESULTADO_ACTUAL["tipo"] == "tabla"


# ============================================================
# TIPO GEOJSON
# ============================================================

def es_geojson():

    return RESULTADO_ACTUAL["tipo"] == "geojson"


# ============================================================
# OBTENER SQL
# ============================================================

def obtener_sql():

    return RESULTADO_ACTUAL["sql"]


# ============================================================
# OBTENER LAYER
# ============================================================

def obtener_layer():

    return RESULTADO_ACTUAL["layer_id"]


# ============================================================
# OBTENER REGISTROS
# ============================================================

def obtener_registros():

    return deepcopy(RESULTADO_ACTUAL["resultado"])


# ============================================================
# IMPRIMIR RESULTADO
# ============================================================

def imprimir_resultado():

    print("\n================ RESULT ENGINE ================\n")

    print("Tipo:", RESULTADO_ACTUAL["tipo"])
    print("Tabla:", RESULTADO_ACTUAL["tabla"])
    print("Layer:", RESULTADO_ACTUAL["layer_id"])
    print("SQL:", RESULTADO_ACTUAL["sql"])
    print("Fecha:", RESULTADO_ACTUAL["fecha"])

    if RESULTADO_ACTUAL["resultado"] is None:
        print("\nSin resultado almacenado.")

    else:
        print("\nResultado almacenado correctamente.")

    print("\n===============================================\n")