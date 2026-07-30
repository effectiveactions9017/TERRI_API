from database import ejecutar_sql


def formato_numero(valor):
    if valor is None:
        return "0"
    return f"{int(valor):,}".replace(",", ".")


def analizar_construcciones(pregunta):

    total = ejecutar_sql("""
        SELECT COUNT(*) AS total
        FROM construcciones_sesquile;
    """)

    area = ejecutar_sql("""
        SELECT AVG(area_in_me) AS promedio
        FROM construcciones_sesquile;
    """)

    altura = ejecutar_sql("""
        SELECT MAX(altura_m) AS maxima
        FROM construcciones_sesquile;
    """)

    anios = ejecutar_sql("""
        SELECT const_year, COUNT(*) AS total
        FROM construcciones_sesquile
        WHERE const_year IS NOT NULL
        GROUP BY const_year
        ORDER BY total DESC
        LIMIT 5;
    """)

    confianza = ejecutar_sql("""
        SELECT AVG(confidence) AS promedio
        FROM construcciones_sesquile;
    """)

    texto_anios = ""

    for fila in anios:
        texto_anios += (
            f"- Año {fila['const_year']}: "
            f"{formato_numero(fila['total'])} construcciones\n"
        )

    return f"""
🤖 TERRI+ IA — Análisis de construcciones

🏗️ Total de construcciones detectadas:
{formato_numero(total[0]['total'])}

📐 Área promedio detectada:
{round(area[0]['promedio'], 2)} m²

🏢 Altura máxima registrada:
{round(altura[0]['maxima'], 2)} metros

📅 Años con mayor número de construcciones:
{texto_anios}

🎯 Confianza promedio del modelo:
{round(confianza[0]['promedio'], 2)}

Fuente:
PostGIS — public.construcciones_sesquile
"""