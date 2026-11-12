import Foundation

/// Decides what this device is: unpaired, a child's phone, or a parent's phone.
/// The role comes from the backend token, so a child's device can never act as a guardian.
@MainActor
final class AppSession: ObservableObject {
    enum Phase {
        case loading
        case needsPairing(message: String?)
        case child(ChildProfile)
        case guardian([ChildProfile])
        case failed(message: String)
    }

    @Published private(set) var phase: Phase = .loading

    private let client: BackendClient

    init(client: BackendClient = BackendClient()) {
        self.client = client
    }

    func load() async {
        guard CredentialStore.load() != nil else {
            phase = .needsPairing(message: nil)
            return
        }
        do {
            let me = try await client.me()
            switch me.role {
            case .child:
                if let child = me.child { phase = .child(child) } else { phase = .needsPairing(message: "Pairing failed.") }
            case .guardian:
                phase = .guardian(me.children)
            }
        } catch BackendError.unauthorized {
            CredentialStore.delete()
            phase = .needsPairing(message: BackendError.unauthorized.errorDescription)
        } catch {
            // Keep the saved code: this is usually just the network. The UI offers Retry.
            phase = .failed(message: error.localizedDescription)
        }
    }

    func pair(code: String) async {
        let trimmed = code.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        do {
            try CredentialStore.save(trimmed)
        } catch {
            phase = .needsPairing(message: "Couldn't save the pairing code: \(error.localizedDescription)")
            return
        }
        phase = .loading
        await load()
    }
}
