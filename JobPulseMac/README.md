# JobPulse — Native macOS App

A native **SwiftUI** front-end for JobPulse, built from scratch. It delivers a real
macOS experience (sidebar navigation, SF Symbols, system materials, native forms,
a live activity stream) while driving the proven Python automation engine as a
child process — so all 14 scrapers, LinkedIn Easy Apply, dynamic form-filling,
CAPTCHA handling, and IMAP/SMTP keep working unchanged.

## Architecture

```
SwiftUI app (this package)
   │  reads/writes  →  <engine>/.env          (EngineConfig)
   │  spawns        →  python -m src.main      (EngineRunner: streams stdout live)
   │  reads         →  <engine>/data/jobpulse.db   (Database: needs-review, applications)
   ▼
Python engine (../  — the JobPulse repo)
```

- **EngineConfig** — resolves the engine folder and reads/writes its `.env`.
- **EngineRunner** — runs the bot via `Process`, streams + classifies each output line.
- **Database** — read-only SQLite over `jobpulse.db` (needs-review queue, applied count).
- **AppState** — `@MainActor ObservableObject` tying it together.

Screens: **Home** (readiness, Run/Stop, dry-run, live activity), **Results**
(applied / skipped), **Needs Review** (jobs the engine honestly skipped — open & apply
manually), **History**, **Settings** (engine folder, SMTP/IMAP, identity, CV, targeting).

## Requirements

- macOS 14+, Xcode 16+ / Swift 6 toolchain
- The Python engine (this repo) with its `.venv` set up — see the main README.

## Build & run

```bash
cd JobPulseMac
swift build            # compile-check
swift run              # run from the terminal
# or build a double-clickable bundle:
./make-app.sh release  # → JobPulse.app
open JobPulse.app
```

On first launch, open **Settings** and confirm the **Engine folder** points at the
JobPulse repo (it auto-detects when run from inside the repo). Everything you save is
written to the engine's `.env`, exactly what the Python bot reads.

## Notes

- The app is **ad-hoc signed** by `make-app.sh` so it launches locally. For
  distribution, sign + notarize with a Developer ID.
- This is the native UI layer; the automation lives in the Python engine. Reimplementing
  individual adapters natively (HTTP-only ones first) is a possible future step.
