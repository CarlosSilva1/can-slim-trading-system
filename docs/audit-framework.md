# 🔍 Framework de Auditoria - CAN SLIM Trading System

## Objetivo

Garantir que todas as decisões de trading sejam rastreáveis, reproduzíveis e auditáveis. A transparência é fundamental para o aprendizado contínuo.

---

## 📋 Estrutura de Auditoria

### Nível 1: Trade Log

Cada trade deve ser registrado com:

| Campo | Descrição | Exemplo |
|-------|-----------|---------|
| Data entrada | Data/hora da compra | 2025-01-15 10:32 ET |
| Ticker | Símbolo da ação | NVDA |
| Preço entrada | Preço de compra | $485.20 |
| Quantidade | Número de ações | 10 |
| Buy Point | Pivot calculado | $482.00 |
| RS Rating entrada | RS no momento da compra | 94 |
| Market Status | Status do mercado | UPTREND |
| Stop Loss | Preço de stop definido | $449.24 (-7%) |
| Motivo entrada | Padrão identificado | Cup with Handle |
| Data saída | Data/hora da venda | 2025-02-20 14:15 ET |
| Preço saída | Preço de venda | $589.40 |
| Resultado % | P&L percentual | +21.5% |
| Motivo saída | Razão da venda | Target 20% atingido |

---

## 📊 Métricas de Performance

### Mensais
- Win Rate (% de trades positivos)
- Average Win / Average Loss (Expectancy)
- Profit Factor = Gross Profit / Gross Loss
- Maximum Drawdown
- Número de trades

### Trimestrais
- Retorno vs. S&P 500 (benchmark)
- Sharpe Ratio estimado
- Análise por setor
- Análise por padrão (Cup, Flat, Double Bottom)

---

## 🔄 Processo de Revisão

### Revisão Semanal
1. Compilar todos os trades da semana
2. Calcular win rate e expectancy
3. Identificar trades que não seguiram o processo
4. Documentar aprendizados

### Revisão Mensal
1. Análise estatística completa
2. Comparar com benchmark S&P 500
3. Revisar parâmetros do sistema se necessário
4. Atualizar config.yaml se mudanças forem justificadas

### Revisão Trimestral
1. Análise de mercado completa
2. Backtesting de mudanças propostas
3. Decisão sobre evolução do sistema
4. Atualizar ROADMAP.md

---

## 🚨 Red Flags - Sinais de Alerta

### Processo Quebrado
- [ ] Trade sem RS Rating > 80 registrado
- [ ] Compra em DOWNTREND
- [ ] Stop loss > 8% do preço de entrada
- [ ] Posição sem stop loss definido

### Performance Preocupante
- [ ] Win rate < 30% por 3 meses consecutivos
- [ ] Perda > 20% do portfólio em um trimestre
- [ ] 3 stops consecutivos atingidos

### Ação Corretiva
1. **Parar** novas operações
2. **Analisar** causa raiz
3. **Corrigir** processo ou parâmetros
4. **Retornar** com position sizing reduzido

---

## 📁 Estrutura de Arquivos de Auditoria

```
audit/
├── trades/
│   ├── 2025-Q1-trades.csv
│   ├── 2025-Q2-trades.csv
│   └── ...
├── reports/
│   ├── 2025-01-monthly-report.md
│   ├── 2025-Q1-quarterly-report.md
│   └── ...
└── scanner-outputs/
    ├── 2025-01-15-candidates.csv
    └── ...
```

---

## 🎯 KPIs do Sistema

| KPI | Meta | Mínimo Aceitável |
|-----|------|-----------------|
| Win Rate | > 50% | > 35% |
| Avg Win / Avg Loss | > 3:1 | > 2:1 |
| Profit Factor | > 2.0 | > 1.5 |
| Max Drawdown | < 15% | < 25% |
| Retorno vs. SPX | Outperform | Equal |
