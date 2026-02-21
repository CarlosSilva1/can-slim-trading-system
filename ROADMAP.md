# 🗺️ Roadmap - CAN SLIM Trading System

## Versão Atual: v0.1 (MVP / Stub)

Status atual: Estrutura base criada, módulos em desenvolvimento.

---

## 🚀 Fase 1: MVP Funcional (v0.2)

**Objetivo**: Sistema funcionando end-to-end com dados reais.

- [ ] `rs_rating.py` - Implementação completa do cálculo RS
- [ ] `market_pulse.py` - Classificação UPTREND/NEUTRAL/DOWNTREND
- [ ] `scanner.py` - Pipeline completo S&P 500
- [ ] Testes unitários básicos (pytest)
- [ ] Output CSV com candidatos ranqueados

**ETA**: Q1 2025

---

## 📊 Fase 2: Detecção de Padrões (v0.3)

**Objetivo**: Identificar automaticamente bases técnicas.

- [ ] `pivot_detector.py` - Cup with Handle
- [ ] `pivot_detector.py` - Flat Base
- [ ] `pivot_detector.py` - Double Bottom
- [ ] Cálculo automático de Buy Points
- [ ] Visualização básica com matplotlib

**ETA**: Q2 2025

---

## 📈 Fase 3: TradingView Integration (v0.4)

**Objetivo**: Pine Script completo com todas as funcionalidades.

- [ ] Indicator completo com todos os padrões
- [ ] Sistema de alertas avançado
- [ ] Dashboard de watchlist
- [ ] Integração com output do Python Engine

**ETA**: Q2 2025

---

## 🤖 Fase 4: Automação (v0.5)

**Objetivo**: Execução automatizada com mínima intervenção.

- [ ] Scheduler diário (pre-market)
- [ ] Notificações por email/Telegram
- [ ] Dashboard web básico
- [ ] Paper trading para validação

**ETA**: Q3 2025

---

## 🧠 Fase 5: Machine Learning (v1.0)

**Objetivo**: Aprimorar modelos com dados históricos.

- [ ] Backtesting engine
- [ ] Otimização de parâmetros
- [ ] Modelos preditivos de breakout
- [ ] Análise de sentimento (news)

**ETA**: Q4 2025

---

## 📋 Backlog (Sem Data)

- Suporte a mercados internacionais (BDRs, ETFs)
- API REST para integração externa
- Mobile app para alertas
- Análise de opções (calls cobertas)
- Relatório PDF automatizado

---

## 🔄 Ciclo de Desenvolvimento

1. **Implementar** → Escrever código funcional
2. **Testar** → Testes unitários + integração
3. **Validar** → Dados históricos (backtest manual)
4. **Documentar** → Atualizar docs
5. **Iterar** → Próxima funcionalidade

---

## 📌 Princípios do Roadmap

- Funcionalidade > Perfeição
- Dados reais > Dados simulados
- Testes sempre
- Documentação junto com código
