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


def listar_bulas():
    """Lista PDFs disponíveis; diretórios externos ao projeto não são pesquisados."""
    if not DOCS_DIR.is_dir():
        return []
    return sorted(
        (arq for arq in DOCS_DIR.glob("*.pdf") if arq.is_file()),
        key=lambda a: a.name.casefold(),
    )


def assinatura_documentos(arquivos):
    """Identifica inclusões, remoções ou modificações sem depender do nome do PDF."""
    assinatura = []
    for arquivo in arquivos:
        h = hashlib.sha256()
        with arquivo.open("rb") as entrada:
            for bloco in iter(lambda: entrada.read(1024 * 1024), b""):
                h.update(bloco)
        assinatura.append((arquivo.name, h.hexdigest()))
    return tuple(assinatura)


@st.cache_resource(show_spinner=False, max_entries=1)
def iniciar_assistente(assinatura):
    """Indexação leve com TF-IDF: evita carregar modelo de embeddings na memória."""
    from types import SimpleNamespace
    import re
    import unicodedata
    import numpy as np
    from pypdf import PdfReader
    from sklearn.feature_extraction.text import TfidfVectorizer
    from langchain_groq import ChatGroq

    if not assinatura:
        raise RuntimeError("Nenhuma bula PDF encontrada na pasta documentos.")

    trechos = []
    fontes = []
    falhas = []
    for nome, _hash in assinatura:
        try:
            reader = PdfReader(str(DOCS_DIR / nome))
            texto_valido = False
            for n, pagina in enumerate(reader.pages):
                texto = (pagina.extract_text() or "").strip()
                if not texto:
                    continue
                texto_valido = True
                for inicio in range(0, len(texto), 1500):
                    trecho = texto[max(0, inicio - 150):inicio + 1500].strip()
                    if len(trecho) >= 30:
                        trechos.append(trecho)
                        fontes.append({"source": nome, "page": n})
            if not texto_valido:
                falhas.append(f"{nome} (sem texto selecionável)")
        except Exception as erro:
            falhas.append(f"{nome} ({type(erro).__name__})")
    if falhas:
        raise RuntimeError("Bulas com problema: " + "; ".join(falhas))
    if not trechos:
        raise RuntimeError("Nenhuma bula contém texto pesquisável.")

    # Busca lexical com baixo uso de memória. Não exige transformers nem Chroma.
    vetorizador = TfidfVectorizer(
        strip_accents="unicode",
        lowercase=True,
        max_features=25000,
        sublinear_tf=True,
        dtype=np.float32,
    )
    matriz = vetorizador.fit_transform(trechos)

    class Recuperador:
        def invoke(self, pergunta):
            consulta = vetorizador.transform([pergunta])
            notas = (matriz @ consulta.T).toarray().ravel()
            # Prioriza os documentos cujo nome do medicamento está na pergunta.
            def normalizar(s):
                return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
            palavras = set(re.findall(r"[a-z0-9]{4,}", normalizar(pergunta)))
            comuns = {"bula", "b ulas", "medicamento", "quais", "para", "serve", "sobre", "contraindicacoes", "cuidados", "reacoes", "adversas", "informa", "segundo"}
            palavras -= comuns
            for i, meta in enumerate(fontes):
                nome = normalizar(meta["source"]).replace("bula_", "")
                if any(p in nome for p in palavras):
                    notas[i] += 0.35
            melhores = np.argsort(notas)[::-1][:5]
            return [
                SimpleNamespace(page_content=trechos[int(i)], metadata=fontes[int(i)])
                for i in melhores if notas[int(i)] > 0.005
            ]

    return Recuperador(), ChatGroq(model="openai/gpt-oss-120b", temperature=0)


