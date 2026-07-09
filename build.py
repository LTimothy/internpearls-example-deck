#!/usr/bin/env python3
"""
Build every spec in specs/ into decks/ and write manifest.json.

manifest.json is the single file the Intern Pearls Deck Tools add-on fetches to
decide what to sync: for each deck it lists the Anki deck name, the .apkg path,
a version hash of the spec (so only changed decks re-import), and a card count.

Run this after editing a spec, then commit the changed .apkg and manifest.json.

Requires genanki (pip3 install genanki). Nothing else.
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILDER = os.path.join(HERE, "tools", "build_deck.py")
_CLOZE_RE = re.compile(r"\{\{c(\d+)::")


def card_count(spec):
    """Anki card count, not note count: a cloze note with c1/c2/c3 is three cards."""
    blocks = spec.get("subdecks") or [{"notes": spec.get("notes", [])}]
    total = 0
    for sd in blocks:
        for n in sd["notes"]:
            if n.get("type") == "cloze":
                total += len(set(_CLOZE_RE.findall(n.get("text", "")))) or 1
            else:
                total += 1
    return total


def main():
    os.makedirs(os.path.join(HERE, "decks"), exist_ok=True)
    decks = []
    for spec_path in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        with open(spec_path, encoding="utf8") as fh:
            spec = json.load(fh)
        # cwd=HERE so a spec's relative "output" resolves against the repo root.
        r = subprocess.run([sys.executable, BUILDER, spec_path],
                           capture_output=True, text=True, cwd=HERE)
        if r.returncode != 0:
            sys.exit(f"FAIL building {spec_path}\n{r.stdout}{r.stderr}")
        version = hashlib.sha256(open(spec_path, "rb").read()).hexdigest()[:8]
        cards = card_count(spec)
        decks.append({
            "name": spec["deck_name"],
            "apkg": spec["output"],
            "spec": os.path.join("specs", os.path.basename(spec_path)),
            "version": version,
            "cards": cards,
        })
        print(f"built  {spec['deck_name']}  [{version}, {cards} cards]")
    manifest = {"schema": 1, "decks": decks, "front_aliases": {}}
    with open(os.path.join(HERE, "manifest.json"), "w", encoding="utf8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    print(f"wrote manifest.json ({len(decks)} decks)")


if __name__ == "__main__":
    main()
