import numpy as np
import pandas as pd
import time
import csv
from algoritmo import run_ga  # troque pelo nome real do .py com o GA

SEEDS = [42, 123, 456, 789, 1011]
resultados = []

for seed in SEEDS:
    print(f"\n{'='*40}")
    print(f"Rodando semente {seed}...")
    inicio = time.time()

    elite, elite_fit, selected, historico = run_ga(seed=seed)

    tempo = time.time() - inicio

    resultados.append({
        "seed":       seed,
        "fitness":    round(elite_fit, 6),
        "n_selected": len(selected),
        "tempo_s":    round(tempo, 2),
        "facilities": list(selected)
    })

    print(f"Seed {seed} | Fitness: {elite_fit:.4f} | Tempo: {tempo:.1f}s")

# Salvar CSV resumido
df = pd.DataFrame([{k: v for k, v in r.items() if k != "facilities"} for r in resultados])
df.to_csv("resultados_seeds.csv", index=False)
print("\n\nResumo final:")
print(df.to_string(index=False))
print(f"\nMédia:    {df['fitness'].mean():.4f}")
print(f"Mediana:  {df['fitness'].median():.4f}")
print(f"Desvio:   {df['fitness'].std():.4f}")

# Salvar facilidades selecionadas por seed (para uso nas figuras)
import json
with open("resultados_detalhados.json", "w") as f:
    json.dump(resultados, f, indent=2, default=lambda x: int(x) if hasattr(x, 'item') else x)