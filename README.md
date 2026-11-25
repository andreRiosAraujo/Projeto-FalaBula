# 💊 Chatbot Farmacêutico para Diabetes (RAG)

## Acessar o FalaBula online

**[Abrir o chatbot FalaBula](https://projeto-falabula-dashshp2g9tj3fr9jop2yv.streamlit.app/)**

A interface pode ser acessada pelo navegador no computador, tablet ou celular, sem instalação local. O chatbot é um projeto acadêmico de caráter informativo e não substitui orientação médica.

**Código-fonte:** [Repositório no GitHub](https://github.com/andreRiosAraujo/Projeto-FalaBula)


![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Interface-Streamlit-FF4B4B)
![LangChain](https://img.shields.io/badge/Framework-LangChain-1C3C3C)
![ChromaDB](https://img.shields.io/badge/VectorDB-Chroma-orange)
![Groq](https://img.shields.io/badge/LLM-Groq%20%7C%20gpt--oss--120b-00A67E)

Assistente virtual inteligente desenvolvido com arquitetura **RAG (Retrieval-Augmented Generation)** para auxiliar pessoas com diabetes a reconhecer, consultar e compreender informações sobre seus medicamentos. O sistema responde a dúvidas em linguagem natural com base exclusivamente em uma base consolidada de bulas e registros farmacêuticos mapeados, evitando alucinações e garantindo fidelidade aos dados clínicos.

## 🎯 Objetivo do Projeto

Facilitar o acesso à informação segura sobre medicamentos antidiabéticos (para Diabetes Tipo 1, Tipo 2 e condições correlatas), permitindo que pacientes e usuários consultem rapidamente:
- Princípio ativo, classe terapêutica e categoria regulatória (Genérico, Similar, Novo, etc.).
- Para que serve o medicamento e como ele funciona no organismo.
- Posologia, forma farmacêutica, apresentações e uso indicado (adulto ou pediátrico).
- Contraindicações, precauções e alertas de segurança.

## 🏗️ Arquitetura e Fluxo do Sistema

O projeto utiliza a arquitetura **RAG**, integrando busca semântica vetorial e geração de texto via LLM em 5 etapas principais:

1. **Fonte de Dados e Carregamento (`PyPDFLoader`)**: Leitura do documento base contendo os registros e posologias dos medicamentos para diabetes.
2. **Preparação dos Textos (`RecursiveCharacterTextSplitter` & `HuggingFaceEmbeddings`)**:
   - **Chunking**: Divisão dos documentos em trechos menores (`chunk_size=1000` caracteres com sobreposição `chunk_overlap=200`) para preservar o contexto clínico.
   - **Embeddings**: Conversão dos trechos de texto em vetores numéricos densos utilizando o modelo `sentence-transformers/all-MiniLM-L6-v2`.
3. **Banco Vetorial e Recuperação (`Chroma`)**: Armazenamento local em memória dos vetores e configuração do *Retriever* para buscar os **5 trechos mais relevantes** (`k=5`) por similaridade semântica a cada pergunta do usuário.
4. **Geração de Resposta (`ChatGroq`)**: Envio da pergunta do usuário junto ao contexto recuperado para o modelo **`openai/gpt-oss-120b`** via API da Groq, configurado com `temperature=0` para máxima precisão e determinismo.
5. **Interface Web (`Streamlit`)**: Camada visual interativa com gerenciamento de estado da sessão (`st.session_state`) para histórico de mensagens e cache de recursos (`@st.cache_resource`) para evitar a recriação do banco vetorial a cada interação.

### Relação de Componentes da Arquitetura

| Etapa | Componente | Papel na Arquitetura |
| :--- | :--- | :--- |
| **1** | Configuração da API Groq | Integração com o serviço externo de IA e gerenciamento seguro de credenciais via `.env`. |
| **2** | Interface Streamlit | Camada de apresentação responsável pela interação via chat com o usuário. |
| **3** | Carregamento do Documento | Definição da entrada e leitura da base de conhecimento em PDF. |
| **4** | Divisão em Chunks | Organização e fragmentação dos textos para otimizar a recuperação posterior. |
| **5** | Modelo de Embeddings | Representação numérica e semântica dos textos farmacêuticos. |
| **6** | Banco Vetorial Chroma | Armazenamento e pesquisa vetorial dos documentos processados. |
| **7** | Retriever | Mecanismo de recuperação dos 5 trechos mais relevantes para a dúvida do usuário. |
| **8** | LLM via Groq | Geração das respostas em linguagem natural estritamente baseadas no contexto recuperado. |
| **9** | Preparação do RAG | Empacotamento e cache da pipeline de dados e IA (`@st.cache_resource`). |
| **10** | Histórico e Fluxo de Chat | Gerenciamento do estado da conversa na sessão e exibição das respostas ao paciente. |

## 📊 Estrutura da Base de Dados

A base de conhecimento (`Base_Unica_Diabetes_Posologia_Mapeada`) reúne **5.761 registros** mapeados na aba `Base Consolidada Posologia`, estruturados em **18 colunas**:

| Coluna | Descrição |
| :--- | :--- |
| `NOME_PRODUTO` | Nome comercial ou denominação do medicamento |
| `PRINCIPIO_ATIVO` | Substância(s) ativa(s) (ex.: *cloridrato de metformina, dapagliflozina, gliclazida*) |
| `CLASSE_TERAPEUTICA` | Classificação farmacológica (ex.: *ANTIDIABETICOS*) |
| `CATEGORIA_REGULATORIA` | Tipo de registro (Genérico, Similar, Novo, Biológico, etc.) |
| `SITUACAO_REGISTRO` | Status atual do registro sanitário (ex.: *Ativo*) |
| `EMPRESA_DETENTORA_REGISTRO` | CNPJ e razão social do laboratório fabricante |
| `FORMA_FARMACEUTICA_BULA` | Apresentação física (Comprimido revestido, solução injetável, etc.) |
| `USO_INDICADO` | Faixa etária e via de administração (ex.: *Adultos e crianças (>10 anos) / Oral*) |
| `APRESENTACAO_BULA` | Concentrações e dosagens disponíveis (ex.: *500 mg, 850 mg ou 1000 mg*) |
| `PARA_QUE_SERVE` | Indicações terapêuticas principais e secundárias |
| `COMO_FUNCIONA` | Mecanismo de ação fisiológico no controle glicêmico |
| `CONTRAINDICACOES` | Condições clínicas em que o medicamento não deve ser utilizado |
| `PRECAUCOES` | Alertas clínicos, riscos (ex.: acidose láctica, hipoglicemia) e cuidados especiais |
| `TIPO_PRODUTO` | Classificação geral do item (`MEDICAMENTO`) |
| `DATA_FINALIZACAO_PROCESSO` | Data de conclusão do processo regulatório |
| `NUMERO_REGISTRO_PRODUTO` | Código oficial de registro do medicamento |
| `DATA_VENCIMENTO_REGISTRO` | Validade do registro regulatório |
| `NUMERO_PROCESSO` | Número do processo administrativo na agência reguladora |

## 🛠️ Tecnologias e Bibliotecas Utilizadas

- **[Streamlit](https://streamlit.io/)**: Construção da interface web interativa.
- **[LangChain](https://www.langchain.com/)**: Orquestração de todo o fluxo RAG (`langchain-community`, `langchain-text-splitters`, `langchain-chroma`, `langchain-groq`, `langchain-huggingface`).
- **[ChromaDB](https://www.trychroma.com/)**: Banco de dados vetorial para busca semântica.
- **[Groq Cloud API](https://groq.com/)**: Inferência em alta velocidade utilizando o modelo `openai/gpt-oss-120b`.
- **[Hugging Face Sentence Transformers](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)**: Geração local de embeddings (`all-MiniLM-L6-v2`).
- **[PyPDF](https://pypdf.readthedocs.io/)**: Extração e leitura de páginas do documento PDF.
- **[Python-dotenv](https://pypi.org/project/python-dotenv/)**: Gerenciamento seguro de variáveis de ambiente.

## ⚙️ Pré-requisitos e Instalação

### 1. Clonar o repositório
```bash
git clone [https://github.com/seu-usuario/seu-repositorio.git](https://github.com/seu-usuario/seu-repositorio.git)
cd seu-repositorio
```

### 2. Criar e ativar um ambiente virtual (recomendado)
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar as dependências
Crie um arquivo `requirements.txt` na raiz do projeto com o seguinte conteúdo:

```txt
streamlit
python-dotenv
langchain-community
langchain-text-splitters
langchain-chroma
langchain-groq
langchain-huggingface
pypdf
sentence-transformers
```

Em seguida, execute o comando de instalação:
```bash
pip install -r requirements.txt
```

### 4. Configurar as variáveis de ambiente
Crie um arquivo chamado `.env` na raiz do projeto e insira sua chave de API da Groq:

```env
GROQ_API_KEY="CHAVE_DE_API_DA_GROQ"
```

## 🚀 Como Executar o Projeto

Certifique-se de que o arquivo PDF da base de conhecimento esteja na raiz do diretório do projeto e execute o comando abaixo no terminal:

```bash
python -m streamlit run app.py
```

O aplicativo será aberto automaticamente no seu navegador padrão (geralmente em `http://localhost:8501`). Para interromper a execução do servidor, pressione `Ctrl + C` no terminal.

## 📁 Estrutura de Arquivos Recomendada

```text
📦 chatbot-farmaceutico-diabetes
 ┣ 📜 app.py                                       # Código principal da aplicação Streamlit e pipeline RAG
 ┣ 📜 Base_Unica_Diabetes_Posologia_Mapeada.xlsx   # Planilha original com os 5.761 registros mapeados
 ┣ 📜 Base_Unica_Diabetes_Posologia_Mapeada.pdf    # Documento PDF consumido pelo PyPDFLoader no RAG
 ┣ 📜 requirements.txt                             # Lista de dependências do Python
 ┣ 📜 .env                                         # Variáveis de ambiente (não versionado no Git)
 ┗ 📜 README.md                                    # Documentação do projeto
```

## ⚠️ Aviso Legal (Disclaimer Médico)

Este chatbot possui finalidade exclusivamente **educativa, acadêmica e informativa**. As respostas geradas pelo sistema são baseadas em dados de bulas e registros públicos, mas **não substituem, em hipótese alguma, a consulta, o diagnóstico ou a prescrição de um médico, endocrinologista ou farmacêutico profissional**. Nunca inicie, altere a dosagem ou interrompa o uso de medicamentos para diabetes sem orientação médica.
