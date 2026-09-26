"""
ia_connector — Camada de IA opcional do planilha_doctor.

Roda APENAS quando:
    1. O usuário passa --com-ia
    2. A variável OPENAI_API_KEY está definida no ambiente
    3. O pacote `openai` está instalado

Caso contrário, degrada silenciosamente (retorna {}).
"""
from __future__ import annotations

import json
import os

MODELO = "gpt-4o-mini"  # barato e suficiente para interpretação

_PROMPT_SISTEMA = """\
Você é um analista de dados brasileiro. Recebe metadados de colunas de uma \
planilha e devolve, em JSON estrito, sua interpretação sobre cada uma.

Para cada coluna, retorne:
- "interpretacao": o que a coluna parece representar (1 frase curta)
- "alerta": problema provável ou null

Responda APENAS com JSON válido, sem markdown, sem comentários.

Formato exato:
{
  "colunas": {
    "<nome_coluna>": {"interpretacao": "...", "alerta": null}
  }
}
"""


def _montar_payload(analise: dict) -> str:
    """Resume a planilha em algo enxuto pra mandar à IA."""
    resumo = {}
    for col in analise["colunas"]:
        amostra = [
            str(r.get(col, "")) for r in analise["linhas_limpas"][:5]
            if r.get(col, "")
        ]
        resumo[col] = {
            "tipo_detectado": analise["tipos"][col],
            "amostra": amostra,
        }
    return json.dumps(resumo, ensure_ascii=False, indent=2)


def analisar_com_ia(analise: dict) -> dict:
    """
    Envia metadados das colunas pra IA e retorna interpretação estruturada.
    Retorna {} se a IA não estiver disponível.
    """
    if not os.getenv("OPENAI_API_KEY"):
        return {}

    try:
        from openai import OpenAI
    except ImportError:
        return {}

    client = OpenAI()
    payload = _montar_payload(analise)

    response = client.chat.completions.create(
        model=MODELO,
        messages=[
            {"role": "system", "content": _PROMPT_SISTEMA},
            {"role": "user", "content": payload},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    try:
        return json.loads(response.choices[0].message.content or "{}")
    except json.JSONDecodeError:
        return {}