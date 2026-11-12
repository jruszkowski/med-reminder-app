import SwiftUI

struct RootView: View {
    @ObservedObject var session: AppSession

    var body: some View {
        Group {
            switch session.phase {
            case .loading:
                ProgressView()
            case .needsPairing(let message):
                PairingView(session: session, message: message)
            case .child(let child):
                ChildCheckInView(child: child)
            case .guardian(let children):
                AdultConfirmView(children: children)
            case .failed(let message):
                VStack(spacing: 12) {
                    Text(message).foregroundStyle(.red).multilineTextAlignment(.center)
                    Button("Retry") { Task { await session.load() } }
                        .buttonStyle(.borderedProminent)
                }
                .padding()
            }
        }
        .task { await session.load() }
    }
}
