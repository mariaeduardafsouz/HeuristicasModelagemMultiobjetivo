import numpy as np
import pandas as pd
import time
from algoritmo import run_ga

SEEDS = [42, 123, 456, 789, 1011]

experimentos = [
    {"nome": "baseline", "pop_size": 100, "n_gen": 300},
    {"nome": "V1_pop200", "pop_size": 200, "n_gen": 300},
    {"nome": "V2_pop50",  "pop_size": 50,  "n_gen": 300},
    {"nome": "V3_gen500", "pop_size": 100, "n_gen": 500},
    {"nome": "V4_pop200_gen500", "pop_size": 200, "n_gen": 500},
]

todos = []

for exp in experimentos:
    print(f"\n{'='*50}")
    print(f"Experimento: {exp['nome']} | pop={exp['pop_size']} | gen={exp['n_gen']}")
    fits = []
    tempos = []

    for seed in SEEDS:
        inicio = time.time()
        _, fit, _, _ = run_ga(seed=seed, pop_size=exp["pop_size"], n_gen=exp["n_gen"], verbose=False)
        tempo = time.time() - inicio
        fits.append(fit)
        tempos.append(tempo)
        print(f"  seed {seed}: fitness={fit:.4f} | tempo={tempo:.1f}s")

    todos.append({
        "config":   exp["nome"],
        "pop_size": exp["pop_size"],
        "n_gen":    exp["n_gen"],
        "media":    round(np.mean(fits), 4),
        "mediana":  round(np.median(fits), 4),
        "desvio":   round(np.std(fits), 4),
        "melhor":   round(min(fits), 4),
        "tempo_medio": round(np.mean(tempos), 1)
    })

df = pd.DataFrame(todos)
df.to_csv("resultados_experimentos.csv", index=False)
print("\n\nTabela comparativa:")
print(df.to_string(index=False))
