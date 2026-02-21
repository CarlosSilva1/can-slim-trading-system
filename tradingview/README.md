# 📈 TradingView - CAN SLIM Indicator

## Visão Geral

Pine Script v5 para visualização e alertas do sistema CAN SLIM no TradingView.

---

## 🚀 Como Usar

1. Abrir [TradingView](https://www.tradingview.com)
2. Acessar **Pine Editor** (botão no rodapé)
3. Copiar o conteúdo de `can_slim_indicator.pine`
4. Colar no Pine Editor
5. Clicar em **Add to chart**

---

## ⚙️ Parâmetros

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| Pivot Lookback | 50 | Barras para detecção do pivot máximo |
| Buy Point Buffer % | 0.05 | Buffer acima do pivot (5%) |

---

## 📊 O que o Indicador Mostra

- **Linha Azul**: Pivot (máximo do período de lookback)
- **Linha Verde**: Buy Point (pivot + buffer)
- **Triângulo Verde**: Sinal de Breakout detectado

---

## 🔔 Alertas

O indicador inclui `alertcondition` para breakouts:
- Condição: `close > buyPoint AND volume > volumeAvg * 1.5`
- Mensagem: `"{{ticker}} breakout!"`

### Configurar Alerta:
1. Clique com botão direito no gráfico
2. Selecione **Add Alert**
3. Em **Condition**, selecione **CAN SLIM Indicator**
4. Selecione **Breakout Alert**
5. Configure notificação (email, push, webhook)

---

## 🔄 Versões Futuras

- [ ] Detecção de Cup with Handle
- [ ] Detecção de Flat Base
- [ ] RS Rating overlay (integrado com Python Engine)
- [ ] Dashboard de múltiplos tickers
- [ ] Alertas avançados com dados fundamentais

---

## ⚠️ Limitações

- O Pine Script não tem acesso a dados fundamentais (EPS, RS real do IBD)
- Volume relativo é calculado vs. média de 20 períodos (não 50 dias como IBD)
- Usar em conjunto com o Python Engine para análise completa
