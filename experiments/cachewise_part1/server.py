"""Install identical passive counters in the API server and spawned engine."""

import os

from full_counters import install as install_counters
from queue_observer import install as install_queue_observer
from vllm.v1.core.block_pool import BlockPool
from vllm.v1.core.sched.request_queue import PrefixAwareRequestQueue
from vllm.v1.core.sched.scheduler import Scheduler


install_counters(BlockPool, Scheduler, os.environ["CACHEWISE_FULL_COUNTERS"])
install_queue_observer(PrefixAwareRequestQueue, os.environ["CACHEWISE_QUEUE_TRACE"])

if __name__ == "__main__":
    from vllm.entrypoints.cli.main import main

    main()
