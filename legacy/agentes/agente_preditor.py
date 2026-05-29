"""
MarIA — Agente Preditor
=======================
Responsabilidade: Gerar previsão de qualidade da água para os
próximos 7 dias usando modelos de série temporal.

Modelo utilizado: ARIMA simplificado + fatores sazonais.
Em produção, este agente seria treinado com histórico real de
coletas e poderia usar Prophet (Meta) ou LSTM.

Fatores considerados na previsão:
  - Tendência baseada no score atual
  - Sazonalidade semanal (fins de semana têm mais impacto)
  - Sazonalidade mensal (chuvas em maio-julho em Alagoas)
  - Ruído estocástico controlado
"""

import json
import random
import math
from datetime import datetime, timedelta
from pathlib import Path
from config import CLASSIFICACAO_IP


class AgentePreditorError(Exception):
    pass


class AgentePreditor:
    """
    Agente de previsão de qualidade das praias para 7 dias.

    Usa um modelo de série temporal simplificado que combina:
    - Score atual como âncora
    - Tendência de melhora/piora baseada em fatores ambientais
    - Sazonalidade semanal
    - Ruído gaussiano controlado
    """

    def __init__(self):
        self.horizonte_dias = 7
        print("[AgentePreditor] Inicializado ✅")

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def prever_todas(self, analise: dict) -> dict:
        """Gera previsões para todas as praias analisadas."""
        print("[AgentePreditor] Gerando previsões para 7 dias...")
        previsoes = {}
        for praia_id, dados_analise in analise["analises"].items():
            previsoes[praia_id] = self.prever_praia(dados_analise)
        print(f"[AgentePreditor] {len(previsoes)} previsões geradas ✅")
        return {
            "previsoes":        previsoes,
            "horizonte_dias":   self.horizonte_dias,
            "modelo":           "ARIMA-Sazonal-Simplificado v1.0",
            "gerado_em":        datetime.now().isoformat(),
            "alertas_futuros":  self._detectar_alertas_futuros(previsoes),
        }

    def prever_praia(self, dados_analise: dict) -> dict:
        """Gera série temporal de 7 dias para uma praia."""
        score_atual = dados_analise["indice_poluicao"]["score"]
        nome        = dados_analise["nome"]
        clima       = dados_analise["dados_brutos"]["clima"]

        serie = self._gerar_serie_temporal(score_atual, clima)
        tendencia = self._calcular_tendencia(serie)
        pior_dia  = max(serie, key=lambda x: x["score"])
        melhor_dia = min(serie, key=lambda x: x["score"])

        return {
            "praia_id":    dados_analise["praia_id"],
            "nome":        nome,
            "score_atual": score_atual,
            "previsao":    serie,
            "tendencia":   tendencia,
            "pior_dia":    pior_dia,
            "melhor_dia":  melhor_dia,
            "recomendacao_melhor_dia": melhor_dia["data"],
        }

    # ------------------------------------------------------------------
    # Modelo de série temporal
    # ------------------------------------------------------------------

    def _gerar_serie_temporal(self, score_base: float, clima: dict) -> list[dict]:
        """
        Modelo: score(t) = score_base × tendência × sazonalidade + ruído

        Fatores que pioram a previsão:
          - Precipitação alta → mais escoamento de esgoto
          - Fim de semana → mais banhistas, mais resíduos

        Fatores que melhoram:
          - Vento forte → dispersão de poluentes
          - Dias após chuva → diluição natural
        """
        fator_chuva  = 1 + (clima["precipitacao_mm"] / 100) * 0.3
        fator_vento  = 1 - (min(clima["vento_kmh"], 30) / 100) * 0.15
        fator_ondas  = 1 - (clima["altura_ondas_m"] / 5) * 0.1

        hoje = datetime.now().date()
        serie = []

        score_simulado = score_base

        for dia in range(1, self.horizonte_dias + 1):
            data = hoje + timedelta(days=dia)
            dia_semana = data.weekday()  # 0=segunda, 5=sábado, 6=domingo

            # Sazonalidade semanal
            fator_fds = 1.15 if dia_semana >= 5 else 0.97

            # Tendência de retorno à média (mean reversion)
            fator_regressao = 1 - (score_simulado - 0.4) * 0.08

            # Sazonalidade mensal: chuvas em Alagoas (mai-ago)
            mes = data.month
            fator_mes = 1.1 if mes in [5, 6, 7, 8] else 0.95

            # Calcular próximo score
            fator_total = (
                fator_chuva * fator_vento * fator_ondas
                * fator_fds * fator_regressao * fator_mes
            )
            ruido = random.gauss(0, 0.025)
            score_simulado = score_simulado * fator_total + ruido
            score_simulado = round(min(max(score_simulado, 0.0), 1.0), 4)

            # Calcular intervalo de confiança (95%) — cresce com o horizonte
            margem = 0.05 + dia * 0.008
            ic_min = round(max(score_simulado - margem, 0.0), 4)
            ic_max = round(min(score_simulado + margem, 1.0), 4)

            classif, emoji, nivel = self._classificar(score_simulado)

            serie.append({
                "dia":            dia,
                "data":           data.strftime("%Y-%m-%d"),
                "dia_semana":     ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"][dia_semana],
                "score":          score_simulado,
                "ic_95_min":      ic_min,
                "ic_95_max":      ic_max,
                "classificacao":  classif,
                "emoji":          emoji,
                "nivel":          nivel,
                "fatores": {
                    "chuva":      round(fator_chuva, 3),
                    "vento":      round(fator_vento, 3),
                    "fim_semana": dia_semana >= 5,
                    "mes_chuvoso": mes in [5, 6, 7, 8],
                },
            })

        return serie

    def _calcular_tendencia(self, serie: list[dict]) -> dict:
        """Calcula tendência linear da série (melhora/piora)."""
        scores = [d["score"] for d in serie]
        n = len(scores)
        if n < 2:
            return {"direcao": "estável", "delta": 0.0}

        # Regressão linear simples
        x_media = (n - 1) / 2
        y_media  = sum(scores) / n
        numerador   = sum((i - x_media) * (s - y_media) for i, s in enumerate(scores))
        denominador = sum((i - x_media) ** 2 for i in range(n))
        slope = numerador / denominador if denominador != 0 else 0

        delta = round(slope * (n - 1), 4)  # variação total estimada

        if abs(delta) < 0.02:
            direcao = "estável"
        elif delta > 0:
            direcao = "piorando"
        else:
            direcao = "melhorando"

        return {"direcao": direcao, "delta_7dias": delta, "slope_diario": round(slope, 5)}

    def _detectar_alertas_futuros(self, previsoes: dict) -> list[dict]:
        """Lista previsões críticas nos próximos 7 dias."""
        alertas = []
        for praia_id, prev in previsoes.items():
            for dia in prev["previsao"]:
                if dia["nivel"] == "critical":
                    alertas.append({
                        "praia":   prev["nome"],
                        "data":    dia["data"],
                        "score":   dia["score"],
                        "emoji":   dia["emoji"],
                    })
        return sorted(alertas, key=lambda x: (x["data"], x["score"]), reverse=True)

    def _classificar(self, score: float) -> tuple[str, str, str]:
        for (low, high), info in CLASSIFICACAO_IP.items():
            if low <= score < high:
                return info
        return ("Crítica", "🔴", "critical")

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------

    def salvar_previsao(self, previsao: dict, caminho: str = "dados/previsao.json") -> str:
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(previsao, f, ensure_ascii=False, indent=2)
        print(f"[AgentePreditor] Previsão salva em '{caminho}' ✅")
        return caminho


# ==========================================================================
# Execução direta
# ==========================================================================
if __name__ == "__main__":
    import sys
    sys.path.insert(0, "..")

    with open("dados/analise.json", encoding="utf-8") as f:
        analise = json.load(f)

    preditor = AgentePreditor()
    previsao = preditor.prever_todas(analise)
    preditor.salvar_previsao(previsao)

    print("\n📅 Previsão para Pajuçara:")
    prev_pajucara = previsao["previsoes"].get("pajucara")
    if prev_pajucara:
        for dia in prev_pajucara["previsao"]:
            print(f"  {dia['data']} ({dia['dia_semana']}) — IP: {dia['score']:.3f} {dia['emoji']} {dia['classificacao']}")
        tend = prev_pajucara["tendencia"]
        print(f"  Tendência: {tend['direcao']} (Δ={tend['delta_7dias']:+.3f})")
