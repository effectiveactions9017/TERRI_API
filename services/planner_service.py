# ============================================================
# TERRI+
# Planner Service
# Motor inicial de planificación territorial
# ============================================================

import re
import unicodedata
from typing import Optional, Tuple


# ============================================================
# TIPOS DE CONSULTA DISPONIBLES
# ============================================================

TIPOS_CONSULTA = [
    "ranking",
    "conteo",
    "listado",
    "estadistica",
    "espacial",
    "proximidad",
    "comparacion",
]


# ============================================================
# NORMALIZAR TEXTO
# ============================================================

def normalizar_texto(texto: str) -> str:
    """
    Convierte el texto a minúsculas, elimina tildes
    y normaliza espacios.
    """

    if not isinstance(texto, str):
        return ""

    texto = texto.strip().lower()

    texto = unicodedata.normalize(
        "NFD",
        texto,
    )

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto


# ============================================================
# NORMALIZAR IDENTIFICADOR DE CAMPO
# ============================================================

def normalizar_identificador_campo(
    nombre: str,
) -> Optional[str]:
    """
    Convierte una expresión natural en un identificador
    comparable con columnas SQL y propiedades GeoJSON.

    Ejemplos:
    - nivel de riesgo -> nivel_riesgo
    - categoría de vigencia -> categoria_vigencia
    - área construida -> area_construida
    """

    if not isinstance(nombre, str):
        return None

    nombre_normalizado = normalizar_texto(nombre)

    if not nombre_normalizado:
        return None

    palabras_omitidas = {
        "de",
        "del",
        "la",
        "el",
        "los",
        "las",
        "un",
        "una",
    }

    palabras = [
        palabra
        for palabra in re.findall(
            r"[a-z0-9]+",
            nombre_normalizado,
        )
        if palabra not in palabras_omitidas
    ]

    if not palabras:
        return None

    return "_".join(palabras)


# ============================================================
# CREAR PLAN VACÍO
# ============================================================

def crear_plan() -> dict:
    """
    Crea la estructura base del plan territorial.
    """

    return {
        "tipo_consulta": None,
        "tabla_principal": None,
        "tabla_secundaria": None,
        "requiere_join": False,
        "requiere_geom": False,
        "cantidad": None,
        "criterio": None,
        "campo": None,
        "distancia": None,
        "unidad_distancia": None,
        "operacion_espacial": None,
        "tema": None,
        "visualizacion": {
            "modo": "simple",
            "campo_categoria": None,
            "campo_valor": None,
            "expresion_campo": None,
            "mostrar_leyenda": False,
            "titulo_leyenda": None,
        },
        "capas_consulta": [],
        "pregunta_original": None,
    }


# ============================================================
# DETECTAR TIPO DE CONSULTA
# ============================================================

def detectar_tipo_consulta(texto: str) -> str:
    """
    Clasifica la intención general de la consulta.
    """

    texto_normalizado = normalizar_texto(texto)

    expresiones_proximidad = [
        "cerca de",
        "cercano a",
        "cercanos a",
        "proximo a",
        "proximos a",
        "a menos de",
        "a una distancia de",
        "metros de",
        "kilometros de",
    ]

    if any(
        expresion in texto_normalizado
        for expresion in expresiones_proximidad
    ):
        return "proximidad"

    expresiones_comparacion = [
        "comparar",
        "compara",
        "comparacion",
        "diferencia entre",
        "frente a",
        "versus",
    ]

    if any(
        expresion in texto_normalizado
        for expresion in expresiones_comparacion
    ):
        return "comparacion"

    expresiones_ranking = [
        "mayor",
        "menor",
        "mas grande",
        "mas grandes",
        "mas pequeno",
        "mas pequenos",
        "top",
        "primero",
        "primer",
        "segundo",
        "tercero",
        "superior",
        "inferior",
    ]

    if any(
        expresion in texto_normalizado
        for expresion in expresiones_ranking
    ):
        return "ranking"

    expresiones_conteo = [
        "cuantos",
        "cuantas",
        "cantidad de",
        "numero de",
        "total de",
    ]

    if any(
        expresion in texto_normalizado
        for expresion in expresiones_conteo
    ):
        return "conteo"

    expresiones_estadistica = [
        "promedio",
        "media",
        "minimo",
        "maximo",
        "suma",
        "sumatoria",
        "mediana",
    ]

    if any(
        expresion in texto_normalizado
        for expresion in expresiones_estadistica
    ):
        return "estadistica"

    expresiones_espaciales = [
        "intersecta",
        "intersectan",
        "dentro de",
        "contiene",
        "contienen",
        "cruza",
        "cruzan",
        "superpone",
        "superponen",
        "buffer",
    ]

    if any(
        expresion in texto_normalizado
        for expresion in expresiones_espaciales
    ):
        return "espacial"

    return "listado"


