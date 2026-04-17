"""Seed the master_cv table from docs/seed/master-cv.json (or template).

Run once after the DB is up. Subsequent edits go through
PUT /api/cv/master from the UI.

    python scripts/seed_master_cv.py
    python scripts/seed_master_cv.py --file path/to/cv.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models.cv import MasterCV
from app.schemas.cv import MasterCVContent


def _find_default_file() -> Path:
    # Repo-relative: jobhunter/docs/seed/master-cv(.template).json
    root = Path(__file__).resolve().parents[2]
    seed_dir = root / "docs" / "seed"
    real = seed_dir / "master-cv.json"
    template = seed_dir / "master-cv.template.json"
    return real if real.exists() else template


def seed(file_path: Path) -> None:
    raw = json.loads(file_path.read_text(encoding="utf-8"))
    # Validate against the schema before committing — a malformed seed should
    # fail loudly, not produce a half-initialized row.
    content = MasterCVContent.model_validate(raw)

    db = SessionLocal()
    try:
        existing = db.query(MasterCV).filter(MasterCV.is_active.is_(True)).first()
        if existing:
            print(f"Active master_cv already exists (id={existing.id}, v{existing.version}) — skipping.")
            print("Use PUT /api/cv/master from the UI to modify.")
            return

        row = MasterCV(
            version=1,
            content=content.model_dump(mode="json"),
            is_active=True,
            source_type="manual",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        print(f"Seeded master_cv id={row.id} v{row.version} from {file_path}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=None)
    args = parser.parse_args()
    path = args.file or _find_default_file()
    if not path.exists():
        raise SystemExit(f"Seed file not found: {path}")
    seed(path)


if __name__ == "__main__":
    main()
