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
GUIDS = os.path.join(HERE, "guids.json")   # committed GUID baseline, see lint below
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


def spec_guids(specs):
    """{deck_name: {guid: identity key}} for every note, exactly as the builder
    derives them (id_seed + note_key)."""
    sys.path.insert(0, os.path.dirname(BUILDER))
    import genanki
    from build_deck import note_key
    out = {}
    for spec in specs:
        seed = spec.get("id_seed", spec["deck_name"])
        per = out.setdefault(spec["deck_name"], {})
        blocks = spec.get("subdecks") or [{"notes": spec.get("notes", [])}]
        for sd in blocks:
            for n in sd["notes"]:
                key = note_key(n)
                per[genanki.guid_for(seed, key)] = key
    return out


def lint_guid_stability(current, baseline):
    """Fail the build if any GUID we've ever shipped would disappear.

    A learner's review history survives a sync only while the card's GUID stays what
    it was when they imported it. A GUID vanishes when a note's identity key changes —
    rewording a front (or an image card's answer) without freezing the old identity
    via an explicit "id". guids.json is the committed record of every GUID ever built;
    a build that would drop one stops here with the fix spelled out. Deliberately
    deleting a card means deleting its guids.json entry in the same commit. New GUIDs
    (new cards) are always fine; guids.json is rewritten after a clean build.
    """
    problems = []
    for deck, old in (baseline or {}).items():
        new = current.get(deck, {})
        for guid, key in old.items():
            if guid not in new:
                problems.append(f'  {deck}:\n    "{key[:90]}"')
    if problems:
        sys.exit(
            "These cards' GUIDs would change or vanish, which silently disconnects "
            "every learner's review history from them:\n" + "\n".join(problems) +
            '\n\nIf you reworded a front (or an image card\'s answer): add '
            '"id": "<the old front text>" to that note in the spec, which keeps its '
            "GUID.\nIf you deleted the card on purpose: remove its entry from "
            "guids.json in the same commit.")


def main():
    os.makedirs(os.path.join(HERE, "decks"), exist_ok=True)
    spec_paths = sorted(glob.glob(os.path.join(HERE, "specs", "*.json")))
    specs = {p: json.load(open(p, encoding="utf8")) for p in spec_paths}
    current_guids = spec_guids(specs.values())
    baseline = {}
    if os.path.exists(GUIDS):
        with open(GUIDS, encoding="utf8") as fh:
            baseline = json.load(fh)
    lint_guid_stability(current_guids, baseline)
    decks = []
    for spec_path in spec_paths:
        spec = specs[spec_path]
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
    # front_aliases maps a card's current front text to its previous wording, so the
    # add-on can keep a learner's history when a front is reworded. Optional: create
    # aliases.json ({"new front": "old front"}) next to this script if you reword one.
    aliases_path = os.path.join(HERE, "aliases.json")
    aliases = {}
    if os.path.exists(aliases_path):
        with open(aliases_path, encoding="utf8") as fh:
            aliases = json.load(fh)
    manifest = {"schema": 1, "decks": decks, "front_aliases": aliases}
    with open(os.path.join(HERE, "manifest.json"), "w", encoding="utf8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    # Only reached after every deck built and the stability lint passed, so a failed
    # build can never fold not-yet-shipped GUIDs into the baseline.
    with open(GUIDS, "w", encoding="utf8") as fh:
        json.dump(current_guids, fh, ensure_ascii=False, indent=2, sort_keys=True)
    total = sum(len(v) for v in current_guids.values())
    print(f"wrote manifest.json ({len(decks)} decks) and guids.json ({total} GUIDs)")


if __name__ == "__main__":
    main()
