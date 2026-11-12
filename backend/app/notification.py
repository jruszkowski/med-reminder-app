import sqlite3
from datetime import datetime

from .models import ChildProfile, NotificationEvent
from .store import Store


class NotificationGateway:
    """Records guardian notifications in an outbox.

    Real delivery (APNs) is not wired up yet: when it is, send the push here after
    recording the event. Guardians can read their own outbox via GET /notifications.
    """

    def __init__(self, store: Store) -> None:
        self._store = store

    def notify_guardian_med_marked(
        self, conn: sqlite3.Connection, child: ChildProfile, date_key: str, now: datetime
    ) -> NotificationEvent:
        event = NotificationEvent(
            guardian_id=child.guardian_id,
            child_id=child.child_id,
            date_key=date_key,
            title=f"{child.display_name} marked their medication as taken",
            body="Please verify the dose and confirm it to unlock screen access.",
            created_at=now,
        )
        self._store.insert_notification(conn, event)
        return event
