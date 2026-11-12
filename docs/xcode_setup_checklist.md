# Xcode Setup Checklist (MedicationReminder)

## 1) Create Targets

1. Create iOS app target: `MedicationReminder` (deployment target **iOS 17** or later)
2. Add extension target: `MedicationActivityMonitorExtension`
   - Template: **Device Activity Monitor Extension**

## 2) Capabilities / Entitlements

For **both** targets:

- **Family Controls** capability (distribution requires Apple's Family Controls entitlement approval)
- **App Groups**, with the same group id as `SharedConstants.appGroupID`
  (default `group.com.example.medicationreminder`; change both together)

App target only:

- Push Notifications, once APNs delivery is added

## 3) Info.plist and Signing

- Matching Team and bundle id prefix for the app and extension
- Confirm the extension is listed under the app target's "Frameworks, Libraries, and Embedded Content"
- Add `BACKEND_BASE_URL` (String) to the app's Info.plist. Use an `https://` URL for device builds;
  the Simulator falls back to `http://127.0.0.1:8000` when it's not set.

## 4) File Wiring

Add to **both** targets:

- `ios/Shared/SharedConstants.swift`
- `ios/Shared/MedicationShield.swift`

Add to the extension target:

- `ios/MedicationActivityMonitorExtension/MedicationActivityMonitor.swift`

Add everything under `ios/MedicationReminder/` to the app target.

## 5) First-Run Flow

1. Parent creates the guardian account and the child on the backend (see the main README).
2. On the child's phone: enter the child's `device_token` in the pairing screen.
3. The app requests Family Controls `.child` authorization; a parent approves with their Apple ID.
4. The app loads the child's schedule from the backend and starts daily monitoring.
5. When the window opens, the extension blocks apps.
6. Child taps **I Took My Medication**.
7. On the parent's phone (paired with the guardian token): confirm the dose.
8. The child's app picks up the confirmation and clears the block.

## 6) Backend Binding

- Run the backend with `uvicorn app.main:create_app --factory`
- Make sure devices can reach it over HTTPS (a tunnel such as ngrok or a hosted server works for testing)
