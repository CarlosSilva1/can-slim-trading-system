# 🎨 Design Guidelines - Apresentação Gamma

## Visão Geral

Este documento define os padrões de design para apresentações e documentação visual do CAN SLIM Trading System, otimizados para a plataforma Gamma.

---

## 🎨 Paleta de Cores

### Cores Primárias
| Cor | Hex | Uso |
|-----|-----|-----|
| Verde Trading | `#00C853` | Sinais de compra, UPTREND, ganhos |
| Vermelho Stop | `#D50000` | Stop loss, DOWNTREND, perdas |
| Azul Dados | `#1565C0` | Dados, RS Rating, análise |
| Dourado Líder | `#FFD600` | Líderes, top picks, destaques |
| Cinza Neutro | `#546E7A` | NEUTRAL, contexto, background |

### Cores de Suporte
| Cor | Hex | Uso |
|-----|-----|-----|
| Branco | `#FFFFFF` | Background principal |
| Preto | `#212121` | Texto principal |
| Cinza Claro | `#F5F5F5` | Background cards |

---

## 📝 Tipografia

### Hierarquia
- **H1**: 36px, Bold - Títulos principais
- **H2**: 28px, SemiBold - Seções
- **H3**: 22px, Medium - Subseções
- **Body**: 16px, Regular - Texto corrido
- **Caption**: 12px, Regular - Notas, fontes

### Fonte Recomendada
- **Headings**: Inter ou Montserrat
- **Body**: Inter ou Source Sans Pro
- **Code**: JetBrains Mono ou Fira Code

---

## 📊 Padrões de Slides

### Slide de Título
```
[Ícone/Logo]
[Título Principal - H1]
[Subtítulo - H2, cor secundária]
[Data / Versão - Caption]
```

### Slide de Dados
```
[Título da Seção - H2]
[Métrica Principal - Número grande, cor destacada]
[Contexto - Body]
[Fonte / Nota - Caption]
```

### Slide de Comparação
```
[Título - H2]
[Tabela comparativa 2-3 colunas]
[Highlight da melhor opção em verde]
```

---

## 📐 Layout e Espaçamento

- **Margem lateral**: 48px mínimo
- **Espaçamento entre seções**: 32px
- **Padding de cards**: 24px
- **Máximo 3 pontos por slide**
- **Máximo 50 palavras por slide**

---

## 🖼️ Iconografia

Usar emojis ou ícones flat:
- 🚀 = Momentum, crescimento
- 📊 = Dados, análise
- 🎯 = Meta, objetivo
- 🛡️ = Proteção, stop loss
- 📈 = Alta, UPTREND
- 📉 = Baixa, DOWNTREND
- ⚡ = Velocidade, eficiência
- 🧠 = Análise, inteligência

---

## 📱 Formatos de Exportação

### Gamma
- Formato: Web interativo
- Resolução: 1920x1080 (16:9)
- Modo: Light (padrão)

### PDF
- Resolução: 300 DPI
- Formato: A4 landscape
- Incluir números de página

### Apresentação ao Vivo
- Modo: Fullscreen
- Fontes: +20% do padrão
- Contraste: Alto
