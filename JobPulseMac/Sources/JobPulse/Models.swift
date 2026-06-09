import Foundation

/// One line of engine output, classified for colored display.
struct ActivityLine: Identifiable, Hashable {
    enum Kind {
        case info, success, applied, skipped, warning, error, discovery, muted
    }
    let id = UUID()
    let kind: Kind
    let text: String
    let time = Date()
}

struct AppliedJob: Identifiable, Hashable {
    let id = UUID()
    let title: String
    let site: String
}

struct SkippedJob: Identifiable, Hashable {
    let id = UUID()
    let title: String
    let reason: String
}

/// A job the engine skipped because a form needed answers it won't fabricate.
struct NeedsReviewItem: Identifiable, Hashable {
    let id = UUID()
    let title: String
    let url: String
    let site: String
    let reasons: [String]
    let at: String
}

struct RunRecord: Identifiable, Hashable {
    let id = UUID()
    let at: String
    let applied: Int
    let skipped: Int
}

/// Engine run lifecycle.
enum EngineState: Equatable {
    case idle
    case preparing       // installing deps / checking chromium
    case running
    case finished(exitCode: Int32)
    case failed(String)

    var label: String {
        switch self {
        case .idle: return "Idle"
        case .preparing: return "Preparing…"
        case .running: return "Running"
        case .finished(let code): return code == 0 ? "Done" : "Finished (exit \(code))"
        case .failed: return "Error"
        }
    }

    var isBusy: Bool {
        switch self {
        case .preparing, .running: return true
        default: return false
        }
    }
}
