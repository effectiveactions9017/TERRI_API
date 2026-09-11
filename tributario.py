# ============================================================
# TERRI+
# MÓDULO TRIBUTARIO
# ETAPA 1:
# - ESTADO BASE MAESTRA
# - ANALIZAR ARCHIVO DE IMPUESTO PREDIAL
# ============================================================

from __future__ import annotations

import io
import re
from typing import Any

import pandas as pd

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from sqlalchemy import text

from database import engine


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/tributario",
    tags=["Actualización tributaria"]
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

MAX_ARCHIVO_MB = 20


# ============================================================
# COLUMNAS POSIBLES DEL REPORTE
# ============================================================

COLUMNAS_POSIBLES = {

    "numero_predial": [
        "NUMERO_PREDIAL",
        "NUMERO PREDIAL",
        "NÚMERO PREDIAL",
        "NUMERO PREDIO",
        "NÚMERO PREDIO",
        "NUMERO PREDIO NUEVO",
        "NÚMERO PREDIO NUEVO",
        "NO. PREDIO NUEVO",
        "NO PREDIO NUEVO",
        "Numero Predio Nuevo",
    ],

    "cedula_nit": [
        "CEDULA",
        "CÉDULA",
        "NIT",
        "NIT/CC",
        "NIT CC",
        "DOCUMENTO",
        "NUMERO_DOCUMENTO",
        "NÚMERO DOCUMENTO",
    ],

    "valor_pago": [
        "VALOR_PAGO",
        "VALOR PAGO",
        "VALOR TOTAL",
        "TOTAL PAGADO",
        "VALOR",
        "PAGO",
    ],

    "fecha_pago": [
        "FECHA_PAGO",
        "FECHA PAGO",
        "FECHA",
        "FECHA DE PAGO",
    ],

    "vigencia": [
        "VIGENCIA",
        "AÑO",
        "ANO",
        "VIGENCIA PAGO",
    ],
}


# ============================================================
# UTILIDADES
# ============================================================

def normalizar_texto(
    valor: Any
) -> str:

    if valor is None:
        return ""

    texto = str(valor).strip().upper()

    reemplazos = {
        "Á": "A",
        "É": "E",
        "Í": "I",
        "Ó": "O",
        "Ú": "U",
        "Ü": "U",
        "Ñ": "N",
    }

    for origen, destino in reemplazos.items():

        texto = texto.replace(
            origen,
            destino
        )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto


def normalizar_numero_predial(
    valor: Any
) -> str | None:

    if valor is None:
        return None

    if pd.isna(valor):
        return None

    codigo = str(valor).strip()

    # Caso típico de Excel:
    # 123456789.0
    if codigo.endswith(".0"):

        codigo = codigo[:-2]

    # Mantener solo dígitos
    codigo = re.sub(
        r"[^0-9]",
        "",
        codigo
    )

    if not codigo:
        return None

    # Nuestra llave maestra tiene 25 dígitos
    if len(codigo) < 25:

        codigo = codigo.zfill(25)

    return codigo


def normalizar_valor_simple(
    valor: Any
) -> str | None:

    if valor is None:
        return None

    if pd.isna(valor):
        return None

    texto = str(valor).strip()

    if not texto:
        return None

    if texto.endswith(".0"):

        texto = texto[:-2]

    return texto


# ============================================================
# DETECTAR COLUMNA
# ============================================================

def detectar_columna(
    columnas: list[str],
    candidatos: list[str]
) -> str | None:

    mapa = {
        normalizar_texto(columna):
            columna
        for columna in columnas
    }

    for candidato in candidatos:

        candidato_normalizado = (
            normalizar_texto(
                candidato
            )
        )

        if candidato_normalizado in mapa:

            return mapa[
                candidato_normalizado
            ]

    return None


# ============================================================
# BUSCAR ENCABEZADO DEL EXCEL
#
# Algunos reportes municipales empiezan varias filas abajo.
# Por eso probamos las primeras filas hasta encontrar
# una columna de número predial.
# ============================================================

