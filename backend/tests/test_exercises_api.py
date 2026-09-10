from app import crud, models, schemas


def _create(client, **overrides):
    payload = {
        "name": "Barbell Back Squat",
        "movement_pattern": "Squat",
        "tracking_type": "reps_weight",
        "difficulty": "intermediate",
        "unilateral": False,
        "primary_muscles": ["Quads", "Glutes"],
        "secondary_muscles": ["Hamstrings"],
        "equipment": ["Barbell"],
        "tags": [],
    }
    payload.update(overrides)
    resp = client.post("/exercises", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_exercise_generates_slug_and_relations(client):
    body = _create(client)
    assert body["slug"] == "barbell-back-squat"
    assert body["movement_pattern"]["name"] == "Squat"
    assert {m["muscle_group"]["name"]: m["role"] for m in body["muscles"]} == {
        "Quads": "primary",
        "Glutes": "primary",
        "Hamstrings": "secondary",
    }
    assert [e["name"] for e in body["equipment"]] == ["Barbell"]
    assert body["is_active"] is True


def test_duplicate_slug_conflict(client):
    _create(client)
    resp = client.post("/exercises", json={
        "name": "Barbell Back Squat",
        "movement_pattern": "Squat",
        "tracking_type": "reps_weight",
    })
    assert resp.status_code == 409


def test_get_by_id_and_slug(client):
    created = _create(client)
    by_id = client.get(f"/exercises/{created['id']}")
    by_slug = client.get(f"/exercises/{created['slug']}")
    assert by_id.status_code == 200
    assert by_slug.status_code == 200
    assert by_id.json()["id"] == by_slug.json()["id"]


def test_get_missing_returns_404(client):
    assert client.get("/exercises/999").status_code == 404
    assert client.get("/exercises/no-such-slug").status_code == 404


def test_update_exercise_partial(client):
    created = _create(client)
    resp = client.patch(f"/exercises/{created['id']}", json={"difficulty": "advanced", "tags": ["strength"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["difficulty"] == "advanced"
    assert [t["name"] for t in body["tags"]] == ["strength"]
    # untouched fields survive the partial update
    assert body["movement_pattern"]["name"] == "Squat"
    assert [e["name"] for e in body["equipment"]] == ["Barbell"]


def test_deactivate_is_soft_delete(client):
    created = _create(client)
    resp = client.post(f"/exercises/{created['id']}/deactivate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # excluded from default listing, present with include_inactive
    default_list = client.get("/exercises").json()
    assert created["id"] not in [e["id"] for e in default_list]

    inactive_list = client.get("/exercises", params={"include_inactive": True}).json()
    assert created["id"] in [e["id"] for e in inactive_list]

    # never hard-deleted — still fetchable by id
    assert client.get(f"/exercises/{created['id']}").status_code == 200


def test_reactivate(client):
    created = _create(client)
    client.post(f"/exercises/{created['id']}/deactivate")
    resp = client.post(f"/exercises/{created['id']}/reactivate")
    assert resp.json()["is_active"] is True


def test_reused_reference_rows_are_not_duplicated(client, db_session):
    _create(client, name="Barbell Back Squat")
    _create(client, name="Goblet Squat", equipment=["Dumbbell"], primary_muscles=["Quads", "Glutes"])
    assert db_session.query(models.MovementPattern).filter_by(name="Squat").count() == 1
    assert db_session.query(models.MuscleGroup).filter_by(name="Quads").count() == 1


def test_filter_by_movement_pattern_muscle_equipment_tag_and_difficulty(client):
    _create(client)  # Barbell Back Squat / Squat / intermediate / Barbell
    _create(
        client,
        name="Goblet Squat",
        difficulty="beginner",
        equipment=["Dumbbell", "Kettlebell"],
        tags=["beginner-friendly"],
    )
    _create(
        client,
        name="Single-Leg RDL",
        movement_pattern="Hinge",
        difficulty="intermediate",
        unilateral=True,
        primary_muscles=["Hamstrings", "Glutes"],
        secondary_muscles=["Core"],
        equipment=["Dumbbell", "Bodyweight"],
        tags=["knee-friendly"],
    )
    _create(
        client,
        name="Push-Up",
        movement_pattern="Push Horizontal",
        difficulty="beginner",
        primary_muscles=["Chest"],
        equipment=["Bodyweight"],
        tags=["beginner-friendly", "home-gym"],
    )

    by_pattern = client.get("/exercises", params={"movement_pattern": "Hinge"}).json()
    assert [e["name"] for e in by_pattern] == ["Single-Leg RDL"]

    by_muscle = client.get("/exercises", params={"muscle_group": "Glutes"}).json()
    assert {e["name"] for e in by_muscle} == {"Barbell Back Squat", "Goblet Squat", "Single-Leg RDL"}

    by_muscle_role = client.get(
        "/exercises", params={"muscle_group": "Core", "muscle_role": "secondary"}
    ).json()
    assert [e["name"] for e in by_muscle_role] == ["Single-Leg RDL"]

    by_equipment_any = client.get("/exercises", params={"equipment": "Dumbbell"}).json()
    assert {e["name"] for e in by_equipment_any} == {"Goblet Squat", "Single-Leg RDL"}

    by_tag = client.get("/exercises", params={"tag": "beginner-friendly"}).json()
    assert {e["name"] for e in by_tag} == {"Goblet Squat", "Push-Up"}

    by_difficulty = client.get("/exercises", params={"difficulty": "beginner"}).json()
    assert {e["name"] for e in by_difficulty} == {"Goblet Squat", "Push-Up"}

    # combined filters (AND across filter types) — the PROJECT_SPEC "done when" scenario:
    # "beginner-friendly hinge exercises using only dumbbells"
    combined = client.get(
        "/exercises",
        params={
            "movement_pattern": "Hinge",
            "difficulty": "intermediate",
            "equipment": "Dumbbell",
            "equipment_mode": "any",
        },
    ).json()
    assert [e["name"] for e in combined] == ["Single-Leg RDL"]


def test_equipment_subset_mode_only_dumbbells(client):
    _create(client, name="Barbell Back Squat", equipment=["Barbell"])
    _create(client, name="Goblet Squat", equipment=["Dumbbell"])
    _create(client, name="DB + KB combo", equipment=["Dumbbell", "Kettlebell"])
    _create(client, name="Bodyweight Squat", equipment=[])

    resp = client.get(
        "/exercises", params={"equipment": "Dumbbell", "equipment_mode": "subset"}
    ).json()
    # only exercises whose *entire* equipment list is within {Dumbbell} qualify;
    # bodyweight (empty equipment) is trivially a subset too.
    assert {e["name"] for e in resp} == {"Goblet Squat", "Bodyweight Squat"}


def test_list_reference_tables(client):
    _create(client)
    assert {p["name"] for p in client.get("/movement-patterns").json()} == {"Squat"}
    assert {m["name"] for m in client.get("/muscle-groups").json()} == {"Quads", "Glutes", "Hamstrings"}
    assert {e["name"] for e in client.get("/equipment").json()} == {"Barbell"}
