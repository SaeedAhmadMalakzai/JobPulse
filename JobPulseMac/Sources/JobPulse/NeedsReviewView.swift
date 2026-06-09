import SwiftUI

/// Jobs the engine honestly skipped because their form needed answers it won't
/// fabricate. Open each to apply manually.
struct NeedsReviewView: View {
    @EnvironmentObject var state: AppState

    var body: some View {
        Group {
            if state.needsReview.isEmpty {
                EmptyState(icon: "checkmark.seal", text: "Nothing needs manual review. 🎉")
            } else {
                List(state.needsReview) { item in
                    Card {
                        VStack(alignment: .leading, spacing: Theme.Space.sm) {
                            HStack {
                                Text(item.title).font(.headline)
                                if !item.site.isEmpty {
                                    Text(item.site).font(.caption.weight(.semibold))
                                        .padding(.horizontal, 6).padding(.vertical, 2)
                                        .background(Theme.Status.info.opacity(0.15), in: Capsule())
                                }
                                Spacer()
                                if let url = URL(string: item.url), !item.url.isEmpty {
                                    Link(destination: url) {
                                        Label("Open & apply", systemImage: "arrow.up.right.square")
                                    }
                                }
                            }
                            if !item.reasons.isEmpty {
                                Text("Needs: " + item.reasons.joined(separator: ", "))
                                    .font(.callout).foregroundStyle(.secondary)
                            }
                        }
                    }
                    .listRowSeparator(.hidden)
                }
                .listStyle(.inset)
            }
        }
        .navigationTitle("Needs Review")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button { state.refreshData() } label: { Image(systemName: "arrow.clockwise") }
                    .help("Refresh")
            }
        }
    }
}
