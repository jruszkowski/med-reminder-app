import Combine
import Foundation

/// Child-device startup and ongoing sync. All shield changes go through `refreshAndSync`,
/// which only touches the shield after a successful backend response.
@MainActor
final class AppStartupCoordinator: ObservableObject {
    @Published private(set) var startupError: String?
    @Published private(set) var isStarted = false

    let statusService: MedicationStatusService
    private let authorizationManager: FamilyControlsAuthorizationManager
    private let scheduleManager: MedicationScheduleManager
    private let policyManager: ScreenTimePolicyManager
    private var cancellables: Set<AnyCancellable> = []

    init(
        statusService: MedicationStatusService = MedicationStatusService(),
        authorizationManager: FamilyControlsAuthorizationManager = FamilyControlsAuthorizationManager(),
        scheduleManager: MedicationScheduleManager = MedicationScheduleManager(),
        policyManager: ScreenTimePolicyManager = ScreenTimePolicyManager()
    ) {
        self.statusService = statusService
        self.authorizationManager = authorizationManager
        self.scheduleManager = scheduleManager
        self.policyManager = policyManager

        // Re-publish status changes so views only need to observe the coordinator.
        statusService.objectWillChange
            .sink { [weak self] _ in self?.objectWillChange.send() }
            .store(in: &cancellables)
    }

    func start(child: ChildProfile) async {
        await authorizationManager.requestAuthorization()
        guard authorizationManager.isAuthorized else {
            startupError = authorizationManager.errorMessage ?? "Screen Time access was not approved."
            return
        }

        do {
            try scheduleManager.startMonitoring(reminderTime: child.reminderTime, windowMinutes: child.windowMinutes)
        } catch {
            startupError = "Couldn't start the medication schedule: \(error.localizedDescription)"
            return
        }

        if await refreshAndSync() {
            startupError = nil
        } else {
            startupError = statusService.errorMessage ?? "Couldn't load today's reminder from the server."
        }
        isStarted = true
    }

    @discardableResult
    func refreshAndSync() async -> Bool {
        guard let state = await statusService.refresh() else { return false }
        policyManager.syncFromState(state)
        return true
    }

    func markTaken() async {
        if let state = await statusService.markTaken() {
            policyManager.syncFromState(state)
        }
    }
}
