-- ============================================================
-- PHASE 1: EXERCISE DATABASE
-- ============================================================

CREATE TABLE muscle_groups (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE          -- e.g. 'Chest', 'Lats', 'Glutes', 'Quads'
);

CREATE TABLE equipment (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE          -- e.g. 'Barbell', 'Dumbbell', 'Cable', 'Bodyweight'
);

CREATE TABLE movement_patterns (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE          -- 'Squat','Hinge','Push Horizontal','Push Vertical',
                                        -- 'Pull Horizontal','Pull Vertical','Lunge','Carry',
                                        -- 'Rotation/Anti-rotation','Isolation'
);

CREATE TABLE exercises (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,                    -- 'barbell-back-squat'
    movement_pattern_id INTEGER REFERENCES movement_patterns(id),
    parent_exercise_id INTEGER REFERENCES exercises(id),  -- links variants, NULL if this IS the base
    unilateral BOOLEAN NOT NULL DEFAULT 0,
    difficulty TEXT CHECK(difficulty IN ('beginner','intermediate','advanced')),
    tracking_type TEXT NOT NULL CHECK(tracking_type IN
        ('reps_weight','reps_only','time','distance','time_distance')),
    cues TEXT,                                    -- coaching cues / setup notes
    video_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE exercise_muscles (
    exercise_id INTEGER REFERENCES exercises(id) ON DELETE CASCADE,
    muscle_group_id INTEGER REFERENCES muscle_groups(id),
    role TEXT NOT NULL CHECK(role IN ('primary','secondary')),
    PRIMARY KEY (exercise_id, muscle_group_id)
);

CREATE TABLE exercise_equipment (
    exercise_id INTEGER REFERENCES exercises(id) ON DELETE CASCADE,
    equipment_id INTEGER REFERENCES equipment(id),
    PRIMARY KEY (exercise_id, equipment_id)
);

CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE          -- 'knee-friendly','low-back-friendly','home-gym','core-anti-extension'
);

CREATE TABLE exercise_tags (
    exercise_id INTEGER REFERENCES exercises(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id),
    PRIMARY KEY (exercise_id, tag_id)
);

-- ============================================================
-- PHASE 2: WORKOUT BUILDER
-- ============================================================

CREATE TABLE clients (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    goal TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE workouts (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    client_id INTEGER REFERENCES clients(id),   -- NULL = reusable template
    is_template BOOLEAN NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE workout_exercises (
    id INTEGER PRIMARY KEY,
    workout_id INTEGER REFERENCES workouts(id) ON DELETE CASCADE,
    exercise_id INTEGER REFERENCES exercises(id),
    order_index INTEGER NOT NULL,          -- sequence within the workout
    superset_group INTEGER,                -- exercises sharing this number = a superset
    sets INTEGER,
    rep_min INTEGER,
    rep_max INTEGER,
    load_type TEXT CHECK(load_type IN ('absolute','percent_1rm','rpe','rir','bodyweight')),
    load_value REAL,                       -- kg/lb, or % of 1RM, or RPE/RIR target
    rest_seconds INTEGER,
    tempo TEXT,                            -- e.g. '3-1-1-0'
    notes TEXT
);

-- ============================================================
-- PHASE 3: PROGRAM BUILDER
-- ============================================================

CREATE TABLE programs (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    client_id INTEGER REFERENCES clients(id),
    goal TEXT,
    periodization_model TEXT CHECK(periodization_model IN
        ('linear','undulating_daily','undulating_weekly','block','conjugate','custom')),
    duration_weeks INTEGER,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE program_weeks (
    id INTEGER PRIMARY KEY,
    program_id INTEGER REFERENCES programs(id) ON DELETE CASCADE,
    week_number INTEGER NOT NULL,
    phase_label TEXT,                      -- 'Accumulation','Intensification','Deload'
    notes TEXT
);

CREATE TABLE program_days (
    id INTEGER PRIMARY KEY,
    program_week_id INTEGER REFERENCES program_weeks(id) ON DELETE CASCADE,
    day_number INTEGER NOT NULL,           -- day within the week
    workout_id INTEGER REFERENCES workouts(id),
    -- per-instance overrides so the same template can progress week to week
    -- without duplicating workout_exercises rows every week
    load_adjustment_pct REAL,              -- e.g. +5% over the template's base load
    notes TEXT
);
