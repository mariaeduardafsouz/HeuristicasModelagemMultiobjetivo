import json
from pathlib import Path

import numpy as np
import pandas as pd


_DIR = Path("dataset/processed")

_df = pd.read_csv(_DIR / "goias_facility_locations.csv")
_cfg = json.loads((_DIR / "problem_config.json").read_text(encoding="utf-8"))

N = len(_df)
K = int(_cfg["default_k"])
BUDGET = float(_cfg["default_budget_brl"])
RADIUS_KM = float(_cfg.get("default_radius_km", 80.0))
POP = _df["population_2022"].to_numpy(dtype=float)
CUSTO = _df["install_cost_brl"].to_numpy(dtype=float)
DIST = np.load(_DIR / "distance_matrix_km.npy")
POP_TOTAL = float(POP.sum())
EPS = 1e-9


def avg_dist_weighted(selected):
    # f(x) = (1/P) * sum_j p_j * min_{i selecionado} d(i,j)
    selected = np.asarray(selected, dtype=int)
    if selected.size == 0:
        return float("inf")
    nearest = DIST[selected, :].min(axis=0)
    return float(np.dot(POP, nearest) / POP_TOTAL)


def budget_violation(selected):
    # max(0, sum_i c_i*x_i - B)
    selected = np.asarray(selected, dtype=int)
    custo_total = float(CUSTO[selected].sum())
    return max(0.0, custo_total - BUDGET)


def estimate_lambda(n_samples=200, seed=2026):
    """Estimate a deterministic penalty coefficient for the single-objective GA."""
    rng = np.random.default_rng(seed)
    amostras_f = []
    amostras_v = []

    for _ in range(n_samples):
        sel_rand = rng.choice(N, K, replace=False)
        amostras_f.append(avg_dist_weighted(sel_rand))
        v = budget_violation(sel_rand)
        if v > 0:
            amostras_v.append(v)

    if not amostras_v:
        return 0.0
    return float(np.mean(amostras_f) / np.mean(amostras_v))


LAMBDA = estimate_lambda()


def fitness(selected):
    # f_pen(x) = f(x) + lambda * violacao_orcamentaria
    return avg_dist_weighted(selected) + LAMBDA * budget_violation(selected)


def gini_espacial(selected):
    d = nearest_distances(selected)
    d_sorted = np.sort(d)
    if d_sorted.mean() == 0:
        return 0.0
    indices = np.arange(1, N + 1)
    return float((2 * (indices * d_sorted).sum()) / (N * d_sorted.sum()) - (N + 1) / N)


def nearest_distances(selected):
    selected = np.asarray(selected, dtype=int)
    if selected.size == 0:
        return np.full(N, float("inf"))
    return DIST[selected, :].min(axis=0)


def weighted_quantile(values, weights, quantile):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    order = np.argsort(values)
    sorted_values = values[order]
    sorted_weights = weights[order]
    cum_weights = np.cumsum(sorted_weights)
    cutoff = quantile * sorted_weights.sum()
    return float(sorted_values[np.searchsorted(cum_weights, cutoff, side="left")])


def solution_metrics(selected, radius_km=RADIUS_KM):
    selected = np.asarray(selected, dtype=int)
    nearest = nearest_distances(selected)
    total_cost = float(CUSTO[selected].sum())
    covered_pop = float(POP[nearest <= radius_km].sum())
    coverage_ratio = covered_pop / POP_TOTAL

    return {
        "avg_distance_km": float(np.dot(POP, nearest) / POP_TOTAL),
        "coverage_80km_pct": float(100.0 * coverage_ratio),
        "uncovered_80km_pct": float(100.0 * (1.0 - coverage_ratio)),
        "p95_distance_km": weighted_quantile(nearest, POP, 0.95),
        "max_distance_km": float(nearest.max()),
        "total_cost_brl": total_cost,
        "budget_violation_brl": max(0.0, total_cost - BUDGET),
        "budget_slack_brl": BUDGET - total_cost,
    }


def multiobjective_values(selected):
    metrics = solution_metrics(selected)
    return np.array(
        [
            metrics["avg_distance_km"],
            metrics["uncovered_80km_pct"],
            metrics["p95_distance_km"],
        ],
        dtype=float,
    )


def evaluate_population(pop):
    objectives = np.zeros((len(pop), 3), dtype=float)
    violations = np.zeros(len(pop), dtype=float)
    for idx, ind in enumerate(pop):
        selected = np.where(ind == 1)[0]
        objectives[idx] = multiobjective_values(selected)
        violations[idx] = budget_violation(selected)
    return objectives, violations


def repair(x, rng):
    ones = int(x.sum())
    if ones > K:
        indx1 = np.where(x == 1)[0]
        remove = rng.choice(indx1, ones - K, replace=False)
        x[remove] = 0

    if ones < K:
        indx0 = np.where(x == 0)[0]
        add = rng.choice(indx0, K - ones, replace=False)
        x[add] = 1
    return x


def init_individual(rng):
    x = np.zeros(N, dtype=int)
    indices = rng.choice(N, K, replace=False)
    x[indices] = 1
    return x


