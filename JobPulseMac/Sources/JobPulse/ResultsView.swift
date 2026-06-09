import SwiftUI

struct ResultsView: View {
    @EnvironmentObject var state: AppState
    @State private var filter = ""
    @State private var tab = 0

    var body: some View {
        VStack(spacing: 0) {
            Picker("", selection: $tab) {
                Text("Applied (\(state.applied.count))").tag(0)
                Text("Skipped (\(state.skipped.count))").tag(1)
            }
            .pickerStyle(.segmented)
            .labelsHidden()
            .padding(Theme.Space.md)

            Divider()

            if tab == 0 { appliedList } else { skippedList }
        }
        .navigationTitle("Results")
        .searchable(text: $filter, placement: .toolbar, prompt: "Filter results")
    }

    private var appliedList: some View {
        Group {
            let items = state.applied.filter { matches($0.title, $0.site) }
            if items.isEmpty {
                EmptyState(icon: "checkmark.seal", title: "No applications yet",
                           message: "Jobs you successfully apply to this run will appear here.",
                           tint: Theme.Status.success)
            } else {
                rows {
                    ForEach(items) { job in
                        RowCard {
                            HStack(spacing: Theme.Space.sm) {
                                IconChip(icon: "checkmark", tint: Theme.Status.success)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(job.title).fontWeight(.medium)
                                    if !job.site.isEmpty {
                                        Text(job.site).font(.caption).foregroundStyle(.secondary)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    private var skippedList: some View {
        Group {
            let items = state.skipped.filter { matches($0.title, $0.reason) }
            if items.isEmpty {
                EmptyState(icon: "minus.circle", title: "Nothing skipped",
                           message: "Jobs skipped this run (duplicates, out of scope, etc.) show here.")
            } else {
                rows {
                    ForEach(items) { job in
                        RowCard {
                            HStack(spacing: Theme.Space.sm) {
                                IconChip(icon: "minus", tint: .orange)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(job.title).fontWeight(.medium)
                                    Text(job.reason).font(.caption).foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder private func rows<Content: View>(@ViewBuilder _ content: () -> Content) -> some View {
        ScrollView {
            LazyVStack(spacing: Theme.Space.sm) {
                content()
            }
            .padding(Theme.Space.md)
        }
    }

    private func matches(_ a: String, _ b: String) -> Bool {
        filter.isEmpty || a.localizedCaseInsensitiveContains(filter) || b.localizedCaseInsensitiveContains(filter)
    }
}
