import json
from types import SimpleNamespace

import pytest

from audit import validate_full_counter
import full_counters


def classes():
    class Pool:
        def __init__(self):
            self.actions = []

        def _maybe_evict_cached_block(self, block):
            self.actions.append(block)
            return block == "cached"

        def get_new_blocks(self, blocks):
            if blocks == "raise":
                raise RuntimeError("allocation failed")
            for block in blocks:
                self._maybe_evict_cached_block(block)
            return blocks

    class Scheduler:
        def _free_request(self, request):
            return request.request_id

        def make_stats(self):
            return {"untouched": True}

    return Pool, Scheduler


def test_full_counts_distinguish_successful_evictions_fresh_blocks_and_resets(tmp_path):
    Pool, Scheduler = classes()
    state = full_counters.install(Pool, Scheduler, tmp_path / "counts")
    pool, scheduler = Pool(), Scheduler()
    blocks = ["cached", "fresh", "cached"]
    assert pool.get_new_blocks(blocks) is blocks
    assert pool.actions == blocks
    assert pool._maybe_evict_cached_block("cached") is True
    assert scheduler._free_request(SimpleNamespace(request_id="one")) == "one"
    assert scheduler.make_stats() == {"untouched": True}
    assert state["cached_blocks_evicted_for_allocation"] == 2
    assert state["cached_blocks_invalidated_elsewhere"] == 1
    assert state["allocated_blocks"] == 3
    assert state["finished_requests"] == 1
    validate_full_counter(state, 1)
    files = list(tmp_path.glob("counts-*.json"))
    assert len(files) == 1 and json.loads(files[0].read_text())["finished_requests"] == 1
    assert not list(tmp_path.glob("*.tmp"))
    assert full_counters.install(Pool, Scheduler, tmp_path / "counts") is state


def test_failed_allocation_restores_context_and_does_not_count_nonexistent_blocks(tmp_path):
    Pool, Scheduler = classes()
    state = full_counters.install(Pool, Scheduler, tmp_path / "counts")
    pool = Pool()
    with pytest.raises(RuntimeError):
        pool.get_new_blocks("raise")
    assert pool._maybe_evict_cached_block("cached")
    assert state["allocation_calls"] == 0
    assert state["cached_blocks_evicted_for_allocation"] == 0
    assert state["cached_blocks_invalidated_elsewhere"] == 1


def test_forked_process_gets_fresh_pid_and_counters(tmp_path, monkeypatch):
    Pool, Scheduler = classes()
    state = full_counters.install(Pool, Scheduler, tmp_path / "counts")
    pool = Pool()
    pool.get_new_blocks(["cached"])
    original = state["pid"]
    monkeypatch.setattr(full_counters.os, "getpid", lambda: original + 10000)
    child = Pool()
    assert state["pid"] == original + 10000
    assert state["pool_instances"] == 1 and state["allocated_blocks"] == 0
    assert child.get_new_blocks(["fresh"]) == ["fresh"]


def test_audit_rejects_partial_counter_stream_and_duplicate_finish(tmp_path):
    Pool, Scheduler = classes()
    state = full_counters.install(Pool, Scheduler, tmp_path / "counts")
    Pool().get_new_blocks(["cached"])
    scheduler = Scheduler()
    scheduler._free_request(SimpleNamespace(request_id="one"))
    with pytest.raises(ValueError, match="every completed"):
        validate_full_counter(state, 2)
    scheduler._free_request(SimpleNamespace(request_id="one"))
    with pytest.raises(ValueError, match="every completed"):
        validate_full_counter(state, 1)
