// Add this file to BOTH targets. The app and the extension apply the shield through this
// one type, so they can never disagree about what "restricted" means.
import Foundation
import ManagedSettings

enum MedicationShield {
    private static let store = ManagedSettingsStore(named: .daily)

    /// Blocks every app category. Fails closed: there is no "empty" restriction.
    ///
    /// NOTE: verify on a device that this does not also shield the MedicationReminder app
    /// itself. If it does, the child can't reach the check-in button; the fix is a
    /// parent-chosen FamilyActivitySelection applied with `.specific(...)` / `.all(except:)`.
    static func apply() {
        store.shield.applicationCategories = .all(except: Set())
        store.shield.webDomainCategories = .all(except: Set())
    }

    static func clear() {
        store.clearAllSettings()
    }
}

/// Small piece of state shared with the extension through the App Group.
enum SharedPolicyState {
    private static var defaults: UserDefaults? { UserDefaults(suiteName: SharedConstants.appGroupID) }
    private static let confirmedDateKeyKey = "confirmedDateKey"

    /// Backend `date_key` (child's local date, yyyy-MM-dd) for which an adult has confirmed the dose.
    static var confirmedDateKey: String? {
        get { defaults?.string(forKey: confirmedDateKeyKey) }
        set { defaults?.set(newValue, forKey: confirmedDateKeyKey) }
    }

    /// Today's date in the device's timezone, in the same format as the backend's `date_key`.
    /// The child's profile timezone on the backend should match the device's timezone.
    static func todayDateKey(now: Date = Date()) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = .current
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: now)
    }
}
