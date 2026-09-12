"""
Seed the exercise database with a ~50-exercise starter set.

Covers every movement_pattern, every exercise_type, every tracking_type,
both compound_or_isolation values, and a spread of equipment (bodyweight
through barbell/machine/sled) and difficulty levels 1-6. A handful of
exercises are wired up as variants (variant_of) of a base movement.

Re-running this script wipes and re-inserts all exercise data (lookup
tables and join rows included) so it stays idempotent during development.

Usage:
    python seed.py
"""

from app.database import engine, get_session
from app.models import Base, Equipment, Exercise, ExerciseEquipment, ExerciseMuscle, Muscle, MovementPattern

MUSCLES = [
    "Chest", "Upper Back", "Lats", "Traps", "Rear Delts", "Front Delts",
    "Side Delts", "Biceps", "Triceps", "Forearms", "Abs", "Obliques",
    "Lower Back", "Glutes", "Quads", "Hamstrings", "Adductors", "Abductors",
    "Calves", "Hip Flexors",
]

EQUIPMENT = [
    "Barbell", "Dumbbell", "Kettlebell", "Bodyweight", "Cable", "Machine",
    "Resistance Band", "Medicine Ball", "TRX", "Landmine", "Bench",
    "Pull-Up Bar", "Sled", "Box", "Foam Roller",
]

MOVEMENT_PATTERNS = [
    "squat", "hinge", "push_horizontal", "push_vertical", "pull_horizontal",
    "pull_vertical", "carry", "rotation", "anti_rotation", "anti_extension",
    "gait",
]

