from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


COMPARISON_PATH = Path("resultados_comparacao_multiobjetivo.csv")
SUMMARY_PATH = Path("resumo_comparacao_multiobjetivo.csv")
HISTORY_PATH = Path("historico_nsga2.csv")


def _require_outputs():
    missing = [path for path in [COMPARISON_PATH, SUMMARY_PATH, HISTORY_PATH] if not path.exists()]
    if missing:
        names = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Arquivos ausentes: {names}. Rode python run_comparacao_multiobjetivo.py antes.")


def plot_comparison(df_comparison):
    order = ["AG baseline", "AG single-objective V3", "NSGA-II compromisso"]
    grouped = df_comparison.groupby("metodo", sort=False)
    means = grouped[["avg_distance_km", "coverage_80km_pct", "p95_distance_km"]].mean().reindex(order)
    stds = grouped[["avg_distance_km", "coverage_80km_pct", "p95_distance_km"]].std().reindex(order)

    labels = ["Baseline", "Single V3", "NSGA-II"]
    colors = ["#6b6b6b", "#d95f02", "#1b9e77"]

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.8))
    panels = [
        ("avg_distance_km", "Distância média (km)", "Menor é melhor"),
        ("coverage_80km_pct", "Cobertura 80 km (%)", "Maior é melhor"),
        ("p95_distance_km", "P95 distância (km)", "Menor é melhor"),
    ]

    for ax, (column, ylabel, title) in zip(axes, panels):
        ax.bar(labels, means[column], yerr=stds[column], capsize=5, color=colors, alpha=0.9)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.25)
        ax.tick_params(axis="x", rotation=12)
        ymin = min((means[column] - stds[column].fillna(0)).min(), means[column].min())
        ymax = max((means[column] + stds[column].fillna(0)).max(), means[column].max())
        pad = max((ymax - ymin) * 0.35, 0.5)
        ax.set_ylim(ymin - pad, ymax + pad)

    fig.suptitle("Comparação média em 5 sementes")
    fig.tight_layout()
    fig.savefig("fig6_comparacao_multiobjetivo.png", dpi=150)
    plt.close(fig)


def plot_nsga_history(df_history):
    grouped = df_history.groupby("generation")
    mean = grouped[
        ["min_avg_distance_km", "max_coverage_80km_pct", "min_p95_distance_km", "feasible_front0_count"]
    ].mean()

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    axes = axes.ravel()

    panels = [
        ("min_avg_distance_km", "Melhor distância média (km)"),
        ("max_coverage_80km_pct", "Melhor cobertura 80 km (%)"),
        ("min_p95_distance_km", "Melhor P95 distância (km)"),
        ("feasible_front0_count", "Soluções na frente viável"),
    ]

    for ax, (column, ylabel) in zip(axes, panels):
        ax.plot(mean.index, mean[column], color="#1b9e77", linewidth=2)
        ax.set_xlabel("Geração")
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.25)

    fig.suptitle("Convergência do NSGA-II")
    fig.tight_layout()
    fig.savefig("fig7_convergencia_nsga2.png", dpi=150)
    plt.close(fig)


def main():
    _require_outputs()
    df_comparison = pd.read_csv(COMPARISON_PATH)
    df_history = pd.read_csv(HISTORY_PATH)

    plot_comparison(df_comparison)
    plot_nsga_history(df_history)

    print("Figuras geradas:")
    print("- fig6_comparacao_multiobjetivo.png")
    print("- fig7_convergencia_nsga2.png")


if __name__ == "__main__":
    main()
