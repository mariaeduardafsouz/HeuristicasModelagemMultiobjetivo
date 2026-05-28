import numpy as np
import pandas as pd
import json
from pathlib import Path

_DIR = Path("dataset/processed")

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

def  budget_violation(selected):
    #max(0, Σ c_i · x_i − B)
    custoTotal = sum(CUSTO[selected])
    return max(0, custoTotal - BUDGET)


# --- estimativa empírica de LAMBDA ---
amostras_f = []
amostras_v = []

for _ in range(50):
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


def init_individual(rng):
    x = np.zeros(N, dtype=int)
    indices = rng.choice(N, K, replace = False)
    x[indices] = 1
    return x


def init_population(pop_size, rng):
    pop = []
    for _ in range(pop_size):
        pop.append(init_individual(rng))
    return np.array(pop)


def tournament_select(pop, fits, k, rng):
    candidatos = (rng.choice(len(pop), k, replace=False))
    fits_candidatos = np.array(fits)[candidatos]
    idxLocal = np.argmin(fits_candidatos)
    vencedor = candidatos[idxLocal]
    return pop[vencedor].copy()

def crossover_2pt(p1, p2, rng):

    pts = sorted(rng.choice(N, 2, replace = False))
    a, b = pts[0], pts[1]

    filho1 = np.concatenate([p1[:a], p2[a:b], p1[b:]])
    filho2 = np.concatenate([p2[:a], p1[a:b], p2[b:]])

    filho1 = repair(filho1, rng)
    filho2 = repair(filho2, rng)
    return filho1, filho2

def mutate_flip(x, prob_flip, rng):
    for i in range(N):
        if rng.random() < prob_flip:
            x[i] = 1 - x[i]
    x = repair(x, rng)
    return x
    


def run_ga(seed=42, pop_size=100, n_gen=300, tourn_k=3, prob_cross=0.8, prob_flip=0.02):
    rng = np.random.default_rng(seed)

    pop = init_population(pop_size, rng)

    fits = [fitness(np.where(ind==1)[0])for ind in pop]

    elite = pop[np.argmin(fits)].copy()
    elite_fit = min(fits)

    historico = []

    for gen in range (n_gen):
        nova_pop = []
        while len(nova_pop) < pop_size:
            p1 = tournament_select(pop, fits, tourn_k, rng)
            p2 = tournament_select(pop, fits, tourn_k, rng)

            if rng.random() <  prob_cross:
                f1,f2 = crossover_2pt(p1,p2, rng)
            else:
                f1,f2 = p1.copy(), p2.copy()
            f1 = mutate_flip(f1, prob_flip, rng)
            f2 = mutate_flip(f2, prob_flip, rng)

            nova_pop.extend([f1, f2])
        
        pop = np.array(nova_pop[:pop_size])
        fits = [fitness(np.where(ind==1)[0]) for ind in pop]
    
    #     # Elitismo: substituir pior pelo elite da geração anterior
        pior = np.argmax(fits)
        if elite_fit < fits[pior]:
            pop[pior] = elite
            fits[pior] = elite_fit
    
    #     # Atualizar elite
        melhor = np.argmin(fits)
        if fits[melhor] < elite_fit:
            elite = pop[melhor].copy()
            elite_fit = fits[melhor]

        historico.append(elite_fit)
    #
        print(f"Gen {gen+1}: melhor fitness = {elite_fit:.4f} km")

    # 5. Retornar melhor solução
    selected = np.where(elite==1)[0]

    
    return elite, elite_fit, selected, historico


