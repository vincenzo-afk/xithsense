"""pytest configuration.

Integration tests run against an isolated SQLite database and model directory,
built from a slice of the real Cricsheet archive (data/raw/all_json.zip) —
configured before any backend module is imported. They are skipped when the
archive is absent.
"""
import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="xithsense-test-"))
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["MODEL_ARTIFACTS_PATH"] = str(_TMP / "models")
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["ANTHROPIC_API_KEY"] = ""      # never call a real LLM from tests
os.environ["RAZORPAY_KEY_ID"] = ""
os.environ["RAZORPAY_KEY_SECRET"] = ""
os.environ["CRICKETDATA_API_KEY"] = ""    # never spend real API quota from tests
os.environ["GROQ_API_KEY"] = ""
os.environ["LLM_MODEL"] = ""
os.environ["WEB_SEARCH_ENABLED"] = "false"  # no network from tests

import pytest  # noqa: E402

TEST_TMP = _TMP
CRICSHEET_ZIP = Path(__file__).resolve().parents[1] / "data" / "raw" / "all_json.zip"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
