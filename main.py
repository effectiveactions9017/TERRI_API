from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import ejecutar_sql
from consultas.predios import analizar_predios
from consultas.construcciones import analizar_construcciones

import ia


app = FastAPI(
    title="TERRI+ IA Territorial",
    description="Motor inteligente para análisis geoespacial con PostGIS",
    version="2.1"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ia.router)


@app.get("/")
def inicio():
    return {
        "estado": "activo",
        "sistema": "🤖 TERRI+ IA Territorial funcionando",
        "postgis": "conectado",
        "version": "2.1 modular"
    }


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


@app.post("/analizar")
def analizar(datos: dict):

    pregunta = datos.get("pregunta", "").lower()

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

    return {
        "pregunta": pregunta,
        "respuesta": """
🤖 TERRI+ IA

Puedo analizar actualmente estas capas:

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

Ejemplos:
- Analiza los predios de Sesquilé
- Dame los destinos principales
- ¿Cuál es el avalúo total?
- Analiza las construcciones de Sesquilé
- ¿Cuántas construcciones detectadas hay?
"""
    }