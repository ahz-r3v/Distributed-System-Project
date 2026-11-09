"""Render the completed coverage study without pooling historical measurements."""

import csv
import hashlib
import json
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EVIDENCE = ROOT / "notes/experiment-evidence"
POLICIES = ["baseline", "eviction_only", "prefix_only_no_aging", "cachewise_no_aging"]
NAMES = ["FCFS / LRU", "FCFS / predictive", "Prefix / LRU", "Prefix / predictive"]
COLORS = ["#536e89", "#cf7934", "#238269", "#8661a6"]
MARKERS = ["o", "s", "^", "D"]
SETTINGS = ["a-n10", "a-n20", "a-n30", "b-n10", "c-n10"]
LABELS = ["A10", "A20", "A30", "B10", "C10"]
METRICS = [
    "mean_session_serving_s", "elapsed_s", "useful_tokens_per_s", "requests_per_s",
    "request_p50_s", "request_p90_s", "request_p99_s", "maximum_request_s",
    "ttft_p50_s", "completed_request_prefix_hit_fraction",
    "reported_uncached_prompt_tokens", "reported_uncached_minus_first_use_tokens",
    "full_cached_block_evictions", "cached_block_invalidations_outside_allocation",
]
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 8,
    "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.facecolor": "white",
})


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load():
    inputs = [EVIDENCE / name for name in [
        "part1-coverage-comparison.json", "part1-coverage-completion.json",
        "part1-coverage-measurements.csv", "part1-preemption-audit-amendment.json",
    ]]
    manifest = json.loads((EVIDENCE / "manifest.json").read_text())
    hashes = {r["snapshot"]: r["sha256"] for r in manifest["snapshots"]}
    for path in inputs:
        if sha(path) != hashes[path.name]:
            raise ValueError(f"Archived evidence changed: {path.name}")
    data = json.loads(inputs[0].read_text())
    completion = json.loads(inputs[1].read_text())
    amendment = json.loads(inputs[3].read_text())
    rows = data["runs"]
    expected = {(setting, repeat, policy) for setting in SETTINGS
                for repeat in range(3) for policy in POLICIES}
    if len(rows) != 60 or {(r["setting"], r["repeat"], r["policy"]) for r in rows} != expected:
        raise ValueError("Expected exactly the 60 registered policy runs")
    for report in [data, completion]:
        if (report["status"] != "complete_with_protocol_deviation"
                or report["original_protocol_fully_satisfied"] is not False
                or report["reported_preemptions"] != 1):
            raise ValueError("Preemption deviation must remain disclosed")
    if (data["protocol_sha256"] != completion["shared_hashes"]["protocol_sha256"]
            or data["protocol_sha256"] != amendment["original_protocol_sha256"]
            or data["audit_amendment_sha256"] != sha(inputs[3])):
        raise ValueError("Protocol/amendment provenance mismatch")
    settings = {r["id"]: r for r in data["selection"]["settings"]}
    for r in rows:
        selected = settings[r["setting"]]
        for key in ["sessions", "requests", "prompt_tokens", "output_tokens", "first_use_prompt_tokens"]:
            if r[key] != selected[key]:
                raise ValueError(f"Workload accounting mismatch: {r['setting']}, {key}")
        if not np.isclose(r["completed_request_prefix_hit_fraction"],
                          1 - r["reported_uncached_prompt_tokens"] / r["prompt_tokens"], atol=1e-12, rtol=0):
            raise ValueError("Hit fraction differs from request token accounting")
    preempted = [r for r in rows if r["preemptions"]]
    if (len(preempted) != 1 or preempted[0]["setting"] != "a-n20"
            or preempted[0]["repeat"] != 0 or preempted[0]["policy"] != "cachewise_no_aging"
            or preempted[0]["preemptions"] != 1
            or preempted[0]["preemption_extra_prefill_tokens"] is not None):
        raise ValueError("Unexpected preemption outcome or hidden unmeasured work")
    if (sum(r["requests"] for r in rows) != completion["completed_requests"]
            or completion["completed_requests"] != 6384):
        raise ValueError("Completed request total differs from provenance")
    if sum(r["requests"] for r in rows) != 6384:
        raise ValueError("Expected 6,384 completed requests")
    with inputs[2].open() as handle:
        saved = list(csv.DictReader(handle))
    if (len(saved) != len(rows)
            or {(r["setting"], r["repeat"], r["policy"]) for r in saved}
            != {(s, str(n), p) for s, n, p in expected}):
        raise ValueError("CSV does not contain exactly the registered rows")
    index = {(r["setting"], str(r["repeat"]), r["policy"]): r for r in rows}
    for row in saved:
        original = index[row["setting"], row["repeat"], row["policy"]]
        if set(row) != set(original) or any(row[k] != ("" if v is None else str(v)) for k, v in original.items()):
            raise ValueError("CSV measurements differ from JSON")
    return data, inputs


