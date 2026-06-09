import SwiftUI
import AppKit

struct SettingsView: View {
    @EnvironmentObject var state: AppState
    @State private var savedFlash = false

    var body: some View {
        Form {
            Section("Engine") {
                HStack {
                    TextField("Engine folder", text: .constant(state.engineRootPath))
                        .disabled(true)
                        .foregroundStyle(.secondary)
                    Button("Choose…") { chooseEngineFolder() }
                }
                HStack(spacing: 6) {
                    Image(systemName: state.engineExists ? "checkmark.circle.fill" : "xmark.circle.fill")
                        .foregroundStyle(state.engineExists ? Theme.Status.success : Theme.Status.error)
                    Text(state.engineExists ? "Engine detected" : "No engine at this path")
                        .font(.callout).foregroundStyle(.secondary)
                }
            }

            Section("Email — sending applications (SMTP)") {
                field("SMTP host", "SMTP_HOST")
                field("SMTP port", "SMTP_PORT")
                field("SMTP user", "SMTP_USER")
                secure("SMTP password (Gmail: App Password)", "SMTP_PASSWORD")
                field("From name", "SMTP_FROM_NAME")
                field("Alert email", "ALERT_EMAIL")
            }

            Section("Inbox — response detection (IMAP)") {
                field("IMAP host", "IMAP_HOST")
                field("IMAP port", "IMAP_PORT")
                field("IMAP user", "IMAP_USER")
                secure("IMAP password", "IMAP_PASSWORD")
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
                Text("Saved to the engine's .env. Passwords are stored locally only.")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .navigationTitle("Settings")
    }

    private func field(_ title: String, _ key: String) -> some View {
        TextField(title, text: state.binding(for: key))
            .textFieldStyle(.roundedBorder)
    }

    private func secure(_ title: String, _ key: String) -> some View {
        SecureField(title, text: state.binding(for: key))
            .textFieldStyle(.roundedBorder)
    }

    private func flashSaved() {
        withAnimation { savedFlash = true }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.8) {
            withAnimation { savedFlash = false }
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
