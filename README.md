# Example deck for Intern Pearls Deck Tools

A tiny, self-contained deck source you can point the [Intern Pearls Deck
Tools](https://github.com/LTimothy/internpearls-anki) Anki add-on at to see how
syncing works. It holds one small deck, **Pharmacology Basics**, of general,
widely-known drug facts, purely as a format demonstration.

> This deck is an example of the deck format, not medical advice. The facts and
> doses are illustrative, general-knowledge examples and are not a clinical
> reference. Do not use them to make treatment decisions.

## What's here

```
specs/pharmacology-basics.json   the deck content you edit
decks/Pharmacology_Basics.apkg   the built deck the add-on downloads
manifest.json                    the index the add-on reads (built)
build.py                         rebuilds the .apkg and manifest.json
tools/build_deck.py              turns one spec into an .apkg
```

`specs/` is the source you edit. `decks/` and `manifest.json` are built outputs,
committed so the add-on can download them without building anything itself.

## Point the add-on at it

The one-click way (add-on v0.18.0+): in Anki, open **Intern Pearls → Manage
decks → Configure source** and pick **Try the example deck** — it points at this
repo for you. Or configure it by hand in the same dialog:

- **GitHub repo**: `LTimothy/internpearls-example-deck` (or your fork)
- **Branch**: `main`
- **Access token**: leave blank for a public repo

Then **Sync decks**. The add-on reads `manifest.json`, downloads
`Pharmacology_Basics.apkg`, and imports it. A local folder works too: point the
source at a checkout of this repo instead of a GitHub repo.

The add-on can protect your own note fields across syncs (so re-importing a deck
never overwrites your personal annotations). That protection applies to notes
under the add-on's configured scope tag; this deck tags its notes under
`ExampleDeck`, so set the scope tag to match if you want to try that feature.

## Make your own deck from this

1. Edit `specs/pharmacology-basics.json`, or add another `specs/*.json` file. Each
   note is `basic`, `cloze`, or `image`; see the header of `tools/build_deck.py`
   for the full spec schema and every optional field.
2. Run `python3 build.py` (needs `pip3 install genanki`). It rebuilds the `.apkg`
   files and regenerates `manifest.json`.
3. Commit the changed `specs/`, `decks/`, and `manifest.json`, and push. The next
   **Sync decks** pulls only what changed, because each deck's `version` in the
   manifest is a hash of its spec.

Keeping review history across edits: the builder derives each card's identity
from its `id_seed` plus its front text, so editing a card's answer keeps its
history, while rewording a front makes a new card. If you do reword a front,
record it in an `aliases.json` next to `build.py` (`{"new front": "old front"}`);
the build folds it into the manifest and the add-on uses it to match learners'
existing cards. Don't change a deck's `deck_name` or `id_seed` once people are
studying it.

## License

Released under [CC0 1.0](LICENSE): public domain, no attribution required. Copy
it, fork it, replace the content with your own.
