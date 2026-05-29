"""
MarIA — Agente Coletor
======================
Responsabilidade: Coletar dados ambientais das praias monitoradas.

Em produção, este agente consumiria APIs externas:
  - OpenWeather API  → temperatura, vento, precipitação
  - Open-Meteo API   → ondas, maré
  - Sensores IoT     → coliformes, pH, turbidez em tempo real

Para a demonstração, gera dados mock realistas baseados em padrões
históricos de Maceió/AL.
"""

import random
import json
from datetime import datetime, date
from pathlib import Path
from config import PRAIAS, LIMITES


class AgenteColetorError(Exception):
    pass


class AgenteColetor:
    """
    Agente responsável pela coleta de dados ambientais.

    Simula a leitura de sensores e APIs externas, retornando um
    dicionário padronizado com todos os parâmetros de qualidade
    da água e condições climáticas para cada praia.
    """

    def __init__(self, seed: int | None = None):
        if seed is not None:
            random.seed(seed)
        self.timestamp = datetime.now().isoformat()
        self.praias = PRAIAS
        print("[AgenteColetor] Inicializado ✅")

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def coletar_todas(self) -> dict:
        """Coleta dados de todas as praias cadastradas."""
        print(f"[AgenteColetor] Coletando dados em {self.timestamp}...")
        resultados = {}
        for praia_id in self.praias:
            resultados[praia_id] = self.coletar_praia(praia_id)
        print(f"[AgenteColetor] {len(resultados)} praias coletadas ✅")
        return resultados

    def coletar_praia(self, praia_id: str) -> dict:
        """Coleta dados de uma praia específica."""
        if praia_id not in self.praias:
            raise AgenteColetorError(f"Praia '{praia_id}' não cadastrada.")

        info = self.praias[praia_id]
        dados = {
            "praia_id":   praia_id,
            "nome":       info["nome"],
            "tipo":       info["tipo"],
            "timestamp":  self.timestamp,
            "localizacao": {"lat": info["lat"], "lon": info["lon"]},
            "agua":       self._simular_qualidade_agua(info),
            "clima":      self._simular_clima(),
            "residuos":   self._simular_residuos(info),
            "ocupacao":   self._simular_ocupacao(info),
        }
        return dados

    # ------------------------------------------------------------------
    # Simuladores de dados (substituir por chamadas reais em produção)
    # ------------------------------------------------------------------

    def _simular_qualidade_agua(self, info: dict) -> dict:
        """
        Simula parâmetros físico-químicos e bacteriológicos da água.
        Praias urbanas tendem a ter índices piores por esgotos.
        """
        fator_urbano = 1.8 if info["tipo"] == "urbana" else 1.0

        coliformes = round(
            random.uniform(50, 1200) * fator_urbano
            + random.gauss(0, 80),
            1,
        )
        coliformes = max(10, coliformes)  # mínimo físico

        return {
            "coliformes_fecais":  coliformes,        # NMP/100mL
            "ph":                 round(random.uniform(6.8, 8.3), 2),
            "turbidez":           round(random.uniform(2, 55), 1),   # NTU
            "oleo_graxas":        round(random.uniform(0, 1.2), 3),  # mg/L
            "temperatura":        round(random.uniform(26, 31), 1),  # °C
            "salinidade":         round(random.uniform(32, 38), 1),  # PSU
            "oxigenio_dissolvido": round(random.uniform(5, 9), 2),   # mg/L
        }

    def _simular_clima(self) -> dict:
        """Simula condições meteorológicas típicas de Maceió."""
        return {
            "temperatura_ar":   round(random.uniform(24, 34), 1),   # °C
            "umidade":          round(random.uniform(60, 95), 1),   # %
            "vento_kmh":        round(random.uniform(5, 35), 1),
            "direcao_vento":    random.choice(["NE", "SE", "E", "S", "N"]),
            "precipitacao_mm":  round(random.uniform(0, 30), 1),
            "altura_ondas_m":   round(random.uniform(0.3, 2.5), 2),
            "visibilidade_km":  round(random.uniform(5, 20), 1),
        }

    def _simular_residuos(self, info: dict) -> dict:
        """Simula presença de resíduos sólidos na faixa de areia."""
        fator_urbano = 1.5 if info["tipo"] == "urbana" else 1.0
        base = random.uniform(0, 8) * fator_urbano
        return {
            "plasticos_por_100m2":   round(base * random.uniform(0.5, 1.5), 1),
            "bitucas_por_100m2":     round(base * random.uniform(0.3, 1.0), 1),
            "vidros_por_100m2":      round(base * random.uniform(0.1, 0.4), 1),
            "esgoto_visivel":        random.random() < (0.3 * fator_urbano),
        }

    def _simular_ocupacao(self, info: dict) -> dict:
        """Simula nível de ocupação da praia."""
        mes_atual = datetime.now().month
        # Alta temporada: dez–mar
        fator_temporada = 1.4 if mes_atual in [12, 1, 2, 3] else 1.0
        ocupacao = int(
            random.uniform(0.1, 0.9) * info["capacidade_banhistas"]
            * fator_temporada
        )
        return {
            "banhistas_estimados": min(ocupacao, info["capacidade_banhistas"]),
            "capacidade_maxima":   info["capacidade_banhistas"],
            "percentual":          round(ocupacao / info["capacidade_banhistas"] * 100, 1),
        }

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------

    def salvar_coleta(self, dados: dict, caminho: str = "dados/coleta.json") -> str:
        """Salva os dados coletados em disco para o próximo agente."""
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        print(f"[AgenteColetor] Dados salvos em '{caminho}' ✅")
        return caminho


# ==========================================================================
# Execução direta (teste rápido)
# ==========================================================================
if __name__ == "__main__":
    agente = AgenteColetor(seed=42)
    dados = agente.coletar_todas()
    caminho = agente.salvar_coleta(dados)

    print("\n📊 Amostra de dados coletados:")
    primeira_praia = list(dados.values())[0]
    print(f"  Praia: {primeira_praia['nome']}")
    print(f"  Coliformes: {primeira_praia['agua']['coliformes_fecais']} NMP/100mL")
    print(f"  pH: {primeira_praia['agua']['ph']}")
    print(f"  Ondas: {primeira_praia['clima']['altura_ondas_m']} m")
    print(f"  Banhistas: {primeira_praia['ocupacao']['banhistas_estimados']}")
