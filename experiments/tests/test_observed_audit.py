"""Regression checks for reporting observed preemptions without hiding failures."""

import importlib.util
import json
from pathlib import Path

import pytest


path = Path(__file__).resolve().parents[1] / "audit_cachewise_part1_observed.py"
spec = importlib.util.spec_from_file_location("observed_part1_audit_test", path)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_actual_preemption_is_retained_and_extra_work_remains_unknown():
    assert audit.validate_output_and_preemptions({"output_tokens": 20, "preemptions": 1.0}, 20) == 1
    row = audit.normalize_accounting({
        "computed_prompt_tokens": 100,
        "excess_computed_prompt_tokens": 30,
        "prompt_cache_hit_fraction": .5,
        "preemptions": 1,
    })
    assert row["preemptions"] == 1
    assert row["reported_uncached_prompt_tokens"] == 100
    assert row["reported_uncached_minus_first_use_tokens"] == 30
    assert row["preemption_extra_prefill_tokens"] is None
    assert "computed_prompt_tokens" not in row


@pytest.mark.parametrize("count", [None, -1, .5, float("nan"), float("inf")])
def test_missing_or_invalid_preemption_counts_are_rejected(count):
    with pytest.raises(ValueError, match="preemption counter"):
        audit.validate_output_and_preemptions({"output_tokens": 20, "preemptions": count}, 20)


def test_nonzero_preemption_does_not_waive_output_integrity():
    with pytest.raises(ValueError, match="output lengths"):
        audit.validate_output_and_preemptions({"output_tokens": 19, "preemptions": 1}, 20)


def registered_root(tmp_path):
    (tmp_path / "prepared").mkdir()
    (tmp_path / "part1").mkdir()
    (tmp_path / "results").mkdir()
    protocol = tmp_path / "prepared/protocol.json"
    worker = tmp_path / "part1/audit.py"
    protocol.write_text('{}\n')
    worker.write_text('# unchanged frozen worker\n')
    (tmp_path / "preemption-audit-amendment.json").write_text(json.dumps({
        "original_protocol_sha256": audit.checksum(protocol),
        "original_worker_audit_sha256": audit.checksum(worker),
    }))
    return tmp_path


def test_amendment_refuses_a_changed_registered_worker(tmp_path):
    root = registered_root(tmp_path)
    audit.amendment(root)
    (root / "part1/audit.py").write_text('# modified worker\n')
    with pytest.raises(ValueError, match="worker audit was changed"):
        audit.amendment(root)


def test_amendment_does_not_accept_unrelated_execution_failure(tmp_path):
    root = registered_root(tmp_path)
    (root / "prepared/selection.json").write_text(json.dumps({
        "tasks": [{"task": 0, "setting": "a-n20", "repeat": 0}],
    }))
    (root / "results/task-0-failed.txt").write_text("CUDA out of memory\n")
    with pytest.raises(ValueError, match="Unresolved execution/validation failure"):
        audit.collect(root)
