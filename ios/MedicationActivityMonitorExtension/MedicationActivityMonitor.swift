import DeviceActivity
import Foundation

// Shared/SharedConstants.swift and Shared/MedicationShield.swift must also be in this target.
final class MedicationActivityMonitor: DeviceActivityMonitor {
    override func intervalDidStart(for activity: DeviceActivityName) {
        super.intervalDidStart(for: activity)
        guard activity == .medicationDaily else { return }

        // If an adult already confirmed today's dose (e.g. before the window opened), don't block.
        if SharedPolicyState.confirmedDateKey == SharedPolicyState.todayDateKey() { return }
        MedicationShield.apply()
    }

    override func intervalDidEnd(for activity: DeviceActivityName) {
        super.intervalDidEnd(for: activity)
        // Intentionally does nothing: the shield stays on past the window until an adult
        // confirms and the app clears it (see ScreenTimePolicyManager.syncFromState).
    }
}
