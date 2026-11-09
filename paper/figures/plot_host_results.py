"""Render existing reported host-DRAM observations; never execute experiments."""

import csv
import hashlib
import json
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INPUT = ROOT / "notes/experiment-evidence/host-dram-reported-results.json"
BLUE, GREEN, PURPLE = "#536e89", "#238269", "#8661a6"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 8,
    "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.facecolor": "white",
})


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(fig, name):
    fig.savefig(HERE / f"{name}.pdf", bbox_inches="tight",
                metadata={"CreationDate": None, "ModDate": None})
    fig.savefig(HERE / f"{name}.png", dpi=230, bbox_inches="tight")
    plt.close(fig)


def clean(ax, axis="y"):
    ax.grid(axis=axis, alpha=.18)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)


def architecture():
    fig, ax = plt.subplots(figsize=(3.35, 2.25))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")

    def box(x, y, w, h, text, color):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=.012",
                                   facecolor=color, edgecolor="#4d5963", linewidth=.8))
        ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=7)

    box(.035, .72, .93, .24,
        "Request queue and radix prefix index\nFCFS / prefix / fetch-aware ordering\nGPU + host residency; reuse priorities", "#edf0f4")
    box(.025, .16, .40, .29,
        "GPU KV cache\n24 GiB\n16-token pages", "#e5eef6")
    box(.575, .16, .40, .29,
        "Pinned host KV cache\n36 GiB\nInclusive clean copies", "#e2f0e9")
    for x, label in [(.225, "GPU hit / prefill"), (.775, "Host match")]:
        ax.annotate("", (x, .46), (x, .71), arrowprops={"arrowstyle": "->", "lw": .8})
        ax.text(x, .61, label, ha="center", va="center", fontsize=6.6,
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
    ax.annotate("", (.57, .37), (.43, .37), arrowprops={"arrowstyle": "->", "color": BLUE, "lw": 1.1})
    ax.text(.50, .44, "D2H", ha="center", fontsize=6.6)
    ax.annotate("", (.43, .24), (.57, .24), arrowprops={"arrowstyle": "->", "color": GREEN, "lw": 1.1})
    ax.text(.50, .17, "H2D", ha="center", fontsize=6.6)
    ax.text(.5, .035, "Dirty eviction: offload   |   Reuse: restore / prefetch", ha="center", fontsize=6.6)
    save(fig, "host-cache-architecture")


def restoration(data):
    fig, axes = plt.subplots(1, 2, figsize=(7, 2.55), layout="constrained")
    ns = [28, 36]
    metrics = [("session_s", "(a) Mean session serving time", "Time (s)", 1200),
               ("prior_prefix_deficit_mtokens", "(b) Prior-prefix deficit estimate", "Tokens (millions)", 7)]
    handles = []
    for ax, (metric, title, ylabel, limit) in zip(axes, metrics):
        for offset, recovery, color in [(-.17, "Recompute", BLUE), (.17, "Host restore", GREEN)]:
            values = [next(r[metric] for r in data["primary_observations"]
                           if r["n"] == n and r["recovery"] == recovery) for n in ns]
            bars = ax.bar(np.arange(2)+offset, values, width=.3, color=color, label=recovery)
            for bar, value in zip(bars, values):
                label = f"{value:,.0f}" if metric == "session_s" and value >= 100 else (
                    f"{value:g}" if metric == "session_s" else f"{value:.3f}")
                ax.text(bar.get_x()+bar.get_width()/2, value+limit*.025, label,
                        ha="center", va="bottom", fontsize=7)
        ax.set(title=title, ylabel=ylabel, xlabel="Concurrent episodes, N",
               xticks=np.arange(2), xticklabels=ns, ylim=(0, limit))
        clean(ax)
        handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper center", ncol=2, frameon=False, fontsize=7)
    save(fig, "host-restoration-results")


def ablation(data):
    fig, axes = plt.subplots(1, 2, figsize=(7, 2.75),
                             gridspec_kw={"width_ratios": [1.2, 1]}, layout="constrained")
    rows = data["n36_policy_observations"]
    colors = [BLUE, GREEN, "#aa96bd", "#c5b6d2", PURPLE]
    for y, (row, color) in enumerate(zip(rows, colors)):
        axes[0].barh(y, row["session_s"], color=color, height=.6)
        axes[0].text(row["session_s"]+4, y, f"{row['session_s']:g}", va="center", fontsize=7)
    axes[0].set(title="(a) Reported policy observations, N = 36",
                yticks=np.arange(len(rows)), yticklabels=[r["policy"] for r in rows],
                xlabel="Mean session serving time (s)", xlim=(0, 255))
    axes[0].invert_yaxis()
    policies = ["Predictive + prefix", "CacheWise-Fetch"]
    for x, (policy, color) in enumerate(zip(policies, ["#aa96bd", PURPLE])):
        values = [r["session_s"] for r in data["n36_repeated_observations"] if r["policy"] == policy]
        for offset, marker, value in zip([-.06, .06], ["o", "s"], values):
            axes[1].scatter(x+offset, value, color=color, marker=marker, s=24)
        mean = statistics.mean(values)
        axes[1].plot([x-.2, x+.2], [mean, mean], color="#303030", lw=.9)
        axes[1].text(x, max(values)+10, f"Mean {mean:g}", ha="center", fontsize=7)
    axes[1].set(title="(b) Available repeated observations",
                xticks=[0, 1], xticklabels=["Predictive +\nprefix", "CacheWise-\nFetch"],
                ylabel="Mean session serving time (s)", xlim=(-.5, 1.5), ylim=(0, 210))
    axes[1].text(.5, .04, "Dots: runs; lines: means of reported values\nNo confidence interval is implied",
                 ha="center", transform=axes[1].transAxes, fontsize=6.4)
    clean(axes[0], "x")
    clean(axes[1])
    save(fig, "host-policy-ablation")


def table(data):
    lines = [r"% Generated from existing rounded reported observations by plot_host_results.py.",
             r"\begin{table*}[t]", r"  \centering", r"  \small",
             r"  \begin{tabular}{rllrrrr}", r"    \toprule",
             r"    $N$ & Recovery & Policy & Session (s) & Goodput (tok/s) & \shortstack{Prior-prefix\\deficit (M)} & P90 (s) \\",
             r"    \midrule"]
    for row in data["primary_observations"]:
        lines.append(f"    {row['n']} & {row['recovery']} & LRU+FCFS & {row['session_s']:g} & "
                     f"{row['goodput_tokens_s']:,.0f} & {row['prior_prefix_deficit_mtokens']:.3f} & {row['request_p90_s']:.1f} " + r"\\")
    lines += [r"    \bottomrule", r"  \end{tabular}",
              r"  \caption{Reported Mini-SGLang observations with LRU+FCFS fixed; one run per cell. Restoration adds 36~GiB of nominal pinned-host KV payload to the common 24~GiB GPU KV pool. Values retain the artifact summary's rounding. Prior-prefix deficit estimates missing reuse at admission and includes page-alignment effects; it is not exclusive GPU compute time.}",
              r"  \label{tab:host-restore-results}", r"\end{table*}"]
    (HERE / "host-restoration-table.tex").write_text("\n".join(lines)+"\n")


def main():
    data = json.loads(INPUT.read_text())
    assert data["revision"] == "3f9aee7362004126e937ba88085ff72f9ad6083a"
    assert data["gpu_kv_tokens"]*data["kv_bytes_per_token"] == 24*1024**3
    assert data["host_kv_tokens"]*data["kv_bytes_per_token"] == data["host_kv_gib"]*1024**3
    records = data["primary_observations"]+data["n36_policy_observations"]+data["n36_repeated_observations"]
    for row in records:
        assert row["session_s"] > 0 and len(row["source_git_blob_sha1"]) == 40
        assert row["source_path"].startswith("cachewise_exp/results/")
    architecture()
    restoration(data)
    ablation(data)
    table(data)
    fields = ["source_path", "source_git_blob_sha1", "n", "policy", "recovery", "session_s", "observations"]
    with (HERE / "host-reported-observations.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for section in ["primary_observations", "n36_policy_observations", "n36_repeated_observations"]:
            for row in data[section]:
                writer.writerow({"n": 36, "recovery": "Host restore", "observations": 1, **row})
    outputs = [HERE / f"{name}.{ext}" for name in ["host-cache-architecture", "host-restoration-results", "host-policy-ablation"]
               for ext in ["pdf", "png"]]
    outputs += [HERE / "host-restoration-table.tex", HERE / "host-reported-observations.csv"]
    provenance = {
        "input": str(INPUT.relative_to(ROOT)), "input_sha256": sha(INPUT),
        "script_sha256": sha(Path(__file__)), "artifact_revision": data["revision"],
        "matplotlib_version": matplotlib.__version__, "numpy_version": np.__version__,
        "outputs": {p.name: sha(p) for p in outputs},
        "scope": "Figures and table render existing rounded reported observations only. No experiment, model execution, or benchmark is run. No confidence intervals or matched-repeat guarantees are inferred from the two N=36 observations.",
    }
    (HERE / "host-figure-provenance.json").write_text(json.dumps(provenance, indent=2)+"\n")
    print("Rendered architecture and two result figures from existing reported data; no experiments executed.")


if __name__ == "__main__":
    main()
