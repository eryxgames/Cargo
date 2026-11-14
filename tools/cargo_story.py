"""Cargo 1 and the story kit: read the story out of cargo.py, and describe play as data.

    python tools/cargo_story.py import        # writes story/cargo1.story.json from the code
    python tools/cargo_story.py check          # fails if the file no longer matches the code

`snapshot(game)` turns a running game into the State the story kit evaluates;
`game_verdicts(game)` asks the game itself whether each extracted condition holds,
so the extraction can be checked against the real code during play (bot.py --trace).
"""
import ast
import inspect
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
INCLUDES = ["cargo1/places.json", "cargo1/main.json", "cargo1/captain.json", "cargo1/synthetics.json",
            "cargo1/pirates.json", "cargo1/passengers.json", "cargo1/houses.json", "cargo1/frontier.json",
            "cargo1/enclaves.json"]

PLACE_TYPES = ["Planet", "AsteroidBase", "DeepSpaceOutpost", "ResearchColony"]
BUILDINGS = ["stockmarket", "Neuroengineering Guild", "Agrobot Assembly Line", "mining_platform"]
VICTORY_TYPES = ["total", "pirate", "militia", "rogue_captain", "uprising"]

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
    "turns_since_vip": "turns since the last VIP passenger appeared",
}
for _t in VICTORY_TYPES[1:]:
    STATS["combat_victories." + _t] = "battles won against " + _t
for _b in BUILDINGS:
    STATS["buildings." + _b] = "%s buildings, all locations" % _b
for _t in PLACE_TYPES:
    STATS["discovered." + _t] = "%s locations visited" % _t

NOT_PRODUCED = {"controlled_locations"}   # stats the game never raises above 0


# ---------------------------------------------------------------------------
# Play as data
# ---------------------------------------------------------------------------

def snapshot(game):
    """The moment of play the story kit evaluates conditions against."""
    ship = game.ship
    sm = game.story_manager
    stats = {
        "money": int(ship.money),
        "plot_points": sm.plot_points,
        "research_points": ship.research_points,
        "trades_completed": game.trades_completed,
        "trade_profit": int(sum(ship.trade_profits.values())),
        "passengers_transported": game.reputation_manager.total_passengers,
        "passenger_reputation": ship.passenger_reputation,
        "combat_rating": ship.attack + ship.defense + ship.speed,
        "combat_victories": ship.combat_victories.get("total", 0),
        "discovered": len(set(game.discovered_locations)),
        "mining_platforms": sum(len(loc.mining_platforms) for loc in game.locations),
        "controlled_locations": sum(1 for loc in game.locations if hasattr(loc, "controlled_by_player")),
        "milestones_done": len(sm.completed_story_beats),
        "turns_since_vip": game.turn - game.reputation_manager.last_vip_spawn,
    }
    for t in VICTORY_TYPES[1:]:
        stats["combat_victories." + t] = ship.combat_victories.get(t, 0)
    for b in BUILDINGS:
        stats["buildings." + b] = sum(loc.buildings.count(b) for loc in game.locations)
    for t in PLACE_TYPES:
        stats["discovered." + t] = game.count_discovered(t)
    markets = [loc for loc in game.locations if loc.location_type in ("Planet", "AsteroidBase", "DeepSpaceOutpost")]
    stats["stockmarket_everywhere"] = int(bool(markets) and all(loc.stockmarket_base for loc in markets))

    done = set(sm.completed_chapters)
    for cid, chapter in sm.chapters.items():
        for mid, milestone in chapter.milestones.items():
            if milestone.completed:
                done.add("%s.%s" % (cid, mid))
    return {
        "turn": game.turn,
        "player": game.player_name,
        "act": sm.get_chapter_number(),
        "chapter": sm.current_chapter,
        "place": game.current_location.name,
        "place_type": game.current_location.location_type,
        "stats": stats,
        "sets": {
            "researched": sorted(game.research.unlocked_options),
            "items": sorted(k for k, v in ship.items.items() if isinstance(v, int) and v > 0),
            "unlocked_types": sorted(getattr(game, "unlocked_location_types", set())),
        },
        "flags": sorted(f for f, on in sm.story_states.items() if on),
        "done": sorted(done),
        "visitors": list(getattr(game, "visiting_captains", [])),
    }


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
    for tid, trigger in game.character_system.character_triggers.items():
        try:
            out["meet." + tid] = bool(trigger["condition"](game))
        except Exception:
            out["meet." + tid] = None
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


