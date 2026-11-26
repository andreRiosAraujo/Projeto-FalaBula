"""FalaBula — interface de consulta a bulas PDF, sem alteração do app.py original.

Execute na raiz do repositório: python -m streamlit run frontend.py
Novos PDFs em documentos/ são reconhecidos após atualização/recarga da aplicação.
"""
from pathlib import Path
import hashlib
import os

import streamlit as st
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "documentos"
load_dotenv(BASE_DIR / ".env")
st.set_page_config(
    page_title="FalaBula | Assistente de bulas",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS_FILE = BASE_DIR / "style.css"
if CSS_FILE.exists():
    st.markdown(
        f'<style>{CSS_FILE.read_text(encoding="utf-8")}</style>',
        unsafe_allow_html=True,
    )

if "acesso_liberado" not in st.session_state:
    st.session_state.acesso_liberado = False
if "mensagens_falabula" not in st.session_state:
    st.session_state.mensagens_falabula = []
if "nome_visitante" not in st.session_state:
    st.session_state.nome_visitante = "Visitante"


from falabula_core import (
    listar_arquivos, assinatura, carregar_paginas, responder_pergunta,
    pergunta_catalogo, resposta_catalogo
)


def listar_bulas():
    return listar_arquivos(DOCS_DIR)


def assinatura_documentos(arquivos):
    return assinatura(arquivos)


@st.cache_resource(show_spinner=False, max_entries=2)
def indexar_documentos(identificacao):
    """Carrega os PDFs uma vez; mudanças de arquivo invalidam o cache."""
    return carregar_paginas(listar_bulas())


def chave_groq():
    """Compatível com .env local e Streamlit Cloud Secrets."""
    chave = os.getenv("GROQ_API_KEY", "")
    if chave:
        return chave
    try:
        return st.secrets.get("GROQ_API_KEY", "")
    except (FileNotFoundError, KeyError):
        return ""


def responder(pergunta, identificacao):
    arquivos = listar_bulas()
    if pergunta_catalogo(pergunta):
        return resposta_catalogo(arquivos), []
    indice = indexar_documentos(identificacao)
    return responder_pergunta(pergunta, arquivos, indice, chave_groq())


st.markdown(
    '<div class="top-brand"><div class="brand-mark">F</div><div>'
    '<div class="brand-name">FalaBula<span>.</span></div>'
    '<div class="brand-subtitle">Informações sobre medicamentos, baseadas em bulas</div>'
    '</div><span class="top-pill">PROJETO ACADÊMICO</span></div>',
    unsafe_allow_html=True,
)

if not st.session_state.acesso_liberado:
    left, center, right = st.columns([1, 1.18, 1])
    with center:
        st.markdown(
            '<div class="login-intro"><div class="eyebrow">BEM-VINDO AO FALABULA</div>'
            '<h1>Informação clara.<br><em>Consulta responsável.</em></h1>'
            '<p>Pesquise informações sobre medicamentos nos documentos '
            'de bula cadastrados pela equipe.</p></div>',
            unsafe_allow_html=True,
        )
        with st.form("acesso_demo", border=False):
            usuario = st.text_input(
                "Seu nome", placeholder="Como podemos chamar você?"
            )
            st.text_input(
                "Senha demonstrativa", type="password",
                placeholder="Qualquer senha (opcional)"
            )
            entrar = st.form_submit_button(
                "Acessar o assistente →", use_container_width=True, type="primary"
            )
            if entrar:
                st.session_state.nome_visitante = usuario.strip() or "Visitante"
                st.session_state.acesso_liberado = True
                st.rerun()
        st.caption(
            "Acesso demonstrativo: não há autenticação de usuários."
        )
else:
    st.markdown(
        '<div class="hero"><div class="eyebrow">SEU ASSISTENTE DE BULAS</div>'
        '<h1>Como podemos <em>ajudar você?</em></h1>'
        '<p>Consulte indicações, precauções, contraindicações e reações adversas '
        'de medicamentos presentes nas bulas cadastradas.</p></div>',
        unsafe_allow_html=True,
    )
    arquivos = listar_bulas()
    assinatura = assinatura_documentos(arquivos)
    with st.sidebar:
        st.markdown("### FalaBula")
        st.write(f"Olá, **{st.session_state.nome_visitante}**.")
        if st.button("Nova conversa", use_container_width=True):
            st.session_state.mensagens_falabula = []
            st.rerun()
        if st.button("Sair da demonstração", use_container_width=True):
            st.session_state.acesso_liberado = False
            st.session_state.mensagens_falabula = []
            st.rerun()
        st.divider()
        st.caption(f"Bulas cadastradas: {len(arquivos)}")
        st.caption("Versão 2.0 — catálogo e busca por bula")
        with st.expander("Documentos disponíveis"):
            for arquivo in arquivos:
                st.caption(arquivo.name)
        st.caption(
            "Projeto acadêmico. Informações não substituem orientação "
            "médica ou farmacêutica."
        )

    if not arquivos:
        st.warning(
            "Nenhum PDF encontrado na pasta documentos. "
            "Inclua arquivos PDF de bula e atualize a aplicação."
        )

    if not st.session_state.mensagens_falabula:
        st.markdown(
            '<div class="suggest-title">Você pode começar por uma destas perguntas:</div>',
            unsafe_allow_html=True,
        )
        temas = [
            "Quais medicamentos estão cadastrados no FalaBula?",
            "Para que serve o Mounjaro, segundo a bula?",
            "Quais contraindicações constam na bula do Glifage?",
            "Quais reações adversas constam na bula do Januvia?",

        ]
        grade = st.columns(2)
        selecionada = None
        for i, tema in enumerate(temas):
            with grade[i % 2]:
                if st.button(tema + "  ↗", key=f"sug_{i}", use_container_width=True):
                    selecionada = tema
    else:
        selecionada = None

    for mensagem in st.session_state.mensagens_falabula:
        with st.chat_message(
            mensagem["role"],
            avatar="👤" if mensagem["role"] == "user" else "💬",
        ):
            st.markdown(mensagem["content"])
            if mensagem.get("fontes"):
                with st.expander("Trechos de origem recuperados"):
                    for fonte in mensagem["fontes"]:
                        st.caption(fonte)

    pergunta_digitada = st.chat_input(
        "Pergunte sobre os medicamentos disponíveis nas bulas..."
    )
    pergunta = pergunta_digitada or selecionada
    if pergunta:
        st.session_state.mensagens_falabula.append(
            {"role": "user", "content": pergunta}
        )
        with st.chat_message("user", avatar="👤"):
            st.markdown(pergunta)
        with st.chat_message("assistant", avatar="💬"):
            try:
                with st.spinner("Consultando bulas cadastradas..."):
                    resposta, fontes = responder(pergunta, assinatura)
            except Exception as erro:
                st.error(f"Não foi possível consultar as bulas: {erro}")
            else:
                st.markdown(resposta)
                if fontes:
                    with st.expander("Trechos de origem recuperados"):
                        for fonte in fontes:
                            st.caption(fonte)
                st.session_state.mensagens_falabula.append(
                    {"role": "assistant", "content": resposta, "fontes": fontes}
                )

    st.markdown(
        '<div class="medical-note"><strong>Atenção:</strong> '
        'conteúdo informativo e acadêmico. Não inicie, suspenda ou altere '
        'medicamentos sem orientação médica. Em urgências, procure '
        'atendimento de saúde.</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="footer">FalaBula · Projeto acadêmico de inteligência artificial'
    ' · Informação responsável</div>',
    unsafe_allow_html=True,
)
