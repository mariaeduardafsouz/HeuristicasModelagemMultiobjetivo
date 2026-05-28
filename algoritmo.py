import numpy as np
import pandas as pd
import json
from pathlib import Path

_DIR = Path("repo/HeuristicasModelagemMultiobjetivo/dataset/processed")

_df    = pd.read_csv(_DIR / "goias_facility_locations.csv")
_cfg   = json.loads((_DIR / "problem_config.json").read_text(encoding="utf-8"))

N         = len(_df)                            # 246
K         = _cfg["default_k"]                  # 12
BUDGET    = _cfg["default_budget_brl"]          # 20_939_128.69
POP       = _df["population_2022"].to_numpy(dtype=float)
CUSTO     = _df["install_cost_brl"].to_numpy(dtype=float)
DIST      = np.load(_DIR / "distance_matrix_km.npy")  # shape (246, 246)
POP_TOTAL = POP.sum()

def avg_dist_weighted(selected):
    #f(x) = (1/P) · Σ_{j∈M} p_j · min_{i: x_i=1} d(i,j)
    somaPonderada = 0
    for j in range(N):
        min_dist = float('inf')
        for i in selected:
            min_dist = min(min_dist, DIST[i][j])
        somaPonderada += POP[j] * min_dist

    return somaPonderada / POP_TOTAL

import numpy as np

# Seleciona as 12 primeiras facilidades arbitrariamente
sel = np.arange(12)
print(avg_dist_weighted(sel))   # deve ser um número em km, algo entre 50–300

def  budget_violation(selected):
    #max(0, Σ c_i · x_i − B)
    custoTotal = sum(CUSTO[selected])
    return max(0, custoTotal - BUDGET)

print(budget_violation(sel))   # deve ser 0.0 se os 12 primeiros municípios cabem no orçamento

# --- estimativa empírica de LAMBDA ---
amostras_f = []
amostras_v = []

for _ in range(500):
    sel_rand = np.random.choice(N, K, replace=False)
    amostras_f.append(avg_dist_weighted(sel_rand))
    v = budget_violation(sel_rand)
    if v > 0:
        amostras_v.append(v)

LAMBDA = float(np.mean(amostras_f) / np.mean(amostras_v))
print(f"λ estimado: {LAMBDA:.6f}")
# -------------------------------------

def fitness(selected):
    #f_pen(x) = f(x) + λ · max(0, Σ c_i·x_i − B)
    #λ ≈ f_típico / v_típico
    return avg_dist_weighted(selected) + LAMBDA * budget_violation(selected)

def repair(x, rng):
    ones = int(x.sum())
    if ones > K:
        indx1 = np.where(x==1)[0]
        remove = rng.choice(indx1, ones - K, replace = False)
        x[remove] = 0

    if ones < K:
        indx0 = np.where(x==0)[0]
        add = rng.choice(indx0, K - ones, replace = False)
        x[add] = 1
    return x

rng = np.random.default_rng(42)
x = np.zeros(N, dtype=int)
x[:15] = 1          # 15 uns — repair deve reduzir para 12
print(repair(x, rng).sum())   # deve imprimir 12


def init_individual(rng):
    x = np.zeros(N, dtype=int)
    indices = rng.choice(N, K, replace = False)
    x[indices] = 1
    return x
    pass


def init_population(pop_size, rng):
    pop = []
    for _ in range(pop_size):
        pop.append(init_individual(rng))
    return np.array(pop)
    pass

# --- testa init_individual ---
ind = init_individual(rng)
print(ind.sum())        # 12
print(len(ind))         # 246

# --- testa init_population ---
pop = init_population(10, rng)
print(pop.shape)        # (10, 246)
print(pop.sum(axis=1))  # todos devem ser 12

def tournament_select(pop, fits, k, rng):
    candidatos = (rng.choice(len(pop), k, replace=False))
    fits_candidatos = np.array(fits)[candidatos]
    idxLocal = np.argmin(fits_candidatos)
    vencedor = candidatos[idxLocal]
    # Sorteia k indivíduos aleatórios da população (sem reposição)
    # candidatos ← rng.choice(len(pop), k, replace=False)
    # vencedor ← candidato com MENOR fits (minimizamos!)
    return pop[vencedor].copy()
    # retornar pop[vencedor]
    pass

fits = [fitness(np.where(ind==1)[0]) for ind in pop]
sel = tournament_select(pop, fits, k=3, rng=rng)
print(sel.shape)   # (246,)
print(sel.sum())   # 12



def crossover_2pt(p1, p2, rng):
    # Sorteia 2 pontos de corte distintos: a, b  (a < b)
    # pts ← sorted(rng.choice(N, 2, replace=False))
    # a, b = pts[0], pts[1]
    #
    # filho1 = [p1[0..a] | p2[a..b] | p1[b..N]]
    # filho2 = [p2[0..a] | p1[a..b] | p2[b..N]]
    #   (use np.concatenate ou cópia + fatiamento)
    #
    # filho1 = repair(filho1, rng)
    # filho2 = repair(filho2, rng)
    # retornar filho1, filho2
    pass


def mutate_flip(x, prob_flip, rng):
    # Para cada posição i em range(N):
    #     se rng.random() < prob_flip:
    #         x[i] = 1 - x[i]    ← inverte o bit
    # x = repair(x, rng)          ← restaura exatamente K uns
    # retornar x
    pass


def run_ga(seed=42, pop_size=100, n_gen=300, tourn_k=3, prob_cross=0.8, prob_flip=0.02):
    rng = np.random.default_rng(seed)

    # 1. Inicializar população
    # pop ← init_population(pop_size, rng)

    # 2. Avaliar fitness inicial
    # fits ← [fitness(np.where(ind==1)[0]) for ind in pop]
    #   (np.where(ind==1)[0] converte vetor binário → índices das facilidades)

    # 3. Elitismo: guardar o melhor indivíduo
    # elite ← pop[np.argmin(fits)].copy()
    # elite_fit ← min(fits)

    # 4. Loop geracional
    # for gen in range(n_gen):
    #     nova_pop ← []
    #
    #     enquanto len(nova_pop) < pop_size:
    #         p1 ← tournament_select(pop, fits, tourn_k, rng)
    #         p2 ← tournament_select(pop, fits, tourn_k, rng)
    #
    #         se rng.random() < prob_cross:
    #             f1, f2 ← crossover_2pt(p1, p2, rng)
    #         senão:
    #             f1, f2 ← p1.copy(), p2.copy()
    #
    #         f1 ← mutate_flip(f1, prob_flip, rng)
    #         f2 ← mutate_flip(f2, prob_flip, rng)
    #
    #         nova_pop.extend([f1, f2])
    #
    #     pop ← np.array(nova_pop[:pop_size])
    #     fits ← [fitness(np.where(ind==1)[0]) for ind in pop]
    #
    #     # Elitismo: substituir pior pelo elite da geração anterior
    #     pior ← np.argmax(fits)
    #     se elite_fit < fits[pior]:
    #         pop[pior] = elite
    #         fits[pior] = elite_fit
    #
    #     # Atualizar elite
    #     melhor ← np.argmin(fits)
    #     se fits[melhor] < elite_fit:
    #         elite = pop[melhor].copy()
    #         elite_fit = fits[melhor]
    #
    #     print(f"Gen {gen+1}: melhor fitness = {elite_fit:.4f} km")

    # 5. Retornar melhor solução
    # selected ← np.where(elite==1)[0]
    # return elite, elite_fit, selected
    pass

