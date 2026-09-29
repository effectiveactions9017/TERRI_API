import requests


# ============================================================
# TERRI+
# GEONAMES SERVICE
# Fuente internacional de toponimia y localización
# ============================================================

GEONAMES_BASE_URL = "https://secure.geonames.org"

# Usuario GeoNames
# Prototipo TERRI+
GEONAMES_USERNAME = "davida.gutierrez"


# ============================================================
# VERIFICAR SERVICIO GEONAMES
# ============================================================

def verificar_geonames():

    try:

        url = f"{GEONAMES_BASE_URL}/searchJSON"

        params = {
            "q": "Madrid",
            "country": "ES",
            "maxRows": 1,
            "username": GEONAMES_USERNAME
        }

        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        # GeoNames puede devolver HTTP 200
        # y reportar el error dentro del JSON.
        if "status" in data:

            return {
                "ok": False,
                "fuente": "GeoNames",
                "error": data["status"]
            }

        return {
            "ok": True,
            "fuente": "GeoNames",
            "mensaje": "Servicio GeoNames disponible"
        }

    except Exception as e:

        return {
            "ok": False,
            "fuente": "GeoNames",
            "error": str(e)
        }


# ============================================================
# BUSCAR LUGAR
# ============================================================

def buscar_lugar(
    nombre: str,
    pais: str | None = None,
    max_resultados: int = 10
):

    try:

        url = f"{GEONAMES_BASE_URL}/searchJSON"

        params = {
            "q": nombre,
            "maxRows": max_resultados,
            "username": GEONAMES_USERNAME,
            "style": "FULL"
        }

        if pais:
            params["country"] = pais.upper()

        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        if "status" in data:

            return {
                "ok": False,
                "fuente": "GeoNames",
                "error": data["status"]
            }

        resultados = []

        for lugar in data.get("geonames", []):

            try:
                latitud = float(lugar["lat"])
                longitud = float(lugar["lng"])

            except (
                KeyError,
                TypeError,
                ValueError
            ):
                continue

            resultados.append({
                "geoname_id": lugar.get(
                    "geonameId"
                ),
                "nombre": lugar.get(
                    "name"
                ),
                "nombre_completo": lugar.get(
                    "toponymName"
                ),
                "pais": lugar.get(
                    "countryName"
                ),
                "codigo_pais": lugar.get(
                    "countryCode"
                ),
                "departamento_estado": lugar.get(
                    "adminName1"
                ),
                "division_2": lugar.get(
                    "adminName2"
                ),
                "latitud": latitud,
                "longitud": longitud,
                "poblacion": lugar.get(
                    "population"
                ),
                "feature_class": lugar.get(
                    "fcl"
                ),
                "feature_code": lugar.get(
                    "fcode"
                )
            })

        return {
            "ok": True,
            "fuente": "GeoNames",
            "consulta": nombre,
            "pais_consultado": pais,
            "total": len(resultados),
            "resultados": resultados
        }

    except Exception as e:

        return {
            "ok": False,
            "fuente": "GeoNames",
            "error": str(e)
        }


# ============================================================
# BUSCAR LUGAR Y CONVERTIRLO A GEOJSON
# ============================================================

def buscar_lugar_geojson(
    nombre: str,
    pais: str | None = None
):

    consulta = buscar_lugar(
        nombre=nombre,
        pais=pais,
        max_resultados=1
    )

    if not consulta.get("ok"):

        return consulta

    resultados = consulta.get(
        "resultados",
        []
    )

    if not resultados:

        return {
            "ok": False,
            "fuente": "GeoNames",
            "consulta": nombre,
            "mensaje": (
                f"No se encontró el lugar "
                f"'{nombre}' en GeoNames."
            )
        }

    lugar = resultados[0]

    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [
                lugar["longitud"],
                lugar["latitud"]
            ]
        },
        "properties": {
            "geoname_id": lugar[
                "geoname_id"
            ],
            "nombre": lugar[
                "nombre"
            ],
            "nombre_completo": lugar[
                "nombre_completo"
            ],
            "pais": lugar[
                "pais"
            ],
            "codigo_pais": lugar[
                "codigo_pais"
            ],
            "departamento_estado": lugar[
                "departamento_estado"
            ],
            "division_2": lugar[
                "division_2"
            ],
            "poblacion": lugar[
                "poblacion"
            ],
            "feature_class": lugar[
                "feature_class"
            ],
            "feature_code": lugar[
                "feature_code"
            ],
            "fuente": "GeoNames"
        }
    }

    geojson = {
        "type": "FeatureCollection",
        "features": [
            feature
        ]
    }

    return {
        "ok": True,
        "tipo": "geojson",
        "modo": "mapa",
        "fuente": "GeoNames",
        "consulta": nombre,
        "resultado": geojson,
        "total_features": 1,

        # Punto único:
        # xmin = xmax y ymin = ymax
        "bbox": [
            lugar["longitud"],
            lugar["latitud"],
            lugar["longitud"],
            lugar["latitud"]
        ],

        "layer_id": "geonames_lugar",

        "visualizacion": {
            "modo": "simple",
            "campo_categoria": None,
            "campo_valor": None,
            "mostrar_leyenda": False,
            "titulo_leyenda": (
                "Lugar — GeoNames"
            )
        },

        "ejecuto_sql": False,
        "reutilizado": False
    }

