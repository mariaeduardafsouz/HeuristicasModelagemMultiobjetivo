# HeuristicasModelagemMultiobjetivo

Repositório dedicado para o desenvolvimento do projeto da disciplina **Heurísticas e Modelagem Multiobjetivo**.

**Tema:** Localização de facilidades em Goiás  
**Equipe:** Christian de Souza Ramos · Igor Garbin Manzan Mazo · Leonardo Lima de Oliveira · Livia Maria Santos Rocha · Maria Eduarda Fernandes de Souza

---

## Como executar

```bash
pip install -r dataset/requirements.txt

# Gerar dataset processado
python dataset/build_dataset.py

# Rodar experimentos do AG
python run_experimentos.py

# Rodar com múltiplas sementes
python run_seeds.py

# Gerar figuras
python gerar_figuras.py

# Rodar comparação multiobjetivo: AG baseline, AG V3 e NSGA-II
python run_comparacao_multiobjetivo.py

# Gerar figuras da comparação multiobjetivo
python gerar_figuras_nsga2.py
```

---

## Estrutura do repositório

```
├── algoritmo.py                  # Algoritmo Genético (funções de fitness, operadores)
├── run_experimentos.py           # Variações de hiperparâmetros
├── run_seeds.py                  # Execução com 5 sementes fixas
├── gerar_figuras.py              # Geração das figuras finais
├── modelagem.md                  # Formulação matemática do problema
├── resumo.csv                    # Resumo estatístico por configuração
├── resultados_experimentos.csv   # Resultados por variação de hiperparâmetro
├── resultados_detalhados.json    # Resultados por semente (baseline)
├── fig1_boxplot.png              # Distribuição dos fitness por configuração
├── fig2_convergencia.png         # Curva de convergência do AG
├── fig3_barras.png               # Comparação entre configurações
├── fig4_mapa.png                 # Mapa das facilidades selecionadas
└── dataset/
    ├── raw/                      # Dados brutos do IBGE
    └── processed/                # Dataset final (CSV, matriz de distâncias, config)
```

Arquivos adicionais da extensão multiobjetivo:

- `run_comparacao_multiobjetivo.py`: reexecuta AG baseline, AG V3 e NSGA-II com 5 sementes.
- `gerar_figuras_nsga2.py`: gera os gráficos novos a partir dos CSVs já salvos.
- `resultados_comparacao_multiobjetivo.csv`: métricas por semente para os três métodos.
- `resumo_comparacao_multiobjetivo.csv`: resumo estatístico da comparação.
- `historico_nsga2.csv`: evolução do NSGA-II por geração.
- `fig6_comparacao_multiobjetivo.png`, `fig7_convergencia_nsga2.png`: novas figuras de análise.

---

## Resultados e Análise

### Configurações avaliadas

O Algoritmo Genético foi executado com cinco sementes fixas (42, 123, 456, 789, 1011) para cada configuração, garantindo reprodutibilidade e permitindo comparação estatística robusta. A métrica principal é a **distância média ponderada pela população (km)** — quanto menor, melhor.

| Configuração       | pop\_size | n\_gen | Média (km) | Mediana (km) | Desvio Padrão | Melhor (km) | Tempo médio |
|--------------------|-----------|--------|------------|--------------|---------------|-------------|-------------|
| AG baseline        | 100       | 300    | 40,3286    | 40,3681      | 0,3592        | 39,7478     | 31,6 s      |
| AG V3 (pop=100, gen=500) | 100 | 500  | 39,3516    | 39,7478      | 1,0178        | 37,5711     | 53,0 s      |

### Verificação da instância

Ambas as configurações utilizaram exatamente a mesma instância do problema: 246 municípios do estado de Goiás (Censo IBGE 2022), k = 12 facilidades a instalar, orçamento B = R$ 20.939.128,69, e matriz de distâncias Haversine calculada sobre os centroides municipais no sistema SIRGAS 2000. A comparação entre baseline e V3 é, portanto, direta e justa.

### Interpretação dos resultados

A configuração **V3_gen500** (pop\_size = 100, n\_gen = 500) obteve a melhor média dentre todas as variações testadas, com **39,3516 km**, representando uma melhoria de **2,42%** sobre o baseline (40,3286 km). A melhoria na melhor solução encontrada foi ainda mais expressiva: **5,48%** (37,5711 km contra 39,7478 km no baseline). Esse resultado indica que ampliar o número de gerações de 300 para 500 permite ao algoritmo explorar melhor o espaço de busca e escapar de ótimos locais, especialmente quando combinado com a operação de reparo que garante a viabilidade das soluções a cada geração.

No entanto, o ganho de qualidade tem um custo: o desvio padrão do V3 (1,0178) é aproximadamente **2,83 vezes maior** que o do baseline (0,3592), evidenciando maior variabilidade entre as execuções. Isso significa que, apesar de encontrar soluções melhores em média, o V3 é menos estável — algumas sementes convergem para soluções muito boas, enquanto outras ficam presas em regiões de qualidade inferior. Esse trade-off entre qualidade esperada e estabilidade é característico de configurações com maior pressão de busca, e reforça a importância de executar múltiplas sementes ao avaliar metaheurísticas.

Em termos práticos, a diferença de **~1 km** na distância média ponderada equivale, considerando a população total de Goiás (7.056.495 habitantes), a uma redução significativa no custo coletivo de deslocamento até as facilidades instaladas — o que justifica o maior tempo de execução da configuração V3 (53,0 s contra 31,6 s do baseline).

