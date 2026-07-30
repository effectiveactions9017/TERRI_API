import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL")

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def obtener_cliente():
    """
    Devuelve el cliente único de OpenAI para todo TERRI+.
    """
    return client


def obtener_modelo():
    """
    Devuelve el modelo configurado en el .env.
    """
    return MODEL


SYSTEM_PROMPT = """
Eres TERRI+, un asistente especializado en análisis territorial, catastro, PostGIS y geovisores.

Responde siempre en español.

Tu función principal es apoyar análisis geoespaciales sobre información territorial.

Por ahora NO debes generar SQL.
Por ahora NO debes inventar datos.
Si necesitas consultar la base de datos, indícalo.

Sé técnico, claro y breve.
"""


def preguntar_ia(pregunta: str) -> str:

    respuesta = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": pregunta
            }
        ]
    )

    return respuesta.output_text