# Nomes de apresentação para o catálogo inicial. Novos PDFs são exibidos
# automaticamente pelo nome do arquivo, mesmo sem cadastro nesta tabela.
NOMES_MEDICAMENTOS = {
    "bula_Mounjaro.pdf": "Mounjaro (tirzepatida)",
    "bula_LANTUS_insulina_glargina.pdf": "Lantus (insulina glargina)",
    "bula_InsulinaHumanaRegular.pdf": "Wosulin R (insulina humana regular)",
    "bula_InsulinaHumana_NovolinN.pdf": "Novolin N (insulina humana NPH)",
    "bula_empagliflozina.pdf": "Empagliflozina",
    "bula_dapagliflozina.pdf": "Dapagliflozina",
    "bula_Januvia.pdf": "Januvia (sitagliptina)",
    "bula_glimepirida.pdf": "Glimepirida",
    "bula_gliclazida.pdf": "Gliclazida",
    "bula_glibenclamida.pdf": "Glibenclamida",
    "bula_glifagexr.pdf": "Glifage XR (metformina de liberação prolongada)",
    "bula_glifage.pdf": "Glifage (metformina)",
}


def pergunta_sobre_catalogo(pergunta):
    """Detecta solicitações de inventário, que não devem usar busca por trechos."""
    import re
    import unicodedata

    texto = unicodedata.normalize("NFKD", pergunta).encode(
        "ascii", "ignore"
    ).decode().lower()
    texto = re.sub(r"[^a-z0-9 ]", " ", texto)
    termos = ("medicamento", "remedio", "bula", "farmaco")
    tem_termo = any(t in texto for t in termos)
    consulta_lista = any(t in texto for t in (
        "quais", "liste", "listar", "lista", "relacao", "catalogo",
        "quantos", "todos", "disponiveis", "disponivel", "cadastrados",
        "cadastrado", "registrados", "tem na base", "tem no sistema",
        "possui", "estao na base",
    ))
    return (tem_termo and consulta_lista) or (
        "o que tem na base" in texto or "o que voce conhece" in texto
    )


def resposta_catalogo(assinatura):
    nomes = []
    for arquivo, _hash in assinatura:
        nome = NOMES_MEDICAMENTOS.get(
            arquivo, Path(arquivo).stem.removeprefix("bula_").replace("_", " ")
        )
        nomes.append(nome)
    linhas = [f"{i}. {nome}" for i, nome in enumerate(nomes, 1)]
    return (
        f"Encontrei **{len(nomes)} bulas em PDF** cadastradas no FalaBula:\\n\\n"
        + "\\n".join(linhas)
        + "\\n\\nA relação indica documentos cadastrados, não disponibilidade "
        "em farmácias, no SUS ou no Farmácia Popular. "
        "Alguns documentos podem corresponder ao mesmo princípio ativo."
    )


def responder(pergunta, assinatura):
    if pergunta_sobre_catalogo(pergunta):
        return resposta_catalogo(assinatura), []
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError(
            "Configure GROQ_API_KEY no arquivo .env (local) ou Secrets (nuvem)."
        )
    retriever, llm = iniciar_assistente(assinatura)
    documentos = retriever.invoke(pergunta)
    if not documentos:
        return "Não encontrei essa informação nas bulas cadastradas.", []

    trechos = []
    fontes = []
    for doc in documentos:
        nome = Path(doc.metadata.get("source", "documento desconhecido")).name
        numero = int(doc.metadata.get("page", 0)) + 1
        fonte = f"{nome} — página {numero}"
        fontes.append(fonte)
        trechos.append(f"[Fonte: {fonte}]\n{doc.page_content}")

    contexto = "\n\n".join(trechos)
    prompt = f"""Você é o FalaBula, assistente acadêmico de consulta a bulas.
Responda em português claro, SOMENTE com informações efetivamente sustentadas
pelos trechos de bulas apresentados. Não presuma que um medicamento trate
determinada doença apenas pelo nome ou classe. Se os trechos não forem
suficientes, diga explicitamente que a informação não foi localizada
nos documentos consultados. Não invente dose, indicação, contraindicação,
interação ou disponibilidade no SUS/Farmácia Popular.
Diferencie informações gerais da bula de orientações individuais.
Não recomende iniciar, interromper, trocar medicamentos ou ajustar doses.
Não faça diagnóstico. Para emergências, oriente procurar atendimento.
Não cite fonte ou página que não apareça no contexto.

Bulas consultadas:
{contexto}

Pergunta: {pergunta}
"""
    resposta = str(llm.invoke(prompt).content)
    return resposta, sorted(set(fontes))


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
            "Para que serve o Mounjaro, segundo a bula?",
            "Quais contraindicações constam na bula do Glifage?",
            "Que cuidados a bula do Lantus informa?",
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
