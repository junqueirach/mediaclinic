# =============================================================================
# pyver_guard.py — Python 3.10 / 3.11 syntax guard for the app's modules
# MediaClinic v0.20.1 BF5                                        ### NEW v0.20.1 BF5 ###
#
# The app supports Python 3.10 and newer (CI runs 3.10 and 3.12). Python 3.12
# (PEP 701) accepts f-strings that 3.10 / 3.11 reject; v0.20.0 shipped two such
# lines in the source and the app did not load on 3.10 / 3.11 at all.
#
# Two layers, both pure (no Tk, no files written):
#   * compile_errors(): compile every module with the running interpreter
#     (on 3.10 / 3.11 this catches the problem directly);
#   * pep701_findings(): on 3.12+, where f-strings are tokenized into parts,
#     find what 3.10 / 3.11 would reject inside a replacement field:
#       - a string that uses the enclosing f-string's quote,
#       - a nested f-string that uses the enclosing quote,
#       - a backslash (in a string literal or as an operator).
#     On 3.10 / 3.11 the tokenizer keeps an f-string as one token, so this
#     layer returns nothing there and compile_errors() does the work.
#   * newer_syntax_findings() (v0.20.2 B27): statements newer than 3.10 that
#     the running interpreter parses — except* (3.11), the type statement and
#     generic parameters def f[T] / class C[T] (3.12), template strings t"…"
#     and "except A, B:" without brackets (3.14).
#   * project_modules() (v0.20.2 B27): the app's modules AND the tests and
#     tools/ (CI runs the tests on 3.10 too).
# =============================================================================
from __future__ import annotations

import ast
import io
import os
import sys
import tokenize
from typing import Iterable, NamedTuple


class Finding(NamedTuple):
    """One problem: the file, its line and what is wrong."""
    path: str
    line: int
    text: str


def _quote_of(token_text: str) -> str:
    """The opening quote of a string or f-string token: ', ", ''' or \"\"\"."""
    s = token_text.lstrip("rRbBuUfFtT")
    return s[:3] if s[:3] in ('"""', "'''") else s[:1]


def _same_quote(inner: str, outer: str) -> bool:
    """True when *inner* would end an f-string opened with *outer* on Python < 3.12."""
    if len(outer) == 3:
        return inner == outer
    return inner[:1] == outer


def pep701_findings(source: str, path: str = "<source>") -> list[Finding]:
    """Constructs inside f-string replacement fields that Python 3.10 / 3.11 cannot parse.

    Works on Python 3.12+ only (FSTRING_START tokens); returns [] on older versions."""
    if not hasattr(tokenize, "FSTRING_START"):
        return []
    out: list[Finding] = []
    stack: list[str] = []                      # quotes of the f-strings that are open
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, SyntaxError) as e:
        return [Finding(path, getattr(e, "lineno", 0) or 0, f"cannot tokenize: {e}")]
    for tok in tokens:
        if tok.type == tokenize.FSTRING_START:
            q = _quote_of(tok.string)
            if any(_same_quote(q, o) for o in stack):
                out.append(Finding(path, tok.start[0], f"nested f-string uses the enclosing quote {q}"))
            stack.append(q)
        elif tok.type == tokenize.FSTRING_END:
            if stack:
                stack.pop()
        elif stack and tok.type == tokenize.STRING:
            q = _quote_of(tok.string)
            if any(_same_quote(q, o) for o in stack):
                out.append(Finding(path, tok.start[0], f"string {tok.string[:30]!r} inside an f-string with the same quote {stack[-1]}"))
            if "\\" in tok.string:
                out.append(Finding(path, tok.start[0], f"backslash in an f-string expression: {tok.string[:30]!r}"))
        elif stack and tok.type == tokenize.OP and tok.string == "\\":
            out.append(Finding(path, tok.start[0], "backslash in an f-string expression"))
    return out


def compile_errors(source: str, path: str = "<source>") -> list[Finding]:
    """[] when the running interpreter compiles *source*, else the syntax error."""
    try:
        compile(source, path, "exec", dont_inherit=True)
    except SyntaxError as e:
        return [Finding(path, e.lineno or 0, f"SyntaxError on Python {sys.version_info[0]}.{sys.version_info[1]}: {e.msg}")]
    return []


def newer_syntax_findings(source: str, path: str = "<source>") -> list[Finding]:   ### NEW v0.20.2 B27 ###
    """Statements newer than Python 3.10 that this interpreter parses (so compile_errors() cannot see them):
    except* (3.11), type X = … and def f[T] / class C[T] (3.12), t-strings and except A, B: (3.14)."""
    try:
        tree = ast.parse(source, path)
    except SyntaxError:
        return []                              # compile_errors() reports it
    out: list[Finding] = []
    try_star = getattr(ast, "TryStar", None)
    type_alias = getattr(ast, "TypeAlias", None)
    template = getattr(ast, "TemplateStr", None)
    for node in ast.walk(tree):
        line = getattr(node, "lineno", 0) or 0
        if try_star is not None and isinstance(node, try_star):
            out.append(Finding(path, line, "except* needs Python 3.11"))
        elif type_alias is not None and isinstance(node, type_alias):
            out.append(Finding(path, line, "the type statement needs Python 3.12"))
        elif template is not None and isinstance(node, template):
            out.append(Finding(path, line, "a template string (t-string) needs Python 3.14"))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and getattr(node, "type_params", None):
            out.append(Finding(path, line, f"generic parameters on {node.name}[…] need Python 3.12"))
        elif isinstance(node, ast.ExceptHandler) and isinstance(node.type, ast.Tuple):
            seg = ast.get_source_segment(source, node.type) or ""
            if not seg.lstrip().startswith("("):
                out.append(Finding(path, line, "except A, B: without brackets needs Python 3.14"))
    return out


def app_modules(app_dir: str) -> list[str]:
    """The app's .py files: the top level of *app_dir* (main file and modules), not tests or tools."""
    return sorted(os.path.join(app_dir, f) for f in os.listdir(app_dir)
                  if f.endswith(".py") and not f.startswith(("selftest", "test_", "settings_test_harness")))


def project_modules(app_dir: str) -> list[str]:                  ### NEW v0.20.2 B27 ###
    """Every .py file CI runs: the top level of *app_dir* (app, self-test, tests, harness), tools/ and, in the
    repository layout, tests/ (v0.20.2: the check found no test there and failed in CI's layout)."""
    out = [os.path.join(app_dir, f) for f in os.listdir(app_dir) if f.endswith(".py")]
    for sub in ("tools", "tests"):
        d = os.path.join(app_dir, sub)
        if os.path.isdir(d):
            out += [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".py")]
    return sorted(out)


def scan(paths: Iterable[str]) -> list[Finding]:
    """The three layers over every file in *paths*."""
    found: list[Finding] = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            src = f.read()
        name = os.path.basename(p)
        found += compile_errors(src, name) + pep701_findings(src, name) + newer_syntax_findings(src, name)
    return found


if __name__ == "__main__":                       # python tools/pyver_guard.py [app folder]
    _dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _hits = scan(project_modules(_dir))                       # v0.20.2 B27: the tests and tools too
    for h in _hits:
        print(f"{h.path}:{h.line}: {h.text}")
    print(f"{len(_hits)} finding(s)")
    sys.exit(1 if _hits else 0)
