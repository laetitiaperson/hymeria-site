#!/usr/bin/env python3
"""
One-shot migration: flat root pages -> /fr/<slug>/ and /en/<slug>/ structure.

For each source -> destination pair:
  - Read source HTML
  - Apply transformations:
      * URL replacements for href + meta + JSON-LD + sitemap entries
      * Asset paths -> root-relative (/assets/..., /favicon..., /logo-*.png, etc.)
      * Lang-switcher hrefs -> equivalent pages in /fr/ and /en/
  - Write destination

Run from repo root. Idempotent for the URL/path substitutions.
"""
from __future__ import annotations
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE = "https://laetitiaperson.github.io/hymeria-site"

# (source path relative to repo, dest path relative to repo, "fr"|"en", language-pair-key)
# The pair-key links each FR page to its EN counterpart for lang-switcher rewriting.
PAGES = [
    # (src, dst, lang, pair_key)
    ("index-fr.html",                                "fr/index.html",                                          "fr", "home"),
    ("contact.html",                                 "fr/contact/index.html",                                  "fr", "contact"),
    ("mentions-legales.html",                        "fr/mentions-legales/index.html",                         "fr", "legal-notice"),
    ("politique-confidentialite.html",               "fr/politique-confidentialite/index.html",                "fr", "privacy"),
    ("cgu.html",                                     "fr/conditions-generales/index.html",                     "fr", "terms"),
    ("insights/ai-act-2026.html",                    "fr/insights/ai-act-2026/index.html",                     "fr", "insight-ai-act"),
    ("insights/consulting-traditionnel-ia.html",     "fr/insights/consulting-traditionnel-ia/index.html",      "fr", "insight-trad-vs-ai"),
    ("insights/exploiter-ia-sans-consultant.html",   "fr/insights/exploiter-ia-sans-consultant/index.html",    "fr", "insight-leveraging"),

    ("index-en.html",                                "en/index.html",                                          "en", "home"),
    ("contact-en.html",                              "en/contact/index.html",                                  "en", "contact"),
    ("mentions-legales-en.html",                     "en/legal-notice/index.html",                             "en", "legal-notice"),
    ("politique-confidentialite-en.html",            "en/privacy-policy/index.html",                           "en", "privacy"),
    ("cgu-en.html",                                  "en/terms/index.html",                                    "en", "terms"),
    ("insights/ai-act-2026-en.html",                 "en/insights/ai-act-2026/index.html",                     "en", "insight-ai-act"),
    ("insights/traditional-consulting-vs-ai.html",   "en/insights/traditional-consulting-vs-ai/index.html",    "en", "insight-trad-vs-ai"),
    ("insights/leveraging-ai-without-consultants.html","en/insights/leveraging-ai-without-consultants/index.html","en", "insight-leveraging"),
]

# Build url maps
# Old "absolute" URLs (BASE + old path) -> new absolute URLs (BASE + new pretty url)
# New pretty URLs (the directory form, trailing slash). For the home, /fr/ and /en/.
NEW_URL = {
    "home-fr": "/fr/",
    "contact-fr": "/fr/contact/",
    "legal-notice-fr": "/fr/mentions-legales/",
    "privacy-fr": "/fr/politique-confidentialite/",
    "terms-fr": "/fr/conditions-generales/",
    "insight-ai-act-fr": "/fr/insights/ai-act-2026/",
    "insight-trad-vs-ai-fr": "/fr/insights/consulting-traditionnel-ia/",
    "insight-leveraging-fr": "/fr/insights/exploiter-ia-sans-consultant/",

    "home-en": "/en/",
    "contact-en": "/en/contact/",
    "legal-notice-en": "/en/legal-notice/",
    "privacy-en": "/en/privacy-policy/",
    "terms-en": "/en/terms/",
    "insight-ai-act-en": "/en/insights/ai-act-2026/",
    "insight-trad-vs-ai-en": "/en/insights/traditional-consulting-vs-ai/",
    "insight-leveraging-en": "/en/insights/leveraging-ai-without-consultants/",
}

# Map "old root-relative path" -> "new root-relative path"
# Used for absolute URL rewrites (full BASE+path) and href substitutions.
OLD_TO_NEW_PATH = {
    "/index-fr.html":                                       NEW_URL["home-fr"],
    "/index-en.html":                                       NEW_URL["home-en"],
    "/contact.html":                                        NEW_URL["contact-fr"],
    "/contact-en.html":                                     NEW_URL["contact-en"],
    "/mentions-legales.html":                               NEW_URL["legal-notice-fr"],
    "/mentions-legales-en.html":                            NEW_URL["legal-notice-en"],
    "/politique-confidentialite.html":                      NEW_URL["privacy-fr"],
    "/politique-confidentialite-en.html":                   NEW_URL["privacy-en"],
    "/cgu.html":                                            NEW_URL["terms-fr"],
    "/cgu-en.html":                                         NEW_URL["terms-en"],
    "/insights/ai-act-2026.html":                           NEW_URL["insight-ai-act-fr"],
    "/insights/ai-act-2026-en.html":                        NEW_URL["insight-ai-act-en"],
    "/insights/consulting-traditionnel-ia.html":            NEW_URL["insight-trad-vs-ai-fr"],
    "/insights/traditional-consulting-vs-ai.html":          NEW_URL["insight-trad-vs-ai-en"],
    "/insights/exploiter-ia-sans-consultant.html":          NEW_URL["insight-leveraging-fr"],
    "/insights/leveraging-ai-without-consultants.html":     NEW_URL["insight-leveraging-en"],
}

