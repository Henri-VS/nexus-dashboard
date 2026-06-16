import os
import tempfile

# Set required env vars before any app module is imported.
# settings = Settings() is a module-level singleton — env vars must be present at import time.
_tmpdir = tempfile.mkdtemp()
os.environ.setdefault("NEXUS_SECRET_KEY", "test-secret-key-for-pytest-use")
os.environ.setdefault("DB_PATH", os.path.join(_tmpdir, "test.db"))
os.environ.setdefault("NEXUS_DATA_DIR", _tmpdir)

import pytest
from fastapi.testclient import TestClient
from app.main import app

TEST_KEY = os.environ["NEXUS_SECRET_KEY"]
AUTH = {"Authorization": f"Bearer {TEST_KEY}"}


@pytest.fixture(scope="session")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