def leer_excel_con_encabezado(
    contenido: bytes
) -> tuple[
    pd.DataFrame,
    str,
    int
]:

    try:

        archivo = io.BytesIO(
            contenido
        )

        excel = pd.ExcelFile(
            archivo
        )

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=(
                "No fue posible abrir el Excel: "
                + str(error)
            )
        )


    if not excel.sheet_names:

        raise HTTPException(
            status_code=400,
            detail="El Excel no contiene hojas."
        )


    # Primero buscamos hojas cuyo nombre tenga relación
    # con pagos / predial
    hojas_ordenadas = sorted(

        excel.sheet_names,

        key=lambda nombre: (
            0
            if (
                "pago" in nombre.lower()
                or "predial" in nombre.lower()
            )
            else 1
        )
    )


    for hoja in hojas_ordenadas:

        # Probamos hasta las primeras 15 filas
        # como posible encabezado.
        for fila_encabezado in range(
            0,
            15
        ):

            try:

                archivo.seek(0)

                df = pd.read_excel(
                    archivo,
                    sheet_name=hoja,
                    header=fila_encabezado,
                    dtype=object
                )

            except Exception:

                continue


            if df.empty:

                continue


            columnas = [
                str(c)
                for c in df.columns
            ]


            columna_codigo = detectar_columna(

                columnas,

                COLUMNAS_POSIBLES[
                    "numero_predial"
                ]
            )


            if columna_codigo:

                df = df.dropna(
                    how="all"
                )

                return (
                    df,
                    hoja,
                    fila_encabezado + 1
                )


    raise HTTPException(
        status_code=400,
        detail=(
            "No se encontró una columna de número predial "
            "en las primeras filas del archivo. "
            "TERRI+ buscó nombres como NUMERO_PREDIAL, "
            "NUMERO PREDIAL y Numero Predio Nuevo."
        )
    )


# ============================================================
# OBTENER BASE MAESTRA
# ============================================================

def obtener_codigos_maestro() -> set[str]:

    sql = """
    SELECT numero_predial
    FROM predios_maestro;
    """

    with engine.connect() as conexion:

        resultado = conexion.execute(
            text(sql)
        )

        codigos = {
            str(fila[0]).strip()
            for fila in resultado.fetchall()
            if fila[0] is not None
        }

    return codigos


# ============================================================
# ESTADO BASE MAESTRA
# ============================================================

@router.get("/estado")
def estado_tributario():

    with engine.connect() as conexion:

        total_maestro = conexion.execute(
            text(
                """
                SELECT COUNT(*)
                FROM predios_maestro;
                """
            )
        ).scalar_one()

    return {
        "ok": True,
        "predios_maestro": total_maestro
    }


# ============================================================
# ANALIZAR ARCHIVO
# ============================================================

