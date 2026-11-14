"""Draw a story (or a whole saga) as one self-contained HTML page.

    python storykit/storymap.py story/saga.json -o story/map.html \\
        --replay cargo1=story/cargo1.replay.json

Lanes are arcs; a node sits at the turn players of each style reach it (from a
replay summary), or in its act.  Validator findings are marked on the nodes.
The page needs nothing but a browser.
"""
import datetime
import json
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story as kit       # noqa: E402
import validate           # noqa: E402

STYLE_NAMES = {"trade": "Trader", "combat": "Fighter", "discovery": "Explorer via trade",
               "discovery2": "Explorer via combat"}


PLACEHOLDER = re.compile(r"\{([a-z_][a-z0-9_]*)(?:\.([a-z_]+))?\}")


def named(value, characters):
    """Text as a reader of the map should see it: {pirate_captain} -> Hedda Mraz."""
    if isinstance(value, list):
        return [named(v, characters) for v in value]
    if not isinstance(value, str):
        return value

    def swap(match):
        info = characters.get(match.group(1))
        if info is None:
            return match.group(0)
        return str(info.get(match.group(2) or "name", match.group(0)))
    return PLACEHOLDER.sub(swap, value)


def game_payload(gid, story, reach, items, replay):
    nodes = {}
    chars = story["characters"]
    for nid, node in story["nodes"].items():
        entry = {k: v for k, v in node.items() if k not in ("source_code",)}
        entry["title"] = named(entry.get("title"), chars)
        entry["text"] = named(entry.get("text"), chars)
        if entry.get("variants"):
            entry["variants"] = [dict(v, text=named(v.get("text"), chars)) for v in entry["variants"]]
        if entry.get("choices"):
            entry["choices"] = [dict(c, say=named(c.get("say"), chars)) for c in entry["choices"]]
        entry["act_"] = kit.act_of(story, nid)
        entry["reach"] = reach.get(nid, "yes")
        entry["why"] = reach.why.get(nid, "")
        entry["refs"] = kit.references(node)
        nodes[nid] = entry
    problems = [i for i in items if i["where"].startswith(gid + ":")]
    for p in problems:
        nid = p["where"].split(":", 1)[1]
        if nid in nodes:
            nodes[nid].setdefault("problems", []).append(p)
    arcs = sorted(story["arcs"].items(), key=lambda kv: kv[1].get("order", 9))
    return {
        "id": gid,
        "title": story.get("game", {}).get("title", gid),
        "short": "Cargo %s" % story["game"]["part"] if story.get("game", {}).get("part") else gid,
        "about": story.get("about", ""),
        "arcs": [{"id": k, "title": v.get("title", k)} for k, v in arcs],
        "characters": story["characters"],
        "nodes": nodes,
        "problems": problems,
        "replay": replay,
        "styles": [{"id": s, "name": STYLE_NAMES.get(s, s), **(replay or {}).get("styles", {}).get(s, {})}
                   for s in (replay or {}).get("styles", {})],
    }


def build(path, replays):
    report = validate.Report()
    with open(path, encoding="utf-8") as handle:
        fmt = json.load(handle).get("format")
    if fmt == kit.SAGA_FORMAT:
        saga = kit.load_saga(path)
        reaches = validate.check_saga(saga, report)
        stories = saga["stories"]
    else:
        saga = None
        story = kit.load(path)
        stories = {story.get("game", {}).get("id", "story"): story}
        reaches = {g: validate.check_story(s, report) for g, s in stories.items()}

    games = []
    for gid, story in stories.items():
        replay = None
        if gid in replays:
            with open(replays[gid], encoding="utf-8") as handle:
                replay = json.load(handle)
        games.append(game_payload(gid, story, reaches[gid], report.items, replay))

    saga_data = None
    if saga:
        made, paid, crossings = {}, {}, []
        for gid, story in stories.items():
            for nid, node in story["nodes"].items():
                for p in kit.as_list(node.get("promises")):
                    made.setdefault(p, []).append([gid, nid])
                for p in kit.as_list(node.get("pays")):
                    paid.setdefault(p, []).append([gid, nid])
                found = []
                for cond in kit.node_conditions(node):
                    kit.walk_condition(cond, lambda k, v, pth: found.append(v) if k == "visiting_captain" else None)
                for v in found:
                    crossings.append({"game": gid, "node": nid, "title": node.get("title", nid),
                                      "from": v.get("game"), "status": node.get("status", "live")})
        appears = {}
        for gid, story in stories.items():
            for nid, node in story["nodes"].items():
                for who in kit.characters_of(node):
                    appears.setdefault(who, {}).setdefault(gid, []).append(nid)
        saga_data = {
            "title": saga.get("title", "Saga"),
            "about": saga.get("about", ""),
            "parts": saga.get("parts", []),
            "characters": saga.get("characters", {}),
            "appears": appears,
            "promises": saga.get("promises", {}),
            "made": made, "paid": paid,
            "crossings": crossings,
            "problems": [i for i in report.items if i["where"].startswith("saga")],
        }
    counts = {lv: report.count(lv) for lv in ("error", "warning", "note")}
    return {
        "generated": datetime.date.today().isoformat(),
        "source": os.path.basename(path),
        "games": games,
        "saga": saga_data,
        "counts": counts,
    }


def main(argv):
    args = argv[1:]
    if not args:
        print(__doc__)
        return 2
    out = "map.html"
    replays = {}
    path = None
    i = 0
    while i < len(args):
        if args[i] == "-o":
            out = args[i + 1]
            i += 2
        elif args[i] == "--replay":
            gid, file = args[i + 1].split("=", 1)
            replays[gid] = file
            i += 2
        else:
            path = args[i]
            i += 1
    data = build(path, replays)
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "map_template.html"), encoding="utf-8") as handle:
        page = handle.read()
    page = page.replace("__STORY_DATA__", blob)
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(page)
    print("wrote %s (%d KB): %s" % (out, len(page) // 1024, ", ".join(
        "%s %d nodes" % (g["id"], len(g["nodes"])) for g in data["games"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
