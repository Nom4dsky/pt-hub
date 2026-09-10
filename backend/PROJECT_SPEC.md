# Coaching Backend — Project Spec

Internal tool, single user (you), backend/database first, UI later. No auth needed yet.

## Stack
- Python 3.11+
- SQLite (file-based, zero setup; migrates cleanly to Postgres later if needed)
- SQLAlchemy (ORM)
- FastAPI (API layer, even before there's a UI — lets you hit endpoints from scripts,
  Postman, or a future frontend without rewriting logic)
- Alembic for migrations once the schema stabilizes past phase 1

## Files provided
- `schema.sql` — full schema across all 3 phases, phase-labeled
- `seed_exercises.json` — 29 starter exercises spanning all movement patterns and
  common equipment types, in a flat format ready to load

## Build order

### Phase 1 — Exercise Database
1. Set up SQLite DB + SQLAlchemy models matching the Phase 1 section of `schema.sql`.
2. Write a seed script that loads `seed_exercises.json`:
   - creates muscle_groups / equipment / movement_patterns / tags rows as needed
     (get-or-create pattern, since the JSON references them by name)
   - inserts exercises and the join table rows
3. Build basic query functions / API endpoints:
   - list exercises filtered by movement pattern, muscle group, equipment, tag
   - get exercise by id/slug with all relations loaded
   - create/update/deactivate exercise (soft delete via `is_active`, never hard-delete —
     workout_exercises will reference these rows later)
4. Expand the seed set toward your full working exercise list. I can help generate
   more in batches (e.g. "give me 20 more pull-pattern exercises in this format")
   whenever you want — happy to do that now or later.

**Done when:** you can query "show me all beginner-friendly hinge exercises using only
dumbbells" and get a correct, structured answer back.

### Phase 2 — Workout Builder
1. Add Phase 2 tables (`clients`, `workouts`, `workout_exercises`).
2. Core logic: given a set of exercises, assemble them into a workout with order,
   sets/rep ranges, load prescription (absolute / %1RM / RPE / RIR), rest, tempo,
   and superset grouping.
3. Support both templates (`client_id` NULL, `is_template` true) and client-assigned
   instances — a template gets copied into a real workout row when assigned, so
   editing the template later doesn't retroactively change what a client already did.
4. Endpoints: create workout, add/reorder/remove exercises, duplicate a workout as
   a new template, list workouts by client.

**Done when:** you can build a full session (e.g. upper body strength day) exercise by
exercise, save it as a template, and assign it to a client without duplicating data
unnecessarily.

### Phase 3 — Program Builder
1. Add Phase 3 tables (`programs`, `program_weeks`, `program_days`).
2. Core logic: a program is N weeks, each week has days, each day points at a workout.
   `load_adjustment_pct` on `program_days` lets the same workout template progress
   week to week (e.g. +2.5% load) without duplicating `workout_exercises` rows every week.
3. Decide and implement your periodization logic per `periodization_model`
   (linear / undulating / block / conjugate) — this is the part most specific to your
   coaching style, worth designing carefully rather than generically. Flag when you're
   ready to spec this out in detail; the progression math deserves its own discussion.
4. Endpoints: create program, generate weeks/days, apply progression rule, view a
   client's full program.

**Done when:** you can generate a 6-week block for a client from a handful of workout
templates with automatic week-to-week load progression.

## Open design decisions (revisit later, not blockers now)
- 1RM tracking / e1RM estimation (Epley, Brzycki, etc.) — needed if you want %1RM
  prescriptions to auto-calculate actual loads.
- Autoregulation: do you want RPE/RIR-based load adjustment feeding back into future
  sessions based on logged performance?
- Exercise substitution logic (e.g. auto-suggest equipment-matched swaps if a client
  reports pain/injury) — this is where the `tags` and `movement_pattern` fields pay off.
- Exporting a program to a client-readable format (PDF/shareable link) — deferred
  since this is backend-first, but worth keeping the schema clean for it.

## Handing this to Claude Code
Give Claude Code this file plus `schema.sql` and `seed_exercises.json`, and ask it to
start on Phase 1 only. Don't let it jump ahead to Phase 2/3 tables in code until
Phase 1 is working end-to-end — the schema already anticipates them, so there's no
rework cost to waiting.
