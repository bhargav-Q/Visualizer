import os
import gc
import logging
import asyncio
import concurrent.futures
from typing import List, Generator, Any

logger = logging.getLogger(__name__)

# Calculate CPU Cores - 1 (Minimum 1, Maximum CPU Cores - 1)
TOTAL_CORES = os.cpu_count() or 4
MAX_WORKERS = max(1, TOTAL_CORES - 1)

logger.info(f"Initialized Resource Manager: System Cores={TOTAL_CORES}, Max OCR Workers={MAX_WORKERS}")

# Global shared Bounded ThreadPoolExecutor for heavy CPU/OCR tasks
_GLOBAL_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=MAX_WORKERS,
    thread_name_prefix="VisualizerWorker"
)

# Global Asyncio Semaphore to throttle concurrent HTTP requests to max worker pool
_REQUEST_SEMAPHORE = asyncio.Semaphore(MAX_WORKERS)

def get_global_executor() -> concurrent.futures.ThreadPoolExecutor:
    """Returns the system-wide CPU-bounded worker pool."""
    return _GLOBAL_EXECUTOR

def get_request_semaphore() -> asyncio.Semaphore:
    """Returns the global asyncio semaphore for request throttling."""
    return _REQUEST_SEMAPHORE

def chunk_list(items: List[Any], chunk_size: int = 5) -> Generator[List[Any], None, None]:
    """
    Yields successive n-sized chunks from a list.
    Processes heavy multi-page documents in controlled batches to prevent RAM exhaustion.
    """
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]

def collect_garbage():
    """Forces garbage collection to release uncompressed pixmap bitmap memory."""
    gc.collect()

def get_resource_stats() -> dict:
    """Returns current system core count, max workers, and active thread pool state."""
    return {
        "total_cores": TOTAL_CORES,
        "max_workers": MAX_WORKERS,
        "executor_threads": len(_GLOBAL_EXECUTOR._threads)
    }
