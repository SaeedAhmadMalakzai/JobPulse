// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "JobPulse",
    platforms: [.macOS(.v14)],
    targets: [
        .executableTarget(
            name: "JobPulse",
            path: "Sources/JobPulse",
            // Swift 5 language mode keeps SwiftUI/ObservableObject ergonomics simple
            // (no strict-concurrency churn) while still building on the Swift 6 toolchain.
            swiftSettings: [.swiftLanguageMode(.v5)],
            linkerSettings: [.linkedLibrary("sqlite3")]
        )
    ]
)
