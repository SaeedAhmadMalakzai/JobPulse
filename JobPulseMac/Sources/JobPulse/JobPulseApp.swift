import SwiftUI

@main
struct JobPulseApp: App {
    @StateObject private var state = AppState()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(state)
                .tint(Theme.brand)
                .frame(minWidth: 940, minHeight: 600)
        }
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified)
        .commands {
            CommandGroup(replacing: .newItem) {}  // no "New Window"
            CommandMenu("Run") {
                Button(state.dryRun ? "Run (Dry)" : "Run") { state.run() }
                    .keyboardShortcut(.return, modifiers: .command)
                    .disabled(state.isBusy)
                Button("Stop") { state.stop() }
                    .keyboardShortcut(".", modifiers: .command)
                    .disabled(!state.isBusy)
                Divider()
                Toggle("Dry run", isOn: Binding(get: { state.dryRun }, set: { state.dryRun = $0 }))
            }
        }
    }
}
