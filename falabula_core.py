"""Núcleo do FalaBula: catálogo verificável, leitura de PDFs e recuperação segura.

Não utiliza serviços externos para reconhecer medicamentos ou listar a base.
A API Groq é acionada somente depois de selecionar a bula correta.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import hashlib
import math
import re
import unicodedata

CATALOGO = {
    "bula_Mounjaro.pdf": ("Mounjaro", ("mounjaro", "monjaro", "tirzepatida")),
    "bula_LANTUS_insulina_glargina.pdf": ("Lantus", ("lantus", "insulina glargina", "glargina")),
    "bula_InsulinaHumanaRegular.pdf": ("Wosulin R", ("wosulin", "insulina humana regular", "insulina regular")),
    "bula_InsulinaHumana_NovolinN.pdf": ("Novolin N", ("novolin", "insulina nph", "insulina humana nph")),
    "bula_empagliflozina.pdf": ("Empagliflozina", ("empagliflozina",)),
    "bula_dapagliflozina.pdf": ("Dapagliflozina", ("dapagliflozina",)),
    "bula_Januvia.pdf": ("Januvia", ("januvia", "sitagliptina")),
    "bula_glimepirida.pdf": ("Glimepirida", ("glimepirida",)),
    "bula_gliclazida.pdf": ("Gliclazida", ("gliclazida",)),
    "bula_glibenclamida.pdf": ("Glibenclamida", ("glibenclamida",)),
    "bula_glifagexr.pdf": ("Glifage XR", ("glifage xr",)),
    "bula_glifage.pdf": ("Glifage", ("glifage",)),
}

# Algumas palavras são comuns a muitos PDFs; não podem identificar um produto.
PALAVRAS_COMUNS = {
    "qual", "quais", "quero", "saber", "sobre", "para", "serve", "servem",
    "bula", "bulas", "medicamento", "medicamentos", "remedio", "remedios",
    "informacao", "informacoes", "com", "sem", "dos", "das", "uma", "por",
    "seus", "seja", "pode", "devo", "usar", "uso", "ter", "tem", "texto",
    "segundo", "nome", "nomes", "quero", "preciso", "liste", "lista",
    "cadastrados", "disponiveis", "projeto", "chatbot", "falabula",
    "efeitos", "colaterais", "indicacao", "indicacoes", "contraindicacoes",
}

def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", texto.lower()).strip()

def listar_arquivos(pasta: Path) -> list[Path]:
    return sorted(
        [p for p in pasta.glob("*.pdf") if p.is_file()],
        key=lambda p: p.name.casefold(),
    ) if pasta.is_dir() else []

def assinatura(arquivos: list[Path]) -> tuple:
    """Identifica alterações sem ler novamente cada PDF em cada mensagem."""
    return tuple(
        (p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in arquivos
    )

def nome_exibicao(nome_arquivo: str) -> str:
    if nome_arquivo in CATALOGO:
        return CATALOGO[nome_arquivo][0]
    return Path(nome_arquivo).stem.removeprefix("bula_").replace("_", " ")

def pergunta_catalogo(pergunta: str) -> bool:
    p = normalizar(pergunta)
    termos = ("medicamento", "remedio", "bula", "farmaco", "base de conhecimento")
    lista = (
        "quais", "liste", "listar", "lista", "relacao", "catalogo", "quantos",
        "todos", "disponiveis", "cadastrados", "registrados", "possui",
        "existem", "temos", "tem na base", "tem no sistema", "estao na base",
    )
    return (
        (any(x in p for x in termos) and any(x in p for x in lista))
        or p in ("o que voce conhece", "o que tem na base", "que medicamentos tem")
    )

def resposta_catalogo(arquivos: list[Path]) -> str:
    linhas = [f"{i}. {nome_exibicao(p.name)}" for i, p in enumerate(arquivos, 1)]
    return (
        f"Há **{len(arquivos)} bulas em PDF** na base do FalaBula:\n\n"
        + "\n".join(linhas)
        + "\n\nEsta lista corresponde aos arquivos cadastrados. "
        "Não confirma disponibilidade no SUS, Farmácia Popular ou estoque."
    )

def identificar_documentos(pergunta: str, arquivos: list[Path]) -> list[Path]:
    """Exige correspondência explícita e inequívoca com o nome/princípio ativo."""
    frase = " " + normalizar(pergunta) + " "
    # Normaliza também o erro comum Monjaro -> Mounjaro.
    frase = frase.replace(" monjaro ", " mounjaro ")
    correspondencias = {}
    for p in arquivos:
        if p.name in CATALOGO:
            apelidos = CATALOGO[p.name][1]
        else:
            apelidos = (normalizar(nome_exibicao(p.name)),)
        melhor = 0
        for alias in apelidos:
            token = " " + normalizar(alias) + " "
            if len(token.strip()) > 3 and token in frase:
                melhor = max(melhor, len(token.strip()))
        if melhor:
            correspondencias[p] = melhor

    # Um nome de marca específico prevalece sobre a forma genérica.
    # "Glifage XR" não deve retornar "Glifage" comum.
    if correspondencias:
        maior = max(correspondencias.values())
        return [p for p, nota in correspondencias.items() if nota == maior]

    return []

def carregar_paginas(arquivos: list[Path]) -> dict[str, list[tuple[int, str]]]:
    """Indexa somente texto legível. PDFs inválidos são reportados ao usuário."""
    from pypdf import PdfReader

    base = {}
    falhas = []
    for arquivo in arquivos:
        try:
            paginas = []
            for i, pagina in enumerate(PdfReader(str(arquivo)).pages, 1):
                texto = (pagina.extract_text() or "").strip()
                if texto:
                    paginas.append((i, texto))
            if not paginas:
                falhas.append(f"{arquivo.name}: não possui texto selecionável")
            else:
                base[arquivo.name] = paginas
        except Exception as erro:
            falhas.append(f"{arquivo.name}: PDF inválido ({type(erro).__name__})")
    if falhas:
        raise RuntimeError("Revise os documentos: " + "; ".join(falhas))
    return base

def foco(pergunta: str) -> str:
    p = normalizar(pergunta)
    if any(x in p for x in ("para que serve", "indicado", "indicacao", "indicações", "trata", "tratamento")):
        return "indicacao"
    if any(x in p for x in ("contraindic", "nao devo", "nao pode usar")):
        return "contraindicacao"
    if any(x in p for x in ("reacao adversa", "reacoes adversas", "efeito colateral", "efeitos colaterais", "males pode")):
        return "reacoes"
    if any(x in p for x in ("como usar", "posologia", "dose", "dosagem")):
        return "posologia"
    return "geral"

ANCORAS = {
    "indicacao": ("para que este medicamento e indicado", "indicacoes", "para que serve"),
    "contraindicacao": ("quando nao devo usar este medicamento", "contraindicacoes"),
    "reacoes": ("quais os males que este medicamento pode me causar", "reacoes adversas"),
    "posologia": ("como devo usar este medicamento", "posologia"),
}

def recuperar_paginas(pergunta: str, documentos: list[Path], base: dict,
                     limite: int = 4) -> list[tuple[str, int, str]]:
    """Nunca mistura medicamentos: busca apenas nos PDFs selecionados."""
    objetivo = foco(pergunta)
    termos = set(normalizar(pergunta).split()) - PALAVRAS_COMUNS
    candidatos = []
    for arquivo in documentos:
        for numero, texto in base.get(arquivo.name, []):
            conteudo = normalizar(texto)
            ocorrencias = sum(min(conteudo.count(t), 8) for t in termos if len(t) > 3)
            ancoras = ANCORAS.get(objetivo, ())
            bonus = 12 if any(a in conteudo for a in ancoras) else 0
            bonus += 2 if numero <= 3 else 0
            candidatos.append((bonus + ocorrencias, arquivo.name, numero, texto))

    candidatos.sort(key=lambda x: (-x[0], x[1], x[2]))
    saida = []
    for nota, nome, pagina, texto in candidatos[:limite]:
        # Textos longos são limitados para controlar custos e contexto.
        bruto = normalizar(texto)
        posicoes = [bruto.find(a) for a in ANCORAS.get(objetivo, ()) if a in bruto]
        # A pagina inteira, limitada, preserva a estrutura das instruções.
        saida.append((nome, pagina, texto[:4200]))
    return saida

def responder_pergunta(pergunta: str, arquivos: list[Path], base: dict,
                      api_key: str) -> tuple[str, list[str]]:
    if not arquivos:
        return "A pasta documentos não possui bulas PDF.", []
    if pergunta_catalogo(pergunta):
        return resposta_catalogo(arquivos), []

    encontrados = identificar_documentos(pergunta, arquivos)
    if not encontrados:
        return (
            "Não identifiquei um medicamento específico da base nesta pergunta. "
            "Informe o nome comercial ou princípio ativo, ou pergunte "
            "'Quais medicamentos estão cadastrados?'.", []
        )
    if len(encontrados) > 1:
        nomes = ", ".join(nome_exibicao(p.name) for p in encontrados)
        return f"Encontrei mais de uma bula correspondente: **{nomes}**. Especifique a apresentação.", []

    trechos = recuperar_paginas(pergunta, encontrados, base)
    if not trechos:
        return "Não foi possível extrair informações da bula selecionada.", []

    fontes = [f"{nome} — página {pagina}" for nome, pagina, _ in trechos]
    contexto = "\n\n".join(
        f"DOCUMENTO: {nome} | PÁGINA: {pagina}\n{texto}"
        for nome, pagina, texto in trechos
    )

    if not api_key:
        return (
            "A bula foi localizada, mas a chave da API Groq não está configurada. "
            "Verifique os Secrets do Streamlit.", fontes
        )

    # A seleção da bula ocorre antes de qualquer chamada ao modelo de linguagem.
    from groq import Groq
    mensagens = [
        {"role": "system", "content": (
            "Você é um assistente acadêmico de consulta a bulas. "
            "Responda em português claro somente com o texto da bula apresentada. "
            "Identifique o medicamento pelo nome da bula. "
            "Nunca invente dose, indicação, apresentação, tempo de ação, "
            "interação, contraindicação, fonte ou disponibilidade gratuita. "
            "Se o trecho não contém a resposta, declare que não foi possível "
            "confirmá-la nos trechos recuperados. "
            "Não faça diagnóstico, prescrição nem recomendação individual. "
            "Resuma somente informações pertinentes à pergunta. "
            "Não misture outros medicamentos. Cite o número da página quando útil."
        )},
        {"role": "user", "content": f"PERGUNTA: {pergunta}\n\nBULA SELECIONADA:\n{contexto}"}
    ]
    resultado = Groq(api_key=api_key, timeout=30.0).chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=mensagens,
        temperature=0,
        max_completion_tokens=900,
    )
    resposta = (resultado.choices[0].message.content or "").strip()
    if not resposta:
        raise RuntimeError("O serviço de geração retornou uma resposta vazia.")
    return resposta, fontes
