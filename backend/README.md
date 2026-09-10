# PT Hub — Backend (Phase 1: Exercise Database)

SQLite + SQLAlchemy + FastAPI, per `PROJECT_SPEC.md`. This covers **Phase 1
only** — the exercise database (movement patterns, muscle groups, equipment,
tags, exercises). Phase 2 (workout builder) and Phase 3 (program builder)
tables from `schema.sql` are not modeled yet.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Seed the database

```bash
python seed.py                       # loads data/seed_exercises.json into ./pt_hub.db
```

Idempotent — re-running skips exercises that already exist (matched by
slug), so it's safe to run again after adding more entries to the JSON.

## Run the API

```bash
uvicorn app.main:app --reload
```

Docs at `http://127.0.0.1:8000/docs`.

## Run tests

```bash
pytest
```

## Endpoints

Reference tables (read-only, mostly to power filter UIs later):
- `GET /movement-patterns`
- `GET /muscle-groups`
- `GET /equipment`
- `GET /tags`

Exercises:
- `GET /exercises` — filter and list. Query params:
  - `movement_pattern` (repeatable) — match any of these pattern names
  - `muscle_group` (repeatable), `muscle_role` (`primary`|`secondary`) — restrict to that role
  - `equipment` (repeatable), `equipment_mode` (`any` default, or `subset`)
    - `any`: exercise uses at least one of the listed equipment
    - `subset`: exercise needs nothing beyond what's listed — e.g.
      `equipment=Dumbbell&equipment_mode=subset` = "what can I do with only dumbbells"
  - `tag` (repeatable) — match any of these tags
  - `difficulty` — `beginner`|`intermediate`|`advanced`
  - `include_inactive` — include soft-deleted exercises (default false)
  - `limit`, `offset` — pagination
  - All filter types combine with AND; values within a repeated param combine with OR.
- `GET /exercises/{identifier}` — fetch by numeric id or by slug, with all relations loaded.
- `POST /exercises` — create. Body accepts names (not ids) for
  `movement_pattern`, `primary_muscles`, `secondary_muscles`, `equipment`,
  `tags` — any that don't exist yet are created (get-or-create), same as the
  seed script. `slug` is auto-generated from `name` if omitted.
- `PATCH /exercises/{id}` — partial update. Only fields present in the body
  are changed. Passing `equipment`/`tags`/`primary_muscles`/`secondary_muscles`
  replaces that whole list.
- `POST /exercises/{id}/deactivate` — soft delete (`is_active = false`).
  Exercises are **never** hard-deleted — Phase 2's `workout_exercises` will
  reference these rows by id.
- `POST /exercises/{id}/reactivate` — undo a deactivate.

### Example: the spec's "done when" query

> show me all beginner-friendly hinge exercises using only dumbbells

```
GET /exercises?movement_pattern=Hinge&difficulty=beginner&equipment=Dumbbell&equipment_mode=subset
```

(The 30-exercise starter seed happens to have no *beginner* hinge exercise
that uses only dumbbells — try dropping `difficulty` or check
`equipment_mode=any` to see what's there.)

## Notes on the schema mapping

- `exercise_muscles` has an extra `role` column (`primary`/`secondary`), so
  it's modeled as a proper association object (`ExerciseMuscle`) rather than
  a bare secondary table, and exposed on `Exercise.muscles`.
- `exercise_equipment` / `exercise_tags` have no extra columns, so they're
  plain SQLAlchemy `secondary=` many-to-many tables.
- SQLite doesn't enforce foreign keys (or `ON DELETE CASCADE`) by default —
  `PRAGMA foreign_keys=ON` is set on every connection in `app/database.py`.
- `DATABASE_URL` env var overrides the default `sqlite:///./pt_hub.db` if
  you want to point this at Postgres later; the models are plain SQLAlchemy
  so that move should be low-friction.
