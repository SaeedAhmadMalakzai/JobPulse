import Foundation
import SQLite3

/// Minimal read-only reader for the engine's SQLite DB (`data/jobpulse.db`).
/// Surfaces the needs-review queue and recent application history natively.
enum Database {
    private static let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)

    static func needsReview() -> [NeedsReviewItem] {
        query(
            "SELECT title, url, site, reasons, at FROM needs_review ORDER BY at DESC LIMIT 300"
        ) { stmt in
            let title = column(stmt, 0)
            let url = column(stmt, 1)
            let site = column(stmt, 2)
            let reasonsJSON = column(stmt, 3)
            let at = column(stmt, 4)
            let reasons = (try? JSONDecoder().decode([String].self, from: Data(reasonsJSON.utf8))) ?? []
            return NeedsReviewItem(title: title, url: url, site: site, reasons: reasons, at: at)
        }
    }

    static func recentApplications(limit: Int = 200) -> [AppliedJob] {
        query(
            "SELECT id, site FROM applications ORDER BY applied_at DESC LIMIT \(limit)"
        ) { stmt in
            AppliedJob(title: column(stmt, 0), site: column(stmt, 1))
        }
    }

    static func appliedCount() -> Int {
        var n = 0
        _ = query("SELECT COUNT(*) FROM applications") { stmt -> Int in
            n = Int(sqlite3_column_int(stmt, 0)); return n
        }
        return n
    }

    // MARK: - core

    private static func query<T>(_ sql: String, _ row: (OpaquePointer) -> T) -> [T] {
        let path = EngineConfig.shared.dbURL.path
        guard FileManager.default.fileExists(atPath: path) else { return [] }
        var db: OpaquePointer?
        guard sqlite3_open_v2(path, &db, SQLITE_OPEN_READONLY, nil) == SQLITE_OK else {
            sqlite3_close(db); return []
        }
        defer { sqlite3_close(db) }
        var stmt: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK else {
            sqlite3_finalize(stmt); return []
        }
        defer { sqlite3_finalize(stmt) }
        var out: [T] = []
        while sqlite3_step(stmt) == SQLITE_ROW {
            if let stmt { out.append(row(stmt)) }
        }
        return out
    }

    private static func column(_ stmt: OpaquePointer, _ index: Int32) -> String {
        guard let c = sqlite3_column_text(stmt, index) else { return "" }
        return String(cString: c)
    }
}
