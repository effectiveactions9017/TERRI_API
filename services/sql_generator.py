# ============================================================
# TERRI+ CORE
# Generador inteligente de SQL PostgreSQL/PostGIS
# ============================================================

import re

from services.schema_service import obtener_esquema_base
from services.llm_service import obtener_cliente, obtener_modelo
from services.registry_manager import (
    generar_contexto_catalogo_unificado,
)
from services.knowledge_engine import (
    generar_contexto_conocimiento,
)
from services.semantic_scanner import (
    generar_contexto_semantico_automatico,
)


# ============================================================
# Respuesta segura por defecto
# ============================================================

SQL_RESPUESTA_SEGURA = (
    "SELECT "
    "'No puedo generar una consulta segura con el esquema disponible' "
    "AS respuesta;"
)


# ============================================================
# Limpiar respuesta del modelo
# ============================================================

def limpiar_sql_generado(respuesta: str) -> str:
    """
    Limpia posibles marcas Markdown o texto adicional
    devuelto accidentalmente por el modelo.
    """

    if not respuesta:
        return SQL_RESPUESTA_SEGURA

    sql = respuesta.strip()

    # Eliminar apertura de bloque Markdown.
    sql = re.sub(
        r"^```(?:sql)?\s*",
        "",
        sql,
        flags=re.IGNORECASE,
    )

    # Eliminar cierre de bloque Markdown.
    sql = re.sub(
        r"\s*```$",
        "",
        sql,
    )

    sql = sql.strip()

    # Buscar el inicio real de SELECT o WITH
    # si el modelo agregó texto antes de la consulta.
    coincidencia = re.search(
        r"\b(?:SELECT|WITH)\b",
        sql,
        flags=re.IGNORECASE,
    )

    if coincidencia:
        sql = sql[coincidencia.start():].strip()

    if not sql:
        return SQL_RESPUESTA_SEGURA

    # Garantizar cierre con punto y coma.
    if not sql.endswith(";"):
        sql += ";"

    return sql


# ============================================================
# Construir contexto TERRI+
# ============================================================

def construir_contexto_sql() -> str:
    """
    Construye el contexto combinado que utilizará GPT:

    1. Esquema físico real de PostgreSQL.
    2. Catálogo unificado de capas.
    3. Conocimiento semántico territorial manual.
    4. Conocimiento semántico inferido automáticamente.
    """

    # ========================================================
    # Esquema físico
    # ========================================================

    try:
        esquema = obtener_esquema_base()

    except Exception as error:

        print(
            "⚠️ No fue posible obtener el esquema base: "
            f"{error}"
        )

        esquema = (
            "No fue posible consultar el esquema físico."
        )

    # ========================================================
    # Catálogo unificado de capas
    # ========================================================

    try:
        contexto_capas = (
            generar_contexto_catalogo_unificado()
        )

    except Exception as error:

        print(
            "⚠️ No fue posible generar el contexto "
            f"unificado de capas: {error}"
        )

        contexto_capas = (
            "No fue posible consultar el catálogo "
            "unificado de capas."
        )

    # ========================================================
    # Conocimiento semántico manual
    # ========================================================

    try:
        contexto_conocimiento = (
            generar_contexto_conocimiento()
        )

    except Exception as error:

        print(
            "⚠️ No fue posible generar el contexto "
            f"semántico manual: {error}"
        )

        contexto_conocimiento = (
            "No fue posible consultar el conocimiento "
            "semántico territorial manual."
        )

    # ========================================================
    # Conocimiento semántico automático
    # ========================================================

    try:
        contexto_semantico_auto = (
            generar_contexto_semantico_automatico()
        )

    except Exception as error:

        print(
            "⚠️ No fue posible generar el contexto "
            f"semántico automático: {error}"
        )

        contexto_semantico_auto = (
            "No fue posible generar el conocimiento "
            "semántico automático."
        )

    return f"""
============================================================
ESQUEMA FÍSICO REAL DE POSTGRESQL
============================================================

{esquema}

============================================================
CATÁLOGO UNIFICADO DE CAPAS DISPONIBLES
============================================================

{contexto_capas}

============================================================
CONOCIMIENTO SEMÁNTICO TERRITORIAL MANUAL
============================================================

{contexto_conocimiento}

============================================================
CONOCIMIENTO SEMÁNTICO AUTOMÁTICO
============================================================

{contexto_semantico_auto}
""".strip()

