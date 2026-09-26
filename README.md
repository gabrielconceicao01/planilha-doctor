<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0d6efd&height=200&section=header&text=planilha-doctor&fontSize=70&fontColor=ffffff&animation=fadeIn&fontAlignY=38&desc=Auditor%20e%20faxineiro%20de%20planilhas%20brasileiras&descAlignY=58&descSize=18" width="100%" />

### Regras quando bastam. IA quando necessário.

[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Tests](https://img.shields.io/badge/tests-26%20passed-2ea44f?style=for-the-badge&logo=pytest&logoColor=white)](https://github.com/gabrielconceicao01/planilha-doctor)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-blueviolet?style=for-the-badge)](#)
[![License](https://img.shields.io/badge/license-MIT-yellow?style=for-the-badge)](LICENSE)
[![Made in Brazil](https://img.shields.io/badge/made%20in-Brasil-009c3b?style=for-the-badge)](#)

[🎯 O problema](#-o-problema) · [⚡ Quickstart](#-quickstart) · [🧠 Arquitetura](#-arquitetura-híbrida) · [🤖 IA](#-camada-de-ia-opcional) · [🗺️ Roadmap](#%EF%B8%8F-roadmap)

</div>

---

## 📌 Índice

- [O problema](#-o-problema)
- [A solução](#-a-solução)
- [Quickstart](#-quickstart)
- [O que ele faz](#-o-que-ele-faz)
- [Arquitetura híbrida](#-arquitetura-híbrida)
- [Camada de IA (opcional)](#-camada-de-ia-opcional)
- [Testes](#-testes)
- [Casos de uso](#-casos-de-uso-reais)
- [Design principles](#-design-principles)
- [Roadmap](#%EF%B8%8F-roadmap)
- [Contribuindo](#-contribuindo)
- [Licença](#-licença)

---

## 🎯 O problema

Todo analista de dados brasileiro conhece essa cena: você recebe uma planilha de 5.000 clientes e precisa **limpar antes de usar**. Aí descobre que:

- 300 CPFs estão com dígito verificador errado
- "João Silva" aparece 3 vezes com formatação diferente (`joão silva`, `JOAO SILVA`, `João Silva`)
- Telefones vêm com e sem DDD, com e sem hífen, às vezes como `11987654321`
- Valores estão metade em `R$ 1.234,56` e metade em `1,234.56` (formato americano)
- E-mails têm maiúsculas, espaços no começo, formato inválido

**Isso leva horas.** E o pior: **tem que ser refeito toda vez**.

Ferramentas existentes?

- **Excel / Google Sheets:** não valida CPF, não deduplica inteligente
- **OpenRefine:** poderoso, mas complexo, Java, sem validação BR
- **Trifacta / Talend:** enterprise, caro, em inglês
- **pandas:** você *escreve* o script toda vez, do zero

**Ninguém fez um "Excel de qualidade pra dados brasileiros".** Até agora.

---

## 💡 A solução

`planilha-doctor` analisa um CSV e devolve **3 arquivos**:

1. `clientes_limpo.csv` — planilha normalizada, pronta pra usar
2. `clientes_problemas.csv` — só as linhas com erro, pra revisar
3. `clientes_relatorio.txt` — diagnóstico legível pro gestor

E faz isso em **3 segundos**.

```bash
python planilha_doctor.py clientes.csv
```

**Saída:**

```
📋 DIAGNÓSTICO — clientes.csv
═══════════════════════════════════════
📊 5 linhas, 5 colunas

COLUNAS DETECTADAS:
  👤 nome      → nome
  🪪 cpf       → cpf
  📧 email     → email
  📞 telefone  → telefone
  💰 valor     → valor

⚠️  1 linha(s) com problema:
  Linha 5:
    • cpf: CPF com dígito verificador inválido (valor: '999.999.999-99')

⚠️  2 linha(s) duplicada(s): [2, 3]
```

---

## ⚡ Quickstart

```bash
git clone https://github.com/gabrielconceicao01/planilha-doctor.git
cd planilha-doctor
python -m pip install pytest

python planilha_doctor.py clientes.csv
```

**Zero dependências obrigatórias.** IA é opcional e plugável.

---

## 📋 O que ele faz

### Detecta tipo de cada coluna automaticamente

Sem você falar "essa coluna é CPF". Ele testa cada padrão nos dados e escolhe o tipo dominante.

| Tipo | Emoji | Como detecta |
|---|---|---|
| Nome | 👤 | 2–6 palavras com letras (aceita acentos) |
| CPF | 🪪 | 11 dígitos + validação de DV (módulo 11) |
| CNPJ | 🏢 | 14 dígitos + validação de DV |
| E-mail | 📧 | Regex RFC-compatível |
| Telefone | 📞 | 10 ou 11 dígitos, DDD válido |
| CEP | 📮 | 8 dígitos com ou sem hífen |
| Data | 📅 | `DD/MM/AAAA` ou `AAAA-MM-DD` |
| Valor | 💰 | Formato BR (`R$ 1.234,56`) |

### Prioridade inteligente

CPF e CNPJ são testados **primeiro** porque têm validação de dígito verificador. Um CPF `111.444.777-35` tem 11 dígitos — igual a um celular. Mas só o CPF valida matematicamente. **O detector sabe disso.**

### Limpa e normaliza

| Tipo | Antes | Depois |
|---|---|---|
| **CPF** | `11144477735` | `111.444.777-35` |
| **CNPJ** | `11222333000181` | `11.222.333/0001-81` |
| **E-mail** | `  JOAO@EMPRESA.COM  ` | `joao@empresa.com` |
| **Telefone** | `11987654321` | `(11) 98765-4321` |
| **CEP** | `01304001` | `01304-001` |
| **Data** | `25/09/2026` | `2026-09-25` |
| **Valor** | `R$ 1.234,56` | `1234.56` |
| **Nome** | `joão da silva` | `João da Silva` |

*Preposições (`de`, `da`, `do`) ficam minúsculas, como manda a norma culta.*

### Detecta duplicatas ignorando acento e caixa

`joão silva` e `JOAO SILVA` **são a mesma pessoa**. O sistema normaliza antes de comparar (remove acentos, lowercase).

### Gera relatório legível

O gestor entende. Não precisa saber Python.

---

## 🧠 Arquitetura híbrida

A parte que **diferencia este projeto de todos os outros**:

```
       CSV bagunçado
            │
            ▼
    ┌───────────────────┐
    │  CAMADA 1         │  ← grátis, instantâneo, determinístico
    │  REGRAS + REGEX   │
    │  (CPF, email, tel)│
    └───────────────────┘
            │
            ▼
    ┌───────────────────┐
    │  CAMADA 2         │  ← só roda onde a camada 1 não decidiu
    │  IA (OpenAI)      │     (com `--com-ia` e API key)
    │  interpretação    │
    └───────────────────┘
            │
            ▼
    ┌───────────────────┐
    │  RELATÓRIO        │
    │  + CSV limpo      │
    └───────────────────┘
```

### Por que não usar só IA?

Porque **regex é 17.000x mais rápido** que uma chamada de LLM, **custa zero** e **é determinístico**. IA alucina. Regex não.

### Por que não usar só regras?

Porque regra não entende contexto. Ela não sabe dizer *"essa coluna parece 'cidade', mas tem CEP misturado"*. IA sabe.

**A sacada:** cada camada faz o que ela faz de melhor. A IA **não substitui** as regras — ela **cobre o que sobra**.

| Tarefa | Camada | Custo |
|---|---|---|
| Validar CPF, CNPJ, e-mail | Regra | Zero |
| Normalizar telefone, CEP, data | Regra | Zero |
| Detectar tipo de coluna | Regra | Zero |
| Detectar duplicatas (com/sem acento) | Regra | Zero |
| Interpretar *"o que essa coluna significa"* | **IA** | ~$0.0001 |
| Alertar sobre anomalia semântica | **IA** | ~$0.0001 |

---

## 🤖 Camada de IA (opcional)

Se você tem uma API key da OpenAI, ligue a camada de IA:

```bash
pip install openai

# Linux/Mac
export OPENAI_API_KEY="sk-..."

# Windows PowerShell
$env:OPENAI_API_KEY="sk-..."

python planilha_doctor.py clientes.csv --com-ia
```

A IA **não toca nos dados** — só recebe **metadados** (nome da coluna, tipo detectado, 5 exemplos). Ela devolve:

```json
{
  "colunas": {
    "cliente_nome": {
      "interpretacao": "Nome completo do cliente",
      "alerta": null
    },
    "cod": {
      "interpretacao": "Código interno de cliente",
      "alerta": "Formato parece inconsistente entre linhas"
    }
  }
}
```

**Custo por planilha: ~$0.0001.** Porque só manda amostra pequena e usa `gpt-4o-mini`.

### Como conectar outros provedores (Claude, Gemini, local)

Edite `ia_connector.py`. A interface é uma função só:

```python
def analisar_com_ia(analise: dict) -> dict:
    """Recebe o resultado da análise por regras, retorna JSON."""
```

Troca o cliente OpenAI pelo que você quiser. Anthropic, Gemini, Ollama local — tudo funciona.

---

## 🧪 Testes

```bash
python -m pytest test_planilha.py -v
```

**26 testes** organizados em 4 classes:

| Classe | Cobre |
|---|---|
| `TestValidadores` | CPF e CNPJ puros |
| `TestDeteccao` | Detecção automática de tipo de coluna |
| `TestLimpeza` | Normalização campo por campo |
| `TestIntegracao` | Pipeline completo com CSV realista |

```
======================= 26 passed in 14.61s =======================
```

---

## 💼 Casos de uso reais

<table>
<tr>
<td width="50%">

### 📊 CRM / Vendas

Limpar lista de leads antes de importar no Pipedrive, HubSpot ou Salesforce.

```bash
python planilha_doctor.py leads.csv
# → leads_limpo.csv pronto pra importar
```

</td>
<td width="50%">

### 👥 RH / Pessoas

Validar base de funcionários antes de rodar folha de pagamento.

```bash
python planilha_doctor.py funcionarios.csv
# → detecta CPFs inválidos antes de dar erro
```

</td>
</tr>
<tr>
<td width="50%">

### 📈 Data / BI

Pré-processar dados antes de jogar no Looker, Metabase ou Power BI.

```bash
python planilha_doctor.py extrato.csv
# → extrato_limpo.csv + relatório de qualidade
```

</td>
<td width="50%">

### 💰 Contabilidade

Auditar planilha de clientes antes de fechar o mês.

```bash
python planilha_doctor.py recebiveis.csv
# → relatório com CPF/CNPJ inválidos
```

</td>
</tr>
<tr>
<td width="50%">

### 📣 Marketing

Deduplicar lista de e-mails antes de disparar campanha.

```bash
python planilha_doctor.py base_email.csv
# → remove duplicatas ignorando caixa e acentos
```

</td>
<td width="50%">

### ⚖️ Jurídico

Verificar CPF/CNPJ em massa antes de abrir processo.

```bash
python planilha_doctor.py partes.csv
# → lista só dos CPFs/CNPJs válidos
```

</td>
</tr>
</table>

---

## 🎨 Design principles

Esta lib foi desenhada com **4 regras não negociáveis**:

### 1. Regras primeiro, IA depois

Regex custa zero, IA custa dinheiro. Use IA só pra o que ela é insubstituível: **interpretar contexto**.

### 2. Zero dependências obrigatórias

Se der pra fazer com `csv` e `re`, faz. Só usa IA se você quiser. O projeto funciona 100% offline por padrão.

### 3. Fail-soft

Se a IA falhar, o sistema continua funcionando com as regras. Se uma célula estiver zoada, ela vira problema e a linha vai pra revisão — sem quebrar tudo.

### 4. Determinístico > inteligente

Validação de CPF tem que dar sempre o mesmo resultado. Regex garante isso. LLM não.

---

## 🗺️ Roadmap

### ✅ Fase 1 — Fundação *(completa)*

- [x] Ler CSV (com autodetecção de delimitador `;`, `,` ou `\t`)
- [x] Detectar tipo de cada coluna
- [x] Validar e normalizar CPF, CNPJ, e-mail, telefone, CEP, data, valor, nome
- [x] Detectar duplicatas ignorando acentos
- [x] Gerar relatório + 2 CSVs de saída
- [x] Camada de IA plugável (OpenAI)
- [x] 26 testes automatizados

### 🚧 Fase 2 — Mais formatos

- [ ] Suporte a Excel (`.xlsx`)
- [ ] Suporte a JSON / NDJSON
- [ ] Leitura direta do Google Sheets (via API)

### 🔮 Fase 3 — Inteligência

- [ ] Dedup fuzzy ("joao silva" vs "j silva")
- [ ] Ordenação configurável por coluna
- [ ] Comparação entre 2 planilhas (quem está em A mas não em B)
- [ ] Detecção de endereço estruturado (rua, número, bairro, cidade, UF)

### 🌎 Fase 4 — Produto

- [ ] Publicação no PyPI (`pip install planilha-doctor`)
- [ ] GitHub Actions com CI
- [ ] CLI com `rich` (saída colorida)
- [ ] Versão Web (upload → download)
- [ ] Plugin para VS Code / Jupyter

---

## 🤝 Contribuindo

Contribuições são muito bem-vindas! Áreas que precisam de ajuda:

### 🧠 Conhecimento de domínio
- Algoritmos adicionais (Cartão SUS, RENAVAM, Inscrição Estadual)
- Regras de validação regionais

### 📊 Formatos
- Parser para Excel sem openpyxl (puro Python)
- Integração com Google Sheets API

### 🌎 Internacionalização
- Suporte a espanhol (Argentina, Chile, México)

### 📝 Testes
- Casos reais (planilhas públicas do governo, dados do Kaggle)
- Property-based testing com Hypothesis

### Como enviar um PR

1. Abra uma [issue](https://github.com/gabrielconceicao01/planilha-doctor/issues)
2. Faça um fork
3. Crie uma branch: `git checkout -b feature/nova-feature`
4. Commit: `git commit -m "feat: adiciona suporte a xlsx"`
5. Push: `git push origin feature/nova-feature`
6. Abra um Pull Request

**Padrão:** [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`).

---

## 💡 Inspiração

- [`brdoc`](https://github.com/gabrielconceicao01/brdoc) — lib irmã para validação de documentos
- [`jeitinho`](https://github.com/gabrielconceicao01/jeitinho) — contexto brasileiro para IAs
- [`OpenRefine`](https://openrefine.org/) — inspiração em limpeza de dados
- A dor real de todo analista de dados brasileiro ✨

---

## 📜 Licença

Distribuído sob a licença **MIT**. Usa, modifica, vende, faz o que quiser — sem pedir permissão, sem pagar royalties.

Veja [LICENSE](LICENSE) para o texto completo.

---

## 📮 Contato

- **Autor:** Gabriel Conceição
- **GitHub:** [@gabrielconceicao01](https://github.com/gabrielconceicao01)
- **Issues:** [abrir uma issue](https://github.com/gabrielconceicao01/planilha-doctor/issues)

---

<div align="center">

### Se esse projeto te ajudou, deixa uma ⭐

Faz diferença pra quem tá começando e precisa de visibilidade.

[⬆ Voltar ao topo](#-planilha-doctor)

<br />

<sub>Feito com 🧠 e ☕ no Brasil 🇧🇷</sub>

</div>
