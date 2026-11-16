"""Make a captain record by hand, to test crossings before the other parts exist.

    python tools/make_captain.py --game cargo2 --name "Kayo Wu" --rank Commodore \
        --ending trade --flag heard_the_warning --turns 240 [--out FILE] [--folder]

Prints the record's CARGO: code.  --out writes the .captain file there; --folder
writes it into the shared records folder (~/.cargo-saga/captains, or $CARGO_SAGA_HOME), where
a new game offers to play as it and the 'captain' command can bring it in as a
visitor.  The record is checked and cleaned exactly as the game cleans records
that come from outside, so what you make here is what the game will see.
"""
import argparse
import importlib.util
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_cargo():
    spec = importlib.util.spec_from_file_location("cargo", os.path.join(ROOT, "cargo.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make(cargo, game, name, rank="", ending="", flags=(), turns=200, version="0.0.0"):
    record = {
        "format": "cargo-captain",
        "version": cargo.CAPTAIN_FORMAT,
        "id": "%s-%08X" % (game.upper().replace("CARGO", "C"), abs(hash((game, name))) % (1 << 32)),
        "name": name,
        "origin": {"game": game, "version": version},
        "rank": rank,
        "career": {"turns": turns, "money": 0, "trades": 0, "victories": 0, "passengers": 0,
                   "reputation": 0, "locations": 0, "research_points": 0},
        "research": [],
        "ship": {"attack": 0, "defense": 0, "speed": 0},
        "story": {"chapter": "", "completed": [], "ending": ending, "flags": sorted(flags), "plot_points": 0},
        "hold": {},
        "log": [{"game": game, "event": "made by hand", "turn": turns, "at": time.strftime("%Y-%m-%d")}],
    }
    record["check"] = cargo._captain_check(record)
    return cargo.clean_captain(record)


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--game", choices=["cargo1", "cargo2", "cargo3"], required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--rank", default="")
    parser.add_argument("--ending", default="", help="trade, combat, discovery, tycoon, or empty")
    parser.add_argument("--flag", action="append", default=[], help="a story flag (repeat for more)")
    parser.add_argument("--turns", type=int, default=200)
    parser.add_argument("--out", help="write the .captain file here")
    parser.add_argument("--folder", action="store_true", help="write it into the shared records folder")
    args = parser.parse_args(argv[1:])
    cargo = load_cargo()
    record = make(cargo, args.game, args.name, args.rank, args.ending, args.flag, args.turns)
    paths = [args.out] if args.out else []
    if args.folder:
        paths.append(os.path.join(cargo.captain_folder(), "%s-%s.captain" % (cargo.safe_name(args.name), args.game)))
    for path in paths:
        cargo.write_json(path, record)
        print("wrote", path)
    print(cargo.captain_to_code(record))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
