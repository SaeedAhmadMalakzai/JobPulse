import Foundation

/// Drives the Python engine (`python -m src.main`) as a child process, streaming
/// its stdout/stderr line-by-line and classifying each line for the UI.
final class EngineRunner {
    private var process: Process?
    private var stdoutPipe: Pipe?
    private var stderrPipe: Pipe?

    var onLine: ((ActivityLine) -> Void)?
    var onStats: ((_ applied: Int, _ skipped: Int) -> Void)?
    var onState: ((EngineState) -> Void)?

    var isRunning: Bool { process?.isRunning ?? false }

    func run(dryRun: Bool) {
        guard !isRunning else { return }
        let config = EngineConfig.shared
        guard config.engineExists else {
            onState?(.failed("Engine not found at \(config.engineRoot.path). Set the engine folder in Settings."))
            return
        }

        let proc = Process()
        proc.currentDirectoryURL = config.engineRoot
        proc.executableURL = URL(fileURLWithPath: config.pythonPath)
        proc.arguments = ["-m", "src.main"]

        var env = ProcessInfo.processInfo.environment
        env["PYTHONPATH"] = config.engineRoot.path
        env["PYTHONUNBUFFERED"] = "1"           // stream output as it happens
        env["DRY_RUN"] = dryRun ? "1" : "0"
        proc.environment = env

        let outPipe = Pipe(), errPipe = Pipe()
        proc.standardOutput = outPipe
        proc.standardError = errPipe
        stdoutPipe = outPipe
        stderrPipe = errPipe

        attachReader(outPipe)
        attachReader(errPipe)

        proc.terminationHandler = { [weak self] p in
            DispatchQueue.main.async {
                self?.cleanup()
                self?.onState?(.finished(exitCode: p.terminationStatus))
            }
        }

        do {
            try proc.run()
            process = proc
            onState?(.running)
        } catch {
            onState?(.failed(error.localizedDescription))
        }
    }

    func stop() {
        guard let proc = process, proc.isRunning else { return }
        proc.terminate()  // SIGTERM; engine handles graceful shutdown
        // Force-kill after a grace period if still alive.
        DispatchQueue.main.asyncAfter(deadline: .now() + 4) { [weak self] in
            if let p = self?.process, p.isRunning { p.interrupt() }
        }
    }

    // MARK: - streaming

    private func attachReader(_ pipe: Pipe) {
        var buffer = Data()
        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let chunk = handle.availableData
            if chunk.isEmpty { return }
            buffer.append(chunk)
            while let nl = buffer.firstIndex(of: 0x0A) {
                let lineData = buffer.subdata(in: buffer.startIndex..<nl)
                buffer.removeSubrange(buffer.startIndex...nl)
                if let text = String(data: lineData, encoding: .utf8) {
                    self?.handleLine(text)
                }
            }
        }
    }

    private func handleLine(_ raw: String) {
        let text = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        let (kind, applied, skipped) = Self.classify(text)
        DispatchQueue.main.async {
            self.onLine?(ActivityLine(kind: kind, text: Self.cleaned(text)))
            if let applied, let skipped { self.onStats?(applied, skipped) }
        }
    }

    /// Strip the leading "2026-… [INFO] " logging prefix for display.
    static func cleaned(_ text: String) -> String {
        if let range = text.range(of: #"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d \[[A-Z]+\]\s*"#, options: .regularExpression) {
            return String(text[range.upperBound...])
        }
        return text
    }

    /// Classify a log line and, for the final summary, extract (applied, skipped).
    static func classify(_ text: String) -> (ActivityLine.Kind, Int?, Int?) {
        let lower = text.lowercased()
        if lower.contains("done.") || lower.contains("run finished") {
            let applied = intValue(after: "applied=", in: text)
            let skipped = intValue(after: "skipped=", in: text)
            return (.success, applied, skipped)
        }
        if lower.contains("] applied") || lower.contains("applied via") { return (.applied, nil, nil) }
        if lower.contains("skip (") || lower.contains("skipped") { return (.skipped, nil, nil) }
        if lower.contains("error") || lower.contains("failed") || lower.contains("traceback") { return (.error, nil, nil) }
        if lower.contains("warning") || lower.contains("rejected") { return (.warning, nil, nil) }
        if lower.contains("discover") { return (.discovery, nil, nil) }
        return (.info, nil, nil)
    }

    private static func intValue(after token: String, in text: String) -> Int? {
        guard let r = text.range(of: token) else { return nil }
        let tail = text[r.upperBound...]
        let digits = tail.prefix { $0.isNumber }
        return Int(digits)
    }

    private func cleanup() {
        stdoutPipe?.fileHandleForReading.readabilityHandler = nil
        stderrPipe?.fileHandleForReading.readabilityHandler = nil
        stdoutPipe = nil
        stderrPipe = nil
        process = nil
    }
}
