# JobPulse

**Always scanning. Always applying.**

Job application bot for Afghan job portals and LinkedIn: discovers jobs, applies via web forms or email, and notifies you when you get a response (interview/acceptance).

---

## Download & run

### For everyone: .exe and .dmg (no terminal needed)

Pre-built installers let you **download, install, and run** without Python or the terminal:

- **Windows:** Download **JobPulse-win64.zip** from the [Releases](https://github.com/SaeedAhmadMalakzai/JobPulse/releases) page. Unzip, copy `.env.example` to `.env` in the same folder as `JobPulse.exe`, edit `.env` with your details, then double‑click **JobPulse.exe**.
- **Mac:** Download **JobPulse-mac.dmg**, open it, drag **JobPulse** to Applications. On first run the app creates a config folder and `.env` at `~/Library/Application Support/JobPulse`; edit `.env` there with your details, then open **JobPulse** from Applications.

The first run may download Chromium once (~150 MB). Full step‑by‑step instructions: **[INSTALL.md](INSTALL.md)**.

---

### Option A: Run from terminal (developers)

You need **Python 3.10+**. Clone or [download the repo](https://github.com/SaeedAhmadMalakzai/JobPulse/archive/refs/heads/main.zip), then:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env               # then edit .env
python -m src.gui                  # or: ./run_gui
```

### Option B: Build .exe / .app yourself

From the project root with venv active:

- **Windows:** `scripts\build_windows.bat` → `dist\JobPulse\JobPulse.exe` and `dist\JobPulse-win64.zip`.
- **Mac:** `./scripts/build_mac.sh` → `dist/JobPulse.app` and `dist/JobPulse-mac.dmg`.

All credentials and personal data go in `.env` only (never in the repo).

---

## Supported Portals

- [ACBAR](https://www.acbar.org/) – Job Centre & Application Form
- [Jobs.af](https://jobs.af/) – Browse & apply
- [UN Jobs – Afghanistan](https://unjobs.org/duty_stations/afghanistan)
- [Wazifaha](https://www.wazifaha.org/)
- [Hadaf.af](https://hadaf.af/)

## Features

- **Job discovery**: Scrapes listed portals, filters by your keywords (IT, programming, AI, management, etc.), and skips expired jobs (close date).
- **Apply by email**: When a job post lists an HR/application email, the bot sends your CV and cover letter from your configured email.
- **Apply by form**: When a job post links to a Google Form or other application URL, the bot fills name, email, job title, uploads CV (and cover letter), and submits. Forms that use CAPTCHA may require manual apply or a CAPTCHA-solving service (e.g. 2Captcha) in future.
- **Response alerts**: Checks your application inbox and emails you when a possible interview/acceptance is detected.
- **Headless**: Runs on a VPS/cron; no need to keep your laptop on.

## Setup

### 1. Clone and install

```bash
cd jobpulse
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Environment variables

Copy the example file and add your own credentials and personal details:

```bash
cp .env.example .env
# Edit .env with your real values. Never commit .env to Git.
```

- **Email (applications)**: `SMTP_USER`, `SMTP_PASSWORD`. Use an [app password](https://support.google.com/accounts/answer/185833) for Gmail if you use 2FA.
- **Email (alerts)**: `ALERT_EMAIL` to receive response notifications.
- **Applicant details**: Name, phone, country, LinkedIn URL (see `.env.example`). Used for forms and cover letter signature.
- **Portal credentials**: Only set the ones you use (Jobs.af, ACBAR, Wazifaha, LinkedIn, etc.).
- **Cover letter**: Optional `COVER_LETTER_UNIVERSITY`, `COVER_LETTER_PREVIOUS_ORGANIZATION`.

All secrets and personal data belong in `.env` only. See [SECURITY.md](SECURITY.md).

### 3. Files to attach

Resume path is set in `.env` (`CV_PATH`). Cover letters are **generated per job** from the job title and company; no static file needed.

**Gmail:** If you use 2FA, use an [App Password](https://support.google.com/accounts/answer/185833) in `SMTP_PASSWORD` and `IMAP_PASSWORD` instead of your normal password.

## Running

**GUI (recommended for non-technical users):**

```bash
python -m src.gui
```

Opens a desktop window: Dashboard (Start/Stop), Keywords, Accounts, and Settings tabs, plus a colored **Activity** panel and **Results** (Applied / Skipped lists when a run finishes). Edit values and click Save per tab, then Start to run the bot. On first run, the app can install dependencies automatically. See [GUI_TIPS.md](GUI_TIPS.md) for tips and suggestions.

**One-off run from terminal (discover → apply → check responses → send alerts):**

```bash
python -m src.main
```

**Cron (e.g. every 6 hours on a VPS):**

```bash
chmod +x scripts/run_cron.sh
# Crontab entry:
0 */6 * * * /path/to/jobpulse/scripts/run_cron.sh >> /path/to/jobpulse/logs/cron.log 2>&1
```

On the VPS: install Python 3, run `pip install -r requirements.txt` and `playwright install chromium`, then create `.env` with your credentials in the project folder.

**List matching, non-expired jobs (no apply):**

```bash
python -m src.main --discover-only
```

**Dry-run (see what would be applied, without sending):**

```bash
python -m src.main --dry-run
```

**Only check for responses and send alerts:**

```bash
python -m src.main --check-responses-only
```

**CAPTCHA:** If an application form shows reCAPTCHA or similar, the bot will try to submit but may be blocked. For full automation on such forms you’d need a CAPTCHA-solving API (e.g. 2Captcha); add `CAPTCHA_API_KEY` in `.env` when supported.

## Building the app (executable)

Use the provided scripts to build a distributable .exe (Windows) or .app/.dmg (Mac):

- **Windows:** Run `scripts\build_windows.bat` (with venv active). Output: `dist\JobPulse\` and `dist\JobPulse-win64.zip`.
- **Mac:** Run `./scripts/build_mac.sh`. Output: `dist/JobPulse.app` and `dist/JobPulse-mac.dmg`.

Or build manually: `pip install pyinstaller` then `pyinstaller jobpulse.spec`. On first run, the app will download Chromium once if needed. Build on each OS for a native build. Do not commit `build/` or `dist/`.

## Project layout

```
jobpulse/
├── src/
│   ├── main.py           # CLI entrypoint
│   ├── config.py         # Env/config
│   ├── gui/              # Desktop GUI (PySide6)
│   ├── email_utils.py    # SMTP send + IMAP inbox check
│   ├── alerts.py         # Send "response detected" to you
│   └── sites/
│       ├── base.py       # Base adapter
│       ├── acbar.py
│       ├── jobs_af.py
│       ├── unjobs.py
│       ├── wazifaha.py
│       └── hadaf.py
├── data/                 # Optional: store applied job IDs
├── logs/                 # Optional: run logs
├── .env.example
├── requirements.txt
└── README.md
```

## Security & pushing to GitHub

- **No credentials or personal data are in the repository.** All secrets (emails, passwords, API keys, names, phone numbers) live only in `.env`, which is in `.gitignore` and is never committed. The codebase and `.env.example` contain only placeholders (e.g. `your-application-email@gmail.com`).
- **Before you push:** Run `git status` and ensure `.env` and `data/` are not staged. If they are, unstage them. Never commit `.env` or PDFs (CV/cover letter).
- Use a dedicated email for applications and app passwords where possible.
- See [SECURITY.md](SECURITY.md) for a full guide (users and contributors).

## Further improvements

Ideas for packaging, UX, and features (onboarding, auto-update, more portals, etc.) are in [IMPROVEMENTS.md](IMPROVEMENTS.md).

## License

[MIT](LICENSE) – use, modify, and distribute freely. No warranty.

## Disclaimer

Automating applications may violate some portals’ terms of service. Use at your own risk. Prefer official APIs where available.
