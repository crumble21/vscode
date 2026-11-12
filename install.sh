#!/usr/bin/env bash
# Symlink this repo's config into VSCodium and/or VS Code (Linux + macOS).
#
#   ./install.sh            every editor that's installed (codium, code)
#   ./install.sh codium     just VSCodium
#   ./install.sh code       just VS Code
#
# Existing files are moved aside to <name>.bak.<timestamp>, never deleted. Safe to re-run.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
stamp="$(date +%Y%m%d-%H%M%S)"
config="${XDG_CONFIG_HOME:-$HOME/.config}"

case "$(uname -s)" in
    Linux)  app_support="$config" ;;
    Darwin) app_support="$HOME/Library/Application Support" ;;
    *) echo "Unsupported OS — use install.ps1 on Windows." >&2; exit 1 ;;
esac

if (( $# )); then
    editors=("$@")
else
    editors=()
    command -v codium >/dev/null && editors+=(codium)
    command -v code   >/dev/null && editors+=(code)
    (( ${#editors[@]} )) || { echo "Neither codium nor code is on PATH; name one: ./install.sh codium|code" >&2; exit 1; }
fi

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

unlink_old() {  # remove a link from an older layout of this repo, only if it points into the repo
    local dst="$1"
    if [[ -L "$dst" && "$(readlink "$dst")" == "$repo/"* && ! -e "$dst" ]]; then
        rm "$dst"; echo "removed $dst (stale link from an older layout)"
    fi
}

register_theme() {  # register_theme <extensions dir>
    # The editor only loads folders listed in extensions.json once that file exists.
    local ext_dir="$1"
    [[ -f "$ext_dir/extensions.json" ]] || return 0
    if ! command -v python3 >/dev/null; then
        echo "warning: python3 not found; add local.greenpuccin to $ext_dir/extensions.json by hand" >&2
        return 0
    fi
    local version
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
}

for editor in "${editors[@]}"; do
    case "$editor" in
        codium) name=VSCodium; user_dir="$app_support/VSCodium/User"; ext_dir="${VSCODIUM_EXTENSIONS_DIR:-$HOME/.vscode-oss/extensions}" ;;
        code)   name="VS Code"; user_dir="$app_support/Code/User";    ext_dir="${VSCODE_EXTENSIONS_DIR:-$HOME/.vscode/extensions}" ;;
        *) echo "Unknown editor '$editor' (use codium or code)" >&2; exit 1 ;;
    esac
    echo "== $name"
    link "$repo/User/settings.json"    "$user_dir/settings.json"
    link "$repo/User/keybindings.json" "$user_dir/keybindings.json"
    # Greenpuccin theme as a local extension. The folder is linked, so `theme/build.py` changes
    # show up after Developer: Reload Window.
    link "$repo/theme/greenpuccin" "$ext_dir/local.greenpuccin"
    register_theme "$ext_dir"
    if [[ "$(uname -s)" == Linux ]]; then
        # Arch wrappers: /usr/bin/codium reads codium-flags.conf, /usr/bin/code reads code-flags.conf
        link "$repo/linux/electron-flags.conf" "$config/$editor-flags.conf"
    fi
    echo
done

if [[ "$(uname -s)" == Linux && -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
    echo "== Hyprland"
    unlink_old "$HOME/.local/bin/codium-term"
    unlink_old "$HOME/.oh-my-zsh/custom/vscodium.zsh"
    unlink_old "$config/hypr/vscodium.lua"
    link "$repo/linux/editor-term" "$HOME/.local/bin/editor-term"
    if [[ -d "$HOME/.oh-my-zsh/custom" ]]; then
        link "$repo/shell/editor.zsh" "$HOME/.oh-my-zsh/custom/editor.zsh"
    fi
    link "$repo/linux/hypr/editor-glass.lua" "$config/hypr/editor-glass.lua"
    echo
    echo "Hyprland: add this line to hyprland.lua (once) to load the window opacity rule:"
    echo '    require("editor-glass")'
fi

echo
echo "Done. Restart the editor to pick up launch flags and the title bar setting."
