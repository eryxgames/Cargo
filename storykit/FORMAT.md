# storykit format, version 1

A game's story is one JSON file (plus the files it includes). A saga file ties
several games together. Nothing in the format is specific to Cargo: a game
declares its own stats, sets, places and characters, and the tools check
everything against those declarations.

## Story file

```json
{
  "format": "storykit", "version": 1,
  "game": {"id": "cargo1", "title": "CARGO", "part": 1},
  "include": ["cargo1/main.json"],
  "stats":  {"money": {"about": "credits on hand"}, "controlled_locations": {"produced": false}},
  "sets":   {"researched": {"about": "research unlocked", "members": ["telemetry", "xenoeconomy"]}},
  "effects": {"code": {"about": "game code the tools cannot read"}},
  "flags":  {"pirate_threat": {"set_by_game": ["a battle against pirates"]},
             "heard_the_warning": {"carries_to": ["cargo2"]}},
  "places": {"Planet": {"kind": "location type"}, "port": {"kind": "venue"}},
  "characters": {"ancient_scholar": {"name": "Ancient Scholar", "kind": "alien", "generated": true}},
  "arcs":   {"main": {"title": "Main story", "order": 0}},
  "nodes":  {"ch1": {"...": "..."}}
}
```

- `stats` are the numbers the game can report. A condition on a stat means
  "at least". `"produced": false` marks a stat the game never raises, so the
  validator knows that anything needing it cannot happen.
- `sets` are named collections (research, items, unlocked location types).
  `members` lists what can exist; without it, anything goes.
- `flags` are story switches. `set_by_game` says the game's code sets it (and how);
  `carries_to` says it travels to later parts in the captain's record.
- `include` merges more files of the same format (drafts, a new arc, translations
  of nothing but text). A name may be defined only once across them.
- `amend` (in an included file) changes things defined in another file without
  touching it: `{"nodes": {"ch1": {"title": "Deadhead", "text": "..."}}}`. It works
  on `nodes`, `characters`, `flags`, `places` and `arcs`. Fields are replaced
  whole; the replaced values are kept under `amended` so the map can show them.
  Use it to rewrite text the game already has, or to repair a condition. A
  repaired `requires` is left out of the replay's fidelity check, because the
  game will disagree until it reads the file.

## Nodes

