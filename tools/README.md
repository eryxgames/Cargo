# Checks for cargo.py

Nothing here is needed to play. These scripts play the game without a terminal and
are how the 1.1.0 release was verified. Standard library only.

    tools/check.sh          # everything (a few minutes)
    tools/check.sh quick    # a smaller matrix

| Script | What it does |
| --- | --- |
| `attrlint.py` | Lists `self.x` reads that the class never defines (methods pasted into the wrong class). |
| `story_probe.py` | Forces the statistics each chapter asks for and runs the real chapter code along all four routes to the three endings. Proves the story machinery; not that the statistics can be earned. |
| `bot.py` | Plays the game through its real prompts to an ending: `bot.py cargo.py trade 1`. Goals: `trade`, `combat`, `discovery` (via chapter 2a), `discovery2` (via 2b). `--save-every=N` saves and reloads every N turns, `--trace=FILE` records each turn for `storykit/replay.py`. Proves the endings can be earned. |
| `infuzz.py` | Random commands at a fixed terminal width; reports crashes and lines wider than the screen: `infuzz.py cargo.py 36 1500 1`. |
| `roundtrip.py` | Plays, saves, loads, compares the two worlds, keeps playing the loaded one. |
| `test_files.py` | Damaged and hostile save and captain files must be refused cleanly. |
| `headless.py` | Shared: loads `cargo.py` as a module with `input()` scripted. |
| `cargo_story.py` | Reads the story out of `cargo.py` into `story/cargo1.story.json` (`import`), or checks the file still matches the code (`check`). The hand-written arcs in `story/cargo1/*.json` are included, not imported: edit them directly. Also `snapshot()`, the trace line `bot.py --trace=FILE` writes each turn. |
| `cargo2_story.py` | Reads Cargo 2's `data/*.yml` into `story/cargo2.story.json` (needs PyYAML). |

The bot reads the game's state to decide, like a player reading the screen, but it only
acts by answering prompts. It sometimes goes bankrupt early on Normal difficulty; that is
the game's lose condition and is reported as such.
