"""Parse bot log lines and return (kind, short_message) for colored display and result extraction."""
import re
from typing import Tuple, List

# Kinds for coloring: info, success, warning, error, applied, skipped, discovery
def parse_log_line(line: str) -> Tuple[str, str]:
    """Return (kind, display_text). kind is used for color; display_text is user-friendly."""
    line = line.strip()
    if not line:
        return ("muted", "")

    # [INFO], [WARNING], [ERROR]
    if "[INFO]" in line:
        kind = "info"
    elif "[WARNING]" in line:
        kind = "warning"
    elif "[ERROR]" in line:
        kind = "error"
    else:
        kind = "info"

    # Strip timestamp and level for display
    display = re.sub(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \[(?:INFO|WARNING|ERROR)\] \s*", "", line)

    # Discovering
    if "Discovering jobs from" in line:
        kind = "info"
        display = "🔍 Discovering jobs from all portals..."
    elif re.search(r"\]\s+discovered \d+ jobs", line):
        m = re.search(r"\[([^\]]+)\]\s+discovered (\d+) jobs", line)
        if m:
            adapter, n = m.group(1), m.group(2)
            kind = "success"
            display = f"✓ {adapter}: found {n} jobs"
    elif "Running: full" in line or "discover + apply" in line:
        kind = "info"
        display = "▶ Starting full run (discover → apply → check responses)"
    elif "Done." in line and "discovered=" in line:
        kind = "success"
        display = "✔ Run finished. " + line.split("Done.")[-1].strip()
    elif "Applied:" in line or "] Applied:" in line:
        m = re.search(r"Applied:\s*(.+)", line)
        title = m.group(1).strip() if m else line
        kind = "applied"
        display = f"✓ Applied: {title[:70]}{'…' if len(title) > 70 else ''}"
    elif "Skip (" in line or "Skip (" in display:
        # e.g. "Skip (already applied...): Title" or "Skip (outside scope): Title"
        m = re.search(r"Skip\s*\(([^)]+)\)[:\s]*(.+)", line)
        if m:
            reason, title = m.group(1).strip(), m.group(2).strip()
            kind = "skipped"
            display = f"⊘ Skipped: {title[:50]}… — {reason}"
        else:
            kind = "skipped"
            display = display[:80]
    elif "Discovery error" in line or "Discovery failed" in line:
        kind = "error"
        m = re.search(r"\[([^\]]+)\].*", line)
        adapter = m.group(1) if m else "?"
        display = f"✗ {adapter}: discovery failed"
    elif "Apply error" in line or "Error applying" in line:
        kind = "error"
        m = re.search(r"Error applying to (.+?):", line) or re.search(r"error for (.+?)(?::|$)", line, re.I)
        detail = m.group(1).strip()[:50] if m else "see log"
        display = f"✗ Apply error: {detail}"
    elif "Exit code:" in line:
        kind = "muted"
        display = line
    else:
        # Shorten Playwright banner etc.
        if "Playwright" in line and "install" in line:
            display = "⚠ Install browsers: run ‘playwright install chromium’"
            kind = "warning"
        elif "╔" in line or "║" in line or "╚" in line:
            return ("muted", "")
        elif len(display) > 85:
            display = display[:82] + "…"

    return (kind, display if display else line[:80])


def extract_applied_and_skipped(log_text: str) -> Tuple[List[str], List[Tuple[str, str]]]:
    """From full log text, return (applied_list, skipped_list). skipped_list items are (title, reason)."""
    applied = []
    skipped = []
    for line in log_text.splitlines():
        line = line.strip()
        if "  [" in line and "] Applied:" in line:
            m = re.search(r"\] Applied:\s*(.+)", line)
            if m:
                applied.append(m.group(1).strip())
        if "  [" in line and "Skip (" in line:
            m = re.search(r"Skip\s*\(([^)]+)\)[:\s]*(.+)", line)
            if m:
                reason, title = m.group(1).strip(), m.group(2).strip()
                skipped.append((title[:80], reason))
    return (applied, skipped)
