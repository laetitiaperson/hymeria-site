#!/usr/bin/env python3
"""
relativize_paths.py — Convert root-absolute paths (/assets/, /fr/, /en/, /logo-*.png, etc.)
to relative paths in HTML body content, so the site works identically on:
- GitHub Pages staging (served under /hymeria-site/ prefix)
- Hostinger production (served at the domain root)

What it touches
---------------
* href="/X"      → href="../../X"  (relative to current file depth)
* src="/X"       → src="../../X"
* url('/X')      → url('../../X')  (in inline CSS or HTML)
* window.location strings starting with / in root index.html

What it does NOT touch
----------------------
* External URLs (https://..., http://, mailto:, tel:)
* Hash-only anchors (#hero, #insights)
* <meta> URLs in <head> (canonical, og:url, hreflang — must stay absolute for SEO)
* <link rel="alternate"> hreflang URLs
* JSON-LD URLs (they're full https:// URLs anyway)
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Files to process
TARGETS = (
    list(REPO.glob("fr/**/index.html"))
    + list(REPO.glob("en/**/index.html"))
    + [REPO / "index.html", REPO / "404.html", REPO / "landing-fr.html"]
)
TARGETS = [t for t in TARGETS if t.exists()]


def to_relative(absolute_path: str, current_file: Path) -> str:
    """Convert /X/Y/Z to relative path from current_file's directory."""
    target = absolute_path.lstrip("/")  # 'assets/visuals/hero-bg.webp'
    cur_dir = current_file.parent.relative_to(REPO)  # PosixPath('fr/contact')
    parts = cur_dir.parts if str(cur_dir) != "." else ()
    depth = len(parts)
    if depth == 0:
        return target if target else "./"
    prefix = "../" * depth
    return prefix + target


# Match href/src/url("...") with paths starting with / (but not //, http, mailto, tel, #)
HREF_RE = re.compile(r'(href|src)="(/[^/"][^"]*)"')
URL_RE = re.compile(r"url\(['\"]?(/[^'\")]+)['\"]?\)")
# Match window.location patterns in JS
JS_LOC_RE = re.compile(r"(window\.location\.(?:replace|assign|href\s*=)\s*\(?['\"])(/[^'\"]+)(['\"])")


def patch_content(content: str, current_file: Path) -> tuple[str, int]:
    n = 0

    def replace_href(m):
        nonlocal n
        attr, path = m.group(1), m.group(2)
        # Skip protocol-relative URLs and special schemes (re already excludes // via [^/"])
        new = to_relative(path, current_file)
        n += 1
        return f'{attr}="{new}"'

    def replace_url(m):
        nonlocal n
        path = m.group(1)
        new = to_relative(path, current_file)
        n += 1
        return f"url('{new}')"

    def replace_js_loc(m):
        nonlocal n
        prefix, path, suffix = m.group(1), m.group(2), m.group(3)
        new = to_relative(path, current_file)
        n += 1
        return f"{prefix}{new}{suffix}"

    content = HREF_RE.sub(replace_href, content)
    content = URL_RE.sub(replace_url, content)
    content = JS_LOC_RE.sub(replace_js_loc, content)
    return content, n


def main() -> None:
    total_files = 0
    total_repl = 0
    for f in TARGETS:
        original = f.read_text(encoding="utf-8")
        patched, n = patch_content(original, f)
        if n:
            f.write_text(patched, encoding="utf-8")
            total_files += 1
            total_repl += n
            print(f"  {f.relative_to(REPO)}: {n} paths relativized")
    print(f"\nTotal: {total_repl} paths across {total_files} files.")


if __name__ == "__main__":
    main()
