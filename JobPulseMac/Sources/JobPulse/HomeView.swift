import SwiftUI

struct HomeView: View {
    @EnvironmentObject var state: AppState

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Space.lg) {
                header
                if !state.engineExists { engineMissingBanner }
                readiness
                runControls
                liveActivity
            }
            .padding(Theme.Space.xl)
        }
        .navigationTitle("Home")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button { state.refreshData() } label: { Image(systemName: "arrow.clockwise") }
                    .help("Refresh data")
            }
        }
    }

    // MARK: header
    private var header: some View {
        HStack(alignment: .center) {
            VStack(alignment: .leading, spacing: 4) {
                Text("JobPulse").font(.largeTitle.bold())
                Text("Automated job discovery & applications")
                    .foregroundStyle(.secondary)
            }
            Spacer()
            StatCard(value: "\(state.totalApplied)", label: "Applied (total)")
            StatCard(value: "\(state.needsReview.count)", label: "Needs review",
                     tint: state.needsReview.isEmpty ? .secondary : Theme.Status.warning)
        }
    }

    private var engineMissingBanner: some View {
        Card {
            HStack(spacing: Theme.Space.sm) {
                Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(Theme.Status.warning)
                VStack(alignment: .leading) {
                    Text("Engine not found").font(.headline)
                    Text("Set the JobPulse engine folder in Settings.").foregroundStyle(.secondary).font(.callout)
                }
            }
        }
    }

    // MARK: readiness
    private var readiness: some View {
        Card {
            HStack(spacing: Theme.Space.lg) {
                ReadinessItem(index: 1, label: "CV", ok: state.cvReady)
                ReadinessItem(index: 2, label: "Email", ok: state.emailReady)
                ReadinessItem(index: 3, label: "Roles (\(state.roleCount))", ok: state.roleCount > 0)
                Spacer()
                Text("Configure in Settings →").font(.callout).foregroundStyle(.tertiary)
            }
        }
    }

    // MARK: run controls
    private var runControls: some View {
        Card {
            VStack(alignment: .leading, spacing: Theme.Space.md) {
                Toggle(isOn: $state.dryRun) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Dry run").font(.callout.weight(.semibold))
                        Text("Discover jobs only — don't submit anything").font(.caption).foregroundStyle(.secondary)
                    }
                }
                .toggleStyle(.switch)
                .disabled(state.isBusy)

                HStack(spacing: Theme.Space.md) {
                    Button(action: { state.run() }) {
                        Label(state.dryRun ? "Run (Dry)" : "Run", systemImage: "play.fill")
                            .frame(maxWidth: .infinity)
                    }
                    .controlSize(.large)
                    .buttonStyle(.borderedProminent)
                    .disabled(state.isBusy || !state.engineExists)

                    Button(action: { state.stop() }) {
                        Label("Stop", systemImage: "stop.fill").frame(maxWidth: .infinity)
                    }
                    .controlSize(.large)
                    .buttonStyle(.bordered)
                    .disabled(!state.isBusy)
                }
            }
        }
    }

    // MARK: live activity
    private var liveActivity: some View {
        VStack(alignment: .leading, spacing: Theme.Space.sm) {
            SectionTitle(text: "Activity", systemImage: "waveform")
            Card(padding: Theme.Space.sm) {
                if state.activity.isEmpty {
                    HStack {
                        Spacer()
                        Text("No activity yet. Press Run to start.")
                            .foregroundStyle(.tertiary).font(.callout)
                            .padding(.vertical, Theme.Space.xl)
                        Spacer()
                    }
                } else {
                    ActivityList(lines: state.activity)
                        .frame(height: 320)
                }
            }
        }
    }
}

// MARK: - components

struct StatCard: View {
    let value: String
    let label: String
    var tint: Color = .primary
    var body: some View {
        VStack(alignment: .trailing, spacing: 2) {
            Text(value).font(.title.bold().monospacedDigit()).foregroundStyle(tint)
            Text(label.uppercased()).font(.caption2.weight(.semibold)).foregroundStyle(.secondary)
        }
        .padding(.horizontal, Theme.Space.md)
        .padding(.vertical, Theme.Space.sm)
        .background(.background.secondary, in: RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous))
    }
}

struct ReadinessItem: View {
    let index: Int
    let label: String
    let ok: Bool
    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: ok ? "checkmark.circle.fill" : "\(index).circle")
                .foregroundStyle(ok ? Theme.Status.success : Color.secondary)
            Text(label).fontWeight(ok ? .semibold : .regular)
                .foregroundStyle(ok ? .primary : .secondary)
        }
    }
}

struct ActivityList: View {
    let lines: [ActivityLine]
    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 1) {
                    ForEach(lines) { line in
                        Text(line.text)
                            .font(.system(.callout, design: .monospaced))
                            .foregroundStyle(color(for: line.kind))
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.horizontal, 8).padding(.vertical, 3)
                            .background(bg(for: line.kind), in: RoundedRectangle(cornerRadius: 5))
                            .textSelection(.enabled)
                            .id(line.id)
                    }
                }
                .padding(4)
            }
            .onChange(of: lines.count) { _, _ in
                if let last = lines.last { withAnimation { proxy.scrollTo(last.id, anchor: .bottom) } }
            }
        }
    }

    private func color(for kind: ActivityLine.Kind) -> Color {
        switch kind {
        case .applied, .success: return Theme.Status.success
        case .skipped: return .orange
        case .warning: return Theme.Status.warning
        case .error: return Theme.Status.error
        case .discovery: return Theme.Status.info
        case .muted: return .secondary
        case .info: return .primary
        }
    }

    private func bg(for kind: ActivityLine.Kind) -> Color {
        switch kind {
        case .applied, .success: return Theme.Status.success.opacity(0.10)
        case .skipped, .warning: return Theme.Status.warning.opacity(0.08)
        case .error: return Theme.Status.error.opacity(0.10)
        default: return .clear
        }
    }
}
