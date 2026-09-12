-- ============================================================
-- PHASE 1 SCHEMA: Exercise Database
-- Stack: SQLite (migration path to Postgres if multi-user later)
-- ============================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- LOOKUP TABLES
-- ------------------------------------------------------------

CREATE TABLE muscles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE movement_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
    -- e.g. squat, hinge, push_horizontal, push_vertical, pull_horizontal,
    -- pull_vertical, carry, rotation, anti_rotation, anti_extension, gait
);

-- ------------------------------------------------------------
-- CORE EXERCISE TABLE
-- ------------------------------------------------------------

CREATE TABLE exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                          -- equipment-prefixed convention, e.g. "Barbell Row"
    variant_of INTEGER,                          -- self-referencing FK for variants
    movement_pattern_id INTEGER NOT NULL,

    exercise_type TEXT NOT NULL CHECK (
        exercise_type IN ('strength', 'mobility', 'conditioning', 'plyometric', 'stability')
    ),

    difficulty INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 6),

    unilateral BOOLEAN NOT NULL DEFAULT 0,
    compound_or_isolation TEXT NOT NULL CHECK (
        compound_or_isolation IN ('compound', 'isolation')
    ),

    tracking_type TEXT NOT NULL CHECK (
        tracking_type IN ('reps_weight', 'reps_only', 'time', 'distance', 'time_distance', 'reps_time')
    ),

    contraindications TEXT,                      -- free text tags for now, comma-separated or JSON
    cue_notes TEXT,
    video_url TEXT,

    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (variant_of) REFERENCES exercises(id) ON DELETE SET NULL,
    FOREIGN KEY (movement_pattern_id) REFERENCES movement_patterns(id)
);

-- ------------------------------------------------------------
-- JOIN TABLES
-- ------------------------------------------------------------

CREATE TABLE exercise_muscles (
    exercise_id INTEGER NOT NULL,
    muscle_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('primary', 'secondary', 'stabilizer')),

    PRIMARY KEY (exercise_id, muscle_id, role),
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
    FOREIGN KEY (muscle_id) REFERENCES muscles(id) ON DELETE CASCADE
);

CREATE TABLE exercise_equipment (
    exercise_id INTEGER NOT NULL,
    equipment_id INTEGER NOT NULL,
    is_required BOOLEAN NOT NULL DEFAULT 1,

    PRIMARY KEY (exercise_id, equipment_id),
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- INDEXES (for the query patterns we care about)
-- ------------------------------------------------------------

CREATE INDEX idx_exercises_movement_pattern ON exercises(movement_pattern_id);
CREATE INDEX idx_exercises_type ON exercises(exercise_type);
CREATE INDEX idx_exercises_difficulty ON exercises(difficulty);
CREATE INDEX idx_exercises_variant_of ON exercises(variant_of);
CREATE INDEX idx_exercise_muscles_muscle ON exercise_muscles(muscle_id);
CREATE INDEX idx_exercise_equipment_equipment ON exercise_equipment(equipment_id);

-- ------------------------------------------------------------
-- PHASE 2 BACKLOG (not built yet — reference only)
-- ------------------------------------------------------------
-- prescribed_sets: exercise_id, workout_id, reps, load or %1RM, RIR, rest, tempo
-- logged_sets: same fields but actuals, + timestamp, + client_id