PAIR_TO_NEW = {
    ("home", "fr"):           NEW_URL["home-fr"],
    ("home", "en"):           NEW_URL["home-en"],
    ("contact", "fr"):        NEW_URL["contact-fr"],
    ("contact", "en"):        NEW_URL["contact-en"],
    ("legal-notice", "fr"):   NEW_URL["legal-notice-fr"],
    ("legal-notice", "en"):   NEW_URL["legal-notice-en"],
    ("privacy", "fr"):        NEW_URL["privacy-fr"],
    ("privacy", "en"):        NEW_URL["privacy-en"],
    ("terms", "fr"):          NEW_URL["terms-fr"],
    ("terms", "en"):          NEW_URL["terms-en"],
    ("insight-ai-act", "fr"): NEW_URL["insight-ai-act-fr"],
    ("insight-ai-act", "en"): NEW_URL["insight-ai-act-en"],
    ("insight-trad-vs-ai", "fr"): NEW_URL["insight-trad-vs-ai-fr"],
    ("insight-trad-vs-ai", "en"): NEW_URL["insight-trad-vs-ai-en"],
    ("insight-leveraging", "fr"): NEW_URL["insight-leveraging-fr"],
    ("insight-leveraging", "en"): NEW_URL["insight-leveraging-en"],
}


def absolutize_assets(html: str) -> str:
    """Convert relative asset references to root-relative paths.

    Handles three styles found in the codebase:
      same-dir   : assets/..., favicon..., logo-*.png, apple-touch-icon.png, og-image.png
      parent-dir : ../assets/..., ../favicon..., ../logo-*.png, ../apple-touch-icon.png
    """

    # Patterns where we look for attr="(prefix)?asset_path"
    # We rewrite to attr="/asset_path".
    # Attributes we touch: href, src, srcset (single URL only — no comma-lists used in this codebase).
    # Use a per-pattern approach for safety.

    def sub_attr(html, attr, old, new):
        return re.sub(
            rf'({attr}=")(?:\.\./)?{re.escape(old)}',
            rf'\1{new}',
            html,
        )

    # assets/* (including assets/fonts/fonts.css, assets/visuals/*, assets/icons/*)
    # Both same-dir "assets/..." and parent-dir "../assets/..."
    html = re.sub(
        r'(href|src|srcset)="(?:\.\./)?assets/',
        r'\1="/assets/',
        html,
    )

    # Specific root files — handle both "x" and "../x", preserve query strings
    root_files = [
        "favicon.ico", "favicon-32.png", "favicon-192.png", "favicon-512.png",
        "apple-touch-icon.png", "og-image.png",
        "logo-blanc.png", "logo-noir.png",
    ]
    for f in root_files:
        # match: (href|src)="(../)?favicon.ico?v=5"   ->  /favicon.ico?v=5
        html = re.sub(
            rf'(href|src)="(?:\.\./)?{re.escape(f)}(\?[^"]*)?"',
            rf'\1="/{f}\2"',
            html,
        )

    return html


