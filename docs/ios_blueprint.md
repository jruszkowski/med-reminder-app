# iOS Blueprint: Screen Time + Medication Verification

## Goal

When medication time starts, restrict distracting apps until medication is verified by an adult.

## Core Apple Components

1. **FamilyControls**
   - Parent authorizes monitoring/controls.
   - Child and guardian relationships are managed by Apple Family setup.

2. **DeviceActivity**
   - Defines schedule windows (for example, 8:00 AM medicine window).
   - Triggers monitoring extension callbacks.

3. **ManagedSettings**
   - Applies app/category restrictions during the medication window.
   - Clears restrictions only after adult confirmation.

## Suggested iOS Module Design

- `MedicationScheduleManager`
  - Reads schedule from backend.
  - Configures `DeviceActivity` intervals.

- `ScreenTimePolicyManager`
  - Applies and clears `ManagedSettingsStore` policies.

- `MedicationStatusService`
  - Calls backend endpoints:
    - `POST /reminders/mark-taken`
    - `POST /reminders/confirm`
    - `GET /reminders/state/{child_id}`

- `AdultApprovalFlow`
  - Receives push notification deep-link.
  - Shows confirmation UI.
  - Calls backend confirmation endpoint.

## Data Contract with Backend

- Child marks dose:
  - backend sets status to `child_marked_taken`
  - backend emits adult notification event
  - iOS keeps restrictions active

- Adult confirms dose:
  - backend sets status to `adult_confirmed`
  - iOS removes restrictions

## Safety / UX Notes

- Require a second confirmation tap for adult action.
- Include timestamp and optional photo/checklist for proof.
- Add grace period + escalation workflow if no adult confirmation arrives.
- Log every status transition for auditability.

