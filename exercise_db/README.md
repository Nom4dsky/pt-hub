# Exercise Database

SQLAlchemy models + Alembic migrations for the exercise database:
Phase 1 (`phase1_schema.sql`) — exercises + lookups; Phase 2
(`phase2_schema.sql`) — the workout builder (workouts, blocks, block
exercises, prescribed sets); Phase 3 (`phase3_schema.sql`) — the program
builder (reusable program templates, cloned into independently-editable
client assignments, with lightweight actuals tracking). Includes a seed
dataset and example filter/query functions for all three phases, plus
(Phase 4a) a FastAPI + vanilla-JS web UI for managing the exercise
database itself — see **Web UI** below.

SQLite for now; the models avoid anything that would block a later move
to Postgres (see the `EXERCISE_DB_URL` note below), except the
`created_at`/`updated_at` `datetime('now')` defaults, which are SQLite
syntax on purpose — that matches the source schema exactly.

## Layout

```
app/
  models.py     # SQLAlchemy models — 1:1 with phase1/2/3_schema.sql
  database.py   # engine/session setup
  schemas.py    # Pydantic request/response schemas for the API (Phase 4a)
  crud.py       # query building + create/update/delete logic for the API (Phase 4a)
  deps.py       # FastAPI DB-session dependency (Phase 4a)
  main.py       # FastAPI app — run this to serve the web UI (Phase 4a)
  routers/      # one router per resource: exercises, movement_patterns, muscles, equipment
  static/       # the web UI itself — index.html + app.js + style.css, no build step
alembic/
  versions/0001_initial_schema.py    # Phase 1: exercises + lookups
  versions/0002_workout_builder.py   # Phase 2: workouts/blocks/block_exercises/prescribed_sets
  versions/0003_program_builder.py   # Phase 3: programs/assignments/session_logs/logged_sets
seed.py             # wipes + inserts exercises, example workouts, and one program + assignment
query_examples.py   # example filter queries + workout/program JSON + reverse-lookup helpers
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# create exercises.sqlite3 with the full schema (Phase 1 + 2 + 3)
alembic upgrade head

# wipe + insert exercises, example workouts, and the program/assignment (safe to re-run)
python seed.py

# run the example queries
python query_examples.py
```

By default everything points at `exercises.sqlite3` in this directory.
Override with `EXERCISE_DB_URL` (e.g. `EXERCISE_DB_URL=sqlite:///:memory:`
or, later, a Postgres URL) — both `app/database.py` and
`alembic/env.py` read it.

## Web UI (Phase 4a — exercise database management)

A FastAPI backend + plain HTML/JS frontend for managing the exercise
database directly, instead of editing `seed.py` by hand. **Scope: exercise
CRUD only** — workouts, programs, and session logging (Phases 2-3) have no
UI yet; that's a later phase.

### Run it

```bash
cd exercise_db          # if you aren't already here
source .venv/bin/activate
alembic upgrade head    # if you haven't already
python seed.py          # if the DB is empty — the UI needs lookup data to populate its dropdowns
uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000/** in a browser (phone or laptop —
the layout is responsive). Interactive API docs are at
http://127.0.0.1:8000/docs if you want to poke the endpoints directly.

### What's there

- **Browse** (landing page) — filter by movement pattern, muscle,
  equipment, exercise type, compound/isolation, difficulty range, and
  name search, all combinable. Click a row to edit it. The results table
  scrolls horizontally on narrow screens rather than wrapping (swipe to
  see Difficulty/Type columns on a phone) — confirmed working in a
  420px-wide browser session, screenshots below.
- **Add / Edit** — one form for both. Muscles and equipment are added via
  a picker + "Add" button that appends a removable chip (native
  multi-select listboxes are unusable on touch, so this replaces them);
  "Variant of" is a custom searchable dropdown rather than `<datalist>`,
  since iOS Safari's `<datalist>` support is unreliable. The difficulty
  selector shows the full 1-6 rubric as inline help beneath it. Enum
  fields (exercise type, tracking type, compound/isolation) are
  `<select>`/radio inputs with only valid options, so the CHECK
  constraints can't be violated from the UI; name and movement-pattern
  presence and the 1-6 difficulty range are checked in JS before
  submitting, and the same rules are enforced again server-side.
- **Manage Lookups** — tabbed (Movement Patterns / Muscles / Equipment),
  each an inline-editable list with add/edit/delete. Deleting any lookup
  value, or an exercise itself, is blocked with a clear message (a count
  of referencing exercises, or workout blocks for an exercise) rather
  than failing with a raw database error or silently orphaning data.

Verified end-to-end with a scripted headless-browser pass (Playwright) at
a phone-width viewport: load → filter → open an existing exercise → add a
new one → confirm it appears in the list → Manage Lookups tabs → a
blocked delete showing its error message. No unexpected console errors
or failed requests in that pass.

### API endpoints

```
GET/POST   /api/exercises            filters: movement_pattern_id, muscle_id, equipment_id,
                                      exercise_type, difficulty_min, difficulty_max,
                                      compound_or_isolation, search