def rewrite_internal_links(html: str) -> str:
    """Rewrite hrefs that point to old HTML files (root or insights/).

    Handles:
      href="index-fr.html"                  -> href="/fr/"
      href="../index-fr.html"               -> href="/fr/"
      href="../index-fr.html#insights"      -> href="/fr/#insights"
      href="contact.html"                   -> href="/fr/contact/"
      href="ai-act-2026.html"               -> href="/fr/insights/ai-act-2026/"  (sibling in insights/)
      href="../contact.html"                -> href="/fr/contact/"
      href="insights/ai-act-2026.html"      -> href="/fr/insights/ai-act-2026/"
      Absolute URLs (https://laetitiaperson.github.io/hymeria-site/<old>) -> BASE + new_path
    """

    # 1. Absolute URLs in meta/canonical/alternate/JSON-LD
    for old, new in OLD_TO_NEW_PATH.items():
        old_abs = BASE + old
        new_abs = BASE + new
        html = html.replace(old_abs, new_abs)

    # The bare BASE + "/" usages in JSON-LD (organization root) stay as-is (BASE root).

    # 2. Root-relative HREFs (rare today, but handle): href="/contact.html"  ->  href="/fr/contact/"
    for old, new in OLD_TO_NEW_PATH.items():
        html = re.sub(
            rf'(href|action)="{re.escape(old)}((?:#|\?)[^"]*)?"',
            rf'\1="{new}\2"',
            html,
        )

    # 3. Same-dir / parent-dir HREFs to *root-level* old files
    #    href="contact.html"       -> /fr/contact/
    #    href="../contact.html"    -> /fr/contact/
    #    href="contact.html#x"     -> /fr/contact/#x
    root_file_to_new = {
        "index-fr.html":                       NEW_URL["home-fr"],
        "index-en.html":                       NEW_URL["home-en"],
        "contact.html":                        NEW_URL["contact-fr"],
        "contact-en.html":                     NEW_URL["contact-en"],
        "mentions-legales.html":               NEW_URL["legal-notice-fr"],
        "mentions-legales-en.html":            NEW_URL["legal-notice-en"],
        "politique-confidentialite.html":      NEW_URL["privacy-fr"],
        "politique-confidentialite-en.html":   NEW_URL["privacy-en"],
        "cgu.html":                            NEW_URL["terms-fr"],
        "cgu-en.html":                         NEW_URL["terms-en"],
    }
    for old, new in root_file_to_new.items():
        html = re.sub(
            rf'(href|action)="(?:\.\./)?{re.escape(old)}((?:#|\?)[^"]*)?"',
            rf'\1="{new}\2"',
            html,
        )

    # 4. insights/* references — three forms:
    #    "insights/x.html"  (from root index files)
    #    "../insights/x.html"  (no current users but cover it)
    #    "x.html"  (sibling within insights/ directory itself — only the 6 specific filenames)
    insights_file_to_new = {
        "ai-act-2026.html":                    NEW_URL["insight-ai-act-fr"],
        "ai-act-2026-en.html":                 NEW_URL["insight-ai-act-en"],
        "consulting-traditionnel-ia.html":     NEW_URL["insight-trad-vs-ai-fr"],
        "traditional-consulting-vs-ai.html":   NEW_URL["insight-trad-vs-ai-en"],
        "exploiter-ia-sans-consultant.html":   NEW_URL["insight-leveraging-fr"],
        "leveraging-ai-without-consultants.html": NEW_URL["insight-leveraging-en"],
    }
    for old, new in insights_file_to_new.items():
        # insights/x.html or ../insights/x.html
        html = re.sub(
            rf'(href)="(?:\.\./)?insights/{re.escape(old)}((?:#|\?)[^"]*)?"',
            rf'\1="{new}\2"',
            html,
        )
        # bare sibling "x.html" (only valid match in insights pages — we run this on every page
        # but the regex is anchored to start of attribute value so it only matches the bare form)
        html = re.sub(
            rf'(href)="{re.escape(old)}((?:#|\?)[^"]*)?"',
            rf'\1="{new}\2"',
            html,
        )

    return html


def fix_lang_switcher(html: str, pair: str, lang: str) -> str:
    """Replace lang-switcher hrefs with the correct equivalent-page targets.

    The pages all use the same markup pattern:
        <a href="X" [class="active"]?>FR</a> <span class="lang-sep">|</span> <a href="Y" [class="active"]?>EN</a>
    After step 3 above, X and Y will already have been mapped to *something* — but
    not necessarily the equivalent page (e.g. contact.html only links FR<->FR home from
    most insights pages). We do a hard reset on the lang-switcher block using the pair_key
    to ensure correctness.
    """
    fr_url = PAIR_TO_NEW[(pair, "fr")]
    en_url = PAIR_TO_NEW[(pair, "en")]

    fr_class = ' class="active"' if lang == "fr" else ""
    en_class = ' class="active"' if lang == "en" else ""

    # Match the FR/EN switch including the separator. Use a permissive regex.
    pattern = re.compile(
        r'<a href="[^"]*"(?:\s+class="active")?>FR</a>'
        r'(<span class="lang-sep">\|</span>)'
        r'<a href="[^"]*"(?:\s+class="active")?>EN</a>',
        re.IGNORECASE,
    )

    replacement = (
        f'<a href="{fr_url}"{fr_class}>FR</a>'
        r'\1'
        f'<a href="{en_url}"{en_class}>EN</a>'
    )
    new_html, n = pattern.subn(replacement, html)
    if n == 0:
        print(f"  WARN: no lang switcher found")
    elif n > 1:
        print(f"  INFO: replaced {n} lang switchers")
    return new_html


def transform_html(html: str, pair: str, lang: str) -> str:
    html = absolutize_assets(html)
    html = rewrite_internal_links(html)
    html = fix_lang_switcher(html, pair, lang)
    return html


def main() -> int:
    if not (REPO / "index-fr.html").exists():
        print("ERROR: not in repo root or already migrated", file=sys.stderr)
        return 1

    for src, dst, lang, pair in PAGES:
        src_path = REPO / src
        dst_path = REPO / dst
        if not src_path.exists():
            print(f"SKIP {src} (not found)")
            continue
        print(f"-> {src}  =>  {dst}")
        html = src_path.read_text(encoding="utf-8")
        new_html = transform_html(html, pair=pair, lang=lang)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        dst_path.write_text(new_html, encoding="utf-8")

    print("\nDone. Old files still in place; delete them in a follow-up step.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
