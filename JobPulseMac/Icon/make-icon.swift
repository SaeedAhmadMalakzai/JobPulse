// Renders a native macOS app icon (1024×1024 PNG) with AppKit/CoreGraphics:
// a Big Sur–style rounded-rect "squircle" with an indigo→violet gradient, a soft
// top highlight and drop shadow, and a crisp white lightning bolt (the ⚡ JobPulse mark).
//
// Usage:  swift make-icon.swift /path/to/icon_1024.png
import AppKit

let size: CGFloat = 1024
let outPath = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "icon_1024.png"

guard let rep = NSBitmapImageRep(
    bitmapDataPlanes: nil, pixelsWide: Int(size), pixelsHigh: Int(size),
    bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
    colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0
) else { fatalError("could not create bitmap") }

guard let ctx = NSGraphicsContext(bitmapImageRep: rep) else { fatalError("no context") }
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = ctx

func srgb(_ r: CGFloat, _ g: CGFloat, _ b: CGFloat, _ a: CGFloat = 1) -> NSColor {
    NSColor(srgbRed: r/255, green: g/255, blue: b/255, alpha: a)
}

// Squircle geometry (native macOS icons keep transparent margin around the art).
let inset: CGFloat = 100
let rect = NSRect(x: inset, y: inset, width: size - 2 * inset, height: size - 2 * inset)
let radius: CGFloat = 185
let squircle = NSBezierPath(roundedRect: rect, xRadius: radius, yRadius: radius)

// 1) Base fill + soft drop shadow.
NSGraphicsContext.saveGraphicsState()
let shadow = NSShadow()
shadow.shadowBlurRadius = 36
shadow.shadowOffset = NSSize(width: 0, height: -22)
shadow.shadowColor = NSColor.black.withAlphaComponent(0.28)
shadow.set()
srgb(79, 70, 229).setFill()      // indigo base (also colors the shadow)
squircle.fill()
NSGraphicsContext.restoreGraphicsState()

// 2) Vertical gradient (indigo → violet), clipped to the squircle.
NSGraphicsContext.saveGraphicsState()
squircle.addClip()
let grad = NSGradient(colors: [srgb(99, 102, 241), srgb(124, 58, 237)])!
grad.draw(in: rect, angle: -90)

// 3) Subtle top highlight for depth.
let highlight = NSGradient(colors: [NSColor.white.withAlphaComponent(0.20),
                                    NSColor.white.withAlphaComponent(0.0)])!
highlight.draw(in: NSRect(x: rect.minX, y: rect.midY, width: rect.width, height: rect.height / 2), angle: -90)
NSGraphicsContext.restoreGraphicsState()

// 4) White lightning bolt (the JobPulse mark), with a faint shadow for separation.
let bolt = NSBezierPath()
let pts: [NSPoint] = [
    NSPoint(x: 539, y: 724),   // top
    NSPoint(x: 402, y: 495),
    NSPoint(x: 495, y: 495),
    NSPoint(x: 478, y: 300),   // bottom point
    NSPoint(x: 622, y: 546),
    NSPoint(x: 529, y: 546),
]
bolt.move(to: pts[0])
for p in pts.dropFirst() { bolt.line(to: p) }
bolt.close()

NSGraphicsContext.saveGraphicsState()
let boltShadow = NSShadow()
boltShadow.shadowBlurRadius = 22
boltShadow.shadowOffset = NSSize(width: 0, height: -10)
boltShadow.shadowColor = NSColor.black.withAlphaComponent(0.22)
boltShadow.set()
NSColor.white.setFill()
bolt.fill()
NSGraphicsContext.restoreGraphicsState()

NSGraphicsContext.restoreGraphicsState()

guard let data = rep.representation(using: .png, properties: [:]) else { fatalError("png encode failed") }
try! data.write(to: URL(fileURLWithPath: outPath))
print("✓ wrote \(outPath)")
