#!/usr/bin/env python3
"""
Build an Anki .apkg deck from a JSON deck spec.

Why this exists: the genanki boilerplate (note types, cloze support, stable
IDs, media embedding) is fiddly and easy to get subtly wrong. Bundling it here
means the card *content and structure* is the only thing you have to think
about — you write a spec, this turns it into a deck that imports cleanly with
images intact.

Usage:
    python3 build_deck.py <spec.json>
    python3 build_deck.py <spec.json> --print   # validate + summarize, don't write

Spec schema (see references/deck-spec.md for the annotated version):
{
  "deck_name": "Regional Anesthesia::LE Blocks (Learn)",   # "::" makes subdecks
  "output": "/abs/path/deck.apkg",
  "media_dir": "/abs/path/to/images",     # optional; where image files live
  "id_seed": "le-blocks-learn",           # optional; stable IDs so re-import UPDATES
  "subdecks": [                           # OR a flat top-level "notes": [...]
    {
      "name": "1. The Big Picture",
      "notes": [
        {"type": "basic", "front": "...", "back": "...", "why": "...", "tag": "..."},
        {"type": "cloze", "text": "The {{c1::lumbar}} plexus ...", "why": "..."},
        {"type": "image", "image": "femoral.jpg", "prompt": "Which block?",
         "answer": "Femoral block", "why": "..."}
      ]
    }
  ]
}

Note types:
  basic  -> front/back Q&A. Optional: why (green sidebar on the back),
            tag (small header on the front), image (shown on the back — good for
            "name the coverage" answers or clinical vignettes), dosing (a labeled
            reference block on the back — e.g. a drug dose + source), notes (a
            dashed "Notes" box; leave empty in the spec so the learner fills it
            in Anki as personal annotations).
  cloze  -> text with {{c1::...}} deletions. Optional: why, image, dosing, notes.
  image  -> image on the FRONT, learner names/explains it. Fields: image,
            answer, optional prompt (defaults to a generic recognition question),
            optional why, notes.

Every note also accepts an optional `id`: a stable string that fixes the note's
GUID so edits UPDATE the card in place. Without it, the GUID is derived from the
primary prompt (front / cloze text / image+answer), so editing the *answer*,
why, dosing, or notes updates in place, but rewording the *prompt* makes a new
card — set an explicit `id` on a live card if you need to reword its prompt.
"""
import sys, os, json, hashlib, re

try:
    import genanki
except ImportError:
    sys.exit("genanki not installed. Run:  pip3 install genanki")

CSS = """
.card { font-family: -apple-system, Helvetica, Arial, sans-serif; font-size: 19px;
        color: #1f2d27; background: #fff; text-align: center; padding: 16px; line-height: 1.45; }
.q { max-width: 620px; margin: 4px auto; }
/* Answer text: high-contrast in both themes (near-black on light, white on dark) —
   avoids the muddy green that's hard to read in bright light. */
.a { font-size: 21px; font-weight: 700; color: #111827; margin: 6px auto; max-width: 620px; }
.why { text-align: left; max-width: 600px; margin: 10px auto; font-size: 16px; color: #555;
       border-left: 3px solid #2e6b3e; padding-left: 10px; }
/* Dosing: a distinct reference block (drug dose + source). */
.dosing { text-align: left; max-width: 600px; margin: 10px auto; font-size: 15px; color: #334155;
          background: #eef2f7; border-radius: 6px; padding: 8px 11px; }
.dosing .lbl { font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: #64748b; display: block; margin-bottom: 3px; }
.dosing .src { color: #94a3b8; font-size: 12px; }
/* Notes: user's own space (we leave it empty; the learner fills it in Anki). */
.notes { text-align: left; max-width: 600px; margin: 10px auto; font-size: 15px; color: #6b7280;
         border: 1px dashed #cbd5e1; border-radius: 6px; padding: 8px 11px; }
.notes .lbl { font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: #94a3b8; display: block; margin-bottom: 3px; }
.tag { font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: #7a9a84; margin-bottom: 8px; }
img { max-height: 320px; max-width: 90%; margin: 10px auto; display: block; }
/* Cloze deletions in Anki's familiar blue (bold), readable on white. */
.cloze { font-weight: 700; color: #2563eb; }
hr#answer { border: none; border-top: 1px solid #cfe0d4; margin: 12px 0; }

/* Night mode: dark card, light body text, white basic answers, lighter-blue cloze. */
.nightMode.card, .nightMode .card { background: #2b2b2b; color: #e6e6e6; }
.nightMode .a { color: #ffffff; }
.nightMode .cloze { color: #7fb3ff; }
.nightMode .why { color: #c2c2c2; }
.nightMode .dosing { background: #37414f; color: #dbe4ee; }
.nightMode .notes { border-color: #4a4a4a; color: #b8b8b8; }
.nightMode hr#answer { border-top-color: #4a4a4a; }
"""

