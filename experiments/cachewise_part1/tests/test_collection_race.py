import importlib.util
from pathlib import Path


def test_last_job_finishing_during_scheduler_query_rereads_completion():
    path = Path(__file__).resolve().parents[2] / "collect_cachewise_part1.py"
    if not path.is_file():
        path = Path(__file__).resolve().parents[2] / "control/collect_cachewise_part1.py"
    spec = importlib.util.spec_from_file_location("collect_part1_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    state = {"finished": False, "reads": 0}

    def ready():
        state["reads"] += 1
        return state["finished"]

    def scheduler_query():
        state["finished"] = True
        return ""

    assert module.completion_poll(ready, scheduler_query) == (True, "")
    assert state["reads"] == 2
