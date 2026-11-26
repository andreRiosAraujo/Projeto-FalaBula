"""Testes de regressão do catálogo e isolamento entre bulas.

Executar: python -m unittest discover -s tests -v
"""
import tempfile
import unittest
from pathlib import Path

from falabula_core import (
    identificar_documentos,
    nome_exibicao,
    pergunta_catalogo,
    resposta_catalogo,
    recuperar_paginas,
    listar_arquivos,
)


class TestesFalaBula(unittest.TestCase):
    def setUp(self):
        self.temporario = tempfile.TemporaryDirectory()
        self.pasta = Path(self.temporario.name)
        self.nomes = (
            "bula_Mounjaro.pdf",
            "bula_glifage.pdf",
            "bula_glifagexr.pdf",
            "bula_dapagliflozina.pdf",
            "bula_LANTUS_insulina_glargina.pdf",
        )
        for nome in self.nomes:
            (self.pasta / nome).write_bytes(b"%PDF-test placeholder")
        self.arquivos = listar_arquivos(self.pasta)

    def tearDown(self):
        self.temporario.cleanup()

    def test_lista_completa_sem_modelo_de_ia(self):
        self.assertTrue(pergunta_catalogo("Liste todos os medicamentos disponíveis"))
        resposta = resposta_catalogo(self.arquivos)
        self.assertIn("5 bulas", resposta)
        for nome in self.nomes:
            self.assertIn(nome_exibicao(nome), resposta)

    def test_mounjaro_identificado_individualmente(self):
        encontrados = identificar_documentos(
            "Para que serve o Mounjaro (tirzepatida)?", self.arquivos
        )
        self.assertEqual([p.name for p in encontrados], ["bula_Mounjaro.pdf"])

    def test_monjaro_erro_de_grafia(self):
        encontrados = identificar_documentos(
            "Para que serve o Monjaro (tirzepatida)?", self.arquivos
        )
        self.assertEqual([p.name for p in encontrados], ["bula_Mounjaro.pdf"])

    def test_monjaro_sem_principio_ativo(self):
        encontrados = identificar_documentos(
            "O Monjaro tem contraindicações?", self.arquivos
        )
        self.assertEqual([p.name for p in encontrados], ["bula_Mounjaro.pdf"])

    def test_medicamento_especifico_nao_mistura_com_outros(self):
        encontrados = identificar_documentos(
            "Quais reações adversas da dapagliflozina?", self.arquivos
        )
        self.assertEqual([p.name for p in encontrados], ["bula_dapagliflozina.pdf"])

    def test_glifage_xr_tem_precedencia(self):
        encontrados = identificar_documentos(
            "Que cuidados há para Glifage XR?", self.arquivos
        )
        self.assertEqual([p.name for p in encontrados], ["bula_glifagexr.pdf"])

    def test_glifage_convencional(self):
        encontrados = identificar_documentos(
            "Contraindicações do Glifage?", self.arquivos
        )
        self.assertEqual([p.name for p in encontrados], ["bula_glifage.pdf"])

    def test_pergunta_sem_nome_nao_inventa_produto(self):
        encontrados = identificar_documentos(
            "Qual remédio trata pressão alta?", self.arquivos
        )
        self.assertEqual(encontrados, [])

    def test_recuperacao_somente_bula_selecionada(self):
        base = {
            "bula_Mounjaro.pdf": [
                (1, "MOUNJARO. Para que este medicamento é indicado? Diabetes tipo 2."),
            ],
            "bula_glifage.pdf": [
                (1, "GLIFAGE. Para que este medicamento é indicado? Metformina."),
            ],
        }
        selecionado = [self.pasta / "bula_Mounjaro.pdf"]
        trechos = recuperar_paginas("Para que serve o Mounjaro?", selecionado, base)
        self.assertEqual(len(trechos), 1)
        self.assertEqual(trechos[0][0], "bula_Mounjaro.pdf")
        self.assertNotIn("GLIFAGE", trechos[0][2])


if __name__ == "__main__":
    unittest.main()
