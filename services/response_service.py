# services/response_service.py

import json

from services.geojson_service import es_consulta_espacial, envolver_sql_geojson
from services.query_executor import ejecutar_consulta
from services.map_memory import guardar_resultado_mapa


def construir_respuesta(sql: str):
    if es_consulta_espacial(sql):
        return construir_respuesta_geojson(sql)

    return construir_respuesta_tabla(sql)


def construir_respuesta_geojson(sql: str):

    sql_geojson = envolver_sql_geojson(sql)
    resultado = ejecutar_consulta(sql_geojson)

    geojson = (
        resultado[0]["geojson"]
        if resultado and "geojson" in resultado[0]
        else {
            "type": "FeatureCollection",
            "features": []
        }
    )

    print("\n========== PRIMER FEATURE GEOJSON ==========\n")

    if geojson.get("features"):
        print(json.dumps(
            geojson["features"][0]["properties"],
            indent=4,
            ensure_ascii=False
        ))
    else:
        print("GeoJSON sin features")

    print("\n===========================================\n")

    total_features = len(geojson.get("features", []))

    memoria = guardar_resultado_mapa(
        tipo="geojson",
        modo="mapa",
        sql=sql,
        resultado=geojson,
        total=total_features
    )

    return {
        "tipo": "geojson",
        "modo": "mapa",
        "sql": sql,
        "resultado": geojson,
        "total_features": total_features,
        "memoria": {
            "total": memoria["total"],
            "campos": memoria["campos"],
            "bbox": memoria["bbox"],
            "fecha": memoria["fecha"]
        }
    }


def construir_respuesta_tabla(sql: str):

    resultado = ejecutar_consulta(sql)
    total_registros = len(resultado)

    memoria = guardar_resultado_mapa(
        tipo="tabla",
        modo="datos",
        sql=sql,
        resultado=resultado,
        total=total_registros
    )

    return {
        "tipo": "tabla",
        "modo": "datos",
        "sql": sql,
        "resultado": resultado,
        "total_registros": total_registros,
        "memoria": {
            "total": memoria["total"],
            "campos": memoria["campos"],
            "bbox": memoria["bbox"],
            "fecha": memoria["fecha"]
        }
    }