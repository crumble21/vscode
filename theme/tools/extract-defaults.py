#!/usr/bin/env python3
"""Extract the editor's registered colour keys and their built-in defaults.

    python3 -I theme/tools/extract-defaults.py [<editor>/resources/app]

Defaults to VSCodium (/opt/vscodium-bin), falling back to VS Code (/usr/share/code); both register
the same colour keys at the same version. Writes theme/tools/vscode-color-defaults.json. Re-run after
an editor upgrade so the theme covers any newly added colour keys, then run theme/build.py.

Defaults are stored as small expression trees, so build.py can resolve them against the
Greenpuccin palette instead of using VSCodium's own hex values:
    {"hex": "#rrggbbaa"}   {"ref": "other.key"}   null
    {"op": "transparent"|"lighten"|"darken", "v": expr, "f": number}
    {"op": "opaque", "v": expr}   {"op": "mix", "v": expr, "with": expr, "f": ratio of `with`}   {"op": "oneOf", "vs": [expr, ...]}
    {"op": "ifDefined", "if": expr, "then": expr, "else": expr}
    {"unknown": "<source>"}
"""
import collections, glob, json, os, re, sys

APPS = ["/opt/vscodium-bin/resources/app", "/usr/share/code/resources/app"]
APP = sys.argv[1] if len(sys.argv) > 1 else next((a for a in APPS if os.path.isdir(a)), APPS[0])
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vscode-color-defaults.json")
js = open(os.path.join(APP, "out/vs/workbench/workbench.desktop.main.js"), encoding="utf-8").read()

KEY = r'"([a-zA-Z][\w-]*(?:\.[\w-]+)*)"'
ID = r'[\w$]+'

# The registerColor() helper is minified; it's the function called as REG("key",{dark:...}).
REG = collections.Counter(re.findall(r'(' + ID + r')\(' + KEY[:-1] + r'",\{(?:dark|light):', js)) \
    .most_common(1)[0][0][0]
# Colour-transform helpers are minified too; find them by their bodies.
OPS = {"0": "darken", "1": "lighten", "2": "transparent", "3": "opaque", "4": "oneOf", "6": "ifDefined"}
funcs = {m.group(1): OPS[m.group(2)]
         for m in re.finditer(r'function (' + ID + r')\([^)]*\)\{return\{op:(\d)', js) if m.group(2) in OPS}
NAMED = {"white": (255, 255, 255, 1), "black": (0, 0, 0, 1), "transparent": (0, 0, 0, 0),
         "red": (255, 0, 0, 1), "blue": (0, 0, 255, 1), "green": (0, 255, 0, 1), "cyan": (0, 255, 255, 1),
         "lightgrey": (211, 211, 211, 1)}


def closer(s, i):  # s[i] is an opener; index of its matching closer
    depth, q = 0, None
    for j in range(i, len(s)):
        c = s[j]
        if q:
            if c == "\\": continue
            if c == q: q = None
            continue
        if c in "\"'`": q = c
        elif c in "{([": depth += 1
        elif c in "})]":
            depth -= 1
            if depth == 0: return j
    raise ValueError("unbalanced")


def take_expr(s, i):  # text of the expression starting at s[i], up to a top-level , ; or closer
    j = i
    while j < len(s) and s[j] not in ",;)}]":
        if s[j] in "{([": j = closer(s, j) + 1
        elif s[j] in "\"'`": j = s.index(s[j], j + 1) + 1
        else: j += 1
    return s[i:j]


def split_top(s):
    parts, i = [], 0
    while i <= len(s):
        e = take_expr(s, i)
        parts.append(e)
        i += len(e) + 1
    return [p for p in parts if p.strip()]


# minified variable -> (position, expression text); names are reused across modules, keep all
var_defs = collections.defaultdict(list)
for m in re.finditer(r'[,;{\s](' + ID + r')=(?!=)', js):
    try: expr = take_expr(js[m.end():m.end() + 400], 0)
    except ValueError: continue  # ran past the window: not a short colour expression
    if expr: var_defs[m.group(1)].append((m.start(), expr))


def hexa(r, g, b, a=1.0):
    return {"hex": "#%02x%02x%02x%02x" % (round(r), round(g), round(b), round(a * 255))}


def norm_hex(h):
    h = h.lstrip("#").lower()
    if len(h) in (3, 4): h = "".join(c * 2 for c in h)
    if len(h) == 6: h += "ff"
    return {"hex": "#" + h}


def num(a, pos):
    try: return float(a)
    except ValueError:
        v = lookup(a.strip(), pos)
        try: return float(v)
        except (TypeError, ValueError): return 0.5


def lookup(name, pos):  # nearest definition before `pos`, else the first after it
    defs = var_defs.get(name)
    if not defs: return None
    before = [e for p, e in defs if p < pos]
    return before[-1] if before else defs[0][1]


