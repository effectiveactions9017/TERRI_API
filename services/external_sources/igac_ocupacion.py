# ============================================================
# TERRI+
# IGAC - COMPONENTE OCUPACIÓN
#
# Consultas nacionales:
# - Centros poblados
# - Cabeceras municipales
# ============================================================

import json
from typing import Any, Dict, Optional

from services.external_sources.igac_carto_100k import (
    buscar_municipio_igac,
    consultar_rest_igac,
    obtener_limite_municipal,
    convertir_geojson_a_arcgis_polygon,
)


IGAC_OCUPACION_BASE = (
    "https://mapas2.igac.gov.co/server/rest/services/"
    "ordenamiento/componenteocupacion/FeatureServer"
)

CAPAS_OCUPACION = {
    "centros_poblados": {
        "id": 3,
        "nombre": "Centros poblados",
        "titulo": "Centros poblados",
    },
    "cabeceras": {
        "id": 4,
        "nombre": "Cabeceras municipales",
        "titulo": "Cabeceras municipales",
    },
}


def consultar_ocupacion_municipio_codigo(
    tema: str,
    codigo: str,
) -> Dict[str, Any]:

    configuracion = CAPAS_OCUPACION.get(
        tema
    )

    if not configuracion:

        return {
            "ok": False,
            "tipo": "tema_no_soportado",
            "modo": "datos",
            "fuente": "IGAC",
            "tema": tema,
            "mensaje": (
                f"El tema '{tema}' no está registrado "
                "en el módulo de ocupación."
            ),
            "ejecuto_sql": False,
            "reutilizado": False,
        }

    try:

        limite = obtener_limite_municipal(
            codigo
        )

        features_limite = limite.get(
            "features",
            []
        )

        if not features_limite:

            return {
                "ok": False,
                "tipo": "sin_resultado",
                "modo": "datos",
                "fuente": "IGAC",
                "tema": tema,
                "mensaje": (
                    f"No se encontró el límite municipal "
                    f"para el código {codigo}."
                ),
                "ejecuto_sql": False,
                "reutilizado": False,
            }

        propiedades_limite = (
            features_limite[0].get(
                "properties",
                {},
            )
        )

        municipio = propiedades_limite.get(
            "MpNombre"
        )

        departamento = propiedades_limite.get(
            "Depto"
        )

        geometria_arcgis = (
            convertir_geojson_a_arcgis_polygon(
                limite
            )
        )

        layer_id = configuracion["id"]

        url = (
            f"{IGAC_OCUPACION_BASE}/"
            f"{layer_id}/query"
        )

        parametros = {
            "where": "1=1",
            "geometry": json.dumps(
                geometria_arcgis,
                separators=(",", ":"),
            ),
            "geometryType": "esriGeometryPolygon",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        }

        resultado = consultar_rest_igac(
            url,
            parametros,
            metodo="post",
        )

        features = resultado.get(
            "features",
            [],
        )

        for feature in features:

            props = feature.setdefault(
                "properties",
                {},
            )

            props["_terri_tema"] = tema
            props["_terri_capa_igac"] = layer_id

        total = len(features)

        if total == 0:

            return {
                "ok": False,
                "tipo": "sin_resultado",
                "modo": "datos",
                "fuente": "IGAC",
                "servicio": (
                    "Componente ocupación y apropiación "
                    "del territorio"
                ),
                "tema": tema,
                "municipio": municipio,
                "departamento": departamento,
                "codigo": codigo,
                "mensaje": (
                    f"El servicio del IGAC no devolvió "
                    f"{configuracion['nombre'].lower()} "
                    f"para {municipio or 'el municipio'}."
                ),
                "ejecuto_sql": False,
                "reutilizado": False,
            }

        return {
            "ok": True,
            "tipo": "geojson",
            "modo": "mapa",
            "fuente": "IGAC",
            "servicio": (
                "Componente ocupación y apropiación "
                "del territorio"
            ),
            "tema": tema,
            "municipio": municipio,
            "departamento": departamento,
            "codigo": codigo,
            "total_features": total,
            "resultado": resultado,
            "layer_id": (
                f"igac_ocupacion_{tema}_{codigo}"
            ),
            "visualizacion": {
                "modo": "simple",
                "mostrar_leyenda": True,
                "titulo_leyenda": (
                    f"{configuracion['titulo']} "
                    f"de {municipio}"
                ),
            },
            "inteligencia": {
                "tipo": "fuente_externa",
                "fuente": "IGAC",
                "tema": tema,
                "mensaje": (
                    f"Se consultaron {total} "
                    f"{configuracion['nombre'].lower()} "
                    f"de {municipio or 'el municipio'} "
                    f"en el servicio territorial del IGAC."
                ),
            },
            "ejecuto_sql": False,
            "reutilizado": False,
        }

    except Exception as error:

        return {
            "ok": False,
            "tipo": "error_fuente_externa",
            "modo": "datos",
            "fuente": "IGAC",
            "tema": tema,
            "codigo": codigo,
            "mensaje": (
                "El servicio territorial del IGAC "
                "no respondió correctamente en este momento. "
                "TERRI+ sigue disponible."
            ),
            "detalle_tecnico": str(error),
            "ejecuto_sql": False,
            "reutilizado": False,
        }


def consultar_ocupacion_municipio(
    tema: str,
    nombre: str,
    departamento: Optional[str] = None,
) -> Dict[str, Any]:

    coincidencias = buscar_municipio_igac(
        nombre=nombre,
        departamento=departamento,
    )

    if not coincidencias:

        return {
            "ok": False,
            "tipo": "sin_resultado",
            "modo": "datos",
            "fuente": "IGAC",
            "tema": tema,
            "mensaje": (
                f"No se encontró el municipio "
                f"'{nombre}' en el catálogo territorial "
                "del IGAC."
            ),
            "ejecuto_sql": False,
            "reutilizado": False,
        }

    if len(coincidencias) > 1:

        return {
            "ok": False,
            "tipo": "ambiguo",
            "modo": "datos",
            "fuente": "IGAC",
            "tema": tema,
            "mensaje": (
                f"Se encontraron varios municipios "
                f"llamados '{nombre}'. "
                "Indica también el departamento."
            ),
            "opciones": coincidencias,
            "ejecuto_sql": False,
            "reutilizado": False,
        }

    codigo = coincidencias[0].get(
        "codigo"
    )

    return consultar_ocupacion_municipio_codigo(
        tema=tema,
        codigo=codigo,
    )
