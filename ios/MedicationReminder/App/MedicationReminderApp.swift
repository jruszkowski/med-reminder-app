import SwiftUI

@main
struct MedicationReminderApp: App {
    @StateObject private var session = AppSession()

    var body: some Scene {
        WindowGroup {
            RootView(session: session)
        }
    }
}
