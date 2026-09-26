"""Testes do planilha_doctor. Rode: python -m pytest test_planilha.py -v"""
from pathlib import Path

import pytest

from planilha_doctor import (
    analisar_planilha,
    detectar_tipo_coluna,
    gerar_relatorio,
    limpar_valor,
    validar_cnpj,
    validar_cpf,
)


# ---------- Validadores ----------
class TestValidadores:
    def test_cpf_valido(self):
        assert validar_cpf("111.444.777-35") is True
        assert validar_cpf("11144477735") is True

    def test_cpf_invalido(self):
        assert validar_cpf("111.444.777-36") is False
        assert validar_cpf("111.111.111-11") is False
        assert validar_cpf("") is False

    def test_cnpj_valido(self):
        assert validar_cnpj("11.222.333/0001-81") is True

    def test_cnpj_invalido(self):
        assert validar_cnpj("11.222.333/0001-82") is False


# ---------- Detecção de tipo ----------
class TestDeteccao:
    def test_detecta_cpf(self):
        valores = ["111.444.777-35", "11144477735", "529.982.247-25"]
        assert detectar_tipo_coluna(valores) == "cpf"

    def test_cpf_tem_prioridade_sobre_telefone(self):
        # 11 dígitos cabem em ambos, mas CPF valida DV → ganha
        valores = ["111.444.777-35", "529.982.247-25"]
        assert detectar_tipo_coluna(valores) == "cpf"

    def test_detecta_email(self):
        valores = ["a@b.com", "c@d.com.br", "e@f.io"]
        assert detectar_tipo_coluna(valores) == "email"

    def test_detecta_telefone(self):
        # telefones genuínos (não são CPFs válidos)
        valores = ["11987654321", "(11) 98765-4321", "1134567890"]
        assert detectar_tipo_coluna(valores) == "telefone"

    def test_detecta_valor(self):
        valores = ["R$ 100", "R$ 1.234,56", "50,00"]
        assert detectar_tipo_coluna(valores) == "valor"

    def test_detecta_nome(self):
        valores = ["João Silva", "Maria Santos", "Pedro Alves"]
        assert detectar_tipo_coluna(valores) == "nome"

    def test_coluna_vazia_e_texto(self):
        assert detectar_tipo_coluna(["", ""]) == "texto"

    def test_coluna_mista_e_texto(self):
        valores = ["abc", "123", "xyz", "!@#", "texto"]
        assert detectar_tipo_coluna(valores) == "texto"


# ---------- Limpeza ----------
class TestLimpeza:
    def test_limpar_cpf(self):
        limpo, prob = limpar_valor("11144477735", "cpf")
        assert limpo == "111.444.777-35"
        assert prob is None

    def test_limpar_cpf_invalido(self):
        limpo, prob = limpar_valor("111.444.777-36", "cpf")
        assert prob is not None

    def test_limpar_email(self):
        limpo, prob = limpar_valor("  JOAO@EMPRESA.COM  ", "email")
        assert limpo == "joao@empresa.com"
        assert prob is None

    def test_limpar_telefone_celular(self):
        limpo, _ = limpar_valor("11987654321", "telefone")
        assert limpo == "(11) 98765-4321"

    def test_limpar_telefone_fixo(self):
        limpo, _ = limpar_valor("1134567890", "telefone")
        assert limpo == "(11) 3456-7890"

    def test_limpar_valor_com_rs(self):
        limpo, _ = limpar_valor("R$ 1.234,56", "valor")
        assert limpo == "1234.56"

    def test_limpar_valor_simples(self):
        limpo, _ = limpar_valor("50,00", "valor")
        assert limpo == "50.00"

    def test_limpar_cep(self):
        limpo, _ = limpar_valor("01304001", "cep")
        assert limpo == "01304-001"

    def test_limpar_data_br(self):
        limpo, _ = limpar_valor("25/09/2026", "data")
        assert limpo == "2026-09-25"

    def test_limpar_nome(self):
        limpo, _ = limpar_valor("joão da silva", "nome")
        assert limpo == "João da Silva"


# ---------- Integração ----------
class TestIntegracao:
    @pytest.fixture
    def csv_baguncado(self, tmp_path: Path) -> Path:
        p = tmp_path / "clientes.csv"
        p.write_text(
            "nome;cpf;email;telefone;valor\n"
            "joão silva;11144477735;JOAO@EMP.com;11987654321;1.234,56\n"
            "JOAO SILVA;111.444.777-35;joao@emp.com;(11) 98765-4321;R$ 1.234,56\n"
            "Maria Santos;529.982.247-25;maria@x.com;1134567890;50,00\n"
            "Pedro Alves;999.999.999-99;pedro@y.com;11912345678;100\n",
            encoding="utf-8",
        )
        return p

    def test_analisa_sem_erro(self, csv_baguncado):
        analise = analisar_planilha(csv_baguncado)
        assert analise["total_linhas"] == 4
        assert analise["tipos"]["cpf"] == "cpf"
        assert analise["tipos"]["email"] == "email"

    def test_detecta_cpf_invalido(self, csv_baguncado):
        analise = analisar_planilha(csv_baguncado)
        linhas_com_erro = [p["linha"] for p in analise["problemas"]]
        assert 5 in linhas_com_erro  # linha do Pedro (5ª linha do CSV)

    def test_detecta_duplicatas(self, csv_baguncado):
        analise = analisar_planilha(csv_baguncado)
        # joão silva e JOAO SILVA devem virar duplicata após limpeza
        assert len(analise["linhas_duplicadas"]) >= 1

    def test_relatorio_gerado(self, csv_baguncado):
        analise = analisar_planilha(csv_baguncado)
        relatorio = gerar_relatorio(analise)
        assert "DIAGNÓSTICO" in relatorio
        assert "COLUNAS DETECTADAS" in relatorio