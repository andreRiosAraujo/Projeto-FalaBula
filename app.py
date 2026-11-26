"""Ponto de entrada do FalaBula no Streamlit Cloud.

O código legado original permanece na branch de backup:
backup/antes-base-dinamica-2026-11-26

Este arquivo carrega a mesma aplicação do frontend.py para evitar que
a versão publicada use a base antiga enquanto o frontend usa documentos/.
"""

import frontend  # noqa: F401  # A interface Streamlit é executada na importação.
