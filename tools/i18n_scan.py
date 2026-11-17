# =============================================================================
# tools/i18n_scan.py — texts shown to the user that do not come from mc_i18n   ### NEW v0.20.0 UI1c ###
#
# Plan Part 6a, UI1 point 10: an `ast` scan of every module for string literals passed to text= / label= /
# title( / the tooltip helper / messagebox.*( / menu add_* / register_action / the status-bar helpers, that are not
# a t() / tn() call.  "report" mode during UI1c–UI1d (counts), "fail" mode from UI1e (0 findings).
#
#   python tools/i18n_scan.py [--fail] [module.py …]   prints the findings and the counts; --fail (UI1e): exit
#                                                       code 1 when there is any finding (the self-test fails on one)
#
# A finding: (file, line, where, text).  "where" is Class.function (or "<module>") so a step can check its own scope
# (UI1c: the main window, the movie panel, the registry, the right-click menu, the status bar).
# =============================================================================
import ast
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES = ("mediaclinic_v0_20_0.py", "settings_dialog.py", "sort_engine.py", "folder_classifier.py",
           "export_list.py", "settings_controller.py", "help_text.py", "image_fix.py", "collection_rules.py")

TEXT_KW = {"text", "label", "title", "message", "detail"}
CALL_ARG0 = {"showinfo", "showwarning", "showerror", "askyesno", "askokcancel", "askyesnocancel",
             "askquestion", "askretrycancel"}                 # messagebox.*(title, message)
ERR_FUNCS = {"_finish_error"}                                    # UI1e: (title, message) shown in a message box
TIP_FUNCS = {"_add_btn_tooltip", "_add_tooltip", "add_tooltip", "Tooltip", "_tip"}
SET_VARS = {"status_var", "stats_var", "_pct_var", "_eta_var", "_msg_var", "_status_var", "_info_var"}   # UI1e: StringVars of shown texts


def _var_name(node):
    return node.attr if isinstance(node, ast.Attribute) else (node.id if isinstance(node, ast.Name) else "")


STATUS_FUNCS = {"_set_status", "_status", "_set_action", "_sb_set", "_flash_status", "_update_status_bar"}

# never translated: brands, formats, file names, symbols (plan UI1 point 8 / point 10)
ALLOW_WORDS = {"MediaClinic", "TMDB", "TMDb", "IMDb", "OMDb", "fanart.tv", "FFmpeg", "FFprobe", "Kodi", "Jellyfin",
               "Emby", "Plex", "NFO", "XML", "Real-ESRGAN", "Infuse", "MediaBrowser", "nfo", "xml", "OK", "GitHub",
               "Full", "Scan", "Quick", "Ctrl", "Shift", "Alt", "Esc", "F1", "F5", "F10", "Y", "N", "v"}
FILE_RE = re.compile(r"\b[\w\-]+\.(?:jpg|png|nfo|xml|json|log|txt|csv|xlsx|exe|py|ico|srt|mkv)\b", re.I)


def _is_t_call(node):
    if isinstance(node, ast.Call):
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
        return name in ("t", "tn", "_t", "_tn", "action_label", "_n")
    return False


def _literal_text(node):
    """The literal text of a str constant / f-string / "a" + "b" (None when the node is not literal text)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = _literal_text(node.left), _literal_text(node.right)
        if a is not None or b is not None:
            return (a or "{}") + (b or "{}")
    if isinstance(node, ast.IfExp):
        a, b = _literal_text(node.body), _literal_text(node.orelse)
        if a is not None or b is not None:
            return (a or "") + " | " + (b or "")
    return None


def needs_translation(text):
    """True when *text* holds a word a person reads (letters left after brands, file names and placeholders)."""
    s = FILE_RE.sub(" ", text)
    s = re.sub(r"\{[^}]*\}", " ", s)
    words = re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'\-]*", s)
    return any(w not in ALLOW_WORDS and len(w) > 1 for w in words)


class _Scan(ast.NodeVisitor):
    def __init__(self, fname):
        self.fname, self.stack, self.found = fname, [], []

    def _where(self):
        return ".".join(self.stack) or "<module>"

    def visit_ClassDef(self, node):
        self.stack.append(node.name); self.generic_visit(node); self.stack.pop()

    def visit_FunctionDef(self, node):
        self.stack.append(node.name); self.generic_visit(node); self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def _add(self, node, arg):
        if arg is None or _is_t_call(arg):
            return
        txt = _literal_text(arg)
        if txt is not None and needs_translation(txt):
            self.found.append((self.fname, getattr(arg, "lineno", node.lineno), self._where(), txt))

    def visit_Call(self, node):
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
        for kw in node.keywords:
            if kw.arg in TEXT_KW:
                self._add(node, kw.value)
        if name in CALL_ARG0 or name == "title" and isinstance(f, ast.Attribute):
            for a in node.args[:2]:
                self._add(node, a)
        elif name in ERR_FUNCS:
            for a in node.args[:2]:
                self._add(node, a)
        elif name in TIP_FUNCS and len(node.args) >= 2:
            self._add(node, node.args[1])
        elif name == "register_action" and len(node.args) >= 2:
            self._add(node, node.args[1])
        elif name in STATUS_FUNCS:
            for a in node.args:
                self._add(node, a)
        elif name == "set" and isinstance(f, ast.Attribute) and node.args and _var_name(f.value) in SET_VARS:   # UI1e
            self._add(node, node.args[0])
        elif name in ("add_command", "add_checkbutton", "add_radiobutton", "add_cascade", "add_button"):
            for a in node.args[:1]:
                self._add(node, a)
        self.generic_visit(node)


def scan_file(path):
    src = open(path, encoding="utf-8-sig").read()
    s = _Scan(os.path.basename(path))
    s.visit(ast.parse(src))
    return s.found


def scan(modules=MODULES, base=HERE):
    out = []
    for m in modules:
        p = os.path.join(base, m)
        if os.path.exists(p):
            out.extend(scan_file(p))
    return out


def in_scope(finding, scopes):
    """True when the finding's Class.function starts with one of *scopes* ("App._build_ui", "_MoviePanel" …)."""
    where = finding[2]
    return any(where == s or where.startswith(s + ".") for s in scopes)


