#!/usr/bin/env python3
"""
swap_domain.py — Switch every SEO-critical URL on the site from the GitHub
Pages staging URL to the production domain.

Usage from the repo root:
    python3 scripts/swap_domain.py
or to revert (for testing):
    python3 scripts/swap_domain.py --revert

What it touches
---------------
* canonical / hreflang URLs (relative + absolute variants)
* Open Graph + Twitter og:url, og:image, twitter:image
* JSON-LD @id, url, image, sameAs, mainEntityOfPage
* sitemap.xml entries (absolute URLs)
* robots.txt Sitemap: line

What it does NOT touch
----------------------
* Internal anchors like #modele, #expertises (relative, still valid)
* External links to formspree, fonts that we deleted earlier, etc.
* Asset paths (assets/visuals/...) which stay relative
"""
import argparse, re, sys, pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

OLD_BASE = "https://laetitiaperson.github.io/hymeria-site"
NEW_BASE = "https://www.hymeria.com"

# additional aliases sometimes used in JSON-LD (no trailing slash, no www, etc.)
PAIRS = [
    (OLD_BASE + "/", NEW_BASE + "/"),
    (OLD_BASE, NEW_BASE),
]


def patch(text: str, revert: bool) -> tuple[str, int]:
    n = 0
    pairs = [(a, b) for a, b in PAIRS]
    if revert:
        pairs = [(b, a) for a, b in pairs]
    for old, new in pairs:
        text, k = re.subn(re.escape(old), new, text)
        n += k
    return text, n


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--revert", action="store_true",
                   help="reverse the swap (production -> staging)")
    args = p.parse_args()

    targets = list(REPO_ROOT.glob("*.html")) + list(REPO_ROOT.glob("insights/*.html"))
    for extra in ("sitemap.xml", "robots.txt"):
        f = REPO_ROOT / extra
        if f.exists():
            targets.append(f)

    total_files = 0
    total_repl = 0
    for f in targets:
        original = f.read_text(encoding="utf-8")
        new, n = patch(original, args.revert)
        if n:
            f.write_text(new, encoding="utf-8")
            total_files += 1
            total_repl += n
            print(f"  {f.relative_to(REPO_ROOT)}: {n} URLs swapped")

    direction = "production -> staging" if args.revert else "staging -> production"
    print(f"\n{direction}: {total_repl} URLs across {total_files} files.")
    print(f"Verify with: grep -rn '{OLD_BASE if not args.revert else NEW_BASE}' --include='*.html' --include='*.xml' --include='*.txt' .")


if __name__ == "__main__":
    sys.exit(main())