def stable_id(seed):
    """Deterministic 31-bit id from a string, so re-importing updates in place."""
    return int(hashlib.md5(seed.encode("utf-8")).hexdigest()[:8], 16) % (1 << 31)

def build_models(seed):
    basic = genanki.Model(
        stable_id(seed + "::basic"), "Study Deck - Basic",
        fields=[{"name": "Front"}, {"name": "Back"}, {"name": "Why"},
                {"name": "Image"}, {"name": "Tag"}, {"name": "Dosing"}, {"name": "Notes"}],
        templates=[{
            "name": "c",
            "qfmt": '{{#Tag}}<div class="tag">{{Tag}}</div>{{/Tag}}<div class="q">{{Front}}</div>',
            "afmt": '{{FrontSide}}<hr id="answer"><div class="a">{{Back}}</div>'
                    '{{#Why}}<div class="why">{{Why}}</div>{{/Why}}'
                    '{{#Image}}{{Image}}{{/Image}}'
                    '{{#Dosing}}<div class="dosing"><span class="lbl">Dosing</span>{{Dosing}}</div>{{/Dosing}}'
                    '{{#Notes}}<div class="notes"><span class="lbl">Notes</span>{{Notes}}</div>{{/Notes}}',
        }], css=CSS)
    image = genanki.Model(
        stable_id(seed + "::image"), "Study Deck - Image ID",
        fields=[{"name": "Image"}, {"name": "Prompt"}, {"name": "Answer"},
                {"name": "Why"}, {"name": "Notes"}],
        templates=[{
            "name": "c",
            "qfmt": '{{Image}}<div class="q">{{Prompt}}</div>',
            "afmt": '{{FrontSide}}<hr id="answer"><div class="a">{{Answer}}</div>'
                    '{{#Why}}<div class="why">{{Why}}</div>{{/Why}}'
                    '{{#Notes}}<div class="notes"><span class="lbl">Notes</span>{{Notes}}</div>{{/Notes}}',
        }], css=CSS)
    cloze = genanki.Model(
        stable_id(seed + "::cloze"), "Study Deck - Cloze",
        fields=[{"name": "Text"}, {"name": "Why"}, {"name": "Image"},
                {"name": "Dosing"}, {"name": "Notes"}],
        templates=[{
            "name": "c", "qfmt": "{{cloze:Text}}",
            "afmt": '{{cloze:Text}}{{#Why}}<div class="why">{{Why}}</div>{{/Why}}'
                    '{{#Image}}{{Image}}{{/Image}}'
                    '{{#Dosing}}<div class="dosing"><span class="lbl">Dosing</span>{{Dosing}}</div>{{/Dosing}}'
                    '{{#Notes}}<div class="notes"><span class="lbl">Notes</span>{{Notes}}</div>{{/Notes}}',
        }], model_type=genanki.Model.CLOZE, css=CSS)
    return basic, image, cloze

IMG_RE = re.compile(r'<img\s+src="([^"]+)"', re.I)

# --- HTML lint: catch bare < / > that would silently break a card ------------
# Card fields are HTML, so a literal comparator like "SpO₂ <94%" is parsed as an
# opening tag and swallows the rest of the field. Real tags (<img>, <br>, <b>,
# <sub>...) are stripped first; anything left is a bare comparator that must be
# written &lt; / &gt;. The `image` field is intentional HTML, so it's excluded.
_TAG_RE = re.compile(r'</?[a-zA-Z][^>]*>')
_LINT_FIELDS = {
    "basic": ("front", "back", "why", "tag", "dosing", "notes"),
    "cloze": ("text", "why", "dosing", "notes"),
    "image": ("prompt", "answer", "why", "notes"),
}

def lint_html(spec):
    problems = []
    def check(note, where):
        t = note.get("type", "basic")
        for f in _LINT_FIELDS.get(t, ()):
            v = note.get(f)
            if not isinstance(v, str):
                continue
            residue = _TAG_RE.sub("", v)
            if "<" in residue or ">" in residue:
                problems.append(f'{where} [{f}]: {v}')
    for i, n in enumerate(spec.get("notes", []) or []):
        check(n, f"note {i + 1}")
    for sd in spec.get("subdecks", []):
        for i, n in enumerate(sd.get("notes", [])):
            check(n, f'subdeck "{sd.get("name", "?")}" note {i + 1}')
    if problems:
        sys.exit(
            "Unescaped '<' or '>' — write &lt; / &gt; instead. A bare comparator "
            "like 'SpO₂ <94%' is parsed as a broken HTML tag and swallows the rest "
            "of the field:\n  " + "\n  ".join(problems))

def img_tag(name):
    return name if name.strip().startswith("<img") else f'<img src="{os.path.basename(name)}">'

