import SwiftUI

struct ChildCheckInView: View {
    let child: ChildProfile
    @StateObject private var coordinator = AppStartupCoordinator()

    @Environment(\.scenePhase) private var scenePhase

    /// How often to re-check while the app is open, so the block lifts soon after a parent confirms.
    private let pollInterval: Duration = .seconds(20)

    private var statusService: MedicationStatusService { coordinator.statusService }

    var body: some View {
        VStack(spacing: 16) {
            Text("Hi \(child.displayName)!")
                .font(.title2)
                .bold()

            if let state = statusService.state {
                Text(state.status.displayText)
                    .font(.headline)
                Text(state.screenTimeShouldBeRestricted ? "Apps are paused until a parent confirms." : "Apps are available.")
                    .foregroundStyle(.secondary)
            }

            Button("I Took My Medication") {
                Task { await coordinator.markTaken() }
            }
            .buttonStyle(.borderedProminent)
            .disabled(statusService.state?.status != .pending)

            if let startupError = coordinator.startupError {
                Text(startupError).foregroundStyle(.red)
            } else if let errorMessage = statusService.errorMessage {
                Text(errorMessage).foregroundStyle(.red)
            }
        }
        .padding()
        // Single startup path: authorization -> schedule -> state sync. No competing refresh.
        .task { await coordinator.start(child: child) }
        // Poll while visible; the child's phone has no push channel yet.
        .task {
            while !Task.isCancelled {
                try? await Task.sleep(for: pollInterval)
                if coordinator.isStarted { await coordinator.refreshAndSync() }
            }
        }
        .onChange(of: scenePhase) { _, newPhase in
            if newPhase == .active, coordinator.isStarted {
                Task { await coordinator.refreshAndSync() }
            }
        }
    }
}
