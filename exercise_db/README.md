# Exercise Database

SQLAlchemy models + Alembic migrations for the Phase 1 exercise schema
(`phase1_schema.sql`), plus a ~50-exercise seed dataset and a couple of
example filter queries.

SQLite for now; the models avoid anything that would block a later move
to Postgres (see the `EXERCISE_DB_URL` note below), except the
`created_at`/`updated_at` `datetime('now')` defaults, which are SQLite
syntax on purpose — that matches the source schema exactly.

## Layout

```
app/
  models.py     # SQLAlchemy models — 1:1 with phase1_schema.sql
  database.py   # engine/session setup
alembic/
  versions/0001_initial_schema.py   # creates all tables/constraints/indexes
seed.py             # wipes + inserts the ~50-exercise dataset
query_examples.py   # a few example filter queries
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# create exercises.sqlite3 with the full schema
alembic upgrade head

# wipe + insert the seed dataset (safe to re-run)
python seed.py

# run the example queries
python query_examples.py
```

By default everything points at `exercises.sqlite3` in this directory.
Override with `EXERCISE_DB_URL` (e.g. `EXERCISE_DB_URL=sqlite:///:memory:`
or, later, a Postgres URL) — both `app/database.py` and
`alembic/env.py` read it.

## Seed dataset

55 exercises, covering:
- all 11 movement patterns (squat, hinge, push/pull horizontal & vertical,
  carry, rotation, anti_rotation, anti_extension, gait)
- all 5 `exercise_type` values (strength, mobility, conditioning,
  plyometric, stability)
- all 6 `tracking_type` values
- both `compound_or_isolation` values
- 15 equipment types (bodyweight through barbell, machine, sled, landmine,
  TRX, foam roller, etc.)
- difficulty levels 1–6
- a handful of `variant_of` relationships (e.g. Front Squat → Back Squat,
  Dumbbell Bench Press → Barbell Bench Press)

## Notes / assumptions

- `seed.py` **wipes** all exercise-related tables before inserting, so it's
  idempotent to re-run during development — don't point it at a database
  with real client-facing data you want to keep.
- `contraindications` is free text as specified in the schema (comma
  separated tags like `lower_back_injury, herniated_disc`), not a
  controlled vocabulary — treat it as a starting point, not medical advice.
- `PRAGMA foreign_keys=ON` is set per-connection via a SQLAlchemy
  `connect` event in `app/database.py`, since SQLite doesn't enforce FKs
  by default and the schema relies on `ON DELETE CASCADE`/`SET NULL`.
