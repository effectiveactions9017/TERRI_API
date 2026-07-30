from fastapi import APIRouter
from pydantic import BaseModel

from services.llm_service import preguntar_ia
from services.sql_generator import generar_sql
from services.analysis_service import analizar_pregunta

router = APIRouter(
    prefix="/ia",
    tags=["IA TERRI+"]
)


class PreguntaIA(BaseModel):
    pregunta: str


@router.post("/preguntar")
def preguntar(data: PreguntaIA):
    respuesta = preguntar_ia(data.pregunta)

    return {
        "pregunta": data.pregunta,
        "respuesta": respuesta
    }


@router.post("/sql")
def generar_consulta_sql(data: PreguntaIA):
    sql = generar_sql(data.pregunta)

    return {
        "pregunta": data.pregunta,
        "sql": sql
    }


@router.post("/consultar")
def consultar_base_datos(data: PreguntaIA):
    return analizar_pregunta(data.pregunta)