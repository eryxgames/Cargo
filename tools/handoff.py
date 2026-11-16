#!/usr/bin/env python3
"""What Cargo 1 hands to the later parts, written out from the built story:
the promises they must pay, the flags a captain record carries to them (by arc, with what
each means) and the characters whose timelines continue.

    python3 tools/handoff.py            # writes story/CARGO1-HANDOFF.md
    python3 tools/handoff.py --check    # fails if that file is out of date
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from headless import load  # noqa: E402

OUT = os.path.join(ROOT, "story", "CARGO1-HANDOFF.md")


def setters(nodes, order):
    """flag -> the arc of the first node, in story order, that sets it (itself or by a choice)."""
    rank = {nid: i for i, nid in enumerate(order)}
    found = {}
    for nid, node in sorted(nodes.items(), key=lambda item: rank.get(item[0], len(rank))):
        effects = [node.get("effects") or {}] + [(c.get("effects") or {}) for c in node.get("choices", [])]
        for eff in effects:
            for flag in eff.get("set", []):
                found.setdefault(flag, node.get("arc") or nid.split(".")[0])
    return found


def build():
    cargo = load(os.path.join(ROOT, "cargo.py"))
    data = cargo.story_data()
    saga = json.load(open(os.path.join(ROOT, "story", "saga.json"), encoding="utf-8"))
    fill = lambda text: runtime_fill(data, text)
    flags = data["flags"]
    by_arc = {}
    arcs_of = setters(data["nodes"], data.get("order", []))
    for flag, info in sorted(flags.items()):
        if not info.get("carries_to"):
            continue
        arc = arcs_of.get(flag, "game")
        by_arc.setdefault(arc, []).append((flag, info))
    lines = ["# Cargo 1: what the later parts inherit", "",
             "Written by `tools/handoff.py` from the built story; do not edit by hand.", "",
             "Cargo 1 has %d story nodes, %d characters and %d flags. A captain record carries every flag"
             " that is set (up to 160, the carried ones first); %d of them are meant for later parts."
             % (len(data["nodes"]), len(data["characters"]), len(flags),
                sum(1 for i in flags.values() if i.get("carries_to"))), "",
             "## Promises", "", "| Promise | Paid by | What |", "| --- | --- | --- |"]
    for pid, prom in saga.get("promises", {}).items():
        lines.append("| `%s` | %s | %s |" % (pid, prom.get("pay_by", ""), prom.get("about", "")))
    lines += ["", "## Flags carried, by arc", "",
              "Cargo 2 reads the ones marked cargo2, Cargo 3 the ones marked cargo3.", ""]
    for arc in sorted(by_arc):
        lines += ["### %s" % arc, "", "| Flag | For | Means |", "| --- | --- | --- |"]
        for flag, info in by_arc[arc]:
            lines.append("| `%s` | %s | %s |" % (flag, ", ".join(info["carries_to"]), fill(info.get("about", ""))))
        lines.append("")
    lines += ["## Characters who go on", "", "| Character | Later |", "| --- | --- |"]
    for cid, char in saga.get("characters", {}).items():
        later = ["%s: %s" % (t.get("game"), t.get("as", "")) for t in char.get("timeline", [])
                 if t.get("game") in ("cargo2", "cargo3")]
        if later:
            name = (data["characters"].get(cid) or char).get("name", cid)
            lines.append("| %s | %s |" % (name, "; ".join(later).replace("|", "/")))
    return "\n".join(lines) + "\n"


def runtime_fill(data, text):
    """Character names in place of {id} and {id.short}, as the game shows them."""
    import re
    chars = data["characters"]

    def swap(m):
        person = chars.get(m.group(1)) or {}
        if m.group(2) == "short":
            return person.get("short") or person.get("name") or m.group(0)
        return person.get("name") or m.group(0)
    return re.sub(r"\{([a-z_][a-z0-9_]*)(?:\.([a-z_]+))?\}", swap, text)


if __name__ == "__main__":
    text = build()
    if "--check" in sys.argv:
        current = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if current != text:
            print("story/CARGO1-HANDOFF.md is out of date: run python3 tools/handoff.py")
            sys.exit(1)
        print("hand-off up to date")
    else:
        open(OUT, "w", encoding="utf-8").write(text)
        print("wrote", OUT)
