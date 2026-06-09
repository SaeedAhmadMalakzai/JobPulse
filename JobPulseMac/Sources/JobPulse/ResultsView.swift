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
            if state.applied.isEmpty {
                EmptyState(icon: "checklist", text: "No applications yet this run.")
            } else {
                List(state.applied.filter { matches($0.title, $0.site) }) { job in
                    HStack {
                        Image(systemName: "checkmark.circle.fill").foregroundStyle(Theme.Status.success)
                        VStack(alignment: .leading) {
                            Text(job.title).fontWeight(.medium)
                            if !job.site.isEmpty { Text(job.site).font(.caption).foregroundStyle(.secondary) }
                        }
                    }
                }
            }
        }
    }

    private var skippedList: some View {
        Group {
            if state.skipped.isEmpty {
                EmptyState(icon: "minus.circle", text: "Nothing skipped this run.")
            } else {
                List(state.skipped.filter { matches($0.title, $0.reason) }) { job in
                    HStack {
                        Image(systemName: "minus.circle").foregroundStyle(.orange)
                        VStack(alignment: .leading) {
                            Text(job.title).fontWeight(.medium)
                            Text(job.reason).font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
            }
        }
    }

    private func matches(_ a: String, _ b: String) -> Bool {
        filter.isEmpty || a.localizedCaseInsensitiveContains(filter) || b.localizedCaseInsensitiveContains(filter)
    }
}

struct EmptyState: View {
    let icon: String
    let text: String
    var body: some View {
        VStack(spacing: Theme.Space.md) {
            Image(systemName: icon).font(.system(size: 40)).foregroundStyle(.tertiary)
            Text(text).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
