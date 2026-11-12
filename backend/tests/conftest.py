from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def set_utc(self, *args: int) -> None:
        self.now = datetime(*args, tzinfo=timezone.utc)


@pytest.fixture
def clock() -> FakeClock:
    # 2026-11-12 09:00 in New York (UTC-5): inside an 8:00 window.
    return FakeClock(datetime(2026, 11, 12, 14, 0, tzinfo=timezone.utc))


@pytest.fixture
def client(tmp_path, clock) -> TestClient:
    return TestClient(create_app(db_path=str(tmp_path / "test.db"), clock=clock))


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def family(client):
    """A guardian with one child (8:00-9:00 America/New_York). Returns (guardian_token, child_id, child_token)."""
    guardian = client.post("/guardians", json={"display_name": "Parent"}).json()
    created = client.post(
        "/children",
        json={"display_name": "Alex", "reminder_time": "08:00", "window_minutes": 60, "timezone": "America/New_York"},
        headers=auth(guardian["token"]),
    ).json()
    return guardian["token"], created["child"]["child_id"], created["device_token"]