# Each row: name, pattern, exercise_type, difficulty(1-6), unilateral,
# compound_or_isolation, tracking_type, equipment[(name, is_required)],
# muscles[(name, role)], variant_of (name or None), contraindications, cue_notes
EXERCISES = [
    # ---------------- SQUAT ----------------
    dict(
        name="Bodyweight Squat", pattern="squat", exercise_type="strength",
        difficulty=1, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_only",
        equipment=[("Bodyweight", True)],
        muscles=[("Quads", "primary"), ("Glutes", "primary"), ("Abs", "stabilizer")],
        variant_of=None, contraindications="acute_knee_pain",
        cue_notes="Sit back and down, knees track over toes, chest stays tall.",
    ),
    dict(
        name="Dumbbell Goblet Squat", pattern="squat", exercise_type="strength",
        difficulty=2, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Dumbbell", True)],
        muscles=[("Quads", "primary"), ("Glutes", "primary"), ("Adductors", "secondary"), ("Abs", "stabilizer")],
        variant_of="Bodyweight Squat", contraindications="acute_knee_pain",
        cue_notes="Elbows inside knees at the bottom, drive floor apart with feet.",
    ),
    dict(
        name="Barbell Back Squat", pattern="squat", exercise_type="strength",
        difficulty=4, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Barbell", True)],
        muscles=[("Quads", "primary"), ("Glutes", "primary"), ("Lower Back", "stabilizer"), ("Abs", "stabilizer")],
        variant_of=None, contraindications="lower_back_injury, herniated_disc",
        cue_notes="Brace before unracking, break at hips and knees together.",
    ),
    dict(
        name="Barbell Front Squat", pattern="squat", exercise_type="strength",
        difficulty=5, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Barbell", True)],
        muscles=[("Quads", "primary"), ("Abs", "secondary"), ("Upper Back", "stabilizer")],
        variant_of="Barbell Back Squat", contraindications="wrist_injury, lower_back_injury",
        cue_notes="Elbows up, keep the bar resting on the shoulder shelf, not the wrists.",
    ),
    dict(
        name="Dumbbell Bulgarian Split Squat", pattern="squat", exercise_type="strength",
        difficulty=4, unilateral=True, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Dumbbell", True), ("Bench", True)],
        muscles=[("Quads", "primary"), ("Glutes", "primary"), ("Abductors", "stabilizer")],
        variant_of=None, contraindications="acute_knee_pain, balance_disorder",
        cue_notes="Rear foot laced on the bench, drop straight down, front shin near vertical.",
    ),
    dict(
        name="Bodyweight Box Jump", pattern="squat", exercise_type="plyometric",
        difficulty=3, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_only",
        equipment=[("Box", True)],
        muscles=[("Quads", "primary"), ("Glutes", "primary"), ("Calves", "secondary")],
        variant_of=None, contraindications="acute_knee_pain, osteoporosis",
        cue_notes="Land soft with hips back, step down between reps — don't jump down.",
    ),
    dict(
        name="Machine Leg Extension", pattern="squat", exercise_type="strength",
        difficulty=1, unilateral=False, compound_or_isolation="isolation",
        tracking_type="reps_weight",
        equipment=[("Machine", True)],
        muscles=[("Quads", "primary")],
        variant_of=None, contraindications="patellar_tendinopathy",
        cue_notes="Control the eccentric, avoid slamming the weight stack at the top.",
    ),
    dict(
        name="Bodyweight Calf Raise", pattern="squat", exercise_type="strength",
        difficulty=1, unilateral=False, compound_or_isolation="isolation",
        tracking_type="reps_only",
        equipment=[("Bodyweight", True)],
        muscles=[("Calves", "primary")],
        variant_of=None, contraindications="achilles_tendinopathy",
        cue_notes="Full stretch at the bottom, pause at the top of each rep.",
    ),
    dict(
        name="Foam Roller Quad Smash", pattern="squat", exercise_type="mobility",
        difficulty=1, unilateral=False, compound_or_isolation="isolation",
        tracking_type="time",
        equipment=[("Foam Roller", True)],
        muscles=[("Quads", "primary")],
        variant_of=None, contraindications="deep_vein_thrombosis",
        cue_notes="Slow rolls, pause 20-30s on any tender spot rather than rolling fast.",
    ),

    # ---------------- HINGE ----------------
    dict(
        name="Bodyweight Hip Hinge Drill", pattern="hinge", exercise_type="mobility",
        difficulty=1, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_only",
        equipment=[("Bodyweight", True)],
        muscles=[("Hamstrings", "primary"), ("Glutes", "primary"), ("Lower Back", "stabilizer")],
        variant_of=None, contraindications=None,
        cue_notes="Push hips back to a wall/dowel behind you, soft knees, flat back.",
    ),
    dict(
        name="Dumbbell Romanian Deadlift", pattern="hinge", exercise_type="strength",
        difficulty=2, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Dumbbell", True)],
        muscles=[("Hamstrings", "primary"), ("Glutes", "primary"), ("Lower Back", "stabilizer")],
        variant_of=None, contraindications="lower_back_injury, herniated_disc",
        cue_notes="Push hips back first, dumbbells stay close to the shins, stop at mid-shin.",
    ),
    dict(
        name="Kettlebell Swing", pattern="hinge", exercise_type="conditioning",
        difficulty=2, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_time",
        equipment=[("Kettlebell", True)],
        muscles=[("Glutes", "primary"), ("Hamstrings", "primary"), ("Abs", "stabilizer")],
        variant_of=None, contraindications="lower_back_injury, pregnancy_late_term",
        cue_notes="Hinge, don't squat — hips snap the bell up, arms are just along for the ride.",
    ),
    dict(
        name="Barbell Deadlift", pattern="hinge", exercise_type="strength",
        difficulty=5, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Barbell", True)],
        muscles=[("Hamstrings", "primary"), ("Glutes", "primary"), ("Lower Back", "stabilizer"), ("Traps", "secondary")],
        variant_of=None, contraindications="lower_back_injury, herniated_disc, uncontrolled_hypertension",
        cue_notes="Bar over midfoot, brace and pull the slack out before the pull.",
    ),
    dict(
        name="Barbell Romanian Deadlift", pattern="hinge", exercise_type="strength",
        difficulty=4, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Barbell", True)],
        muscles=[("Hamstrings", "primary"), ("Glutes", "primary"), ("Lower Back", "stabilizer")],
        variant_of="Barbell Deadlift", contraindications="lower_back_injury, herniated_disc",
        cue_notes="Soft knees throughout, bar tracks close to the legs, stop when hamstrings load up.",
    ),
    dict(
        name="Dumbbell Single-Leg Deadlift", pattern="hinge", exercise_type="strength",
        difficulty=4, unilateral=True, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Dumbbell", True)],
        muscles=[("Hamstrings", "primary"), ("Glutes", "primary"), ("Abs", "stabilizer")],
        variant_of=None, contraindications="balance_disorder, lower_back_injury",
        cue_notes="Square the hips to the floor, reach the free arm forward for counterbalance.",
    ),
    dict(
        name="Machine Leg Curl", pattern="hinge", exercise_type="strength",
        difficulty=1, unilateral=False, compound_or_isolation="isolation",
        tracking_type="reps_weight",
        equipment=[("Machine", True)],
        muscles=[("Hamstrings", "primary")],
        variant_of=None, contraindications="hamstring_strain",
        cue_notes="Squeeze at full contraction, don't let hips rise off the pad.",
    ),
    dict(
        name="Medicine Ball Slam", pattern="hinge", exercise_type="plyometric",
        difficulty=3, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_only",
        equipment=[("Medicine Ball", True)],
        muscles=[("Lats", "primary"), ("Abs", "primary"), ("Hamstrings", "secondary")],
        variant_of=None, contraindications="lower_back_injury, shoulder_impingement",
        cue_notes="Full body extension overhead, then hinge and slam — let the hips lead.",
    ),

    # ---------------- PUSH_HORIZONTAL ----------------
    dict(
        name="Bodyweight Push-Up", pattern="push_horizontal", exercise_type="strength",
        difficulty=2, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_only",
        equipment=[("Bodyweight", True)],
        muscles=[("Chest", "primary"), ("Triceps", "secondary"), ("Front Delts", "secondary"), ("Abs", "stabilizer")],
        variant_of=None, contraindications="wrist_injury, shoulder_impingement",
        cue_notes="Straight line from shoulders to ankles, elbows ~45° from the torso.",
    ),
    dict(
        name="Barbell Bench Press", pattern="push_horizontal", exercise_type="strength",
        difficulty=4, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Barbell", True), ("Bench", True)],
        muscles=[("Chest", "primary"), ("Triceps", "secondary"), ("Front Delts", "secondary")],
        variant_of=None, contraindications="shoulder_impingement",
        cue_notes="Shoulder blades pinched and down, feet driving into the floor.",
    ),
    dict(
        name="Dumbbell Bench Press", pattern="push_horizontal", exercise_type="strength",
        difficulty=3, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Dumbbell", True), ("Bench", True)],
        muscles=[("Chest", "primary"), ("Triceps", "secondary"), ("Front Delts", "secondary")],
        variant_of="Barbell Bench Press", contraindications="shoulder_impingement",
        cue_notes="Let the dumbbells travel slightly wider than the barbell path for a deeper stretch.",
    ),
    dict(
        name="Cable Chest Press", pattern="push_horizontal", exercise_type="strength",
        difficulty=3, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Cable", True)],
        muscles=[("Chest", "primary"), ("Front Delts", "secondary"), ("Triceps", "secondary")],
        variant_of=None, contraindications="shoulder_impingement",
        cue_notes="Split stance for stability, squeeze the handles together at full extension.",
    ),
    dict(
        name="TRX Chest Press", pattern="push_horizontal", exercise_type="strength",
        difficulty=3, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_only",
        equipment=[("TRX", True)],
        muscles=[("Chest", "primary"), ("Front Delts", "secondary"), ("Abs", "stabilizer")],
        variant_of=None, contraindications="shoulder_impingement",
        cue_notes="Body stays rigid plank-to-heels, regulate difficulty with foot position.",
    ),

    # ---------------- PUSH_VERTICAL ----------------
    dict(
        name="Machine Shoulder Press", pattern="push_vertical", exercise_type="strength",
        difficulty=2, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Machine", True)],
        muscles=[("Front Delts", "primary"), ("Triceps", "secondary")],
        variant_of=None, contraindications="shoulder_impingement",
        cue_notes="Set seat height so handles start level with the shoulders.",
    ),
    dict(
        name="Dumbbell Shoulder Press", pattern="push_vertical", exercise_type="strength",
        difficulty=3, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Dumbbell", True)],
        muscles=[("Front Delts", "primary"), ("Triceps", "secondary"), ("Abs", "stabilizer")],
        variant_of="Machine Shoulder Press", contraindications="shoulder_impingement",
        cue_notes="Ribs down, avoid flaring the lower back to get the last rep.",
    ),
    dict(
        name="Barbell Overhead Press", pattern="push_vertical", exercise_type="strength",
        difficulty=4, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Barbell", True)],
        muscles=[("Front Delts", "primary"), ("Triceps", "secondary"), ("Abs", "stabilizer")],
        variant_of=None, contraindications="shoulder_impingement, lower_back_injury",
        cue_notes="Bar path grazes the chin, drive head through at the top.",
    ),
    dict(
        name="Landmine Press", pattern="push_vertical", exercise_type="strength",
        difficulty=3, unilateral=True, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Landmine", True), ("Barbell", True)],
        muscles=[("Front Delts", "primary"), ("Chest", "secondary"), ("Abs", "stabilizer")],
        variant_of=None, contraindications="shoulder_impingement",
        cue_notes="Press up and slightly forward along the natural arc, easier on the shoulder than straight overhead.",
    ),
    dict(
        name="Cable Lateral Raise", pattern="push_vertical", exercise_type="strength",
        difficulty=1, unilateral=True, compound_or_isolation="isolation",
        tracking_type="reps_weight",
        equipment=[("Cable", True)],
        muscles=[("Side Delts", "primary")],
        variant_of=None, contraindications="shoulder_impingement",
        cue_notes="Lead with the elbow, stop at shoulder height, no swinging.",
    ),
    dict(
        name="Cable Triceps Pushdown", pattern="push_vertical", exercise_type="strength",
        difficulty=1, unilateral=False, compound_or_isolation="isolation",
        tracking_type="reps_weight",
        equipment=[("Cable", True)],
        muscles=[("Triceps", "primary")],
        variant_of=None, contraindications="elbow_tendinopathy",
        cue_notes="Elbows pinned to the ribs, only the forearm moves.",
    ),

    # ---------------- PULL_HORIZONTAL ----------------
    dict(
        name="TRX Row", pattern="pull_horizontal", exercise_type="strength",
        difficulty=2, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_only",
        equipment=[("TRX", True)],
        muscles=[("Upper Back", "primary"), ("Lats", "secondary"), ("Biceps", "secondary")],
        variant_of=None, contraindications=None,
        cue_notes="Lean back to add load, pull chest to hands, squeeze shoulder blades.",
    ),
    dict(
        name="Dumbbell Bent-Over Row", pattern="pull_horizontal", exercise_type="strength",
        difficulty=3, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Dumbbell", True)],
        muscles=[("Upper Back", "primary"), ("Lats", "secondary"), ("Biceps", "secondary"), ("Lower Back", "stabilizer")],
        variant_of=None, contraindications="lower_back_injury",
        cue_notes="Hinge to ~45°, flat back, row to the hip not the chest.",
    ),
    dict(
        name="Barbell Bent-Over Row", pattern="pull_horizontal", exercise_type="strength",
        difficulty=4, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Barbell", True)],
        muscles=[("Upper Back", "primary"), ("Lats", "secondary"), ("Biceps", "secondary"), ("Lower Back", "stabilizer")],
        variant_of="Dumbbell Bent-Over Row", contraindications="lower_back_injury",
        cue_notes="Brace hard, pull to the lower ribs, control the negative.",
    ),
    dict(
        name="Cable Seated Row", pattern="pull_horizontal", exercise_type="strength",
        difficulty=2, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Cable", True)],
        muscles=[("Upper Back", "primary"), ("Lats", "secondary"), ("Biceps", "secondary")],
        variant_of=None, contraindications=None,
        cue_notes="Chest up, drive elbows back rather than just pulling with the arms.",
    ),
    dict(
        name="Machine Chest-Supported Row", pattern="pull_horizontal", exercise_type="strength",
        difficulty=2, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Machine", True)],
        muscles=[("Upper Back", "primary"), ("Lats", "secondary"), ("Rear Delts", "secondary")],
        variant_of=None, contraindications="lower_back_injury",
        cue_notes="Chest pinned to the pad the whole set — takes the low back out of the equation.",
    ),

    # ---------------- PULL_VERTICAL ----------------
    dict(
        name="Cable Lat Pulldown", pattern="pull_vertical", exercise_type="strength",
        difficulty=2, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Cable", True)],
        muscles=[("Lats", "primary"), ("Upper Back", "secondary"), ("Biceps", "secondary")],
        variant_of=None, contraindications="shoulder_impingement",
        cue_notes="Pull elbows down and back, avoid leaning back excessively to cheat the rep.",
    ),
    dict(
        name="Machine Lat Pulldown", pattern="pull_vertical", exercise_type="strength",
        difficulty=2, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Machine", True)],
        muscles=[("Lats", "primary"), ("Upper Back", "secondary"), ("Biceps", "secondary")],
        variant_of="Cable Lat Pulldown", contraindications="shoulder_impingement",
        cue_notes="Same cue as the cable version — fixed path is a good regression for beginners.",
    ),
    dict(
        name="Resistance Band Assisted Pull-Up", pattern="pull_vertical", exercise_type="strength",
        difficulty=3, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_only",
        equipment=[("Resistance Band", True), ("Pull-Up Bar", True)],
        muscles=[("Lats", "primary"), ("Upper Back", "secondary"), ("Biceps", "secondary")],
        variant_of=None, contraindications="shoulder_impingement",
        cue_notes="Band under the knee or foot, still work to control the descent, don't just drop.",
    ),
    dict(
        name="Bodyweight Pull-Up", pattern="pull_vertical", exercise_type="strength",
        difficulty=5, unilateral=False, compound_or_isolation="compound",
        tracking_type="reps_only",
        equipment=[("Pull-Up Bar", True)],
        muscles=[("Lats", "primary"), ("Upper Back", "secondary"), ("Biceps", "secondary")],
        variant_of="Resistance Band Assisted Pull-Up", contraindications="shoulder_impingement",
        cue_notes="Full hang to chin over the bar, avoid kipping unless training for it specifically.",
    ),
    dict(
        name="Dumbbell Bicep Curl", pattern="pull_vertical", exercise_type="strength",
        difficulty=1, unilateral=False, compound_or_isolation="isolation",
        tracking_type="reps_weight",
        equipment=[("Dumbbell", True)],
        muscles=[("Biceps", "primary"), ("Forearms", "secondary")],
        variant_of=None, contraindications="elbow_tendinopathy",
        cue_notes="Elbows stay pinned at the sides, no swinging the torso for momentum.",
    ),

    # ---------------- CARRY ----------------
    dict(
        name="Dumbbell Farmer's Carry", pattern="carry", exercise_type="strength",
        difficulty=2, unilateral=False, compound_or_isolation="compound",
        tracking_type="distance",
        equipment=[("Dumbbell", True)],
        muscles=[("Traps", "primary"), ("Forearms", "primary"), ("Abs", "stabilizer"), ("Glutes", "stabilizer")],
        variant_of=None, contraindications="uncontrolled_hypertension",
        cue_notes="Tall posture, ribs stacked over hips, don't let the weights swing.",
    ),
    dict(
        name="Kettlebell Suitcase Carry", pattern="carry", exercise_type="strength",
        difficulty=3, unilateral=True, compound_or_isolation="compound",
        tracking_type="distance",
        equipment=[("Kettlebell", True)],
        muscles=[("Obliques", "primary"), ("Abs", "stabilizer"), ("Traps", "secondary")],
        variant_of=None, contraindications="uncontrolled_hypertension",
        cue_notes="Resist leaning toward the loaded side — that side-bend resistance is the point.",
    ),
    dict(
        name="Sled Push", pattern="carry", exercise_type="conditioning",
        difficulty=3, unilateral=False, compound_or_isolation="compound",
        tracking_type="time_distance",
        equipment=[("Sled", True)],
        muscles=[("Quads", "primary"), ("Glutes", "primary"), ("Calves", "secondary")],
        variant_of=None, contraindications="uncontrolled_hypertension, acute_knee_pain",
        cue_notes="Long strides, drive through the whole foot, keep a flat back angle.",
    ),

    # ---------------- ROTATION ----------------
    dict(
        name="Medicine Ball Rotational Throw", pattern="rotation", exercise_type="plyometric",
        difficulty=3, unilateral=True, compound_or_isolation="compound",
        tracking_type="reps_only",
        equipment=[("Medicine Ball", True)],
        muscles=[("Obliques", "primary"), ("Abs", "secondary"), ("Glutes", "secondary")],
        variant_of=None, contraindications="lower_back_injury",
        cue_notes="Power comes from the hips turning first, the arms just release the ball.",
    ),
    dict(
        name="Cable Woodchop", pattern="rotation", exercise_type="strength",
        difficulty=3, unilateral=True, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Cable", True)],
        muscles=[("Obliques", "primary"), ("Abs", "secondary")],
        variant_of=None, contraindications="lower_back_injury",
        cue_notes="Rotate through the trunk and hips together, arms stay relatively straight.",
    ),
    dict(
        name="Landmine Rotation", pattern="rotation", exercise_type="strength",
        difficulty=2, unilateral=True, compound_or_isolation="compound",
        tracking_type="reps_only",
        equipment=[("Landmine", True), ("Barbell", True)],
        muscles=[("Obliques", "primary"), ("Abs", "secondary"), ("Front Delts", "stabilizer")],
        variant_of=None, contraindications="lower_back_injury",
        cue_notes="Arms stay long, rotate the bar in an arc while keeping hips relatively square.",
    ),

    # ---------------- ANTI_ROTATION ----------------
    dict(
        name="Resistance Band Half-Kneeling Chop", pattern="anti_rotation", exercise_type="stability",
        difficulty=2, unilateral=True, compound_or_isolation="isolation",
        tracking_type="reps_only",
        equipment=[("Resistance Band", True)],
        muscles=[("Obliques", "primary"), ("Abs", "primary")],
        variant_of=None, contraindications=None,
        cue_notes="Resist the band pulling you into rotation — ribcage and hips stay square.",
    ),
    dict(
        name="Cable Half-Kneeling Chop", pattern="anti_rotation", exercise_type="stability",
        difficulty=2, unilateral=True, compound_or_isolation="isolation",
        tracking_type="reps_only",
        equipment=[("Cable", True)],
        muscles=[("Obliques", "primary"), ("Abs", "primary")],
        variant_of="Resistance Band Half-Kneeling Chop", contraindications=None,
        cue_notes="Same brief as the band version — fixed cable path makes the resistance more consistent.",
    ),
    dict(
        name="TRX Plank with Reach", pattern="anti_rotation", exercise_type="stability",
        difficulty=3, unilateral=True, compound_or_isolation="isolation",
        tracking_type="time",
        equipment=[("TRX", True)],
        muscles=[("Abs", "primary"), ("Obliques", "primary"), ("Front Delts", "stabilizer")],
        variant_of=None, contraindications="shoulder_impingement",
        cue_notes="Hips stay level as the straps swing — don't let one side dip or rotate.",
    ),

    # ---------------- ANTI_EXTENSION ----------------
    dict(
        name="Bodyweight Plank", pattern="anti_extension", exercise_type="stability",
        difficulty=1, unilateral=False, compound_or_isolation="isolation",
        tracking_type="time",
        equipment=[("Bodyweight", True)],
        muscles=[("Abs", "primary"), ("Lower Back", "stabilizer")],
        variant_of=None, contraindications="lower_back_injury",
        cue_notes="Ribs down, glutes lightly squeezed, don't let the hips sag or pike.",
    ),
    dict(
        name="Bodyweight Dead Bug", pattern="anti_extension", exercise_type="stability",
        difficulty=1, unilateral=True, compound_or_isolation="isolation",
        tracking_type="reps_only",
        equipment=[("Bodyweight", True)],
        muscles=[("Abs", "primary"), ("Hip Flexors", "secondary")],
        variant_of=None, contraindications=None,
        cue_notes="Lower back stays flat on the floor the entire rep — that's the whole drill.",
    ),
    dict(
        name="Cable Kneeling Crunch", pattern="anti_extension", exercise_type="strength",
        difficulty=2, unilateral=False, compound_or_isolation="isolation",
        tracking_type="reps_weight",
        equipment=[("Cable", True)],
        muscles=[("Abs", "primary")],
        variant_of=None, contraindications="lower_back_injury",
        cue_notes="Curl the ribcage toward the hips, hips stay still — don't hinge from them.",
    ),

    # ---------------- GAIT ----------------
    dict(
        name="Bodyweight High Knee March", pattern="gait", exercise_type="conditioning",
        difficulty=1, unilateral=False, compound_or_isolation="compound",
        tracking_type="time",
        equipment=[("Bodyweight", True)],
        muscles=[("Hip Flexors", "primary"), ("Abs", "stabilizer"), ("Calves", "secondary")],
        variant_of=None, contraindications=None,
        cue_notes="Tall posture, drive the knee to hip height without leaning back.",
    ),
    dict(
        name="Bodyweight Walking Lunge", pattern="gait", exercise_type="strength",
        difficulty=2, unilateral=True, compound_or_isolation="compound",
        tracking_type="reps_only",
        equipment=[("Bodyweight", True)],
        muscles=[("Quads", "primary"), ("Glutes", "primary"), ("Adductors", "stabilizer")],
        variant_of=None, contraindications="acute_knee_pain",
        cue_notes="Step to a stride length that lets the back knee drop straight down.",
    ),
    dict(
        name="Dumbbell Walking Lunge", pattern="gait", exercise_type="strength",
        difficulty=3, unilateral=True, compound_or_isolation="compound",
        tracking_type="reps_weight",
        equipment=[("Dumbbell", True)],
        muscles=[("Quads", "primary"), ("Glutes", "primary"), ("Adductors", "stabilizer")],
        variant_of="Bodyweight Walking Lunge", contraindications="acute_knee_pain",
        cue_notes="Same stride mechanics as the bodyweight version, dumbbells at the sides or racked.",
    ),
    dict(
        name="Sled Drag", pattern="gait", exercise_type="conditioning",
        difficulty=2, unilateral=False, compound_or_isolation="compound",
        tracking_type="distance",
        equipment=[("Sled", True)],
        muscles=[("Quads", "primary"), ("Hamstrings", "secondary"), ("Calves", "secondary")],
        variant_of=None, contraindications="acute_knee_pain",
        cue_notes="Backward drag, stay low, short quick steps for the quad/knee-friendly version.",
    ),
    dict(
        name="Resistance Band Hip Abduction", pattern="gait", exercise_type="strength",
        difficulty=1, unilateral=True, compound_or_isolation="isolation",
        tracking_type="reps_only",
        equipment=[("Resistance Band", True)],
        muscles=[("Abductors", "primary"), ("Glutes", "secondary")],
        variant_of=None, contraindications=None,
        cue_notes="Standing or side-lying, lead with the heel, keep the toe from turning up.",
    ),
]


