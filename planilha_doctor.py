"""
planilha_doctor — Auditor e faxineiro de planilhas brasileiras.

Pipeline híbrido:
    1. Camada de REGRAS (sempre roda): detecta tipos, limpa o que dá.
    2. Camada de IA (opcional): interpreta o que sobra.

Uso:
    python planilha_doctor.py clientes.csv
    python planilha_doctor.py clientes.csv --com-ia
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

__version__ = "0.1.0"
__all__ = [
    "detectar_tipo_coluna",
    "limpar_valor",
    "analisar_planilha",
    "gerar_relatorio",
    "validar_cpf",
    "validar_cnpj",
]


# =============================================================
# VALIDADORES (algoritmo módulo 11)
# =============================================================

def _apenas_digitos(s: str) -> str:
    return re.sub(r"\D", "", s)


def validar_cpf(cpf: str) -> bool:
    d = _apenas_digitos(cpf)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for i in (9, 10):
        soma = sum(int(d[j]) * ((i + 1) - j) for j in range(i))
        resto = soma % 11
        dv = 0 if resto < 2 else 11 - resto
        if int(d[i]) != dv:
            return False
    return True


def validar_cnpj(cnpj: str) -> bool:
    d = _apenas_digitos(cnpj)
    if len(d) != 14 or d == d[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    for pesos, pos in ((pesos1, 12), (pesos2, 13)):
        soma = sum(int(d[i]) * pesos[i] for i in range(len(pesos)))
        resto = soma % 11
        dv = 0 if resto < 2 else 11 - resto
        if int(d[pos]) != dv:
            return False
    return True


# =============================================================
# PADRÕES E DETECÇÃO DE TIPO
# =============================================================

_RE_EMAIL = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
_RE_CPF_FMT = re.compile(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$")
_RE_CNPJ_FMT = re.compile(r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$")
_RE_CEP = re.compile(r"^\d{5}-?\d{3}$")
_RE_DATA_BR = re.compile(r"^\d{2}/\d{2}/\d{4}$")
_RE_DATA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RE_VALOR_BR = re.compile(r"^(R\$\s*)?\d{1,3}(\.\d{3})*(,\d{2})?$")
_RE_NOME = re.compile(r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ' ]{2,60}$")


def _parece_cpf(v: str) -> bool:
    if _RE_CPF_FMT.match(v):
        return validar_cpf(v)
    return len(_apenas_digitos(v)) == 11 and validar_cpf(v)


def _parece_cnpj(v: str) -> bool:
    if _RE_CNPJ_FMT.match(v):
        return validar_cnpj(v)
    return len(_apenas_digitos(v)) == 14 and validar_cnpj(v)


def _parece_telefone(v: str) -> bool:
    d = _apenas_digitos(v)
    return len(d) in (10, 11) and d[0] != "0"


def _parece_valor(v: str) -> bool:
    if not _RE_VALOR_BR.match(v.strip()):
        return False
    return not _parece_cpf(v) and not _RE_CEP.match(v)


def _parece_nome(v: str) -> bool:
    if not _RE_NOME.match(v):
        return False
    palavras = v.split()
    return 2 <= len(palavras) <= 6


_DETECTORES = {
    "cpf": _parece_cpf,
    "cnpj": _parece_cnpj,
    "email": lambda v: bool(_RE_EMAIL.match(v)),
    "telefone": _parece_telefone,
    "cep": lambda v: bool(_RE_CEP.match(v)),
    "data": lambda v: bool(_RE_DATA_BR.match(v) or _RE_DATA_ISO.match(v)),
    "valor": _parece_valor,
    "nome": _parece_nome,
}


def detectar_tipo_coluna(valores: list[str], limiar: float = 0.6) -> str:
    """
    Detecta o tipo dominante de uma coluna.

    Usa ordem de PRIORIDADE: tipos com validação forte (CPF, CNPJ)
    são testados primeiro. Um CPF válido NÃO deve virar 'telefone'.
    """
    amostra = [v.strip() for v in valores if v and v.strip()][:100]
    if not amostra:
        return "texto"

    # Ordem importa: CPF/CNPJ primeiro porque têm validação de DV
    ordem_prioridade = [
        "cpf", "cnpj", "email", "cep", "data", "valor", "nome", "telefone",
    ]

    for tipo in ordem_prioridade:
        detector = _DETECTORES[tipo]
        acertos = sum(1 for v in amostra if detector(v))
        if acertos / len(amostra) >= limiar:
            return tipo
    return "texto"


# =============================================================
# LIMPEZA / NORMALIZAÇÃO
# =============================================================

def _titulo_br(nome: str) -> str:
    """'joão da silva' → 'João da Silva' (preposições minúsculas)."""
    minusculas = {"de", "da", "do", "das", "dos", "e", "di", "du"}
    return " ".join(
        p.lower() if p.lower() in minusculas else p.capitalize()
        for p in nome.split()
    )


def limpar_valor(valor: str, tipo: str) -> tuple[str, str | None]:
    """
    Limpa um valor de acordo com o tipo.
    Retorna (valor_limpo, problema_ou_None).
    """
    v = valor.strip()

    if tipo == "cpf":
        d = _apenas_digitos(v)
        if len(d) != 11:
            return v, "CPF com tamanho inválido"
        if not validar_cpf(v):
            return v, "CPF com dígito verificador inválido"
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}", None

    if tipo == "cnpj":
        d = _apenas_digitos(v)
        if not validar_cnpj(v):
            return v, "CNPJ com dígito verificador inválido"
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}", None

    if tipo == "email":
        v2 = v.lower()
        if not _RE_EMAIL.match(v2):
            return v, "E-mail com formato inválido"
        return v2, None

    if tipo == "telefone":
        d = _apenas_digitos(v)
        if len(d) == 11:
            return f"({d[:2]}) {d[2:7]}-{d[7:]}", None
        if len(d) == 10:
            return f"({d[:2]}) {d[2:6]}-{d[6:]}", None
        return v, "Telefone com tamanho inválido"

    if tipo == "cep":
        d = _apenas_digitos(v)
        if len(d) != 8:
            return v, "CEP com tamanho inválido"
        return f"{d[:5]}-{d[5:]}", None

    if tipo == "valor":
        s = v.replace("R$", "").strip().replace(".", "").replace(",", ".")
        try:
            return f"{float(s):.2f}", None
        except ValueError:
            return v, "Valor não numérico"

    if tipo == "data":
        if _RE_DATA_BR.match(v):
            d, m, a = v.split("/")
            return f"{a}-{m}-{d}", None
        return v, None

    if tipo == "nome":
        return _titulo_br(v), None

    return v, None


# =============================================================
# ANÁLISE PRINCIPAL
# =============================================================

def _chave_dedup(linha: dict) -> tuple:
    """Chave para detectar duplicatas ignorando acentos e maiúsculas."""
    def normalizar(s: str) -> str:
        s = unicodedata.normalize("NFKD", str(s))
        s = s.encode("ascii", "ignore").decode("ascii")
        return s.lower().strip()
    return tuple(sorted((k, normalizar(v)) for k, v in linha.items()))


def analisar_planilha(caminho: Path) -> dict:
    """Lê o CSV, detecta tipos e limpa tudo. Retorna dict estruturado."""
    with caminho.open("r", encoding="utf-8-sig", newline="") as f:
        # Tenta detectar o delimitador automaticamente
        amostra = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(amostra, delimiters=";,\t")
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ","

        reader = csv.DictReader(f, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError("CSV vazio ou sem cabeçalho")
        linhas = [dict(r) for r in reader]
        colunas = list(reader.fieldnames)

    # 1. Detectar tipo de cada coluna
    tipos: dict[str, str] = {}
    for col in colunas:
        valores = [str(r.get(col, "")) for r in linhas]
        tipos[col] = detectar_tipo_coluna(valores)

    # 2. Limpar cada célula
    linhas_limpas: list[dict] = []
    problemas: list[dict] = []
    for i, linha in enumerate(linhas, start=2):
        nova = {}
        problemas_da_linha: list[str] = []
        for col in colunas:
            bruto = str(linha.get(col, "") or "")
            tipo = tipos[col]
            limpo, problema = limpar_valor(bruto, tipo)
            nova[col] = limpo
            if problema:
                problemas_da_linha.append(f"{col}: {problema} (valor: '{bruto}')")
        linhas_limpas.append(nova)
        if problemas_da_linha:
            problemas.append({"linha": i, "erros": problemas_da_linha})

    # 3. Detecta duplicatas ignorando acentos e maiúsculas
    chaves = [_chave_dedup(r) for r in linhas_limpas]
    contagem = Counter(chaves)
    duplicatas = [i + 2 for i, k in enumerate(chaves) if contagem[k] > 1]

    return {
        "caminho": str(caminho),
        "total_linhas": len(linhas),
        "colunas": colunas,
        "tipos": tipos,
        "linhas_limpas": linhas_limpas,
        "problemas": problemas,
        "linhas_duplicadas": sorted(set(duplicatas)),
    }


# =============================================================
# RELATÓRIO
# =============================================================

def gerar_relatorio(analise: dict, ia_resultado: dict | None = None) -> str:
    """Gera relatório em texto legível para o gestor."""
    linhas = []
    linhas.append("=" * 60)
    linhas.append(f"📋 DIAGNÓSTICO — {Path(analise['caminho']).name}")
    linhas.append("=" * 60)
    linhas.append(f"📊 {analise['total_linhas']} linhas, {len(analise['colunas'])} colunas")
    linhas.append("")

    linhas.append("COLUNAS DETECTADAS:")
    emojis = {
        "cpf": "🪪", "cnpj": "🏢", "email": "📧", "telefone": "📞",
        "cep": "📮", "data": "📅", "valor": "💰", "nome": "👤", "texto": "📝",
    }
    for col in analise["colunas"]:
        tipo = analise["tipos"][col]
        emoji = emojis.get(tipo, "📝")
        linhas.append(f"  {emoji} {col:<20} → {tipo}")
    linhas.append("")

    if analise["problemas"]:
        linhas.append(f"⚠️  {len(analise['problemas'])} linha(s) com problema:")
        for p in analise["problemas"][:10]:
            linhas.append(f"  Linha {p['linha']}:")
            for e in p["erros"]:
                linhas.append(f"    • {e}")
        if len(analise["problemas"]) > 10:
            linhas.append(f"  ... e mais {len(analise['problemas']) - 10} linhas")
    else:
        linhas.append("✅ Nenhum problema encontrado nas linhas.")
    linhas.append("")

    if analise["linhas_duplicadas"]:
        linhas.append(
            f"⚠️  {len(analise['linhas_duplicadas'])} linha(s) duplicada(s): "
            f"{analise['linhas_duplicadas'][:10]}"
        )
    else:
        linhas.append("✅ Nenhuma linha duplicada.")
    linhas.append("")

    if ia_resultado:
        linhas.append("=" * 60)
        linhas.append("🤖 ANÁLISE DA IA")
        linhas.append("=" * 60)
        for col, info in ia_resultado.get("colunas", {}).items():
            linhas.append(f"  {col}:")
            linhas.append(f"    → {info.get('interpretacao', '?')}")
            if info.get("alerta"):
                linhas.append(f"    ⚠️  {info['alerta']}")
        linhas.append("")

    return "\n".join(linhas)


# =============================================================
# SAÍDA
# =============================================================

def salvar_resultados(analise: dict, caminho_origem: Path, com_ia: bool) -> None:
    base = caminho_origem.stem
    pasta = caminho_origem.parent

    # 1. CSV limpo
    limpo = pasta / f"{base}_limpo.csv"
    with limpo.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=analise["colunas"], delimiter=";")
        w.writeheader()
        w.writerows(analise["linhas_limpas"])
    print(f"  ✅ {limpo}")

    # 2. CSV problemas
    if analise["problemas"]:
        prob = pasta / f"{base}_problemas.csv"
        with prob.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["linha", "erros"])
            for p in analise["problemas"]:
                w.writerow([p["linha"], " | ".join(p["erros"])])
        print(f"  ✅ {prob}")

    # 3. Relatório
    ia_resultado = None
    if com_ia:
        try:
            from ia_connector import analisar_com_ia
            print("  🤖 Consultando IA...")
            ia_resultado = analisar_com_ia(analise)
        except ImportError:
            print("  ⚠️  ia_connector não disponível. Pulando análise de IA.")
        except Exception as e:
            print(f"  ⚠️  IA falhou: {e}. Continuando só com regras.")

    relatorio = pasta / f"{base}_relatorio.txt"
    relatorio.write_text(gerar_relatorio(analise, ia_resultado), encoding="utf-8")
    print(f"  ✅ {relatorio}")


# =============================================================
# CLI
# =============================================================

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="planilha_doctor",
        description="Auditor e faxineiro de planilhas brasileiras.",
    )
    parser.add_argument("arquivo", type=Path, help="Caminho do CSV")
    parser.add_argument(
        "--com-ia", action="store_true",
        help="Ativa a camada de IA (requer OPENAI_API_KEY)",
    )
    parser.add_argument("--versao", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args(argv)

    if not args.arquivo.exists():
        print(f"❌ Arquivo não encontrado: {args.arquivo}", file=sys.stderr)
        return 1

    print(f"🔍 Analisando {args.arquivo}...")
    try:
        analise = analisar_planilha(args.arquivo)
    except Exception as e:
        print(f"❌ Erro ao ler planilha: {e}", file=sys.stderr)
        return 1

    print(f"📊 {analise['total_linhas']} linhas, {len(analise['colunas'])} colunas")
    print("📄 Gerando saídas:")
    salvar_resultados(analise, args.arquivo, com_ia=args.com_ia)

    print("")
    print(gerar_relatorio(analise))
    return 0


if __name__ == "__main__":
    sys.exit(main())