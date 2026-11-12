# iOS App Shell

Swift starter for the Medication Reminder app. One app serves both roles; which one a device
plays comes from the token it's paired with, so a child's phone can never act as a parent's.

## Structure

- `Shared/` — **add to both the app and the extension targets**
  - `SharedConstants.swift` — App Group id, activity name, ManagedSettings store name
  - `MedicationShield.swift` — the one place the shield is applied or cleared; App Group state
- `MedicationActivityMonitorExtension/` — blocks apps when the daily window opens (unless today is already confirmed)
- `MedicationReminder/`
  - `App/MedicationReminderApp.swift` — entry point
  - `Views/RootView.swift` — routes to pairing, child, or parent screens
  - `Views/PairingView.swift` — one-time pairing code entry (stored in the Keychain)
  - `Views/ChildCheckInView.swift` — child's check-in; polls while open
  - `Views/AdultConfirmView.swift` — parent's list of children with a two-step confirm
  - `Services/` — startup/sync, schedule, authorization (`.child`), policy, parent flow
  - `Networking/BackendClient.swift`, `Security/CredentialStore.swift`, `Config/BackendConfig.swift`

## Setup in Xcode

Follow [docs/xcode_setup_checklist.md](../docs/xcode_setup_checklist.md).

## Behavior notes

- The child's schedule (reminder time, window length) comes from the backend, not from hardcoded hours.
- The shield is only changed after a successful backend response, so losing the network
  leaves the phone in whatever state it was (blocked stays blocked).
- After a parent confirms, the child's block lifts the next time the child app is opened
  or within ~20 seconds if it's already open. A silent push would remove that delay.
- **Verify on a device** that blocking all categories does not also block this app. If it
  does, the child can't check in; switch to a parent-chosen `FamilyActivitySelection`.
