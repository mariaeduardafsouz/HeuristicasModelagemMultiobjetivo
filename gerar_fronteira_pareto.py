"""
Gera os graficos da fronteira de Pareto a partir de fronteira_pareto.csv.

Pre-requisito: python run_pareto.py

Figuras geradas:
  fig8_fronteira_pareto.png  -- projecao principal  f1 x cobertura,  cor = f3
  fig9_pareto_pairwise.png   -- tres projecoes 2-a-2 dos objetivos

Notas metodologicas:
  - As solucoes no CSV sao nao-dominadas em 3D (f1, f2, f3) dentro de cada seed.
    Isso nao garante que uma solucao de uma seed nao seja dominada por solucao
    de outra seed na projecao 2D. O envelope global combina todas as seeds.
  - As linhas tracejadas por seed conectam todos os pontos 3D-nao-dominados
    ordenados por f1; alguns podem ser dominados na projecao 2D.
  - f2_uncovered_80km_pct + coverage_80km_pct = 100 (redundancia intencional
    para rastreabilidade: f2 e o objetivo minimizado pelo NSGA-II, coverage
    e a forma legivel para humanos).
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATA_PATH = Path("fronteira_pareto.csv")

SEED_COLORS = {
    42:   "#1b9e77",
    123:  "#d95f02",
    456:  "#7570b3",
    789:  "#e7298a",
    1011: "#66a61e",
}


def _load():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"{DATA_PATH} nao encontrado. Execute: python run_pareto.py"
        )
    return pd.read_csv(DATA_PATH)


def _nondominated_2d(x_vals, y_vals, x_dir="min", y_dir="min"):
    """
    Retorna (x_nd, y_nd) dos pontos nao-dominados na projecao 2D,
    SEMPRE com x_nd em ordem crescente no dominio original.

    x_dir / y_dir: "min" (menor e melhor) ou "max" (maior e melhor).

    Algoritmo:
      1. Transforma ambos os eixos para minimizacao (nega os "max").
      2. Ordena por x_transformado crescente (melhor x primeiro).
      3. Varre mantendo o minimo acumulado de y_transformado:
         um ponto e nao-dominado se seu y_transformado e menor que
         todos os y_transformados vistos anteriormente (com x menor).
      4. Retorna valores originais ordenados por x CRESCENTE no dominio
         original, independente da direcao — necessario para _build_step
         desenhar o degrau da esquerda para a direita.

    Atencao: para x_dir="max" a ordenacao interna e decrescente (melhor
    x = maior), mas ao retornar invertemos para crescente no dominio
    original. Sem essa inversao o _build_step desenharia o degrau de
    tras para frente (bug corrigido nesta versao).
    """
    x = np.asarray(x_vals, dtype=float)
    y = np.asarray(y_vals, dtype=float)

    xs = x if x_dir == "min" else -x
    ys = y if y_dir == "min" else -y

    order = np.argsort(xs)
    x_s = x[order]
    y_s = y[order]
    ys_s = ys[order]

    keep = []
    min_ys = np.inf
    for i in range(len(x_s)):
        if ys_s[i] < min_ys:
            min_ys = ys_s[i]
            keep.append(i)

    x_nd = x_s[keep]
    y_nd = y_s[keep]

    sort_asc = np.argsort(x_nd)
    return x_nd[sort_asc], y_nd[sort_asc]


def _build_step(x_front, y_front, x_left, x_right):
    """
    Constroi arrays (x, y) para a fronteira de Pareto em degraus.

    Para cada par consecutivo de pontos nao-dominados:
      - segmento horizontal mantendo y anterior ate o proximo x
      - salto vertical para o proximo y

    Exige x_front em ordem CRESCENTE (garantido por _nondominated_2d).
    Estende a linha horizontalmente ate x_left e x_right.

    O formato em degraus e a representacao correta da fronteira 2D:
    "para qualquer x no intervalo [x_i, x_{i+1}), o melhor y alcancavel
    e y_i sem piorar x".
    """
    xs = [x_left, x_front[0]]
    ys = [y_front[0], y_front[0]]

    for i in range(1, len(x_front)):
        xs.append(x_front[i])
        ys.append(y_front[i - 1])
        xs.append(x_front[i])
        ys.append(y_front[i])

    xs.append(x_right)
    ys.append(y_front[-1])

    return np.array(xs), np.array(ys)


def plot_main_front(df: pd.DataFrame):
    """
    Eixo X : f1 — distancia media ponderada (km)    [minimizar]
    Eixo Y : cobertura dentro de 80 km (%)          [maximizar]
    Cor    : f3 — percentil 95 ponderado (km)       [minimizar]

    Linha preta em degraus: envelope de Pareto 2D global (todas as seeds).
      Interpreta-se como: "e impossivel estar simultaneamente a esquerda
      E acima desta linha com as configuracoes testadas".

    Linhas tracejadas por seed: conectam todos os pontos 3D-nao-dominados
      de cada seed, ordenados por f1. SAO GUIAS VISUAIS, nao fronteiras
      2D formais — alguns pontos conectados podem ser dominados na
      projecao 2D.

    Estrelas: solucao de compromisso por seed (minima norma L2 apos
      normalizacao dos 3 objetivos dentro do proprio front da seed).
    """
    fig, ax = plt.subplots(figsize=(10, 6.5))

    f3_min = df["f3_p95_distance_km"].min()
    f3_max = df["f3_p95_distance_km"].max()
    cmap = plt.get_cmap("plasma_r")
    norm = plt.Normalize(vmin=f3_min, vmax=f3_max)

    x_left  = df["f1_avg_distance_km"].min() - 1.0
    x_right = df["f1_avg_distance_km"].max() + 1.0

    for seed, grp in df.groupby("seed"):
        grp_s = grp.sort_values("f1_avg_distance_km")
        ax.plot(
            grp_s["f1_avg_distance_km"],
            grp_s["coverage_80km_pct"],
            color=SEED_COLORS[seed],
            linewidth=0.9,
            alpha=0.30,
            linestyle="--",
            zorder=1,
        )

    x_nd, y_nd = _nondominated_2d(
        df["f1_avg_distance_km"].values,
        df["coverage_80km_pct"].values,
        x_dir="min",
        y_dir="max",
    )
    xs_step, ys_step = _build_step(x_nd, y_nd, x_left, x_right)
    ax.plot(
        xs_step, ys_step,
        color="#111111",
        linewidth=2.0,
        alpha=0.88,
        zorder=2,
        label="Envelope Pareto 2D (limite global)",
        solid_capstyle="round",
    )

    for seed, grp in df.groupby("seed"):
        regular    = grp[grp["is_compromise"] == 0]
        compromise = grp[grp["is_compromise"] == 1]
        edge = SEED_COLORS[seed]

        ax.scatter(
            regular["f1_avg_distance_km"],
            regular["coverage_80km_pct"],
            c=regular["f3_p95_distance_km"],
            cmap=cmap, norm=norm,
            s=55, linewidths=0.8, edgecolors=edge, alpha=0.85,
            label=f"seed {int(seed)}", zorder=3,
        )

        if not compromise.empty:
            ax.scatter(
                compromise["f1_avg_distance_km"],
                compromise["coverage_80km_pct"],
                c=compromise["f3_p95_distance_km"],
                cmap=cmap, norm=norm,
                s=210, marker="*", linewidths=1.2,
                edgecolors="#111111", alpha=1.0, zorder=5,
            )

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, pad=0.02)
    cbar.set_label("f3 — P95 distancia ponderada (km)", fontsize=10)

    ax.set_xlabel("f1 — Distancia media ponderada (km)  [menor e melhor]", fontsize=11)
    ax.set_ylabel("Cobertura dentro de 80 km (%)  [maior e melhor]", fontsize=11)
    ax.set_title(
        "Fronteira de Pareto — NSGA-II\n"
        "linha preta = limite alcancavel | linha tracejada = pontos 3D por seed (projecao) | * = compromisso",
        fontsize=11,
    )
    ax.legend(fontsize=9, title_fontsize=9, loc="lower left")
    ax.grid(alpha=0.25)
    ax.set_xlim(x_left, x_right)

    fig.tight_layout()
    fig.savefig("fig8_fronteira_pareto.png", dpi=150)
    plt.close(fig)
    print("fig8_fronteira_pareto.png gerada")


def plot_pairwise(df: pd.DataFrame):
    """
    Tres paineis com todas as combinacoes de pares de objetivos.
    Cada painel inclui o envelope 2D correto para aquele par.
    A cor representa o terceiro objetivo.

    Painel 1: f1 (min) x cobertura (max)  — trade-off principal
    Painel 2: f1 (min) x f3 (min)         — correlacao entre as duas metricas de distancia
    Painel 3: cobertura (max) x f3 (min)  — cobertura vs equidade espacial

    Para o envelope de cada painel: _nondominated_2d retorna x SEMPRE
    em ordem crescente no dominio original, garantindo que _build_step
    desenhe o degrau da esquerda para a direita em todos os casos.
    """
    panels = [
        {
            "xcol": "f1_avg_distance_km",   "xdir": "min",
            "ycol": "coverage_80km_pct",    "ydir": "max",
            "ccol": "f3_p95_distance_km",
            "xlabel": "f1 — Distancia media (km)",
            "ylabel": "Cobertura 80 km (%)",
            "clabel": "f3 P95 (km)",
        },
        {
            "xcol": "f1_avg_distance_km",   "xdir": "min",
            "ycol": "f3_p95_distance_km",   "ydir": "min",
            "ccol": "coverage_80km_pct",
            "xlabel": "f1 — Distancia media (km)",
            "ylabel": "f3 — P95 distancia (km)",
            "clabel": "Cobertura (%)",
        },
        {
            "xcol": "coverage_80km_pct",    "xdir": "max",
            "ycol": "f3_p95_distance_km",   "ydir": "min",
            "ccol": "f1_avg_distance_km",
            "xlabel": "Cobertura 80 km (%)",
            "ylabel": "f3 — P95 distancia (km)",
            "clabel": "f1 Dist. media (km)",
        },
    ]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    for ax, p in zip(axes, panels):
        x_left  = df[p["xcol"]].min() - 0.5
        x_right = df[p["xcol"]].max() + 0.5

        x_nd, y_nd = _nondominated_2d(
            df[p["xcol"]].values,
            df[p["ycol"]].values,
            x_dir=p["xdir"],
            y_dir=p["ydir"],
        )
        xs_step, ys_step = _build_step(x_nd, y_nd, x_left, x_right)

        sc = ax.scatter(
            df[p["xcol"]], df[p["ycol"]],
            c=df[p["ccol"]], cmap="viridis_r",
            s=40, alpha=0.75, edgecolors="none", zorder=3,
        )
        ax.plot(xs_step, ys_step, color="#111111", linewidth=1.6, alpha=0.85, zorder=2)

        cbar = fig.colorbar(sc, ax=ax, pad=0.02)
        cbar.set_label(p["clabel"], fontsize=8)
        ax.set_xlabel(p["xlabel"], fontsize=9)
        ax.set_ylabel(p["ylabel"], fontsize=9)
        ax.set_xlim(x_left, x_right)
        ax.grid(alpha=0.2)

    fig.suptitle("Fronteira de Pareto — projecoes 2-a-2 dos tres objetivos", fontsize=12)
    fig.tight_layout()
    fig.savefig("fig9_pareto_pairwise.png", dpi=150)
    plt.close(fig)
    print("fig9_pareto_pairwise.png gerada")


def print_summary(df: pd.DataFrame):
    print("\n-- Resumo da fronteira de Pareto ------------------------------")
    print(f"Seeds: {[int(s) for s in sorted(df['seed'].unique())]}")
    print(f"Total de solucoes nao-dominadas (3D, por seed): {len(df)}")

    by_seed = df.groupby("seed")["point_idx"].count().rename("tamanho_front")
    by_seed.index = by_seed.index.astype(int)
    print(by_seed.to_string())

    print("\nIntervalo dos objetivos (todas as seeds):")
    for col, label in [
        ("f1_avg_distance_km",  "f1 distancia media (km)  "),
        ("coverage_80km_pct",   "cobertura 80 km (%)      "),
        ("f3_p95_distance_km",  "f3 P95 distancia (km)    "),
        ("total_cost_brl",      "custo total (R$)         "),
    ]:
        print(f"  {label}: [{df[col].min():.2f},  {df[col].max():.2f}]")

    x_nd, y_nd = _nondominated_2d(
        df["f1_avg_distance_km"].values,
        df["coverage_80km_pct"].values,
        x_dir="min", y_dir="max",
    )
    print(f"\nEnvelope 2D global (f1 x cobertura): {len(x_nd)} pontos nao-dominados")
    print("  (nao-dominados na projecao 2D, combinando todas as seeds)")
    for xi, yi in zip(x_nd, y_nd):
        print(f"  f1={xi:.2f} km  |  cobertura={yi:.2f}%")


def main():
    df = _load()
    print_summary(df)
    plot_main_front(df)
    plot_pairwise(df)
    print("\nFiguras salvas:")
    print("  fig8_fronteira_pareto.png")
    print("  fig9_pareto_pairwise.png")


if __name__ == "__main__":
    main()
