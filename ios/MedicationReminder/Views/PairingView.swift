import SwiftUI

/// One-time setup. The parent creates the child on the backend (POST /children) and enters
/// the returned `device_token` here on the child's phone; on their own phone they enter
/// their guardian token. There is no editable child id anywhere in the app.
struct PairingView: View {
    @ObservedObject var session: AppSession
    let message: String?

    @State private var serverAddress = BackendConfig.baseURL?.absoluteString ?? ""
    @State private var code = ""
    @State private var isPairing = false

    var body: some View {
        VStack(spacing: 16) {
            Text("Set Up This Device")
                .font(.title2)
                .bold()

            Text("Enter the server address and the pairing code from the parent setup.")
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)

            TextField("Server address (https://…)", text: $serverAddress)
                .textFieldStyle(.roundedBorder)
                .keyboardType(.URL)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()

            SecureField("Pairing code", text: $code)
                .textFieldStyle(.roundedBorder)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()

            Button {
                isPairing = true
                Task {
                    await session.pair(serverAddress: serverAddress, code: code)
                    isPairing = false
                }
            } label: {
                if isPairing { ProgressView() } else { Text("Pair") }
            }
            .buttonStyle(.borderedProminent)
            .disabled(code.isEmpty || serverAddress.isEmpty || isPairing)

            if let message {
                Text(message).foregroundStyle(.red)
            }
        }
        .padding()
    }
}
