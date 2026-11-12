import Foundation

final class ScreenTimePolicyManager {
    /// Applies the backend's verdict. Only called after a successful backend response, so a
    /// network failure leaves whatever shield is currently in place untouched (fails closed).
    func syncFromState(_ state: ReminderState) {
        if state.status == .adultConfirmed {
            SharedPolicyState.confirmedDateKey = state.dateKey
        }
        if state.screenTimeShouldBeRestricted {
            MedicationShield.apply()
        } else {
            MedicationShield.clear()
        }
    }
}