def init_population(pop_size, rng):
    pop = []
    for _ in range(pop_size):
        pop.append(init_individual(rng))
    return np.array(pop)


def tournament_select(pop, fits, k, rng):
    candidatos = rng.choice(len(pop), k, replace=False)
    fits_candidatos = np.array(fits)[candidatos]
    idx_local = np.argmin(fits_candidatos)
    vencedor = candidatos[idx_local]
    return pop[vencedor].copy()


def crossover_2pt(p1, p2, rng):
    pts = sorted(rng.choice(N, 2, replace=False))
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
    return repair(x, rng)


def run_ga(seed=42, pop_size=100, n_gen=300, tourn_k=3, prob_cross=0.8, prob_flip=0.02, verbose=True):
    rng = np.random.default_rng(seed)

    pop = init_population(pop_size, rng)
    fits = [fitness(np.where(ind == 1)[0]) for ind in pop]

    elite = pop[np.argmin(fits)].copy()
    elite_fit = min(fits)
    historico = []

    for gen in range(n_gen):
        nova_pop = []
        while len(nova_pop) < pop_size:
            p1 = tournament_select(pop, fits, tourn_k, rng)
            p2 = tournament_select(pop, fits, tourn_k, rng)

            if rng.random() < prob_cross:
                f1, f2 = crossover_2pt(p1, p2, rng)
            else:
                f1, f2 = p1.copy(), p2.copy()

            f1 = mutate_flip(f1, prob_flip, rng)
            f2 = mutate_flip(f2, prob_flip, rng)
            nova_pop.extend([f1, f2])

        pop = np.array(nova_pop[:pop_size])
        fits = [fitness(np.where(ind == 1)[0]) for ind in pop]

        pior = np.argmax(fits)
        if elite_fit < fits[pior]:
            pop[pior] = elite
            fits[pior] = elite_fit

        melhor = np.argmin(fits)
        if fits[melhor] < elite_fit:
            elite = pop[melhor].copy()
            elite_fit = fits[melhor]

        historico.append(elite_fit)
        if verbose:
            print(f"Gen {gen + 1}: melhor fitness = {elite_fit:.4f} km")

    selected = np.where(elite == 1)[0]
    return elite, elite_fit, selected, historico


def constrained_dominates(idx_a, idx_b, objectives, violations):
    va = violations[idx_a]
    vb = violations[idx_b]

    if va <= EPS and vb > EPS:
        return True
    if va > EPS and vb <= EPS:
        return False
    if va > EPS and vb > EPS:
        return va < vb - EPS

    a = objectives[idx_a]
    b = objectives[idx_b]
    return bool(np.all(a <= b + EPS) and np.any(a < b - EPS))


def fast_non_dominated_sort(objectives, violations):
    n = len(objectives)
    if n == 0:
        return []

    feasible = violations <= EPS
    both_feasible = feasible[:, None] & feasible[None, :]
    both_infeasible = (~feasible[:, None]) & (~feasible[None, :])

    feasible_dominates_infeasible = feasible[:, None] & (~feasible[None, :])
    infeasible_dominance = both_infeasible & (violations[:, None] < violations[None, :] - EPS)

    less_equal = np.all(objectives[:, None, :] <= objectives[None, :, :] + EPS, axis=2)
    strictly_less = np.any(objectives[:, None, :] < objectives[None, :, :] - EPS, axis=2)
    feasible_objective_dominance = both_feasible & less_equal & strictly_less

    dominance = feasible_dominates_infeasible | infeasible_dominance | feasible_objective_dominance
    np.fill_diagonal(dominance, False)

    dominated_count = dominance.sum(axis=0).astype(int)
    assigned = np.zeros(n, dtype=bool)
    fronts = []
    current_front = np.where(dominated_count == 0)[0]

    while current_front.size:
        fronts.append(current_front.tolist())
        assigned[current_front] = True
        dominated_count -= dominance[current_front].sum(axis=0).astype(int)
        current_front = np.where((dominated_count == 0) & (~assigned))[0]

    return fronts


def crowding_distance(front, objectives):
    front = list(front)
    distances = np.zeros(len(front), dtype=float)
    if len(front) == 0:
        return distances
    if len(front) <= 2:
        distances[:] = np.inf
        return distances

    front_objectives = objectives[front]
    for obj_idx in range(front_objectives.shape[1]):
        order = np.argsort(front_objectives[:, obj_idx])
        distances[order[0]] = np.inf
        distances[order[-1]] = np.inf

        min_value = front_objectives[order[0], obj_idx]
        max_value = front_objectives[order[-1], obj_idx]
        span = max_value - min_value
        if span <= EPS:
            continue

        for pos in range(1, len(front) - 1):
            if np.isinf(distances[order[pos]]):
                continue
            prev_value = front_objectives[order[pos - 1], obj_idx]
            next_value = front_objectives[order[pos + 1], obj_idx]
            distances[order[pos]] += (next_value - prev_value) / span

    return distances


