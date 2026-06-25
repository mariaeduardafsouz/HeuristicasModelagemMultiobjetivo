"""
Executa o NSGA-II para todas as seeds e salva o front de Pareto completo
(todos os pontos não-dominados, não apenas a solução de compromisso).

Saída: fronteira_pareto.csv
"""

import time

import numpy as np
import pandas as pd

from algoritmo import choose_compromise_index, run_nsga2, solution_metrics

SEEDS = [42, 123, 456, 789, 1011]
POP_SIZE = 100
N_GEN = 300

rows = []

for seed in SEEDS:
    print(f"Rodando NSGA-II  seed={seed}  pop={POP_SIZE}  gen={N_GEN} ...")
    t0 = time.time()
    result = run_nsga2(seed=seed, pop_size=POP_SIZE, n_gen=N_GEN, verbose=False)
    tempo_s = time.time() - t0

    front_pop = result["front_population"]
    front_obj = result["front_objectives"]
    compromise_idx = choose_compromise_index(front_obj)

    for i, (ind, obj) in enumerate(zip(front_pop, front_obj)):
        selected = np.where(ind == 1)[0]
        metrics = solution_metrics(selected)
        rows.append(
            {
                "seed": seed,
                "point_idx": i,
                "is_compromise": int(i == compromise_idx),
                "f1_avg_distance_km": round(obj[0], 6),
                "f2_uncovered_80km_pct": round(obj[1], 6),
                "f3_p95_distance_km": round(obj[2], 6),
                "coverage_80km_pct": round(metrics["coverage_80km_pct"], 6),
                "total_cost_brl": round(metrics["total_cost_brl"], 2),
                "budget_slack_brl": round(metrics["budget_slack_brl"], 2),
                "tempo_s": round(tempo_s, 2),
                "facilities": ";".join(str(int(f)) for f in selected),
            }
        )

    print(
        f"  -> {len(front_pop)} soluções na frente de Pareto | tempo={tempo_s:.1f}s"
    )

df = pd.DataFrame(rows)
df.to_csv("fronteira_pareto.csv", index=False)
print(f"\nArquivo gerado: fronteira_pareto.csv  ({len(df)} linhas)")
