# Security

This document explains how to keep your credentials and personal data safe when using or contributing to JobPulse.

## For users (running the bot)

- **All secrets live in `.env`.** The bot reads email addresses, passwords, API keys, and personal details only from environment variables loaded from `.env`. No secrets are hardcoded in the repository.

- **Do not commit `.env`.** The file `.env` is listed in `.gitignore`. Never add it, and never commit it to any repository (including a fork). If you use Git, run `git status` before pushing to confirm `.env` is not staged.

- **Use `.env.example` as a template.** Copy it to `.env` and fill in your own values:
  ```bash
  cp .env.example .env
  # Edit .env with your real credentials (never commit .env)
  ```

- **Optional: use a separate secrets folder.** You can keep `.env` outside the repo (e.g. in a private directory) and symlink it, or use your OS/cloud secrets manager and export variables before running the bot. The code only reads from the environment (via `config.py`).

- **Session and state files.** The `data/` directory may contain session cookies and state (e.g. `jobs_af_state.json`, `linkedin_state.json`). These are ignored by Git. Do not commit them; they can be used to access your accounts.

## For contributors (open source)

- **No personal data in code.** Do not add real names, email addresses, phone numbers, passwords, or API keys in source files, README, or comments. Use `.env` and `.env.example` (with placeholders only in `.env.example`).

- **Default config values.** `src/config.py` uses empty or generic defaults for all user-specific settings so that nothing sensitive appears if someone runs the app without a `.env` file.

- **Cover letters and bio.** Cover letter text (including university and previous employer) is driven by env vars `COVER_LETTER_UNIVERSITY`, `COVER_LETTER_PREVIOUS_ORGANIZATION`, and the usual applicant details. No real names or contact details are hardcoded in `cover_letter.py`.

## Before pushing to GitHub

- Run `git status` and ensure **`.env` is not staged**. If it appears, run `git restore --staged .env` and keep `.env` only on your machine.
- Ensure **`data/`** is not staged (it is in `.gitignore`; if you added it earlier, unstage and do not commit).
- Do not commit **PDFs** (CV, cover letter); they are ignored via `*.pdf` in `.gitignore`.
- `.env.example` is safe to commit (placeholders only). Never commit `.env`.

## If you accidentally committed secrets

If you ever committed `.env` or a file containing passwords:

1. Rotate all credentials (passwords, API keys) that were in that file immediately.
2. Remove the file from Git history (e.g. `git filter-branch` or BFG Repo-Cleaner) and force-push, or create a new repository and push only safe commits. See [GitHub: Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).
