"""Cargo 1 and the story kit: read the story out of cargo.py, and describe play as data.

    python tools/cargo_story.py import        # writes story/cargo1.story.json from the code
    python tools/cargo_story.py check          # fails if the file no longer matches the code

`snapshot(game)` turns a running game into the State the story kit evaluates;
`game_verdicts(game)` asks the game itself whether each extracted condition holds,
so the extraction can be checked against the real code during play (bot.py --trace).
"""
import ast
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "storykit"))

import story as kit  # noqa: E402

STORY_PATH = os.path.join(ROOT, "story", "cargo1.story.json")

# Hand-written story files merged into the imported one (drafts until the game reads them)
INCLUDES = ["cargo1/legacy.json", "cargo1/places.json", "cargo1/main.json", "cargo1/captain.json", "cargo1/synthetics.json",
            "cargo1/pirates.json", "cargo1/passengers.json", "cargo1/houses.json", "cargo1/frontier.json",
            "cargo1/enclaves.json", "cargo1/neons.json", "cargo1/crew.json", "cargo1/hansa.json",
            "cargo1/science.json", "cargo1/recurring.json", "cargo1/serac.json",
            "cargo1/people.json", "cargo1/cargolytes.json", "cargo1/legion_freight.json",
            "cargo1/rootstock.json", "cargo1/contracts.json", "cargo1/odds.json", "cargo1/drama.json", "cargo1/rumours.json", "cargo1/gossip.json",
            "cargo1/epilogue.json"]

PLACE_TYPES = ["Planet", "AsteroidBase", "DeepSpaceOutpost", "ResearchColony"]
BUILDINGS = ["stockmarket", "Neuroengineering Guild", "Agrobot Assembly Line", "mining_platform"]
VICTORY_TYPES = ["total", "pirate", "militia", "raider", "machine", "rogue_captain", "uprising"]

STATS = {
    "money": "credits on hand",
    "plot_points": "story points (StoryManager.plot_points)",
    "research_points": "research points on hand",
    "trades_completed": "buy and sell actions completed",
    "trade_profit": "total trade profit, all goods",
    "passengers_transported": "passengers delivered",
    "passenger_reputation": "passenger reputation",
    "combat_rating": "attack + defence + speed",
    "combat_victories": "battles won (all kinds)",
    "discovered": "locations visited at least once",
    "mining_platforms": "mining platforms built, all locations",
    "stockmarket_everywhere": "1 when every planet, asteroid base and outpost has a stock market",
    "controlled_locations": "locations marked controlled_by_player (nothing in the game sets this)",
    "milestones_done": "story milestones completed (StoryManager.completed_story_beats)",
    "best_cabin": "comfort level of the best passenger cabin aboard",
    "turns_since_vip": "turns since the last VIP passenger appeared",
    "crew_size": "helpers hired (the ship has bunks for four)",
    "hansa_bonds": "Hansa bonds held (each lowers the convoy dues)",
    "dues_arrears": "convoy dues owed and not yet paid",
    "hull_class": "the ship's hull: 0 the old hauler, 1 Ironback, 2 Farstrider",
    "hold_free": "free room in the hold for dry goods, after special cargo",
}
for _g in ("tech", "agri", "salt", "fuel"):
    STATS["cargo." + _g] = "%s in the hold (an effect adds or takes it)" % _g
for _t in VICTORY_TYPES[1:]:
    STATS["combat_victories." + _t] = "battles won against " + _t
for _b in BUILDINGS:
    STATS["buildings." + _b] = "%s buildings, all locations" % _b
for _t in PLACE_TYPES:
    STATS["discovered." + _t] = "%s locations visited" % _t

NOT_PRODUCED = {"controlled_locations"}

# What a text may say in braces besides a character ({pirate_captain}, {pirate_captain.short})
PLACEHOLDERS = ["player_name", "rank", "money", "trades_completed", "combat_victories", "research_points",
                "discoveries", "place", "turn", "visitor.name", "visitor.rank", "visitor.game", "visitor.ending",
                "origin.name", "origin.rank", "origin.game", "origin.ending", "origin.turns"]   # stats the game never raises above 0


