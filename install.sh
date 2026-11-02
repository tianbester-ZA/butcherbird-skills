#!/bin/bash
# Installs the Butcherbird skills for Claude Code. Safe to run again. Nothing here prints or stores a credential.
# Every command reads from /dev/null, because this script can arrive through a pipe and they would eat the rest of it.
#   ./install.sh                  from a copy of the repo, or piped from GitHub (see README)
#   SKIP_SETUP=1 ./install.sh     skip the /bb:edit tools (you can still write scripts and search the books)
#   BB_MARKETPLACE=/some/path ./install.sh   install from a local copy instead of GitHub (for testing)
set -u

REPO="tianbester-ZA/butcherbird-skills"
SOURCE="${BB_MARKETPLACE:-$REPO}"
CONFIG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

say()  { printf '%s\n' "$*"; }
stop() { printf '\nStopped: %s\n' "$*"; exit 1; }

say "Butcherbird skills: installing"
say ""

command -v git    >/dev/null 2>&1 || stop "git isn't installed. Run: xcode-select --install"
command -v claude >/dev/null 2>&1 || stop "Claude Code isn't installed. See https://code.claude.com/docs"
command -v python3 >/dev/null 2>&1 || stop "python3 isn't installed. Run: xcode-select --install"
say "OK  git, Claude Code and python3"

# The repo is public, so no GitHub login is needed. HTTPS always works; SSH only works with a key.
export CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1

if claude plugin marketplace list 2>/dev/null </dev/null | grep -qE '(^|[^[:alnum:]-])butcherbird([^[:alnum:]-]|$)'; then
  say "OK  marketplace already added"
  claude plugin marketplace update butcherbird >/dev/null 2>&1 </dev/null
else
  claude plugin marketplace add "$SOURCE" </dev/null || stop "couldn't add the marketplace"
fi

if claude plugin list 2>/dev/null </dev/null | grep -q "bb@butcherbird"; then
  claude plugin update bb@butcherbird >/dev/null 2>&1 </dev/null
  say "OK  plugin already installed, and up to date"
else
  claude plugin install bb@butcherbird </dev/null || stop "couldn't install the plugin"
fi

# Auto-update: off by default for a marketplace like ours. autoUpdate on its settings entry turns it on.
# FORCE_AUTOUPDATE_PLUGINS keeps it on in the Claude desktop app, which starts Claude Code with updates switched off.
SETTINGS="$CONFIG/settings.json" python3 - <<'PY' || stop "couldn't turn on auto-update in settings.json. Turn it on under Marketplaces in /plugin instead."
import json, os
path = os.environ["SETTINGS"]
d = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
entry = d.get("extraKnownMarketplaces", {}).get("butcherbird")
if entry is None:
    raise SystemExit("the marketplace isn't declared in settings.json")
entry["autoUpdate"] = True
env = d.setdefault("env", {})
env["FORCE_AUTOUPDATE_PLUGINS"] = "1"
env["CLAUDE_CODE_PLUGIN_PREFER_HTTPS"] = "1"
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(d, f, indent=2)
    f.write("\n")
os.replace(tmp, path)
PY
say "OK  auto-update on"

say ""
if [ "${SKIP_SETUP:-0}" = "1" ]; then
  say "Skipped the /bb:edit tools. /bb:edit checks for them when you first run it."
else
  say "Checking the tools /bb:edit needs (the first time takes a few minutes):"
  ROOT=$(CONFIG="$CONFIG" python3 - <<'PY'
import json, os
p = os.path.join(os.environ["CONFIG"], "plugins", "installed_plugins.json")
try:
    print(json.load(open(p))["plugins"]["bb@butcherbird"][0]["installPath"])
except (OSError, KeyError, IndexError, ValueError):
    pass
PY
)
  SETUP="$ROOT/skills/edit/scripts/setup.py"
  [ -f "$SETUP" ] || SETUP="$SOURCE/plugins/bb/skills/edit/scripts/setup.py"
  if [ -f "$SETUP" ]; then
    python3 "$SETUP" --data "$CONFIG/plugins/data/bb-butcherbird" </dev/null
    say ""
    say "Anything marked MISSING only affects /bb:edit. The fix is on its line. /bb:script and /bb:books work now."
  else
    say "Couldn't find the setup script. /bb:edit runs it when you first use it."
  fi
fi

say ""
say "Done. Open Claude Code in any folder and try:"
say "  /bb:books what makes a hook work"
say "  /bb:script five videos for <client> and <the deal>"
say "  /bb:edit <your footage folder>"
say "If Claude Code was already open, run /reload-plugins first."
