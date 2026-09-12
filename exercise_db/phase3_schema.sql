-- ============================================================
-- PHASE 3 SCHEMA: Program Builder
-- Builds on Phase 1 (exercises) and Phase 2 (workouts/blocks/sets)
--
-- Model: reusable program TEMPLATES, cloned into client-specific
-- ASSIGNMENTS at signup. After cloning, an assignment is fully
-- independent — editing a client's plan never touches the template
-- or other clients' assignments, and vice versa.
--
-- Periodization: planned linear progression (accumulation ->
-- intensification -> deload as the usual base), autoregulated
-- session-to-session. Actuals are tracked lightweight: one
-- session_log per completed day (with notes) + logged_sets
-- against what was prescribed. No formal plan-change audit trail.
-- ============================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- TEMPLATE LAYER (reusable, not tied to any client)
-- ------------------------------------------------------------

CREATE TABLE programs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                          -- e.g. "12-Week HYROX Prep"
    description TEXT,
    duration_weeks INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE program_weeks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id INTEGER NOT NULL,
    week_number INTEGER NOT NULL,

    phase_label TEXT CHECK (
        phase_label IN ('accumulation', 'intensification', 'deload') OR phase_label IS NULL
    ),                                            -- nullable: not every week needs a label

    notes TEXT,

    FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE CASCADE,
    UNIQUE (program_id, week_number)
);

CREATE TABLE program_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_week_id INTEGER NOT NULL,
    day_number INTEGER NOT NULL,                  -- flexible: however many training days this week has
    label TEXT,                                   -- optional, e.g. "Lower Body", "Conditioning"

    FOREIGN KEY (program_week_id) REFERENCES program_weeks(id) ON DELETE CASCADE,
    UNIQUE (program_week_id, day_number)
);

CREATE TABLE program_day_workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_day_id INTEGER NOT NULL,
    workout_id INTEGER NOT NULL,                  -- links to Phase 2 workouts (template)
    order_index INTEGER NOT NULL DEFAULT 0,        -- supports multiple workouts per day if ever needed

    FOREIGN KEY (program_day_id) REFERENCES program_days(id) ON DELETE CASCADE,
    FOREIGN KEY (workout_id) REFERENCES workouts(id),
    UNIQUE (program_day_id, order_index)
);

-- ------------------------------------------------------------
-- ASSIGNMENT LAYER (client-specific clones, independently editable)
-- ------------------------------------------------------------

CREATE TABLE program_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id INTEGER,                           -- nullable: keeps a reference to the template it was cloned from, but assignment survives if template is later deleted
    client_name TEXT NOT NULL,                    -- swap for client_id FK once a clients table exists
    start_date TEXT NOT NULL,
    duration_weeks INTEGER NOT NULL,               -- copied at clone time, independently adjustable after
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'paused', 'cancelled')),
    notes TEXT,

    FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE SET NULL
);

CREATE TABLE assigned_program_weeks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_assignment_id INTEGER NOT NULL,
    week_number INTEGER NOT NULL,

    phase_label TEXT CHECK (
        phase_label IN ('accumulation', 'intensification', 'deload') OR phase_label IS NULL
    ),

    notes TEXT,

    FOREIGN KEY (program_assignment_id) REFERENCES program_assignments(id) ON DELETE CASCADE,
    UNIQUE (program_assignment_id, week_number)
);

CREATE TABLE assigned_program_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assigned_program_week_id INTEGER NOT NULL,
    day_number INTEGER NOT NULL,
    label TEXT,
    scheduled_date TEXT,                          -- nullable: actual calendar date once scheduled

    FOREIGN KEY (assigned_program_week_id) REFERENCES assigned_program_weeks(id) ON DELETE CASCADE,
    UNIQUE (assigned_program_week_id, day_number)
);

CREATE TABLE assigned_day_workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assigned_program_day_id INTEGER NOT NULL,
    workout_id INTEGER NOT NULL,                  -- can point to a different workout than the template if client's plan was edited
    order_index INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (assigned_program_day_id) REFERENCES assigned_program_days(id) ON DELETE CASCADE,
    FOREIGN KEY (workout_id) REFERENCES workouts(id),
    UNIQUE (assigned_program_day_id, order_index)
);

-- ------------------------------------------------------------
-- ACTUALS LAYER (lightweight — what really happened)
-- ------------------------------------------------------------

CREATE TABLE session_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assigned_program_day_id INTEGER NOT NULL,
    completed_at TEXT NOT NULL DEFAULT (datetime('now')),
    session_notes TEXT,                           -- e.g. "felt flat today", "cut short - client running late"

    FOREIGN KEY (assigned_program_day_id) REFERENCES assigned_program_days(id) ON DELETE CASCADE
);

CREATE TABLE logged_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_log_id INTEGER NOT NULL,
    prescribed_set_id INTEGER,                    -- nullable: link back to what was planned, if applicable
    workout_block_exercise_id INTEGER NOT NULL,   -- which exercise this actual belongs to
    set_number INTEGER NOT NULL,

    actual_reps INTEGER,
    actual_load_value REAL,
    actual_load_type TEXT CHECK (actual_load_type IN ('absolute', 'percent_1rm') OR actual_load_type IS NULL),
    actual_rir INTEGER,

    FOREIGN KEY (session_log_id) REFERENCES session_logs(id) ON DELETE CASCADE,
    FOREIGN KEY (prescribed_set_id) REFERENCES prescribed_sets(id) ON DELETE SET NULL,
    FOREIGN KEY (workout_block_exercise_id) REFERENCES workout_block_exercises(id)
);

-- ------------------------------------------------------------
-- INDEXES
-- ------------------------------------------------------------

CREATE INDEX idx_program_weeks_program ON program_weeks(program_id);
CREATE INDEX idx_program_days_week ON program_days(program_week_id);
CREATE INDEX idx_program_day_workouts_day ON program_day_workouts(program_day_id);

CREATE INDEX idx_assignments_program ON program_assignments(program_id);
CREATE INDEX idx_assigned_weeks_assignment ON assigned_program_weeks(program_assignment_id);
CREATE INDEX idx_assigned_days_week ON assigned_program_days(assigned_program_week_id);
CREATE INDEX idx_assigned_day_workouts_day ON assigned_day_workouts(assigned_program_day_id);

CREATE INDEX idx_session_logs_day ON session_logs(assigned_program_day_id);
CREATE INDEX idx_logged_sets_session ON logged_sets(session_log_id);
CREATE INDEX idx_logged_sets_prescribed ON logged_sets(prescribed_set_id);
