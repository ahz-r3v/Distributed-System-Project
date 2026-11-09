"""Check exact eviction semantics on the real BlockPool using CPU objects only."""

import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace


def check(root, output):
    sys.path.insert(0, str(root / "src/vllm-cachewise"))
    sys.path.insert(0, str(root / "part1"))
    from common import atomic_json
    from full_counters import install
    from vllm.v1.core.block_pool import BlockPool
    from vllm.v1.core.kv_cache_utils import BlockHash, make_block_hash_with_group_id

    class Completion:
        def _free_request(self, request):
            return None

        def make_stats(self):
            return None

    output.mkdir(parents=True, exist_ok=False)
    state = install(BlockPool, Completion, output / "probe-full-counters")
    pool = BlockPool(4, enable_caching=True, hash_block_size=16)
    initial = pool.get_new_blocks(2)
    for index, block in enumerate(initial):
        key = make_block_hash_with_group_id(BlockHash(bytes([index + 1]) * 32), 0)
        block.block_hash = key
        pool.cached_block_hash_to_block.insert(key, block)
    pool.free_blocks(initial)
    allocated = pool.get_new_blocks(3)
    assert state["cached_blocks_evicted_for_allocation"] == 2
    assert state["allocated_blocks"] == 5
    fresh = allocated[0]
    key = make_block_hash_with_group_id(BlockHash(b"z" * 32), 0)
    fresh.block_hash = key
    pool.cached_block_hash_to_block.insert(key, fresh)
    pool.evict_blocks({fresh.block_id})
    assert state["cached_blocks_invalidated_elsewhere"] == 1
    Completion()._free_request(SimpleNamespace(request_id="cpu-only-probe"))
    result = {
        "status": "passed", "method": "Real engine BlockPool and synthetic hash metadata; no model or GPU kernels executed.",
        "expected_allocation_evictions": 2, "observed_allocation_evictions": state["cached_blocks_evicted_for_allocation"],
        "expected_other_invalidations": 1, "observed_other_invalidations": state["cached_blocks_invalidated_elsewhere"],
        "allocated_blocks_including_fresh": state["allocated_blocks"],
    }
    atomic_json(output / "counter-probe.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    check(args.root.resolve(), args.output.resolve())