GET        /api/exercises/options    minimal {id, name} list, for the "variant of" picker
GET/PUT/DELETE /api/exercises/{id}
GET/POST/PUT/DELETE /api/movement-patterns[/{id}]
GET/POST/PUT/DELETE /api/muscles[/{id}]
GET/POST/PUT/DELETE /api/equipment[/{id}]
```

`POST`/`PUT` on `/api/exercises` take muscles/equipment as nested lists
(`muscles: [{muscle_id, role}]`, `equipment: [{equipment_id, is_required}]`)
and replace the exercise's existing links wholesale on each save — same
delete-then-reinsert pattern `seed.py` uses.

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

**Programs** — one template, **12-Week HYROX Prep** (`duration_weeks=12`),
with 5 representative weeks seeded (not all 12 — see the comment on
`PROGRAMS` in `seed.py`):
- week 1: `accumulation`, 4 training days
- week 2: `phase_label=NULL` (not every week needs one), 3 days
- week 3: `accumulation`, 5 days
- week 4: `intensification`, 3 days
- week 5: `deload`, 2 days

Each day links to one of the 5 seeded Phase 2 workouts via
`program_day_workouts`. One **assignment** clones this template for a mock
client ("Alex Rivera") via `clone_program_to_assignment` (see below), then
has week 4 / day 3's workout swapped from AMRAP Finisher to Full Body
Circuit *on the clone only* — proving the clone is independently editable.
One **session log** (week 1 / day 1, the Squat Strength Day) has 4
`logged_sets` against its 4 prescribed sets: two hit as planned, one
pushed slightly past prescription, and one where a rep was missed on the
final top set.

## Query examples (`query_examples.py`)

**Phase 1:**
- `beginner_hinge_with_dumbbells`, `bodyweight_only_by_pattern`,
  `exercises_targeting_muscle_as_primary`, `variants_of` — basic filters.
- `get_compound_exercises_by_pattern(session, pattern)` — the guardrail
  query for "find a main-lift substitute": pairs `movement_pattern` with
  `compound_or_isolation == 'compound'` so isolation accessories (e.g.
  Machine Leg Extension under `squat`, Machine Leg Curl under `hinge`)
  never surface as substitutes for the lift itself. `main()` prints a
  side-by-side count showing exactly what that filter excludes.

**Phase 2:**
- `build_workout_dict` / `build_workout_json(session, workout_id)` — the
  full nested object: workout → blocks (by `order_index`) → block
  exercises (by `order_index`) → prescribed sets (by `set_number`).
- `workouts_using_exercise(session, exercise_id)` — reverse lookup: every
  workout that uses a given exercise in any block.

**Phase 3:**
- `clone_program_to_assignment(session, program_id, client_name, start_date, notes=None)`
  — clones a `programs` template's full week → day → workout structure
  into new `assigned_*` rows. After this call the assignment is physically
  separate data; editing it never touches the template or any other
  assignment. Computes each assigned day's `scheduled_date` as consecutive
  calendar days from `start_date` (a modeling choice — the schema doesn't
  specify a cadence; see the function's docstring).
- `build_assignment_dict` / `build_assignment_json(session, program_assignment_id)`
  — the full nested view: assignment → weeks (by `week_number`) → days (by
  `day_number`) → workouts (by `order_index`).
- `compare_prescribed_vs_actual(session, session_log_id)` — planned vs.
  actual for one completed session, joining `logged_sets` back to
  `prescribed_sets` via `(workout_block_exercise_id, set_number)` (the
  natural key `prescribed_sets` is uniquely constrained on) rather than
  via `logged_sets.prescribed_set_id`, per the brief — see the function's
  docstring for why that's more robust.

`main()` runs and prints all of the above against the seeded data,
including cloning a *second*, throwaway assignment on the fly (guarded so
re-running the script doesn't pile up duplicates) to prove the clone
function works standalone and doesn't mutate the template.

Note: the Phase 2 and Phase 3 handoff prompts both referred to a
`test_queries.py` runner that doesn't exist in this repo — Phase 1 already
put both the reusable query functions and their `main()` demo in
`query_examples.py`, so Phase 2 and 3 both extended that same file rather
than starting a second, parallel one. Say so if you actually want a
separate `test_queries.py`.

## Known follow-up (flagged, not built)

`program_assignments.client_name` is a plain `TEXT` column, not a foreign
key — there's no `clients` table yet. Per the brief, this phase
deliberately does not build one; `client_name` is a placeholder that
should become a `client_id` FK once that table exists. `seed.py` and
`query_examples.py` both use free-text client names for the same reason
(marked `TODO(clients table)` in `app/models.py`).

## Notes / assumptions

- `seed.py` **wipes** all exercise, workout, and program tables before
  inserting, so it's idempotent to re-run during development — don't
  point it at a database with real client-facing data you want to keep.
  Program tables are wiped before workout tables, which are wiped before
  exercise tables, since none of `program_day_workouts.workout_id`,
  `assigned_day_workouts.workout_id`, `logged_sets.workout_block_exercise_id`,
  or `workout_block_exercises.exercise_id` have an `ON DELETE` clause.
- `contraindications` is free text as specified in the schema (comma
  separated tags like `lower_back_injury, herniated_disc`), not a
  controlled vocabulary — treat it as a starting point, not medical advice.
- `PRAGMA foreign_keys=ON` is set per-connection via a SQLAlchemy
  `connect` event in `app/database.py`, since SQLite doesn't enforce FKs
  by default and the schema relies on `ON DELETE CASCADE`/`SET NULL`.
- `prescribed_sets.load_value` and `logged_sets.actual_load_value` use
  SQLAlchemy's `REAL` type to match the schema's `REAL` columns exactly
  (rather than the equivalent but differently-rendered generic `Float`).
- In the EMOM/circuit/AMRAP seed data, `set_number` tracks "how many times
  has this exercise appeared" (round 1, 2, 3...) per the schema comment
  ("set_number doubles as round number... depending on block_type"), not
  a shared absolute clock across exercises in the same block.
- The `phase_label` and `actual_load_type` CHECK constraints repeat
  `OR <column> IS NULL` even though that's redundant in standard SQL (a
  CHECK already passes on NULL) — kept verbatim to match
  `phase3_schema.sql` exactly rather than "simplifying" the source schema.