| Field | Meaning |
| --- | --- |
| `kind` | `chapter`, `milestone`, `ending`, `quest`, `event`, `encounter`, `stage` (of a chain), `unlock`, `beat`; `intro` (the first scene of a new game: the first whose `requires` holds), `epilogue` (a line shown after any ending when its `requires` holds), `rumour` (a line overheard in a cantina) |
| `arc` | lane on the map |
| `title`, `text` | text is a string or a list of lines; `{placeholders}` are filled when shown (see Names) |
| `variants` | `[{"requires": {...}, "text": "..."}]` or `[{"when": "alternate", "text": "..."}]`: other text for other circumstances |
| `requires` | condition (below); for a chapter, a milestone or a stage it is checked once its parent or predecessor allows |
| `effects` | effects (below) when it happens |
| `choices` | `[{"id", "say", "requires", "effects", "next"}]` |
| `next` | node ids that follow; with `"choose": true` the player picks one, and the sides exclude each other |
| `in` | parent (a milestone's chapter) |
| `start` | `true` on the node where the story begins |
| `act` | the act a node belongs to (chapters: their number; endings: the last act) |
| `who`, `as` | characters present, and in what role ("future self") |
| `where` | a place |
| `chance` | probability per turn once `requires` holds |
| `repeat` | `true`, or `{"cooldown": turns}`; default: happens once |
| `promises`, `pays` | saga promises this node makes or pays off |
| `status` | `draft` (written, not in the game yet), `unused` (in the game's data, nothing starts it); default live |
| `handled_by` | the game code that runs this node (a runtime that plays the story leaves it to the game) |
| `sound` | a sound cue name; played if the game has a sound kit |
| `source`, `notes` | where an imported node came from; free notes |

## Conditions

An object is "all of these". Keys:

| Key | Holds when |
| --- | --- |
| any declared stat | the stat is at least the value; `{"min": a, "max": b}` for a range |
| `flag`, `not_flag` | the flag(s) are on / off |
| `done`, `done_any`, `not_done` | the node(s) have happened |
| `since` | `{"node": turns}`: that node happened at least so many turns ago (spaces scenes out) |
| `act_min`, `act_max`, `turn_min`, `turn_max` | the act or turn is in range |
| `at`, `at_type` | the player is at this place, or a place of this type |
| `has` | `{"researched": ["telemetry"]}`: the set holds these members |
| `player_origin` | `{"game": "cargo2", "ending": "trade"}`: the player is playing as a captain from that record; `{}` any record |
| `venue` | the player is visiting this place inside a location (`port`, `cantina`), declared as a place of kind `venue` |
| `chapter` | the player is in this chapter now (its id, or one of a list); a finished chapter still counts until the next one starts |
| `visiting_captain` | `{"game": "cargo2", "ending": "trade", "flag": "x", "same_name": true}`: a captain record from that part has been imported; `same_name` true when it carries the current captain's name, false when another |
| `all`, `any`, `not` | combine conditions |
| `code` | opaque game code; the tools report it and cannot judge it |

## Effects

Any declared stat adds the value (`"money": -1500`). `set` and `clear` take flags,
`give` adds members to sets (`{"items": ["navcomp"]}`), `start` starts nodes,
`spawn` brings in a character, `reveal` puts places on the map (a place may say
how to build it under `made`), `code` names game code.

## How a game plays the nodes

A runtime (Cargo 1 has one inside `cargo.py`) looks once per turn and place. A node
plays when its `requires` hold, its `chance` is rolled, and it is not done (or it
`repeat`s and its cooldown is over). A node another node leads to through `next`
plays on a later turn than that node; a node reached through a choice's `next` plays
at once, and only after that choice. At most two scenes play at one moment; the rest
wait. A `{"code": ...}` condition never holds in a runtime: write the story in the
game's declared stats instead.

## Names

A character is named in one place: its story file, or the saga file if it lives in
more than one part (a story file says `"saga": "saga.json"` to take names from it,
and may not repeat them). Characters have `name` and may have `short`, `full` and
`title`. Texts say `{pirate_captain}` or `{pirate_captain.short}`, so renaming a
character renames it everywhere. The validator warns when a text writes out a name
that has a `short`, and, in a story that lists its `placeholders` (the game values
it can fill, like `money` or `visitor.name`), reports any other placeholder.

## Saga file

```json
{
  "format": "storykit-saga", "version": 1,
  "parts": [{"game": "cargo1", "file": "cargo1.story.json"}, {"game": "cargo3", "status": "planned"}],
  "characters": {"captain": {"timeline": [{"game": "cargo1", "as": "the player"}]}},
  "promises": {"the_warning": {"about": "...", "pay_by": "cargo3"}}
}
```

Parts are in story order. `"open": true` marks a part still being written:
promises it owes and characters it should use are reported as pending, not as
warnings. A character's `timeline` says in which parts they appear
and as what; the validator checks that the story files agree. Every promise a node
makes must be declared here and paid (`pays`) in the same or a later part; a promise
due in a part not written yet is reported as pending. A flag whose `carries_to` names a
later part should be read there through `player_origin` (the record that came in); the
validator reports one that is not (pending while that part is open).

## Traces (for replay)

One JSON object per line, one line per turn, written while the game is played:

```json
{"turn": 12, "act": 2, "chapter": "ch2a", "place": "Delta", "place_type": "Planet",
 "stats": {"money": 23000}, "sets": {"researched": []}, "flags": [], "done": ["ch1"],
 "visitors": [], "style": "trade", "verdicts": {"ch2a.establish_route": false}}
```

`verdicts` (optional) is the game's own answer for nodes it knows; replay compares
them with the story file to prove an import or a hand translation right.
