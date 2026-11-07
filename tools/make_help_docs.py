"""Write docs/help/*.md from help_text.HELP_TABS, the same text the app's Help shows. Part of every release.
Usage: python tools/make_help_docs.py   (from the program folder). check_pages() is what the self-test compares."""
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import help_text


def page_name(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") + ".md"


def pages():
    """{file name: text}: one page per Help tab and an index."""
    out, index = {}, ["# MediaClinic Help", "", "The same text as Help in the app.", ""]
    for title, body in help_text.HELP_TABS:
        clean = re.sub(r"^[^A-Za-z0-9]+", "", title)
        name = page_name(clean)
        out[name] = f"# {clean}\n\n" + re.sub(r"\[\[(.+?)\]\]", r"`\1`", body).strip() + "\n"
        index.append(f"- [{clean}]({name})")
    out["README.md"] = "\n".join(index) + "\n"
    return out


def check_pages(folder):
    """The names that are missing or differ; [] when the pages match the app."""
    bad = []
    for name, text in pages().items():
        p = os.path.join(folder, name)
        if not os.path.isfile(p) or open(p, encoding="utf-8").read() != text:
            bad.append(name)
    return bad


if __name__ == "__main__":
    folder = os.path.join(HERE, "docs", "help")
    os.makedirs(folder, exist_ok=True)
    for name, text in pages().items():
        with open(os.path.join(folder, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    print("wrote", len(pages()), "pages to", folder)
