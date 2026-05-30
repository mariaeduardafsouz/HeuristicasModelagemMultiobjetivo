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

## Formulação matemática

Ver [modelagem.md](modelagem.md) para a descrição formal do problema, variáveis de decisão, função objetivo e restrições.

---

## Fonte dos dados

- IBGE. Censo Demográfico 2022.
- IMB — Instituto Mauro Borges de Estatísticas e Estudos Socioeconômicos.
