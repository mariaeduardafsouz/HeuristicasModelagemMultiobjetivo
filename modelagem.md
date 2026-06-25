## 1. Conjunto e parâmetros

Seja `M = {1,2,...,n}` um conjunto de municípios, no nosso contexto, localizados no estado de Goiás, com `n = 246`

Temos para cada ``i ∈ M``:
- ``p_i``: população residente (Censo 2022)
- `(lat_i, lon_i)`: coordenadas geográficas do centroide do polígono municipal (SIRGAS 2000)
- ``c_i``:  custo sintético de instalação em BRL, definido por:

  ``c_i = [0,80 + 1,60·φ(log(1+pop_i)) + 0,50·φ(log(1+area_i)) + 0,30·φ(log(1+pib_i))] × 10⁶``

  onde φ(·) é a normalização min-max aplicada sobre todos os municípios

-  ``d_ij``: distância Haversine em km entre os centroides dos municípios ***i*** e ***j***

Parâmetros globais:

 - ``k = 12``: número de facilidades a instalar
 - ``B = 20.939.128,69``: orçamento total
 - ``P = 7.056.495``: população total 
 - ``R = 80 km ``: (raio máximo de cobertura)

## 2. Variáveis de decisão


A variável de decisão principal é ``x_i``, que representa se uma unidade foi instalada ou não no município ``i``

``x_i ∈ {0, 1},  ∀ i ∈ M``


## 3. Função objetivo (single-objective)

A função objetivo é aplicada para **minimizar a distância média ponderada da população até a facilidade mais próxima**, de modo que populações maiores possuem maior peso

`f(x) = (1/P) · Σ_{j ∈ M}  p_j · min_{i: x_i=1} d(i, j)`

Interpretação: média em km que um habitante aleatório precisa
percorrer até a facilidade mais próxima, ponderada pela população `p_j`
de cada município.

A extensão multiobjetivo implementada com NSGA-II também maximiza a cobertura populacional dentro de um raio máximo de atendimento R e minimiza a desigualdade espacial no acesso, procurando evitar que apenas regiões centrais ou mais populosas sejam atendidas em detrimento de regiões mais afastadas.



## 4. Restrições

- **(C1)**: exatamente k unidades devem ser instaladas

- **(C2)**: o custo total de instalação não deve exceder o orçamento estabelecido

## 5. Penalização

Como a restrição C2 (orçamento) é tratada por penalização em vez de
ser imposta diretamente, a função objetivo é estendida para:

`f_pen(x) = f(x) + λ · max(0, Σ_{i∈M} c_i · x_i − B)`

onde o termo `max(0, ...)` representa a violação do orçamento em BRL
e λ é o coeficiente de penalidade que converte essa violação em km,
tornando-a comparável ao valor de f(x).

O valor de λ foi estimado empiricamente pela razão:

`λ ≈ f_típico / v_típico`

onde f_típico é a média de f(x) em soluções aleatórias e v_típico é
a violação média de C2 nas soluções que excedem o orçamento.
Essa calibração garante que uma violação típica adicione uma penalidade
da mesma ordem de grandeza que o próprio objetivo.

Embora C2 seja uma restrição inegociável na prática, optou-se pela
abordagem de penalização por ser mais simples de implementar em AGs
do que um operador de reparo para o orçamento. A penalidade λ é
calibrada para tornar violações de orçamento desvantajosas o suficiente
para que o AG evite soluções infeasíveis.




## 6. Correspondência com o código

| Símbolo matemático        | Função/variável no código         |
|---------------------------|-----------------------------------|
| M, n                      | `df`, `N = len(df)`               |
| p_i                       | `df["population_2022"]`           |
| c_i                       | `df["install_cost_brl"]`          |
| d(i, j)                   | `distance_matrix[i, j]` (de `distance_matrix_km.npy`)   |
| k, B                      | `config["default_k"]`, `config["default_budget_brl"]`   |
| x_i                       | `vetor binário x de tamanho N (1 = facilidade instalada)`|
| f(x)                      | ``avg_dist_weighted(selected)``    |
| C1:                       | ``repair(x, rng)`` garante exatamente K uns|
| C2:                       | ``budget_violation(selected)   ``  |
| f_pen(x)                  | ``fitness(selected)*        ``|
| λ                         | ``LAMBDA`` estimado empiricamente|

## 7. Formulação multiobjetivo implementada

Para o NSGA-II, a solução `x` é avaliada por um vetor de três objetivos. Como o algoritmo trabalha com minimização, a cobertura é representada pela parcela da população não coberta.

Defina:

`δ_j(x) = min_{i: x_i=1} d(i,j)`

ou seja, a distância do município `j` até a facilidade selecionada mais próxima.

O vetor multiobjetivo é:

`min F(x) = (f_1(x), f_2(x), f_3(x))`

com:

`f_1(x) = (1/P) · Σ_{j∈M} p_j · δ_j(x)`

distância média ponderada pela população.

`f_2(x) = 100 · (1 - (1/P) · Σ_{j∈M} p_j · I[δ_j(x) ≤ R])`

percentual da população descoberta em até `R = 80 km`. Minimizar `f_2` equivale a maximizar a cobertura populacional.

`f_3(x) = Q^p_{0,95}({δ_j(x) | j∈M})`

percentil 95 ponderado pela população das distâncias até a facilidade mais próxima. Esse termo mede a cauda da distribuição de acesso: valores menores indicam que os municípios/populações mais distantes não estão tão penalizados.

As restrições permanecem:

- **(C1)** exatamente `k = 12` unidades instaladas;
- **(C2)** custo total de instalação menor ou igual ao orçamento `B`.

No AG single-objective, C2 é incorporada por penalização em `fitness(selected)`. No NSGA-II, C2 é tratada por **dominância restrita**:

- uma solução viável domina uma solução inviável;
- entre duas soluções inviáveis, domina a que tiver menor violação orçamentária;
- entre duas soluções viáveis, aplica-se a dominância de Pareto usual sobre `(f_1, f_2, f_3)`.

## 8. Correspondência da extensão NSGA-II com o código

| Conceito | Função/arquivo |
|----------|----------------|
| `δ_j(x)` | `nearest_distances(selected)` em `algoritmo.py` |
| `f_1(x)` | `avg_distance_km` em `solution_metrics(selected)` |
| `f_2(x)` | `uncovered_80km_pct` em `solution_metrics(selected)` |
| `f_3(x)` | `p95_distance_km` em `solution_metrics(selected)` |
| Vetor multiobjetivo | `multiobjective_values(selected)` |
| Dominância restrita | `constrained_dominates(...)` |
| Ordenação não-dominada | `fast_non_dominated_sort(...)` |
| NSGA-II | `run_nsga2(...)` |
| Solução de compromisso | `choose_compromise_index(...)` |
| Comparação experimental | `run_comparacao_multiobjetivo.py` |