---

## Comparação multiobjetivo com NSGA-II

Foi implementado um NSGA-II para tratar explicitamente três objetivos:

1. minimizar a distância média ponderada pela população;
2. maximizar a cobertura populacional em até 80 km, implementado como minimização da população descoberta;
3. minimizar o percentil 95 ponderado das distâncias, usado como medida de desigualdade espacial no acesso.

A restrição de exatamente `k = 12` facilidades continua sendo garantida pelo operador `repair`. A restrição orçamentária é tratada por dominância restrita: soluções viáveis dominam soluções inviáveis; entre soluções inviáveis, vence a de menor violação orçamentária.

Os resultados abaixo foram gerados por `run_comparacao_multiobjetivo.py`, que reexecuta o AG com a penalização `LAMBDA` estimada de forma determinística. Por isso, estes números são a referência mais consistente para comparar baseline, single-objective e NSGA-II.

| Método | Configuração | Distância média (km) | Cobertura 80 km (%) | P95 distância (km) | Gini espacial | Melhor distância (km) | Violação máxima |
|--------|--------------|----------------------|---------------------|--------------------|---------------|-----------------------|-----------------|
| AG baseline | pop=100, gen=300 | 39,7370 ± 0,4940 | 84,9825 ± 2,9734 | 109,9120 ± 5,4085 | 0,3224 ± 0,0122 | 39,0240 | 0 |
| AG single-objective V3 | pop=100, gen=500 | **39,4369 ± 0,6015** | 85,5147 ± 2,4929 | 108,8669 ± 3,6754 | 0,3341 ± 0,0149 | **38,6152** | 0 |
| NSGA-II compromisso | pop=100, gen=300 | 40,3372 ± 0,5001 | **90,4040 ± 0,3250** | **97,9035 ± 4,2181** | **0,3154 ± 0,0192** | 39,9881 | 0 |

O AG V3 continua sendo a melhor alternativa quando o único critério é distância média. O NSGA-II, porém, entrega uma solução de compromisso mais equilibrada: em relação ao V3, perde cerca de **0,90 km** na distância média, mas ganha aproximadamente **4,89 pontos percentuais** de cobertura em até 80 km e reduz o P95 em cerca de **10,96 km**. Isso mostra que a formulação multiobjetivo consegue reduzir a desigualdade espacial de acesso, mesmo sem otimizar exclusivamente a média.

As novas figuras geradas são:

- `fig6_comparacao_multiobjetivo.png`: comparação média dos três métodos.
- `fig7_convergencia_nsga2.png`: evolução dos objetivos ao longo das gerações.

---

## Diferencial ético — equidade espacial

### Métrica de equidade: índice de Gini espacial

A proposta do projeto define como diferencial ético a incorporação de equidade espacial no acesso às facilidades. Para medir isso formalmente, foi implementado o **índice de Gini espacial**, calculado sobre as distâncias mínimas de cada município até a facilidade mais próxima:

```
G = (2 · Σᵢ i·dᵢ) / (n · Σᵢ dᵢ) − (n+1)/n
```

onde `dᵢ` são as distâncias mínimas de cada um dos 246 municípios à facilidade mais próxima, ordenadas em ordem crescente. O índice varia de 0 (todos os municípios equidistantes das facilidades — acesso perfeitamente igual) a 1 (máxima concentração do acesso em poucos municípios). A função `gini_espacial(selected)` está implementada em [`algoritmo.py`](algoritmo.py).

### Por que Gini e não P95?

O P95 captura apenas o extremo superior da distribuição de distâncias, ignorando a distribuição completa. O Gini, por ser sensível a toda a curva de Lorenz, detecta desigualdades que o P95 não vê — por exemplo, uma solução pode ter P95 baixo mas concentrar boa cobertura em municípios populosos enquanto deixa os menores sistematicamente distantes. O Gini penaliza essa concentração.

### Resultado

| Método | Gini espacial médio | Desvio |
|--------|---------------------|--------|
| AG baseline | 0,3224 | 0,0122 |
| AG single-objective V3 | 0,3341 | 0,0149 |
| NSGA-II compromisso | **0,3154** | 0,0192 |

O **NSGA-II** apresenta o menor Gini médio (0,3154), confirmando que a formulação multiobjetivo — ao otimizar explicitamente cobertura e P95 como objetivos separados — produz soluções mais equitativas do que o AG single-objective. Curiosamente, o AG V3 (gen=500) tem Gini ligeiramente **maior** que o baseline (0,3341 vs 0,3224): ao buscar exclusivamente a menor distância média ponderada por população, o algoritmo tende a concentrar facilidades em regiões densamente povoadas, penalizando municípios menores e mais afastados.

Esse resultado reforça o argumento central do diferencial ético do projeto: otimizar apenas eficiência (distância média) pode gerar soluções mais rápidas e com melhor média, mas às custas de maior desigualdade espacial. O NSGA-II, ao tratar equidade como objetivo explícito, oferece ao tomador de decisão soluções onde o ganho de cobertura e a redução do Gini compensam a pequena perda na distância média.

---

## Formulação matemática

Ver [modelagem.md](modelagem.md) para a descrição formal do problema, variáveis de decisão, função objetivo e restrições.

---

## Fonte dos dados

- IBGE. Censo Demográfico 2022.
- IMB — Instituto Mauro Borges de Estatísticas e Estudos Socioeconômicos.