def summarize(data):
    groups = {}
    for setting in SETTINGS:
        for policy in POLICIES:
            rows = [r for r in data["runs"] if r["setting"] == setting and r["policy"] == policy]
            groups[setting, policy] = {
                metric: {"mean": statistics.mean(r[metric] for r in rows),
                         "min": min(r[metric] for r in rows), "max": max(r[metric] for r in rows)}
                for metric in METRICS
            }
    contrasts = [("prefix_only_no_aging", "baseline"), ("eviction_only", "baseline"),
                 ("cachewise_no_aging", "prefix_only_no_aging")]
    index = {(r["setting"], r["repeat"], r["policy"]): r for r in data["runs"]}
    effects = []
    for setting in SETTINGS:
        for treatment, control in contrasts:
            for repeat in range(3):
                a, b = index[setting, repeat, treatment], index[setting, repeat, control]
                effects.append({
                    "setting": setting, "repeat": repeat, "treatment": treatment, "control": control,
                    "mean_session_time_change_percent": 100 * (a["mean_session_serving_s"] / b["mean_session_serving_s"] - 1),
                    "treatment_preemptions": a["preemptions"], "control_preemptions": b["preemptions"],
                })
    return groups, effects


def save(fig, name):
    fig.savefig(HERE / f"{name}.pdf", bbox_inches="tight", metadata={"CreationDate": None, "ModDate": None})
    fig.savefig(HERE / f"{name}.png", dpi=230, bbox_inches="tight")
    plt.close(fig)


def decorate(ax):
    ax.grid(axis="y", alpha=.2, linewidth=.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_axisbelow(True)


def observed(ax, x, values, label, color, marker, scale=1, connect=False):
    means = np.array([v["mean"] for v in values]) / scale
    lower = means - np.array([v["min"] for v in values]) / scale
    upper = np.array([v["max"] for v in values]) / scale - means
    return ax.errorbar(x, means, yerr=np.vstack([lower, upper]), color=color, marker=marker,
                       linestyle="-" if connect else "none", linewidth=1.15, markersize=4,
                       capsize=2, elinewidth=.8, label=label)


def serving(groups, effects):
    fig, axes = plt.subplots(1, 2, figsize=(7, 2.85), layout="constrained")
    for policy, name, color, marker in zip(POLICIES, NAMES, COLORS, MARKERS):
        observed(axes[0], [10, 20, 30], [groups[f"a-n{n}", policy]["mean_session_serving_s"] for n in [10, 20, 30]],
                 name, color, marker, connect=True)
    axes[0].set(title="(a) Nested cohort A", xlabel="Concurrent segments, N",
                ylabel="Mean session serving time (s)", xticks=[10, 20, 30], ylim=(0, 2200))
    for offset, scheduler, treatment, control, color in [
        (-.1, "FCFS", "eviction_only", "baseline", COLORS[1]),
        (.1, "Prefix-aware", "cachewise_no_aging", "prefix_only_no_aging", COLORS[3]),
    ]:
        for repeat, marker in enumerate(["o", "s", "^"]):
            values = [next(r["mean_session_time_change_percent"] for r in effects
                           if r["setting"] == setting and r["repeat"] == repeat
                           and r["treatment"] == treatment and r["control"] == control) for setting in SETTINGS]
            axes[1].scatter(np.arange(5) + offset + (repeat - 1) * .035, values,
                            marker=marker, color=color, s=19, linewidths=.5,
                            label=scheduler if repeat == 0 else None)
    axes[1].axhline(0, color="#555555", linewidth=.8, linestyle="--")
    axes[1].set(title="(b) Predictive versus LRU, matched repeats",
                xlabel="Cohort and concurrent segments", ylabel="Change in mean session time (%)",
                xticks=np.arange(5), xticklabels=LABELS, ylim=(-18, 51))
    axes[1].legend(frameon=False, fontsize=7, loc="upper left")
    axes[1].text(.98, .02, "Negative = lower time", transform=axes[1].transAxes,
                 ha="right", va="bottom", fontsize=6.7, color="#444444")
    for ax in axes:
        decorate(ax)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper center", ncol=4, frameon=False,
               fontsize=7, columnspacing=1.2, handlelength=1.5)
    save(fig, "replication-coverage-serving")