def parse(e, pos, depth=0):
    e = e.strip()
    if depth > 8: return {"unknown": e}
    if e in ("null", "void 0", "undefined"): return None
    m = re.fullmatch(r'"(#[0-9a-fA-F]{3,8})"', e)
    if m: return norm_hex(m.group(1))
    m = re.fullmatch(KEY, e)
    if m: return {"ref": m.group(1)}
    m = re.fullmatch(re.escape(REG) + r'\(' + KEY + r',.*', e, re.S)
    if m: return {"ref": m.group(1)}
    m = re.fullmatch(ID + r'\.fromHex\("(#[0-9a-fA-F]{3,8})"\)', e)
    if m: return norm_hex(m.group(1))
    m = re.fullmatch(r'new ' + ID + r'\(new ' + ID + r'\(([\d.]+),([\d.]+),([\d.]+)(?:,([\d.]+))?\)\)', e)
    if m: return hexa(*(float(x) for x in m.group(1, 2, 3)), float(m.group(4) or 1))
    m = re.fullmatch(ID + r'\.(' + "|".join(NAMED) + r')', e)
    if m: return hexa(*NAMED[m.group(1)])
    m = re.fullmatch(r'(.+)\.(transparent|lighten|darken)\(([^()]+)\)', e, re.S)
    if m: return {"op": m.group(2), "v": parse(m.group(1), pos, depth + 1), "f": num(m.group(3), pos)}
    m = re.fullmatch(r'(' + ID + r')\((.*)\)', e, re.S)
    if m and m.group(1) in funcs and closer(e, len(m.group(1))) == len(e) - 1:
        op, args = funcs[m.group(1)], split_top(m.group(2))
        p = lambda a: parse(a, pos, depth + 1)
        if op in ("transparent", "lighten", "darken"): return {"op": op, "v": p(args[0]), "f": num(args[1], pos)}
        if op == "opaque": return {"op": "opaque", "v": p(args[0])}
        if op == "oneOf": return {"op": "oneOf", "vs": [p(a) for a in args]}
        if op == "ifDefined": return {"op": "ifDefined", "if": p(args[0]), "then": p(args[1]), "else": p(args[2])}
    m = re.fullmatch(r'\{op:7,color:(.+?),with:(.+?),ratio:([\d.]+)\}', e)
    if m:  # inline mix(color, with, ratio)
        return {"op": "mix", "v": parse(m.group(1), pos, depth + 1), "with": parse(m.group(2), pos, depth + 1),
                "f": float(m.group(3))}
    if re.fullmatch(ID, e):
        d = lookup(e, pos)
        if d is not None: return parse(d, pos, depth + 1)
    return {"unknown": e}


out = {}
for m in re.finditer(re.escape(REG) + r'\(' + KEY + r',', js):
    key, pos = m.group(1), m.start()
    if key in out: continue
    arg = take_expr(js, m.end())
    fm = re.fullmatch(r'\{(.*)\}', arg, re.S)
    if fm and re.search(r'(^|,)(dark|light):', fm.group(1)):
        fields = dict(p.split(":", 1) for p in split_top(fm.group(1)) if ":" in p)
        out[key] = {mode: parse(fields.get(mode, "null"), pos) for mode in ("dark", "light")}
    else:
        v = parse(arg, pos)
        if v and re.fullmatch(r'!?[01]|true|false', v.get("unknown", "")): continue  # not a colour
        out[key] = {"dark": v, "light": v}

# Terminal ANSI colours are registered in a loop from a table: {ansiBlack:{index:0,defaults:{...}},...}
for m in re.finditer(r'"?(ansi[A-Za-z]+)"?:\{index:\d+,defaults:', js):
    i = m.end()
    fields = dict(p.split(":", 1) for p in split_top(js[i + 1:closer(js, i)]) if ":" in p)
    out.setdefault("terminal." + m.group(1), {mode: parse(fields.get(mode, "null"), m.start()) for mode in ("dark", "light")})

for path in sorted(glob.glob(os.path.join(APP, "extensions/*/package.json"))):
    for c in json.load(open(path, encoding="utf-8")).get("contributes", {}).get("colors", []):
        d = c.get("defaults", {})
        out.setdefault(c["id"], {mode: parse(json.dumps(d[mode]) if d.get(mode) else "null", 0)
                                 for mode in ("dark", "light")})

unknown = sorted({k for k, v in out.items() if '"unknown"' in json.dumps(v)})
json.dump(dict(sorted(out.items())), open(OUT, "w"), indent=1)
print(f"{len(out)} colour keys -> {OUT}")
if unknown:
    print(f"{len(unknown)} with unparsed parts (build.py falls back to name rules):", ", ".join(unknown))
