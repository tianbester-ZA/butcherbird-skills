"""Finds where this pack keeps its setup on this Mac: the Python, the models and the compiled text tool.
They live in Claude Code's data folder for the plugin, because the plugin folder is replaced on every update.

Order: $BB_EDIT_DATA, then $CLAUDE_PLUGIN_DATA, then the folder holding the Python running this
(setup.py builds it at <data>/venv), then the record setup.py leaves in Claude's plugin data folders, then a fallback.
Standard library only, because setup.py uses it before the Python tools exist."""
import glob, os, sys

RECORD = "setup.json"


def _config_dir():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def data_dir():
    for name in ("BB_EDIT_DATA", "CLAUDE_PLUGIN_DATA"):
        if os.environ.get(name):
            return os.environ[name]
    if os.path.basename(sys.prefix) == "venv" and os.path.exists(os.path.join(os.path.dirname(sys.prefix), RECORD)):
        return os.path.dirname(sys.prefix)
    found = glob.glob(os.path.join(_config_dir(), "plugins", "data", "bb-*", RECORD))
    if found:
        return os.path.dirname(max(found, key=os.path.getmtime))
    return os.path.expanduser("~/.cache/butcherbird-bb")


def model(name):
    return os.path.join(data_dir(), "models", name)


def venv_python():
    return os.path.join(data_dir(), "venv", "bin", "python")


def need(module):
    """Stop with the fix, not a traceback, when run with the wrong Python."""
    try:
        __import__(module)
    except ImportError:
        sys.exit(f"this needs the pack's Python ({module} is missing here).\n"
                 f"Run it with: {venv_python()}\nIf that doesn't exist, run setup.py first.")


def need_file(path):
    if not os.path.exists(path):
        sys.exit(f"missing {path}\nRun setup.py with --download-models (or --download-large for the bigger whisper model).")
