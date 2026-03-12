# Automated CV Submissions

Automated job application bot for Afghan job portals: discovers jobs, applies via web forms or email, and notifies you when you get a response (interview/acceptance).

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
cd automated-cv-submissions
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

**One-off run (discover → apply → check responses → send alerts):**

```bash
python -m src.main
```

**Cron (e.g. every 6 hours on a VPS):**

```bash
chmod +x scripts/run_cron.sh
# Crontab entry:
0 */6 * * * /path/to/automated-cv-submissions/scripts/run_cron.sh >> /path/to/automated-cv-submissions/logs/cron.log 2>&1
```

On the VPS: install Python 3, run `pip install -r requirements.txt` and `playwright install chromium`, then create `.env` with your credentials.

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

## Project layout

```
automated-cv-submissions/
├── src/
│   ├── main.py           # Entrypoint
│   ├── config.py         # Env/config
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

## Security

- **Secrets only in `.env`.** Store all passwords, API keys, and personal details in `.env`. Never commit `.env` (it is in `.gitignore`). Use `.env.example` as a template with placeholders only.
- Use a dedicated email for applications and app passwords where possible.
- The `data/` and `logs/` directories are ignored by Git; they may contain session data and job IDs.
- See [SECURITY.md](SECURITY.md) for a full guide (users and contributors).

## Disclaimer

Automating applications may violate some portals’ terms of service. Use at your own risk. Prefer official APIs where available.
