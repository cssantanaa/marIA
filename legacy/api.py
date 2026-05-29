"""
MarIA — API REST (FastAPI)
==========================
Expõe os resultados do pipeline via endpoints HTTP documentados.

Swagger UI disponível em: http://localhost:8000/docs
ReDoc disponível em:      http://localhost:8000/redoc

Iniciar servidor:
  uvicorn api:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "agentes"))

from config import API_TITLE, API_VERSION, API_DESCRIPTION
from orchestrator import MarIAPipeline

# ==========================================================================
# App e CORS
# ==========================================================================

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    contact={
        "name":  "Projeto Deumach / FAPEAL",
        "email": "contato@deumach.al.gov.br",
    },
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache em memória do último pipeline executado
_cache: dict = {}


# ==========================================================================
# Schemas (Pydantic)
# ==========================================================================

class PipelineResponse(BaseModel):
    status: str
    executado_em: str
    tempo_total_s: float
    mensagem: str


class PerguntaChat(BaseModel):
    pergunta: str
    praia_id: Optional[str] = None


# ==========================================================================
# Utilitários
# ==========================================================================

def _carregar_dados() -> dict:
    """Carrega o resultado mais recente do pipeline."""
    global _cache
    if _cache:
        return _cache

    caminho = Path("dados/analise.json")
    if not caminho.exists():
        raise HTTPException(
            status_code=503,
            detail="Dados ainda não disponíveis. Execute POST /api/v1/executar-pipeline primeiro.",
        )
    with open(caminho, encoding="utf-8") as f:
        analise = json.load(f)

    previsao_path = Path("dados/previsao.json")
    previsao = {}
    if previsao_path.exists():
        with open(previsao_path, encoding="utf-8") as f:
            previsao = json.load(f)

    notif_path = Path("dados/notificacoes.json")
    notif = {}
    if notif_path.exists():
        with open(notif_path, encoding="utf-8") as f:
            notif = json.load(f)

    _cache = {"analise": analise, "previsao": previsao, "notificacoes": notif}
    return _cache


# ==========================================================================
# Endpoints
# ==========================================================================

@app.get("/", tags=["Status"])
def raiz():
    """Verifica se a API está online."""
    return {
        "projeto": "MarIA",
        "descricao": "Monitor de Poluição Marinha — Maceió/AL",
        "versao": API_VERSION,
        "status": "online 🌊",
        "docs": "/docs",
    }


@app.post("/api/v1/executar-pipeline", tags=["Pipeline"], response_model=PipelineResponse)
def executar_pipeline(background_tasks: BackgroundTasks):
    """
    Dispara o pipeline completo dos 4 agentes.

    Executa em background para não bloquear a resposta HTTP.
    Aguarde ~2s e consulte /api/v1/praias para ver os resultados.
    """
    global _cache
    _cache = {}  # limpa cache

    def rodar():
        global _cache
        pipeline = MarIAPipeline(modo_simulacao=True)
        resultado = pipeline.executar()
        _cache = {
            "analise":      resultado["analise"],
            "previsao":     resultado["previsao"],
            "notificacoes": resultado["notificacoes"],
        }

    background_tasks.add_task(rodar)
    return PipelineResponse(
        status="iniciado",
        executado_em=datetime.now().isoformat(),
        tempo_total_s=0,
        mensagem="Pipeline iniciado em background. Consulte /api/v1/praias em instantes.",
    )


@app.get("/api/v1/praias", tags=["Praias"])
def listar_praias():
    """
    Lista todas as praias com seu Índice de Poluição e classificação atual.
    """
    dados = _carregar_dados()
    analise = dados["analise"]

    praias = []
    for praia_id, info in analise["analises"].items():
        ip = info["indice_poluicao"]
        praias.append({
            "id":            praia_id,
            "nome":          info["nome"],
            "score":         ip["score"],
            "classificacao": ip["classificacao"],
            "emoji":         ip["emoji"],
            "propria_banho": info["conama_274"]["propria_para_banho"],
            "parametros_criticos": info["parametros_criticos"],
        })

    return {
        "total": len(praias),
        "atualizado_em": analise["analises"][list(analise["analises"].keys())[0]]["timestamp"],
        "praias": praias,
        "ranking": analise["ranking"],
        "resumo":  analise["resumo"],
    }


@app.get("/api/v1/praias/{praia_id}", tags=["Praias"])
def detalhe_praia(praia_id: str):
    """
    Retorna análise completa de uma praia específica.

    **praia_id** pode ser: `pajucara`, `ponta_verde`, `jatiuca`,
    `cruz_das_almas`, `sereia`.
    """
    dados = _carregar_dados()
    analise = dados["analise"]

    if praia_id not in analise["analises"]:
        raise HTTPException(
            status_code=404,
            detail=f"Praia '{praia_id}' não encontrada. IDs disponíveis: {list(analise['analises'].keys())}",
        )

    return analise["analises"][praia_id]


@app.get("/api/v1/praias/{praia_id}/previsao", tags=["Previsão"])
def previsao_praia(praia_id: str):
    """
    Retorna a previsão de qualidade para os próximos 7 dias de uma praia.
    """
    dados = _carregar_dados()
    previsao = dados.get("previsao", {})

    if not previsao or praia_id not in previsao.get("previsoes", {}):
        raise HTTPException(status_code=404, detail=f"Previsão para '{praia_id}' não encontrada.")

    return previsao["previsoes"][praia_id]


@app.get("/api/v1/previsao/alertas-futuros", tags=["Previsão"])
def alertas_futuros():
    """
    Lista todas as previsões críticas nos próximos 7 dias em todas as praias.
    """
    dados = _carregar_dados()
    previsao = dados.get("previsao", {})
    return {
        "alertas": previsao.get("alertas_futuros", []),
        "modelo":  previsao.get("modelo"),
        "gerado_em": previsao.get("gerado_em"),
    }


@app.get("/api/v1/boletim", tags=["Boletim"])
def boletim_diario():
    """
    Boletim diário consolidado de balneabilidade — formato SEMARH/AL.
    """
    dados = _carregar_dados()
    notif = dados.get("notificacoes", {})
    if not notif:
        raise HTTPException(status_code=503, detail="Boletim ainda não gerado.")
    return notif.get("boletim", {})


@app.get("/api/v1/alertas", tags=["Alertas"])
def listar_alertas(nivel: Optional[str] = None):
    """
    Lista todos os alertas gerados.

    **nivel** (opcional): `low`, `medium`, `high`, `critical`
    """
    dados = _carregar_dados()
    alertas = dados.get("notificacoes", {}).get("alertas", [])

    if nivel:
        alertas = [a for a in alertas if a["nivel"] == nivel]

    return {
        "total": len(alertas),
        "alertas": sorted(alertas, key=lambda x: x["prioridade"], reverse=True),
    }


@app.post("/api/v1/chat", tags=["Chat IA"])
def chat_agente(body: PerguntaChat):
    """
    Chat com o agente MarIA. Faça perguntas em linguagem natural sobre
    as praias, poluição e recomendações.

    **Exemplos de perguntas:**
    - "Qual praia está mais crítica?"
    - "O que fazer em Pajuçara?"
    - "Posso levar meu filho para a Jatiúca?"
    - "Qual a previsão para o fim de semana?"
    """
    dados = _carregar_dados()
    analise = dados["analise"]
    previsao = dados.get("previsao", {})

    pergunta = body.pergunta.lower()

    # Roteamento simples de intenções
    if any(p in pergunta for p in ["crítica", "crítico", "pior", "ruim", "perigosa"]):
        pior = analise["ranking"][-1]
        return {
            "resposta": (
                f"A praia mais crítica agora é **{pior['nome']}** com Índice de Poluição "
                f"{pior['score']:.2f} ({pior['classificacao']}). "
                f"Recomendo evitar o banho nessa praia no momento."
            ),
            "praia_referencia": pior,
        }

    if any(p in pergunta for p in ["melhor", "boa", "própria", "tranquila", "segura"]):
        melhor = analise["ranking"][0]
        return {
            "resposta": (
                f"A melhor praia agora é **{melhor['nome']}** com Índice de Poluição "
                f"{melhor['score']:.2f} ({melhor['classificacao']}). "
                f"Aproveite! 🏖️"
            ),
            "praia_referencia": melhor,
        }

    if any(p in pergunta for p in ["fim de semana", "sábado", "domingo", "previsão", "previsao"]):
        alertas_fds = []
        for prev in previsao.get("previsoes", {}).values():
            for dia in prev.get("previsao", []):
                if dia["dia_semana"] in ["Sáb", "Dom"]:
                    alertas_fds.append(f"{prev['nome']}: {dia['data']} ({dia['dia_semana']}) — {dia['classificacao']} {dia['emoji']}")
        return {
            "resposta": "Previsão para o fim de semana:\n" + "\n".join(alertas_fds) if alertas_fds else "Sem dados de previsão disponíveis.",
        }

    if any(p in pergunta for p in ["filho", "criança", "criancas", "bebê", "bebe", "levar"]):
        proprias = [
            item["nome"] for item in analise["ranking"]
            if analise["analises"][item["praia_id"]]["conama_274"]["propria_para_banho"]
        ]
        improprias = [
            item["nome"] for item in analise["ranking"]
            if not analise["analises"][item["praia_id"]]["conama_274"]["propria_para_banho"]
        ]
        resposta = ""
        if proprias:
            resposta += f"✅ Praias próprias para banho (incluindo crianças): {', '.join(proprias)}.\n"
        if improprias:
            resposta += f"❌ Evite com crianças: {', '.join(improprias)}."
        return {"resposta": resposta or "Sem dados disponíveis no momento."}

    # Busca por praia específica
    for praia_id, info in analise["analises"].items():
        nome_lower = info["nome"].lower()
        if nome_lower in pergunta or praia_id in pergunta:
            ip = info["indice_poluicao"]
            criticos = info["parametros_criticos"]
            msg = (
                f"**{info['nome']}** está com IP {ip['score']:.2f} — {ip['classificacao']} {ip['emoji']}. "
            )
            if criticos:
                msg += f"Pontos de atenção: {'; '.join(criticos)}."
            else:
                msg += "Sem parâmetros críticos no momento. ✅"
            return {"resposta": msg, "dados": info}

    # Resposta padrão
    return {
        "resposta": (
            "Posso responder sobre: qual praia está mais crítica ou melhor, "
            "previsão para o fim de semana, se é seguro levar crianças, "
            "ou informações específicas de qualquer praia (Pajuçara, Ponta Verde, "
            "Jatiúca, Cruz das Almas, Sereia). Qual desses temas te interessa?"
        )
    }
