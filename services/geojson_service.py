# services/geojson_service.py

def es_consulta_espacial(sql: str) -> bool:
    """
    Detecta si una consulta SQL devuelve geometría.
    """
    sql_lower = sql.lower()

    indicadores_geom = [
        " geom",
        ".geom",
        "st_asgeojson",
        "geometry",
        "geometria",
        "the_geom"
    ]

    return any(indicador in sql_lower for indicador in indicadores_geom)


def envolver_sql_geojson(sql: str) -> str:
    """
    Envuelve una consulta espacial para que PostGIS devuelva
    una FeatureCollection GeoJSON estándar.
    """

    sql_limpio = sql.strip().rstrip(";")

    return f"""
    SELECT json_build_object(
        'type', 'FeatureCollection',
        'features', COALESCE(json_agg(feature), '[]'::json)
    ) AS geojson
    FROM (
        SELECT json_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(t.geom)::json,
            'properties', to_jsonb(t) - 'geom'
        ) AS feature
        FROM (
            {sql_limpio}
        ) AS t
        WHERE t.geom IS NOT NULL
    ) AS features;
    """