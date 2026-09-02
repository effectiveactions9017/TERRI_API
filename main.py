from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import ejecutar_sql

from consultas.predios import analizar_predios
from consultas.construcciones import analizar_construcciones

from services.external_sources.igac_service import (
    verificar_servicio_igac,
    listar_municipios,
    buscar_municipio,
    consultar_limite_municipio,
    consultar_limite_municipio_codigo,
    listar_departamentos,
)

import ia


# ============================================================
# TERRI+
# API PRINCIPAL
# ============================================================

app = FastAPI(
    title="TERRI+ IA Territorial",
    description=(
        "Motor inteligente para análisis geoespacial "
        "con PostGIS y fuentes oficiales externas como IGAC"
    ),
    version="2.3"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTER IA TERRI+
# ============================================================

app.include_router(
    ia.router
)


# ============================================================
# INICIO
# ============================================================

@app.get("/")
def inicio():

    return {
        "estado": "activo",
        "sistema": "🤖 TERRI+ IA Territorial funcionando",
        "postgis": "conectado",
        "igac": "disponible",
        "version": "2.3 modular"
    }


# ============================================================
# TEST POSTGIS - PREDIOS
# ============================================================

@app.get("/test_predios")
def test_predios():

    resultado = ejecutar_sql(
        """
        SELECT COUNT(*) AS total_predios
        FROM predios_sesquile;
        """
    )

    return {
        "capa": "predios_sesquile",
        "resultado": resultado
    }


# ============================================================
# TEST POSTGIS - CONSTRUCCIONES
# ============================================================

@app.get("/test_construcciones")
def test_construcciones():

    resultado = ejecutar_sql(
        """
        SELECT COUNT(*) AS total_construcciones
        FROM construcciones_sesquile;
        """
    )

    return {
        "capa": "construcciones_sesquile",
        "resultado": resultado
    }


# ============================================================
# TEST CONEXIÓN IGAC
# ============================================================

@app.get("/test_igac")
def test_igac():

    return verificar_servicio_igac()


# ============================================================
# TEST LÍMITE MUNICIPAL IGAC
# ============================================================

@app.get("/test_igac/municipio/{nombre}")
def test_igac_municipio(
    nombre: str
):

    return consultar_limite_municipio(
        nombre
    )


# ============================================================
# LISTAR MUNICIPIOS IGAC
# ============================================================

@app.get("/igac/municipios")
def igac_listar_municipios():

    municipios = listar_municipios()

    return {
        "fuente": "IGAC",
        "total": len(municipios),
        "resultados": municipios
    }


# ============================================================
# BUSCAR MUNICIPIO IGAC
# ============================================================

@app.get("/igac/municipio/buscar")
def igac_buscar_municipio(
    nombre: str,
    departamento: str | None = None
):

    resultados = buscar_municipio(
        nombre=nombre,
        departamento=departamento
    )

    return {
        "fuente": "IGAC",
        "consulta": nombre,
        "departamento": departamento,
        "total": len(resultados),
        "resultados": resultados
    }


# ============================================================
# LÍMITE MUNICIPAL POR NOMBRE
# ============================================================

@app.get("/igac/limite/municipio")
def igac_limite_municipio(
    nombre: str,
    departamento: str | None = None
):

    return consultar_limite_municipio(
        nombre=nombre,
        departamento=departamento
    )


# ============================================================
# LÍMITE MUNICIPAL POR CÓDIGO DANE
# ============================================================

@app.get("/igac/limite/municipio/codigo/{codigo}")
def igac_limite_municipio_codigo(
    codigo: str
):

    geojson = (
        consultar_limite_municipio_codigo(
            codigo
        )
    )

    return {
        "ok": True,
        "tipo": "geojson",
        "modo": "mapa",
        "fuente": "IGAC",
        "codigo": codigo,
        "resultado": geojson,
        "layer_id": (
            "igac_limite_municipio_"
            + str(codigo)
        ),
        "visualizacion": {
            "modo": "simple",
            "mostrar_leyenda": False,
            "titulo_leyenda": (
                "Límite municipal IGAC"
            )
        },
        "ejecuto_sql": False,
        "reutilizado": False
    }


# ============================================================
# LISTAR DEPARTAMENTOS IGAC
# ============================================================

@app.get("/igac/departamentos")
def igac_listar_departamentos():

    departamentos = (
        listar_departamentos()
    )

    return {
        "fuente": "IGAC",
        "total": len(departamentos),
        "resultados": departamentos
    }


# ============================================================
# ANALIZADOR TERRI+
# ============================================================

@app.post("/analizar")
def analizar(
    datos: dict
):

    pregunta_original = str(
        datos.get(
            "pregunta",
            ""
        )
    ).strip()

    pregunta = (
        pregunta_original.lower()
    )


    # ========================================================
    # CONSTRUCCIONES
    # ========================================================

    if (
        "construccion" in pregunta
        or "construcciones" in pregunta
        or "edificacion" in pregunta
        or "edificaciones" in pregunta
    ):

        return {
            "pregunta": pregunta_original,
            "respuesta": (
                analizar_construcciones(
                    pregunta
                )
            )
        }


    # ========================================================
    # PREDIOS
    # ========================================================

    if (
        "predio" in pregunta
        or "predios" in pregunta
        or "destino" in pregunta
        or "destinos" in pregunta
        or "avaluo" in pregunta
        or "avalúo" in pregunta
        or "catastro" in pregunta
        or "cuántos" in pregunta
        or "cuantos" in pregunta
        or "total" in pregunta
    ):

        return {
            "pregunta": pregunta_original,
            "respuesta": (
                analizar_predios(
                    pregunta
                )
            )
        }


    # ========================================================
    # AYUDA
    # ========================================================

    return {
        "pregunta": pregunta_original,
        "respuesta": """
🤖 TERRI+ IA

Puedo analizar actualmente información territorial
almacenada en PostGIS y consultar fuentes oficiales
externas.

1. Predios
   - total de predios
   - destinos principales
   - avalúo total
   - predios con mayor avalúo

2. Construcciones
   - total de construcciones detectadas
   - área promedio
   - altura máxima
   - años con mayor número de construcciones
   - confianza promedio del modelo

3. Servicios oficiales IGAC
   - consultar municipios
   - buscar municipios por nombre
   - consultar límites municipales
   - consultar límites mediante código DANE
   - consultar departamentos

Ejemplos:

- Analiza los predios de Sesquilé

- Dame los destinos principales

- ¿Cuál es el avalúo total?

- Analiza las construcciones de Sesquilé

- Muéstrame el límite de Sesquilé según el IGAC

- Muéstrame el límite de Guatavita

- Consulta el municipio de Chía

- Lista los departamentos disponibles en el IGAC
"""
    }
