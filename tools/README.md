# Checks for cargo.py

Nothing here is needed to play. These scripts play the game without a terminal and
are how the releases were verified. Standard library only.

    tools/check.sh          # everything (a few minutes)
    tools/check.sh quick    # a smaller matrix

| Script | What it does |
| --- | --- |
| `attrlint.py` | Lists `self.x` reads that the class never defines (methods pasted into the wrong class). |
| `story_probe.py` | Forces the statistics each chapter asks for (the story file's, where it repairs them) and runs the real chapter code along all four routes to the three endings. Proves the story machinery; not that the statistics can be earned. |
| `scenes.py` | Plays every story scene the game plays on its own, once per choice, on a well-stocked ship: no crashes, no `{name}` left unfilled. Also checks that special cargo (`stow`/`unstow`) takes and frees hold room and that the Cargolyte and Rootstock enemies wait for the story. |
| `smoke.py` | Starts the real game as a program (`smoke.py python3 cargo.py`, or a built `cargo.exe`), answers the new-game questions and closes its input: it must show the title, autosave and exit cleanly, with UTF-8 and with cp1252 output. The release workflow runs it on the Windows build. |
| `handoff.py` | Writes `story/CARGO1-HANDOFF.md` from the built story: the promises later parts must pay, every flag a captain record carries to Cargo 2 or 3 (by arc, with what it means), and the characters whose timelines go on. `--check` fails when it is out of date. |
| `bot.py` | Plays the game through its real prompts to an ending: `bot.py cargo.py trade 1`. Goals: `trade`, `combat`, `discovery` (via chapter 2a), `discovery2` (via 2b). `--save-every=N` saves and reloads every N turns, `--trace=FILE` records each turn for `storykit/replay.py`, `--ledger` prints where money, research and plot points came from and went, by the function that changed them, and the turn each chapter opened. Fights, situations and the bounty board are answered from what the screen shows (`game.move_options`); a fighter hunts two days in three, every bot drinks in a cantina every fourth turn. Proves the endings can be earned. |
| `commands.py` | Every command each kind of location advertises must be accepted there, and every command and its first-level options must answer without crashing or getting stuck. |
| `quests.py` | Makes each kind of quest (contracts, event, cantina and unlock quests), checks it is not finished the moment it is taken, does the work, and checks the quest completes, pays and hands over its cargo or passenger. |
| `infuzz.py` | Random commands at a fixed terminal width; reports crashes and lines wider than the screen: `infuzz.py cargo.py 36 1500 1`. |
| `roundtrip.py` | Plays, saves, loads, compares the two worlds, keeps playing the loaded one. |
| `test_files.py` | Damaged and hostile save and captain files must be refused cleanly. |
| `headless.py` | Shared: loads `cargo.py` as a module with `input()` scripted. |
| `cargo_story.py` | Reads the chapters, milestones and frontier out of `cargo.py` into `story/cargo1.story.json` (`import`), or checks the file still matches the code (`check`). Everything else is written in `story/cargo1/*.json`: edit those directly. Also `snapshot()` and `story_moment()`, what `bot.py --trace=FILE` writes each turn (the runtime's verdicts and the state it judged). |
| `build_story.py` | Builds the story (with names from `story/saga.json`) into `cargo.py` between two marker lines; `--check` fails if the block is out of date; `--out FILE` writes it for `CARGO_STORY=FILE python cargo.py`. |
| `make_captain.py` | Makes a captain record by hand (`--game cargo2 --name ... --rank ... --ending ...`), to play crossings before Cargo 2 and 3 exist. `--folder` puts it where a new game offers it. |
| `cargo2_story.py` | Reads Cargo 2's `data/*.yml` into `story/cargo2.story.json` (needs PyYAML). |

The bot reads the game's state to decide, like a player reading the screen, but it only
acts by answering prompts. It sometimes goes bankrupt early on Normal difficulty; that is
the game's lose condition and is reported as such.
