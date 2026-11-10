import os
import tempfile
from pathlib import Path

# Force deterministic, offline extraction and an isolated database before
# any app module is imported.
os.environ["LLM_PROVIDER"] = "mock"
os.environ["DATABASE_PATH"] = str(
    Path(tempfile.mkdtemp(prefix="doc2data-tests-")) / "test.db"
)
