// Add this file to BOTH the MedicationReminder app target and the
// MedicationActivityMonitorExtension target, so the names are declared exactly once.
import DeviceActivity
import ManagedSettings

enum SharedConstants {
    /// Must match the App Group capability added to both targets in Xcode.
    static let appGroupID = "group.com.example.medicationreminder"
}

extension DeviceActivityName {
    static let medicationDaily = Self("MedicationDailyWindow")
}

extension ManagedSettingsStore.Name {
    static let daily = Self("MedicationDailyPolicy")
}