# ---------------------------------------------------------------------------
# Play as data
# ---------------------------------------------------------------------------

def snapshot(game):
    """The moment of play the story kit evaluates conditions against (the game's own view)."""
    snap = game.story_snapshot()
    snap["origin"] = game.story.origin
    return snap


def story_moment(game):
    """The story runtime's last look: the state it judged and its verdicts (the
    evaluator inlined in cargo.py must agree with storykit's on the same state)."""
    moments = getattr(sys.modules[type(game).__module__], "STORY_MOMENTS", {})
    snap, verdicts = moments.get(id(game), (None, None))
    if snap is None:
        return None
    return {"state": snap, "verdicts": dict(verdicts)}


def game_verdicts(game):
    """The game's own answer, per extracted node, to 'do your requirements hold now?'."""
    out = {}
    sm = game.story_manager
    check = game.story_manager.chapters["ch1"].milestones["first_trade"].__class__  # StoryMilestone
    reqs = sys.modules[type(game).__module__].MilestoneRequirements
    for cid, chapter in sm.chapters.items():
        out[cid] = bool(reqs.check_requirements(chapter.requirements, game))
        for mid, milestone in chapter.milestones.items():
            out["%s.%s" % (cid, mid)] = bool(reqs.check_requirements(milestone.requirements, game))
    del check
    return out


# ---------------------------------------------------------------------------
# Requirement translation (Cargo 1 requirement dicts -> storykit conditions)
# ---------------------------------------------------------------------------

def translate(reqs, milestone_parent):
    cond = {}
    notes = []
    for key, value in reqs.items():
        if key in ("plot_points", "money", "research_points", "combat_rating", "trades_completed",
                   "trade_profit", "passengers_transported", "passenger_reputation"):
            cond[key] = value
        elif key == "combat_victories":
            if isinstance(value, dict):
                for t, n in value.items():
                    cond["combat_victories" if t == "total" else "combat_victories." + t] = n
            else:
                cond["combat_victories"] = value
        elif key == "buildings_built":
            for b, n in value.items():
                cond["buildings." + b] = n
        elif key == "locations_discovered":
            if isinstance(value, dict):
                for t, n in value.items():
                    cond["discovered." + t] = n
            else:
                cond["discovered"] = value
        elif key == "research_unlocked":
            cond.setdefault("has", {})["researched"] = list(value)
        elif key == "items":
            cond.setdefault("has", {})["items"] = list(value)
        elif key == "chapters_completed":
            cond["done"] = list(value)
        elif key == "chapters_completed_any":
            cond["done_any"] = list(value)
        elif key == "milestones_completed":
            cond["done"] = cond.get("done", []) + ["%s.%s" % (milestone_parent.get(m, "?"), m) for m in value]
        elif key == "story_states":
            cond["flag"] = list(value)
        elif key == "visiting_captain":
            cond["visiting_captain"] = value
        else:
            cond.setdefault("code", []).append("%s: %r" % (key, value))
            notes.append("requirement type %r has no storykit translation" % key)
    if "code" in cond:
        cond["code"] = "; ".join(cond["code"])
    return cond, notes


def translate_rewards(rewards):
    effects = {}
    for key, value in (rewards or {}).items():
        if key == "items":
            effects.setdefault("give", {})["items"] = list(value)
        else:
            effects[key] = value
    return effects


# ---------------------------------------------------------------------------
# Reading literals out of the source
# ---------------------------------------------------------------------------

def _function(tree, cls, name):
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == cls:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == name:
                    return item
    raise KeyError("%s.%s" % (cls, name))


def _assigned_dict(func, var):
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == var for t in node.targets):
            return node.value
    raise KeyError(var)


