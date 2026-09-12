# Exercise Database

SQLAlchemy models + Alembic migrations for the exercise database:
Phase 1 (`phase1_schema.sql`) — exercises + lookups — and Phase 2
(`phase2_schema.sql`) — the workout builder (workouts, blocks, block
exercises, prescribed sets). Includes a seed dataset (exercises + example
workouts) and example filter/query functions.

SQLite for now; the models avoid anything that would block a later move
to Postgres (see the `EXERCISE_DB_URL` note below), except the
`created_at`/`updated_at` `datetime('now')` defaults, which are SQLite
syntax on purpose — that matches the source schema exactly.

## Layout

```
app/
  models.py     # SQLAlchemy models — 1:1 with phase1_schema.sql + phase2_schema.sql
  database.py   # engine/session setup
alembic/
  versions/0001_initial_schema.py    # Phase 1: exercises + lookups
  versions/0002_workout_builder.py   # Phase 2: workouts/blocks/block_exercises/prescribed_sets
seed.py             # wipes + inserts exercises and example workouts
query_examples.py   # example filter queries + workout JSON/reverse-lookup helpers
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# create exercises.sqlite3 with the full schema (Phase 1 + Phase 2)
alembic upgrade head

# wipe + insert exercises and example workouts (safe to re-run)
python seed.py

# run the example queries
python query_examples.py
```

By default everything points at `exercises.sqlite3` in this directory.
Override with `EXERCISE_DB_URL` (e.g. `EXERCISE_DB_URL=sqlite:///:memory:`
or, later, a Postgres URL) — both `app/database.py` and
`alembic/env.py` read it.

## Seed dataset

**Exercises** — 55 exercises, covering:
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

**Workouts** — 5 example workouts built from the seeded exercises, covering
every `block_type` except `triset` / `for_time`:
- **Squat Strength Day** — pure `straight_set` blocks (main lift + accessories)
- **Upper Body Push-Pull Superset** — one `superset` block (bench press +
  row, paired sets)
- **Full Body Circuit** — one `circuit` block, 4 exercises, 4 fixed rounds
- **EMOM Conditioning** — one `emom` block, 10-minute cap, alternating
  exercises
- **AMRAP Finisher** — one `amrap` block, 8-minute cap, 3-exercise round

## Query examples (`query_examples.py`)

- `beginner_hinge_with_dumbbells`, `bodyweight_only_by_pattern`,
  `exercises_targeting_muscle_as_primary`, `variants_of` — Phase 1 filters.
- `get_compound_exercises_by_pattern(session, pattern)` — the guardrail
  query for "find a main-lift substitute": pairs `movement_pattern` with
  `compound_or_isolation == 'compound'` so isolation accessories (e.g.
  Machine Leg Extension under `squat`, Machine Leg Curl under `hinge`)
  never surface as substitutes for the lift itself. `main()` prints a
  side-by-side count showing exactly what that filter excludes.
- `build_workout_dict` / `build_workout_json(session, workout_id)` — the
  full nested object: workout → blocks (by `order_index`) → block
  exercises (by `order_index`) → prescribed sets (by `set_number`).
- `workouts_using_exercise(session, exercise_id)` — reverse lookup: every
  workout that uses a given exercise in any block.

Note: the Phase 2 handoff prompt referred to a `test_queries.py` runner
that doesn't exist in this repo — Phase 1 already put both the reusable
query functions and their `main()` demo in `query_examples.py`, so Phase 2
extends that same file rather than starting a second, parallel one. Say
so if you actually want a separate `test_queries.py`.

## Notes / assumptions

- `seed.py` **wipes** all exercise and workout tables before inserting, so
  it's idempotent to re-run during development — don't point it at a
  database with real client-facing data you want to keep. Workout tables
  are wiped before exercise tables since `workout_block_exercises.exercise_id`
  has no `ON DELETE` clause.
- `contraindications` is free text as specified in the schema (comma
  separated tags like `lower_back_injury, herniated_disc`), not a
  controlled vocabulary — treat it as a starting point, not medical advice.
- `PRAGMA foreign_keys=ON` is set per-connection via a SQLAlchemy
  `connect` event in `app/database.py`, since SQLite doesn't enforce FKs
  by default and the schema relies on `ON DELETE CASCADE`/`SET NULL`.
- `prescribed_sets.load_value` uses SQLAlchemy's `REAL` type to match the
  schema's `REAL` column exactly (rather than the equivalent but
  differently-rendered generic `Float`).
- In the EMOM/circuit/AMRAP seed data, `set_number` tracks "how many times
  has this exercise appeared" (round 1, 2, 3...) per the schema comment
  ("set_number doubles as round number... depending on block_type"), not
  a shared absolute clock across exercises in the same block.
