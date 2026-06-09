import SwiftUI
import AppKit

/// A polished terminal/console for the live engine stream: a dark code surface
/// (in both light and dark mode), a window-style header with live status, an
/// inline filter, timestamped + severity-gutter rows, monospaced text, copy,
/// autoscroll, and a blinking caret while the engine runs.
struct ConsoleView: View {
    let lines: [ActivityLine]
    var running: Bool = false
    var onClear: (() -> Void)? = nil

    @State private var autoscroll = true
    @State private var filter = ""

    private static let surface = Color(red: 0.043, green: 0.055, blue: 0.086)   // ~#0B0E16
    private static let headerBg = Color(red: 0.09, green: 0.10, blue: 0.14)
    private static let tsFormatter: DateFormatter = {
        let f = DateFormatter(); f.dateFormat = "HH:mm:ss"; return f
    }()

    private var visible: [ActivityLine] {
        filter.isEmpty ? lines : lines.filter { $0.text.localizedCaseInsensitiveContains(filter) }
    }

    var body: some View {
        VStack(spacing: 0) {
            header
            Rectangle().fill(Color.black.opacity(0.35)).frame(height: 1)
            consoleBody
        }
        .background(Self.surface)
        .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous)
                .strokeBorder(Color.white.opacity(0.08), lineWidth: 1)
        )
        .shadow(color: .black.opacity(0.28), radius: 16, y: 8)
    }

    // MARK: header (terminal window bar)

    private var header: some View {
        HStack(spacing: 10) {
            Image(systemName: "terminal.fill")
                .font(.caption)
                .foregroundStyle(.white.opacity(0.45))
            Text("jobpulse · engine")
                .font(.system(.caption, design: .monospaced))
                .foregroundStyle(.white.opacity(0.6))
            if running { RunningBadge() }
            Spacer()
            searchField
            Text("\(visible.count)")
                .font(.system(.caption2, design: .monospaced).monospacedDigit())
                .foregroundStyle(.white.opacity(0.4))
            iconButton(autoscroll ? "arrow.down.to.line" : "pause.fill",
                       help: autoscroll ? "Auto-scroll on" : "Auto-scroll paused") { autoscroll.toggle() }
            iconButton("doc.on.doc", help: "Copy") { copyAll() }
            if onClear != nil {
                iconButton("trash", help: "Clear") { onClear?() }
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Self.headerBg)
    }

    private var searchField: some View {
        HStack(spacing: 5) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 10))
                .foregroundStyle(.white.opacity(0.35))
            TextField("filter", text: $filter)
                .textFieldStyle(.plain)
                .font(.system(.caption, design: .monospaced))
                .foregroundStyle(.white.opacity(0.9))
                .frame(width: 130)
            if !filter.isEmpty {
                Button { filter = "" } label: {
                    Image(systemName: "xmark.circle.fill").font(.system(size: 10))
                        .foregroundStyle(.white.opacity(0.4))
                }.buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(Color.white.opacity(0.06), in: Capsule())
    }

    // MARK: body

    private var consoleBody: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    ForEach(visible) { line in
                        ConsoleRow(line: line, timestamp: Self.tsFormatter.string(from: line.time))
                            .id(line.id)
                    }
                    if running { CaretRow().id("__caret") }
                }
                .padding(.vertical, 8)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .overlay(alignment: .center) {
                if visible.isEmpty && !running {
                    Text(filter.isEmpty ? "Press Run to start the engine." : "No lines match “\(filter)”.")
                        .font(.system(.callout, design: .monospaced))
                        .foregroundStyle(.white.opacity(0.3))
                }
            }
            .onChange(of: lines.count) { _, _ in
                guard autoscroll else { return }
                withAnimation(.easeOut(duration: 0.18)) {
                    if running {
                        proxy.scrollTo("__caret", anchor: .bottom)
                    } else if let last = visible.last {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }
        }
    }

    // MARK: helpers

    private func iconButton(_ icon: String, help: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 11))
                .foregroundStyle(.white.opacity(0.55))
                .frame(width: 18, height: 18)
        }
        .buttonStyle(.plain)
        .help(help)
    }

    private func copyAll() {
        let text = visible.map { $0.text }.joined(separator: "\n")
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)
    }
}

// MARK: - rows

private struct ConsoleRow: View {
    let line: ActivityLine
    let timestamp: String

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            RoundedRectangle(cornerRadius: 1.5)
                .fill(line.kind.consoleColor)
                .frame(width: 3)
            Text(timestamp)
                .font(.system(.caption2, design: .monospaced))
                .foregroundStyle(.white.opacity(0.28))
                .padding(.top, 1)
            Text(line.text)
                .font(.system(.caption, design: .monospaced))
                .foregroundStyle(line.kind.consoleColor)
                .textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 2)
        .background(line.kind.consoleRowTint)
    }
}

private struct CaretRow: View {
    @State private var on = false
    var body: some View {
        HStack(spacing: 8) {
            RoundedRectangle(cornerRadius: 1.5).fill(Color.green.opacity(0.6)).frame(width: 3)
            Text("▋")
                .font(.system(.caption, design: .monospaced))
                .foregroundStyle(.green.opacity(on ? 0.9 : 0.15))
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 2)
        .onAppear {
            withAnimation(.easeInOut(duration: 0.6).repeatForever(autoreverses: true)) { on = true }
        }
    }
}

private struct RunningBadge: View {
    @State private var on = false
    var body: some View {
        HStack(spacing: 5) {
            Circle().fill(.green).frame(width: 6, height: 6).opacity(on ? 1 : 0.3)
            Text("running")
                .font(.system(.caption2, design: .monospaced))
                .foregroundStyle(.green.opacity(0.85))
        }
        .padding(.horizontal, 7)
        .padding(.vertical, 2)
        .background(Color.green.opacity(0.12), in: Capsule())
        .onAppear {
            withAnimation(.easeInOut(duration: 0.7).repeatForever(autoreverses: true)) { on = true }
        }
    }
}

// MARK: - terminal palette (tuned for the dark surface)

private extension ActivityLine.Kind {
    var consoleColor: Color {
        switch self {
        case .applied, .success: return Color(red: 0.45, green: 0.92, blue: 0.55)
        case .skipped:           return Color(red: 1.00, green: 0.80, blue: 0.40)
        case .warning:           return Color(red: 1.00, green: 0.72, blue: 0.30)
        case .error:             return Color(red: 1.00, green: 0.45, blue: 0.42)
        case .discovery:         return Color(red: 0.45, green: 0.80, blue: 1.00)
        case .info:              return Color.white.opacity(0.86)
        case .muted:             return Color.white.opacity(0.40)
        }
    }

    var consoleRowTint: Color {
        switch self {
        case .applied, .success: return Color(red: 0.45, green: 0.92, blue: 0.55).opacity(0.06)
        case .error:             return Color(red: 1.00, green: 0.45, blue: 0.42).opacity(0.08)
        case .skipped, .warning: return Color(red: 1.00, green: 0.72, blue: 0.30).opacity(0.05)
        default:                 return .clear
        }
    }
}
