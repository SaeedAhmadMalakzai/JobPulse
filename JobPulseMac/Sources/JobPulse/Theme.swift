import SwiftUI

/// Design tokens for a deliberately native, modern macOS look:
/// system materials, semantic colors, a single confident accent, and a
/// consistent spacing/radius rhythm.
enum Theme {
    /// Brand accent (indigo) — matches the hero mark and the console; applied app-wide
    /// via `.tint(Theme.brand)` so primary controls share one confident accent.
    static let brand = Color(red: 0.36, green: 0.33, blue: 0.86)
    static let accent = brand

    enum Status {
        static let idle = Color.secondary
        static let running = Color.green
        static let success = Color.green
        static let warning = Color.orange
        static let error = Color.red
        static let skipped = Color.yellow
        static let info = Color.blue
    }

    enum Space {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 14
        static let lg: CGFloat = 20
        static let xl: CGFloat = 32
    }

    enum Radius {
        static let card: CGFloat = 12
        static let pill: CGFloat = 999
    }
}

/// A frosted surface card used across the app.
struct Card<Content: View>: View {
    var padding: CGFloat = Theme.Space.md
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(.background.secondary, in: RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous)
                    .strokeBorder(.separator.opacity(0.6), lineWidth: 1)
            )
    }
}

/// Small status pill (e.g. Idle / Running / Done).
struct StatusPill: View {
    let text: String
    let color: Color
    var pulsing: Bool = false
    @State private var on = false

    var body: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(color)
                .frame(width: 8, height: 8)
                .opacity(pulsing ? (on ? 1 : 0.35) : 1)
                .animation(pulsing ? .easeInOut(duration: 0.7).repeatForever(autoreverses: true) : .default, value: on)
            Text(text)
                .font(.callout.weight(.semibold))
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .background(color.opacity(0.12), in: Capsule())
        .onAppear { if pulsing { on = true } }
    }
}

struct SectionTitle: View {
    let text: String
    var systemImage: String? = nil
    var body: some View {
        HStack(spacing: 6) {
            if let systemImage { Image(systemName: systemImage).foregroundStyle(.secondary) }
            Text(text).font(.headline)
        }
    }
}
