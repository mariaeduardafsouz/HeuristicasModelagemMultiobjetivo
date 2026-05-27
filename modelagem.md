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

No decorrer do trabalho planeja-se também maximizar a cobertura populacional dentro de um raio máximo de atendimento R, e também minimizar a desigualdade espacial no acesso, procurando evitar que apenas regiões centrais ou mais populosas sejam atendidas em detrimento de regiões mais afastadas.



## 4. Restrições

- **(C1)**: exatamente k unidades devem ser instaladas

- **(C2)**: o custo total de instalação não deve exceder o orçamento estabelecido

- **(C3)**: cada município recebe ou não recebe uma facilidade


## 5. Penalização


## 6. Correspondência com o código

| Símbolo matemático        | Função/variável no código         |
|---------------------------|-----------------------------------|
| M, n                      | `df`, `N = len(df)`                                      |
| p_i                       | `df["population_2022"]`                                  |
| c_i                       | `df["install_cost_brl"]`                                 |
| d(i, j)                   | `distance_matrix[i, j]` (de `distance_matrix_km.npy`)   |
| k, B                      | `config["default_k"]`, `config["default_budget_brl"]`   |
| x_i                       | *(a implementar)*                                        |
| f(x)                      | *(a implementar)*                                        |
|     | *(a implementar)*                                        |
| C1:             | *(a implementar)*                                        |
| C2:         | *(a implementar)*                                        |
| f_pen(x)                  | *(a implementar)*                                        |
| ` `                   | *(a implementar)*                                        |