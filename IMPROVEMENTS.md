# JobPulse — Improvement Ideas & Roadmap

**Lock file:** The run lock now stores the **bot process PID** (not the GUI). When you click Start, the app checks if that process is still running. If it’s not (e.g. crash or force quit), the lock is treated as stale and removed automatically, so “lock exists” should not block you after an abnormal exit.

---

## Design

- **Custom app icon**  
  Use a dedicated JobPulse icon in the title bar and system tray instead of the system default.

- **Consistent spacing and hierarchy**  
  Use a simple 8px grid for padding/margins; make primary actions (Start, Save) more prominent than secondary (Clear, Tips).

- **Empty states**  
  When Activity or Results are empty, show a short message and one clear action (e.g. “No runs yet. Click Start to run the bot.”).

- **Status and progress**  
  One clear status line (e.g. “Idle” / “Discovering…” / “Applying (3/12)” / “Done”) and optional progress bar or step indicator for long runs.

- **Color and contrast**  
  Keep sufficient contrast for text (already improved); use a single accent color for primary actions and links.

---

## UI/UX

- **Onboarding**  
  First launch: short “Welcome” with 3 steps (Keywords → Accounts → Settings → Start) and a “Don’t show again” checkbox.

- **Inline validation**  
  When leaving a required field empty (e.g. CV path when not in dry run), show a short hint next to the field instead of only a popup on Start.

- **Confirmation patterns**  
  Use “Are you sure?” only for destructive actions (Clear applied history, Quit). Avoid confirmations for normal actions (Start, Save).

- **Responsive layout**  
  On smaller windows, allow the right panel (Activity + Results) to collapse or stack so the app stays usable.

- **Search / filter in Results**  
  Filter Applied and Skipped lists by text or by “last run only” so long lists are easier to scan.

- **Copy from Activity**  
  Right‑click or button to copy the selected Activity line or full log to clipboard.

- **Export options**  
  Besides CSV/text, optional “Copy to clipboard” for Applied/Skipped lists.

---

## Functionality

- **Per-portal CV**  
  In Accounts or Settings, choose which CV to use per portal (e.g. Tech CV for LinkedIn, General for Jobs.af).

- **Pause / Resume**  
  Pause = stop starting new applications, finish the current one. Resume continues from the queue.

- **Templates**  
  Save named presets (keywords + portals + CV + dry run) and run a template with one click.

- **Re-run last run**  
  “Run again” reuses the last run’s options without re-saving each tab.

- **Persistent Activity log**  
  Append Activity to a log file each run; add “Open log file” or “View full log” in the app or external editor.

- **Backup / restore .env**  
  “Backup config” and “Restore from backup” (e.g. `data/backups/.env.YYYY-MM-DD`).

- **Application limit per portal**  
  Optional “Max applications per portal per run” in addition to the global limit.

---

## Performance & Reliability

- **Lazy Dashboard**  
  Refresh last-run summary and stats when the Dashboard tab is selected (or on a short timer) to keep startup fast.

- **Activity cap and throttle**  
  Already in place: cap Activity list size and batch log updates. Tune limits if needed.

- **Discovery cache (optional)**  
  “Use cached discovery for X minutes” with a “Refresh now” to avoid re-fetching too often.

- **Stale lock handling**  
  Already in place: lock stores bot PID; if that process is not running, lock is removed automatically so it doesn’t block the next run.

---

## What else to add

- **Telegram / Discord / email summary**  
  Optional webhook or email to send a short “X applied, Y skipped” when a run finishes.

- **Simple analytics**  
  Local stats (e.g. CSV/JSON): date, applied/skipped counts, per-portal breakdown for your own charts or export.

- **“Open data folder”**  
  Menu or Settings link to open `data/` (logs, run history, applied store) in the file manager.

- **Check for updates**  
  Already present; optional: show a small “Update available” when a newer release is detected.

- **Help / Docs**  
  In-app “Help” or “Docs” that opens the README or a short user guide (local or GitHub).

- **Log level**  
  Settings: “Verbose / Normal / Quiet” for how much the bot prints (and how much appears in Activity).

- **Run summary in tray**  
  Tray tooltip already shows last run; optional: tray menu item “Last run: X applied, Y skipped” that opens the Results panel.

---

## Priority overview

| Priority   | Area        | Examples |
|-----------|-------------|----------|
| High      | Reliability | Stale lock (done), graceful stop (done), run lock (done) |
| High      | UX          | No save popups on Start (done), tooltips (done), clear form-filling section (done) |
| Medium    | Design      | App icon, empty states, one clear status line |
| Medium    | Functionality | Per-portal CV, Re-run last run, persistent log |
| Lower     | Nice-to-have | Templates, Pause/Resume, backup/restore, Telegram/Discord |

Implement in small steps: one or two items per release keeps changes testable and the codebase maintainable.
