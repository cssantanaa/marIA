"""
MarIA — Agente Notificador
==========================
Responsabilidade: Processar os resultados da análise e da previsão
e gerar alertas estruturados + recomendações para cada público:

  👨‍👩‍👧 Banhistas       → segurança pessoal
  🏖️  Órgãos públicos  → ações de fiscalização e limpeza
  🐠  Pescadores       → segurança alimentar
  📰  Imprensa         → comunicados públicos

Canais simulados (em produção, enviariam de verdade):
  - E-mail (SMTP)
  - SMS (Twilio)
  - Push notification (Firebase)
  - Webhook (dashboard municipal)
"""

import json
from datetime import datetime
from pathlib import Path
from config import LIMITES


class AgenteNotificador:
    """
    Agente responsável por gerar e despachar alertas.

    Prioriza notificações por nível de criticidade:
      CRÍTICO  → envia para todos os canais imediatamente
      ALTO     → e-mail + push
      MÉDIO    → push + dashboard
      BAIXO    → apenas dashboard
    """

    PRIORIDADE = {
        "critical": 4,
        "high":     3,
        "medium":   2,
        "low":      1,
    }

    def __init__(self, modo_simulacao: bool = True):
        self.modo_simulacao = modo_simulacao
        self.log_notificacoes: list[dict] = []
        print(f"[AgenteNotificador] Inicializado — modo={'simulação' if modo_simulacao else 'produção'} ✅")

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def notificar_todas(self, analise: dict, previsao: dict) -> dict:
        """Processa todas as praias e gera relatório completo de alertas."""
        print("[AgenteNotificador] Gerando notificações...")

        alertas: list[dict] = []
        recomendacoes: list[dict] = []

        for praia_id, dados in analise["analises"].items():
            prev = previsao["previsoes"].get(praia_id, {})
            alerta     = self._gerar_alerta(dados, prev)
            recomendac = self._gerar_recomendacoes(dados, prev)

            alertas.append(alerta)
            recomendacoes.append(recomendac)

            # Despachar notificação
            self._despachar(alerta)

        # Boletim público consolidado
        boletim = self._gerar_boletim_publico(analise, alertas)

        print(f"[AgenteNotificador] {len(alertas)} alertas gerados ✅")
        return {
            "alertas":       alertas,
            "recomendacoes": recomendacoes,
            "boletim":       boletim,
            "log":           self.log_notificacoes,
            "gerado_em":     datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Geração de alertas
    # ------------------------------------------------------------------

    def _gerar_alerta(self, dados: dict, prev: dict) -> dict:
        ip     = dados["indice_poluicao"]
        conama = dados["conama_274"]
        nivel  = ip["nivel"]

        mensagens_nivel = {
            "low":      "✅ Praia em ótimas condições. Aproveite!",
            "medium":   "⚠️  Qualidade boa, mas fique atento às condições.",
            "high":     "🟠 Qualidade regular. Evite contato prolongado com a água.",
            "critical": "🔴 ALERTA CRÍTICO: Banho não recomendado! Risco à saúde.",
        }

        tendencia_texto = ""
        if prev.get("tendencia"):
            d = prev["tendencia"]["direcao"]
            tendencia_texto = f"Tendência nos próximos dias: {d}."

        return {
            "praia_id":          dados["praia_id"],
            "nome":              dados["nome"],
            "nivel":             nivel,
            "prioridade":        self.PRIORIDADE[nivel],
            "propria_banho":     conama["propria_para_banho"],
            "score":             ip["score"],
            "classificacao":     ip["classificacao"],
            "emoji":             ip["emoji"],
            "mensagem_publica":  mensagens_nivel[nivel],
            "tendencia":         tendencia_texto,
            "parametros_criticos": dados["parametros_criticos"],
            "timestamp":         datetime.now().isoformat(),
            "canais_acionados":  self._definir_canais(nivel),
        }

    def _gerar_recomendacoes(self, dados: dict, prev: dict) -> dict:
        nivel    = dados["indice_poluicao"]["nivel"]
        criticos = dados["parametros_criticos"]
        nome     = dados["nome"]

        rec_banhistas = self._rec_banhistas(nivel)
        rec_orgaos    = self._rec_orgaos(nivel, criticos, nome)
        rec_pescadores = self._rec_pescadores(dados["dados_brutos"]["agua"])
        rec_imprensa  = self._rec_imprensa(dados, prev)

        return {
            "praia_id":       dados["praia_id"],
            "nome":           nome,
            "banhistas":      rec_banhistas,
            "orgaos_publicos": rec_orgaos,
            "pescadores":     rec_pescadores,
            "imprensa":       rec_imprensa,
        }

    # ------------------------------------------------------------------
    # Recomendações por público-alvo
    # ------------------------------------------------------------------

    def _rec_banhistas(self, nivel: str) -> list[str]:
        base = {
            "low": [
                "Praia própria para banho. Aproveite com segurança!",
                "Hidrate-se e use protetor solar.",
                "Respeite as bandeiras dos guarda-vidas.",
            ],
            "medium": [
                "Qualidade aceitável — evite engolir a água.",
                "Prefira nadar em áreas sinalizadas.",
                "Observe a cor e o cheiro da água antes de entrar.",
            ],
            "high": [
                "Evite banho prolongado, especialmente crianças e idosos.",
                "Não entre na água após chuvas fortes.",
                "Lave-se bem com água doce após o banho.",
                "Pessoas imunossuprimidas devem evitar o banho.",
            ],
            "critical": [
                "🚫 BANHO NÃO RECOMENDADO — risco de doenças gastrointestinais.",
                "Não leve crianças para o contato com a água.",
                "Informe o guarda-vidas sobre qualquer sintoma.",
                "Acesse o site da SEMARH para atualizações.",
            ],
        }
        return base.get(nivel, [])

    def _rec_orgaos(self, nivel: str, criticos: list[str], nome: str) -> list[str]:
        acoes = []
        if nivel in ["high", "critical"]:
            acoes.append(f"Intensificar coleta de resíduos em {nome}.")
            acoes.append("Notificar CASAL sobre possíveis vazamentos de esgoto.")
            acoes.append("Instalar faixas de interdição se IP > 0.75.")
        if "Esgoto visível" in " ".join(criticos):
            acoes.append("Acionar equipe de campo imediatamente para vistoria.")
            acoes.append("Registrar ocorrência no sistema de ouvidoria ambiental.")
        if nivel == "critical":
            acoes.append("Emitir comunicado à imprensa e redes sociais oficiais.")
            acoes.append("Coleta de amostra confirmativa em laboratório.")
        if not acoes:
            acoes.append("Manter monitoramento padrão.")
        return acoes

    def _rec_pescadores(self, agua: dict) -> list[str]:
        rec = []
        if agua["coliformes_fecais"] > LIMITES["coliformes_propria"]:
            rec.append("⚠️  Não consumir peixes ou frutos do mar desta área sem análise.")
            rec.append("Comunicar ao IBAMA e SEAP se observar mortandade de peixes.")
        if agua["oleo_graxas"] > LIMITES["oleo_max"]:
            rec.append("Óleo detectado — evitar pesca na área por 48h.")
        if not rec:
            rec.append("Condições normais para pesca artesanal.")
        return rec

    def _rec_imprensa(self, dados: dict, prev: dict) -> str:
        nome  = dados["nome"]
        ip    = dados["indice_poluicao"]
        score = ip["score"]

        lead = (
            f"O sistema MarIA registrou Índice de Poluição {score:.2f} "
            f"({ip['classificacao']}) na praia {nome} em "
            f"{datetime.now().strftime('%d/%m/%Y')}."
        )
        if prev.get("tendencia"):
            tend = prev["tendencia"]["direcao"]
            lead += f" A tendência para os próximos 7 dias é de {tend}."
        return lead

    # ------------------------------------------------------------------
    # Despacho de notificações
    # ------------------------------------------------------------------

    def _definir_canais(self, nivel: str) -> list[str]:
        canais = {
            "low":      ["dashboard"],
            "medium":   ["dashboard", "push"],
            "high":     ["dashboard", "push", "email"],
            "critical": ["dashboard", "push", "email", "sms", "webhook_municipal"],
        }
        return canais.get(nivel, ["dashboard"])

    def _despachar(self, alerta: dict) -> None:
        """Simula o envio de notificação pelos canais definidos."""
        if not self.modo_simulacao:
            # TODO: implementar integrações reais
            raise NotImplementedError("Modo produção ainda não implementado.")

        entrada_log = {
            "praia":    alerta["nome"],
            "nivel":    alerta["nivel"],
            "canais":   alerta["canais_acionados"],
            "enviado":  True,
            "timestamp": datetime.now().isoformat(),
        }
        self.log_notificacoes.append(entrada_log)

        if alerta["prioridade"] >= 3:
            print(f"  [ALERTA {alerta['nivel'].upper()}] {alerta['nome']}: {alerta['mensagem_publica']}")

    # ------------------------------------------------------------------
    # Boletim público
    # ------------------------------------------------------------------

    def _gerar_boletim_publico(self, analise: dict, alertas: list[dict]) -> dict:
        """Gera o boletim diário resumido no formato da SEMARH/AL."""
        resumo = analise["resumo"]
        data_hoje = datetime.now().strftime("%d/%m/%Y")

        return {
            "titulo":    f"Boletim de Balneabilidade — Maceió/AL — {data_hoje}",
            "orgao":     "MarIA / DEUMACH-FAPEAL",
            "data":      data_hoje,
            "resumo": {
                "praias_proprias":   resumo["proprias_para_banho"],
                "praias_improprias": resumo["improprias"],
                "ip_medio":          resumo["ip_medio"],
            },
            "praias_em_alerta": [
                a for a in alertas if a["nivel"] in ["high", "critical"]
            ],
            "ranking": analise["ranking"],
            "nota_tecnica": (
                "Avaliação baseada no padrão CONAMA 274/2000. "
                "Amostras coletadas por sensores IoT e análises laboratoriais. "
                "Atualizações às 6h e 14h."
            ),
        }

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------

    def salvar_notificacoes(self, notif: dict, caminho: str = "dados/notificacoes.json") -> str:
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(notif, f, ensure_ascii=False, indent=2)
        print(f"[AgenteNotificador] Notificações salvas em '{caminho}' ✅")
        return caminho


# ==========================================================================
# Execução direta
# ==========================================================================
if __name__ == "__main__":
    import sys
    sys.path.insert(0, "..")

    with open("dados/analise.json", encoding="utf-8") as f:
        analise = json.load(f)
    with open("dados/previsao.json", encoding="utf-8") as f:
        previsao = json.load(f)

    notif = AgenteNotificador(modo_simulacao=True)
    resultado = notif.notificar_todas(analise, previsao)
    notif.salvar_notificacoes(resultado)

    print("\n📢 Boletim público:")
    b = resultado["boletim"]
    print(f"  {b['titulo']}")
    print(f"  Próprias: {b['resumo']['praias_proprias']} | Impróprias: {b['resumo']['praias_improprias']}")
    print(f"  IP médio: {b['resumo']['ip_medio']:.3f}")
