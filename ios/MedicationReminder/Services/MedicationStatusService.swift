import Foundation

/// Child-device view of today's reminder.
@MainActor
final class MedicationStatusService: ObservableObject {
    @Published private(set) var state: ReminderState?
    @Published private(set) var errorMessage: String?

    private let client: BackendClient

    init(client: BackendClient = BackendClient()) {
        self.client = client
    }

    /// Returns the fresh state, or nil if the request failed (errorMessage is set).
    @discardableResult
    func refresh() async -> ReminderState? {
        await callAndStore { try await client.childState() }
    }

    @discardableResult
    func markTaken() async -> ReminderState? {
        await callAndStore { try await client.markTaken() }
    }

    private func callAndStore(_ block: () async throws -> ReminderState) async -> ReminderState? {
        do {
            let value = try await block()
            state = value
            errorMessage = nil
            return value
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }
}
