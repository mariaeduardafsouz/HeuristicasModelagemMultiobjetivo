import pandas as pd
import numpy as np

df = pd.read_csv("resultados_experimentos.csv")

# Pegar só baseline e melhor config (V3)
tabela = df[df["config"].isin(["baseline", "V3_gen500"])][
    ["config", "media", "mediana", "desvio", "melhor", "tempo_medio"]
].copy()

tabela.columns = ["Configuração", "Média", "Mediana", "Desvio Padrão", "Melhor", "Tempo Médio (s)"]

print("\n=== NÚMEROS DO AG PARA PESSOA 4 ===\n")
print(tabela.to_string(index=False))
print("\nObservações:")
print(f"- Sementes usadas: 42, 123, 456, 789, 1011")
print(f"- Métrica: distância média ponderada pela população (km)")
print(f"- Melhor configuração encontrada: V3_gen500 (pop=100, gerações=500)")
print(f"- Melhoria V3 sobre baseline AG: {((df[df['config']=='baseline']['media'].values[0] - df[df['config']=='V3_gen500']['media'].values[0]) / df[df['config']=='baseline']['media'].values[0] * 100):.2f}%")

tabela.to_csv("numeros_p4.csv", index=False)
print("\nSalvo em numeros_p4.csv")