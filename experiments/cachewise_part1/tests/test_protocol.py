import copy
import json
from pathlib import Path
import shlex

import pytest

from common import first_use_tokens
from prepare import build, exclusion_reasons


def protocol():
    return json.loads((Path(__file__).parents[1] / "protocol.json").read_text())


def session(source, index=0, wait=1):
    return {"id": f"{source}-{index}", "source_session": source,
            "turns": [{"prompt_tokens": 1000, "output_tokens": 5, "delay_after_s": wait},
                      {"prompt_tokens": 1100, "output_tokens": 7, "delay_after_s": 0}]}


def test_selection_is_disjoint_nested_and_preserves_complete_segments():
    sessions = [session(f"s{i}", j) for i in range(45) for j in range(3)]
    workload = {"training_sessions": ["train"], "sessions": [*sessions, session("train")]}
    saved = copy.deepcopy(workload)
    data, selection = build(workload, protocol(), {"s1", "s2"})
    assert workload == saved
    assert selection["full_runs"] == 60
    assert data["a-n10"]["sessions"] == data["a-n30"]["sessions"][:10]
    assert data["a-n20"]["sessions"] == data["a-n30"]["sessions"][:20]
    groups = {k: set(v) for k, v in selection["source_groups"].items()}
    assert not groups["a"] & groups["b"] and not groups["b"] & groups["c"]
    assert not groups["a"] & groups["c"]
    assert not {"s1", "s2", "train"} & (groups["b"] | groups["c"])
    assert all(s in sessions for x in data.values() for s in x["sessions"])
    assert data == build(workload, protocol(), {"s1", "s2"})[0]


def test_wait_budget_excludes_whole_segment_without_clipping():
    long = session("s", wait=178164)
    saved = copy.deepcopy(long)
    assert "recorded_wait_budget" in exclusion_reasons(long, protocol()["selection"], set())
    assert long == saved


def test_source_level_training_exclusion_and_insufficient_sources_fail_closed():
    assert "training_source" in exclusion_reasons(session("train"), protocol()["selection"], {"train"})
    with pytest.raises(ValueError, match="twenty"):
        build({"training_sessions": [], "sessions": [session("one")]}, protocol(), set())


def test_first_use_accounting_excludes_repeated_prefix_and_keeps_output():
    assert first_use_tokens([session("one")]) == {
        "first_use_prompt_tokens": 1095, "output_tokens": 12,
        "useful_tokens": 1107, "transitions": 1,
    }
    bad = session("one")
    bad["turns"][1]["prompt_tokens"] = 900
    with pytest.raises(ValueError, match="Context shrink"):
        first_use_tokens([bad])


def test_gpu_scripts_request_one_node_and_one_gpu_not_a_required_host_list():
    root = Path(__file__).parents[1]
    for name in ["smoke.slurm", "array.slurm"]:
        directives = [line.removeprefix("#SBATCH ") for line in (root / name).read_text().splitlines()
                      if line.startswith("#SBATCH ")]
        options = [word for line in directives for word in shlex.split(line)]
        assert "--nodes=1" in options and "--ntasks=1" in options
        assert "--gres=gpu:nvidia_rtx_pro_6000_blackwell:1" in options
        assert not any(word.startswith("--nodelist") for word in options)