# ============================================================
# DETECTAR CANTIDAD
# ============================================================

def detectar_cantidad(texto: str) -> Optional[int]:
    """
    Detecta únicamente una cantidad explícita de resultados.

    Ejemplos válidos:
    - Muéstrame 5 predios
    - Dame los 10 predios con mayor avalúo
    - Lista 20 contribuyentes
    - Top 15 predios

    Ejemplos que NO deben tomarse como cantidad:
    - Predios con menos de 5 años
    - Predios a 300 metros
    - Avalúo mayor a 100 millones
    - Cartera de 3 vigencias
    """

    texto_normalizado = normalizar_texto(texto)

    if not texto_normalizado:
        return None

    if re.search(
        r"\b(todos|todas|todo|toda|sin limite|completo|completa)\b",
        texto_normalizado,
    ):
        return None

    patrones_numericos = [
        (
            r"\b(?:muestrame|muestra|mostrar|dame|lista|listar|"
            r"consulta|consultar)\s+(?:los|las)?\s*(\d+)\s+"
            r"(?:predios?|parcelas?|registros?|resultados?|"
            r"contribuyentes?|construcciones?)\b"
        ),
        (
            r"\b(?:los|las)\s+(\d+)\s+"
            r"(?:predios?|parcelas?|registros?|resultados?|"
            r"contribuyentes?|construcciones?)\b"
        ),
        r"\b(?:top|primeros?|primeras?)\s+(\d+)\b",
    ]

    for patron in patrones_numericos:
        coincidencia = re.search(
            patron,
            texto_normalizado,
        )

        if coincidencia:
            return int(coincidencia.group(1))

    cantidades_texto = {
        "un": 1,
        "uno": 1,
        "una": 1,
        "dos": 2,
        "tres": 3,
        "cuatro": 4,
        "cinco": 5,
        "seis": 6,
        "siete": 7,
        "ocho": 8,
        "nueve": 9,
        "diez": 10,
    }

    objetos = (
        r"predios?|parcelas?|registros?|resultados?|"
        r"contribuyentes?|construcciones?"
    )

    for palabra, cantidad in cantidades_texto.items():
        patrones_texto = [
            (
                rf"\b(?:muestrame|muestra|mostrar|dame|lista|listar)\s+"
                rf"(?:los|las)?\s*{palabra}\s+(?:{objetos})\b"
            ),
            rf"\b(?:los|las)\s+{palabra}\s+(?:{objetos})\b",
        ]

        for patron in patrones_texto:
            if re.search(
                patron,
                texto_normalizado,
            ):
                return cantidad

    return None


# ============================================================
# DETECTAR SI NECESITA GEOMETRÍA
# ============================================================

def detectar_geom(texto: str) -> bool:
    """
    Determina si la respuesta debe incluir geometría
    para ser dibujada en el mapa.
    """

    texto_normalizado = normalizar_texto(texto)

    palabras_mapa = [
        "mapa",
        "mostrar",
        "muestrame",
        "muestra",
        "ver",
        "dibuja",
        "dibujame",
        "ubica",
        "ubicar",
        "localiza",
        "localizar",
        "resalta",
        "representa",
        "colores",
        "clasifica",
        "clasificados",
        "clasificadas",
        "diferencia",
        "diferenciados",
        "diferenciadas",
    ]

    return any(
        palabra in texto_normalizado
        for palabra in palabras_mapa
    )


