#!/usr/bin/env bash
# Run from cron on a VPS. Example crontab (every 6 hours):
# 0 */6 * * * /path/to/automated-cv-submissions/scripts/run_cron.sh >> /path/to/automated-cv-submissions/logs/cron.log 2>&1

set -e
cd "$(dirname "$0")/.."
mkdir -p logs
if [ -d ".venv" ]; then
  .venv/bin/python -m src.main
else
  python3 -m src.main
fi
