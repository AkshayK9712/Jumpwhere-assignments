"""Run from the project root:  python scripts/seed.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.db.seed import main  # noqa: E402

if __name__ == "__main__":
    main()
