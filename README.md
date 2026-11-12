# Med Reminder App (ADHD Child Support)

This workspace provides:

1. A **Python backend** that tracks each day's medication reminder, authenticates every device, and records an audit log.
2. An **iOS Swift app shell** that blocks apps during the medication window and unblocks them once a parent confirms.
3. A **blueprint** for the iOS Screen Time integration ([docs/ios_blueprint.md](docs/ios_blueprint.md)).

## Important Apple Platform Note

iOS Screen Time controls can't be managed from Python. On-device control uses Apple's
`FamilyControls`, `ManagedSettings` and `DeviceActivity` frameworks. The backend coordinates
reminder state, logs confirmations, and records notifications for parents.

## Flow

1. A parent creates a guardian account and adds a child (reminder time, window length, timezone).
2. The child's phone is paired with the child's device token; the parent's phone with the guardian token.
3. When the window opens, the DeviceActivity extension blocks apps on the child's phone.
4. The child taps **I Took My Medication**. The backend records it once and adds a notification for the parent.
5. The parent confirms on **their own phone** (the backend rejects confirmations from a child's token).
6. The child's app sees the confirmation (on open, or by polling while open) and lifts the block.

The day resets at the child's local midnight. Before today's window opens, apps are not blocked.

## Quick Start (Backend)

From `backend/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest
uvicorn app.main:create_app --factory --reload
```

API docs: `http://127.0.0.1:8000/docs`. Data is stored in SQLite at `med_reminder.db`
(override with the `MED_REMINDER_DB` environment variable).

### Setting up a family

```powershell
# 1. Create the guardian account. Save the returned "token" (shown once).
curl -X POST http://127.0.0.1:8000/guardians -H "Content-Type: application/json" -d '{\"display_name\": \"Parent\"}'

# 2. Add a child. Save the returned "device_token": it's the pairing code for the child's phone.
curl -X POST http://127.0.0.1:8000/children -H "Authorization: Bearer <guardian token>" -H "Content-Type: application/json" `
  -d '{\"display_name\": \"Alex\", \"reminder_time\": \"08:00\", \"window_minutes\": 60, \"timezone\": \"America/New_York\"}'

# Lost the child's pairing code? Issue a new one (the old one stops working):
curl -X POST http://127.0.0.1:8000/children/<child_id>/device-token -H "Authorization: Bearer <guardian token>"
```

## API summary

| Endpoint | Who | Purpose |
|---|---|---|
| `POST /guardians` | anyone | Create a guardian account; returns its token |
| `GET /me` | any token | Role, and the child profile or the guardian's children |
| `POST /children` | guardian | Add a child; returns the child's device token |
| `POST /children/{id}/device-token` | guardian | Re-issue the child's pairing code |
| `GET /reminders/state` | child | Today's state for this child |
| `POST /reminders/mark-taken` | child | Child marks the dose (idempotent) |
| `GET /reminders/state/{id}` | guardian | A child's state |
| `POST /reminders/confirm` | guardian | Confirm the dose; lifts the restriction |
| `GET /notifications` | guardian | The guardian's own notifications |

## Not done yet

- **Push delivery (APNs).** Notifications are recorded in an outbox; the parent app polls instead of receiving a push.
- **Choosing which apps to block.** The shield blocks all app and web categories. A parent-only `FamilyActivityPicker` is the next step.

## Key Files

- Backend app factory and routes: [backend/app/main.py](backend/app/main.py)
- Reminder logic: [backend/app/reminder_engine.py](backend/app/reminder_engine.py)
- Persistence: [backend/app/store.py](backend/app/store.py)
- Notification outbox: [backend/app/notification.py](backend/app/notification.py)
- iOS setup notes: [ios/README.md](ios/README.md)
- Xcode setup checklist: [docs/xcode_setup_checklist.md](docs/xcode_setup_checklist.md)
