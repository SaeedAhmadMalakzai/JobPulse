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

    // MARK: live console
    private var liveActivity: some View {
        VStack(alignment: .leading, spacing: Theme.Space.sm) {
            HStack(spacing: 6) {
                SectionTitle(text: "Console", systemImage: "terminal")
                Spacer()
                if !state.activity.isEmpty {
                    Text("\(state.activity.count) lines")
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.tertiary)
                }
            }
            ConsoleView(lines: state.activity, running: state.isBusy,
                        onClear: { state.clearActivity() })
                .frame(minHeight: 360, maxHeight: 460)
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

