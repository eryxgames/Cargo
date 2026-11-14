# storykit

Tools to write, check and see a game's story as data. Standard library only.
Nothing here is Cargo-specific: a game declares its own vocabulary in the story
file (see [FORMAT.md](FORMAT.md)) and, for replay, writes a trace while it is played.

| Tool | What it answers |
| --- | --- |
| `validate.py` | Is anything broken or wasted? Unknown names, broken links, content that can never happen, flags nobody reads, both sides of a choice required, unpaid promises, characters missing from their timeline. `--baseline` accepts known findings and fails only on new ones. |
| `replay.py` | When does each node happen for each kind of player? Replays recorded games (traces) against the story file, so a changed threshold or a new draft shows its timing at once, without playing again. With the game's own verdicts in the trace it proves the story file matches the code. |
| `storymap.py` | One HTML page: arcs as lanes, nodes at the turn each kind of player reaches them (or by act), findings marked, the saga's characters, promises and crossings. |
| `story.py` | The shared rules: loading, conditions, effects. A game can embed it to run its story from the file. |

Typical loop for Cargo 1 (from the repository root):

```sh
python tools/bot.py cargo.py trade 1 1500 --trace=story/traces/trade-1.jsonl   # record (any style)
python storykit/validate.py story/saga.json
python storykit/replay.py story/cargo1.story.json story/traces/*.jsonl --json story/cargo1.replay.json
python storykit/storymap.py story/saga.json -o story/map.html --replay cargo1=story/cargo1.replay.json
```

## Using it for another game

1. Write the vocabulary: the stats, sets, places and characters the game has.
2. Import or write the nodes. An importer reads the game's own data or objects
   (see `tools/cargo_story.py` for code, `tools/cargo2_story.py` for YAML).
3. Make the game write a trace line per turn (a `snapshot()` of its state).
   A bot that plays the game, or recordings of people playing, both work.
4. Run the three tools. For an RPG the "styles" might be warrior, thief and
   pacifist runs; for a strategy game, rush and economy openings.
