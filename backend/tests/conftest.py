import os
from pathlib import Path


_test_database = Path(__file__).parent / ".pytest-runtime.db"
for suffix in ("", "-shm", "-wal"):
    candidate = Path(f"{_test_database}{suffix}")
    if candidate.exists():
        candidate.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{_test_database.as_posix()}"
