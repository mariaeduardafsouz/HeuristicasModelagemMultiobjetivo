"""
Verificacao e validacao dos resultados da fronteira de Pareto.

Pre-requisito: fronteira_pareto.csv (gerado por run_pareto.py)

Checagens:
  1. Integridade do CSV (complementaridade f2/cobertura, orcamento,
     is_compromise por seed, numero de facilidades)
  2. Dominancia: nenhuma solucao dentro de uma seed domina outra
  3. Envelope 2D: todo ponto fora do envelope e dominado por algum ponto do envelope
  4. Solucao de compromisso: nao e extremo de nenhum objetivo (quando front > 1)
  5. Consistencia entre seeds: dispersao do front por seed

Saidas:
  - Relatorio no terminal (PASSOU / FALHOU)
  - fig_verificacao_seeds.png  (scatter por seed)
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATA_PATH = Path("fronteira_pareto.csv")

SEED_COLORS = {
    42: "#1b9e77", 123: "#d95f02", 456: "#7570b3",
    789: "#e7298a", 1011: "#66a61e",
}

_resultados = []


def _registrar(nome, passou, detalhe=""):
    tag = "PASSOU" if passou else "FALHOU"
    _resultados.append((nome, tag, detalhe))
    print(f"  [{tag}] {nome}")
    if detalhe:
        for linha in detalhe.strip().split("\n"):
            print(f"          {linha}")


def _nondominated_2d(x_vals, y_vals, x_dir="min", y_dir="min"):
    """Pontos nao-dominados 2D. Retorna x SEMPRE em ordem crescente."""
    x = np.asarray(x_vals, dtype=float)
    y = np.asarray(y_vals, dtype=float)
    xs = x if x_dir == "min" else -x
    ys = y if y_dir == "min" else -y
    order = np.argsort(xs)
    x_s, y_s, ys_s = x[order], y[order], ys[order]
    keep, min_ys = [], np.inf
    for i in range(len(x_s)):
        if ys_s[i] < min_ys:
            min_ys = ys_s[i]
            keep.append(i)
    x_nd, y_nd = x_s[keep], y_s[keep]
    asc = np.argsort(x_nd)
    return x_nd[asc], y_nd[asc]


def checar_csv(df):
    print("\n=== 1. Integridade do CSV ===")

    soma = (df["f2_uncovered_80km_pct"] + df["coverage_80km_pct"]).round(4)
    erros = df[soma != 100.0]
    _registrar(
        "f2_uncovered + coverage_80km == 100 em todas as linhas",
        erros.empty,
        f"{len(erros)} linha(s) com soma != 100" if not erros.empty else "",
    )

    inviaveis = df[df["budget_slack_brl"] < 0]
    _registrar(
        "Todas as solucoes dentro do orcamento (budget_slack >= 0)",
        inviaveis.empty,
        f"{len(inviaveis)} solucao(oes) inviavel(is)" if not inviaveis.empty else "",
    )

    comp_por_seed = df.groupby("seed")["is_compromise"].sum().astype(int)
    comp_por_seed.index = comp_por_seed.index.astype(int)
    erros_comp = comp_por_seed[comp_por_seed != 1]
    _registrar(
        "Exatamente 1 solucao de compromisso por seed",
        erros_comp.empty,
        "\n".join(f"seed {s}: {v} compromisso(s)" for s, v in erros_comp.items())
        if not erros_comp.empty else "",
    )

    n_fac = df["facilities"].apply(lambda x: len(x.split(";")))
    erros_fac = df[n_fac != 12]
    _registrar(
        "Exatamente 12 facilidades por solucao",
        erros_fac.empty,
        f"{len(erros_fac)} linha(s) com numero diferente de 12" if not erros_fac.empty else "",
    )


def checar_dominancia(df):
    print("\n=== 2. Dominancia intra-seed ===")
    EPS = 1e-9
    obj_cols = ["f1_avg_distance_km", "f2_uncovered_80km_pct", "f3_p95_distance_km"]

    total_violacoes = 0
    detalhes = []

    for seed, grp in df.groupby("seed"):
        obj = grp[obj_cols].values
        n = len(obj)
        violacoes_seed = 0
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                if np.all(obj[i] <= obj[j] + EPS) and np.any(obj[i] < obj[j] - EPS):
                    violacoes_seed += 1
        if violacoes_seed > 0:
            detalhes.append(f"seed {int(seed)}: {violacoes_seed} par(es) com dominancia")
        total_violacoes += violacoes_seed

    _registrar(
        "Nenhuma solucao domina outra dentro da mesma seed (3D)",
        total_violacoes == 0,
        "\n".join(detalhes) if detalhes else "",
    )


def checar_envelope(df):
    print("\n=== 3. Envelope 2D (f1 x cobertura) ===")

    f1 = df["f1_avg_distance_km"].values
    cov = df["coverage_80km_pct"].values

    x_nd, y_nd = _nondominated_2d(f1, cov, x_dir="min", y_dir="max")
    n_envelope = len(x_nd)

    EPS = 1e-9
    nao_dominados_fora = []
    for i in range(len(f1)):
        dominado = any(
            x_nd[k] <= f1[i] + EPS and y_nd[k] >= cov[i] - EPS
            for k in range(n_envelope)
        )
        if not dominado:
            nao_dominados_fora.append(i)

    _registrar(
        f"Envelope calculado com {n_envelope} pontos nao-dominados 2D",
        True,
        f"f1 em [{x_nd.min():.2f}, {x_nd.max():.2f}] | "
        f"cobertura em [{y_nd.min():.2f}%, {y_nd.max():.2f}%]",
    )
    _registrar(
        "Todo ponto fora do envelope e dominado por algum ponto do envelope",
        len(nao_dominados_fora) == 0,
        f"{len(nao_dominados_fora)} ponto(s) escaparam ao envelope (bug em _nondominated_2d)"
        if nao_dominados_fora else "",
    )


def checar_compromisso(df):
    print("\n=== 4. Solucao de compromisso ===")
    avisos = []
    detalhes_ok = []

    for seed, grp in df.groupby("seed"):
        seed = int(seed)
        comp = grp[grp["is_compromise"] == 1]
        if comp.empty:
            avisos.append(f"seed {seed}: sem solucao de compromisso marcada")
            continue

        n = len(grp)
        if n == 1:
            avisos.append(f"seed {seed}: front com 1 solucao — compromisso trivialmente extremo")
            continue

        f1_comp  = comp["f1_avg_distance_km"].iloc[0]
        cov_comp = comp["coverage_80km_pct"].iloc[0]
        f3_comp  = comp["f3_p95_distance_km"].iloc[0]

        f1_min  = grp["f1_avg_distance_km"].min()
        cov_max = grp["coverage_80km_pct"].max()
        f3_min  = grp["f3_p95_distance_km"].min()

        EPS = 1e-6
        e_extremo_f1  = abs(f1_comp  - f1_min)  < EPS
        e_extremo_cov = abs(cov_comp - cov_max)  < EPS
        e_extremo_f3  = abs(f3_comp  - f3_min)   < EPS

        detalhes_ok.append(
            f"seed {seed}: f1={f1_comp:.2f} (min={f1_min:.2f}) | "
            f"cov={cov_comp:.2f}% (max={cov_max:.2f}%) | "
            f"f3={f3_comp:.2f} (min={f3_min:.2f})"
        )

        if e_extremo_f1 or e_extremo_cov or e_extremo_f3:
            quais = []
            if e_extremo_f1:  quais.append("f1")
            if e_extremo_cov: quais.append("cobertura")
            if e_extremo_f3:  quais.append("f3")
            avisos.append(f"seed {seed}: compromisso coincide com extremo de {', '.join(quais)}")

    _registrar(
        "Compromisso nao e extremo em nenhum objetivo (front com > 1 ponto)",
        len(avisos) == 0,
        "\n".join(avisos) if avisos else "\n".join(detalhes_ok),
    )


def checar_consistencia_seeds(df):
    print("\n=== 5. Consistencia entre seeds ===")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for seed, grp in df.groupby("seed"):
        c = SEED_COLORS[int(seed)]
        comp = grp[grp["is_compromise"] == 1]

        axes[0].scatter(
            grp["f1_avg_distance_km"], grp["coverage_80km_pct"],
            color=c, alpha=0.6, s=45, label=f"seed {int(seed)} (n={len(grp)})",
        )
        if not comp.empty:
            axes[0].scatter(
                comp["f1_avg_distance_km"], comp["coverage_80km_pct"],
                color=c, marker="*", s=200, edgecolors="#111", zorder=5,
            )

        axes[1].scatter(
            grp["f1_avg_distance_km"], grp["f3_p95_distance_km"],
            color=c, alpha=0.6, s=45,
        )

    for ax, (xlabel, ylabel) in zip(axes, [
        ("f1 — Distancia media (km)", "Cobertura 80 km (%)"),
        ("f1 — Distancia media (km)", "f3 — P95 distancia (km)"),
    ]):
        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.grid(alpha=0.25)

    axes[0].legend(fontsize=8, title="Seed (n = tamanho do front)")
    fig.suptitle("Consistencia entre seeds — dispersao dos fronts individuais\n* = solucao de compromisso", fontsize=11)
    fig.tight_layout()
    fig.savefig("fig_verificacao_seeds.png", dpi=150)
    plt.close(fig)

    stats = df.groupby("seed")[["f1_avg_distance_km", "coverage_80km_pct"]].agg(["min", "max", "std"])
    stats.index = stats.index.astype(int)
    f1_ranges  = (stats["f1_avg_distance_km"]["max"] - stats["f1_avg_distance_km"]["min"]).round(2)
    cov_ranges = (stats["coverage_80km_pct"]["max"] - stats["coverage_80km_pct"]["min"]).round(2)

    seed_mais_disperso   = int(f1_ranges.idxmax())
    seed_menos_disperso  = int(f1_ranges.idxmin())

    detalhe = (
        f"Amplitude de f1 por seed (km): {f1_ranges.to_dict()}\n"
        f"Amplitude de cobertura por seed (%): {cov_ranges.to_dict()}\n"
        f"Seed com front mais disperso em f1:  seed {seed_mais_disperso}\n"
        f"Seed com front menos disperso em f1: seed {seed_menos_disperso} "
        f"({'possivel convergencia prematura' if f1_ranges[seed_menos_disperso] < 1.0 else 'ok'})"
    )

    _registrar(
        "Dispersao dos fronts por seed (grafico salvo em fig_verificacao_seeds.png)",
        True,
        detalhe,
    )


def relatorio_final():
    print("\n" + "=" * 60)
    print("RELATORIO FINAL")
    print("=" * 60)
    passou = sum(1 for _, s, _ in _resultados if s == "PASSOU")
    falhou = sum(1 for _, s, _ in _resultados if s == "FALHOU")
    for nome, status, _ in _resultados:
        print(f"  [{status}] {nome}")
    print("-" * 60)
    print(f"  Total: {passou} passou | {falhou} falhou")
    if falhou == 0:
        print("  Todos os resultados validados com sucesso.")
    else:
        print("  ATENCAO: ha checagens com falha — revise os detalhes acima.")


def main():
    if not DATA_PATH.exists():
        print(f"Arquivo {DATA_PATH} nao encontrado. Execute: python run_pareto.py")
        return

    df = pd.read_csv(DATA_PATH)
    print(f"Carregado: {len(df)} solucoes | {df['seed'].nunique()} seeds\n")

    checar_csv(df)
    checar_dominancia(df)
    checar_envelope(df)
    checar_compromisso(df)
    checar_consistencia_seeds(df)
    relatorio_final()


if __name__ == "__main__":
    main()