@router.post("/analizar")
async def analizar_archivo_tributario(

    tipo: str = Form(...),

    fecha_corte: str = Form(...),

    archivo: UploadFile = File(...),

):

    # ========================================================
    # VALIDAR TIPO
    # ========================================================

    tipo = str(
        tipo
    ).strip().lower()


    if tipo != "predial":

        raise HTTPException(
            status_code=400,
            detail=(
                "Por ahora TERRI+ solo tiene habilitado "
                "el análisis de impuesto predial."
            )
        )


    # ========================================================
    # VALIDAR ARCHIVO
    # ========================================================

    nombre_archivo = (
        archivo.filename
        or "archivo.xlsx"
    )


    if not nombre_archivo.lower().endswith(
        (
            ".xlsx",
            ".xls"
        )
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "El archivo debe ser Excel "
                "(.xlsx o .xls)."
            )
        )


    contenido = await archivo.read()


    if not contenido:

        raise HTTPException(
            status_code=400,
            detail="El archivo está vacío."
        )


    tamano_mb = (
        len(contenido)
        / 1024
        / 1024
    )


    if tamano_mb > MAX_ARCHIVO_MB:

        raise HTTPException(
            status_code=400,
            detail=(
                f"El archivo supera el máximo "
                f"permitido de {MAX_ARCHIVO_MB} MB."
            )
        )


    # ========================================================
    # LEER EXCEL Y DETECTAR ENCABEZADO
    # ========================================================

    (
        dataframe,
        hoja_detectada,
        fila_encabezado
    ) = leer_excel_con_encabezado(
        contenido
    )


    columnas = [
        str(c)
        for c in dataframe.columns
    ]


    # ========================================================
    # DETECTAR CAMPOS
    # ========================================================

    columna_numero_predial = detectar_columna(

        columnas,

        COLUMNAS_POSIBLES[
            "numero_predial"
        ]
    )


    columna_cedula = detectar_columna(

        columnas,

        COLUMNAS_POSIBLES[
            "cedula_nit"
        ]
    )


    columna_valor = detectar_columna(

        columnas,

        COLUMNAS_POSIBLES[
            "valor_pago"
        ]
    )


    columna_fecha = detectar_columna(

        columnas,

        COLUMNAS_POSIBLES[
            "fecha_pago"
        ]
    )


    columna_vigencia = detectar_columna(

        columnas,

        COLUMNAS_POSIBLES[
            "vigencia"
        ]
    )


    if not columna_numero_predial:

        raise HTTPException(
            status_code=400,
            detail=(
                "No se pudo identificar la columna "
                "del número predial."
            )
        )


    # ========================================================
    # NORMALIZAR CÓDIGOS
    # ========================================================

    dataframe[
        "_numero_predial_terri"
    ] = dataframe[
        columna_numero_predial
    ].apply(
        normalizar_numero_predial
    )


    # ========================================================
    # REGISTROS RECIBIDOS
    # ========================================================

    registros_recibidos = len(
        dataframe
    )


    # Filas con código válido
    dataframe_valido = dataframe[
        dataframe[
            "_numero_predial_terri"
        ].notna()
    ].copy()


    registros_con_codigo = len(
        dataframe_valido
    )


    # ========================================================
    # PREDIOS ÚNICOS
    # ========================================================

    codigos_archivo = set(

        dataframe_valido[
            "_numero_predial_terri"
        ].astype(str)

    )


    # ========================================================
    # CRUCE
    # ========================================================

    maestro = obtener_codigos_maestro()


    cruzados = (
        codigos_archivo
        & maestro
    )


    no_cruzados = (
        codigos_archivo
        - maestro
    )


    # ========================================================
    # DETALLE NO CRUZADOS
    # ========================================================

    detalle_no_cruzados = []


    if no_cruzados:

        df_no_cruzados = dataframe_valido[

            dataframe_valido[
                "_numero_predial_terri"
            ].isin(
                no_cruzados
            )

        ].copy()


        # Solo una fila por código
        df_no_cruzados = (
            df_no_cruzados
            .drop_duplicates(
                subset=[
                    "_numero_predial_terri"
                ],
                keep="first"
            )
        )


        for _, fila in (
            df_no_cruzados
            .head(500)
            .iterrows()
        ):

            detalle_no_cruzados.append(
                {
                    "numero_predial":
                        fila[
                            "_numero_predial_terri"
                        ],

                    "cedula_nit":
                        (
                            normalizar_valor_simple(
                                fila[
                                    columna_cedula
                                ]
                            )
                            if columna_cedula
                            else None
                        ),

                    "vigencia":
                        (
                            normalizar_valor_simple(
                                fila[
                                    columna_vigencia
                                ]
                            )
                            if columna_vigencia
                            else None
                        ),

                    "fecha_pago":
                        (
                            normalizar_valor_simple(
                                fila[
                                    columna_fecha
                                ]
                            )
                            if columna_fecha
                            else None
                        ),
                }
            )


    # ========================================================
    # RESPUESTA
    # ========================================================

    return {

        "ok": True,

        "analisis_id": None,

        "tipo": tipo,

        "archivo": nombre_archivo,

        "fecha_corte": fecha_corte,

        "hoja_detectada":
            hoja_detectada,

        "fila_encabezado":
            fila_encabezado,

        "columnas_detectadas": {

            "numero_predial":
                columna_numero_predial,

            "cedula_nit":
                columna_cedula,

            "valor_pago":
                columna_valor,

            "fecha_pago":
                columna_fecha,

            "vigencia":
                columna_vigencia,
        },

        "resumen": {

            "registros_recibidos":
                registros_recibidos,

            "registros_con_codigo":
                registros_con_codigo,

            "predios_unicos":
                len(
                    codigos_archivo
                ),

            "predios_cruzados":
                len(
                    cruzados
                ),

            "predios_no_cruzados":
                len(
                    no_cruzados
                ),

            "total_base_maestra":
                len(
                    maestro
                ),
        },

        "no_cruzados":
            detalle_no_cruzados,

        "nota": (
            "Este endpoint solo analiza. "
            "Todavía no guarda información "
            "en PostgreSQL."
        )
    }
