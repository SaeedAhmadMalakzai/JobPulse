import SwiftUI

/// Jobs the engine honestly skipped because their form needed answers it won't
/// fabricate (Google Forms, external ATS). Open each to apply manually.
struct NeedsReviewView: View {
    @EnvironmentObject var state: AppState

    var body: some View {
        Group {
            if state.needsReview.isEmpty {
                EmptyState(icon: "checkmark.seal.fill", title: "Nothing needs review",
                           message: "Jobs that require a manual application (Google Forms, company sites) will collect here with a direct link.",
                           tint: Theme.Status.success)
            } else {
                ScrollView {
                    LazyVStack(spacing: Theme.Space.sm) {
                        ForEach(state.needsReview) { item in
                            RowCard {
                                VStack(alignment: .leading, spacing: Theme.Space.sm) {
                                    HStack(spacing: Theme.Space.sm) {
                                        IconChip(icon: "exclamationmark", tint: Theme.Status.warning)
                                        Text(item.title).font(.headline)
                                        if !item.site.isEmpty {
                                            Text(item.site)
                                                .font(.caption.weight(.semibold))
                                                .padding(.horizontal, 7).padding(.vertical, 2)
                                                .background(Theme.Status.info.opacity(0.15), in: Capsule())
                                        }
                                        Spacer()
                                        if let url = URL(string: item.url), !item.url.isEmpty {
                                            Link(destination: url) {
                                                Label("Open & apply", systemImage: "arrow.up.right.square.fill")
                                            }
                                            .buttonStyle(.borderedProminent)
                                            .controlSize(.small)
                                        }
                                    }
                                    if !item.reasons.isEmpty {
                                        Text(item.reasons.joined(separator: " · "))
                                            .font(.callout).foregroundStyle(.secondary)
                                    }
                                    if !item.url.isEmpty {
                                        Text(item.url)
                                            .font(.caption.monospaced())
                                            .foregroundStyle(.tertiary)
                                            .lineLimit(1).truncationMode(.middle)
                                    }
                                }
                            }
                        }
                    }
                    .padding(Theme.Space.md)
                }
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