def _text_template(node):
    """A string or f-string as text, with {expressions} kept readable."""
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.JoinedStr):
        out = []
        for part in node.values:
            if isinstance(part, ast.Constant):
                out.append(str(part.value))
            else:
                expr = ast.unparse(part.value)
                expr = re.sub(r"self\.game\.format_money\((.*)\)", r"\1", expr)
                expr = expr.replace("self.game.", "").replace("ship.", "")
                out.append("{%s}" % expr)
        return "".join(out)
    return ast.unparse(node)


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def import_story(cargo, game):
    sm = game.story_manager
    nodes = {}

    def add(nid, **node):
        if nid in nodes:
            raise ValueError("duplicate node " + nid)
        nodes[nid] = node
        return node

    milestone_parent = {mid: cid for cid, ch in sm.chapters.items() for mid in ch.milestones}

    # --- main story: chapters, milestones, endings ------------------------------
    for cid, ch in sm.chapters.items():
        cond, notes = translate(ch.requirements, milestone_parent)
        is_ending = not ch.next_chapters
        node = add(cid, kind="ending" if is_ending else "chapter", arc="main",
                   act=sm.get_chapter_number(cid), title=ch.title, text=ch.description,
                   requires=cond, next=list(ch.next_chapters),
                   source="cargo.py StoryManager.__init__ (chapters)")
        if len(ch.next_chapters) > 1:
            node["choose"] = True
        if is_ending:
            node["text"] = [ch.description]
            node["effects"] = {"code": "ending screen, score, epilogue, captain record exported"}
        if cid == "ch1":
            node["start"] = True
        if notes:
            node["notes"] = notes
        for mid, m in ch.milestones.items():
            mcond, mnotes = translate(m.requirements, milestone_parent)
            mnode = add("%s.%s" % (cid, mid), kind="milestone", arc="main", **{"in": cid},
                        title=m.title, text=m.description, requires=mcond,
                        effects=translate_rewards(m.rewards),
                        source="cargo.py StoryManager.__init__ (milestones)")
            if mnotes:
                mnode["notes"] = mnotes
        # chapter completion needs its milestones: say so explicitly
        node["completes_when"] = "requirements and all milestones"

    # --- the tycoon ending and the Stellar Portal (Game.play) ------------------
    add("tycoon_offer", kind="event", arc="main", title="The galaxy's markets are yours",
        text="Every planet, asteroid base and outpost has a stock market. Resign as Galactic Tycoon, "
             "or pay for the secret quest and continue into the unknown.",
        requires={"stockmarket_everywhere": 1}, repeat={"cooldown": 10},
        choices=[
            {"id": "resign", "say": "Resign", "next": "ending_tycoon"},
            {"id": "continue", "say": "Continue into the unknown", "requires": {"money": 1500},
             "effects": {"money": -1500, "set": ["stellar_portal"], "code": "new set of locations; jump there"},
             "next": "stellar_portal"},
        ],
        notes=["offered every 10 turns while the condition holds: keep trading, retire, or the portal"],
        handled_by="Game.play (text from the story)",
        source="cargo.py Game.play (secret quest)")
    add("ending_tycoon", kind="ending", arc="main", act=4, title="Galactic Tycoon",
        text=["You are the Galactic Tycoon!",
              "Congratulations, {player_name}! You have achieved the rank of {rank}.",
              "Your story will be remembered throughout the galaxy."],
        requires={"done": "tycoon_offer"}, effects={"code": "score screen, epilogue, captain record exported"},
        handled_by="Game.play (text from the story)",
        source="cargo.py Game.play (secret quest)")
    add("stellar_portal", kind="event", arc="main", title="The Stellar Portal",
        text="A Stellar Portal appears. You travel to a new set of locations with more volatile price movements.",
        requires={"flag": "stellar_portal"}, source="cargo.py Game.play (secret quest), Game.open_portal",
        handled_by="Game.open_portal (text from the story)")

    characters = {}

    # --- chance encounters (SpecialCharacterEncounters, random events) ---------
    enc = game.character_encounters.encounter_chances
    for place_type, chances in enc.items():
        for who, chance in chances.items():
            characters.setdefault(who, {"name": who.replace("_", " ").title(), "kind": "human",
                                        "generated": True, "about": "met by chance"})
            node = add("chance.%s.%s" % (place_type, who), kind="encounter", arc="chance meetings",
                       title="%s (%s)" % (characters[who]["name"], place_type), who=[who],
                       chance=round(0.15 * chance, 4), repeat=True,
                       handled_by="SpecialCharacterEncounters.handle_%s_encounter" % who,
                       source="cargo.py SpecialCharacterEncounters.encounter_chances + Game.random_event")
            if place_type != "Space":
                node["status"] = "unused"
                node["notes"] = ["random_event only rolls the 'Space' table"]
            elif chance == 0:
                node["status"] = "unused"
                node["notes"] = ["chance is 0"]
            if who == "rogue_captain":
                node.setdefault("notes", []).append(
                    "demands money or fights; does not start the 'rogue_captain' event chain")

    # --- the frontier: hidden location types and their story events -----------
    lm = game.location_manager
    for ltype, q in lm.location_quests.items():
        if ltype == "Planet":
            continue
        cond = {}
        for k, v in q["unlock_requirements"].items():
            if k == "mining_platforms_built":
                cond["mining_platforms"] = v
            elif k == "discoveries":
                cond["milestones_done"] = v
            elif k in STATS:
                cond[k] = v
            elif k == "combat_victories":
                cond["combat_victories"] = v
            else:
                cond.setdefault("code", "")
                cond["code"] = (cond["code"] + " %s >= %s" % (k, v)).strip()
        uq = q["unlock_quest"]
        add("unlock." + ltype, kind="quest", arc="frontier", title=uq["name"], text=uq["description"],
            requires=cond, effects={"money": uq.get("reward_money", 0), "research_points": uq.get("reward_rp", 0),
                                    "give": {"unlocked_types": [ltype]}},
            notes=["offered when the requirements hold; completes on the next journey and reveals the locations"],
            handled_by="LocationManager.trigger_location_unlock_quest (text from the story)",
            source="cargo.py LocationManager.location_quests")
    for ltype, events in lm.location_story_events.items():
        for ev in events:
            add("beat.%s.%s" % (ltype, ev), kind="beat", arc="frontier",
                title=ev.replace("_", " ").capitalize(), where=ltype,
                requires={"at_type": ltype, "has": {"unlocked_types": [ltype]}}, chance=round(0.3 / len(events), 4),
                effects={"plot_points": 10},
                notes=["names from LocationManager.location_story_events; the story plays them"],
                source="cargo.py LocationManager.location_story_events")

    # --- synthetics: uprisings ------------------------------------------------
    for stype, building in (("Neurodroid", "Neuroengineering Guild"), ("Agrobot", "Agrobot Assembly Line")):
        add("uprising.%s.local" % stype, kind="event", arc="synthetics",
            title="%s demands (one location)" % stype, who=[stype.lower()],
            handled_by="SyntheticEventManager.handle_synthetic_uprising",
            requires={"code": "4 or more %s at one location" % building, "buildings." + building: 4},
            repeat=True, source="cargo.py SyntheticEventManager.check_synthetic_awareness")
        add("uprising.%s.global" % stype, kind="event", arc="synthetics",
            title="%s uprising (sector)" % stype, who=[stype.lower()],
            handled_by="SyntheticEventManager.start_uprising",
            requires={"buildings." + building: 8}, repeat=True,
            source="cargo.py SyntheticEventManager.check_synthetic_awareness")
        characters.setdefault(stype.lower(), {"name": stype + "s", "kind": "synthetic", "generated": True,
                                              "about": "synthetic workers that gain awareness"})

    # --- story flags -----------------------------------------------------------
    flags = {f: {"about": "", "set_by_game": []} for f in sm.story_states}
    rules = {
        "pirate_threat": ["a battle against pirates (process_event)", "a combat quest done with 25+ victories"],
        "alien_discovery": ["an exploration event with an artifact"],
        "trade_empire": ["a trade quest done with 50+ trades"],
        "tech_breakthrough": ["a research quest done with 3+ research unlocked"],
        "ancient_mystery": ["an exploration quest done with 5+ locations discovered"],
    }
    for f, how in rules.items():
        flags.setdefault(f, {"about": ""})["set_by_game"] = how
    flags["tech_breakthrough"]["notes"] = ["set by the game but missing from StoryManager.story_states"]
    flags["stellar_portal"] = {"about": "the captain paid for the secret quest", "set_by_game": [],
                               "carries_to": ["cargo2"]}       # Cargo 2's tycoon opening reads it

    places = {t: {"kind": "location type", "hidden": t != "Planet"} for t in PLACE_TYPES}
    places["Space"] = {"kind": "between locations"}

    return {
        "format": kit.FORMAT,
        "version": kit.VERSION,
        "game": {"id": "cargo1", "title": "CARGO: Space Trading Saga", "part": 1},
        "about": "Chapters, milestones and the frontier are read out of cargo.py by tools/cargo_story.py; "
                 "everything else is written in the files listed under include. tools/build_story.py "
                 "puts the whole story into cargo.py, which plays it.",
        "saga": "saga.json",
        "placeholders": PLACEHOLDERS,
        "include": INCLUDES,
        "stats": {k: {"about": v, **({"produced": False} if k in NOT_PRODUCED else {})} for k, v in STATS.items()},
        "sets": {"researched": {"about": "research unlocked", "members": sorted(game.research.research_costs)},
                 "items": {"about": "items carried"},
                 "crew": {"about": "helpers aboard", "members": ["loader", "steward", "mechanic", "gunner",
                                                                 "navigator", "broker"]},
                 "unlocked_types": {"about": "hidden location types revealed", "members": PLACE_TYPES}},
        "effects": {"code": {"about": "game code the tools cannot read"}},
        "flags": flags,
        "places": places,
        "characters": dict(sorted(characters.items())),
        "arcs": {
            "main": {"title": "Main story", "order": 0},
            "frontier": {"title": "Frontier: hidden locations", "order": 1},
            "passengers": {"title": "Passengers and envoys", "order": 2},
            "pirates": {"title": "Pirates", "order": 3},
            "synthetics": {"title": "Synthetics", "order": 4},
            "chance meetings": {"title": "Chance meetings", "order": 5},
            "characters": {"title": "Other character chains", "order": 6},
            "quest lines": {"title": "Quest lines", "order": 7},
        },
        "nodes": nodes,
    }