def accounting(groups, data):
    fig, axes = plt.subplots(1, 3, figsize=(7, 2.8), layout="constrained")
    panels = [
        ("full_cached_block_evictions", 1000, "(a) Full allocation evictions", "Cached-block eviction events (thousands)"),
        ("reported_uncached_prompt_tokens", 1000000, "(b) Reported uncached usage", "Uncached prompt tokens (millions)"),
        ("request_p99_s", 1, "(c) Per-run P99 request latency", "P99 request latency (s)"),
    ]
    for ax, (metric, scale, title, ylabel) in zip(axes, panels):
        for i, (policy, name, color, marker) in enumerate(zip(POLICIES, NAMES, COLORS, MARKERS)):
            observed(ax, np.arange(5) + (i - 1.5) * .15,
                     [groups[setting, policy][metric] for setting in SETTINGS],
                     name, color, marker, scale=scale)
        ax.set(title=title, ylabel=ylabel, xticks=np.arange(5), xticklabels=LABELS,
               xlabel="Cohort and concurrent segments", xlim=(-.6, 4.6), ylim=(0, None))
        decorate(ax)
    selected = {s["id"]: s for s in data["selection"]["settings"]}
    first_use, = axes[1].plot(np.arange(5), [selected[s]["first_use_prompt_tokens"] / 1000000 for s in SETTINGS],
                 linestyle="none", marker="_", markersize=12, markeredgewidth=1.5,
                 color="#303030", label="First-use prompt tokens")
    axes[1].legend(handles=[first_use],
                   labels=["First-use prompt"], frameon=False, fontsize=6.2,
                   loc="center right", bbox_to_anchor=(1, .75))
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper center", ncol=4, frameon=False,
               fontsize=7, columnspacing=1.2, handlelength=1.5)
    save(fig, "replication-coverage-accounting")


