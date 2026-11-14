"""Replay recorded play against a story: when would each node happen, for each kind of player?

    python storykit/replay.py story/cargo1.story.json story/traces/*.jsonl
    python storykit/replay.py STORY TRACES... --json out.json

A trace is a JSON-lines file written while a game is played (by a person or a bot):
one snapshot per turn with stats, sets, flags, completed nodes, act, place.  The
game supplies the numbers; the story file supplies the rules.  Change a threshold
or add a draft quest, replay, and see at which turn trader, fighter and explorer
players would meet it - without playing again.

If snapshots carry "verdicts" (the game's own answer for a node's requirements),
every one is compared with the story file's: that is how an extraction is checked.
"""
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story as kit  # noqa: E402


def read_trace(path):
    lines = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                lines.append(json.loads(line))
    lines.sort(key=lambda s: (s.get("turn", 0), bool(s.get("final"))))
    return lines


def predecessors(story):
    preds = {}
    for nid, node in story["nodes"].items():
        for kind, target in kit.references(node):
            if kind in ("next", "start"):
                preds.setdefault(target, set()).add(nid)
    return preds


def replay_one(story, trace, preds):
    """First turn each node becomes available in one recorded game; plus mismatches."""
    nodes = story["nodes"]
    available = {}
    sim_done = set()
    entered = set()
    mismatches = []
    for snap in trace:
        state = kit.State.from_snapshot(snap)
        game_done = set(state.done)
        current = snap.get("chapter")
        if current:
            entered.add(current)
        entered.update(n for n in game_done if n in nodes and nodes[n].get("kind") in ("chapter", "ending"))
        state.done = game_done | sim_done
        state.flags |= {f for n in sim_done for f in kit.flags_set(nodes[n])}

        # the game's own verdicts against the file's
        for nid, verdict in (snap.get("verdicts") or {}).items():
            if verdict is None or nid not in nodes:
                continue
            ours = kit.check(nodes[nid].get("requires"), state, unknown="pass")
            if ours != verdict:
                mismatches.append({"turn": snap.get("turn"), "node": nid, "game": verdict, "story": ours})

        for _ in range(4):                 # let chains settle within a turn
            changed = False
            for nid, node in nodes.items():
                if nid in available or node.get("status") == "unused":
                    continue
                kind = node.get("kind")
                from_game = bool(node.get("source"))
                if node.get("in"):
                    if node["in"] not in entered:
                        continue
                elif kind in ("chapter", "ending") and from_game and current:
                    # the recorded game decides which path was taken, and when
                    if nid not in entered:
                        continue
                    available[nid] = snap.get("turn", 0)
                    changed = True
                    continue
                elif kind in ("chapter", "ending", "stage") and not node.get("start"):
                    if not any(p in state.done for p in preds.get(nid, ())):
                        continue
                if not kit.check(node.get("requires"), state, unknown="pass"):
                    continue
                available[nid] = snap.get("turn", 0)
                changed = True
                if kind in ("chapter", "ending"):
                    entered.add(nid)
                if not from_game or kind in ("stage", "encounter", "event", "beat", "quest"):
                    sim_done.add(nid)
                    state.done.add(nid)
                    state.flags |= kit.flags_set(node)
            if not changed:
                break
    last = trace[-1] if trace else {}
    return available, mismatches, {"turns": last.get("turn", 0), "ending": last.get("ending"),
                                   "style": last.get("style"), "seed": last.get("seed")}


def replay(story, paths):
    preds = predecessors(story)
    runs = []
    for path in paths:
        trace = read_trace(path)
        available, mismatches, info = replay_one(story, trace, preds)
        info["file"] = os.path.basename(path)
        runs.append({"info": info, "available": available, "mismatches": mismatches})
    return runs


def summarize(story, runs):
    """Per node and play style: share of games where it became available, and when."""
    styles = sorted({r["info"].get("style") or "?" for r in runs})
    out = {"styles": {}, "nodes": {}}
    for style in styles:
        mine = [r for r in runs if (r["info"].get("style") or "?") == style]
        out["styles"][style] = {
            "games": len(mine),
            "endings": [r["info"].get("ending") for r in mine],
            "turns": [r["info"].get("turns") for r in mine],
        }
        for nid, node in story["nodes"].items():
            turns = [r["available"][nid] for r in mine if nid in r["available"]]
            entry = {"share": round(len(turns) / len(mine), 2) if mine else 0}
            if turns:
                entry["median"] = statistics.median(turns)
                entry["first"] = min(turns)
                entry["last"] = max(turns)
                chance = node.get("chance")
                if chance:
                    entry["expected_wait"] = round(1 / chance, 1)
            out["nodes"].setdefault(nid, {})[style] = entry
    out["mismatches"] = [dict(m, trace=r["info"]["file"]) for r in runs for m in r["mismatches"]]
    return out


def main(argv):
    args = [a for i, a in enumerate(argv[1:], 1) if not a.startswith("--") and argv[i - 1] != "--json"]
    if len(args) < 2:
        print(__doc__)
        return 2
    story = kit.load(args[0])
    runs = replay(story, args[1:])
    summary = summarize(story, runs)
    if "--json" in argv:
        out = argv[argv.index("--json") + 1]
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(summary, handle, ensure_ascii=False, indent=1)
        print("wrote", out)
    styles = list(summary["styles"])
    print("games: " + ", ".join("%s %d (endings: %s; turns %s)" % (
        s, v["games"], ",".join(str(e) for e in v["endings"]), ",".join(str(t) for t in v["turns"]))
        for s, v in summary["styles"].items()))
    print()
    print("%-38s" % "node" + "".join("%-18s" % s for s in styles))
    rows = []
    for nid, per in summary["nodes"].items():
        meds = [per[s].get("median") for s in styles if per[s].get("median") is not None]
        rows.append((min(meds) if meds else 10 ** 9, nid, per))
    for _, nid, per in sorted(rows):
        cells = []
        for s in styles:
            e = per[s]
            if not e.get("share"):
                cells.append("-")
            else:
                cells.append("t%-4s %3d%%%s" % (int(e["median"]), int(e["share"] * 100),
                                                 " +%s" % int(e["expected_wait"]) if e.get("expected_wait") else ""))
        print("%-38s" % nid[:37] + "".join("%-18s" % c for c in cells))
    print()
    mm = summary["mismatches"]
    if mm:
        print("MISMATCHES between the file and the game (%d):" % len(mm))
        seen = set()
        for m in mm:
            if m["node"] in seen:
                continue
            seen.add(m["node"])
            print("  %s at turn %s (%s): game says %s, story file says %s" % (
                m["node"], m["turn"], m["trace"], m["game"], m["story"]))
    else:
        print("file and game agree on every recorded verdict")
    return 1 if mm else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
