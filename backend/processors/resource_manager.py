import os
import gc
import logging
import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Calculate system CPU cores safely: Core count - 1 (minimum 2 workers)
CPU_CORES = os.cpu_count() or 4
MAX_WORKERS = max(2, CPU_CORES - 1)

logger.info(f"Initialized Resource Manager: CPU Cores={CPU_CORES}, Max Extraction Workers={MAX_WORKERS}")

# Global asyncio Semaphore to limit concurrent heavy extraction tasks across HTTP requests
CONCURRENCY_SEMAPHORE = asyncio.Semaphore(MAX_WORKERS)

def get_max_workers() -> int:
    return MAX_WORKERS

def force_garbage_collection():
    """Forces immediate garbage collection to release uncompressed pixmap RAM buffers."""
    gc.collect()
