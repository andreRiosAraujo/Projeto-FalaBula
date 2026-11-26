# FalaBula — Assistente de consulta a bulas (RAG)

**[Acessar o FalaBula online](https://projeto-falabula-dashshp2g9tj3fr9jop2yv.streamlit.app/)**

Projeto acadêmico de chatbot que responde a perguntas em português sobre **medicamentos documentados nas bulas cadastradas**, utilizando recuperação de informações (RAG). A aplicação foi preparada para receber documentos de outras áreas terapêuticas, sem depender de uma doença específica.

> **Atenção:** conteúdo informativo, não é diagnóstico, prescrição nem orientação de tratamento individual. Não inicie, altere ou interrompa medicamentos com base nas respostas. Consulte profissional habilitado.

## Situação da base documental

- A pasta `documentos/` contém **12 PDFs recebidos pela equipe** na [pasta compartilhada no Google Drive](https://drive.google.com/drive/folders/1pw05qc4SeUuLskEq6FS0q0vY1_n5jcBM).
- Nesta etapa, os documentos são predominantemente relacionados a **diabetes e condições associadas**. A arquitetura é genérica, mas **a cobertura de outras enfermidades dependerá do cadastro de novas bulas**.
- A origem regulatória, atualização, laboratório e validade de cada PDF devem ser conferidos pela equipe antes de considerá-lo uma fonte oficial atualizada. A existência do arquivo no Drive não constitui essa validação.
- Os arquivos antigos `Base_Unica_Diabetes_Posologia_Mapeada.pdf` e `GuiaDiabetes.pdf` permanecem na raiz como legado; **a nova interface `frontend.py` consulta somente a pasta `documentos/`**.

## Adicionar, substituir ou retirar bulas

1. Obter o PDF de fonte confiável, preferencialmente no [Bulário Eletrônico da Anvisa](https://consultas.anvisa.gov.br/#/bulario/), conferindo o medicamento, apresentação, fabricante e data da revisão.
2. Colocar o PDF na pasta `documentos/`, mantendo um nome de arquivo identificável. O arquivo deve possuir texto selecionável: PDFs de imagem sem texto exigem preparação anterior.
3. Para execução local, salvar o arquivo nessa pasta e atualizar a página; o índice vetorial é refeito **na próxima consulta** quando for detectada inclusão, alteração ou remoção de arquivos.
4. Para a versão online do Streamlit, enviar o PDF ao diretório `documentos/` na branch `main` do GitHub. O Streamlit deve implantar a atualização; depois da implantação, a próxima consulta reconstrói a base. **Editar apenas o Google Drive não atualiza automaticamente o GitHub nem a aplicação.**
5. Testar consultas sobre indicações, contraindicações, efeitos adversos e ausência de informação. Evitar documentos duplicados, versões conflitantes ou não verificadas.

A atualização é uma **reindexação de documentos**, não o treinamento ou ajuste dos pesos do modelo de linguagem. A primeira consulta após mudanças pode ser mais lenta e usar recursos de memória; muitos PDFs grandes podem exceder os limites de hospedagem gratuita.

## Como executar no computador

Requisitos: Python 3.10+ e acesso à Groq.

```bash
git clone https://github.com/andreRiosAraujo/Projeto-FalaBula.git
cd Projeto-FalaBula
python -m venv .venv
# Windows: .venv\Scripts\python.exe -m pip install -r requirements.txt
# macOS/Linux: .venv/bin/python -m pip install -r requirements.txt
python -m pip install -r requirements.txt
```

Crie um arquivo local `.env` com a chave:

```env
GROQ_API_KEY=COLE_SUA_CHAVE_AQUI
```

Execute:

```bash
python -m streamlit run frontend.py
```

A aplicação abre normalmente em http://localhost:8501. Para execução online, configure `GROQ_API_KEY` no campo privado **Secrets** da aplicação Streamlit, nunca no GitHub. Em implantações com escopo de segredos do Streamlit, a variável precisa estar disponível ao processo.

## Arquitetura

1. **Frontend** — `frontend.py` e `style.css`, com tela de acesso demonstrativa (sem autenticação) e chat responsivo.
2. **Documentos** — PDFs em `documentos/`, listados automaticamente.
3. **Leitura** — `PyPDFLoader` e divisão do texto em trechos com sobreposição.
4. **Indexação** — embeddings do modelo `sentence-transformers/all-MiniLM-L6-v2` e banco vetorial Chroma.
5. **Consulta** — recuperação dos cinco trechos de maior similaridade e geração de respostas pela API Groq (`openai/gpt-oss-120b`).
6. **Rastreabilidade** — cada resposta apresenta, em uma seção expansível, os nomes dos PDFs e as páginas dos trechos recuperados. Essa lista é uma trilha de recuperação, não uma garantia automática de correção de cada afirmação.
7. **Atualização da base** — assinatura SHA-256 dos PDFs usada para invalidar o índice em cache quando os documentos mudam.

O arquivo `app.py` original **não foi modificado** e ainda representa o fluxo legado sobre diabetes; para a nova experiência, execute **`frontend.py`**.

## Perguntas de validação inicial

- Para que serve o Mounjaro, segundo a bula?
- Quais contraindicações constam na bula do Glifage?
- Que cuidados a bula do Lantus informa?
- Quais reações adversas constam na bula do Januvia?
- O FalaBula possui informações documentadas sobre um medicamento que ainda não está na pasta?
- Uma bula prova que o medicamento está disponível no Farmácia Popular? (Resposta esperada: **não**; exige fonte oficial específica e atualizada.)

**Observação:** a resposta de IA pode conter erros. Confira sempre o conteúdo integral da bula e seus dados de referência; não use a aplicação para decisões clínicas.

## Organização do repositório

```text
Projeto-FalaBula/
├── documentos/       # PDFs indexados automaticamente pelo frontend
├── frontend.py       # aplicação atual, genérica
├── style.css         # estilos responsivos
├── requirements.txt  # dependências
├── app.py            # aplicação antiga (preservada)
├── GuiaDiabetes.pdf  # legado
├── Base_Unica_Diabetes_Posologia_Mapeada.pdf  # legado
└── README.md
```

## Histórico e preservação

Antes da atualização, foi criada a branch de segurança [`backup/antes-base-dinamica-2026-11-26`](https://github.com/andreRiosAraujo/Projeto-FalaBula/tree/backup/antes-base-dinamica-2026-11-26). Os arquivos originais permanecem recuperáveis nessa referência.

## Responsabilidade

Este é um protótipo acadêmico. As respostas são limitadas às bulas presentes na pasta `documentos/`. Informações sobre disponibilidade no SUS, Farmácia Popular, preços, estoque e elegibilidade devem ser verificadas em fontes governamentais atuais, não deduzidas de bulas.
