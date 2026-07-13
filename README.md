# Example deck for Intern Pearls Deck Tools

A tiny, self-contained deck source you can point the [Intern Pearls Deck
Tools](https://github.com/LTimothy/internpearls-anki) Anki add-on at to see how
syncing works, or try in your browser first via the
[live demo](https://ltimothy.github.io/internpearls-anki/), which mirrors this
repo's content. It holds two small decks, **Pharmacology Basics** and **ABG
Basics**, of general, widely-known facts, purely as a format demonstration
(two decks so Manage decks, selective sync, and per-deck versioning have
something real to show).

It's also a **template**: copy it, replace the example cards with your own, and
you have a deck your whole study group can subscribe to. You can do everything
in the browser on github.com; no installs needed. See "Make and share your own
decks" below.

> This deck is an example of the deck format, not medical advice. The facts and
> doses are illustrative, general-knowledge examples and are not a clinical
> reference. Do not use them to make treatment decisions.

## What's here

```
specs/*.json                     the deck content you edit (one file per deck)
decks/*.apkg                     the built decks the add-on downloads
manifest.json                    the index the add-on reads (built)
guids.json                       every card GUID ever shipped (built; see below)
build.py                         rebuilds the .apkg, manifest.json, and guids.json
tools/build_deck.py              turns one spec into an .apkg
.github/workflows/build.yml      runs build.py for you on every change
```

`specs/` is the source you edit. `decks/`, `manifest.json`, and `guids.json`
are built outputs, committed so the add-on can download them without building
anything itself. The workflow keeps them current, so you never have to run
`build.py` yourself unless you want to (see "Building on your own computer").

## Point the add-on at this repo

The one-click way (add-on v0.18.0+): in Anki, open **Intern Pearls > Manage
decks > Configure source** and pick **Try the example deck**. It points at this
repo for you. Or configure it by hand in the same dialog:

- **GitHub repo**: `LTimothy/internpearls-example-deck` (or your own copy)
- **Branch**: `main`
- **Access token**: leave blank for a public repo

Then **Update my decks**. The add-on reads `manifest.json`, downloads the
decks, and imports them. A local folder works too: point the source at a
download of this repo instead of a GitHub repo.

## Make and share your own decks

No terminal or programming needed; every step happens on github.com.

1. **Copy this repo.** Sign in to GitHub (a free account is fine), then click
   **Use this template > Create a new repository** at the top of this page.
   Name it whatever you like and keep it Public (a private repo works too, but
   then everyone subscribing needs an access token; public is simpler).
2. **Write your cards.** In your new repo, open a file under `specs/`, click
   the pencil icon to edit, and change the notes. Each note is one card (see
   "Card format" below for the three kinds). Click **Commit changes** when done.
3. **Let it build.** Committing a spec change starts the build automatically:
   the **Actions** tab shows it running, and about a minute later the rebuilt
   deck files appear as a "Rebuild decks" commit. A red X instead means the
   build stopped to protect something, most often review history; open the
   failed run and the message names the exact card and the fix.
4. **Replacing the example decks?** When you remove the two example spec files,
   delete `guids.json` in the same commit (it's the history ledger for cards
   this repo no longer ships; the build regenerates it for your decks). Give
   your own spec its own `deck_name`, `id_seed`, and `base_tag`.
5. **Share it.** Send your group something like this:

   > Install the Intern Pearls Deck Tools add-on in Anki
   > ([download](https://github.com/LTimothy/internpearls-anki/releases/latest),
   > then Tools > Add-ons > Install from file, and restart Anki). Open
   > **Intern Pearls > Manage decks > Configure source**, pick GitHub repo, and
   > enter `YOURNAME/YOURREPO`. Then click **Update my decks**. One more step so
   > your own notes on cards survive updates: in Tools > Add-ons > Intern Pearls
   > Deck Tools > Config, set `scope_tag` to `YOURBASETAG` and `export_deck` to
   > `YOURDECKNAME`.

   That last config step matters: the add-on only protects personal annotations
   and takes its automatic pre-sync backups for cards under its configured
   `scope_tag` and `export_deck`, and those default to the Intern Pearls deck's
   values, not yours.
6. **Publish updates.** Edit the specs again, commit, and wait for the green
   check. Everyone's next **Update my decks** pulls only the decks that
   changed, keeps their review scheduling, and preserves the personal notes
   they've written on cards.

## Card format

Three kinds of notes, all illustrated in `specs/`:

```json
{"type": "basic",
 "front": "What is the normal range for arterial blood pH?",
 "back": "About 7.35 to 7.45.",
 "why": "Optional context shown in a sidebar on the back."}

{"type": "cloze",
 "text": "Normal pCO₂ is about {{c1::35-45}} mmHg.",
 "why": "Each {{c1::...}} becomes a fill-in-the-blank card."}

{"type": "image", "image": "femoral.jpg",
 "prompt": "Which block?", "answer": "Femoral block"}
```

A spec file wraps notes in a `deck_name`, an `output` path, an `id_seed`, a
`base_tag`, and optional `subdecks`; the two files in `specs/` are working
examples of all of it. The header of `tools/build_deck.py` documents every
optional field (`dosing`, `tag`, per-note `image`, and more).

## Keeping everyone's review history

Anki tracks review scheduling per card, hung on a hidden ID the builder derives
from each note. The practical rules:

- Editing a card's `back`, `why`, or `dosing`, or adding new cards, is always
  safe. History carries over.
- Rewording a card's `front` (or an image card's `answer`) changes its identity,
  so freeze it in the same edit: add `"id": "<the old front text>"` to that
  note. The build fails with exactly this instruction if you forget, so you
  can't lose anyone's history by accident.
- Deleting a card on purpose means deleting its entry from `guids.json` in the
  same commit (again, the failed build tells you).
- Never change a deck's `deck_name` or `id_seed` once people are studying it.

`aliases.json` (`{"new front": "old front"}`, folded into the manifest) exists
as a fallback for collections that predate stable ids; new renames shouldn't
need it.

## Building on your own computer (optional)

The workflow does this for you, but the build also runs anywhere Python does:

```bash
pip3 install genanki
python3 build.py
```

It rebuilds every `.apkg`, regenerates `manifest.json` and `guids.json`, and
enforces the history rules above. Commit the changed `specs/`, `decks/`,
`manifest.json`, and `guids.json` together. This is also how you'd maintain a
deck source in a plain shared folder with no GitHub at all: the add-on's
"Local folder" source reads the same files from disk.

## License

Released under [CC0 1.0](LICENSE): public domain, no attribution required. Copy
it, fork it, replace the content with your own.
