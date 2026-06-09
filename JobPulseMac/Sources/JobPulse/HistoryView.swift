import SwiftUI

struct HistoryView: View {
    @EnvironmentObject var state: AppState

    var body: some View {
        Group {
            if state.history.isEmpty {
                EmptyState(icon: "clock.arrow.circlepath", title: "No run history yet",
                           message: "Each completed run records how many jobs were applied and skipped.")
            } else {
                ScrollView {
                    LazyVStack(spacing: Theme.Space.sm) {
                        ForEach(state.history) { run in
                            RowCard {
                                HStack(spacing: Theme.Space.md) {
                                    IconChip(icon: "clock", tint: .secondary)
                                    Text(formatted(run.at)).fontWeight(.medium)
                                    Spacer()
                                    metric("checkmark.circle.fill", "\(run.applied)", Theme.Status.success)
                                    metric("minus.circle", "\(run.skipped)", .orange)
                                }
                            }
                        }
                    }
                    .padding(Theme.Space.md)
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

    private func metric(_ icon: String, _ value: String, _ tint: Color) -> some View {
        Label(value, systemImage: icon)
            .font(.callout.weight(.semibold).monospacedDigit())
            .foregroundStyle(tint)
    }

    private func formatted(_ iso: String) -> String {
        let trimmed = iso.replacingOccurrences(of: "T", with: " ")
        return String(trimmed.prefix(16))
    }
}
