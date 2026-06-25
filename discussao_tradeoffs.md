# Discussão de Trade-offs: Formulação Multiobjetivo vs. Single-objective

## 1. Contextualização do problema

O problema consiste em selecionar exatamente **k = 12** municípios dentre os 246 de Goiás para instalar facilidades, respeitando um orçamento de **R$ 20.939.128,69**, de modo a minimizar a distância média ponderada pela população até a facilidade mais próxima.

Na versão single-objective, esse problema é reduzido a uma única grandeza escalar — a distância média ponderada — com a restrição orçamentária tratada por penalização. Na versão multiobjetivo implementada com NSGA-II, três objetivos são otimizados simultaneamente:

- **f₁**: distância média ponderada pela população até a facilidade mais próxima (km) — *minimizar*
- **f₂**: percentual da população não coberta dentro de 80 km — *minimizar* (equivalente a maximizar cobertura)
- **f₃**: percentil 95 ponderado das distâncias — *minimizar* (medida de equidade espacial)

Essa distinção de formulação é a origem de todos os trade-offs discutidos a seguir.

---

## 2. Trade-off central: eficiência média vs. cobertura vs. equidade

O principal trade-off identificado nos experimentos é que **otimizar exclusivamente a distância média não equivale a maximizar a cobertura nem a garantir equidade espacial**. Os números abaixo resumem os resultados médios sobre cinco sementes:

| Método | Dist. média (km) | Cobertura ≤ 80 km (%) | P95 distância (km) |
|---|---|---|---|
| AG baseline (gen=300) | 39,74 ± 0,49 | 84,98 ± 2,97 | 109,91 ± 5,41 |
| AG single-obj. V3 (gen=500) | **39,44 ± 0,60** | 85,51 ± 2,49 | 108,87 ± 3,68 |
| NSGA-II (compromisso) | 40,34 ± 0,50 | **90,40 ± 0,33** | **97,90 ± 4,22** |

O AG com 500 gerações encontra a menor distância média (39,44 km), mas a cobertura que entrega (85,51%) é praticamente a mesma do baseline. O NSGA-II, ao tratar cobertura e equidade como objetivos independentes, entrega **+4,89 pontos percentuais de cobertura** e **−10,97 km no P95**, ao custo de apenas **+0,90 km na distância média**.

Esse resultado mostra um fenômeno estrutural do problema: minimizar a média privilegia regiões mais populosas e centrais, que naturalmente já estariam próximas de alguma facilidade. As populações periféricas — as que ficam além de 80 km — têm peso proporcional pequeno na média, portanto o single-objective as ignora sistematicamente. A formulação multiobjetivo torna esse custo explícito e negociável.

---

## 3. Trade-off entre os três objetivos na fronteira de Pareto

A fronteira de Pareto gerada pelo NSGA-II com 5 sementes (42, 123, 456, 789, 1011) contém entre **10 e 28 soluções não-dominadas por semente**, cobrindo os seguintes intervalos:

- f₁ (distância média): de ≈ 38,1 km a ≈ 52,0 km
- cobertura ≤ 80 km: de ≈ 83% a ≈ 92,8%
- f₃ (P95 ponderado): de ≈ 88,1 km a ≈ 107,4 km

Três relações de trade-off se destacam nas projeções 2D:

### 3.1 Distância média × cobertura (f₁ × cobertura)

Este é o trade-off mais intuitivo e relevante para o tomador de decisão. Soluções que minimizam a distância média tendem a concentrar as facilidades nas regiões mais populosas de Goiás, reduzindo o numerador ponderado de f₁ mas deixando municípios periféricos além do raio de 80 km. Soluções que maximizam cobertura distribuem as facilidades de forma mais dispersa, o que pode aumentar levemente a distância média mas garante que a maior parcela possível da população tenha acesso em até 80 km.

A fronteira em degraus (envelope Pareto 2D, figura `fig8_fronteira_pareto.png`) delimita o limite do que é alcançável: não é possível estar simultaneamente abaixo de um certo nível de distância média **e** acima de um certo nível de cobertura com a configuração testada.

### 3.2 Distância média × P95 (f₁ × f₃)

As duas métricas de distância são positivamente correlacionadas, mas não idênticas. O P95 penaliza desproporcionalmente soluções que deixam um pequeno grupo de municípios muito afastado, mesmo que a média geral seja baixa. Soluções que reduzem f₁ abaixo de ≈ 40 km tendem a apresentar P95 acima de 100 km — o que significa que pelo menos 5% da população ponderada percorre mais de 100 km. A fronteira nesta projeção mostra que reduzir o P95 de forma significativa requer aceitar um pequeno aumento na distância média.

### 3.3 Cobertura × P95 (cobertura × f₃)

Este é o trade-off de equidade: cobertura mede se a população está dentro de um raio fixo de 80 km, enquanto o P95 mede a cauda da distribuição de acesso. A correlação negativa entre os dois (quanto maior a cobertura, menor tende a ser o P95) sugere que eles são parcialmente redundantes — ambos capturam aspectos do acesso das populações mais distantes —, mas a fronteira mostra que nenhum domina completamente o outro. Há soluções que melhoram cobertura sem melhorar o P95, e vice-versa.

---

## 4. Trade-off na modelagem das restrições

A restrição orçamentária (C2) é tratada de formas distintas nas duas abordagens, com consequências práticas diferentes.

**No AG single-objective**, C2 é incorporada por penalização escalar:

```
f_pen(x) = f(x) + λ · max(0, custo_total − B)
```

