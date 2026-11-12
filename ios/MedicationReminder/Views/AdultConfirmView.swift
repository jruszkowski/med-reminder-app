import SwiftUI

/// Runs on the parent's phone (guardian token). The backend refuses confirmations from a
/// child's device token, so this screen being present in the app is not a bypass.
struct AdultConfirmView: View {
    @StateObject private var approvalFlow: AdultApprovalFlow
    @State private var pendingConfirmation: ChildProfile?

    init(children: [ChildProfile]) {
        _approvalFlow = StateObject(wrappedValue: AdultApprovalFlow(children: children))
    }

    var body: some View {
        NavigationStack {
            List {
                if let errorMessage = approvalFlow.errorMessage {
                    Text(errorMessage).foregroundStyle(.red)
                }
                if approvalFlow.children.isEmpty {
                    Text("No children set up yet.").foregroundStyle(.secondary)
                }
                ForEach(approvalFlow.children) { child in
                    let state = approvalFlow.states[child.childId]
                    VStack(alignment: .leading, spacing: 8) {
                        Text(child.displayName).font(.headline)
                        Text(state?.status.displayText ?? "Loading…").foregroundStyle(.secondary)
                        if let state, state.status != .adultConfirmed {
                            Button("Confirm Dose") { pendingConfirmation = child }
                                .buttonStyle(.borderedProminent)
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
            .navigationTitle("Medication")
            .refreshable { await approvalFlow.refresh() }
            .task {
                // Light polling while open; replace with APNs once push delivery exists.
                while !Task.isCancelled {
                    await approvalFlow.refresh()
                    try? await Task.sleep(for: .seconds(30))
                }
            }
            // Second, deliberate tap before unlocking the child's phone.
            .confirmationDialog(
                "Confirm medication",
                isPresented: Binding(
                    get: { pendingConfirmation != nil },
                    set: { if !$0 { pendingConfirmation = nil } }
                ),
                presenting: pendingConfirmation
            ) { child in
                Button("Yes, \(child.displayName) took today's dose") {
                    Task { await approvalFlow.approveDose(childId: child.childId) }
                }
                Button("Cancel", role: .cancel) {}
            } message: { child in
                Text("This unlocks \(child.displayName)'s apps for the rest of today.")
            }
        }
    }
}