# ── v0.20.0 UI1f: the broad look — any English sentence (3+ words) in a function body that is not a log / raise /
# comparison / dict key / docstring and does not go through t(); the texts that stay English by design are listed in
# tools/i18n_allow.json (module, function, text start).  leftovers() returns what is neither translated nor allowed.
_LOG_BASES = ("logger", "logging", "log", "_i18n", "re", "os", "json")
_SKIP_CALLS = ("t", "tn", "_t", "warning", "info", "debug", "error", "exception", "get", "startswith", "endswith",
               "replace", "split", "join", "sub", "match", "search", "compile", "findall", "format", "encode",
               "strftime", "strptime", "open", "_log", "getattr", "setdefault", "pop", "find", "index", "count")
_WORDS = re.compile(r"[A-Za-z]{2,}")


def _broad_file(path):
    src = open(path, encoding="utf-8-sig").read()
    tree = ast.parse(src)
    par = {}
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n):
            par[c] = n

    def skip(node):
        p = node
        while p in par:
            q = par[p]
            if isinstance(q, ast.Call):
                f = q.func
                name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
                base = f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else ""
                if base in _LOG_BASES or name in _SKIP_CALLS:
                    return True
            if isinstance(q, (ast.Raise, ast.Compare, ast.Assert, ast.Subscript)):
                return True
            if isinstance(q, ast.Dict) and p in q.keys:
                return True
            if isinstance(q, ast.Expr) and q.value is node:              # a docstring / bare string statement
                return True
            if isinstance(q, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                return isinstance(q, (ast.ClassDef, ast.Module))
            p = q
        return False

    def func_of(node):
        p = node
        while p in par:
            p = par[p]
            if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return p.name
        return ""

    out = set()
    for n in ast.walk(tree):
        s = None
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and not isinstance(par.get(n), ast.JoinedStr):
            s = n.value
        elif isinstance(n, ast.JoinedStr):
            s = "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in n.values)
        if not s or len(_WORDS.findall(s)) < 3 or " " not in s or s.startswith(("<", "http", "#", "%", "{", "(?", "^")) \
                or "\\" in s[:3] or skip(n):
            continue
        out.add((n.lineno, func_of(n), s))
    return sorted(out)


def leftovers(modules=MODULES, base=HERE):
    """[(module, line, function, text)] — English sentences neither translated nor in tools/i18n_allow.json."""
    allow = json.load(open(os.path.join(base, "tools", "i18n_allow.json"), encoding="utf-8"))["allow"]
    ok = {(a["module"], a["func"], a["text"]) for a in allow}
    res = []
    for m in modules:
        p = os.path.join(base, m)
        if not os.path.exists(p):
            continue
        for ln, fn, s in _broad_file(p):
            if (m, fn, s[:60]) not in ok:
                res.append((m, ln, fn, s))
    return res


if __name__ == "__main__":
    fail = "--fail" in sys.argv[1:]
    mods = [a for a in sys.argv[1:] if a != "--fail"] or MODULES
    found = scan(mods)
    by_file = {}
    for f, ln, where, txt in found:
        by_file[f] = by_file.get(f, 0) + 1
        print(f"{f}:{ln}  [{where}]  {txt[:90]!r}")
    print()
    for f, n in sorted(by_file.items()):
        print(f"{n:5d}  {f}")
    print(f"{len(found):5d}  in all")
    if fail and found:
        sys.exit(1)