# ============================================================
# DETECTAR TABLA PRINCIPAL
# ============================================================

def detectar_tabla_principal(texto: str) -> Optional[str]:
    """
    Selecciona la capa principal según el tema territorial.
    """

    texto_normalizado = normalizar_texto(texto)

    reglas_tablas = [
        {
            "tabla": "placa_huellas_sesquile",
            "terminos": [
                "placa huella",
                "placas huella",
                "placa-huella",
                "vias rurales",
                "via rural",
            ],
        },
        {
            "tabla": "contribuyentes_ica_sesquile",
            "terminos": [
                "contribuyente",
                "contribuyentes",
                "ica",
                "persona juridica",
                "persona natural",
                "razon social",
                "establecimiento comercial",
            ],
        },
        {
            "tabla": "construcciones_sesquile",
            "terminos": [
                "construccion",
                "construcciones",
                "area construida",
                "edificacion",
                "edificaciones",
            ],
        },
        {
            "tabla": "destino_economico_sesquile",
            "terminos": [
                "destino economico",
                "uso economico",
                "predio comercial",
                "predios comerciales",
                "comercial",
                "industrial",
                "agropecuario",
                "residencial",
                "habitacional",
            ],
        },
        {
            "tabla": "predios_sesquile",
            "terminos": [
                "predio",
                "predios",
                "propietario",
                "propietarios",
                "avaluo",
                "numero predial",
                "codigo catastral",
                "area de terreno",
            ],
        },
    ]

    for regla in reglas_tablas:
        if any(
            termino in texto_normalizado
            for termino in regla["terminos"]
        ):
            return regla["tabla"]

    return None


# ============================================================
# DETECTAR CAMPO PRINCIPAL
# ============================================================

def detectar_campo(
    texto: str,
    tabla_principal: Optional[str],
) -> Optional[str]:
    """
    Detecta el atributo sobre el que se realizará
    el ranking, estadística o filtro principal.

    Este detector se reserva para campos frecuentes usados
    en ordenamientos y cálculos. La visualización usa además
    un extractor genérico independiente.
    """

    texto_normalizado = normalizar_texto(texto)

    if any(
        termino in texto_normalizado
        for termino in [
            "area de terreno",
            "area terreno",
            "tamano",
            "superficie",
            "extension",
            "mas grande",
            "mas grandes",
            "mas pequeno",
            "mas pequenos",
        ]
    ):
        if tabla_principal == "destino_economico_sesquile":
            return "AREA.DE.TERRENO"

        if tabla_principal == "predios_sesquile":
            return "AREA DE TERRENO"

        return "area"

    if any(
        termino in texto_normalizado
        for termino in [
            "area construida",
            "construido",
            "construida",
        ]
    ):
        return "AREA CONSTRUIDA"

    if any(
        termino in texto_normalizado
        for termino in [
            "avaluo 2026",
            "valor 2026",
        ]
    ):
        return "AVALUO 2026"

    if any(
        termino in texto_normalizado
        for termino in [
            "avaluo 2025",
            "valor 2025",
        ]
    ):
        return "AVALUO 2025"

    if "avaluo" in texto_normalizado:
        return "AVALUO 2026"

    return None


# ============================================================
# EXTRAER CAMPO SOLICITADO PARA VISUALIZACIÓN
# ============================================================

