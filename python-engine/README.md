# 🐍 Python Engine - CAN SLIM Trading System

## Visão Geral

O Python Engine é o cérebro quantitativo do sistema. Responsável por calcular RS Ratings, classificar o estado do mercado, detectar padrões técnicos e gerar a lista de candidatos.

---

## 🚀 Quick Start

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar scanner principal
python src/scanner.py

# Executar módulos individuais
python src/market_pulse.py
python src/rs_rating.py
```

---

## 📁 Estrutura

```
python-engine/
├── README.md           # Este arquivo
├── requirements.txt    # Dependências Python
├── config.yaml        # Configurações do sistema
├── src/
│   ├── __init__.py
│   ├── scanner.py      # Orquestrador principal
│   ├── rs_rating.py    # Cálculo RS Rating
│   ├── market_pulse.py # Status do mercado
│   └── pivot_detector.py # Detecção de bases
├── tests/             # Testes unitários (pytest)
└── data/
    └── output/        # Resultados CSV/JSON
```

---

## 🔧 Configuração

Editar `config.yaml` para ajustar parâmetros:

```yaml
rs_rating:
  min_threshold: 80  # Mínimo RS para candidatos

market_pulse:
  index: "^GSPC"  # S&P 500

pivot:
  min_depth: 0.12  # Profundidade mínima da base (12%)
  max_depth: 0.45  # Profundidade máxima (45%)
```

---

## 📦 Dependências

| Pacote | Versão | Uso |
|--------|--------|-----|
| pandas | 2.0+ | Manipulação de dados |
| numpy | 1.24+ | Cálculos numéricos |
| yfinance | 0.2.28+ | Dados de mercado |
| pyyaml | 6.0+ | Configurações |
| pytest | 7.4+ | Testes |
| loguru | 0.7+ | Logging |

---

## 🧪 Testes

```bash
# Executar todos os testes
pytest tests/

# Com verbosidade
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=src
```

---

## 📊 Output

O scanner gera `data/output/candidates.csv` com:
- Ticker
- RS Rating (1-99)
- Preço atual
- Volume relativo
- Padrão detectado
- Buy Point
- Stop Loss sugerido

---

## ⚠️ Status

> **v0.1 - Em Desenvolvimento**
> Módulos são stubs funcionais. Implementação completa em progresso.
> Ver [ROADMAP.md](../ROADMAP.md) para cronograma.
