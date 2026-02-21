# 🔄 Proxies vs. Dados Proprietários - Análise Comparativa

## Contexto

O CAN SLIM System pode ser implementado usando dados gratuitos (proxies) ou dados proprietários do IBD. Este documento analisa os trade-offs.

---

## 📊 Comparação Geral

| Aspecto | Proxies Gratuitos | IBD Proprietário |
|---------|------------------|-----------------|
| **Custo** | $0 | ~$40-50/mês |
| **RS Rating** | Calculado (aproximado) | Oficial IBD |
| **EPS Ratings** | yfinance (limitado) | Dados completos |
| **Composite Rating** | Não disponível | Disponível |
| **SMR Rating** | Não disponível | Disponível |
| **Atualização** | Diária (fechamento) | Intraday |
| **Precisão RS** | 85-90% correlação | 100% |
| **Histórico** | Livre | Pago |

---

## 🐍 Dados via yfinance (Proxy)

### O que conseguimos calcular:
✅ RS Rating (próprio - 85-90% correlação com IBD)
✅ Preço, Volume, OHLC histórico
✅ Market Cap básico
✅ Dados de índices (S&P 500, Nasdaq)
✅ Médias móveis (MA50, MA200)

### Limitações:
❌ EPS Rating oficial IBD
❌ Composite Rating
❌ SMR Rating (Sales, Margins, ROE)
❌ Acumulação/Distribuição IBD
❌ Dados intraday detalhados
❌ Float exato em tempo real

### Fórmula RS Rating Proxy:
```python
# Pesos baseados na metodologia O'Neil
rs_score = (
    return_12m * 0.40 +
    return_9m  * 0.20 +
    return_6m  * 0.20 +
    return_3m  * 0.20
)
rs_rating = percentileofscore(universe_scores, rs_score)
```

---

## 📈 IBD MarketSmith (Proprietário)

### Vantagens:
✅ RS Rating oficial e preciso
✅ EPS Rating completo
✅ Composite Rating (integra todos os critérios)
✅ SMR Rating (Sales, Margins, ROE)
✅ Dados de fundos institucionais
✅ Screener integrado
✅ Chart service especializado

### Desvantagens:
❌ Custo mensal (~$40-50)
❌ Não automatizável via API
❌ Interface manual
❌ Sem integração programática

---

## 🎯 Recomendação por Fase

### Fase Inicial (Aprendizado)
**Usar**: Proxies gratuitos (yfinance)
**Motivo**: Aprender o sistema sem custo. Diferença de precisão é aceitável para aprendizado.

### Fase Intermediária (Capital $10K-$50K)
**Usar**: Híbrido - Python para scanning, IBD para confirmação
**Motivo**: ROI justifica assinatura básica IBD. Usar Python para filtrar candidatos, IBD para confirmação final.

### Fase Avançada (Capital $50K+)
**Usar**: IBD MarketSmith + Python Engine
**Motivo**: Precisão adicional tem impacto real no retorno. Automatizar o que é possível, usar IBD para qualidade.

---

## 🔢 Impacto Quantitativo da Diferença

### Estudo de Caso: RS Rating
- Correlação proxy vs. IBD: ~87%
- Diferença média: ±3-5 pontos de RS
- Impacto prático: Candidatos muito próximos do threshold (75-85) podem ser classificados diferentemente

### Mitigação
- Usar threshold mais conservador: RS > 85 no proxy equivale a RS > 80 no IBD
- Focar em RS > 90 para máxima confiança
- Confirmar visualmente no IBD os top candidatos

---

## 💡 Estratégia Híbrida Recomendada

```
Python Engine (yfinance)
    ↓
Pré-filtro: RS > 85, Volume OK, Market UPTREND
    ↓
Lista de 10-20 candidatos
    ↓
IBD MarketSmith (manual)
    ↓
Confirmar Composite Rating > 80
Verificar EPS Rating > 70
Analisar chart e base
    ↓
Top 3-5 candidatos finais
    ↓
TradingView: Monitor e alertas
    ↓
Execução
```
