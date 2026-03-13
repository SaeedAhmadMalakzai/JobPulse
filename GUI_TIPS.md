# JobPulse GUI – Tips and suggestions

## For users

- **First run:** If you see "First run: checking dependencies...", the app is installing Python packages and Playwright Chromium. Wait until it says "Dependencies ready. Starting bot..."; the bot will then start automatically.
- **Activity panel:** Blue = info, green = success/applied, orange = skipped/warning, red = errors. Use **Clear** to reset before a new run.
- **Results:** After each run, check the **Applied** and **Skipped** tabs to see exactly which jobs were applied to and which were skipped (with reasons).
- **Save before Start:** Always click **Save** in Keywords, Accounts, and Settings before clicking **Start**, so the bot uses your latest data.
- **Playwright errors:** If you see "Executable doesn't exist" for Chromium, run in a terminal: `playwright install chromium` (use the same Python as the app, e.g. `.venv/bin/playwright install chromium`).

## For developers (improving the GUI)

- **More animation:** Add a `QPropertyAnimation` on the status label (e.g. opacity or color pulse) while the bot is running.
- **Sound:** Optional short sound when a run finishes (success vs. errors).
- **Export results:** Add a "Export" button to save the Applied/Skipped lists to a CSV or text file.
- **Run history:** Keep the last N runs’ summaries in a sidebar or a "History" tab.
- **Per-portal toggle:** Let users enable/disable specific portals (e.g. LinkedIn, Jobs.af) via checkboxes in the Accounts tab.
- **Dark theme:** Add a theme switch (light/dark) and a second stylesheet.
- **System tray:** Minimize to tray when the bot is running and show a notification when the run finishes.

## Recommendations – what else to add to the application

- **Scheduling:** Run the bot automatically (e.g. every day at 9 AM).
- **Notifications:** Desktop notification when a run finishes (e.g. "Applied to 3 jobs").
- **Last run summary on Dashboard:** Show "Last run: 2 applied, 5 skipped" with a link to Results.
- **Per-portal enable/disable:** Checkboxes in Accounts to turn specific job sites on or off.
- **Resume/CV selector:** Choose among multiple CVs (e.g. Developer CV, Data CV).
- **Application limit:** "Apply to at most N jobs per run" to cap applications.
- **Retry failed:** Re-run only jobs that errored last time.
- **Check for updates:** Button or menu to check for a new JobPulse version (e.g. GitHub releases).