def tables(groups, data):
    table = [r"% Generated by plot_coverage.py from archived numeric evidence.",
             r"\begin{table}[t]", r"  \centering", r"  \small", r"  \setlength{\tabcolsep}{4pt}",
             r"  \begin{tabular}{lrrr}", r"    \toprule",
             r"    Setting & Sources & Requests & Wait sum (s) \\", r"    \midrule"]
    selected = {s["id"]: s for s in data["selection"]["settings"]}
    for setting in SETTINGS:
        s = selected[setting]
        table.append(f"    {s['cohort'].upper()}, $N={s['sessions']}$ & {len(s['source_sessions'])} & {s['requests']} & {s['recorded_wait_sum_s']:.2f} " + r"\\")
    table += [r"    \bottomrule", r"  \end{tabular}",
              r"  \caption{Frozen coverage-study workloads, per policy run. $N$ counts complete segments; sources count distinct source sessions. Wait sums add recorded between-turn delays, which can overlap during replay and are not elapsed times.}",
              r"  \label{tab:replication-coverage-workloads}", r"\end{table}"]
    (HERE / "replication-coverage-workloads.tex").write_text("\n".join(table) + "\n")
    table = [r"% Generated by plot_coverage.py from archived numeric evidence.",
             r"\begin{table*}[t]", r"  \centering", r"  \small", r"  \begin{tabular}{lrrrr}",
             r"    \toprule", r"    & \multicolumn{2}{c}{FCFS} & \multicolumn{2}{c}{Prefix-aware} \\",
             r"    Setting & LRU & Predictive & LRU & Predictive \\", r"    \midrule"]
    for setting in SETTINGS:
        s = selected[setting]
        means = [groups[setting, policy]["mean_session_serving_s"]["mean"] for policy in POLICIES]
        cells = [f"{v:,.2f}" if v != min(means) else r"\textbf{" + f"{v:,.2f}" + "}" for v in means]
        if setting == "a-n20":
            cells[-1] += r"$^{\dagger}$"
        table.append(f"    {s['cohort'].upper()}, $N={s['sessions']}$ & " + " & ".join(cells) + r" \\")
    table += [r"    \bottomrule", r"  \end{tabular}",
              r"  \caption{Coverage-study mean session serving time in seconds, averaged over three matched repeats per cell. Lower is better; prefix-aware queue aging is disabled. $\dagger$Includes the single observed preemption in A, $N=20$, repeat 0. All 60 runs are retained under the declared audit amendment; the original zero-preemption condition was not fully satisfied. Historical measurements in Table~\ref{tab:replication-results} are a separate study.}",
              r"  \label{tab:replication-coverage-results}", r"\end{table*}"]
    (HERE / "replication-coverage-results.tex").write_text("\n".join(table) + "\n")


def main():
    data, inputs = load()
    groups, effects = summarize(data)
    serving(groups, effects)
    accounting(groups, data)
    tables(groups, data)
    with (HERE / "replication-coverage-paired-effects.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(effects[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(effects)
    summary = {
        "status": data["status"], "policy_runs": len(data["runs"]),
        "requests": sum(r["requests"] for r in data["runs"]),
        "reported_preemptions": data["reported_preemptions"],
        "statistics": [{"setting": setting, "policy": policy, "repeats": 3,
                        **groups[setting, policy]} for setting in SETTINGS for policy in POLICIES],
        "effects": [{"setting": setting, "treatment": treatment, "control": control,
                     "ratio_of_means_change_percent": 100 * (groups[setting, treatment]["mean_session_serving_s"]["mean"] /
                                                             groups[setting, control]["mean_session_serving_s"]["mean"] - 1)}
                    for setting in SETTINGS for treatment, control in [
                        ("prefix_only_no_aging", "baseline"), ("eviction_only", "baseline"),
                        ("cachewise_no_aging", "prefix_only_no_aging")]],
        "scope": "Means and observed three-repeat ranges, not confidence intervals. No pooling with the historical study. Usage-derived tokens do not measure all executed or redundant prefill; extra preemption work is unknown.",
    }
    (HERE / "replication-coverage-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    outputs = [HERE / name for name in [
        "replication-coverage-serving.pdf", "replication-coverage-serving.png",
        "replication-coverage-accounting.pdf", "replication-coverage-accounting.png",
        "replication-coverage-workloads.tex", "replication-coverage-results.tex",
        "replication-coverage-paired-effects.csv", "replication-coverage-summary.json",
    ]]
    provenance = {
        "inputs": {str(p.relative_to(ROOT)): sha(p) for p in inputs},
        "script_sha256": sha(Path(__file__)), "matplotlib_version": matplotlib.__version__,
        "numpy_version": np.__version__, "outputs": {p.name: sha(p) for p in outputs},
        "method": "Equal-weight means over three repeats; whiskers show observed minimum and maximum. Matched percentage effects use policy pairs from the same setting and GPU repeat. Repeat markers are circles, squares, triangles. The single preemption is retained. No confidence intervals, exact executed-prefill, or offloading claims are implied.",
    }
    (HERE / "replication-coverage-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print("Verified 60 runs / 6,384 requests; generated two figures, two tables, and numeric provenance.")


if __name__ == "__main__":
    main()
