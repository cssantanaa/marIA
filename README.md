# 🌊 MarIA — Monitor de Poluição Marinha em Maceió/AL

> **Projeto de IA Aplicada** — 3ª Avaliação | Programa Deumach / FAPEAL  
> Universidade Federal de Alagoas — Maceió, AL

---

## 📌 Sobre o Projeto

O **MarIA** é um sistema multiagente de Inteligência Artificial para monitoramento contínuo da qualidade das praias de Maceió. O sistema coleta dados ambientais, calcula um Índice de Poluição (IP), gera previsões para 7 dias e emite alertas automáticos para banhistas, órgãos públicos e pescadores.

O projeto foi desenvolvido como resposta ao desafio real submetido pelas empresas parceiras do programa **Deumach/FAPEAL**, que identificaram a necessidade de um sistema acessível de monitoramento da balneabilidade das praias alagoanas.

---

## 🏖️ Praias Monitoradas

| Praia | Tipo | Capacidade |
|-------|------|-----------|
| Pajuçara | Urbana | 5.000 banhistas |
| Ponta Verde | Urbana | 4.000 banhistas |
| Jatiúca | Urbana | 6.000 banhistas |
| Cruz das Almas | Semi-urbana | 3.000 banhistas |
| Praia da Sereia | Semi-urbana | 2.500 banhistas |

---

## 🤖 Arquitetura dos Agentes

```
┌─────────────────────────────────────────────────────┐
│                   orchestrator.py                    │
│              (Coordenador do Pipeline)               │
└──────┬────────────┬────────────┬────────────────────┘
       │            │            │            │
       ▼            ▼            ▼            ▼
 ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
 │ Agente   │ │ Agente   │ │ Agente   │ │ Agente       │
 │ Coletor  │ │Analisador│ │ Preditor │ │ Notificador  │
 └──────────┘ └──────────┘ └──────────┘ └──────────────┘
       │            │            │            │
       ▼            ▼            ▼            ▼
  coleta.json  analise.json previsao.json notif.json
                                                │
                                                ▼
                                           api.py (FastAPI)
```

### Agente Coletor (`agentes/agente_coletor.py`)
- Coleta dados de qualidade da água: coliformes, pH, turbidez, óleo/graxas
- Coleta dados climáticos: temperatura, vento, ondas, precipitação
- Coleta dados de resíduos sólidos e ocupação da praia
- Em produção: integra OpenWeather API, Open-Meteo e sensores IoT

### Agente Analisador (`agentes/agente_analisador.py`)
- Calcula o **Índice de Poluição (IP)** de 0.0 a 1.0 via média ponderada
- Verifica conformidade com a **Resolução CONAMA 274/2000**
- Classifica cada praia: Excelente 🟢 / Boa 🟡 / Regular 🟠 / Crítica 🔴
- Identifica parâmetros fora dos limites e gera ranking das praias

### Agente Preditor (`agentes/agente_preditor.py`)
- Gera previsão de qualidade para **7 dias à frente**
- Modelo ARIMA-Sazonal com fatores de chuva, vento, sazonalidade
- Calcula intervalo de confiança 95% para cada previsão
- Detecta automaticamente alertas futuros críticos

### Agente Notificador (`agentes/agente_notificador.py`)
- Gera alertas personalizados por público: banhistas, órgãos, pescadores, imprensa
- Aciona canais proporcionais ao nível: dashboard / push / e-mail / SMS / webhook
- Produz boletim diário no formato oficial SEMARH/AL

---

## 🗂️ Estrutura do Projeto

```
maria/
├── agentes/
│   ├── __init__.py
│   ├── agente_coletor.py       # Agente 1 — Coleta de dados
│   ├── agente_analisador.py    # Agente 2 — Análise e IP
│   ├── agente_preditor.py      # Agente 3 — Previsão 7 dias
│   └── agente_notificador.py   # Agente 4 — Alertas
├── dados/                      # JSONs gerados pelo pipeline
│   ├── coleta.json
│   ├── analise.json
│   ├── previsao.json
│   └── notificacoes.json
├── resultados/                 # Histórico de execuções
├── testes/                     # Testes unitários
├── config.py                   # Configurações e constantes
├── orchestrator.py             # Coordenador do pipeline
├── api.py                      # API REST FastAPI
├── requirements.txt
└── README.md
```

---

## ⚙️ Como Executar

### 1. Clonar o repositório
```bash
git clone https://github.com/<seu-usuario>/maria
cd maria
```

### 2. Instalar dependências
```bash
pip install -r requirements.txt
```

### 3. Executar o pipeline completo
```bash
python orchestrator.py
```

### 4. Subir a API
```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### 5. Acessar a documentação Swagger
Abra no navegador: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🌐 Endpoints da API

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET`  | `/` | Status da API |
| `POST` | `/api/v1/executar-pipeline` | Dispara os 4 agentes |
| `GET`  | `/api/v1/praias` | Lista todas as praias com IP atual |
| `GET`  | `/api/v1/praias/{id}` | Detalhe de uma praia |
| `GET`  | `/api/v1/praias/{id}/previsao` | Previsão de 7 dias |
| `GET`  | `/api/v1/previsao/alertas-futuros` | Alertas críticos futuros |
| `GET`  | `/api/v1/boletim` | Boletim diário oficial |
| `GET`  | `/api/v1/alertas` | Lista alertas por nível |
| `POST` | `/api/v1/chat` | Chat com o agente MarIA |

### Exemplo de chat via curl
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "Qual praia está mais crítica?"}'
```

---

## 📐 Índice de Poluição (IP)

O IP é calculado por média ponderada de 6 sub-índices:

| Parâmetro | Peso | Base normativa |
|-----------|------|----------------|
| Coliformes fecais | 35% | CONAMA 274/2000 |
| Óleo e graxas | 20% | CONAMA 357/2005 |
| Turbidez | 15% | ABNT NBR 13969 |
| Resíduos sólidos | 15% | PNRS |
| pH | 10% | CONAMA 274/2000 |
| Esgoto visível | 5% | Observação direta |

| Score | Classificação | Banho |
|-------|--------------|-------|
| 0.00 – 0.25 | 🟢 Excelente | ✅ Permitido |
| 0.25 – 0.50 | 🟡 Boa | ✅ Permitido |
| 0.50 – 0.75 | 🟠 Regular | ⚠️ Com cautela |
| 0.75 – 1.00 | 🔴 Crítica | ❌ Não recomendado |

---

## 👥 Equipe

| Nome | Função |
|------|--------|
| | |

---

## 📄 Licença

MIT License — Projeto acadêmico sem fins comerciais.

---

*Desenvolvido para o programa Deumach/FAPEAL — Maceió, Alagoas, 2026.*
