"""
LangSmith trace viewer for YourCoolingPartner.

Fetches recent agent runs from LangSmith and structures them for the
dashboard UI.  Returns empty data when LangSmith is not configured.
"""

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

load_dotenv()

LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "YourCoolingPartner")

_FETCH_TIMEOUT = 15


def get_recent_traces(limit: int = 20) -> list[dict[str, Any]]:
    """Fetch the most recent root traces from LangSmith.

    Runs inside a thread with *overall* timeout so the HTTP request
    never blocks the server indefinitely.
    """
    if not LANGCHAIN_API_KEY:
        return []

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_do_fetch, limit)
        try:
            return future.result(timeout=_FETCH_TIMEOUT)
        except FuturesTimeout:
            print("[log_viewer] Timed out fetching traces")
            return []
        except Exception as e:
            print(f"[log_viewer] Fetch error: {e}")
            return []


def _do_fetch(limit: int) -> list[dict[str, Any]]:
    """Actual fetch logic run inside a thread."""
    from langsmith import Client

    client = Client(timeout_ms=_FETCH_TIMEOUT * 1000)

    try:
        runs = list(
            client.list_runs(
                project_name=LANGCHAIN_PROJECT,
                is_root=True,
                limit=limit,
            )
        )
    except Exception as e:
        print(f"[log_viewer] Client list_runs error: {e}")
        return []

    traces = []
    for run in runs:
        children = _fetch_child_tree(client, run.id)
        traces.append(_format_run(run, children))

    return traces


def _fetch_child_tree(client, parent_id, depth=0, max_depth=10):
    """Recursively fetch child runs to build a tree.

    Each recursion level is also timed out via ThreadPoolExecutor so a
    single slow sub-query does not hang the whole operation.
    """
    if depth >= max_depth:
        return []

    from langsmith import Client

    if not isinstance(client, Client):
        return []

    # Fetch children inside a thread with a per-level timeout
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(_list_child_runs, client, parent_id)
        try:
            children = fut.result(timeout=min(10, _FETCH_TIMEOUT))
        except FuturesTimeout:
            return []
        except Exception:
            return []

    if not children:
        return []

    result = []
    for child in children:
        grandchildren = _fetch_child_tree(
            client, child.id, depth + 1, max_depth
        )
        result.append(_format_run(child, grandchildren))

    return result


def _list_child_runs(client, parent_id):
    """Thin wrapper so it can be submitted to a thread pool."""
    return list(client.list_runs(parent_run_id=parent_id, limit=100))


def _format_run(run, children: list[dict] | None = None) -> dict[str, Any]:
    """Convert a Run object to a serialisable dict."""
    inputs = _truncate_dict(run.inputs or {})
    outputs = _truncate_dict(run.outputs or {})

    duration_ms = None
    if run.start_time and run.end_time:
        duration_ms = round(
            (run.end_time - run.start_time).total_seconds() * 1000
        )

    return {
        "id": str(run.id),
        "trace_id": str(run.trace_id) if run.trace_id else None,
        "name": run.name,
        "run_type": run.run_type,
        "start_time": run.start_time.isoformat() if run.start_time else None,
        "end_time": run.end_time.isoformat() if run.end_time else None,
        "duration_ms": duration_ms,
        "error": run.error,
        "inputs": inputs,
        "outputs": outputs,
        "prompt_tokens": run.prompt_tokens,
        "completion_tokens": run.completion_tokens,
        "total_tokens": run.total_tokens,
        "status": run.status,
        "children": children or [],
    }


def _truncate_dict(d: dict, max_str_len: int = 500) -> dict:
    """Truncate long string values so the UI doesn't choke."""
    result = {}
    for k, v in d.items():
        if isinstance(v, str) and len(v) > max_str_len:
            result[k] = v[:max_str_len] + "..."
        elif isinstance(v, dict):
            result[k] = _truncate_dict(v, max_str_len)
        elif isinstance(v, list):
            result[k] = (
                [_truncate_dict(i, max_str_len) if isinstance(i, dict) else i
                 for i in v[:50]]
            )
        else:
            result[k] = v
    return result


def is_configured() -> bool:
    return bool(LANGCHAIN_API_KEY)
