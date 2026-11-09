"""Observe actual cache removals without changing allocation or eviction choices.

The engine's successful hash-removal result defines an eviction. Sampled block
lifetime callbacks are deliberately not used as a full eviction count.
"""

from functools import wraps
import os
from pathlib import Path
import time

from common import atomic_json


def install(block_pool_class, scheduler_class, output_prefix, clock=time.monotonic):
    if getattr(block_pool_class, "_part1_full_counter_installation", None):
        return block_pool_class._part1_full_counter_installation
    state = {
        "version": 1,
        "pid": os.getpid(),
        "pool_instances": 0,
        "allocation_calls": 0,
        "allocated_blocks": 0,
        "eviction_checks": 0,
        "cached_blocks_evicted_for_allocation": 0,
        "cached_blocks_invalidated_elsewhere": 0,
        "finished_requests": 0,
        "duplicate_finish_callbacks": 0,
        "snapshot_writes": 0,
    }
    depth = 0
    last_write = -float("inf")
    finished = set()
    destination = Path(f"{output_prefix}-{os.getpid()}.json")

    def ensure_process():
        nonlocal depth, last_write, destination
        pid = os.getpid()
        if state["pid"] != pid:
            for key in state:
                if key not in {"version", "pid"}:
                    state[key] = 0
            state["pid"] = pid
            depth = 0
            last_write = -float("inf")
            finished.clear()
            destination = Path(f"{output_prefix}-{pid}.json")

    def flush(force=False):
        nonlocal last_write
        ensure_process()
        now = clock()
        if force or now - last_write >= 1:
            state["snapshot_writes"] += 1
            atomic_json(destination, {**state, "observed_at_unix": time.time()})
            last_write = now

    original_init = block_pool_class.__init__
    original_allocate = block_pool_class.get_new_blocks
    original_evict = block_pool_class._maybe_evict_cached_block
    original_finish = scheduler_class._free_request
    original_stats = scheduler_class.make_stats

    @wraps(original_init)
    def initialize(self, *args, **kwargs):
        ensure_process()
        original_init(self, *args, **kwargs)
        state["pool_instances"] += 1
        flush(force=True)

    @wraps(original_allocate)
    def allocate(self, *args, **kwargs):
        nonlocal depth
        depth += 1
        try:
            blocks = original_allocate(self, *args, **kwargs)
        finally:
            depth -= 1
        state["allocation_calls"] += 1
        state["allocated_blocks"] += len(blocks)
        return blocks

    @wraps(original_evict)
    def evict(self, *args, **kwargs):
        result = original_evict(self, *args, **kwargs)
        state["eviction_checks"] += 1
        if result:
            key = ("cached_blocks_evicted_for_allocation" if depth
                   else "cached_blocks_invalidated_elsewhere")
            state[key] += 1
        return result

    @wraps(original_finish)
    def finish(self, request, *args, **kwargs):
        result = original_finish(self, request, *args, **kwargs)
        request_id = request.request_id
        if request_id in finished:
            state["duplicate_finish_callbacks"] += 1
        else:
            finished.add(request_id)
            state["finished_requests"] += 1
        flush(force=True)
        return result

    @wraps(original_stats)
    def stats(self, *args, **kwargs):
        result = original_stats(self, *args, **kwargs)
        flush()
        return result

    block_pool_class.__init__ = initialize
    block_pool_class.get_new_blocks = allocate
    block_pool_class._maybe_evict_cached_block = evict
    scheduler_class._free_request = finish
    scheduler_class.make_stats = stats
    block_pool_class._part1_full_counter_installation = state
    return state
