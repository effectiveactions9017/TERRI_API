from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import ejecutar_sql
from consultas.predios import analizar_predios
from consultas.construcciones import analizar_construcciones

from consultas.igac import (
    estado_igac,
    buscar_municipio,
    limite_municipio,
    limite_municipio_codigo
)

import ia


app = FastAPI(
    title="TERRI+ IA Territorial",
    description="Motor inteligente para análisis geoespacial con PostGIS e IGAC",
    version="2.2"
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
# ROUTER IA
# ============================================================

app.include_router(ia.router)


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
        "version": "2.2 modular"
    }


# ============================================================
# TEST POSTGIS - PREDIOS
# ============================================================

@app.get("/test_predios")
def test_predios():

    resultado = ejecutar_sql("""
        SELECT COUNT(*) AS total_predios
        FROM predios_sesquile;
    """)

    return {
        "capa": "predios_sesquile",
        "resultado": resultado
    }


# ============================================================
# TEST POSTGIS - CONSTRUCCIONES
# ============================================================

@app.get("/test_construcciones")
def test_construcciones():

    resultado = ejecutar_sql("""
        SELECT COUNT(*) AS total_construcciones
        FROM construcciones_sesquile;
    """)

    return {
        "capa": "construcciones_sesquile",
        "resultado": resultado
    }


# ============================================================
# TEST IGAC
# ============================================================

@app.get("/test_igac")
def test_igac():

    return estado_igac()


# ============================================================
# BUSCAR MUNICIPIO EN IGAC
# ============================================================

@app.get("/igac/municipio/buscar")
def igac_buscar_municipio(nombre: str):

    resultado = buscar_municipio(nombre)

    return {
        "consulta": nombre,
        "total": len(resultado),
        "resultados": resultado
    }


# ============================================================
# LÍMITE MUNICIPAL POR NOMBRE
# ============================================================

@app.get("/igac/limite/municipio")
def igac_limite_municipio(nombre: str):

    return limite_municipio(nombre)


# ============================================================
# LÍMITE MUNICIPAL POR CÓDIGO DANE
# ============================================================

@app.get("/igac/limite/municipio/{codigo}")
def igac_limite_municipio_codigo(codigo: str):

    return {
        "tipo": "municipio",
        "fuente": "IGAC",
        "codigo": codigo,
        "geojson": limite_municipio_codigo(codigo)
    }


# ============================================================
# ANALIZADOR TERRI+
# ============================================================

@app.post("/analizar")
def analizar(datos: dict):

    pregunta = datos.get("pregunta", "").lower()

    # --------------------------------------------------------
    # CONSTRUCCIONES
    # --------------------------------------------------------

    if (
        "construccion" in pregunta
        or "construcciones" in pregunta
        or "edificacion" in pregunta
        or "edificaciones" in pregunta
    ):

        return {
            "pregunta": pregunta,
            "respuesta": analizar_construcciones(pregunta)
        }

    # --------------------------------------------------------
    # PREDIOS
    # --------------------------------------------------------

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
            "pregunta": pregunta,
            "respuesta": analizar_predios(pregunta)
        }

    # --------------------------------------------------------
    # AYUDA
    # --------------------------------------------------------

    return {
        "pregunta": pregunta,
        "respuesta": """
🤖 TERRI+ IA

Puedo analizar actualmente:

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
   - confianza promedio

3. Servicios oficiales IGAC
   - búsqueda de municipios
   - límites municipales
   - consulta mediante código DANE

Ejemplos:
- Analiza los predios de Sesquilé
- Dame los destinos principales
- ¿Cuál es el avalúo total?
- Analiza las construcciones de Sesquilé
- Muéstrame el límite de Sesquilé según el IGAC
"""
    }
