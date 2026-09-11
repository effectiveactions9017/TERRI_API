# ============================================================
# TERRI+
# MÓDULO TRIBUTARIO
# ============================================================

from fastapi import APIRouter
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
# ESTADO DE LA BASE MAESTRA
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
