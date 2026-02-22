# 🔄 Fluxo Operacional Diário - CAN SLIM Trading System

## Visão Geral

O sistema opera em três janelas temporais: pré-mercado, intraday e pós-mercado.

---

## ⏰ Rotina Pré-Mercado (7:00 - 9:30 AM ET)

### 1. Status do Mercado (7:00 AM)
```bash
cd python-engine
python src/market_pulse.py
```
**Output esperado:**
```
Market Status: UPTREND
S&P 500 vs MA50: +2.3%
S&P 500 vs MA200: +8.1%
Advancing/Declining: 62%/38%
```

### 2. Scanner de Candidatos (7:30 AM)
```bash
python src/scanner.py
```
**Output esperado:**
```
🚀 CAN SLIM Scanner v0.1
Scanning 500 stocks...
Found 12 candidates with RS > 80
Top candidates exported to data/output/candidates.csv
```

### 3. Revisão Manual (8:00 - 9:30 AM)
- Abrir TradingView com candidatos do CSV
- Verificar charts individualmente
- Confirmar formação de base e volume
- Definir buy points e stop losses

---

## 📈 Rotina Intraday (9:30 AM - 4:00 PM ET)

### Monitoramento Passivo
- TradingView alertas configurados para breakouts
- Verificar alertas a cada 30-60 minutos
- **Não tomar decisões baseadas em preço intraday isolado**

### Critérios de Entrada
- [ ] Mercado em UPTREND
- [ ] RS Rating > 80
- [ ] Volume > 40% acima da média de 50 dias
- [ ] Preço acima do buy point (máximo +5%)
- [ ] Formação de base validada

### Execução
- Ordem limite no buy point ou até +5% acima
- Stop loss imediato: 7-8% abaixo do compra
- Tamanho da posição: Risco máximo 1-2% do portfólio

---

## 🌙 Rotina Pós-Mercado (4:00 - 6:00 PM ET)

### 1. Atualizar RS Ratings
- Dados fechados disponíveis
- Recalcular rankings
- Identificar mudanças de tendência

### 2. Revisar Posições Abertas
- Verificar stops atingidos
- Avaliar progresso das posições
- Ajustar trailing stops se necessário

### 3. Log e Documentação
- Registrar trades do dia
- Anotar observações de mercado
- Atualizar watchlist

---

## 📋 Checklist Semanal (Sexta-feira)

- [ ] Revisar todas as posições abertas
- [ ] Analisar trades da semana (ganhos e perdas)
- [ ] Atualizar watchlist para semana seguinte
- [ ] Verificar earnings releases da próxima semana
- [ ] Avaliar saúde geral do mercado
- [ ] Revisar RS Leaders que saíram do top 20%

---

## 🚨 Protocolo de Emergência

### Mercado Muda para DOWNTREND
1. **Parar** todas as novas compras imediatamente
2. Revisar posições abertas
3. Executar stops mais agressivos
4. Mover para cash gradualmente

### Stop Loss Ativado
1. Executar sem hesitação
2. Não fazer média para baixo
3. Registrar na log de trades
4. Analisar o que errou (não o mercado - a análise)