def wipe_all(session) -> None:
    session.query(ExerciseMuscle).delete()
    session.query(ExerciseEquipment).delete()
    session.query(Exercise).delete()
    session.query(Muscle).delete()
    session.query(Equipment).delete()
    session.query(MovementPattern).delete()
    session.commit()


def get_or_create(session, model, name: str):
    obj = session.query(model).filter_by(name=name).one_or_none()
    if obj is None:
        obj = model(name=name)
        session.add(obj)
        session.flush()
    return obj


def seed(session) -> int:
    wipe_all(session)

    muscles = {name: get_or_create(session, Muscle, name) for name in MUSCLES}
    equipment = {name: get_or_create(session, Equipment, name) for name in EQUIPMENT}
    patterns = {name: get_or_create(session, MovementPattern, name) for name in MOVEMENT_PATTERNS}
    session.commit()

    by_name: dict[str, Exercise] = {}

    for row in EXERCISES:
        exercise = Exercise(
            name=row["name"],
            movement_pattern_id=patterns[row["pattern"]].id,
            exercise_type=row["exercise_type"],
            difficulty=row["difficulty"],
            unilateral=row["unilateral"],
            compound_or_isolation=row["compound_or_isolation"],
            tracking_type=row["tracking_type"],
            contraindications=row["contraindications"],
            cue_notes=row["cue_notes"],
            variant_of=by_name[row["variant_of"]].id if row["variant_of"] else None,
        )
        session.add(exercise)
        session.flush()  # need exercise.id for the join rows below
        by_name[row["name"]] = exercise

        for eq_name, is_required in row["equipment"]:
            session.add(
                ExerciseEquipment(
                    exercise_id=exercise.id,
                    equipment_id=equipment[eq_name].id,
                    is_required=is_required,
                )
            )
        for muscle_name, role in row["muscles"]:
            session.add(
                ExerciseMuscle(
                    exercise_id=exercise.id,
                    muscle_id=muscles[muscle_name].id,
                    role=role,
                )
            )

    session.commit()
    return len(EXERCISES)


def main() -> None:
    Base.metadata.create_all(engine)  # no-op once alembic has run; safety net for quick starts
    session = get_session()
    try:
        count = seed(session)
        print(f"Seeded {count} exercises, {len(MUSCLES)} muscles, "
              f"{len(EQUIPMENT)} equipment types, {len(MOVEMENT_PATTERNS)} movement patterns.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
