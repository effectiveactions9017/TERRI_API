# services/map_memory.py

from datetime import datetime


ULTIMO_RESULTADO_MAPA = {
    "tipo": None,
    "modo": None,
    "sql": None,
    "resultado": None,
    "total": 0,
    "campos": [],
    "bbox": None,
    "fecha": None
}


def calcular_bbox_geojson(geojson: dict):
    """
    Calcula el bbox general de un GeoJSON.
    Retorna [minx, miny, maxx, maxy].
    """

    coords = []

    def extraer_coordenadas(geometria):
        if not geometria:
            return

        tipo = geometria.get("type")
        coordenadas = geometria.get("coordinates", [])

        if tipo == "Point":
            coords.append(coordenadas)

        elif tipo in ["LineString", "MultiPoint"]:
            coords.extend(coordenadas)

        elif tipo in ["Polygon", "MultiLineString"]:
            for parte in coordenadas:
                coords.extend(parte)

        elif tipo == "MultiPolygon":
            for poligono in coordenadas:
                for anillo in poligono:
                    coords.extend(anillo)

    for feature in geojson.get("features", []):
        extraer_coordenadas(feature.get("geometry"))

    if not coords:
        return None

    xs = [c[0] for c in coords if len(c) >= 2]
    ys = [c[1] for c in coords if len(c) >= 2]

    if not xs or not ys:
        return None

    return [min(xs), min(ys), max(xs), max(ys)]


def extraer_campos_geojson(geojson: dict):
    """
    Extrae los campos disponibles desde las propiedades del primer feature.
    """

    features = geojson.get("features", [])

    if not features:
        return []

    propiedades = features[0].get("properties", {})

    return list(propiedades.keys())


def guardar_resultado_mapa(tipo: str, modo: str, sql: str, resultado, total: int):
    """
    Guarda el último resultado mostrado o consultado por TERRI+.
    """

    global ULTIMO_RESULTADO_MAPA

    bbox = None
    campos = []

    if tipo == "geojson" and isinstance(resultado, dict):
        bbox = calcular_bbox_geojson(resultado)
        campos = extraer_campos_geojson(resultado)

    elif tipo == "tabla" and isinstance(resultado, list) and resultado:
        campos = list(resultado[0].keys())

    ULTIMO_RESULTADO_MAPA = {
        "tipo": tipo,
        "modo": modo,
        "sql": sql,
        "resultado": resultado,
        "total": total,
        "campos": campos,
        "bbox": bbox,
        "fecha": datetime.now().isoformat()
    }

    return ULTIMO_RESULTADO_MAPA


def obtener_ultimo_resultado():
    """
    Devuelve la memoria actual del mapa.
    """
    return ULTIMO_RESULTADO_MAPA


def limpiar_memoria():
    """
    Limpia la memoria espacial.
    """

    global ULTIMO_RESULTADO_MAPA

    ULTIMO_RESULTADO_MAPA = {
        "tipo": None,
        "modo": None,
        "sql": None,
        "resultado": None,
        "total": 0,
        "campos": [],
        "bbox": None,
        "fecha": None
    }

    return ULTIMO_RESULTADO_MAPA