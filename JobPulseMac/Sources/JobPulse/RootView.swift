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
                Section {
                    ForEach(SidebarItem.allCases) { item in
                        Label {
                            HStack {
                                Text(item.rawValue)
                                Spacer()
                                if item == .needsReview, !state.needsReview.isEmpty {
                                    Text("\(state.needsReview.count)")
                                        .font(.caption2.weight(.bold))
                                        .padding(.horizontal, 6).padding(.vertical, 2)
                                        .background(Theme.Status.warning.opacity(0.2), in: Capsule())
                                }
                            }
                        } icon: {
                            Image(systemName: item.icon)
                        }
                        .tag(item)
                    }
                } header: {
                    Text("JobPulse").font(.title3.bold()).foregroundStyle(.primary)
                }
            }
            .listStyle(.sidebar)
            .navigationSplitViewColumnWidth(min: 200, ideal: 220, max: 280)
            .safeAreaInset(edge: .bottom) {
                sidebarStatus
            }
        } detail: {
            detail
        }
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
        HStack {
            StatusPill(
                text: state.engineState.label,
                color: statusColor,
                pulsing: state.engineState.isBusy
            )
            Spacer()
        }
        .padding(.horizontal, Theme.Space.md)
        .padding(.vertical, Theme.Space.sm)
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
