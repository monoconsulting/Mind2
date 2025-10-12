from __future__ import annotations

import time
from functools import wraps
from typing import Callable

from prometheus_client import Counter, Summary, generate_latest, CONTENT_TYPE_LATEST
from flask import Response, request

REQUEST_COUNT = Counter(
    "mind_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Summary(
    "mind_api_request_latency_seconds",
    "API request latency",
    ["endpoint"],
)

TASK_COUNT = Counter(
    "mind_task_executions_total",
    "Total Celery task executions",
    ["task", "status"],
)
TASK_LATENCY = Summary(
    "mind_task_latency_seconds",
    "Celery task latency",
    ["task"],
)

# Invoice reconciliation metrics
INVOICE_MATCH_COUNT = Counter(
    "mind_invoice_matches_total",
    "Invoice line match decisions",
    ["decision"],  # matched|rejected|confirmed|unmatched
)

INVOICE_STATE_ASSERTIONS = Counter(
    "mind_invoice_state_assertions_total",
    "Illegal invoice lifecycle transitions detected",
    ["entity", "from_state", "to_state"],
)


def metrics_endpoint() -> Response:
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


def track_request(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        endpoint = request.path
        start = time.time()
        status_code = "200"
        try:
            resp = func(*args, **kwargs)
            status_code = str(getattr(resp, "status_code", 200))
            return resp
        finally:
            dur = time.time() - start
            REQUEST_LATENCY.labels(endpoint=endpoint).observe(dur)
            REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, status=status_code).inc()
    return wrapper


def track_task(task_name: str):
    def _decorator(func: Callable):
        @wraps(func)
        def _wrap(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                TASK_COUNT.labels(task=task_name, status="success").inc()
                return result
            except Exception:
                TASK_COUNT.labels(task=task_name, status="error").inc()
                raise
            finally:
                TASK_LATENCY.labels(task=task_name).observe(time.time() - start)
        return _wrap
    return _decorator


def record_invoice_decision(decision: str) -> None:
    try:
        INVOICE_MATCH_COUNT.labels(decision=decision).inc()
    except Exception:
        pass


def record_invoice_state_assertion(entity: str, from_state: str | None, to_state: str) -> None:
    try:
        INVOICE_STATE_ASSERTIONS.labels(
            entity=entity,
            from_state=(from_state or "missing"),
            to_state=to_state,
        ).inc()
    except Exception:
        pass
