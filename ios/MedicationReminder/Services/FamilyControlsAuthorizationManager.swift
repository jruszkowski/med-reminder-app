import FamilyControls
import Foundation

@MainActor
final class FamilyControlsAuthorizationManager: ObservableObject {
    @Published private(set) var isAuthorized = false
    @Published private(set) var errorMessage: String?

    private let center = AuthorizationCenter.shared

    /// `.child` authorization: a parent approves it with their Apple ID through Family Sharing,
    /// and the child can't revoke it or delete the app without the parent.
    func requestAuthorization() async {
        if center.authorizationStatus == .approved {
            isAuthorized = true
            return
        }
        do {
            try await center.requestAuthorization(for: .child)
            isAuthorized = center.authorizationStatus == .approved
            errorMessage = isAuthorized ? nil : "Screen Time access was not approved."
        } catch {
            isAuthorized = false
            errorMessage = error.localizedDescription
        }
    }
}
