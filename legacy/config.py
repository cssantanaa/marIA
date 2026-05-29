"""
MarIA - Sistema de Monitoramento de Poluição Marinha em Maceió/AL
Configurações globais do projeto
"""

# Praias monitoradas em Maceió
PRAIAS = {
    "pajucara": {
        "nome": "Pajuçara",
        "lat": -9.6658,
        "lon": -35.7350,
        "tipo": "urbana",
        "capacidade_banhistas": 5000,
    },
    "ponta_verde": {
        "nome": "Ponta Verde",
        "lat": -9.6602,
        "lon": -35.7239,
        "tipo": "urbana",
        "capacidade_banhistas": 4000,
    },
    "jatiuca": {
        "nome": "Jatiúca",
        "lat": -9.6462,
        "lon": -35.7145,
        "tipo": "urbana",
        "capacidade_banhistas": 6000,
    },
    "cruz_das_almas": {
        "nome": "Cruz das Almas",
        "lat": -9.6103,
        "lon": -35.7019,
        "tipo": "semiurbana",
        "capacidade_banhistas": 3000,
    },
    "sereia": {
        "nome": "Praia da Sereia",
        "lat": -9.5891,
        "lon": -35.6928,
        "tipo": "semiurbana",
        "capacidade_banhistas": 2500,
    },
}

# Limiares de qualidade da água (baseados em padrões CONAMA 274/2000)
LIMITES = {
    "coliformes_propria":    250,   # NMP/100mL — própria para banho
    "coliformes_impropia":  1000,   # NMP/100mL — imprópria para banho
    "ph_min": 6.5,
    "ph_max": 8.5,
    "turbidez_max": 40,             # NTU
    "oleo_max": 0.5,                # mg/L
    "residuos_max": 5,              # unidades por 100m²
}

# Classificação do Índice de Poluição (IP)
CLASSIFICACAO_IP = {
    (0.0, 0.25):  ("Excelente", "🟢", "low"),
    (0.25, 0.50): ("Boa",       "🟡", "medium"),
    (0.50, 0.75): ("Regular",   "🟠", "high"),
    (0.75, 1.01): ("Crítica",   "🔴", "critical"),
}

# Configurações da API
API_HOST = "0.0.0.0"
API_PORT = 8000
API_TITLE = "MarIA — Monitor de Poluição Marinha"
API_VERSION = "1.0.0"
API_DESCRIPTION = """
## MarIA: Sistema de Agentes de IA para Monitoramento Marinho

Projeto desenvolvido para o programa **Deumach/FAPEAL** — Maceió, Alagoas.

### Agentes disponíveis:
| Agente | Função |
|--------|--------|
| **Coletor** | Coleta dados ambientais das praias |
| **Analisador** | Calcula o Índice de Poluição (IP) |
| **Preditor** | Gera previsão de qualidade para 7 dias |
| **Notificador** | Emite alertas e recomendações |
"""
