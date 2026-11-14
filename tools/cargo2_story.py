"""Read Cargo 2's story data (YAML) into a storykit file.

    python tools/cargo2_story.py PATH/TO/Cargo-2        # writes story/cargo2.story.json

Development tool only: needs PyYAML (Cargo 2 already depends on it).
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "storykit"))

import story as kit           # noqa: E402
from cargo_story import STATS, translate, translate_rewards   # noqa: E402

OUT = os.path.join(ROOT, "story", "cargo2.story.json")

CHAR_REQS = {
    "min_reputation": "passenger_reputation",
    "min_plot_points": "plot_points",
    "min_chapters_completed": "chapters_completed",
    "min_neuroengineering_guilds": "buildings.Neuroengineering Guild",
    "min_agrobot_assembly_lines": "buildings.Agrobot Assembly Line",
    "min_comfort_level": "comfort_level",
}
EVENT_REQS = {
    "min_reputation": ("passenger_reputation", "min"), "max_reputation": ("passenger_reputation", "max"),
    "min_plot_points": ("plot_points", "min"), "max_plot_points": ("plot_points", "max"),
    "min_trades_completed": ("trades_completed", "min"), "max_trades_completed": ("trades_completed", "max"),
    "min_combat_victories": ("combat_victories", "min"),
    "min_passengers_transported": ("passengers_transported", "min"),
    "min_ship_speed": ("ship_speed", "min"), "min_trade_profit": ("trade_profit", "min"),
}


def load_yaml(path):
    import yaml
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def text(value):
    return " ".join(str(value).split()) if value else ""


def import_cargo2(repo):
    data = os.path.join(repo, "data")
    story = load_yaml(os.path.join(data, "story.yml"))
    chars = load_yaml(os.path.join(data, "characters.yml"))
    events = load_yaml(os.path.join(data, "events.yml"))
    quests = load_yaml(os.path.join(data, "quests.yml"))
    research = sorted((load_yaml(os.path.join(data, "research.yml")) or {}).get("research_options", {}))
    with open(os.path.join(data, "locations.csv"), encoding="utf-8") as handle:
        place_types = sorted({row["location_type"] for row in csv.DictReader(handle)})

    nodes = {}
    milestone_parent = {m["milestone_id"]: cid for cid, ch in story.items() for m in ch.get("milestones", [])}
    acts = {"ch1": 1, "ch2a": 2, "ch2b": 2, "ch3a": 3, "ch3b": 3, "ch3c": 3}
    for cid, ch in story.items():
        cond, notes = translate(ch.get("requirements") or {}, milestone_parent)
        ending = not ch.get("next_chapters")
        node = {"kind": "ending" if ending else "chapter", "arc": "main", "act": acts.get(cid, 4),
                "title": ch.get("title", cid), "text": text(ch.get("description")), "requires": cond,
                "next": list(ch.get("next_chapters") or []), "source": "data/story.yml"}
        if len(node["next"]) > 1:
            node["choose"] = True
        if cid == "ch1":
            node["start"] = True
        if notes:
            node["notes"] = notes
        nodes[cid] = node
        for m in ch.get("milestones", []):
            mcond, mnotes = translate(m.get("requirements") or {}, milestone_parent)
            mnode = {"kind": "milestone", "arc": "main", "in": cid, "title": m.get("title"),
                     "text": text(m.get("story_text")) or text(m.get("description")),
                     "requires": mcond, "effects": translate_rewards(m.get("rewards")), "source": "data/story.yml"}
            variants = []
            if m.get("alternate_text"):
                variants.append({"when": "alternate", "text": text(m["alternate_text"])})
            for key, line in (m.get("dialogue") or {}).items():
                variants.append({"when": key, "text": text(line)})
            if variants:
                mnode["variants"] = variants
            if mnotes:
                mnode["notes"] = mnotes
            nodes["%s.%s" % (cid, m["milestone_id"])] = mnode

    characters = {}
    for tid, t in chars.items():
        if not isinstance(t, dict) or "basic_info" not in t:
            continue
        info = t["basic_info"]
        pattern = (info.get("name_pattern") or [""])[0]
        name = pattern if pattern and "{" not in pattern else (info.get("title_pool") or [tid.replace("_", " ").title()])[0]
        characters[tid] = {"name": name,
                           "kind": info.get("type", "human"), "role": info.get("specialization", ""),
                           "generated": "{" in str(info.get("name_pattern", ["{"])[0]) or "name_pattern" not in info}
        req = t.get("requirements", {})
        cond = {}
        for key, value in req.items():
            if key in CHAR_REQS and value:
                cond[CHAR_REQS[key]] = value
            elif key == "spawn_locations":
                cond["at"] = list(value)
        node = {"kind": "encounter", "arc": "characters", "title": characters[tid]["name"], "who": [tid],
                "requires": cond, "chance": req.get("spawn_chance", 0), "repeat": True,
                "text": text((t.get("dialogue") or {}).get("first_meeting", [""])[0]),
                "source": "data/characters.yml"}
        if "spawn_locations" not in req:
            node["notes"] = ["no spawn_locations: never offered in a port or cantina"]
            node["status"] = "unused"
        nodes["visit." + tid] = node

    for eid, e in events.items():
        cond = {}
        for key, value in (e.get("conditions") or {}).items():
            if key in EVENT_REQS:
                stat, side = EVENT_REQS[key]
                if side == "min":
                    cond[stat] = value if not isinstance(cond.get(stat), dict) else dict(cond[stat], min=value)
                else:
                    cond[stat] = dict(min=cond.get(stat, 0) if not isinstance(cond.get(stat), dict) else
                                      cond[stat].get("min", 0), max=value)
            elif key == "min_turn":
                cond["turn_min"] = value
            elif key == "max_turn":
                cond["turn_max"] = value
            elif key == "location_type":
                cond["at_type"] = value
            else:
                cond["code"] = "%s = %s" % (key, value)
        msgs = e.get("messages") or {}
        nodes["event." + eid] = {
            "kind": "event", "arc": "events: " + str(e.get("type", "other")), "title": eid.replace("_", " ").capitalize(),
            "text": text(msgs.get("default") or e.get("message")), "requires": cond, "repeat": {"cooldown": e.get("cooldown", 0)},
            "effects": {"plot_points": e.get("plot_points", 0)},
            "variants": [{"when": k, "text": text(v)} for k, v in msgs.items() if k != "default"],
            "source": "data/events.yml"}

    for qtype, templates in quests.get("quests", {}).items():
        for i, q in enumerate(templates, 1):
            nodes["quest.%s.%d" % (qtype, i)] = {
                "kind": "quest", "arc": "quests", "title": q.get("name"), "text": text(q.get("description")),
                "requires": {}, "repeat": True, "chance": 0.1,
                "effects": {"money": q.get("reward_money", 0), "research_points": q.get("reward_rp", 0)},
                "notes": ["procedural quest template: offered in the cantina"], "source": "data/quests.yml"}

    arcs = {"main": {"title": "Main story", "order": 0}, "characters": {"title": "Characters", "order": 1},
            "quests": {"title": "Quests", "order": 9}}
    for n in nodes.values():
        arcs.setdefault(n["arc"], {"title": n["arc"].capitalize(), "order": 5})

    stats = {k: {"about": v} for k, v in STATS.items()}
    stats.update({"chapters_completed": {"about": "chapters completed"},
                  "comfort_level": {"about": "passenger module comfort"},
                  "ship_speed": {"about": "ship speed"}})
    places = {t: {"kind": "location type"} for t in place_types}
    places.update({"port": {"kind": "venue"}, "cantina": {"kind": "venue"}})
    return {
        "format": kit.FORMAT, "version": kit.VERSION,
        "game": {"id": "cargo2", "title": "Cargo 2", "part": 2},
        "about": "Imported from Cargo 2's data/*.yml by tools/cargo2_story.py.",
        "stats": stats,
        "sets": {"researched": {"about": "research unlocked", "members": research}, "items": {"about": "items carried"}},
        "effects": {"code": {"about": "game code"}},
        "flags": {}, "places": places, "characters": characters, "arcs": arcs, "nodes": nodes,
    }


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    data = import_cargo2(argv[1])
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
    print("wrote %s: %d nodes, %d characters" % (os.path.relpath(OUT, ROOT), len(data["nodes"]), len(data["characters"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
