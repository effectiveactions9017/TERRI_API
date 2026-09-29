        ):

            coincidencias.append(
                departamento
            )

    if not coincidencias:
        return None

    coincidencias.sort(
        key=lambda item: len(
            normalizar_texto(
                item.get(
                    "departamento"
                )
            )
        ),
        reverse=True
    )

    return coincidencias[0]


# ============================================================
# RESOLVER CONSULTA NATURAL DE LÍMITES
# ============================================================

def resolver_consulta_limites(
    pregunta: str
) -> Optional[Dict[str, Any]]:

    if not es_consulta_limites_igac(
        pregunta
    ):
        return None

    texto = normalizar_texto(
        pregunta
    )

    # --------------------------------------------------------
    # PRIORIZAR DEPARTAMENTO SOLO SI EL USUARIO LO PIDE
    # EXPLÍCITAMENTE.
    # --------------------------------------------------------

    solicita_departamento = (
        "departamento" in texto
        or "departamental" in texto
    )

    if solicita_departamento:

        departamento = (
            detectar_departamento_en_pregunta(
                pregunta
            )
        )

        if departamento:

            return consultar_limite_departamento(
                departamento.get(
                    "departamento"
                )
            )

    # --------------------------------------------------------
    # MUNICIPIO
    # Si encontramos un municipio, no consultamos además
    # el catálogo de departamentos. Evita una petición IGAC
    # innecesaria y reduce el riesgo de timeout.
    # --------------------------------------------------------

    municipio = (
        detectar_municipio_en_pregunta(
            pregunta
        )
    )

    if municipio:

        return consultar_limite_municipio(
            nombre=municipio.get(
                "municipio"
            ),
            departamento=municipio.get(
                "departamento"
            )
        )

    # --------------------------------------------------------
    # DEPARTAMENTO
    # Solo consultamos departamentos si no identificamos
    # previamente un municipio.
    # --------------------------------------------------------

    departamento = (
        detectar_departamento_en_pregunta(
            pregunta
        )
    )

    if departamento:

        return consultar_limite_departamento(
            departamento.get(
                "departamento"
            )
        )

    return {
        "ok": False,
        "tipo": "sin_resultado",
        "fuente": "IGAC",
        "mensaje": (
            "Entendí que deseas consultar un límite del IGAC, "
            "pero no pude identificar el municipio o departamento."
        )
    }

