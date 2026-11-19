"""Put Cargo 1's story into cargo.py (a release step), or check it is there.

    python tools/build_story.py            write the story block into cargo.py
    python tools/build_story.py --check    fail if cargo.py's block is out of date
    python tools/build_story.py --out F    write the built story to a file instead
                                           (play it with CARGO_STORY=F python cargo.py)

The story is written in story/cargo1.story.json and the files it includes;
character names that span the saga come from story/saga.json, with the errands
between the parts.  cargo.py stays one file: the built story sits between two
marker lines, one node per line, and storykit/record.py (the captain record's
history, shared by the three parts) between two more.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "storykit"))
import story as kit  # noqa: E402

STORY = os.path.join(ROOT, "story", "cargo1.story.json")
GAME = os.path.join(ROOT, "cargo.py")
BEGIN = "# --- story data (tools/build_story.py) ---\n"
END = "# --- end of story data ---\n"
RECORD = os.path.join(ROOT, "storykit", "record.py")
RECORD_BEGIN = "# --- captain history: storykit/record.py (tools/build_story.py) ---\n"
RECORD_END = "# --- end of captain history ---\n"

NODE_FIELDS = ("kind", "arc", "act", "title", "text", "variants", "requires", "effects", "choices", "next",
               "choose", "in", "who", "where", "chance", "repeat", "status", "handled_by", "sound")
CHARACTER_FIELDS = ("name", "short", "full", "title", "kind", "generated")
PLACE_FIELDS = ("kind", "type", "system", "ly", "made")


def build():
    story = kit.load(STORY)
    nodes = {}
    repaired = []
    for nid, node in story["nodes"].items():
        nodes[nid] = {k: node[k] for k in NODE_FIELDS if k in node}
        if any("requires" in a.get("fields", []) for a in node.get("amended", [])):
            repaired.append(nid)
    return {
        "game": story["game"]["id"],
        "characters": {cid: {k: c[k] for k in CHARACTER_FIELDS if k in c}
                       for cid, c in sorted(story["characters"].items())},
        "flags": {fid: {k: f[k] for k in ("about", "carries_to") if k in f}
                  for fid, f in sorted(story["flags"].items())},
        "places": {pid: {k: p[k] for k in PLACE_FIELDS if k in p}
                   for pid, p in story["places"].items() if p.get("kind") == "location"},
        "errands": story.get("errands", {}),
        "aliases": story.get("aliases", {}),
        "features": story.get("features", {}),
        "repaired": sorted(repaired),
        "order": list(nodes),
        "nodes": nodes,
    }


def as_block(data):
    """The story as Python source: a raw string, one node per line (readable diffs)."""
    head = {k: v for k, v in data.items() if k != "nodes"}
    lines = [json.dumps(head, ensure_ascii=False, separators=(",", ":"))[:-1] + ',"nodes":{']
    items = list(data["nodes"].items())
    for i, (nid, node) in enumerate(items):
        lines.append(json.dumps(nid) + ":" + json.dumps(node, ensure_ascii=False, separators=(",", ":"))
                     + ("," if i < len(items) - 1 else ""))
    lines.append("}}")
    text = "\n".join(lines)
    if '"""' in text:
        raise SystemExit("story text contains a triple quote; cannot embed it")
    return 'STORY_JSON = r"""' + text + '"""\n'


def record_block():
    """storykit/record.py as it is, run into its own namespace (`history`) when cargo.py loads."""
    with open(RECORD, encoding="utf-8") as handle:
        source = handle.read()
    if "\'\'\'" in source or source.rstrip().endswith("\\"):
        raise SystemExit("storykit/record.py cannot be embedded (triple single quote or a trailing backslash)")
    return "CAPTAIN_HISTORY_SOURCE = r\'\'\'" + source + "\'\'\'\n"


def main(argv):
    data = build()
    if "--out" in argv:
        path = argv[argv.index("--out") + 1]
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=1)
        print("wrote %s (%d nodes)" % (path, len(data["nodes"])))
        return 0
    with open(GAME, encoding="utf-8") as handle:
        source = handle.read()
    try:
        a = source.index(BEGIN) + len(BEGIN)
        b = source.index(END, a)
    except ValueError:
        print("cargo.py has no story block markers")
        return 1
    try:
        c = source.index(RECORD_BEGIN) + len(RECORD_BEGIN)
        d = source.index(RECORD_END, c)
    except ValueError:
        print("cargo.py has no captain history markers")
        return 1
    block = as_block(data)
    history = record_block()
    if "--check" in argv:
        if source[a:b] != block:
            print("cargo.py's story block is out of date: run python tools/build_story.py")
            return 1
        if source[c:d] != history:
            print("cargo.py's captain history is not storykit/record.py: run python tools/build_story.py")
            return 1
        print("cargo.py carries the current story (%d nodes) and captain history" % len(data["nodes"]))
        return 0
    if a > c:
        raise SystemExit("cargo.py: the story block must come before the captain history")
    with open(GAME, "w", encoding="utf-8") as handle:
        handle.write(source[:a] + block + source[b:c] + history + source[d:])
    print("wrote the story into cargo.py: %d nodes, %d characters, %d repaired conditions" % (
        len(data["nodes"]), len(data["characters"]), len(data["repaired"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
