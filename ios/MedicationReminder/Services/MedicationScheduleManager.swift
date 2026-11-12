import DeviceActivity
import Foundation

enum ScheduleError: LocalizedError {
    case invalidReminderTime(String)

    var errorDescription: String? {
        switch self {
        case .invalidReminderTime(let value): return "Invalid reminder time from server: \(value)"
        }
    }
}

final class MedicationScheduleManager {
    private let center = DeviceActivityCenter()

    /// Starts (or restarts) daily monitoring using the child's schedule from the backend.
    /// `reminderTime` is the backend's "HH:MM[:SS]" string; the backend guarantees the window
    /// ends before midnight and is at least 15 minutes (the DeviceActivity minimum).
    func startMonitoring(reminderTime: String, windowMinutes: Int) throws {
        let parts = reminderTime.split(separator: ":").compactMap { Int($0) }
        guard parts.count >= 2, (0..<24).contains(parts[0]), (0..<60).contains(parts[1]) else {
            throw ScheduleError.invalidReminderTime(reminderTime)
        }
        let startMinutes = parts[0] * 60 + parts[1]
        let endMinutes = min(startMinutes + windowMinutes, 24 * 60 - 1)

        let schedule = DeviceActivitySchedule(
            intervalStart: DateComponents(hour: parts[0], minute: parts[1]),
            intervalEnd: DateComponents(hour: endMinutes / 60, minute: endMinutes % 60),
            repeats: true
        )
        center.stopMonitoring([.medicationDaily])
        try center.startMonitoring(.medicationDaily, during: schedule)
    }

    func stopMonitoring() {
        center.stopMonitoring([.medicationDaily])
    }
}
