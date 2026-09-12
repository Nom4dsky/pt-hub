-- ============================================================
-- PHASE 2 SCHEMA: Workout Builder
-- Builds on Phase 1 (exercises table + lookups)
-- Handles: straight sets, supersets, trisets, circuits, EMOM, AMRAP, for_time
-- ============================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- WORKOUTS (reusable templates, not scheduled instances)
-- ------------------------------------------------------------

CREATE TABLE workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ------------------------------------------------------------
-- WORKOUT BLOCKS
-- A block is one "chunk" of a workout: a straight-set exercise,
-- a superset/triset, a circuit, an EMOM, an AMRAP, or a for-time piece.
-- ------------------------------------------------------------

CREATE TABLE workout_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id INTEGER NOT NULL,
    order_index INTEGER NOT NULL,               -- sequence of this block within the workout

    block_type TEXT NOT NULL CHECK (
        block_type IN ('straight_set', 'superset', 'triset', 'circuit', 'emom', 'amrap', 'for_time')
    ),

    rounds INTEGER,                              -- fixed round count (circuit, EMOM); null for AMRAP/for_time
    duration_seconds INTEGER,                    -- total time cap (EMOM, AMRAP, for_time); null for straight_set/superset/triset
    rest_between_rounds_seconds INTEGER,         -- rest for circuits between rounds; null where not applicable

    notes TEXT,

    FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE,
    UNIQUE (workout_id, order_index)
);

-- ------------------------------------------------------------
-- WORKOUT BLOCK EXERCISES
-- Which exercises live in a block, and their order within it
-- (A1/A2/A3 for supersets, or sequence within a circuit/EMOM)
-- ------------------------------------------------------------

CREATE TABLE workout_block_exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    order_index INTEGER NOT NULL,                -- A1=0, A2=1, A3=2 etc within the block

    FOREIGN KEY (block_id) REFERENCES workout_blocks(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id),
    UNIQUE (block_id, order_index)
);

-- ------------------------------------------------------------
-- PRESCRIBED SETS
-- The actual prescription. set_number doubles as "round number"
-- for circuits/EMOM/AMRAP. Mandatory for every block type,
-- including conditioning blocks (load prescribed per exercise).
-- ------------------------------------------------------------

CREATE TABLE prescribed_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_block_exercise_id INTEGER NOT NULL,
    set_number INTEGER NOT NULL,                 -- or round number, depending on block_type

    reps_min INTEGER,
    reps_max INTEGER,

    load_value REAL,                             -- absolute weight OR %1RM, interpreted via load_type
    load_type TEXT CHECK (load_type IN ('absolute', 'percent_1rm')),

    rir_min INTEGER,
    rir_max INTEGER,

    rest_seconds INTEGER,
    tempo TEXT,                                  -- e.g. "3-1-1-0"

    FOREIGN KEY (workout_block_exercise_id) REFERENCES workout_block_exercises(id) ON DELETE CASCADE,
    UNIQUE (workout_block_exercise_id, set_number)
);

-- ------------------------------------------------------------
-- INDEXES
-- ------------------------------------------------------------

CREATE INDEX idx_workout_blocks_workout ON workout_blocks(workout_id);
CREATE INDEX idx_block_exercises_block ON workout_block_exercises(block_id);
CREATE INDEX idx_block_exercises_exercise ON workout_block_exercises(exercise_id);
CREATE INDEX idx_prescribed_sets_block_exercise ON prescribed_sets(workout_block_exercise_id);

-- ------------------------------------------------------------
-- PHASE 3 BACKLOG (not built yet — reference only)
-- ------------------------------------------------------------
-- programs: multi-week structures referencing workouts, with periodization logic
-- scheduled_workouts: workout_id, client_id, date, completed (thin scheduling layer)
-- logged_sets: actuals vs prescribed_sets, per client, per date
