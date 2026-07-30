from database import ejecutar_sql


def formato_numero(valor):
    if valor is None:
        return "0"
    return f"{int(valor):,}".replace(",", ".")


def formato_pesos(valor):
    if valor is None:
        return "$0"
    return "$" + f"{int(valor):,}".replace(",", ".")


def analizar_predios(pregunta):

    # ===============================
    # CONSULTA: DESTINOS PRINCIPALES
    # ===============================

    if "destino" in pregunta or "destinos" in pregunta:

        destinos = ejecutar_sql("""
            SELECT 
                COALESCE("DESTINO", 'Sin destino') AS destino,
                COUNT(*) AS total
            FROM predios_sesquile
            GROUP BY "DESTINO"
            ORDER BY total DESC
            LIMIT 10;
        """)

        texto = ""

        for i, item in enumerate(destinos, start=1):
            texto += (
                f"{i}. {item['destino']}\n"
                f"   {formato_numero(item['total'])} predios\n\n"
            )

        return f"""
🤖 TERRI+ IA — Destinos prediales principales

Los principales destinos identificados en la capa predial son:

{texto}

Fuente:
PostGIS — public.predios_sesquile
"""

    # ===============================
    # CONSULTA: AVALÚO TOTAL
    # ===============================

    if "avaluo" in pregunta or "avalúo" in pregunta:

        avaluo = ejecutar_sql("""
            SELECT 
                SUM(
                    NULLIF(
                        regexp_replace("AVALUO 2026", '[^0-9]', '', 'g'),
                        ''
                    )::numeric
                ) AS total_avaluo_2026
            FROM predios_sesquile;
        """)

        top = ejecutar_sql("""
            SELECT 
                "NUMERO_PREDIAL",
                "NOMBRE",
                "DESTINO",
                NULLIF(
                    regexp_replace("AVALUO 2026", '[^0-9]', '', 'g'),
                    ''
                )::numeric AS avaluo
            FROM predios_sesquile
            WHERE "AVALUO 2026" IS NOT NULL
            ORDER BY avaluo DESC
            LIMIT 5;
        """)

        texto_top = ""

        for i, item in enumerate(top, start=1):
            texto_top += (
                f"{i}. Predio: {item['NUMERO_PREDIAL']}\n"
                f"   Titular: {item['NOMBRE']}\n"
                f"   Destino: {item['DESTINO']}\n"
                f"   Avalúo: {formato_pesos(item['avaluo'])}\n\n"
            )

        return f"""
🤖 TERRI+ IA — Avalúo predial 2026

El avalúo total aproximado registrado para 2026 es:

{formato_pesos(avaluo[0]['total_avaluo_2026'])}

Predios con mayor avalúo:

{texto_top}

Fuente:
PostGIS — public.predios_sesquile
"""

    # ===============================
    # CONSULTA: TOTAL DE PREDIOS
    # ===============================

    if "cuántos" in pregunta or "cuantos" in pregunta or "total" in pregunta:

        total = ejecutar_sql("""
            SELECT COUNT(*) AS total
            FROM predios_sesquile;
        """)

        return f"""
🤖 TERRI+ IA — Total predial

La capa predial de Sesquilé registra:

{formato_numero(total[0]['total'])} predios.

Fuente:
PostGIS — public.predios_sesquile
"""

    # ===============================
    # CONSULTA: RESUMEN GENERAL
    # ===============================

    total_predios = ejecutar_sql("""
        SELECT COUNT(*) AS total
        FROM predios_sesquile;
    """)

    destinos = ejecutar_sql("""
        SELECT 
            COALESCE("DESTINO", 'Sin destino') AS destino,
            COUNT(*) AS total
        FROM predios_sesquile
        GROUP BY "DESTINO"
        ORDER BY total DESC
        LIMIT 5;
    """)

    avaluo = ejecutar_sql("""
        SELECT 
            SUM(
                NULLIF(
                    regexp_replace("AVALUO 2026", '[^0-9]', '', 'g'),
                    ''
                )::numeric
            ) AS total_avaluo_2026
        FROM predios_sesquile;
    """)

    texto_destinos = ""

    for item in destinos:
        texto_destinos += f"- {item['destino']}: {formato_numero(item['total'])} predios\n"

    return f"""
🤖 TERRI+ IA — Resumen predial de Sesquilé

🏠 Total de predios:
{formato_numero(total_predios[0]['total'])}

📊 Principales destinos:
{texto_destinos}

💰 Avalúo total 2026 aproximado:
{formato_pesos(avaluo[0]['total_avaluo_2026'])}

Puedes preguntarme, por ejemplo:
- ¿Cuántos predios tiene Sesquilé?
- Dame los destinos principales.
- ¿Cuál es el avalúo total?
- Muéstrame los predios con mayor avalúo.

Fuente:
PostGIS — public.predios_sesquile
"""