import os
import sys
from pathlib import Path
import pytest

# Make backend/src importable in tests
ROOT = Path(__file__).resolve().parents[1]  # .../backend
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(scope="session")
def base_url():
    # Assuming Nginx proxy on localhost:8008 per docker-compose.yml
    return os.environ.get("MIND_API_BASE", "http://localhost:8008/ai/api")
