"""Regenerate Part 1 figures from the numeric evidence saved with the paper."""

import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parents[1] / "notes/experiment-evidence"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 7.5, "axes.titlesize": 8,
    "axes.labelsize": 7.5, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.facecolor": "white",
})


def save(fig, name):
    for extension in ["pdf", "png"]:
        fig.savefig(HERE / f"{name}.{extension}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot():
    corpus = json.loads((EVIDENCE / "workload-characterization.json").read_text())
    report = json.loads((EVIDENCE / "consolidated-comparison.json").read_text())
    fig, axes = plt.subplots(1, 3, figsize=(7, 2.15), layout="constrained")
    for key, name, color in [("prompt", "Prompt", "#245878"), ("output", "Output", "#c66337")]:
        data = corpus[key]
        axes[0].plot(data["cdf_x"], data["cdf_y"], label=name, color=color, linewidth=1.4)
    axes[0].set(xscale="log", xlabel="Tokens per unique message", ylabel="CDF",
                title="(a) Prompt and output lengths", ylim=(0, 1.02))
    axes[0].legend(frameon=False, fontsize=6.5)
    data = corpus["turns"]
    axes[1].plot(data["cdf_x"], data["cdf_y"], color="#287b63", linewidth=1.4)
    axes[1].set(xscale="log", xlabel="Unique messages per source trace", ylabel="CDF",
                title="(b) Trace turn counts", ylim=(0, 1.02))
    axes[2].bxp(corpus["tool_boxes"], showfliers=False, patch_artist=True,
                boxprops={"facecolor": "#e2edf2", "linewidth": .8},
                medianprops={"color": "#a9462b", "linewidth": 1.2},
                whiskerprops={"linewidth": .8}, capprops={"linewidth": .8})
    axes[2].set(yscale="log", ylabel="Individual tool duration (s)", title="(c) Six most frequent tools")
    axes[2].tick_params(axis="x", labelrotation=45, labelsize=6.5)
    for label in axes[2].get_xticklabels(): label.set_horizontalalignment("right")
    for ax in axes:
        ax.grid(axis="y", alpha=.18)
        ax.spines[["top", "right"]].set_visible(False)
    save(fig, "replication-workload")

    policies = ["baseline", "eviction_only", "prefix_only_no_aging", "cachewise_no_aging",
                "cachewise_oracle_no_aging", "cachewise"]
    names = ["FCFS / LRU", "FCFS / predictive", "Prefix / LRU", "Prefix / predictive",
             "Prefix / oracle", "Prefix / predictive + aging"]
    fig, axes = plt.subplots(1, 2, figsize=(7, 2.45), gridspec_kw={"width_ratios": [1.45, 1]}, layout="constrained")
    means = np.array([report["policies"][p]["mean_session_llm_time_s"] for p in policies])
    low = np.array([report["policies"][p]["observed_mean_time_range_s"][0] for p in policies])
    high = np.array([report["policies"][p]["observed_mean_time_range_s"][1] for p in policies])
    ypos = np.arange(len(policies))
    colors = ["#b4c5d0", "#8db3c8", "#438467", "#826aa0", "#aea0c0", "#d2a28e"]
    axes[0].barh(ypos, means, height=.62, color=colors, edgecolor="white")
    axes[0].errorbar(means, ypos, xerr=np.vstack((means-low, high-means)), fmt="none", ecolor="#242424", capsize=2, linewidth=.8)
    axes[0].set(yticks=ypos, yticklabels=names, xlabel="Mean session serving time (s)",
                title="(a) Six-policy results, N = 10", xlim=(0, 690))
    axes[0].invert_yaxis()
    for y, mean in zip(ypos, means): axes[0].text(mean+14, y, f"{mean:.1f}", va="center", fontsize=6.7)

    contrasts = [("eviction_only", "baseline"), ("cachewise_no_aging", "prefix_only_no_aging"),
                 ("cachewise_oracle_no_aging", "cachewise_no_aging")]
    labels = ["Predictive vs LRU\nFCFS", "Predictive vs LRU\nPrefix-aware", "Oracle vs learned\nPrefix-aware"]
    exports = []
    for y, (treatment, control) in enumerate(contrasts):
        for repeat, (marker, color) in enumerate(zip(["o", "s", "^"], ["#245878", "#a1502a", "#287b63"])):
            def value(policy):
                return next(r["mean_session_llm_time_s"] for r in report["runs"] if r["run"]==f"{policy}-r{repeat}")
            change = 100 * (value(treatment) / value(control) - 1)
            axes[1].plot(change, y+(repeat-1)*.11, marker, color=color, markersize=4,
                         label=f"Repeat {repeat+1}" if y==0 else None)
            exports.append({"treatment": treatment, "control": control, "repeat": repeat,
                            "time_change_percent": change})
    axes[1].axvline(0, color="#555555", linewidth=.7, linestyle="--")
    axes[1].set(yticks=range(3), yticklabels=labels, xlabel="Change in mean time (%)",
                title="(b) Effects within matched repeats", xlim=(-14, 7), ylim=(2.65, -.45))
    axes[1].legend(loc="lower left", fontsize=6, frameon=False, ncol=1)
    for ax in axes:
        ax.grid(axis="x", alpha=.18)
        ax.spines[["top", "right"]].set_visible(False)
    save(fig, "replication-serving")
    with (HERE / "replication-paired-effects.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(exports[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(exports)
    provenance = {
        "inputs": {str(p.relative_to(HERE.parents[1])): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [EVIDENCE/"workload-characterization.json", EVIDENCE/"consolidated-comparison.json"]},
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "method": "Workload ECDFs use deduplicated source messages; tool boxes show the 25th/75th percentiles and 5th/95th percentile whiskers. Serving bars show three-repeat means and observed ranges; paired effects compare policies within the same GPU block. Negative time change means faster. No confidence intervals are implied.",
        "matplotlib_version": matplotlib.__version__, "numpy_version": np.__version__,
        "outputs": ["replication-workload.pdf", "replication-serving.pdf"],
    }
    (HERE / "replication-figure-provenance.json").write_text(json.dumps(provenance, indent=2)+"\n")


if __name__ == "__main__":
    plot()