# ============================================================
# CONSTRUIR CONTEXTO DEL PLAN TERRITORIAL
# ============================================================

def construir_contexto_plan(
    plan: dict | None,
) -> str:
    """
    Convierte el plan territorial en instrucciones estructuradas
    para el generador SQL.

    Cuando la visualización sea categórica, obliga a incluir
    en el SELECT el atributo solicitado por el usuario.
    """

    if not isinstance(plan, dict) or not plan:

        return (
            "No se proporcionó un plan territorial. "
            "Interpreta la pregunta usando el contexto disponible."
        )


    # ========================================================
    # INFORMACIÓN GENERAL DEL PLAN
    # ========================================================

    tipo_consulta = (
        plan.get("tipo_consulta")
        or "no definido"
    )

    tabla_principal = (
        plan.get("tabla_principal")
        or "no definida"
    )

    campo = (
        plan.get("campo")
        or "no definido"
    )

    criterio = (
        plan.get("criterio")
        or "no definido"
    )

    cantidad = plan.get("cantidad")

    cantidad_texto = (
        cantidad
        if cantidad is not None
        else "no definida"
    )

    requiere_geom = bool(
        plan.get("requiere_geom", False)
    )

    operacion_espacial = (
        plan.get("operacion_espacial")
        or "no definida"
    )

    distancia = (
        plan.get("distancia")
        or "no definida"
    )

    tema = (
        plan.get("tema")
        or "no definido"
    )


    # ========================================================
    # INFORMACIÓN DE VISUALIZACIÓN
    # ========================================================

    visualizacion = (
        plan.get("visualizacion")
        if isinstance(
            plan.get("visualizacion"),
            dict,
        )
        else {}
    )

    modo_visualizacion = (
        visualizacion.get("modo")
        or "simple"
    )

    campo_categoria = (
        visualizacion.get("campo_categoria")
        or "no definido"
    )

    campo_valor = (
        visualizacion.get("campo_valor")
        or "no definido"
    )

    expresion_campo = (
        visualizacion.get("expresion_campo")
        or "no definida"
    )

    mostrar_leyenda = bool(
        visualizacion.get(
            "mostrar_leyenda",
            False,
        )
    )

    titulo_leyenda = (
        visualizacion.get("titulo_leyenda")
        or "no definido"
    )


    # ========================================================
    # INSTRUCCIONES OBLIGATORIAS PARA EL SELECT
    # ========================================================

    instrucciones_obligatorias = []

    if requiere_geom:

        instrucciones_obligatorias.append(
            "- Incluye obligatoriamente la geometría real "
            "con el alias exacto geom."
        )

    if (
        modo_visualizacion == "categorico"
        and campo_categoria != "no definido"
    ):

        instrucciones_obligatorias.append(
            "- La visualización es categórica."
        )

        instrucciones_obligatorias.append(
            "- Incluye obligatoriamente en el SELECT el campo "
            f"categórico solicitado: {campo_categoria}."
        )

        instrucciones_obligatorias.append(
            "- El campo categórico debe conservarse en cada "
            "registro individual; no lo elimines del resultado."
        )

        instrucciones_obligatorias.append(
            "- No reemplaces el campo categórico por un conteo, "
            "salvo que la pregunta solicite explícitamente una "
            "tabla agregada."
        )

        instrucciones_obligatorias.append(
            "- Usa el nombre físico real de la columna según "
            "el esquema de la tabla."
        )

        instrucciones_obligatorias.append(
            "- Si el nombre físico requiere comillas dobles, "
            "utilízalas."
        )

        instrucciones_obligatorias.append(
            "- Puedes asignar un alias limpio en minúscula y "
            "snake_case, pero el alias debe coincidir con "
            f"{campo_categoria} siempre que sea posible."
        )

    if (
        modo_visualizacion == "graduado"
        and campo_valor != "no definido"
    ):

        instrucciones_obligatorias.append(
            "- La visualización es graduada."
        )

        instrucciones_obligatorias.append(
            "- Incluye obligatoriamente en el SELECT el campo "
            f"numérico solicitado: {campo_valor}."
        )

        instrucciones_obligatorias.append(
            "- Conserva el valor en cada registro individual "
            "para que el frontend pueda construir la escala."
        )

    if not instrucciones_obligatorias:

        instrucciones_obligatorias.append(
            "- No existen atributos adicionales obligatorios "
            "definidos por la visualización."
        )

    bloque_instrucciones = "\n".join(
        instrucciones_obligatorias
    )


    # ========================================================
    # CONTEXTO FINAL DEL PLAN
    # ========================================================

    return f"""
Tipo de consulta: {tipo_consulta}
Tabla principal: {tabla_principal}
Campo principal: {campo}
Criterio: {criterio}
Cantidad: {cantidad_texto}
Requiere geometría: {"sí" if requiere_geom else "no"}
Operación espacial: {operacion_espacial}
Distancia: {distancia}
Tema: {tema}

VISUALIZACIÓN SOLICITADA
Modo: {modo_visualizacion}
Campo categórico: {campo_categoria}
Campo de valor: {campo_valor}
Expresión natural del campo: {expresion_campo}
Mostrar leyenda: {"sí" if mostrar_leyenda else "no"}
Título de leyenda: {titulo_leyenda}

INSTRUCCIONES OBLIGATORIAS DEL PLAN
{bloque_instrucciones}
""".strip()