def extraer_campo_visualizacion(
    texto: str,
) -> Optional[str]:
    """
    Extrae de manera genérica el atributo solicitado
    para representar, categorizar o graduar un mapa.

    Ejemplos reconocidos:
    - categorizados por R1
    - clasificados por estado de pago
    - agrupados por vereda
    - diferenciados por destino
    - pintados por actividad económica
    - coloreados según el nivel de riesgo
    - por tipo de contribuyente
    - según el avalúo
    """

    texto_normalizado = normalizar_texto(texto)

    if not texto_normalizado:
        return None

    # --------------------------------------------------------
    # Patrones explícitos de clasificación o agrupación
    # --------------------------------------------------------

    patrones = [
        (
            r"\b(?:categoriza|categorizar|categorizado|categorizada|"
            r"categorizados|categorizadas|clasifica|clasificar|"
            r"clasificado|clasificada|clasificados|clasificadas|"
            r"agrupa|agrupar|agrupado|agrupada|agrupados|agrupadas|"
            r"discrimina|discriminar|discriminado|discriminada|"
            r"discriminados|discriminadas|diferencia|diferenciar|"
            r"diferenciado|diferenciada|diferenciados|diferenciadas|"
            r"segmenta|segmentar|segmentado|segmentada|"
            r"segmentados|segmentadas|separa|separar|"
            r"separado|separada|separados|separadas)"
            r"\s+(?:los|las|el|la)?\s*"
            r"(?:predios?|parcelas?|registros?|resultados?|"
            r"contribuyentes?|construcciones?|elementos?|objetos?)?"
            r"\s*por\s+"
            r"(.+?)"
            r"(?=\s+(?:con|usando|mediante)\s+"
            r"(?:colores|color|una escala|un gradiente)|$)"
        ),
        (
            r"\b(?:categorizados?|categorizadas?|clasificados?|"
            r"clasificadas?|agrupados?|agrupadas?|discriminados?|"
            r"discriminadas?|diferenciados?|diferenciadas?|"
            r"segmentados?|segmentadas?|separados?|separadas?)"
            r"\s+por\s+"
            r"(.+?)"
            r"(?=\s+(?:con|usando|mediante)\s+"
            r"(?:colores|color|una escala|un gradiente)|$)"
        ),
        (
            r"\b(?:pinta|pintar|pintados?|pintadas?|colorea|colorear|"
            r"coloreados?|coloreadas?|representa|representar|"
            r"representados?|representadas?|simboliza|simbolizar|"
            r"simbolizados?|simbolizadas?)"
            r"\s+(?:los|las|el|la)?\s*"
            r"(?:predios?|parcelas?|registros?|resultados?|"
            r"contribuyentes?|construcciones?|elementos?|objetos?)?"
            r"\s*(?:por|segun)\s+"
            r"(.+?)"
            r"(?=\s+(?:con|usando|mediante)\s+"
            r"(?:colores|color|una escala|un gradiente)|$)"
        ),
        (
            r"\bsegun\s+(?:el|la|los|las)?\s*"
            r"(.+?)"
            r"(?=\s+(?:con|usando|mediante)\s+"
            r"(?:colores|color|una escala|un gradiente)|$)"
        ),
        (
            r"\bpor\s+"
            r"(.+?)"
            r"(?=\s+(?:con|usando|mediante)\s+"
            r"(?:colores|color|una escala|un gradiente)|$)"
        ),
    ]

    expresion = None

    for patron in patrones:
        coincidencia = re.search(
            patron,
            texto_normalizado,
        )

        if coincidencia:
            expresion = coincidencia.group(1).strip()
            break

    if not expresion:
        return None

    # --------------------------------------------------------
    # Limpiar instrucciones cartográficas posteriores
    # --------------------------------------------------------

    expresion = re.sub(
        (
            r"\s+(?:y|e)\s+"
            r"(?:diferencialos|diferencialas|diferenciados|"
            r"diferenciadas|representalos|representalas|"
            r"muestralos|muestralas|pintalos|pintalas|"
            r"colorealos|colorealas)\b.*$"
        ),
        "",
        expresion,
    ).strip()

    expresion = re.sub(
        (
            r"\s+(?:con|usando|mediante)\s+"
            r"(?:colores|color|una escala de colores|"
            r"un gradiente|rangos|simbolos)\b.*$"
        ),
        "",
        expresion,
    ).strip()

    # --------------------------------------------------------
    # Eliminar signos de puntuación finales
    # --------------------------------------------------------

    expresion = re.sub(
        r"[\s.,;:!?]+$",
        "",
        expresion,
    ).strip()

    # --------------------------------------------------------
    # Eliminar artículos iniciales
    # --------------------------------------------------------

    articulos = [
        "el ",
        "la ",
        "los ",
        "las ",
        "un ",
        "una ",
    ]

    for articulo in articulos:
        if expresion.startswith(articulo):
            expresion = expresion[len(articulo):].strip()
            break

    # --------------------------------------------------------
    # Evitar confundir palabras cartográficas con atributos
    # --------------------------------------------------------

    palabras_no_campo = {
        "colores",
        "color",
        "categorias",
        "categoria",
        "rangos",
        "rango",
        "intensidad",
        "gradiente",
        "mapa",
        "simbolos",
        "simbologia",
    }

    if expresion in palabras_no_campo:
        return None

    return expresion or None

