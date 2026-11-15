"""Try every command the game offers, at every kind of location.

    python tools/commands.py cargo.py

For each location type it lists the commands the turn screen advertises and the
ones the prompt accepts, then plays each accepted command (long and short form)
with harmless answers to whatever it asks next.  Reported: commands advertised
but refused, commands accepted but not advertised, "Invalid" answers to the
command itself, crashes, and commands that never return to the turn prompt.
"""
import os
import re
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from headless import load, new_game, quiet  # noqa: E402

# what to answer after a command, so it finishes without changing much
FOLLOW_UP = ["back", "", "back", "", "no", "", "back", ""]


def advertised(text):
    """Commands named in the 'Commands:' line of the turn screen, as (long, short)."""
    line = " ".join(re.findall(r"Commands:([^\n]*?)(?:\.\.\.|\n|$)", re.sub(r"[│║|]", " ", text)))
    return re.findall(r"([a-z]+)/([a-z]+)", line)


def accepted(game):
    asked = {}

    def spy(prompt, options, custom=None):
        asked.setdefault("options", list(options))
        return None

    original = game.validate_input
    game.validate_input = spy
    with quiet():
        game.play_turn()
    game.validate_input = original
    return asked.get("options", [])


def try_command(cargo, kind, command, then=()):
    game, io = new_game(cargo)
    place(game, kind)
    game.ship.money = 200000              # enough to say yes to things
    io.feed([command] + list(then) + FOLLOW_UP)
    prompts = []
    original = game.validate_input

    def spy(prompt, options, custom=None, _orig=original):
        prompts.append((custom or prompt, list(options)))
        return _orig(prompt, options, custom)
    game.validate_input = spy
    io.strict = False
    before = len(io.asked)
    try:
        with quiet() as buf:
            game.play_turn()
        out = buf.getvalue()
    except SystemExit:
        return "exits the game", ""
    except Exception:
        return "CRASH " + traceback.format_exc().strip().splitlines()[-1], ""
    first = out.split("Choose action", 2)
    # the answer to the command itself comes right after the first prompt
    after_first = first[1] if len(first) > 1 else out
    if re.search(r"Invalid (input|action)", after_first[:400]):
        return "refused", out
    if len(io.asked) - before > len([command] + list(then) + FOLLOW_UP):
        return "never returns", out
    try_command.prompts = prompts
    return "ok", out


def place(game, kind):
    # the story's scenes (a science mission at an outpost, say) would answer the command
    # before the turn prompt does; this audit is about commands, so they stay quiet
    game.story.tick = lambda: None
    for group in getattr(game, "hidden_locations", {}).values():
        for loc in group:
            if loc not in game.locations:
                game.locations.append(loc)
    for chapter in getattr(game, "chapter_locations", {}).values():
        for group in chapter.values():
            for loc in group:
                if loc not in game.locations:
                    game.locations.append(loc)
    for loc in game.locations:
        if loc.location_type == kind:
            game.current_location = loc
            if loc.name not in game.known_locations:
                game.known_locations.append(loc.name)
            return loc
    raise SystemExit("no location of type %s" % kind)


def main(argv):
    cargo = load(argv[1] if len(argv) > 1 else "cargo.py")
    kinds = []
    game, _ = new_game(cargo)
    place(game, "Planet")
    for group in game.hidden_locations.values():
        kinds.extend(loc.location_type for loc in group)
    for chapter in game.chapter_locations.values():
        for group in chapter.values():
            kinds.extend(loc.location_type for loc in group)
    kinds = ["Planet"] + sorted(set(kinds))
    problems = 0
    for kind in kinds:
        game, io = new_game(cargo)
        place(game, kind)
        with quiet() as buf:
            game.display_turn_info()
        shown = advertised(buf.getvalue())
        taken = accepted(game)
        refused = ["%s/%s" % pair for pair in shown if pair[0] not in taken and pair[1] not in taken]
        hidden = sorted(o for o in taken if len(o) > 2 and o not in [p[0] for p in shown])
        results = []
        for option in taken:
            verdict, _ = try_command(cargo, kind, option)
            if verdict != "ok":
                results.append("%s: %s" % (option, verdict))
                continue
            if option in ("quit", "q", "resign", "rs", "load", "ld") or len(option) <= 2:
                continue
            # one level down: every answer the command's first question accepts
            asked = getattr(try_command, "prompts", [])
            if len(asked) > 1 and len(asked[1][1]) <= 30:
                for sub in asked[1][1]:
                    verdict, _ = try_command(cargo, kind, option, [sub])
                    if verdict.startswith("CRASH") or verdict == "never returns":
                        results.append("%s > %s: %s" % (option, sub, verdict))
        print("%s" % kind)
        print("  advertised but refused: %s" % (", ".join(refused) or "-"))
        print("  accepted, not advertised: %s" % (", ".join(hidden) or "-"))
        print("  problems: %s" % ("; ".join(results) or "-"))
        problems += len(refused) + len(results)
    print("TOTAL PROBLEMS: %d" % problems)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
