import Foundation

/// Guardian-device view: every child's state, and confirming a dose.
@MainActor
final class AdultApprovalFlow: ObservableObject {
    @Published private(set) var children: [ChildProfile]
    @Published private(set) var states: [String: ReminderState] = [:]
    @Published private(set) var errorMessage: String?

    private let client: BackendClient

    init(children: [ChildProfile], client: BackendClient = BackendClient()) {
        self.children = children
        self.client = client
    }

    func refresh() async {
        do {
            let me = try await client.me()
            children = me.children
            var fresh: [String: ReminderState] = [:]
            for child in me.children {
                fresh[child.childId] = try await client.state(childId: child.childId)
            }
            states = fresh
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func approveDose(childId: String) async {
        do {
            states[childId] = try await client.confirmDose(childId: childId)
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