# ============================================================
# DETECTAR CRITERIO DE ORDENAMIENTO
# ============================================================

def detectar_criterio(texto: str) -> Optional[str]:
    """
    Detecta si el usuario solicita orden ascendente
    o descendente.
    """

    texto_normalizado = normalizar_texto(texto)

    criterios_descendentes = [
        "mayor",
        "mayores",
        "mas grande",
        "mas grandes",
        "maximo",
        "maximos",
        "top",
        "superior",
        "superiores",
        "mas alto",
        "mas altos",
    ]

    if any(
        criterio in texto_normalizado
        for criterio in criterios_descendentes
    ):
        return "desc"

    criterios_ascendentes = [
        "menor",
        "menores",
        "mas pequeno",
        "mas pequenos",
        "minimo",
        "minimos",
        "inferior",
        "inferiores",
        "mas bajo",
        "mas bajos",
    ]

    if any(
        criterio in texto_normalizado
        for criterio in criterios_ascendentes
    ):
        return "asc"

    return None


# ============================================================
# DETECTAR DISTANCIA
# ============================================================

def detectar_distancia(
    texto: str,
) -> Tuple[Optional[float], Optional[str]]:
    """
    Extrae una distancia y la convierte a metros.
    """

    texto_normalizado = normalizar_texto(texto)

    coincidencia = re.search(
        r"\b(\d+(?:[.,]\d+)?)\s*"
        r"(m|metro|metros|km|kilometro|kilometros)\b",
        texto_normalizado,
    )

    if not coincidencia:
        return None, None

    valor_texto = coincidencia.group(1).replace(",", ".")
    valor = float(valor_texto)
    unidad = coincidencia.group(2)

    if unidad in [
        "km",
        "kilometro",
        "kilometros",
    ]:
        return valor * 1000, "metros"

    return valor, "metros"


# ============================================================
# DETECTAR OPERACIÓN ESPACIAL
# ============================================================

def detectar_operacion_espacial(
    texto: str,
    tipo_consulta: str,
) -> Optional[str]:
    """
    Determina la operación espacial probable.
    """

    texto_normalizado = normalizar_texto(texto)

    if tipo_consulta == "proximidad":
        return "ST_DWithin"

    if "buffer" in texto_normalizado:
        return "ST_Buffer"

    if any(
        expresion in texto_normalizado
        for expresion in [
            "dentro de",
            "contenido en",
            "contenidos en",
        ]
    ):
        return "ST_Within"

    if any(
        expresion in texto_normalizado
        for expresion in [
            "intersecta",
            "intersectan",
            "cruza",
            "cruzan",
            "superpone",
            "superponen",
        ]
    ):
        return "ST_Intersects"

    if any(
        expresion in texto_normalizado
        for expresion in [
            "contiene",
            "contienen",
        ]
    ):
        return "ST_Contains"

    return None


# ============================================================
# DETECTAR TEMA PRINCIPAL
# ============================================================

def detectar_tema(
    texto: str,
    tabla_principal: Optional[str],
) -> Optional[str]:
    """
    Produce una etiqueta semántica legible.
    """

    texto_normalizado = normalizar_texto(texto)

    temas = [
        "comercial",
        "industrial",
        "agropecuario",
        "residencial",
        "habitacional",
        "contribuyentes",
        "placa huella",
        "construcciones",
        "predios",
        "avaluo",
    ]

    for tema in temas:
        if tema in texto_normalizado:
            return tema

    return tabla_principal


# ============================================================
# DETECTAR INTENCIÓN DE VISUALIZACIÓN
# ============================================================

