"""
MarIA — Agente Analisador
=========================
Responsabilidade: Processar os dados coletados e calcular o
Índice de Poluição (IP) de cada praia.

O IP é um score de 0.0 a 1.0 calculado por uma média ponderada
de sub-índices normalizados, inspirado na metodologia do
CONAMA 274/2000 e no IQA (Índice de Qualidade da Água).

Pesos do modelo (podem ser ajustados com dados históricos reais):
  - Coliformes fecais : 35%  ← maior risco sanitário
  - pH                : 10%
  - Turbidez          : 15%
  - Óleo/graxas       : 20%
  - Resíduos sólidos  : 15%
  - Esgoto visível    :  5%
"""

import json
import math
from pathlib import Path
from config import LIMITES, CLASSIFICACAO_IP


class AgenteAnalisadorError(Exception):
    pass


class AgenteAnalisador:
    """
    Agente de análise e pontuação de qualidade das praias.

    Recebe o output do AgenteColetor e devolve um relatório
    estruturado com o Índice de Poluição e classificação CONAMA.
    """

    PESOS = {
        "coliformes":  0.35,
        "ph":          0.10,
        "turbidez":    0.15,
        "oleo":        0.20,
        "residuos":    0.15,
        "esgoto":      0.05,
    }

    def __init__(self):
        self.limites = LIMITES
        print("[AgenteAnalisador] Inicializado ✅")

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def analisar_todas(self, dados_coleta: dict) -> dict:
        """Analisa todas as praias presentes nos dados coletados."""
        print("[AgenteAnalisador] Iniciando análise...")
        resultados = {}
        for praia_id, dados in dados_coleta.items():
            resultados[praia_id] = self.analisar_praia(dados)

        # Ranking das praias (melhor → pior)
        ranking = sorted(
            resultados.items(),
            key=lambda x: x[1]["indice_poluicao"]["score"],
        )
        print(f"[AgenteAnalisador] {len(resultados)} praias analisadas ✅")
        return {
            "analises":   resultados,
            "ranking":    [{"posicao": i+1, "praia_id": k, "nome": v["nome"],
                            "score": v["indice_poluicao"]["score"],
                            "classificacao": v["indice_poluicao"]["classificacao"]}
                           for i, (k, v) in enumerate(ranking)],
            "resumo":     self._gerar_resumo(resultados),
        }

    def analisar_praia(self, dados: dict) -> dict:
        """Calcula o Índice de Poluição de uma praia individual."""
        agua    = dados["agua"]
        residuos = dados["residuos"]

        sub_indices = {
            "coliformes": self._normalizar_coliformes(agua["coliformes_fecais"]),
            "ph":         self._normalizar_ph(agua["ph"]),
            "turbidez":   self._normalizar_linear(agua["turbidez"],  0, self.limites["turbidez_max"] * 2),
            "oleo":       self._normalizar_linear(agua["oleo_graxas"], 0, self.limites["oleo_max"] * 3),
            "residuos":   self._normalizar_residuos(residuos),
            "esgoto":     1.0 if residuos["esgoto_visivel"] else 0.0,
        }

        score = sum(self.PESOS[k] * v for k, v in sub_indices.items())
        score = round(min(max(score, 0.0), 1.0), 4)

        classif, emoji, nivel = self._classificar(score)

        # Conformidade CONAMA 274/2000
        propria = agua["coliformes_fecais"] <= self.limites["coliformes_propria"]

        return {
            "praia_id":         dados["praia_id"],
            "nome":             dados["nome"],
            "timestamp":        dados["timestamp"],
            "indice_poluicao": {
                "score":          score,
                "classificacao":  classif,
                "emoji":          emoji,
                "nivel":          nivel,
            },
            "conama_274": {
                "propria_para_banho": propria,
                "coliformes_medidos": agua["coliformes_fecais"],
                "limite_proprio":     self.limites["coliformes_propria"],
            },
            "sub_indices": sub_indices,
            "parametros_criticos": self._identificar_criticos(agua, residuos),
            "dados_brutos":  {
                "agua":     agua,
                "residuos": residuos,
                "clima":    dados["clima"],
                "ocupacao": dados["ocupacao"],
            },
        }

    # ------------------------------------------------------------------
    # Normalização (0 = perfeito, 1 = crítico)
    # ------------------------------------------------------------------

    def _normalizar_coliformes(self, valor: float) -> float:
        """
        Escala logarítmica: sensível a pequenas variações na faixa baixa,
        robusta a outliers extremos.
        """
        if valor <= 0:
            return 0.0
        limite = self.limites["coliformes_impropia"]
        score = math.log1p(valor) / math.log1p(limite)
        return min(score, 1.0)

    def _normalizar_ph(self, valor: float) -> float:
        """pH ótimo é 7–8; desvios nas duas direções aumentam o score."""
        ph_min = self.limites["ph_min"]
        ph_max = self.limites["ph_max"]
        centro = (ph_min + ph_max) / 2
        raio   = (ph_max - ph_min) / 2
        desvio = abs(valor - centro)
        return min(desvio / raio, 1.0)

    def _normalizar_linear(self, valor: float, minimo: float, maximo: float) -> float:
        if maximo <= minimo:
            return 0.0
        return min(max((valor - minimo) / (maximo - minimo), 0.0), 1.0)

    def _normalizar_residuos(self, residuos: dict) -> float:
        total = (
            residuos["plasticos_por_100m2"]
            + residuos["bitucas_por_100m2"]
            + residuos["vidros_por_100m2"]
        )
        return self._normalizar_linear(total, 0, self.limites["residuos_max"] * 5)

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    def _classificar(self, score: float) -> tuple[str, str, str]:
        for (low, high), info in CLASSIFICACAO_IP.items():
            if low <= score < high:
                return info
        return ("Crítica", "🔴", "critical")

    def _identificar_criticos(self, agua: dict, residuos: dict) -> list[str]:
        criticos = []
        if agua["coliformes_fecais"] > self.limites["coliformes_propria"]:
            criticos.append(f"Coliformes acima do limite ({agua['coliformes_fecais']:.0f} NMP/100mL)")
        if not (self.limites["ph_min"] <= agua["ph"] <= self.limites["ph_max"]):
            criticos.append(f"pH fora da faixa segura ({agua['ph']})")
        if agua["turbidez"] > self.limites["turbidez_max"]:
            criticos.append(f"Turbidez elevada ({agua['turbidez']} NTU)")
        if agua["oleo_graxas"] > self.limites["oleo_max"]:
            criticos.append(f"Óleo/graxas detectado ({agua['oleo_graxas']} mg/L)")
        if residuos["esgoto_visivel"]:
            criticos.append("Esgoto visível na praia ⚠️")
        return criticos

    def _gerar_resumo(self, resultados: dict) -> dict:
        scores = [v["indice_poluicao"]["score"] for v in resultados.values()]
        proprias = sum(
            1 for v in resultados.values()
            if v["conama_274"]["propria_para_banho"]
        )
        return {
            "total_praias":        len(resultados),
            "proprias_para_banho": proprias,
            "improprias":          len(resultados) - proprias,
            "ip_medio":            round(sum(scores) / len(scores), 4),
            "ip_pior":             round(max(scores), 4),
            "ip_melhor":           round(min(scores), 4),
        }

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------

    def salvar_analise(self, analise: dict, caminho: str = "dados/analise.json") -> str:
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(analise, f, ensure_ascii=False, indent=2)
        print(f"[AgenteAnalisador] Análise salva em '{caminho}' ✅")
        return caminho


# ==========================================================================
# Execução direta
# ==========================================================================
if __name__ == "__main__":
    import sys
    sys.path.insert(0, "..")

    # Carregar dados do coletor
    with open("dados/coleta.json", encoding="utf-8") as f:
        dados = json.load(f)

    analisador = AgenteAnalisador()
    analise = analisador.analisar_todas(dados)
    analisador.salvar_analise(analise)

    print("\n📊 Ranking de praias:")
    for item in analise["ranking"]:
        ip = item["score"]
        classif = item["classificacao"]
        print(f"  {item['posicao']}º {item['nome']:20s} IP={ip:.3f}  {classif}")

    resumo = analise["resumo"]
    print(f"\n✅ Próprias para banho: {resumo['proprias_para_banho']}/{resumo['total_praias']}")
