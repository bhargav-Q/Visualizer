import logging
import time
import functools
import traceback
from contextvars import ContextVar
from typing import Optional, Callable, Any

# ContextVar for tracking dynamic Trace IDs across async execution contexts
current_trace_id: ContextVar[str] = ContextVar("current_trace_id", default="system")

class TraceLogFormatter(logging.Formatter):
    """Custom Log Formatter injecting [TraceID: <id>] into log messages."""
    
    def format(self, record: logging.LogRecord) -> str:
        trace_id = current_trace_id.get("system")
        record.trace_id = trace_id
        return super().format(record)

def get_visualizer_logger(name: str = "visualizer") -> logging.Logger:
    """Returns a configured VisualizerLogger with trace_id formatting."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = TraceLogFormatter(
            fmt="%(asctime)s [%(levelname)s] [TraceID: %(trace_id)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

logger = get_visualizer_logger(__name__)

def trace_stage(stage_name: str):
    """
    Decorator for tracking pipeline stage execution:
    - Logs stage entry and execution duration (ms).
    - Captures and logs explicit error messages and full stack traces if exceptions occur.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio_is_coroutine_function(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                t0 = time.perf_counter()
                trace_id = current_trace_id.get("system")
                logger.info(f"[STAGE_START] Entering stage '{stage_name}' (TraceID: {trace_id})")
                try:
                    result = await func(*args, **kwargs)
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    logger.info(f"[STAGE_COMPLETE] Stage '{stage_name}' completed in {elapsed_ms:.2f}ms")
                    return result
                except Exception as exc:
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    logger.error(f"[STAGE_ERROR] Stage '{stage_name}' failed after {elapsed_ms:.2f}ms: {exc}\n{traceback.format_exc()}")
                    raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                t0 = time.perf_counter()
                trace_id = current_trace_id.get("system")
                logger.info(f"[STAGE_START] Entering stage '{stage_name}' (TraceID: {trace_id})")
                try:
                    result = func(*args, **kwargs)
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    logger.info(f"[STAGE_COMPLETE] Stage '{stage_name}' completed in {elapsed_ms:.2f}ms")
                    return result
                except Exception as exc:
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    logger.error(f"[STAGE_ERROR] Stage '{stage_name}' failed after {elapsed_ms:.2f}ms: {exc}\n{traceback.format_exc()}")
                    raise
            return sync_wrapper
    return decorator

def asyncio_is_coroutine_function(func: Callable[..., Any]) -> bool:
    import inspect
    return inspect.iscoroutinefunction(func)
