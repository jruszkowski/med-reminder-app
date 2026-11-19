import Foundation

enum BackendConfig {
    private static let storedKey = "backendBaseURL"

    /// Server address, in priority order: the one entered on the pairing screen,
    /// `BACKEND_BASE_URL` from Info.plist, then localhost in the Simulator.
    /// Physical devices need an https:// address.
    static var baseURL: URL? {
        if let stored = UserDefaults.standard.string(forKey: storedKey), let url = URL(string: stored) {
            return url
        }
        if let value = Bundle.main.object(forInfoDictionaryKey: "BACKEND_BASE_URL") as? String,
           !value.isEmpty,
           let url = URL(string: value) {
            return url
        }
        #if targetEnvironment(simulator)
        return URL(string: "http://127.0.0.1:8000")
        #else
        return nil
        #endif
    }

    static func save(_ url: URL) {
        UserDefaults.standard.set(url.absoluteString, forKey: storedKey)
    }

    /// Accepts "https://host[:port][/path]". Plain http is only allowed in the Simulator.
    static func validated(_ text: String) -> URL? {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: trimmed), let scheme = url.scheme?.lowercased(), url.host != nil else { return nil }
        #if targetEnvironment(simulator)
        return ["http", "https"].contains(scheme) ? url : nil
        #else
        return scheme == "https" ? url : nil
        #endif
    }
}
