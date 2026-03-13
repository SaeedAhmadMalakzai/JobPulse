"""Read and write .env file for the GUI. Preserves keys not managed by the GUI."""
import re
import shutil
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Project root: when frozen use exe dir (Windows) or Application Support (macOS .app); else parent of src."""
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parent.parent.parent
    exe = Path(sys.executable).resolve()
    # macOS .app: use Application Support so .env and data are in a user writable place
    if sys.platform == "darwin" and exe.parent.name == "MacOS" and "Contents" in str(exe.parent.parent):
        root = Path.home() / "Library" / "Application Support" / "JobPulse"
        root.mkdir(parents=True, exist_ok=True)
        return root
    return exe.parent


def _env_path() -> Path:
    return get_project_root() / ".env"


def _example_path() -> Path:
    return get_project_root() / ".env.example"


def load_env() -> dict:
    """Parse .env into a dict. If .env missing, copy .env.example and then load."""
    root = get_project_root()
    env_file = _env_path()
    example_path = _example_path()
    if not env_file.exists():
        if not example_path.exists() and getattr(sys, "frozen", False) and sys.platform == "darwin":
            # macOS .app: copy .env.example from app bundle to Application Support
            bundle_resources = Path(sys.executable).resolve().parent.parent / "Resources"
            bundle_example = bundle_resources / ".env.example"
            if bundle_example.exists():
                try:
                    shutil.copy(bundle_example, example_path)
                except Exception:
                    pass
        if example_path.exists():
            shutil.copy(example_path, env_file)
    out = {}
    if not env_file.exists():
        return out
    content = env_file.read_text(encoding="utf-8", errors="replace")
    for line in content.splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val.startswith('"') and val.endswith('"') and len(val) >= 2:
                val = val[1:-1].replace('\\"', '"')
            elif val.startswith("'") and val.endswith("'") and len(val) >= 2:
                val = val[1:-1].replace("\\'", "'")
            out[key] = val
    return out


def save_env(updates: dict) -> None:
    """Merge updates into .env and write back. Preserves existing keys and comment lines."""
    env_file = _env_path()
    existing = load_env()
    existing.update(updates)
    lines_out = []
    seen = set()
    if env_file.exists():
        content = env_file.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            if not line.strip() or line.strip().startswith("#"):
                lines_out.append(line)
                continue
            m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
            if m:
                key = m.group(1)
                seen.add(key)
                val = existing.get(key, "")
                if "\n" in val or '"' in val or " " in val or "#" in val:
                    val_esc = val.replace("\\", "\\\\").replace('"', '\\"')
                    lines_out.append(f'{key}="{val_esc}"')
                else:
                    lines_out.append(f"{key}={val}")
                continue
            lines_out.append(line)
    for key, val in sorted(existing.items()):
        if key in seen:
            continue
        if "\n" in val or '"' in val or " " in val or "#" in val:
            val_esc = val.replace("\\", "\\\\").replace('"', '\\"')
            lines_out.append(f'{key}="{val_esc}"')
        else:
            lines_out.append(f"{key}={val}")
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
