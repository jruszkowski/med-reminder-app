from __future__ import annotations

import hashlib
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .models import (
    ChildCreateRequest,
    ChildProfile,
    ReminderStateResponse,
    ReminderStatus,
    Role,
)
from .notification import NotificationGateway
from .store import Store, reminder_times

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NotFoundError(Exception):
    """Unknown resource, or one the caller is not allowed to see (deliberately indistinguishable)."""


@dataclass(frozen=True)
class Principal:
    role: Role
    subject_id: str  # guardian_id or child_id


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class ReminderEngine:
    def __init__(self, store: Store, notifications: NotificationGateway, clock: Clock = utc_now) -> None:
        self._store = store
        self._notifications = notifications
        self._clock = clock

    # --- accounts & auth ------------------------------------------------------

    def create_guardian(self, display_name: str) -> tuple[str, str]:
        """Returns (guardian_id, token)."""
        guardian_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(32)
        now = self._clock()
        with self._store.transaction() as conn:
            self._store.insert_guardian(conn, guardian_id, display_name, now)
            self._store.insert_token(conn, _hash_token(token), Role.guardian.value, guardian_id, now)
        return guardian_id, token

    def create_child(self, guardian_id: str, request: ChildCreateRequest) -> tuple[ChildProfile, str]:
        """Child ids are generated server-side, so an existing child can never be overwritten."""
        child = ChildProfile(child_id=str(uuid.uuid4()), guardian_id=guardian_id, **request.model_dump())
        token = secrets.token_urlsafe(32)
        now = self._clock()
        with self._store.transaction() as conn:
            self._store.insert_child(conn, child, now)
            self._store.insert_token(conn, _hash_token(token), Role.child.value, child.child_id, now)
        return child, token

    def reissue_child_token(self, guardian_id: str, child_id: str) -> str:
        """Revokes the child's existing device tokens and returns a new pairing code."""
        token = secrets.token_urlsafe(32)
        with self._store.transaction() as conn:
            self._owned_child(conn, guardian_id, child_id)
            self._store.delete_tokens(conn, Role.child.value, child_id)
            self._store.insert_token(conn, _hash_token(token), Role.child.value, child_id, self._clock())
        return token

    def authenticate(self, token: str) -> Principal | None:
        with self._store.transaction() as conn:
            found = self._store.find_token(conn, _hash_token(token))
        if found is None:
            return None
        role, subject_id = found
        return Principal(role=Role(role), subject_id=subject_id)

    def get_child(self, child_id: str) -> ChildProfile:
        with self._store.transaction() as conn:
            child = self._store.get_child(conn, child_id)
        if child is None:
            raise NotFoundError(f"Unknown child_id '{child_id}'")
        return child

    def get_owned_child(self, guardian_id: str, child_id: str) -> ChildProfile:
        with self._store.transaction() as conn:
            return self._owned_child(conn, guardian_id, child_id)

    def list_children(self, guardian_id: str) -> list[ChildProfile]:
        with self._store.transaction() as conn:
            return self._store.list_children(conn, guardian_id)

    def list_notifications(self, guardian_id: str):
        with self._store.transaction() as conn:
            return self._store.list_notifications(conn, guardian_id)

    # --- reminder flow --------------------------------------------------------

    def mark_taken_by_child(self, child_id: str) -> ReminderStateResponse:
        with self._store.transaction() as conn:
            child = self._require_child(conn, child_id)
            date_key, now, starts_at = self._today(child)
            row = self._store.get_or_create_reminder(conn, child_id, date_key)
            status = ReminderStatus(row["status"])
            marked_at, confirmed_at = reminder_times(row)

            # Idempotent: repeated taps don't re-notify or move the timestamp.
            if status == ReminderStatus.pending:
                marked_at = now
                self._transition(conn, child, date_key, status, ReminderStatus.child_marked_taken,
                                 Role.child, child_id, marked_at, confirmed_at, now)
                self._notifications.notify_guardian_med_marked(conn, child, date_key, now)
                status = ReminderStatus.child_marked_taken
            return self._state(child, date_key, now, starts_at, status, marked_at, confirmed_at)

    def confirm_by_adult(self, guardian_id: str, child_id: str) -> ReminderStateResponse:
        """Only the child's guardian may confirm. Confirming straight from `pending` is allowed:
        the adult may have handed over the dose themselves."""
        with self._store.transaction() as conn:
            child = self._owned_child(conn, guardian_id, child_id)
            date_key, now, starts_at = self._today(child)
            row = self._store.get_or_create_reminder(conn, child_id, date_key)
            status = ReminderStatus(row["status"])
            marked_at, confirmed_at = reminder_times(row)

            if status != ReminderStatus.adult_confirmed:
                confirmed_at = now
                self._transition(conn, child, date_key, status, ReminderStatus.adult_confirmed,
                                 Role.guardian, guardian_id, marked_at, confirmed_at, now)
                status = ReminderStatus.adult_confirmed
            return self._state(child, date_key, now, starts_at, status, marked_at, confirmed_at)

    def current_state(self, child_id: str) -> ReminderStateResponse:
        with self._store.transaction() as conn:
            child = self._require_child(conn, child_id)
            date_key, now, starts_at = self._today(child)
            row = self._store.get_or_create_reminder(conn, child_id, date_key)
            marked_at, confirmed_at = reminder_times(row)
            return self._state(child, date_key, now, starts_at, ReminderStatus(row["status"]), marked_at, confirmed_at)

    # --- helpers --------------------------------------------------------------

    def _today(self, child: ChildProfile) -> tuple[str, datetime, datetime]:
        """The child's local date (the day resets at the child's midnight, not UTC's) and today's window start."""
        tz = ZoneInfo(child.timezone)
        now = self._clock()
        local_now = now.astimezone(tz)
        starts_at = datetime.combine(local_now.date(), child.reminder_time, tzinfo=tz)
        return local_now.date().isoformat(), now, starts_at

    @staticmethod
    def _state(
        child: ChildProfile,
        date_key: str,
        now: datetime,
        starts_at: datetime,
        status: ReminderStatus,
        marked_at: datetime | None,
        confirmed_at: datetime | None,
    ) -> ReminderStateResponse:
        # Restricted from the start of today's window until an adult confirms; open before the window.
        restricted = status != ReminderStatus.adult_confirmed and now >= starts_at
        return ReminderStateResponse(
            child_id=child.child_id,
            date_key=date_key,
            status=status,
            screen_time_should_be_restricted=restricted,
            reminder_starts_at=starts_at,
            child_marked_at=marked_at,
            adult_confirmed_at=confirmed_at,
        )

    def _transition(self, conn, child, date_key, from_status, to_status, actor_role, actor_id,
                    marked_at, confirmed_at, now) -> None:
        self._store.update_reminder(conn, child.child_id, date_key, to_status, marked_at, confirmed_at)
        self._store.log_transition(conn, child.child_id, date_key, from_status, to_status,
                                   actor_role.value, actor_id, now)

    def _require_child(self, conn, child_id: str) -> ChildProfile:
        child = self._store.get_child(conn, child_id)
        if child is None:
            raise NotFoundError(f"Unknown child_id '{child_id}'")
        return child

    def _owned_child(self, conn, guardian_id: str, child_id: str) -> ChildProfile:
        child = self._store.get_child(conn, child_id)
        if child is None or child.guardian_id != guardian_id:
            raise NotFoundError(f"Unknown child_id '{child_id}'")
        return child
