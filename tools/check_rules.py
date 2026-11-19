#!/usr/bin/env python3
"""Enforce spec rule R1 mechanically: curriculum files carry concept IDs and
ordering only -- no section/unit/chapter numbering or source identifiers.

Source identifiers are caught by a general rule rather than by name: any
all-caps acronym of four or more letters is rejected (concept vocabulary
uses only short ones such as KE, PE, SHM). JSON and ASCII are exempt because
the prompt must name those formats.

Scans every file NAME and file CONTENT under curriculum/. Exits non-zero on
any match. DENYLIST is also imported by the prompt golden-file test, so the
same patterns are asserted absent from every prompt sent to a provider.
"""
import os
import re
import sys

DENYLIST = [
    r"\d+\.\d+",
    r"[Uu]nit \d",
    r"[Cc]hapter \d",
    r"[Mm]odule \d",
    r"[Aa]ctivity",
    r"\b(?!(?:JSON|ASCII)\b)[A-Z]{4,}\b",
    r"PHY-?\d",
]
PATTERNS = [re.compile(p) for p in DENYLIST]


def scan_text(text):
    """Return the denylist patterns that match text."""
    return [p.pattern for p in PATTERNS if p.search(text)]


def scan_tree(root="curriculum"):
    problems = []
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(dirpath, name)
            for pat in scan_text(name):
                problems.append(f"{path}: filename matches /{pat}/")
            with open(path, encoding="utf-8") as f:
                for n, line in enumerate(f, 1):
                    for pat in scan_text(line):
                        problems.append(f"{path}:{n}: matches /{pat}/")
    return problems


def main():
    problems = scan_tree(sys.argv[1] if len(sys.argv) > 1 else "curriculum")
    for p in problems:
        print(p)
    if problems:
        sys.exit(f"R1 violation: {len(problems)} match(es)")
    print("check_rules: curriculum/ is clean")


if __name__ == "__main__":
    main()
