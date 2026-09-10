"""Load data/seed_exercises.json into the database.

Idempotent: re-running skips exercises that already exist (matched by slug),
so it's safe to run again after adding a few new entries to the JSON file.

Usage:
    python seed.py                       # uses data/seed_exercises.json
    python seed.py path/to/other.json    # or point at a different file
"""
import json
import sys
from pathlib import Path

from app import crud, models
from app.database import Base, SessionLocal, engine
from app.utils import slugify

DEFAULT_SEED_PATH = Path(__file__).resolve().parent / "data" / "seed_exercises.json"


def seed(seed_path: Path = DEFAULT_SEED_PATH) -> None:
    Base.metadata.create_all(bind=engine)

    entries = json.loads(seed_path.read_text())
    db = SessionLocal()
    created, skipped = 0, 0
    try:
        for entry in entries:
            slug = slugify(entry["name"])
            if db.query(models.Exercise).filter(models.Exercise.slug == slug).first():
                skipped += 1
                print(f"  skip (already exists): {entry['name']}")
                continue

            movement_pattern = crud.get_or_create(db, models.MovementPattern, entry["movement_pattern"])

            exercise = models.Exercise(
                name=entry["name"],
                slug=slug,
                movement_pattern_id=movement_pattern.id,
                unilateral=bool(entry.get("unilateral", False)),
                difficulty=entry.get("difficulty"),
                tracking_type=entry["tracking_type"],
                cues=entry.get("cues"),
                video_url=entry.get("video_url"),
            )
            db.add(exercise)
            db.flush()

            crud.sync_muscles(db, exercise, entry.get("primary_muscles", []), entry.get("secondary_muscles", []))
            crud.sync_equipment(db, exercise, entry.get("equipment", []))
            crud.sync_tags(db, exercise, entry.get("tags", []))

            db.commit()
            created += 1
            print(f"  created: {entry['name']}")
    finally:
        db.close()

    print(f"\nDone. {created} created, {skipped} skipped.")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SEED_PATH
    seed(path)
