import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from algoritmo import run_ga

# ── dados já coletados ──────────────────────────────────────────
df_exp = pd.read_csv("resultados_experimentos.csv")
SEEDS  = [42, 123, 456, 789, 1011]

# ── coletar fitness por seed para boxplot ───────────────────────
fits_por_config = {}
for _, row in df_exp.iterrows():
    fits = []
    for seed in SEEDS:
        _, fit, _, _ = run_ga(seed=seed,
                               pop_size=int(row["pop_size"]),
                               n_gen=int(row["n_gen"]))
        fits.append(fit)
    fits_por_config[row["config"]] = fits
    print(f"{row['config']} coletado")

# ── coletar histórico de convergência (baseline, V3) ────────────
historicos = {}
for config, pop_size, n_gen in [("baseline", 100, 300), ("V3_gen500", 100, 500)]:
    hist_seeds = []
    for seed in SEEDS:
        _, _, _, hist = run_ga(seed=seed, pop_size=pop_size, n_gen=n_gen)
        hist_seeds.append(hist)
    historicos[config] = np.mean(hist_seeds, axis=0)
    print(f"Histórico {config} coletado")

# ════════════════════════════════════════════════════════════════
# FIGURA 1 — Boxplot
# ════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(10, 5))
ax.boxplot(fits_por_config.values(), labels=fits_por_config.keys(), patch_artist=True)
ax.set_title("Distribuição do Fitness por Configuração")
ax.set_xlabel("Configuração")
ax.set_ylabel("Fitness (km)")
ax.tick_params(axis='x', rotation=15)
plt.tight_layout()
plt.savefig("fig1_boxplot.png", dpi=150)
plt.close()
print("Fig 1 salva")

# ════════════════════════════════════════════════════════════════
# FIGURA 2 — Convergência
# ════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(10, 5))
for config, hist in historicos.items():
    ax.plot(hist, label=config)
ax.set_title("Convergência do Algoritmo Genético")
ax.set_xlabel("Geração")
ax.set_ylabel("Fitness (km)")
ax.legend()
plt.tight_layout()
plt.savefig("fig2_convergencia.png", dpi=150)
plt.close()
print("Fig 2 salva")

# ════════════════════════════════════════════════════════════════
# FIGURA 3 — Barras média por configuração
# ════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(df_exp["config"], df_exp["media"], 
       yerr=df_exp["desvio"], capsize=5, color="steelblue")
ax.set_ylim(37, 42)
ax.set_title("Média do Fitness por Configuração")
ax.set_xlabel("Configuração")
ax.set_ylabel("Fitness médio (km)")
ax.tick_params(axis='x', rotation=15)
plt.tight_layout()
plt.savefig("fig3_barras.png", dpi=150)
plt.close()
print("Fig 3 salva")

# ════════════════════════════════════════════════════════════════
# FIGURA 4 — Mapa das facilidades (melhor solução = V3, seed 789)
# ════════════════════════════════════════════════════════════════
import pandas as pd, json
from pathlib import Path

_DIR = Path("dataset/processed")
_df  = pd.read_csv(_DIR / "goias_facility_locations.csv")

_, _, selected, _ = run_ga(seed=789, pop_size=100, n_gen=500)

fig, ax = plt.subplots(figsize=(8, 8))
ax.scatter(_df["longitude"], _df["latitude"],
           c="lightgray", s=20, label="Municípios")
ax.scatter(_df.iloc[selected]["longitude"],
           _df.iloc[selected]["latitude"],
           c="red", s=80, zorder=5, label="Facilidades selecionadas")
ax.set_title("Localização das Facilidades — Melhor Solução (V3, seed 789)")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.legend()
plt.tight_layout()
plt.savefig("fig4_mapa.png", dpi=150)
plt.close()
print("Fig 4 salva")

print("\nTodas as figuras geradas!")