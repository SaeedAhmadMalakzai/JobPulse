import SwiftUI

/// Centered empty/placeholder state with a tinted icon chip.
struct EmptyState: View {
    let icon: String
    let title: String
    var message: String = ""
    var tint: Color = .secondary

    var body: some View {
        VStack(spacing: Theme.Space.md) {
            Image(systemName: icon)
                .font(.system(size: 26, weight: .medium))
                .foregroundStyle(tint)
                .frame(width: 64, height: 64)
                .background(tint.opacity(0.12), in: Circle())
            VStack(spacing: 4) {
                Text(title).font(.headline)
                if !message.isEmpty {
                    Text(message)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(Theme.Space.xl)
    }
}

/// Gradient hero banner for the Home header (the ⚡ JobPulse mark + title).
struct HeroBanner: View {
    let title: String
    let subtitle: String

    private static let mark = LinearGradient(
        colors: [Color(red: 0.31, green: 0.27, blue: 0.90), Color(red: 0.49, green: 0.23, blue: 0.93)],
        startPoint: .topLeading, endPoint: .bottomTrailing
    )

    var body: some View {
        HStack(alignment: .center, spacing: Theme.Space.md) {
            ZStack {
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Self.mark)
                    .frame(width: 54, height: 54)
                    .shadow(color: Color(red: 0.4, green: 0.25, blue: 0.9).opacity(0.4), radius: 8, y: 3)
                Image(systemName: "bolt.fill")
                    .font(.system(size: 24, weight: .bold))
                    .foregroundStyle(.white)
            }
            VStack(alignment: .leading, spacing: 3) {
                Text(title).font(.system(size: 26, weight: .bold))
                Text(subtitle).foregroundStyle(.secondary)
            }
            Spacer(minLength: 0)
        }
        .padding(Theme.Space.lg)
        .background(
            LinearGradient(
                colors: [Color.accentColor.opacity(0.10), Color.accentColor.opacity(0.02)],
                startPoint: .leading, endPoint: .trailing
            ),
            in: RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous)
        )
        .overlay(
            RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous)
                .strokeBorder(.separator.opacity(0.5), lineWidth: 1)
        )
    }
}

/// A list row rendered as a soft card — consistent across Results / Needs Review / History.
struct RowCard<Content: View>: View {
    @ViewBuilder var content: Content
    var body: some View {
        content
            .padding(.horizontal, Theme.Space.md)
            .padding(.vertical, Theme.Space.sm + 2)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(.background.secondary, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .strokeBorder(.separator.opacity(0.4), lineWidth: 1)
            )
    }
}

/// Small leading icon chip for list rows.
struct IconChip: View {
    let icon: String
    let tint: Color
    var body: some View {
        Image(systemName: icon)
            .font(.system(size: 13, weight: .semibold))
            .foregroundStyle(tint)
            .frame(width: 30, height: 30)
            .background(tint.opacity(0.14), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }
}
