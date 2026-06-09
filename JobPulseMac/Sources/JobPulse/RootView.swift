import SwiftUI

enum SidebarItem: String, CaseIterable, Identifiable {
    case home = "Home"
    case results = "Results"
    case needsReview = "Needs Review"
    case history = "History"
    case settings = "Settings"

    var id: String { rawValue }
    var icon: String {
        switch self {
        case .home: return "bolt.fill"
        case .results: return "checklist"
        case .needsReview: return "exclamationmark.bubble"
        case .history: return "clock.arrow.circlepath"
        case .settings: return "gearshape"
        }
    }
}

struct RootView: View {
    @EnvironmentObject var state: AppState
    @State private var selection: SidebarItem? = .home

    var body: some View {
        NavigationSplitView {
            List(selection: $selection) {
                Section { row(.home) }
                Section("Activity") {
                    row(.results); row(.needsReview); row(.history)
                }
                Section("Setup") { row(.settings) }
            }
            .listStyle(.sidebar)
            .navigationSplitViewColumnWidth(min: 210, ideal: 228, max: 300)
            .safeAreaInset(edge: .top) { brandHeader }
            .safeAreaInset(edge: .bottom) { sidebarStatus }
        } detail: {
            detail
        }
    }

    private func row(_ item: SidebarItem) -> some View {
        Label {
            HStack {
                Text(item.rawValue)
                Spacer()
                if item == .needsReview, !state.needsReview.isEmpty {
                    Text("\(state.needsReview.count)")
                        .font(.caption2.weight(.bold))
                        .padding(.horizontal, 6).padding(.vertical, 2)
                        .background(Theme.Status.warning.opacity(0.22), in: Capsule())
                }
            }
        } icon: {
            Image(systemName: item.icon).foregroundStyle(Theme.brand)
        }
        .tag(item)
    }

    private var brandHeader: some View {
        HStack(spacing: 8) {
            ZStack {
                RoundedRectangle(cornerRadius: 7, style: .continuous)
                    .fill(LinearGradient(colors: [Color(red: 0.31, green: 0.27, blue: 0.90),
                                                  Color(red: 0.49, green: 0.23, blue: 0.93)],
                                         startPoint: .topLeading, endPoint: .bottomTrailing))
                    .frame(width: 26, height: 26)
                Image(systemName: "bolt.fill").font(.system(size: 12, weight: .bold)).foregroundStyle(.white)
            }
            Text("JobPulse").font(.headline)
            Spacer()
        }
        .padding(.horizontal, Theme.Space.md)
        .padding(.top, Theme.Space.sm)
        .padding(.bottom, 2)
    }

    @ViewBuilder private var detail: some View {
        switch selection ?? .home {
        case .home: HomeView()
        case .results: ResultsView()
        case .needsReview: NeedsReviewView()
        case .history: HistoryView()
        case .settings: SettingsView()
        }
    }

    private var sidebarStatus: some View {
        VStack(alignment: .leading, spacing: 5) {
            Divider().opacity(0.5)
            StatusPill(
                text: state.engineState.label,
                color: statusColor,
                pulsing: state.engineState.isBusy
            )
            if let last = state.history.first {
                Label("\(last.applied) applied · \(last.skipped) skipped",
                      systemImage: "clock.arrow.circlepath")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
        }
        .padding(.horizontal, Theme.Space.md)
        .padding(.top, 6)
        .padding(.bottom, Theme.Space.sm)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.bar)
    }

    private var statusColor: Color {
        switch state.engineState {
        case .idle: return Theme.Status.idle
        case .preparing, .running: return Theme.Status.running
        case .finished(let code): return code == 0 ? Theme.Status.success : Theme.Status.warning
        case .failed: return Theme.Status.error
        }
    }
}