O coeficiente λ é calibrado empiricamente pela razão entre a magnitude típica de f₁ e a violação orçamentária típica. Isso converte a violação de reais para km, tornando-a comparável à função objetivo. A abordagem é simples de implementar, mas introduz um parâmetro que precisa ser ajustado com cuidado: λ muito pequeno permite soluções que violam o orçamento; λ muito grande pode tornar a penalidade dominante e comprometer a busca da melhor solução viável.

**No NSGA-II**, C2 é tratada por **dominância restrita**:
- soluções viáveis sempre dominam soluções inviáveis, independentemente dos objetivos;
- entre soluções inviáveis, a de menor violação orçamentária é preferida;
- entre soluções viáveis, aplica-se a dominância de Pareto usual.

Essa abordagem é mais robusta: não requer calibração de parâmetro e garante que a fronteira de Pareto final contenha apenas soluções viáveis. Nos resultados, de fato, todas as soluções do front NSGA-II apresentam violação orçamentária zero, confirmando que a dominância restrita funcionou corretamente.

O trade-off aqui é de **custo de implementação vs. garantia de viabilidade**: a penalização é mais simples, mas a dominância restrita é mais confiável quando a violação de restrições é inaceitável na prática.

---

## 5. Trade-off: qualidade de pico vs. estabilidade

O desvio padrão da cobertura é um indicador revelador da estabilidade dos métodos:

| Método | Desvio padrão da cobertura (%) |
|---|---|
| AG baseline | 2,97 |
| AG V3 (gen=500) | 2,49 |
| NSGA-II (compromisso) | **0,33** |

O NSGA-II é **9 vezes mais estável** que o baseline na cobertura. Isso ocorre porque o mecanismo de ordenação por rank e distância de crowding mantém a diversidade da população durante toda a busca, impedindo que o algoritmo colapse em um único ótimo local. O AG single-objective, por selecionar apenas uma solução por geração, é mais suscetível a variações entre sementes.

A contrapartida é que o NSGA-II abre mão da melhor solução de pico em f₁: a melhor distância média encontrada pelo NSGA-II em qualquer seed é ≈ 38,1 km (melhor ponto do front), enquanto o AG V3 chega a 38,62 km como solução única — e o AG baseline já alcança 39,02 km de forma mais rápida e simples.

Portanto: **quando se busca a melhor solução possível para um único critério e aceita-se variabilidade entre execuções, o single-objective é mais competitivo. Quando se precisa de resultados robustos e equilibrados entre múltiplos critérios, o NSGA-II é superior.**

---

## 6. Trade-off computacional

| Método | Tempo médio por execução (s) |
|---|---|
| AG baseline (gen=300) | 4,61 |
| AG V3 (gen=500) | 7,63 |
| NSGA-II (gen=300) | 7,96 |

O NSGA-II tem custo por geração maior que o AG baseline porque, a cada geração, avalia a população combinada de pais e filhos (2×pop_size indivíduos) para realizar a seleção por dominância. Ainda assim, o tempo total é comparável ao AG V3 (gen=500), porque o NSGA-II usa apenas 300 gerações.

A diferença mais importante é o **output**: o AG single-objective entrega **uma solução** por execução, enquanto o NSGA-II entrega uma **fronteira com 10 a 28 soluções não-dominadas** por execução. Isso significa que, pelo mesmo custo computacional, o NSGA-II devolve um conjunto de alternativas que permite ao tomador de decisão escolher o ponto da fronteira que melhor se alinha às prioridades políticas ou operacionais — sem precisar reexecutar o algoritmo para cada combinação de pesos.

---

## 7. A solução de compromisso e sua limitação

Para facilitar a comparação numérica, o NSGA-II foi reduzido a uma única solução representativa por semente usando a **solução de compromisso** (ponto de menor norma L2 após normalização dos três objetivos no front). Essa solução é a que "menos piora" em nenhum dos três critérios simultaneamente.

No entanto, a escolha da solução de compromisso introduz um julgamento de valor implícito: ao normalizar e medir distância euclidiana, os três objetivos recebem peso igual. Na prática, um gestor público pode priorizar cobertura (acesso básico para mais pessoas) em detrimento de reduzir o P95 (equidade espacial), ou vice-versa. A fronteira de Pareto preserva essa escolha em aberto; a solução de compromisso a resolve de uma forma específica.

Isso evidencia um trade-off metodológico fundamental: **a formulação multiobjetivo não elimina a necessidade de julgamento sobre preferências — ela a adia para o momento da escolha da solução**, o que é, em geral, desejável, pois essa escolha pode ser feita com informação completa sobre os custos de cada compromisso.

---

## 8. Síntese dos trade-offs

| Dimensão | AG Single-objective | NSGA-II |
|---|---|---|
| Melhor distância média (km) | **38,62** | 38,10 (no front, não como solução única) |
| Cobertura média (%) | 85,51 | **90,40** |
| P95 médio (km) | 108,87 | **97,90** |
| Estabilidade (desvio da cobertura) | 2,49% | **0,33%** |
| Modelagem da restrição C2 | Penalização (requer calibração de λ) | **Dominância restrita (sem parâmetro)** |
| Output por execução | 1 solução | **10–28 soluções** |
| Tempo por execução | ≈ 7,6 s | ≈ 8,0 s |
| Flexibilidade de decisão | Baixa (critério fixo) | **Alta (fronteira de Pareto)** |

A formulação multiobjetivo com NSGA-II representa um ganho qualitativo significativo quando o problema envolve múltiplas dimensões de valor que não podem ser colapsadas em uma única função escalar sem perda de informação. No caso da localização de facilidades em Goiás, a tensão entre eficiência (distância média) e equidade (cobertura e P95) é inerente ao problema e não deve ser resolvida arbitrariamente na modelagem — ela deve ser exposta ao tomador de decisão, que é exatamente o que a fronteira de Pareto faz.
