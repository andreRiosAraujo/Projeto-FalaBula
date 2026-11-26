"""FalaBula: interface de apresentação independente do app.py original.
Execute na raiz do repositório: python -m streamlit run frontend.py
"""
from pathlib import Path
import os
import streamlit as st
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')
st.set_page_config(page_title='FalaBula | Assistente sobre diabetes', page_icon='💬', layout='wide', initial_sidebar_state='collapsed')

CSS_FILE = BASE_DIR / 'style.css'
if CSS_FILE.exists():
    st.markdown(f'<style>{CSS_FILE.read_text(encoding="utf-8")}</style>', unsafe_allow_html=True)

# Sem autenticação real: campos meramente demonstrativos.
if 'acesso_liberado' not in st.session_state:
    st.session_state.acesso_liberado = False
if 'mensagens_falabula' not in st.session_state:
    st.session_state.mensagens_falabula = []
if 'nome_visitante' not in st.session_state:
    st.session_state.nome_visitante = 'Visitante'

@st.cache_resource(show_spinner=False)
def iniciar_assistente():
    # Instancia um pipeline equivalente ao do app.py, sem importar nem alterar
    # esse arquivo (o app.py executa a interface quando importado).
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_chroma import Chroma
    from langchain_groq import ChatGroq
    from langchain_huggingface import HuggingFaceEmbeddings

    arquivos = ['Base_Unica_Diabetes_Posologia_Mapeada.pdf', 'GuiaDiabetes.pdf']
    documentos = []
    for nome in arquivos:
        caminho = BASE_DIR / nome
        if not caminho.is_file():
            raise FileNotFoundError(f'Arquivo necessário não encontrado: {nome}')
        documentos.extend(PyPDFLoader(str(caminho)).load())
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(documentos)
    embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')
   
    # Cria o banco vetorial em lotes menores.
    # Isso ajuda a reduzir o consumo de memória.

    tamanho_lote = 25

    if not chunks:
        raise RuntimeError("Nenhum texto foi extraído dos PDFs.")

    total = len(chunks)
    print(f"INICIO DA INDEXACAO: {total} trechos", flush=True)

    # Cria o banco com os primeiros 25 trechos.
    banco = Chroma.from_documents(
        documents=chunks[:tamanho_lote],
        embedding=embeddings
    )

    print(
        f"INDEXADOS: {min(tamanho_lote, total)}/{total}",
        flush=True
    )

    # Adiciona os demais trechos em pequenos lotes.
    for inicio in range(tamanho_lote, total, tamanho_lote):
        lote = chunks[inicio:inicio + tamanho_lote]
        banco.add_documents(lote)

        print(
            f"INDEXADOS: {inicio + len(lote)}/{total}",
            flush=True
        )

    print("INDEXACAO CONCLUIDA", flush=True)

    retriever = banco.as_retriever(search_kwargs={'k': 5})

    llm = ChatGroq(model='openai/gpt-oss-120b', temperature=0)
    return retriever, llm


def responder(pergunta):
    if not os.getenv('GROQ_API_KEY'):
        raise RuntimeError('A chave GROQ_API_KEY não foi configurada no arquivo .env.')
    retriever, llm = iniciar_assistente()
    documentos = retriever.invoke(pergunta)
    contexto = '\n\n'.join(doc.page_content for doc in documentos)
    prompt = f'''Você é um assistente informativo sobre diabetes e medicamentos.
Responda somente com base no contexto fornecido. Se não houver informação
suficiente, diga que a informação não foi localizada na base consultada.
Não invente doses, contraindicações, interações ou condutas terapêuticas.
Não substitua a orientação de profissionais de saúde.

Contexto:\n{contexto}\n\nPergunta:\n{pergunta}'''
    resposta = llm.invoke(prompt).content
    return str(resposta)

st.markdown('''<div class="top-brand"><div class="brand-mark">F</div><div><div class="brand-name">FalaBula<span>.</span></div><div class="brand-subtitle">Informação sobre diabetes, de forma acessível</div></div><span class="top-pill">PROJETO ACADÊMICO</span></div>''', unsafe_allow_html=True)

