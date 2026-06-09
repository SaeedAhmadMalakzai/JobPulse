import Foundation
import SwiftUI
import Combine

@MainActor
final class AppState: ObservableObject {
    private let runner = EngineRunner()
    private let config = EngineConfig.shared

    // Run state
    @Published var engineState: EngineState = .idle
    @Published var dryRun: Bool = false
    @Published var activity: [ActivityLine] = []
    @Published var applied: [AppliedJob] = []
    @Published var skipped: [SkippedJob] = []

    // Data surfaces
    @Published var needsReview: [NeedsReviewItem] = []
    @Published var history: [RunRecord] = []
    @Published var totalApplied: Int = 0

    // Config (engine .env), edited in Settings
    @Published var env: [String: String] = [:]
    @Published var engineRootPath: String = ""

    init() {
        reloadConfig()
        wireRunner()
        refreshData()
    }

    var isBusy: Bool { engineState.isBusy }
    var engineExists: Bool { config.engineExists }

    // Readiness indicators for Home
    var cvReady: Bool { !(env["CV_PATH"] ?? "").isEmpty }
    var emailReady: Bool { !(env["SMTP_USER"] ?? "").isEmpty && !(env["SMTP_PASSWORD"] ?? "").isEmpty }
    var roleCount: Int {
        (env["JOB_KEYWORDS"] ?? "").split(separator: ",").filter { !$0.trimmingCharacters(in: .whitespaces).isEmpty }.count
    }

    // MARK: - engine control

    func run() {
        guard !isBusy else { return }
        activity.removeAll()
        applied.removeAll()
        skipped.removeAll()
        append(.init(kind: .info, text: dryRun ? "Starting dry run (discover only)…" : "Starting JobPulse…"))
        runner.run(dryRun: dryRun)
    }

    func stop() {
        append(.init(kind: .warning, text: "Stopping…"))
        runner.stop()
    }

    func clearActivity() {
        activity.removeAll()
    }

    private func wireRunner() {
        runner.onState = { [weak self] state in
            guard let self else { return }
            self.engineState = state
            if case .finished = state { self.refreshData() }
        }
        runner.onLine = { [weak self] line in
            guard let self else { return }
            self.append(line)
            self.parseResult(from: line)
        }
        runner.onStats = { [weak self] applied, skipped in
            self?.append(.init(kind: .success, text: "Run complete — \(applied) applied, \(skipped) skipped."))
        }
    }

    private func append(_ line: ActivityLine) {
        activity.append(line)
        if activity.count > 1000 { activity.removeFirst(activity.count - 1000) }
    }

    /// Pull a job title/reason out of an engine result line.
    private func parseResult(from line: ActivityLine) {
        let site = Self.bracketSite(line.text)
        switch line.kind {
        case .applied:
            if let title = Self.text(after: "Applied:", in: line.text) ?? Self.text(after: "Applied via", in: line.text) {
                applied.append(AppliedJob(title: Self.trimEllipsis(title), site: site))
            }
        case .skipped:
            if let (reason, title) = Self.skipParts(line.text) {
                skipped.append(SkippedJob(title: Self.trimEllipsis(title), reason: reason))
            }
        default:
            break
        }
    }

    // MARK: - data

    func refreshData() {
        needsReview = Database.needsReview()
        totalApplied = Database.appliedCount()
        history = loadHistory()
    }

    private func loadHistory() -> [RunRecord] {
        guard let data = try? Data(contentsOf: config.runHistoryURL),
              let arr = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]] else { return [] }
        return arr.compactMap { d in
            let at = (d["at"] as? String) ?? ""
            let a = (d["applied"] as? Int) ?? 0
            let s = (d["skipped"] as? Int) ?? 0
            return RunRecord(at: at, applied: a, skipped: s)
        }
    }

    // MARK: - config

    func reloadConfig() {
        env = config.loadEnv()
        engineRootPath = config.engineRoot.path
    }

    func binding(for key: String) -> Binding<String> {
        Binding(
            get: { self.env[key] ?? "" },
            set: { self.env[key] = $0 }
        )
    }

    func saveSettings() {
        config.saveEnv(env)
    }

    func setEngineRoot(_ path: String) {
        config.engineRoot = URL(fileURLWithPath: path, isDirectory: true)
        reloadConfig()
        refreshData()
    }

    // MARK: - line parsing helpers

    private static func bracketSite(_ text: String) -> String {
        guard let open = text.firstIndex(of: "["), let close = text.firstIndex(of: "]"), open < close else { return "" }
        return String(text[text.index(after: open)..<close])
    }

    private static func text(after token: String, in text: String) -> String? {
        guard let r = text.range(of: token) else { return nil }
        let t = text[r.upperBound...].trimmingCharacters(in: .whitespaces)
        return t.isEmpty ? nil : t
    }

    private static func skipParts(_ text: String) -> (reason: String, title: String)? {
        // "[site] Skip (reason): title"
        guard let open = text.range(of: "("),
              let close = text.range(of: "):") else { return nil }
        let reason = String(text[open.upperBound..<close.lowerBound])
        let title = String(text[close.upperBound...]).trimmingCharacters(in: .whitespaces)
        return (reason, title.isEmpty ? "(job)" : title)
    }

    private static func trimEllipsis(_ s: String) -> String {
        s.replacingOccurrences(of: "...", with: "").trimmingCharacters(in: .whitespaces)
    }
}
