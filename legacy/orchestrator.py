"""
MarIA — Orchestrator
====================
Coordena a execução sequencial dos 4 agentes em pipeline:

  1. AgenteColetor     → coleta dados das praias
  2. AgenteAnalisador  → calcula Índice de Poluição
  3. AgentePreditor    → gera previsão de 7 dias
  4. AgenteNotificador → emite alertas e recomendações

Pode ser executado:
  - Manualmente:  python orchestrator.py
  - Via cron:     0 6,14 * * * python /app/orchestrator.py
  - Via API:      POST /api/v1/executar-pipeline
"""

import json
import time
import sys
from datetime import datetime
from pathlib import Path

# Permite importar os agentes de qualquer diretório
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "agentes"))

from agentes.agente_coletor     import AgenteColetor
from agentes.agente_analisador  import AgenteAnalisador
from agentes.agente_preditor    import AgentePreditor
from agentes.agente_notificador import AgenteNotificador


class MarIAPipeline:
    """
    Orchestrator principal do sistema MarIA.

    Gerencia o ciclo completo de monitoramento:
    coleta → análise → previsão → notificação.
    """

    VERSION = "1.0.0"

    def __init__(self, seed: int | None = None, modo_simulacao: bool = True):
        self.seed            = seed
        self.modo_simulacao  = modo_simulacao
        self.resultado_final = {}
        print("=" * 60)
        print("  🌊  MarIA — Monitor de Poluição Marinha")
        print(f"  Versão {self.VERSION} | {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        print("=" * 60)

    # ------------------------------------------------------------------
    # Pipeline principal
    # ------------------------------------------------------------------

    def executar(self) -> dict:
        """Executa o pipeline completo e retorna o resultado consolidado."""
        inicio = time.time()
        etapas = {}

        try:
            # ── Etapa 1: Coleta ───────────────────────────────────────
            print("\n🔵 Etapa 1/4 — Coleta de dados")
            t0 = time.time()
            coletor = AgenteColetor(seed=self.seed)
            dados_coleta = coletor.coletar_todas()
            coletor.salvar_coleta(dados_coleta)
            etapas["coleta"] = {"status": "ok", "tempo_s": round(time.time() - t0, 3)}

            # ── Etapa 2: Análise ──────────────────────────────────────
            print("\n🟡 Etapa 2/4 — Análise e cálculo do Índice de Poluição")
            t0 = time.time()
            analisador = AgenteAnalisador()
            analise = analisador.analisar_todas(dados_coleta)
            analisador.salvar_analise(analise)
            etapas["analise"] = {"status": "ok", "tempo_s": round(time.time() - t0, 3)}

            # ── Etapa 3: Previsão ─────────────────────────────────────
            print("\n🟠 Etapa 3/4 — Previsão para os próximos 7 dias")
            t0 = time.time()
            preditor = AgentePreditor()
            previsao = preditor.prever_todas(analise)
            preditor.salvar_previsao(previsao)
            etapas["previsao"] = {"status": "ok", "tempo_s": round(time.time() - t0, 3)}

            # ── Etapa 4: Notificação ──────────────────────────────────
            print("\n🔴 Etapa 4/4 — Geração de alertas e notificações")
            t0 = time.time()
            notificador = AgenteNotificador(modo_simulacao=self.modo_simulacao)
            notificacoes = notificador.notificar_todas(analise, previsao)
            notificador.salvar_notificacoes(notificacoes)
            etapas["notificacao"] = {"status": "ok", "tempo_s": round(time.time() - t0, 3)}

        except Exception as e:
            etapa_atual = max(etapas.keys(), default="coleta")
            etapas[etapa_atual] = {"status": "erro", "mensagem": str(e)}
            print(f"\n❌ ERRO na etapa '{etapa_atual}': {e}")
            raise

        # ── Resultado consolidado ─────────────────────────────────────
        tempo_total = round(time.time() - inicio, 3)
        self.resultado_final = {
            "status":      "sucesso",
            "versao":      self.VERSION,
            "executado_em": datetime.now().isoformat(),
            "tempo_total_s": tempo_total,
            "etapas":      etapas,
            "analise":     analise,
            "previsao":    previsao,
            "notificacoes": notificacoes,
        }

        self._imprimir_resumo(analise, notificacoes, tempo_total)
        self._salvar_resultado()
        return self.resultado_final

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    def _imprimir_resumo(self, analise: dict, notif: dict, tempo: float) -> None:
        print("\n" + "=" * 60)
        print("  ✅  Pipeline concluído com sucesso!")
        print("=" * 60)
        resumo = analise["resumo"]
        print(f"\n📊 Resumo do monitoramento:")
        print(f"   Praias monitoradas : {resumo['total_praias']}")
        print(f"   Próprias p/ banho  : {resumo['proprias_para_banho']}")
        print(f"   Impróprias         : {resumo['improprias']}")
        print(f"   IP médio           : {resumo['ip_medio']:.3f}")

        print(f"\n🏖️  Ranking de qualidade:")
        for item in analise["ranking"]:
            barra = "█" * int(item["score"] * 20)
            print(f"   {item['posicao']}º {item['nome']:20s} {item['classificacao']:10s} {barra}")

        alertas_criticos = [
            a for a in notif["alertas"] if a["nivel"] == "critical"
        ]
        if alertas_criticos:
            print(f"\n🚨 Praias em alerta crítico:")
            for a in alertas_criticos:
                print(f"   {a['emoji']} {a['nome']}: {a['mensagem_publica']}")

        print(f"\n⏱️  Tempo total de execução: {tempo}s")
        print("=" * 60)

    def _salvar_resultado(self) -> None:
        Path("resultados").mkdir(exist_ok=True)
        caminho = f"resultados/pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(self.resultado_final, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Resultado completo salvo em '{caminho}'")


# ==========================================================================
# Execução direta
# ==========================================================================
if __name__ == "__main__":
    pipeline = MarIAPipeline(seed=42, modo_simulacao=True)
    pipeline.executar()
