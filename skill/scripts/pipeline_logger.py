"""Lightweight pipeline logger. Every script imports this.

Logs to both stdout (always) and Convex pipelineLogs (when available).
Fire-and-forget: logging failures never crash the pipeline.
"""
import time
import sys

_task_id = None
_start_times = {}
_convex_available = None


def init(task_id: str):
    """Set task ID for all subsequent log calls."""
    global _task_id
    _task_id = task_id


def _try_convex_log(phase: str, message: str, level: str, metadata: dict = None):
    """Attempt to log to Convex. Silent failure.

    Handles the case where convex_client.py calls sys.exit(1) at import
    when .env is missing — we catch SystemExit and disable Convex logging.
    """
    global _convex_available
    if _convex_available is False or not _task_id:
        return
    try:
        from convex_client import log_pipeline_event
        log_pipeline_event(_task_id, phase, message, level=level, metadata=metadata)
        _convex_available = True
    except (Exception, SystemExit):
        _convex_available = False


def log(phase: str, message: str, level: str = "info", metadata: dict = None):
    """Log to Convex AND stdout."""
    prefix = {"info": "[INFO]", "warn": "[WARN]", "error": "[ERROR]"}
    ts = time.strftime("%H:%M:%S")
    print(f"  {ts} {prefix.get(level, '[INFO]')} [{phase}] {message}")
    _try_convex_log(phase, message, level, metadata)


def start_timer(phase: str):
    """Start a phase timer."""
    _start_times[phase] = time.time()


def end_timer(phase: str) -> int:
    """End a phase timer, return duration in ms."""
    start = _start_times.pop(phase, time.time())
    return int((time.time() - start) * 1000)
