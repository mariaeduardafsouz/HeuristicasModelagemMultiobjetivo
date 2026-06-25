import time

import numpy as np
import pandas as pd

from algoritmo import (
    choose_compromise_index,
    run_ga,
    run_nsga2,
    solution_metrics,
)


SEEDS = [42, 123, 456, 789, 1011]


def _facilities_to_text(selected):
    return ";".join(str(int(i)) for i in selected)


def _row_from_solution(metodo, algoritmo, config, seed, pop_size, n_gen, selected, tempo_s, fitness_single=None):
    metrics = solution_metrics(selected)
    return {
        "metodo": metodo,
        "algoritmo": algoritmo,
        "config": config,
        "seed": seed,
        "pop_size": pop_size,
        "n_gen": n_gen,
        "fitness_single": fitness_single,
        "avg_distance_km": metrics["avg_distance_km"],
        "coverage_80km_pct": metrics["coverage_80km_pct"],
        "uncovered_80km_pct": metrics["uncovered_80km_pct"],
        "p95_distance_km": metrics["p95_distance_km"],
        "max_distance_km": metrics["max_distance_km"],
        "total_cost_brl": metrics["total_cost_brl"],
        "budget_violation_brl": metrics["budget_violation_brl"],
        "budget_slack_brl": metrics["budget_slack_brl"],
        "tempo_s": tempo_s,
        "n_selected": len(selected),
        "facilities": _facilities_to_text(selected),
    }


def _summarize_comparison(df):
    grouped = df.groupby(["metodo", "algoritmo", "config", "pop_size", "n_gen"], sort=False)
    summary = grouped.agg(
        avg_distance_mean=("avg_distance_km", "mean"),
        avg_distance_std=("avg_distance_km", "std"),
        avg_distance_best=("avg_distance_km", "min"),
        coverage_80km_mean=("coverage_80km_pct", "mean"),
        coverage_80km_std=("coverage_80km_pct", "std"),
        coverage_80km_best=("coverage_80km_pct", "max"),
        p95_distance_mean=("p95_distance_km", "mean"),
        p95_distance_std=("p95_distance_km", "std"),
        p95_distance_best=("p95_distance_km", "min"),
        max_distance_mean=("max_distance_km", "mean"),
        total_cost_mean=("total_cost_brl", "mean"),
        budget_violation_max=("budget_violation_brl", "max"),
        tempo_medio_s=("tempo_s", "mean"),
    ).reset_index()
    return summary


def _round_numeric(df):
    rounded = df.copy()
    for col in rounded.select_dtypes(include=[np.number]).columns:
        if col in {"seed", "pop_size", "n_gen", "n_selected"}:
            continue
        rounded[col] = rounded[col].round(6)
    return rounded


def main():
    comparison_rows = []
    history_rows = []
    nsga_seed_rows = []

    ga_configs = [
        {
            "metodo": "AG baseline",
            "algoritmo": "GA",
            "config": "baseline",
            "pop_size": 100,
            "n_gen": 300,
        },
        {
            "metodo": "AG single-objective V3",
            "algoritmo": "GA",
            "config": "V3_gen500",
            "pop_size": 100,
            "n_gen": 500,
        },
    ]

    for cfg in ga_configs:
        print(f"\nRodando {cfg['metodo']} ({cfg['config']})")
        for seed in SEEDS:
            start = time.time()
            _, fit, selected, _ = run_ga(
                seed=seed,
                pop_size=cfg["pop_size"],
                n_gen=cfg["n_gen"],
                verbose=False,
            )
            tempo_s = time.time() - start
            comparison_rows.append(
                _row_from_solution(
                    cfg["metodo"],
                    cfg["algoritmo"],
                    cfg["config"],
                    seed,
                    cfg["pop_size"],
                    cfg["n_gen"],
                    selected,
                    tempo_s,
                    fitness_single=fit,
                )
            )
            print(f"  seed {seed}: dist={fit:.4f} km | tempo={tempo_s:.1f}s")

    print("\nRodando NSGA-II (pop=100, gen=300)")
    for seed in SEEDS:
        start = time.time()
        result = run_nsga2(seed=seed, pop_size=100, n_gen=300, verbose=False)
        tempo_s = time.time() - start

        front_pop = result["front_population"]
        front_obj = result["front_objectives"]
        compromise_idx = choose_compromise_index(front_obj)
        compromise_selected = np.where(front_pop[compromise_idx] == 1)[0]

        comparison_rows.append(
            _row_from_solution(
                "NSGA-II compromisso",
                "NSGA-II",
                "nsga2_pop100_gen300",
                seed,
                100,
                300,
                compromise_selected,
                tempo_s,
            )
        )

        best_distance_idx = int(np.argmin(front_obj[:, 0]))
        best_coverage_idx = int(np.argmin(front_obj[:, 1]))
        best_p95_idx = int(np.argmin(front_obj[:, 2]))
        nsga_seed_rows.append(
            {
                "seed": seed,
                "front_size": len(front_pop),
                "tempo_s": tempo_s,
                "compromise_avg_distance_km": solution_metrics(compromise_selected)["avg_distance_km"],
                "compromise_coverage_80km_pct": solution_metrics(compromise_selected)["coverage_80km_pct"],
                "compromise_p95_distance_km": solution_metrics(compromise_selected)["p95_distance_km"],
                "best_avg_distance_km": front_obj[best_distance_idx, 0],
                "best_coverage_80km_pct": 100.0 - front_obj[best_coverage_idx, 1],
                "best_p95_distance_km": front_obj[best_p95_idx, 2],
            }
        )

        for item in result["history"]:
            history_rows.append({"seed": seed, **item})

        comp_metrics = solution_metrics(compromise_selected)
        print(
            "  seed {seed}: front={front} | compromisso dist={dist:.4f} km | "
            "cov={cov:.2f}% | p95={p95:.1f} km | tempo={tempo:.1f}s".format(
                seed=seed,
                front=len(front_pop),
                dist=comp_metrics["avg_distance_km"],
                cov=comp_metrics["coverage_80km_pct"],
                p95=comp_metrics["p95_distance_km"],
                tempo=tempo_s,
            )
        )

    comparison_df = _round_numeric(pd.DataFrame(comparison_rows))
    comparison_df.to_csv("resultados_comparacao_multiobjetivo.csv", index=False)

    summary_df = _round_numeric(_summarize_comparison(comparison_df))
    summary_df.to_csv("resumo_comparacao_multiobjetivo.csv", index=False)

    nsga_seed_df = _round_numeric(pd.DataFrame(nsga_seed_rows))
    nsga_seed_df.to_csv("resultados_nsga2_seeds.csv", index=False)

    history_df = _round_numeric(pd.DataFrame(history_rows))
    history_df.to_csv("historico_nsga2.csv", index=False)

    print("\nResumo comparativo:")
    print(summary_df.to_string(index=False))
    print("\nArquivos gerados:")
    print("- resultados_comparacao_multiobjetivo.csv")
    print("- resumo_comparacao_multiobjetivo.csv")
    print("- resultados_nsga2_seeds.csv")
    print("- historico_nsga2.csv")


if __name__ == "__main__":
    main()