def compose_tags(base_tag, *tag_lists):
    """Build real Anki tags, all rooted under base_tag.

    Anki tags can't contain spaces (a space starts a new tag), so each `::`
    segment has spaces collapsed to underscores. Every tag is forced under
    base_tag (e.g. "InternPearls") so the whole deck is filterable from one
    parent tag. If nothing is specified, the note still gets base_tag itself.
    """
    out = []
    for lst in tag_lists:
        if not lst:
            continue
        if isinstance(lst, str):
            lst = [lst]
        for t in lst:
            t = "::".join(seg.strip().replace(" ", "_") for seg in t.split("::") if seg.strip())
            if not t:
                continue
            if base_tag and t != base_tag and not t.startswith(base_tag + "::"):
                t = f"{base_tag}::{t}"
            if t not in out:
                out.append(t)
    if base_tag and not out:
        out = [base_tag]
    return out

def note_key(note):
    """Stable identity for a note, independent of its answer/why/dosing/notes.

    Used to derive a fixed GUID so that editing a card's back (or adding the
    Dosing/Notes fields) UPDATES the card in place instead of duplicating it.
    Prefer an explicit `id`; otherwise key on the primary prompt (front / cloze
    text / image+answer). Editing the *prompt* re-identifies the card — give a
    live card an explicit `id` if you need to reword its front without dupes.
    """
    if note.get("id"):
        return str(note["id"])
    t = note.get("type", "basic")
    if t == "cloze":
        return note.get("text", "")
    if t == "image":
        return f'{note.get("image", "")}||{note.get("answer", "")}'
    return note.get("front", "")

def make_note(note, models, tags=None, seed=""):
    basic, image, cloze = models
    tags = tags or []
    t = note.get("type", "basic")
    guid = genanki.guid_for(seed, note_key(note))
    if t == "basic":
        img = img_tag(note["image"]) if note.get("image") else ""
        return genanki.Note(model=basic, tags=tags, guid=guid,
                            fields=[note.get("front", ""), note.get("back", ""),
                                    note.get("why", ""), img, note.get("tag", ""),
                                    note.get("dosing", ""), note.get("notes", "")])
    if t == "image":
        prompt = note.get("prompt", "What is this, and what does it show?")
        return genanki.Note(model=image, tags=tags, guid=guid,
                            fields=[img_tag(note["image"]), prompt,
                                    note.get("answer", ""), note.get("why", ""),
                                    note.get("notes", "")])
    if t == "cloze":
        img = img_tag(note["image"]) if note.get("image") else ""
        return genanki.Note(model=cloze, tags=tags, guid=guid,
                            fields=[note["text"], note.get("why", ""), img,
                                    note.get("dosing", ""), note.get("notes", "")])
    raise ValueError(f"Unknown note type: {t!r} (use basic | cloze | image)")

def collect_media(spec, media_dir):
    """Find every image referenced anywhere and resolve it against media_dir."""
    names = set()
    blob = json.dumps(spec)
    for m in IMG_RE.findall(blob):
        names.add(os.path.basename(m))
    # bare-filename image fields (not wrapped in <img>)
    def scan(notes):
        for n in notes:
            for k in ("image",):
                v = n.get(k)
                if v and not v.strip().startswith("<img"):
                    names.add(os.path.basename(v))
    if spec.get("notes"): scan(spec["notes"])
    for sd in spec.get("subdecks", []): scan(sd.get("notes", []))
    paths, missing = [], []
    for n in sorted(names):
        p = os.path.join(media_dir, n) if media_dir else n
        (paths if os.path.exists(p) else missing).append(p)
    if missing:
        sys.exit("Missing media files:\n  " + "\n  ".join(missing) +
                 "\n(Check media_dir and that image filenames match.)")
    return paths

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    spec = json.load(open(args[0]))
    lint_html(spec)
    seed = spec.get("id_seed", spec["deck_name"])
    models = build_models(seed)
    media_dir = spec.get("media_dir", "")

    base_tag = spec.get("base_tag", "")      # e.g. "InternPearls" — root of every tag
    spec_tags = spec.get("tags", [])         # applied to every note in the deck

    decks, total_notes = [], 0
    def add_notes(deck, notes, subdeck_tags=None):
        nonlocal total_notes
        for n in notes:
            tags = compose_tags(base_tag, spec_tags, subdeck_tags, n.get("tags"))
            deck.add_note(make_note(n, models, tags, seed)); total_notes += 1

    if spec.get("subdecks"):
        for sd in spec["subdecks"]:
            full = f'{spec["deck_name"]}::{sd["name"]}'
            d = genanki.Deck(stable_id(full), full)
            add_notes(d, sd.get("notes", []), sd.get("tags"))
            decks.append(d)
    else:
        d = genanki.Deck(stable_id(spec["deck_name"]), spec["deck_name"])
        add_notes(d, spec.get("notes", []))
        decks.append(d)

    media = collect_media(spec, media_dir)
    print(f"deck: {spec['deck_name']}")
    print(f"subdecks: {len(decks)} | notes: {total_notes} | media: {len(media)}")

    if "--print" in sys.argv:
        print("(--print: validated, not written)")
        return
    pkg = genanki.Package(decks)
    pkg.media_files = media
    pkg.write_to_file(spec["output"])
    print(f"wrote: {spec['output']}")

if __name__ == "__main__":
    main()
