from __future__ import annotations

import os
try:  # Optional dependency in unit-test context
    from celery import Celery as _Celery
    from kombu import Queue
except Exception:  # pragma: no cover
    _Celery = None
    Queue = None


class _StubConf:
    def __init__(self) -> None:
        # Defaults aligned with our expectations/tests
        self.task_acks_late = True
        self.worker_prefetch_multiplier = 1
        self.task_default_queue = "default"
        self.broker_transport_options = {}
        self.task_default_retry_delay = 5
        self.task_time_limit = 300

    def update(self, **kwargs) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class _StubCelery:  # Minimal stand-in when Celery isn't installed
    def __init__(self, name: str, broker: str | None = None, backend: str | None = None) -> None:
        self.name = name
        self.broker = broker
        self.backend = backend
        self.conf = _StubConf()

    def task(self, *_, **__):
        def _decorator(func):
            return func
        return _decorator


def _redis_url() -> str:
    host = os.getenv("REDIS_HOST", "localhost")
    port = os.getenv("REDIS_PORT", "6380")
    db = os.getenv("REDIS_DB", "0")
    return f"redis://{host}:{port}/{db}"


BROKER_URL = _redis_url()
BACKEND_URL = BROKER_URL

CeleryClass = _Celery or _StubCelery
celery_app = CeleryClass("mind", broker=BROKER_URL, backend=BACKEND_URL)

# Define workflow-specific queues for hard workflow separation
# WF1: Receipt workflow (AI1-AI4 pipeline)
# WF2: Credit card invoice workflow (AI6 pipeline, PDF splitting)
if Queue is not None:
    _task_queues = (
        Queue('default', routing_key='default'),
        Queue('wf1', routing_key='wf1.#'),
        Queue('wf2', routing_key='wf2.#'),
    )
else:
    # Stub for testing
    _task_queues = {}

# Basic configuration; can be extended per environment
celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_transport_options={
        "visibility_timeout": 3600,  # 1 hour
    },
    task_default_queue="default",
    task_queues=_task_queues,
    task_routes={
        # Workflow 1: Receipt processing (AI1-AI4)
        'wf1.*': {'queue': 'wf1', 'routing_key': 'wf1.default'},
        # Workflow 2: Credit card invoice processing (AI6, PDF split)
        'wf2.*': {'queue': 'wf2', 'routing_key': 'wf2.default'},
    },
    task_default_retry_delay=5,  # seconds
    task_time_limit=300,  # seconds
)


def get_celery():
    return celery_app