# ============================================================
# Generar SQL
# ============================================================

def generar_sql(
    pregunta: str,
    plan: dict | None = None
) -> str:
    """
    Genera una consulta SQL PostgreSQL/PostGIS a partir
    de una pregunta en lenguaje natural.

    Parámetros
    ----------
    pregunta : str
        Pregunta del usuario.

    plan : dict | None, opcional
        Plan territorial generado previamente por el Planner.

    La función únicamente genera SQL.
    No ejecuta consultas.
    """

    if not isinstance(pregunta, str):
        return SQL_RESPUESTA_SEGURA

    pregunta = pregunta.strip()

    if not pregunta:
        return SQL_RESPUESTA_SEGURA

    contexto = construir_contexto_sql()
    contexto_plan = construir_contexto_plan(plan)

    client = obtener_cliente()
    model = obtener_modelo()

    prompt = f"""
Eres TERRI+, el motor experto en generación de consultas
SQL para una plataforma de inteligencia territorial.

Tu tarea es convertir la pregunta del usuario en UNA consulta
segura para PostgreSQL/PostGIS.

============================================================
REGLAS DE SALIDA
============================================================

1. Devuelve únicamente SQL.
2. No expliques el resultado.
3. No uses Markdown.
4. No uses bloques ```sql.
5. Genera una sola sentencia.
6. La sentencia debe comenzar con SELECT o WITH.
7. Termina la consulta con punto y coma.

Si la solicitud no se puede responder con las tablas y campos
disponibles, devuelve exactamente:

{SQL_RESPUESTA_SEGURA}

============================================================
REGLAS DE SEGURIDAD
============================================================

1. Solo puedes generar consultas SELECT o WITH que finalicen
   en un SELECT.
2. Nunca generes INSERT, UPDATE, DELETE, DROP, ALTER,
   TRUNCATE, CREATE, GRANT, REVOKE, COPY o CALL.
3. Usa exclusivamente tablas y columnas existentes en el
   esquema proporcionado.
4. No inventes nombres de tablas o columnas.
5. No consultes catálogos internos salvo que la pregunta
   solicite explícitamente metadatos.
6. No uses SELECT *.
7. Cuando un campo tenga espacios, mayúsculas o caracteres
   especiales, escribe su nombre entre comillas dobles.
8. Si una capa fue descubierta automáticamente y no tiene
   conocimiento semántico manual, utiliza su esquema físico
   y su conocimiento semántico automático.
9. Los valores frecuentes incluidos en el contexto representan
   valores reales existentes en la base de datos.
10. No inventes valores categóricos que no aparezcan en el
    contexto o en la pregunta del usuario.

============================================================
PRIORIDAD DEL CONOCIMIENTO
============================================================

Utiliza esta prioridad al interpretar los campos:

1. Esquema físico real de PostgreSQL.
2. Conocimiento semántico manual.
3. Conocimiento semántico automático.
4. Nombre físico del campo.

El conocimiento manual puede complementar o corregir la
inferencia automática.

La inferencia automática permite trabajar con capas nuevas
aunque todavía no tengan reglas manuales específicas.

# ============================================================
# USO DEL CONOCIMIENTO SEMÁNTICO AUTOMÁTICO
# ============================================================
============================================================
USO DEL CONOCIMIENTO SEMÁNTICO AUTOMÁTICO
============================================================

1. Un campo inferido como "categoria" puede usarse para:
   - filtros;
   - agrupaciones;
   - conteos;
   - porcentajes;
   - mapas temáticos.
2. Un campo inferido como "nombre" puede usarse para:
   - búsqueda;
   - filtros de texto;
   - identificación en resultados y popups.
3. Un campo inferido como "identificador_persona" puede usarse
   para búsquedas exactas o parciales.
4. Un campo inferido como "direccion" puede usarse para
   búsqueda e identificación.
5. Un campo inferido como "geometria" debe incluirse cuando
   la pregunta solicite mostrar, ubicar o mapear resultados.
6. Usa los valores frecuentes reales para interpretar
   expresiones del usuario.

Ejemplo:

Si el contexto indica:

tipo_contribuyente:
- Persona Natural
- Persona Jurídica

y el usuario pide personas jurídicas, utiliza el valor real:

tipo_contribuyente = 'Persona Jurídica'

============================================================
COMPARACIONES DE TEXTO
============================================================

1. Para comparar valores categóricos cuando existan
   inconsistencias de mayúsculas y minúsculas, utiliza UPPER
   o LOWER.
2. Ejemplo:

UPPER(estado) = 'ACTIVO'

3. Para búsquedas por nombre, razón social, documento o
   dirección, utiliza ILIKE cuando corresponda.
4. Para coincidencias parciales utiliza:

campo ILIKE '%texto%'

5. Para valores categóricos conocidos y exactos, puede usarse
   igualdad directa.
6. No conviertas identificadores personales a números, porque
   pueden contener ceros iniciales o caracteres especiales.

============================================================
CAMPOS VACÍOS O SIN INFORMACIÓN
============================================================

1. Si el conocimiento automático muestra cero valores no nulos
   o no presenta valores frecuentes en un campo categórico,
   no lo utilices para responder una pregunta salvo que el
   usuario lo solicite explícitamente.
2. No asumas que un campo vacío contiene información.
3. Prefiere campos con valores reales disponibles.
4. Si no existe información suficiente, devuelve la consulta
   segura por defecto.

============================================================
CAMPOS NUMÉRICOS ALMACENADOS COMO TEXTO
============================================================

1. Algunos campos están almacenados físicamente como texto.
2. Para sumar, promediar, comparar, ordenar o filtrar
   numéricamente esos campos, utiliza la EXPRESIÓN SQL
   definida en el conocimiento semántico manual.
3. No ordenes avalúos o áreas directamente como texto.
4. Usa NULLS LAST al ordenar campos convertidos que puedan
   contener valores vacíos.
5. Asigna alias limpios a los valores convertidos.
6. No modifiques la expresión SQL configurada en el
   conocimiento semántico salvo que sea necesario añadir
   un alias de tabla.

Ejemplo conceptual:

EXPRESIÓN_CONFIGURADA AS avaluo_2026

============================================================
CONSULTAS DE MAPA
============================================================

Considera que la pregunta requiere un resultado espacial cuando
el usuario emplee expresiones como:

- mostrar
- dibujar
- visualizar
- mapear
- ubicar
- localizar
- resaltar
- ver en el mapa
- cargar al visor
- representar espacialmente
- dónde están
- dónde se encuentran

También incluye geometría cuando la consulta identifica
elementos territoriales individuales, por ejemplo:

- el predio de mayor avalúo;
- los cinco predios más grandes;
- las construcciones más altas;
- los contribuyentes buscados;
- los elementos más cercanos;
- un ranking de objetos territoriales;
- un listado de entidades concretas.

En estos casos:

1. Incluye la geometría real.

2. La geometría debe salir con el alias exacto geom.

3. No uses ST_AsGeoJSON; el backend realizará la conversión.

4. Incluye entre 5 y 12 atributos útiles para identificación
   y popup.

5. Usa alias en minúscula y snake_case.

6. No incluyas datos innecesarios.

7. Cuando el usuario solicite mostrar, visualizar, mapear,
   ubicar, localizar, dibujar, representar o cargar elementos
   en el visor, devuelve TODOS los resultados que cumplan los
   filtros de la consulta.

8. No agregues LIMIT 100 automáticamente a las consultas
   espaciales.

9. Si el usuario indica una cantidad concreta, respeta
   exactamente esa cantidad.

10. Si el usuario solicita un ranking, utiliza la cantidad
    indicada en la pregunta.

11. Si el usuario solicita un único elemento, utiliza LIMIT 1.

12. Expresiones como las siguientes implican devolver todos
    los resultados:

    - todos;
    - todas;
    - muéstralos;
    - muéstralas;
    - verlos en el mapa;
    - verlas en el mapa;
    - mostrar los resultados;
    - cargar los resultados;
    - visualizar los elementos.

13. No interpretes la ausencia de una cantidad como una
    solicitud de muestra.

14. Solo utiliza LIMIT cuando:

    - el usuario indique explícitamente una cantidad;
    - la consulta sea un ranking con una cantidad definida;
    - la solicitud busque un único elemento;
    - el plan territorial proporcione una cantidad concreta.

15. Si el usuario no define una cantidad y solicita una
    visualización espacial, no utilices LIMIT.

16. Si el campo geométrico real no se llama geom, usa:

    nombre_campo_geometrico AS geom.

17. Cuando combines varias capas y el resultado sea espacial,
    incluye una sola geometría final con alias geom.

# ============================================================
# MAPAS DE PREDIOS Y CAPAS PREDIALES
# ============================================================

Cuando el resultado espacial utilice una capa predial, identifica
primero qué tabla está siendo utilizada antes de seleccionar los
atributos.

A. SI LA TABLA ES:

predios_sesquile

incluye, cuando existan y sean pertinentes:

- id
- codigo
- "NUMERO_PREDIAL" AS numero_predial
- "DESTINO" AS destino
- "NOMBRE" AS nombre
- "NUMERO_DOCUMENTO" AS documento
- "DIRECCION" AS direccion

Para el área utiliza la expresión configurada para:

"AREA DE TERRENO"

según el conocimiento semántico manual.

Para el avalúo utiliza la expresión configurada para:

"AVALUO 2026"

según el conocimiento semántico manual.

Incluye:

geom AS geom


B. SI LA TABLA ES:

destino_economico_sesquile

incluye, cuando existan y sean pertinentes:

- id
- codigo
- "NUMERO_PREDIAL" AS numero_predial
- "DESTINO" AS destino

El campo físico real del área NO es:

"AREA DE TERRENO"

El campo correcto es:

"AREA.DE.TERRENO"

Cuando necesites ordenar, comparar, sumar,
promediar o filtrar por área utiliza exactamente:

NULLIF(
    REGEXP_REPLACE(
        COALESCE("AREA.DE.TERRENO"::text, ''),
        '[^0-9,.]',
        '',
        'g'
    ),
    ''
)::numeric

AS area_terreno

Nunca reemplaces el nombre físico de la columna.

No conviertas automáticamente:

"AREA.DE.TERRENO"

en

"AREA DE TERRENO"

porque son columnas distintas.

Incluye:

geom AS geom


Reglas obligatorias:

1. Antes de generar SQL identifica la tabla utilizada.

2. Utiliza los nombres físicos reales de esa tabla.

3. Nunca reutilices nombres de columnas de otra capa.

4. Si dos tablas poseen atributos equivalentes,
   utiliza SIEMPRE los nombres físicos propios de
   la tabla seleccionada.

5. No inventes columnas.

6. Si el esquema físico indica un nombre con puntos,
   utiliza exactamente ese nombre entre comillas dobles.

Ejemplo válido:

"AREA.DE.TERRENO"

Ejemplo incorrecto:

"AREA DE TERRENO"
============================================================
MAPAS DE CONSTRUCCIONES
============================================================

Cuando el resultado espacial utilice construcciones, incluye,
cuando existan y sean pertinentes:

- id
- id_0
- const_year AS anio_construccion
- altura_m AS altura_metros
- area_in_me AS area_m2
- longitude AS longitud
- latitude AS latitud
- confidence AS confianza
- geom AS geom

No inventes atributos que no existan físicamente en la tabla.

============================================================
MAPAS DE CONTRIBUYENTES ICA
============================================================

Cuando el resultado espacial utilice contribuyentes ICA,
incluye, cuando existan y sean pertinentes:

- id
- tipo_documento
- numero_documento
- nombre_contribuyente
- razon_social
- naturaleza_juridica
- direccion
- estado
- tipo_contribuyente
- direccion_formateada
- geom AS geom

Reglas específicas:

1. Para persona natural utiliza el valor real:

   'Persona Natural'.

2. Para persona jurídica utiliza el valor real:

   'Persona Jurídica'.

3. Para contribuyentes activos utiliza una comparación que
   ignore mayúsculas:

   UPPER(estado) = 'ACTIVO'

4. Para buscar una persona o empresa utiliza ILIKE sobre:

   - nombre_contribuyente;
   - razon_social.

5. Para buscar por cédula o NIT utiliza:

   numero_documento.

6. No utilices regimen_tributario como criterio principal
   mientras el campo no contenga información.

7. Si el usuario solicita mostrar, visualizar, ubicar o mapear
   contribuyentes, incluye geom.

8. Cuando la solicitud sea espacial, devuelve todos los
   contribuyentes que cumplan los filtros establecidos.

9. No utilices LIMIT 100 automáticamente en mapas de
   contribuyentes.

10. Si existen 300, 643, 1000 o más contribuyentes que cumplen
    la condición, devuelve el conjunto completo, salvo que el
    usuario indique expresamente una cantidad diferente.

11. Si el usuario solicita una cantidad concreta, utiliza
    exactamente esa cantidad.

12. Si solicita los primeros, mayores, menores o un ranking,
    utiliza ORDER BY y el LIMIT solicitado.

13. Si no indica una cantidad y pide mostrarlos en el mapa,
    no utilices LIMIT.

============================================================
CONSULTAS TABULARES, CATEGORÍAS Y ESTADÍSTICAS
============================================================

1. Si el usuario solicita conteos, sumas, promedios,
   porcentajes o resúmenes, no incluyas geometría salvo que
   también solicite un mapa.

2. Para conteos utiliza COUNT(*) con un alias descriptivo.

3. Para agrupaciones utiliza alias comprensibles.

4. Ordena los resultados cuando facilite su interpretación.

5. Evita LIMIT en un único resultado agregado.

6. En listados tabulares, devuelve todos los registros que
   cumplan los filtros cuando el usuario no indique una
   cantidad específica.

7. No agregues LIMIT 100 automáticamente a los listados
   tabulares.

8. Si el usuario solicita una cantidad concreta, utiliza
   exactamente esa cantidad.

9. Si la consulta corresponde a un ranking, utiliza ORDER BY
   y el LIMIT solicitado por el usuario.

10. Si el usuario pide un único registro, utiliza LIMIT 1.

11. Para porcentajes, evita divisiones enteras y utiliza
    conversión decimal cuando sea necesario.

12. Para evitar división por cero, utiliza NULLIF cuando
    corresponda.

13. Cuando agrupes valores de texto con diferencias únicamente
    de mayúsculas o minúsculas, normalízalos con UPPER, LOWER
    o INITCAP.

14. Las consultas agrupadas deben devolver todas las categorías
    o unidades territoriales resultantes, salvo que el usuario
    solicite expresamente las primeras, las últimas, las mayores
    o las menores.

15. No limites los resultados necesarios para exportaciones,
    mapas de calor, simbología temática, agrupaciones,
    estadísticas o cruces espaciales.

16. Interpreta las siguientes expresiones como una solicitud
    para conocer los valores o categorías existentes de un
    campo:

    - qué categorías hay;
    - cuáles categorías existen;
    - qué tipos hay;
    - cuáles tipos existen;
    - qué clases hay;
    - cuáles clases existen;
    - qué valores hay;
    - cuáles valores existen;
    - qué destinos hay;
    - cuáles destinos existen;
    - qué usos hay;
    - cuáles usos existen;
    - qué opciones hay;
    - cómo se clasifican;
    - categorías por;
    - tipos por;
    - clases por.

17. Cuando el usuario solicite conocer qué categorías, tipos,
    clases, destinos, usos o valores existen, genera una
    consulta agrupada que incluya:

    - el campo categórico;
    - COUNT(*) AS cantidad;
    - GROUP BY sobre el campo categórico;
    - ORDER BY cantidad DESC.

18. Excluye categorías vacías o nulas usando:

    campo IS NOT NULL
    AND TRIM(campo::text) <> ''

19. No utilices SELECT DISTINCT únicamente cuando sea útil
    conocer también cuántos registros pertenecen a cada
    categoría. En ese caso utiliza GROUP BY y COUNT(*).

20. Utiliza SELECT DISTINCT solamente cuando el usuario pida
    explícitamente una lista de valores sin cantidades, por
    ejemplo:

    - lista las categorías;
    - dame únicamente los tipos;
    - muéstrame los valores diferentes;
    - cuáles son los nombres distintos.

21. Para preguntas sobre categorías por destino económico en
    la tabla predios_sesquile, utiliza el campo físico:

    "DESTINO"

22. La pregunta:

    ¿Qué categorías por destino económico hay?

    debe interpretarse como:

    SELECT
        "DESTINO" AS destino_economico,
        COUNT(*) AS cantidad
    FROM predios_sesquile
    WHERE "DESTINO" IS NOT NULL
      AND TRIM("DESTINO") <> ''
    GROUP BY "DESTINO"
    ORDER BY cantidad DESC;

23. No incluyas geom en preguntas destinadas únicamente a
    conocer categorías, tipos, clases o distribuciones, salvo
    que el usuario también solicite verlas en el mapa.

24. Si el usuario pregunta cuántos registros existen por una
    categoría, agrupa por el campo categórico y devuelve el
    conteo de cada grupo.

25. Si el usuario pregunta únicamente cuántas categorías
    diferentes existen, utiliza:

    COUNT(DISTINCT campo)

26. Distingue entre estas intenciones:

    A. "¿Qué categorías hay?"
       Devuelve cada categoría y su cantidad.

    B. "¿Cuántas categorías hay?"
       Devuelve el número de categorías diferentes.

    C. "Lista las categorías"
       Puede devolver únicamente los valores distintos.

    D. "¿Cuántos predios hay por categoría?"
       Devuelve la categoría y COUNT(*) por cada grupo.
============================================================
MÁXIMOS, MÍNIMOS Y RANKINGS
============================================================

1. Para "mayor", "más grande", "más costoso", "más alto" o
   equivalentes, usa ORDER BY ... DESC NULLS LAST.
2. Para "menor", "más pequeño", "más barato" o equivalentes,
   usa ORDER BY ... ASC NULLS LAST.
3. Si el usuario pide un solo elemento, usa LIMIT 1.
4. Si pide los cinco, diez u otra cantidad, usa el límite
   solicitado.
5. Incluye geometría cuando el resultado represente objetos
   territoriales identificables.
6. Cuando ordenes por una expresión calculada, puedes repetir
   la expresión en ORDER BY o utilizar su alias cuando
   PostgreSQL lo permita.

============================================================
CONSULTAS MULTICAPA
============================================================

1. Cuando una pregunta requiera relacionar dos capas, identifica
   claramente qué tabla aporta la geometría final.
2. Utiliza JOIN espacial con ST_Intersects, ST_Within,
   ST_Contains o ST_DWithin según la intención.
3. Evita productos cartesianos sin condición de relación.
4. Si existe riesgo de duplicar entidades por múltiples
   coincidencias espaciales, utiliza DISTINCT o una agregación
   apropiada.
5. Para contar entidades únicas, utiliza COUNT(DISTINCT ...).
6. Para consultas de cercanía en SRID 4326, utiliza geography
   cuando la distancia solicitada esté expresada en metros.
7. Mantén alias limpios para atributos procedentes de distintas
   capas.
8. No combines capas si la pregunta puede responderse con una
   sola capa.
9. En relaciones entre puntos y polígonos utiliza, según la
   pregunta:
   - ST_Within;
   - ST_Contains;
   - ST_Intersects.
10. Para cercanía entre contribuyentes y predios puede usarse:

ST_DWithin(
    contribuyente.geom::geography,
    predio.geom::geography,
    distancia_metros
)

============================================================
CONTEXTO DISPONIBLE
============================================================

{contexto}

============================================================
PLAN TERRITORIAL
============================================================

{contexto_plan}

El plan territorial orienta la generación de la consulta.

No inventes tablas, campos, cantidades ni operaciones que
contradigan el plan.

============================================================
PREGUNTA DEL USUARIO
============================================================

{pregunta}

============================================================
RESPUESTA
============================================================

Devuelve únicamente la consulta SQL.
"""

    respuesta = client.responses.create(
        model=model,
        input=prompt,
    )

    return limpiar_sql_generado(
        respuesta.output_text
    )