def rank_and_crowding(objectives, violations):
    fronts = fast_non_dominated_sort(objectives, violations)
    rank = np.zeros(len(objectives), dtype=int)
    crowding = np.zeros(len(objectives), dtype=float)

    for front_rank, front in enumerate(fronts):
        distances = crowding_distance(front, objectives)
        for local_idx, pop_idx in enumerate(front):
            rank[pop_idx] = front_rank
            crowding[pop_idx] = distances[local_idx]

    return fronts, rank, crowding


def nsga2_tournament_select(pop, rank, crowding, tourn_k, rng):
    candidatos = rng.choice(len(pop), tourn_k, replace=False)
    best = candidatos[0]
    for candidate in candidatos[1:]:
        if rank[candidate] < rank[best]:
            best = candidate
        elif rank[candidate] == rank[best] and crowding[candidate] > crowding[best]:
            best = candidate
    return pop[best].copy()


def _nsga2_history_record(gen, objectives, violations):
    fronts, _, _ = rank_and_crowding(objectives, violations)
    feasible = np.where(violations <= EPS)[0]
    front0 = np.array(fronts[0], dtype=int) if fronts else np.array([], dtype=int)
    feasible_front0 = np.array([idx for idx in front0 if violations[idx] <= EPS], dtype=int)

    if feasible_front0.size:
        pool = feasible_front0
    elif feasible.size:
        pool = feasible
    else:
        pool = front0

    return {
        "generation": gen,
        "feasible_count": int(feasible.size),
        "front0_count": int(front0.size),
        "feasible_front0_count": int(feasible_front0.size),
        "min_avg_distance_km": float(np.min(objectives[pool, 0])),
        "max_coverage_80km_pct": float(100.0 - np.min(objectives[pool, 1])),
        "min_p95_distance_km": float(np.min(objectives[pool, 2])),
        "min_budget_violation_brl": float(np.min(violations)),
    }


def run_nsga2(seed=42, pop_size=100, n_gen=300, tourn_k=2, prob_cross=0.8, prob_flip=0.02, verbose=False):
    rng = np.random.default_rng(seed)
    pop = init_population(pop_size, rng)
    objectives, violations = evaluate_population(pop)
    history = []

    for gen in range(n_gen):
        _, rank, crowding = rank_and_crowding(objectives, violations)
        offspring = []
        while len(offspring) < pop_size:
            p1 = nsga2_tournament_select(pop, rank, crowding, tourn_k, rng)
            p2 = nsga2_tournament_select(pop, rank, crowding, tourn_k, rng)

            if rng.random() < prob_cross:
                f1, f2 = crossover_2pt(p1, p2, rng)
            else:
                f1, f2 = p1.copy(), p2.copy()

            offspring.append(mutate_flip(f1, prob_flip, rng))
            if len(offspring) < pop_size:
                offspring.append(mutate_flip(f2, prob_flip, rng))

        offspring = np.array(offspring[:pop_size])
        combined = np.vstack([pop, offspring])
        combined_objectives, combined_violations = evaluate_population(combined)
        combined_fronts, _, combined_crowding = rank_and_crowding(combined_objectives, combined_violations)

        selected_indices = []
        for front in combined_fronts:
            remaining = pop_size - len(selected_indices)
            if remaining <= 0:
                break
            if len(front) <= remaining:
                selected_indices.extend(front)
            else:
                ordered_front = sorted(front, key=lambda idx: combined_crowding[idx], reverse=True)
                selected_indices.extend(ordered_front[:remaining])
                break

        selected_indices = np.array(selected_indices, dtype=int)
        pop = combined[selected_indices]
        objectives = combined_objectives[selected_indices]
        violations = combined_violations[selected_indices]

        record = _nsga2_history_record(gen + 1, objectives, violations)
        history.append(record)
        if verbose:
            print(
                f"Gen {gen + 1}: front0={record['front0_count']} "
                f"viaveis={record['feasible_count']} "
                f"min_dist={record['min_avg_distance_km']:.4f} km "
                f"max_cov={record['max_coverage_80km_pct']:.2f}%"
            )

    fronts, rank, crowding = rank_and_crowding(objectives, violations)
    first_front = np.array(fronts[0], dtype=int)
    feasible_first_front = np.array([idx for idx in first_front if violations[idx] <= EPS], dtype=int)

    if feasible_first_front.size == 0:
        feasible = np.where(violations <= EPS)[0]
        feasible_first_front = feasible if feasible.size else first_front

    return {
        "population": pop,
        "objectives": objectives,
        "violations": violations,
        "front_indices": feasible_first_front,
        "front_population": pop[feasible_first_front],
        "front_objectives": objectives[feasible_first_front],
        "front_violations": violations[feasible_first_front],
        "rank": rank,
        "crowding": crowding,
        "history": history,
    }


def choose_compromise_index(objectives):
    objectives = np.asarray(objectives, dtype=float)
    mins = objectives.min(axis=0)
    maxs = objectives.max(axis=0)
    spans = np.where(maxs - mins <= EPS, 1.0, maxs - mins)
    normalized = (objectives - mins) / spans
    scores = np.linalg.norm(normalized, axis=1)
    return int(np.argmin(scores))
