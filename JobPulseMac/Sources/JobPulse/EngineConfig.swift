import Foundation

/// Resolves where the Python engine lives and reads/writes its `.env`.
///
/// Default engine root = the parent of this Swift package (the JobPulse repo),
/// so running from the repo "just works". The root is user-overridable and
/// persisted in UserDefaults for a packaged .app.
final class EngineConfig {
    static let shared = EngineConfig()

    private let defaults = UserDefaults.standard
    private let rootKey = "engineRootPath"

    /// The Python project root (contains `src/`, `.env`, `.venv`).
    var engineRoot: URL {
        get {
            if let saved = defaults.string(forKey: rootKey), !saved.isEmpty {
                return URL(fileURLWithPath: saved, isDirectory: true)
            }
            return Self.defaultEngineRoot
        }
        set { defaults.set(newValue.path, forKey: rootKey) }
    }

    /// Best guess at the repo root: two levels up from this source file at dev time,
    /// else ~/automated-cv-submissions.
    static var defaultEngineRoot: URL {
        // .../JobPulseMac/Sources/JobPulse/EngineConfig.swift -> repo root is 3 up.
        let here = URL(fileURLWithPath: #filePath)
        let candidate = here.deletingLastPathComponent()  // JobPulse
            .deletingLastPathComponent()                   // Sources
            .deletingLastPathComponent()                   // JobPulseMac
            .deletingLastPathComponent()                   // repo root
        if FileManager.default.fileExists(atPath: candidate.appendingPathComponent("src").path) {
            return candidate
        }
        return FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("automated-cv-submissions")
    }

    var envURL: URL { engineRoot.appendingPathComponent(".env") }
    var dbURL: URL { engineRoot.appendingPathComponent("data/jobpulse.db") }
    var runHistoryURL: URL { engineRoot.appendingPathComponent("data/run_history.json") }

    /// Path to the Python interpreter (prefers the project venv).
    var pythonPath: String {
        let venv = engineRoot.appendingPathComponent(".venv/bin/python")
        if FileManager.default.fileExists(atPath: venv.path) { return venv.path }
        return "/usr/bin/python3"
    }

    var engineExists: Bool {
        FileManager.default.fileExists(atPath: engineRoot.appendingPathComponent("src/main.py").path)
    }

    // MARK: - .env read/write

    func loadEnv() -> [String: String] {
        guard let text = try? String(contentsOf: envURL, encoding: .utf8) else { return [:] }
        var result: [String: String] = [:]
        for raw in text.split(separator: "\n", omittingEmptySubsequences: false) {
            let line = raw.trimmingCharacters(in: .whitespaces)
            if line.isEmpty || line.hasPrefix("#") { continue }
            guard let eq = line.firstIndex(of: "=") else { continue }
            let key = String(line[..<eq]).trimmingCharacters(in: .whitespaces)
            var value = String(line[line.index(after: eq)...]).trimmingCharacters(in: .whitespaces)
            if value.count >= 2, value.hasPrefix("\""), value.hasSuffix("\"") {
                value = String(value.dropFirst().dropLast())
            }
            if !key.isEmpty { result[key] = value }
        }
        return result
    }

    /// Merge `updates` into `.env`, preserving comments and unrelated keys.
    func saveEnv(_ updates: [String: String]) {
        var lines: [String] = []
        if let text = try? String(contentsOf: envURL, encoding: .utf8) {
            lines = text.components(separatedBy: "\n")
        }
        var remaining = updates
        for (i, raw) in lines.enumerated() {
            let line = raw.trimmingCharacters(in: .whitespaces)
            if line.isEmpty || line.hasPrefix("#") { continue }
            guard let eq = line.firstIndex(of: "=") else { continue }
            let key = String(line[..<eq]).trimmingCharacters(in: .whitespaces)
            if let newValue = remaining[key] {
                lines[i] = "\(key)=\(newValue)"
                remaining.removeValue(forKey: key)
            }
        }
        for (key, value) in remaining {
            lines.append("\(key)=\(value)")
        }
        let output = lines.joined(separator: "\n")
        try? output.write(to: envURL, atomically: true, encoding: .utf8)
    }
}
