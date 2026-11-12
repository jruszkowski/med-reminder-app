from conftest import auth


def test_default_state_is_pending_and_restricted_inside_window(client, family) -> None:
    _, _, child_token = family
    state = client.get("/reminders/state", headers=auth(child_token)).json()
    assert state["status"] == "pending"
    assert state["screen_time_should_be_restricted"] is True


def test_child_mark_then_adult_confirm_clears_restriction(client, family) -> None:
    guardian_token, child_id, child_token = family

    after_child = client.post("/reminders/mark-taken", headers=auth(child_token)).json()
    assert after_child["status"] == "child_marked_taken"
    assert after_child["screen_time_should_be_restricted"] is True

    after_adult = client.post("/reminders/confirm", json={"child_id": child_id}, headers=auth(guardian_token)).json()
    assert after_adult["status"] == "adult_confirmed"
    assert after_adult["screen_time_should_be_restricted"] is False


def test_not_restricted_before_window_opens(client, clock, family) -> None:
    _, _, child_token = family
    clock.set_utc(2026, 11, 12, 12, 0)  # 07:00 New York
    state = client.get("/reminders/state", headers=auth(child_token)).json()
    assert state["screen_time_should_be_restricted"] is False


def test_day_rolls_over_at_childs_local_midnight_not_utc(client, clock, family) -> None:
    guardian_token, child_id, _ = family
    client.post("/reminders/confirm", json={"child_id": child_id}, headers=auth(guardian_token))

    clock.set_utc(2026, 11, 13, 1, 0)  # 20:00 New York, already Nov 13 in UTC
    state = client.get(f"/reminders/state/{child_id}", headers=auth(guardian_token)).json()
    assert state["date_key"] == "2026-11-12"
    assert state["status"] == "adult_confirmed"
    assert state["screen_time_should_be_restricted"] is False

    clock.set_utc(2026, 11, 13, 5, 30)  # 00:30 New York on Nov 13
    state = client.get(f"/reminders/state/{child_id}", headers=auth(guardian_token)).json()
    assert state["date_key"] == "2026-11-13"
    assert state["status"] == "pending"
    assert state["screen_time_should_be_restricted"] is False  # window hasn't opened yet


def test_repeated_marks_notify_once_and_keep_first_timestamp(client, clock, family) -> None:
    guardian_token, _, child_token = family
    first = client.post("/reminders/mark-taken", headers=auth(child_token)).json()
    clock.set_utc(2026, 11, 12, 14, 5)
    second = client.post("/reminders/mark-taken", headers=auth(child_token)).json()
    assert second["child_marked_at"] == first["child_marked_at"]
    assert len(client.get("/notifications", headers=auth(guardian_token)).json()) == 1


def test_marking_after_confirmation_does_not_change_state(client, family) -> None:
    guardian_token, child_id, child_token = family
    client.post("/reminders/confirm", json={"child_id": child_id}, headers=auth(guardian_token))
    state = client.post("/reminders/mark-taken", headers=auth(child_token)).json()
    assert state["status"] == "adult_confirmed"
    assert client.get("/notifications", headers=auth(guardian_token)).json() == []


def test_child_cannot_confirm(client, family) -> None:
    _, child_id, child_token = family
    response = client.post("/reminders/confirm", json={"child_id": child_id}, headers=auth(child_token))
    assert response.status_code == 403


def test_requests_without_token_are_rejected(client, family) -> None:
    _, child_id, _ = family
    assert client.post("/reminders/confirm", json={"child_id": child_id}).status_code == 401
    assert client.get("/reminders/state").status_code == 401
    assert client.get("/notifications").status_code == 401
    assert client.get("/reminders/state", headers=auth("not-a-real-token")).status_code == 401


def test_other_guardian_cannot_see_or_confirm_child(client, family) -> None:
    _, child_id, _ = family
    stranger = client.post("/guardians", json={"display_name": "Stranger"}).json()["token"]
    assert client.post("/reminders/confirm", json={"child_id": child_id}, headers=auth(stranger)).status_code == 404
    assert client.get(f"/reminders/state/{child_id}", headers=auth(stranger)).status_code == 404
    assert client.post(f"/children/{child_id}/device-token", headers=auth(stranger)).status_code == 404


def test_children_get_server_generated_ids_and_cannot_be_overwritten(client, family) -> None:
    guardian_token, child_id, _ = family
    second = client.post(
        "/children",
        json={"display_name": "Sam", "reminder_time": "07:30", "timezone": "America/New_York"},
        headers=auth(guardian_token),
    ).json()
    assert second["child"]["child_id"] != child_id
    me = client.get("/me", headers=auth(guardian_token)).json()
    assert {c["display_name"] for c in me["children"]} == {"Alex", "Sam"}


def test_child_me_returns_own_schedule(client, family) -> None:
    _, child_id, child_token = family
    me = client.get("/me", headers=auth(child_token)).json()
    assert me["role"] == "child"
    assert me["child"]["child_id"] == child_id
    assert me["child"]["reminder_time"] == "08:00:00"
    assert me["child"]["window_minutes"] == 60


def test_reissued_device_token_revokes_old_one(client, family) -> None:
    guardian_token, child_id, old_token = family
    new_token = client.post(f"/children/{child_id}/device-token", headers=auth(guardian_token)).json()["device_token"]
    assert client.get("/reminders/state", headers=auth(old_token)).status_code == 401
    assert client.get("/reminders/state", headers=auth(new_token)).status_code == 200


def test_invalid_child_settings_rejected(client, family) -> None:
    guardian_token, _, _ = family
    bad_tz = {"display_name": "X", "reminder_time": "08:00", "timezone": "Mars/Olympus"}
    past_midnight = {"display_name": "X", "reminder_time": "23:30", "window_minutes": 60, "timezone": "UTC"}
    too_short = {"display_name": "X", "reminder_time": "08:00", "window_minutes": 5, "timezone": "UTC"}
    for body in (bad_tz, past_midnight, too_short):
        assert client.post("/children", json=body, headers=auth(guardian_token)).status_code == 422


def test_state_survives_restart(tmp_path, clock) -> None:
    from fastapi.testclient import TestClient

    from app.main import create_app

    db = str(tmp_path / "persist.db")
    first = TestClient(create_app(db_path=db, clock=clock))
    guardian = first.post("/guardians", json={"display_name": "P"}).json()["token"]
    child = first.post(
        "/children",
        json={"display_name": "A", "reminder_time": "08:00", "timezone": "America/New_York"},
        headers=auth(guardian),
    ).json()
    first.post("/reminders/confirm", json={"child_id": child["child"]["child_id"]}, headers=auth(guardian))

    second = TestClient(create_app(db_path=db, clock=clock))
    state = second.get("/reminders/state", headers=auth(child["device_token"])).json()
    assert state["status"] == "adult_confirmed"