RENAME = {"reputation": "passenger_reputation"}


def _numeric_effects(values):
    out = {}
    for k, v in values.items():
        k = RENAME.get(k, k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and k in STATS:
            out[k] = v
    return out


def _load_game():
    from headless import load, new_game
    cargo = load(os.path.join(ROOT, "cargo.py"))
    game, _ = new_game(cargo)
    return cargo, game


def main(argv):
    if len(argv) < 2 or argv[1] not in ("import", "check"):
        print(__doc__)
        return 2
    cargo, game = _load_game()
    data = import_story(cargo, game)
    if argv[1] == "check":
        with open(STORY_PATH, encoding="utf-8") as handle:
            current = json.load(handle)
        drift = sorted(k for k in set(data["nodes"]) | set(current["nodes"])
                       if data["nodes"].get(k) != current["nodes"].get(k))
        other = [k for k in data if k != "nodes" and data[k] != current.get(k)]
        if drift or other:
            print("story/cargo1.story.json no longer matches cargo.py: nodes %s; sections %s" % (drift[:12], other))
            print("run: python tools/cargo_story.py import")
            return 1
        print("story/cargo1.story.json matches cargo.py (%d nodes)" % len(data["nodes"]))
        return 0
    os.makedirs(os.path.dirname(STORY_PATH), exist_ok=True)
    with open(STORY_PATH, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
    kinds = {}
    for n in data["nodes"].values():
        kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
    print("wrote %s: %d nodes %s, %d characters, %d flags" % (
        os.path.relpath(STORY_PATH, ROOT), len(data["nodes"]), kinds, len(data["characters"]), len(data["flags"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
