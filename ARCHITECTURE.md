# 🏗️ Arquitetura Técnica - CAN SLIM Trading System

## Visão Geral da Arquitetura

O sistema é composto por duas camadas principais que trabalham em conjunto:

```
┌─────────────────────────────────────────┐
│           CAMADA 1: Python Engine        │
│  Scanner → RS Rating → Market Pulse      │
│  Pivot Detector → Breakout Validator     │
└─────────────────┬───────────────────────┘
                  │ Output CSV / JSON
┌─────────────────▼───────────────────────┐
│        CAMADA 2: TradingView             │
│  Pine Script Indicator → Alertas         │
│  Confirmação Visual → Execução           │
└─────────────────────────────────────────┘
```

---

## 🐍 Python Engine

### Módulos Principais

#### `scanner.py` - Orquestrador Principal
- Coordena todos os módulos
- Filtra universo de ações (S&P 500)
- Gera lista de candidatos ranqueados
- Exporta resultados para CSV/JSON

#### `rs_rating.py` - Cálculo de Relative Strength
- Implementa fórmula IBD adaptada
- Pesos: 12m(40%) + 9m(20%) + 6m(20%) + 3m(20%)
- Rankeia vs. universo completo (percentil 1-99)

#### `market_pulse.py` - Análise de Mercado
- Monitora S&P 500 (^GSPC)
- Classifica: UPTREND / NEUTRAL / DOWNTREND
- Analisa MAs 50/200 dias + breadth do mercado

#### `pivot_detector.py` - Detecção de Bases
- Identifica Cup with Handle, Flat Base, Double Bottom
- Calcula Buy Points automaticamente
- Valida profundidade e duração das bases

### Fluxo de Dados

```
yfinance API
    │
    ▼
Universe Filter (S&P 500, market cap, volume)
    │
    ▼
RS Rating Calculation (paralelo)
    │
    ▼
Market Pulse Check
    │
    ▼ (apenas em UPTREND)
Pivot Detection
    │
    ▼
Breakout Validation
    │
    ▼
Output: candidates.csv
```

### Configuração (`config.yaml`)

```yaml
universe:
  source: "SP500"
  min_market_cap: 10B
  min_avg_volume: 1M

rs_rating:
  min_threshold: 80

market_pulse:
  index: "^GSPC"
```

---

## 📊 TradingView (Pine Script v5)

### Funcionalidades
- Plotagem de pivots e buy points
- Detecção de breakouts em tempo real
- Sistema de alertas automáticos
- Overlay sobre gráfico de preço

### Variáveis Principais
- `lookback`: Período para detecção de pivot (padrão: 50 barras)
- `buffer`: Buffer acima do buy point (padrão: 5%)
- `volumeAvg`: Média de volume (20 períodos)

---

## 🔄 Pipeline de Execução

### Diário (Pré-mercado)
1. `market_pulse.py` → Status do mercado
2. `scanner.py` → Lista de candidatos
3. Exportar para CSV

### Intraday
1. TradingView monitora candidatos
2. Alertas disparados em breakout
3. Análise manual final

### Pós-mercado
1. Atualizar RS Ratings
2. Revisar posições abertas
3. Log de resultados

---

## 🛠️ Stack Tecnológico

| Componente | Tecnologia | Versão |
|-----------|-----------|--------|
| Linguagem | Python | 3.9+ |
| Dados | yfinance | 0.2.28+ |
| Análise | pandas | 2.0+ |
| Numérico | numpy | 1.24+ |
| Config | PyYAML | 6.0+ |
| Testes | pytest | 7.4+ |
| Logs | loguru | 0.7+ |
| Charts | TradingView Pine Script | v5 |

---

## 📁 Estrutura de Diretórios

```
can-slim-trading-system/
├── README.md
├── METHODOLOGY.md
├── ARCHITECTURE.md
├── PHILOSOPHY.md
├── ROADMAP.md
├── LICENSE
├── .gitignore
├── docs/
│   ├── operational-flow.md
│   ├── design-guidelines.md
│   ├── audit-framework.md
│   └── proxy-vs-proprietary.md
├── python-engine/
│   ├── README.md
│   ├── requirements.txt
│   ├── config.yaml
│   ├── src/
│   │   ├── __init__.py
│   │   ├── scanner.py
│   │   ├── rs_rating.py
│   │   ├── market_pulse.py
│   │   └── pivot_detector.py
│   ├── tests/
│   └── data/output/
├── tradingview/
│   ├── README.md
│   └── can_slim_indicator.pine
├── slides/
│   ├── README.md
│   └── 01-title-slide.md
└── .github/
    └── workflows/
        └── python-tests.yml
```