# Hand translations of the trigger conditions written as Python lambdas.
# Each one is checked against the lambda itself during play (check command).
TRIGGERS = {
    "neuroengineering_uprising": {"buildings.Neuroengineering Guild": 4},
    "agrobot_rebellion": {"buildings.Agrobot Assembly Line": 4},
    "pirate_nemesis": {"combat_victories.pirate": 10},
    "vip_passenger": {"passenger_reputation": 40, "turns_since_vip": 5},
    "galactic_alliance": {"passenger_reputation": 60, "act_min": 2},
    "system_rebellion": {"passenger_reputation": 70, "act_min": 3, "controlled_locations": 2},
    "ancient_mysteries": {"passenger_reputation": 80, "act_min": 4, "done": "ch3c.alien_artifacts"},
}
TRIGGER_ARCS = {
    "neuroengineering_uprising": "synthetics", "agrobot_rebellion": "synthetics",
    "pirate_nemesis": "pirates", "vip_passenger": "passengers", "galactic_alliance": "passengers",
    "system_rebellion": "passengers", "ancient_mysteries": "passengers",
}


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
    src = inspect.getsource(cargo)
    tree = ast.parse(src)
    sm = game.story_manager
    nodes = {}

    def add(nid, **node):
        if nid in nodes:
            raise ValueError("duplicate node " + nid)
        nodes[nid] = node
        return node

    milestone_parent = {mid: cid for cid, ch in sm.chapters.items() for mid in ch.milestones}

    # --- main story: chapters, milestones, endings ------------------------------
    endings_func = _function(tree, "StoryManager", "handle_game_ending")
    ending_texts = {}
    for k, v in zip(_assigned_dict(endings_func, "ending_messages").keys,
                    _assigned_dict(endings_func, "ending_messages").values):
        ending_texts[k.value] = [_text_template(e) for e in v.elts]

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
            node["text"] = [ch.description] + ending_texts.get(cid, [])
            node["effects"] = {"code": "ending screen, score, captain record exported"}
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
        requires={"stockmarket_everywhere": 1}, repeat=True,
        choices=[
            {"id": "resign", "say": "Resign", "next": "ending_tycoon"},
            {"id": "continue", "say": "Continue into the unknown", "requires": {"money": 1500},
             "effects": {"money": -1500, "set": ["stellar_portal"], "code": "new set of locations; jump there"},
             "next": "stellar_portal"},
        ],
        notes=["asked every turn while the condition holds, until the captain resigns"],
        source="cargo.py Game.play (secret quest)")
    add("ending_tycoon", kind="ending", arc="main", act=4, title="Galactic Tycoon",
        text=["You are the Galactic Tycoon!",
              "Congratulations, {player_name}! You have achieved the rank of {rank}.",
              "Your story will be remembered throughout the galaxy."],
        requires={"done": "tycoon_offer"}, effects={"code": "score screen, game ends"},
        notes=["outside the chapter system: no captain record is exported"],
        source="cargo.py Game.play (secret quest)")
    add("stellar_portal", kind="event", arc="main", title="The Stellar Portal",
        text="A Stellar Portal appears. You travel to a new set of locations with more volatile price movements.",
        requires={"flag": "stellar_portal"}, source="cargo.py Game.play (secret quest)",
        notes=["no story follows the portal yet: the natural door for the saga's time-space quests"])

    # --- characters triggered by progress (DynamicCharacterSystem) -------------
    cs = game.character_system
    chain_func = _function(tree, "DynamicCharacterSystem", "create_event_chain")
    names = [k.value for k in _assigned_dict(chain_func, "event_chain_templates").keys]

    class _Someone:                      # stands in for a generated character
        full_name = name = title = role = "Someone"

    templates = {name: cs.create_event_chain(name, _Someone()).stages for name in names}
    characters = {}
    used_chains = set()
    for tid, trig in cs.character_triggers.items():
        cond = dict(TRIGGERS.get(tid) or {"code": inspect.getsource(trig["condition"]).strip()})
        words = re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z][a-z]+|[A-Z]+", trig["character_type"])
        char_id = "_".join(words).lower()
        characters.setdefault(char_id, {
            "name": " ".join(words),
            "kind": trig["generator"], "generated": True,
            "about": "name and look generated when met (%s generator)" % trig["generator"]})
        node = add("meet." + tid, kind="encounter", arc=TRIGGER_ARCS.get(tid, "characters"),
                   title="%s appears" % characters[char_id]["name"], who=[char_id], requires=cond,
                   source="cargo.py DynamicCharacterSystem.character_triggers",
                   source_code=inspect.getsource(trig["condition"]).strip())
        if tid == "vip_passenger":
            node["repeat"] = {"cooldown": 5}
            node["handled_by"] = "Port: VIP boarding, PassengerReputationManager"
            node["notes"] = ["the VIP itself is boarded in the port; the 5-turn spacing comes from "
                             "PassengerReputationManager.last_vip_spawn"]
        chain = trig.get("event_chain")
        stages = templates.get(chain) if chain else None
        if stages is None and chain:
            stages = cs.event_chains.get(chain) if isinstance(cs.event_chains.get(chain), list) else None
        if stages:
            used_chains.add(chain)
            node["next"] = ["%s.%d" % (chain, 1)]
            _add_chain(add, chain, stages, node["arc"], [char_id])
        elif chain:
            node.setdefault("notes", []).append("event chain %r is not defined" % chain)

    # chains that exist but no trigger uses
    for chain, stages in list(templates.items()) + [(k, v) for k, v in cs.event_chains.items() if isinstance(v, list)]:
        if chain not in used_chains and isinstance(stages, list):
            used_chains.add(chain)
            first = _add_chain(add, chain, stages, "characters", [], status="unused")
            nodes[first].setdefault("notes", []).append("no trigger starts this chain")

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

    # --- CharacterManager templates (met in ports and cantinas) ----------------
    for tid, t in game.character_manager.templates.items():
        req = t.get("requirements", {})
        characters.setdefault(tid, {"name": t["basic_info"]["title_pool"][0], "kind": t["basic_info"].get("type", "human"),
                                    "generated": True, "about": "CharacterManager template"})
        cond = {"at_type": req.get("spawn_locations", [])} if req.get("spawn_locations") else {}
        for k, v in req.items():
            if k.startswith("min_") and k != "min_reputation":
                cond["code"] = (cond.get("code", "") + " %s >= %s" % (k[4:], v)).strip()
            elif k == "min_reputation" and v:
                cond["passenger_reputation"] = v
        node = add("visit." + tid, kind="encounter", arc="chance meetings", title=characters[tid]["name"],
                   who=[tid], requires=cond, chance=req.get("spawn_chance", 0), repeat=True,
                   text=(t.get("dialogue", {}).get("first_meeting") or [""])[0],
                   source="cargo.py CharacterManager.templates")
        if not req.get("spawn_locations"):
            node["status"] = "unused"
            node["notes"] = ["no spawn_locations: CharacterManager.update never spawns it"]

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
            source="cargo.py LocationManager.location_quests")
    for ltype, events in lm.location_story_events.items():
        for ev in events:
            add("beat.%s.%s" % (ltype, ev), kind="beat", arc="frontier",
                title=ev.replace("_", " ").capitalize(), where=ltype,
                requires={"has": {"unlocked_types": [ltype]}}, chance=round(0.3 / len(events), 4),
                trigger="on first visit to a %s" % ltype, effects={"plot_points": 10},
                notes=["a name only: no text, choice or consequence beyond plot points"],
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

    # --- quest lines declared but never used ----------------------------------
    for line, stages in game.quest_system.quest_lines.items():
        prev = None
        for i, stage in enumerate(stages, 1):
            nid = "questline.%s.%d" % (line, i)
            add(nid, kind="quest", arc="quest lines", title=stage.replace("_", " ").capitalize(),
                requires={"done": prev} if prev else {}, status="unused",
                notes=["QuestSystem.quest_lines: declared, never read"],
                source="cargo.py QuestSystem.quest_lines")
            prev = nid

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
    flags["stellar_portal"] = {"about": "the captain paid for the secret quest", "set_by_game": []}

    places = {t: {"kind": "location type", "hidden": t != "Planet"} for t in PLACE_TYPES}
    places["Space"] = {"kind": "between locations"}

    return {
        "format": kit.FORMAT,
        "version": kit.VERSION,
        "game": {"id": "cargo1", "title": "CARGO: Space Trading Saga", "part": 1},
        "about": "Extracted from cargo.py by tools/cargo_story.py. Until the game reads this file, "
                 "cargo.py is the truth for every node with a 'source'; new content goes in "
                 "the files listed under include.",
        "include": INCLUDES,
        "stats": {k: {"about": v, **({"produced": False} if k in NOT_PRODUCED else {})} for k, v in STATS.items()},
        "sets": {"researched": {"about": "research unlocked", "members": sorted(game.research.research_costs)},
                 "items": {"about": "items carried"},
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


def _add_chain(add, chain, stages, arc, who, status=None):
    for i, stage in enumerate(stages, 1):
        node = {"kind": "stage", "arc": arc, "title": "%s %d: %s" % (chain.replace("_", " ").capitalize(), i,
                                                                      stage.get("type", "stage")),
                "who": list(who), "requires": {"done": "%s.%d" % (chain, i - 1)} if i > 1 else {},
                "source": "cargo.py DynamicCharacterSystem (event chains)"}
        if stage.get("message"):
            node["text"] = stage["message"]
        if stage.get("choices"):
            node["choices"] = [{"id": c, "say": c.replace("_", " "),
                                "effects": _numeric_effects(stage.get("consequences", {}).get(c, {}))}
                               for c in stage["choices"]]
            for choice in node["choices"]:
                extra = {k: v for k, v in stage.get("consequences", {}).get(choice["id"], {}).items()
                         if RENAME.get(k, k) not in choice["effects"]}
                if extra:
                    choice["effects"]["code"] = json.dumps(extra)
        if stage.get("rewards"):
            node["effects"] = _numeric_effects(stage["rewards"])
            extra = {k: v for k, v in stage["rewards"].items() if RENAME.get(k, k) not in node["effects"]}
            if extra:
                node["effects"]["code"] = json.dumps(extra)
        extra = {k: v for k, v in stage.items() if k not in ("type", "message", "choices", "consequences", "rewards")}
        if extra:
            node["notes"] = ["stage data only the game's code reads: " + ", ".join(sorted(extra))]
        if i < len(stages):
            node["next"] = ["%s.%d" % (chain, i + 1)]
        if status:
            node["status"] = status
        add("%s.%d" % (chain, i), **node)
    return "%s.1" % chain


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