if not st.session_state.acesso_liberado:
    left, center, right = st.columns([1, 1.18, 1])
    with center:
        st.markdown('''<div class="login-intro"><div class="eyebrow">BEM-VINDO AO FALABULA</div><h1>Informação clara.<br><em>Saúde com consciência.</em></h1><p>Converse com nosso assistente e consulte informações sobre diabetes e medicamentos a partir dos documentos do projeto.</p></div>''', unsafe_allow_html=True)
        with st.form('acesso_demo', border=False):
            usuario = st.text_input('Seu nome', placeholder='Como podemos chamar você?')
            st.text_input('Senha demonstrativa', type='password', placeholder='Qualquer senha (opcional)')
            entrar = st.form_submit_button('Acessar o assistente →', use_container_width=True, type='primary')
            if entrar:
                st.session_state.nome_visitante = usuario.strip() or 'Visitante'
                st.session_state.acesso_liberado = True
                st.rerun()
        st.caption('Acesso de demonstração: não é necessário cadastrar usuário ou informar senha válida. Nenhum dado de login é verificado.')
else:
    st.markdown('''<div class="hero"><div class="eyebrow">SEU ASSISTENTE VIRTUAL</div><h1>Como podemos <em>ajudar você?</em></h1><p>Tire dúvidas sobre diabetes, medicamentos, indicações e precauções com informações da base documental do projeto.</p></div>''', unsafe_allow_html=True)
    with st.sidebar:
        st.markdown('### FalaBula')
        st.write(f'Olá, **{st.session_state.nome_visitante}**.')
        if st.button('Nova conversa', use_container_width=True):
            st.session_state.mensagens_falabula = []
            st.rerun()
        if st.button('Sair da demonstração', use_container_width=True):
            st.session_state.acesso_liberado = False
            st.session_state.mensagens_falabula = []
            st.rerun()
        st.divider()
        st.caption('Projeto acadêmico. As respostas não substituem consulta médica, farmacêutica ou prescrição.')
    if not st.session_state.mensagens_falabula:
        st.markdown('<div class="suggest-title">Você pode começar por uma destas perguntas:</div>', unsafe_allow_html=True)
        temas = [
            'O que é diabetes tipo 2?',
            'Para que serve a metformina?',
            'Quais cuidados são importantes com medicamentos para diabetes?',
            'Quais são os sinais de hipoglicemia?',
        ]
        grade = st.columns(2)
        selecionada = None
        for i, tema in enumerate(temas):
            with grade[i % 2]:
                if st.button(tema + '  ↗', key=f'sug_{i}', use_container_width=True):
                    selecionada = tema
    else:
        selecionada = None
    for mensagem in st.session_state.mensagens_falabula:
        with st.chat_message(mensagem['role'], avatar='👤' if mensagem['role'] == 'user' else '💬'):
            st.markdown(mensagem['content'])
    pergunta_digitada = st.chat_input('Escreva sua pergunta sobre diabetes ou medicamentos...')
    pergunta = pergunta_digitada or selecionada
    if pergunta:
        st.session_state.mensagens_falabula.append({'role': 'user', 'content': pergunta})
        with st.chat_message('user', avatar='👤'):
            st.markdown(pergunta)
        with st.chat_message('assistant', avatar='💬'):
            try:
                with st.spinner('Consultando os documentos do projeto...'):
                    resposta = responder(pergunta)
            except Exception as erro:
                st.error(f'Não foi possível consultar o assistente: {erro}')
            else:
                st.markdown(resposta)
                st.session_state.mensagens_falabula.append({'role': 'assistant', 'content': resposta})
    st.markdown('''<div class="medical-note"><strong>Atenção:</strong> conteúdo informativo e acadêmico. Não inicie, suspenda ou altere medicamentos sem orientação médica. Em situações de urgência, procure atendimento de saúde.</div>''', unsafe_allow_html=True)

st.markdown('<div class="footer">FalaBula · Projeto acadêmico de inteligência artificial · Informação responsável</div>', unsafe_allow_html=True)
