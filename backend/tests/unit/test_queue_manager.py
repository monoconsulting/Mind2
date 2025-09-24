import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from importlib import import_module  # noqa: E402

queue_manager = import_module("services.queue_manager")


def test_celery_singleton_and_basic_conf():
    c1 = queue_manager.get_celery()
    c2 = queue_manager.get_celery()
    assert c1 is c2
    assert c1.conf.task_acks_late is True
    assert c1.conf.worker_prefetch_multiplier == 1
    assert c1.conf.task_default_queue == "default"
