# 🧠 Filosofia e Princípios - CAN SLIM Trading System

## Princípios Fundamentais

### 1. 📊 Dados Antes de Emoção

Toda decisão de investimento deve ser baseada em dados quantificáveis. O sistema elimina o viés emocional ao fornecer rankings objetivos e critérios claros de entrada e saída.

> *"The whole secret to winning in the stock market is to lose the least amount possible when you're not right."* - William O'Neil

### 2. 🎯 Líderes, Não Seguidores

Investir apenas nos líderes absolutos de cada setor. Ações com RS Rating 80+ representam as empresas que já provaram sua força relativa ao mercado.

### 3. 🛡️ Proteção de Capital Primeiro

O stop loss de 7-8% é inegociável. Preservar capital é a condição necessária para sobreviver no mercado a longo prazo.

### 4. 📈 Seguir o Mercado

Três de quatro ações seguem a direção do mercado. Nunca comprar em DOWNTREND. Cash é uma posição legítima e valiosa.

### 5. 🔄 Processo Repetível e Auditável

Cada decisão deve poder ser replicada e auditada. O sistema é projetado para consistência, não para genialidade esporádica.

---

## Filosofia de Design do Sistema

### Transparência Total
- Cada RS Rating tem cálculo documentado
- Cada sinal tem critérios explícitos
- Logs completos para auditoria

### Simplicidade Efetiva
- Menos filtros, mais qualidade
- Configurações em YAML legível
- Código modular e testável

### Evolução Gradual
- Começar com stubs funcionais
- Adicionar complexidade apenas quando necessário
- Testes antes de produção

---

## O'Neil vs. Trading Algorítmico Puro

| Aspecto | O'Neil/CAN SLIM | Algo Puro |
|---------|-----------------|-----------|
| Fundamentos | Essencial | Irrelevante |
| Timing | Técnico + Volume | Apenas técnico |
| Julgamento | Necessário | Eliminado |
| Edge | Qualidade dos líderes | Velocidade/frequência |

**Nossa abordagem**: Híbrido - quantificar o que pode ser quantificado, preservar o julgamento onde ele adiciona valor.

---

## Princípios de Engenharia

1. **Modularidade**: Cada módulo faz uma coisa bem
2. **Testabilidade**: Código que pode ser testado unitariamente
3. **Configurabilidade**: Parâmetros em config.yaml, não hardcoded
4. **Reprodutibilidade**: Mesmo input → mesmo output
5. **Observabilidade**: Logs estruturados com loguru

---

## Evolução Filosófica

O sistema começou como uma tentativa de replicar o IBD manualmente. Evoluiu para um sistema automatizado que:
- Elimina o trabalho repetitivo de coleta de dados
- Mantém o julgamento humano nos momentos críticos
- Aprende com cada ciclo de mercado
- Documenta decisões para aprendizado futuro
