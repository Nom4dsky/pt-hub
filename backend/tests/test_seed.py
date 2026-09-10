from pathlib import Path

from app import models
from seed import seed

SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_exercises.json"


def test_seed_loads_all_entries_without_duplicating_reference_rows(db_session, monkeypatch):
    import seed as seed_module

    monkeypatch.setattr(seed_module, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)  # conftest owns the session lifecycle

    seed(SEED_PATH)

    import json

    entries = json.loads(SEED_PATH.read_text())
    assert db_session.query(models.Exercise).count() == len(entries)

    # get-or-create should collapse repeated names across entries
    pattern_names = {e["movement_pattern"] for e in entries}
    assert db_session.query(models.MovementPattern).count() == len(pattern_names)

    squat = db_session.query(models.Exercise).filter_by(slug="barbell-back-squat").first()
    assert squat is not None
    assert squat.movement_pattern.name == "Squat"
    assert {(m.muscle_group.name, m.role) for m in squat.exercise_muscles} == {
        ("Quads", "primary"),
        ("Glutes", "primary"),
        ("Hamstrings", "secondary"),
        ("Core", "secondary"),
    }


def test_seed_is_idempotent(db_session, monkeypatch, capsys):
    import seed as seed_module

    monkeypatch.setattr(seed_module, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    seed(SEED_PATH)
    count_after_first = db_session.query(models.Exercise).count()

    seed(SEED_PATH)
    count_after_second = db_session.query(models.Exercise).count()

    assert count_after_first == count_after_second
    assert "skip (already exists)" in capsys.readouterr().out
