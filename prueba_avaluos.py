from pprint import pprint

from services.query_executor import ejecutar_consulta


sql = """
SELECT
    "AVALUO 2026" AS valor_original,
    NULLIF(
        REGEXP_REPLACE(
            "AVALUO 2026",
            '[^0-9,.-]',
            '',
            'g'
        ),
        ''
    )::numeric AS valor_convertido
FROM predios_sesquile
WHERE "AVALUO 2026" IS NOT NULL
ORDER BY valor_convertido DESC NULLS LAST
LIMIT 10;
"""

resultado = ejecutar_consulta(sql)

pprint(resultado)