def detectar_visualizacion(
    texto: str,
    campo_detectado: Optional[str] = None,
) -> dict:
    """
    Detecta automáticamente el tipo de representación
    cartográfica solicitado por el usuario.

    Reglas generales:

    1. Si solicita varias capas, usa modo multicapa.
    2. Si solicita rangos, gradiente o intensidad, usa modo graduado.
    3. Si solicita clasificar, categorizar, agrupar, pintar,
       colorear o representar por un atributo, usa modo categórico.
    4. Si se logra extraer un atributo mediante "por" o "según",
       se interpreta como categórico, salvo que sea graduado.
    5. Si no se identifica ninguna intención cartográfica,
       conserva el modo simple.
    """

    texto_normalizado = normalizar_texto(texto)

    visualizacion = {
        "modo": "simple",
        "campo_categoria": None,
        "campo_valor": None,
        "expresion_campo": None,
        "mostrar_leyenda": False,
        "titulo_leyenda": None,
    }

    if not texto_normalizado:
        return visualizacion

    # --------------------------------------------------------
    # 1. Detectar visualización multicapa
    # --------------------------------------------------------

    expresiones_multicapa = [
        "junto con",
        "al mismo tiempo",
        "simultaneamente",
        "ademas de",
        "superpuesto con",
        "superpuesta con",
        "superpuestos con",
        "superpuestas con",
        "y tambien",
        "las dos capas",
        "ambas capas",
        "varias capas",
        "multiples capas",
    ]

    if any(
        expresion in texto_normalizado
        for expresion in expresiones_multicapa
    ):
        visualizacion["modo"] = "multicapa"
        visualizacion["mostrar_leyenda"] = True
        visualizacion["titulo_leyenda"] = "Capas del resultado"

        return visualizacion

    # --------------------------------------------------------
    # 2. Extraer atributo solicitado
    # --------------------------------------------------------

    expresion_campo = extraer_campo_visualizacion(
        texto
    )

    campo_normalizado = normalizar_identificador_campo(
        expresion_campo
    )

    if not campo_normalizado and campo_detectado:
        campo_normalizado = normalizar_identificador_campo(
            campo_detectado
        )

    # --------------------------------------------------------
    # 3. Detectar visualización graduada
    # --------------------------------------------------------

    expresiones_graduadas = [
        "por rangos",
        "por rango",
        "segun el valor",
        "segun su valor",
        "segun los valores",
        "de menor a mayor",
        "de mayor a menor",
        "por intensidad",
        "segun la intensidad",
        "escala de colores",
        "escala cromatica",
        "gradiente",
        "graduado",
        "graduada",
        "graduados",
        "graduadas",
        "intervalos",
        "por intervalos",
        "cuantiles",
        "por cuantiles",
    ]

    solicita_graduado = any(
        expresion in texto_normalizado
        for expresion in expresiones_graduadas
    )

    if solicita_graduado:
        visualizacion["modo"] = "graduado"
        visualizacion["campo_valor"] = campo_normalizado
        visualizacion["expresion_campo"] = expresion_campo
        visualizacion["mostrar_leyenda"] = True

        if expresion_campo:
            visualizacion["titulo_leyenda"] = (
                expresion_campo.title()
            )
        else:
            visualizacion["titulo_leyenda"] = (
                "Rangos del resultado"
            )

        return visualizacion

    # --------------------------------------------------------
    # 4. Detectar intención categórica explícita
    # --------------------------------------------------------

    expresiones_categoricas = [
        "categoriza",
        "categorizar",
        "categorizado",
        "categorizada",
        "categorizados",
        "categorizadas",
        "clasifica",
        "clasificar",
        "clasificado",
        "clasificada",
        "clasificados",
        "clasificadas",
        "agrupa",
        "agrupar",
        "agrupado",
        "agrupada",
        "agrupados",
        "agrupadas",
        "discrimina",
        "discriminar",
        "discriminado",
        "discriminada",
        "discriminados",
        "discriminadas",
        "diferencia",
        "diferenciar",
        "diferenciado",
        "diferenciada",
        "diferenciados",
        "diferenciadas",
        "segmenta",
        "segmentar",
        "segmentado",
        "segmentada",
        "segmentados",
        "segmentadas",
        "separa por",
        "separar por",
        "separados por",
        "separadas por",
        "pinta por",
        "pintar por",
        "pintados por",
        "pintadas por",
        "colorea por",
        "colorear por",
        "coloreados por",
        "coloreadas por",
        "representa por",
        "representar por",
        "simboliza por",
        "simbolizar por",
        "por categorias",
        "por categoria",
        "cada categoria",
        "cada tipo",
        "por colores",
        "segun el tipo",
        "segun la categoria",
        "segun el estado",
        "por estado",
        "por tipo",
        "por nivel",
    ]

    solicita_categorias = any(
        expresion in texto_normalizado
        for expresion in expresiones_categoricas
    )

    if solicita_categorias and campo_normalizado:
        visualizacion["modo"] = "categorico"
        visualizacion["campo_categoria"] = campo_normalizado
        visualizacion["expresion_campo"] = expresion_campo
        visualizacion["mostrar_leyenda"] = True

        visualizacion["titulo_leyenda"] = (
            expresion_campo.title()
            if expresion_campo
            else campo_normalizado.replace("_", " ").title()
        )

        return visualizacion

    # --------------------------------------------------------
    # 5. Respaldo genérico
    #
    # Si existe una expresión extraída mediante "por" o "según"
    # y no corresponde a una representación graduada, se asume
    # que el usuario solicita una clasificación categórica.
    # --------------------------------------------------------

    indicadores_representacion = [
        "muestra",
        "muestrame",
        "mostrar",
        "mapa",
        "dibuja",
        "dibujame",
        "representa",
        "pinta",
        "colorea",
        "simboliza",
        "visualiza",
        "visualizar",
        "ubica",
        "resalta",
        "por colores",
        "segun",
    ]

    solicita_representacion = any(
        expresion in texto_normalizado
        for expresion in indicadores_representacion
    )

    if (
        expresion_campo is not None
        and campo_normalizado is not None
        and solicita_representacion
    ):
        visualizacion["modo"] = "categorico"
        visualizacion["campo_categoria"] = campo_normalizado
        visualizacion["expresion_campo"] = expresion_campo
        visualizacion["mostrar_leyenda"] = True
        visualizacion["titulo_leyenda"] = (
            expresion_campo.title()
        )

        return visualizacion

    return visualizacion


