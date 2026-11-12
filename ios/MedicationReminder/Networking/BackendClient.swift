import Foundation

enum BackendError: LocalizedError {
    case notPaired
    case unauthorized
    case server(status: Int, detail: String?)
    case invalidResponse

    var errorDescription: String? {
        switch self {
        case .notPaired: return "This device isn't paired yet."
        case .unauthorized: return "This device's pairing code is no longer valid. Ask a parent for a new one."
        case .server(let status, let detail): return detail ?? "Server error (\(status))."
        case .invalidResponse: return "Unexpected response from the server."
        }
    }
}

final class BackendClient {
    private let session: URLSession
    private let tokenProvider: () -> String?
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()

    init(session: URLSession = .shared, tokenProvider: @escaping () -> String? = CredentialStore.load) {
        self.session = session
        self.tokenProvider = tokenProvider
    }

    func me() async throws -> MeResponse {
        try await send("GET", "me")
    }

    /// Child device: its own state (the child is identified by the device token, not an id).
    func childState() async throws -> ReminderState {
        try await send("GET", "reminders/state")
    }

    /// Child device: "I took my medication".
    func markTaken() async throws -> ReminderState {
        try await send("POST", "reminders/mark-taken")
    }

    /// Guardian device: one child's state.
    func state(childId: String) async throws -> ReminderState {
        try await send("GET", "reminders/state/\(childId)")
    }

    /// Guardian device: confirm the dose. The backend rejects this for child tokens.
    func confirmDose(childId: String) async throws -> ReminderState {
        try await send("POST", "reminders/confirm", body: ConfirmRequest(childId: childId))
    }

    private func send<T: Decodable>(_ method: String, _ path: String, body: (any Encodable)? = nil) async throws -> T {
        guard let token = tokenProvider() else { throw BackendError.notPaired }

        var request = URLRequest(url: BackendConfig.baseURL.appendingPathComponent(path))
        request.httpMethod = method
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try encoder.encode(body)
        }

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw BackendError.invalidResponse }
        switch http.statusCode {
        case 200..<300:
            return try decoder.decode(T.self, from: data)
        case 401:
            throw BackendError.unauthorized
        default:
            let detail = (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["detail"] as? String
            throw BackendError.server(status: http.statusCode, detail: detail)
        }
    }
}
