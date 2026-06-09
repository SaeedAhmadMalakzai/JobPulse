import SwiftUI
import AppKit

struct SettingsView: View {
    @EnvironmentObject var state: AppState
    @State private var savedFlash = false
    @State private var smtpResult: Reachability.Result = .unknown
    @State private var imapResult: Reachability.Result = .unknown

    var body: some View {
        Form {
            Section("Engine") {
                HStack {
                    TextField("Engine folder", text: .constant(state.engineRootPath))
                        .disabled(true)
                        .foregroundStyle(.secondary)
                    Button("Choose…") { chooseEngineFolder() }
                }
                hint(ok: state.engineExists,
                     state.engineExists ? "Engine detected" : "No engine at this path")
            }

            Section("Email — sending applications (SMTP)") {
                field("SMTP host", "SMTP_HOST")
                field("SMTP port", "SMTP_PORT")
                field("SMTP user", "SMTP_USER")
                secure("SMTP password (Gmail: App Password)", "SMTP_PASSWORD")
                field("From name", "SMTP_FROM_NAME")
                field("Alert email", "ALERT_EMAIL")
                hint(ok: emailReady,
                     emailReady ? "SMTP user + password set" : "Set both SMTP user and password to send")
                testRow(result: smtpResult) {
                    runTest(host: "SMTP_HOST", port: "SMTP_PORT", default: 587) { smtpResult = $0 }
                }
            }

            Section("Inbox — response detection (IMAP)") {
                field("IMAP host", "IMAP_HOST")
                field("IMAP port", "IMAP_PORT")
                field("IMAP user", "IMAP_USER")
                secure("IMAP password", "IMAP_PASSWORD")
                testRow(result: imapResult) {
                    runTest(host: "IMAP_HOST", port: "IMAP_PORT", default: 993) { imapResult = $0 }
                }
            }

            Section("Your details (used on forms)") {
                field("Full name", "FULL_NAME")
                field("Submission email", "SUBMISSION_EMAIL")
                field("Phone country code", "PHONE_COUNTRY_CODE")
                field("Phone number", "PHONE_NUMBER")
                field("LinkedIn profile URL", "LINKEDIN_PROFILE_URL")
            }

            Section("Attachments") {
                HStack {
                    field("CV path", "CV_PATH")
                    Button("Choose…") { chooseFile(into: "CV_PATH") }
                }
                hint(ok: cvExists,
                     cvExists ? "CV file found" : "CV file not found at this path")
                HStack {
                    field("Cover letter path", "COVER_LETTER_PATH")
                    Button("Choose…") { chooseFile(into: "COVER_LETTER_PATH") }
                }
            }

            Section("Targeting") {
                field("Keywords (comma-separated)", "JOB_KEYWORDS")
                field("Exclude keywords", "JOB_EXCLUDE_KEYWORDS")
                field("Max job age (days)", "MAX_JOB_AGE_DAYS")
                field("Max applications per run (0 = no limit)", "MAX_APPLICATIONS_PER_RUN")
                hint(ok: state.roleCount > 0,
                     state.roleCount > 0 ? "\(state.roleCount) keyword(s) — discovery will filter to these"
                                         : "No keywords — every discovered job will match")
            }

            Section {
                HStack {
                    Button {
                        state.saveSettings()
                        flashSaved()
                    } label: {
                        Label("Save to .env", systemImage: "tray.and.arrow.down.fill")
                    }
                    .buttonStyle(.borderedProminent)
                    if savedFlash {
                        Label("Saved", systemImage: "checkmark.circle.fill")
                            .foregroundStyle(Theme.Status.success).transition(.opacity)
                    }
                    Spacer()
                    Button("Reload") { state.reloadConfig() }
                }
            } footer: {
                Text("Saved to the engine's .env. Passwords are stored locally only and never leave your Mac.")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .navigationTitle("Settings")
    }

    // MARK: rows / hints

    private func field(_ title: String, _ key: String) -> some View {
        TextField(title, text: state.binding(for: key))
            .textFieldStyle(.roundedBorder)
    }

    private func secure(_ title: String, _ key: String) -> some View {
        SecureField(title, text: state.binding(for: key))
            .textFieldStyle(.roundedBorder)
    }

    private func hint(ok: Bool, _ text: String) -> some View {
        HStack(spacing: 6) {
            Image(systemName: ok ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                .foregroundStyle(ok ? Theme.Status.success : Theme.Status.warning)
            Text(text).font(.caption).foregroundStyle(.secondary)
        }
    }

    @ViewBuilder
    private func testRow(result: Reachability.Result, action: @escaping () -> Void) -> some View {
        HStack(spacing: 10) {
            Button(action: action) {
                Label("Test reachability", systemImage: "bolt.horizontal.circle")
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
            .disabled(result == .checking)

            switch result {
            case .unknown:
                EmptyView()
            case .checking:
                HStack(spacing: 6) {
                    ProgressView().controlSize(.small)
                    Text("Checking…").font(.caption).foregroundStyle(.secondary)
                }
            case .reachable:
                hint(ok: true, "Server reachable (credentials are verified on first send)")
            case .unreachable:
                hint(ok: false, "Unreachable — check host/port or your network")
            }
            Spacer()
        }
    }

    // MARK: derived state

    private var emailReady: Bool {
        !(state.env["SMTP_USER"] ?? "").isEmpty && !(state.env["SMTP_PASSWORD"] ?? "").isEmpty
    }

    private var cvExists: Bool {
        let p = (state.env["CV_PATH"] ?? "").trimmingCharacters(in: .whitespaces)
        guard !p.isEmpty else { return false }
        return FileManager.default.fileExists(atPath: (p as NSString).expandingTildeInPath)
    }

    // MARK: actions

    private func flashSaved() {
        withAnimation { savedFlash = true }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.8) {
            withAnimation { savedFlash = false }
        }
    }

    private func runTest(host hostKey: String, port portKey: String, default def: Int,
                         set: @escaping (Reachability.Result) -> Void) {
        let host = state.env[hostKey] ?? ""
        let port = Int(state.env[portKey] ?? "") ?? def
        set(.checking)
        Task {
            let ok = await Reachability.check(host: host, port: port)
            await MainActor.run { set(ok ? .reachable : .unreachable) }
        }
    }

    private func chooseEngineFolder() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.allowsMultipleSelection = false
        if panel.runModal() == .OK, let url = panel.url {
            state.setEngineRoot(url.path)
        }
    }

    private func chooseFile(into key: String) {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        if panel.runModal() == .OK, let url = panel.url {
            state.env[key] = url.path
        }
    }
}