# ============================================================
# CONSTRUIR PLAN
# ============================================================

def construir_plan(pregunta: str) -> dict:
    """
    Construye el plan territorial completo a partir
    de la pregunta original.
    """

    if not isinstance(pregunta, str):
        raise ValueError(
            "La pregunta del planificador debe ser texto."
        )

    pregunta = pregunta.strip()

    if not pregunta:
        raise ValueError(
            "La pregunta del planificador no puede estar vacía."
        )

    plan = crear_plan()

    tipo_consulta = detectar_tipo_consulta(
        pregunta
    )

    tabla_principal = detectar_tabla_principal(
        pregunta
    )

    distancia, unidad_distancia = detectar_distancia(
        pregunta
    )

    plan["pregunta_original"] = pregunta
    plan["tipo_consulta"] = tipo_consulta
    plan["tabla_principal"] = tabla_principal

    plan["cantidad"] = detectar_cantidad(
        pregunta
    )

    plan["requiere_geom"] = detectar_geom(
        pregunta
    )

    plan["criterio"] = detectar_criterio(
        pregunta
    )

    plan["campo"] = detectar_campo(
        pregunta,
        tabla_principal,
    )

    plan["visualizacion"] = detectar_visualizacion(
        pregunta,
        plan["campo"],
    )

    plan["distancia"] = distancia
    plan["unidad_distancia"] = unidad_distancia

    plan["operacion_espacial"] = (
        detectar_operacion_espacial(
            pregunta,
            tipo_consulta,
        )
    )

    plan["tema"] = detectar_tema(
        pregunta,
        tabla_principal,
    )

    return plan