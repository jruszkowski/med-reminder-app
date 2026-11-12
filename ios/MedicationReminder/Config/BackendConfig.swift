import Foundation

enum BackendConfig {
    /// Set `BACKEND_BASE_URL` in the app target's Info.plist (e.g. https://meds.example.com).
    /// Physical devices need HTTPS: App Transport Security blocks plain HTTP to non-local hosts,
    /// and 127.0.0.1 on a phone is the phone itself.
    static let baseURL: URL = {
        if let value = Bundle.main.object(forInfoDictionaryKey: "BACKEND_BASE_URL") as? String,
           !value.isEmpty,
           let url = URL(string: value) {
            return url
        }
        #if targetEnvironment(simulator)
        return URL(string: "http://127.0.0.1:8000")!
        #else
        fatalError("Set BACKEND_BASE_URL (an https:// URL) in Info.plist for device builds.")
        #endif
    }()
}
