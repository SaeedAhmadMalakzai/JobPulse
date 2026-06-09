import SwiftUI

struct HistoryView: View {
    @EnvironmentObject var state: AppState

    var body: some View {
        Group {
            if state.history.isEmpty {
                EmptyState(icon: "clock", text: "No run history yet.")
            } else {
                List(state.history) { run in
                    HStack {
                        Image(systemName: "clock.arrow.circlepath").foregroundStyle(.secondary)
                        Text(formatted(run.at)).fontWeight(.medium)
                        Spacer()
                        Label("\(run.applied)", systemImage: "checkmark.circle.fill")
                            .foregroundStyle(Theme.Status.success)
                        Label("\(run.skipped)", systemImage: "minus.circle")
                            .foregroundStyle(.orange)
                    }
                    .padding(.vertical, 2)
                }
            }
        }
        .navigationTitle("History")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button { state.refreshData() } label: { Image(systemName: "arrow.clockwise") }
            }
        }
    }

    private func formatted(_ iso: String) -> String {
        // Engine stores ISO-ish timestamps; show date + HH:MM if parseable.
        let trimmed = iso.replacingOccurrences(of: "T", with: " ")
        return String(trimmed.prefix(16))
    }
}
