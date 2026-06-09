import Foundation
import Network

/// Lightweight TCP reachability check for a host:port. Confirms the mail server is
/// reachable from this machine (catches wrong host/port or a blocked firewall).
/// It does NOT verify credentials — that happens when the engine actually sends.
enum Reachability {
    enum Result { case unknown, checking, reachable, unreachable }

    /// Thread-safe one-shot latch so the continuation resumes exactly once.
    private final class Latch: @unchecked Sendable {
        private let lock = NSLock()
        private var done = false
        func claim() -> Bool {
            lock.lock(); defer { lock.unlock() }
            if done { return false }
            done = true
            return true
        }
    }

    static func check(host: String, port: Int, timeout: TimeInterval = 6) async -> Bool {
        let trimmed = host.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty, port > 0, port <= 65_535,
              let nwPort = NWEndpoint.Port(rawValue: UInt16(port)) else { return false }

        let conn = NWConnection(host: NWEndpoint.Host(trimmed), port: nwPort, using: .tcp)
        return await withCheckedContinuation { (cont: CheckedContinuation<Bool, Never>) in
            let latch = Latch()
            let finish: @Sendable (Bool) -> Void = { ok in
                guard latch.claim() else { return }
                conn.cancel()
                cont.resume(returning: ok)
            }
            conn.stateUpdateHandler = { state in
                switch state {
                case .ready: finish(true)
                case .failed, .cancelled: finish(false)
                default: break
                }
            }
            conn.start(queue: .global(qos: .userInitiated))
            DispatchQueue.global().asyncAfter(deadline: .now() + timeout) { finish(false) }
        }
    }
}
