"""Generate the JobPulse app icon (rounded indigo→violet tile with a lightning bolt + pulse).

Renders crisp PNGs with Qt at every size macOS wants, writes them to an .iconset,
then calls `iconutil` to produce assets/icon.icns. Also writes assets/icon.png (1024)
for the window/tray icon (used in dev and frozen builds).

Run:  QT_QPA_PLATFORM=offscreen .venv/bin/python assets/make_icon.py
"""
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QFont, QGuiApplication, QImage, QLinearGradient,
    QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient,
)

ASSETS = Path(__file__).resolve().parent


def _bolt_path(size: float) -> QPainterPath:
    """A clean lightning bolt centred in a `size`×`size` box, normalised to 0..1 coords."""
    pts = [
        (0.560, 0.140), (0.330, 0.560), (0.470, 0.560),
        (0.420, 0.860), (0.690, 0.420), (0.545, 0.420),
    ]
    poly = QPolygonF([QPointF(x * size, y * size) for x, y in pts])
    path = QPainterPath()
    path.addPolygon(poly)
    path.closeSubpath()
    return path


def render(size: int) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHints(
        QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
    )

    s = float(size)
    # macOS rounded-rect tile with a small margin (squircle-ish via large radius)
    margin = s * 0.085
    rect = QRectF(margin, margin, s - 2 * margin, s - 2 * margin)
    radius = rect.width() * 0.225

    # Background gradient: indigo-600 -> indigo-500 -> violet-600 (design system)
    grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    grad.setColorAt(0.0, QColor("#4f46e5"))
    grad.setColorAt(0.55, QColor("#6366f1"))
    grad.setColorAt(1.0, QColor("#7c3aed"))

    tile = QPainterPath()
    tile.addRoundedRect(rect, radius, radius)
    p.fillPath(tile, QBrush(grad))

    # Soft top-left sheen for depth
    p.setClipPath(tile)
    sheen = QRadialGradient(QPointF(rect.left() + rect.width() * 0.28,
                                     rect.top() + rect.height() * 0.22),
                            rect.width() * 0.9)
    sheen.setColorAt(0.0, QColor(255, 255, 255, 60))
    sheen.setColorAt(0.5, QColor(255, 255, 255, 12))
    sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.fillRect(rect, QBrush(sheen))
    p.setClipping(False)

    # Pulse ring behind the bolt (a heartbeat nod to "JobPulse")
    p.save()
    p.translate(rect.center())
    ring_pen = QPen(QColor(255, 255, 255, 55))
    ring_pen.setWidthF(s * 0.018)
    p.setPen(ring_pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    r = rect.width() * 0.34
    p.drawEllipse(QPointF(0, 0), r, r)
    p.restore()

    # Lightning bolt (white, with a faint outline for crispness)
    box = rect.width() * 0.62
    p.save()
    p.translate(rect.center().x() - box / 2, rect.center().y() - box / 2)
    bolt = _bolt_path(box)
    p.setPen(QPen(QColor(79, 70, 229, 90), max(1.0, s * 0.006)))
    p.setBrush(QBrush(QColor("#ffffff")))
    p.drawPath(bolt)
    p.restore()

    p.end()
    return img


def main() -> int:
    QGuiApplication(sys.argv)
    iconset = ASSETS / "icon.iconset"
    iconset.mkdir(exist_ok=True)

    # Standard macOS iconset sizes (1x and 2x)
    specs = [
        (16, "icon_16x16.png"), (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"), (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"), (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"), (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"), (1024, "icon_512x512@2x.png"),
    ]
    for px, name in specs:
        render(px).save(str(iconset / name), "PNG")

    # Window / tray icon
    render(1024).save(str(ASSETS / "icon.png"), "PNG")

    # Build .icns
    icns = ASSETS / "icon.icns"
    r = subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(icns)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print("iconutil failed:", r.stderr, file=sys.stderr)
        return 1
    print(f"Wrote {icns} and {ASSETS / 'icon.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
