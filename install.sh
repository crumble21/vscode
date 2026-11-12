#!/usr/bin/env bash
# Symlink this repo's VSCodium config into place (Linux + macOS).
# Existing files are moved aside to <name>.bak.<timestamp>, never deleted.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
stamp="$(date +%Y%m%d-%H%M%S)"

case "$(uname -s)" in
    Linux)  user_dir="${XDG_CONFIG_HOME:-$HOME/.config}/VSCodium/User" ;;
    Darwin) user_dir="$HOME/Library/Application Support/VSCodium/User" ;;
    *) echo "Unsupported OS — use install.ps1 on Windows." >&2; exit 1 ;;
esac

link() {  # link <source> <target>
    local src="$1" dst="$2"
    mkdir -p "$(dirname "$dst")"
    if [[ -L "$dst" && "$(readlink "$dst")" == "$src" ]]; then
        echo "ok      $dst"; return
    fi
    if [[ -e "$dst" || -L "$dst" ]]; then
        mv "$dst" "$dst.bak.$stamp"
        echo "backup  $dst -> $dst.bak.$stamp"
    fi
    ln -s "$src" "$dst"
    echo "linked  $dst"
}

link "$repo/User/settings.json"    "$user_dir/settings.json"
link "$repo/User/keybindings.json" "$user_dir/keybindings.json"

# Greenpuccin theme, as a local extension (the folder is linked, so `theme/build.py` changes show up
# after Developer: Reload Window). VSCodium only loads folders listed in extensions.json once that file
# exists, so register it there too.
ext_dir="${VSCODIUM_EXTENSIONS_DIR:-$HOME/.vscode-oss/extensions}"
link "$repo/theme/greenpuccin" "$ext_dir/local.greenpuccin"
if [[ -f "$ext_dir/extensions.json" ]]; then
    if command -v python3 >/dev/null; then
        version="$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$repo/theme/greenpuccin/package.json" | head -1)"
        python3 -I - "$ext_dir" "$version" <<'PY'
import json, os, sys
ext_dir, version = sys.argv[1:3]
path, name = os.path.join(ext_dir, "extensions.json"), "local.greenpuccin"
entries = [e for e in json.load(open(path)) if e.get("identifier", {}).get("id") != name]
entries.append({"identifier": {"id": name}, "version": version, "relativeLocation": name,
                "location": {"$mid": 1, "path": os.path.join(ext_dir, name), "scheme": "file"}})
json.dump(entries, open(path, "w"))
print(f"registered {name} {version} in {path}")
PY
    else
        echo "warning: python3 not found; add local.greenpuccin to $ext_dir/extensions.json by hand" >&2
    fi
fi

if [[ "$(uname -s)" == Linux ]]; then
    link "$repo/linux/codium-flags.conf" "${XDG_CONFIG_HOME:-$HOME/.config}/codium-flags.conf"
    if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
        link "$repo/linux/hypr/vscodium.lua" "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/vscodium.lua"
        link "$repo/linux/codium-term"       "$HOME/.local/bin/codium-term"
        if [[ -d "$HOME/.oh-my-zsh/custom" ]]; then
            link "$repo/shell/vscodium.zsh" "$HOME/.oh-my-zsh/custom/vscodium.zsh"
        fi
        echo
        echo "Hyprland: add this line to hyprland.lua (once) to load the window rule:"
        echo '    require("vscodium")'
    fi
fi

echo
echo "Done. Restart VSCodium to pick up launch flags."
