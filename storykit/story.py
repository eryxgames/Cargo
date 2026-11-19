"""storykit: a game's story as data, and the rules for reading it.

Standard library only, no game imports: the same file serves the validator, the
replay simulator, the map, and (later) the games themselves.

A story file holds nodes (chapters, milestones, quests, events, encounters,
endings...), the characters and places they use, and the vocabulary of
requirements and effects the game understands.  See FORMAT.md.
"""
import json
import os

try:                                    # the captain record's history (storykit/record.py)
    from . import record as captain_record
except ImportError:
    import record as captain_record

FORMAT = "storykit"
SAGA_FORMAT = "storykit-saga"
VERSION = 1

# Condition keys every game understands (anything else must be a declared stat)
CORE_CONDITIONS = {
    "all", "any", "not",            # combinators
    "flag", "not_flag",             # story flags
    "done", "done_any", "not_done", # nodes completed
    "since",                        # {node: turns}: that node happened at least so many turns ago
    "act_min", "act_max",           # act (chapter number) of the main story
    "turn_min", "turn_max",
    "at", "at_type",                # where the player is
    "has",                          # members of a declared set (items, research ...)
    "visiting_captain",             # a captain record from another part of the saga
    "player_origin",                # the record of the captain the player is playing as
    "venue",                        # a place inside a location the player is visiting (port, cantina)
    "chapter",                      # the chapter the player is in now (its id, or a list of ids)
    "here",                         # a character (or one of a list) whose route has them where the player is
    "past",                         # what the captain left in another part (era): {"era", "flag", "not_flag", "ending"}
    "errand",                       # errands (saga file) in a state: {"id": "none" | "open" | "done" | [...]}
    "code",                         # opaque: game code the tools cannot read
}

# Effect keys every game understands (anything else must be a declared stat or effect)
CORE_EFFECTS = {"set", "clear", "start", "spawn", "give", "reveal", "code",
                "errand",                   # give the captain an errand for another era (its id, or a list)
                "errand_done"}              # the errand is done here

NODE_KINDS = {"chapter", "milestone", "ending", "quest", "event", "encounter", "stage", "unlock", "beat",
              "intro", "epilogue", "rumour", "sight", "thought"}


class StoryError(Exception):
    pass


def _read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


AMENDABLE = ("nodes", "characters", "flags", "places", "arcs")
NAME_FIELDS = ("name", "short", "full", "title")      # how a character is called in text


def load(path):
    """Load a story file and every file it includes, merged into one dict."""
    data = _read_json(path)
    if data.get("format") != FORMAT:
        raise StoryError("%s is not a storykit file" % path)
    data.setdefault("nodes", {})
    for section in ("stats", "sets", "effects", "flags", "places", "characters", "arcs"):
        data.setdefault(section, {})
    base = os.path.dirname(os.path.abspath(path))
    amends = []
    for include in data.get("include", []):
        part = _read_json(os.path.join(base, include))
        for section in ("stats", "sets", "effects", "flags", "places", "characters", "arcs", "nodes"):
            for key, value in part.get(section, {}).items():
                if key in data[section]:
                    raise StoryError("%s: %s %r is defined twice" % (include, section, key))
                if section == "nodes":
                    value.setdefault("file", include)
                data[section][key] = value
        for section, entries in part.get("amend", {}).items():
            if section not in AMENDABLE:
                raise StoryError("%s: cannot amend %r" % (include, section))
            for key, changes in entries.items():
                amends.append((include, section, key, changes))
    # An amendment rewrites fields of something defined in another file (new text
    # for an imported chapter, a repaired condition) without touching that file.
    # The fields it replaced are kept under "amended", so the map can show both.
    for include, section, key, changes in amends:
        entry = data[section].get(key)
        if entry is None:
            raise StoryError("%s: amends unknown %s %r" % (include, section[:-1], key))
        before = {k: entry.get(k) for k in changes if k in entry}
        entry.update(changes)
        entry.setdefault("amended", []).append({"file": include, "fields": sorted(changes), "was": before})
    # Characters who live across the saga are named once, in the saga file.
    if data.get("saga"):
        saga = _read_json(os.path.join(base, data["saga"]))
        for cid, info in saga.get("characters", {}).items():
            here = data["characters"].get(cid)
            if here is None:
                continue
            for field in NAME_FIELDS:
                if field in info:
                    if field in here:
                        raise StoryError("character %r: %s is set in %s and in the saga file; keep it in one place"
                                         % (cid, field, path))
                    here[field] = info[field]
            here["saga"] = True
        # errands between the eras, renamed flags and what each version of a part understands
        for section in ("errands", "aliases", "features", "fixed_points"):
            data[section] = saga.get(section, {})
    data.setdefault("errands", {})
    data.setdefault("aliases", {})
    data.setdefault("features", {})
    data.setdefault("fixed_points", [])
    data["path"] = path
    return data


def load_saga(path):
    """Load a saga file (the trilogy) and the story files of the parts that exist."""
    saga = _read_json(path)
    if saga.get("format") != SAGA_FORMAT:
        raise StoryError("%s is not a storykit saga file" % path)
    base = os.path.dirname(os.path.abspath(path))
    saga["stories"] = {}
    for part in saga.get("parts", []):
        file = part.get("file")
        if file and os.path.exists(os.path.join(base, file)):
            saga["stories"][part["game"]] = load(os.path.join(base, file))
    saga["path"] = path
    return saga


# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------

def as_list(value):
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


class State:
    """What a condition is evaluated against: a snapshot of one moment of play.

    stats   {"money": 1200, "combat_victories.pirate": 3, ...}
    sets    {"researched": [...], "items": [...]}
    flags   set of story flags that are on
    done    set of node ids that are complete
    act     current act (chapter number); turn; place; place_type
    visitors  captain records that crossed over from other games
    past      the ledger the captain came with: {era: {"flags", "ending", ...}} (record.py)
    errands   {errand id: "open" | "done"}
    """

    def __init__(self, stats=None, sets=None, flags=None, done=None, act=1, turn=0,
                 place=None, place_type=None, visitors=None, player=None, venue=None, origin=None,
                 chapter=None, done_at=None, past=None, errands=None):
        self.stats = dict(stats or {})
        self.sets = {k: set(v) for k, v in (sets or {}).items()}
        self.flags = set(flags or ())
        self.done = set(done or ())
        self.act = act
        self.turn = turn
        self.place = place
        self.place_type = place_type
        self.visitors = list(visitors or [])
        self.player = player
        self.venue = venue
        self.origin = origin
        self.chapter = chapter
        self.done_at = dict(done_at or {})
        self.past = dict(past or {})
        self.errands = dict(errands or {})

    @classmethod
    def from_snapshot(cls, snap):
        return cls(snap.get("stats"), snap.get("sets"), snap.get("flags"), snap.get("done"),
                   snap.get("act", 1), snap.get("turn", 0), snap.get("place"), snap.get("place_type"),
                   snap.get("visitors"), snap.get("player"), snap.get("venue"), snap.get("origin"),
                   snap.get("chapter"), snap.get("done_at"), snap.get("past"), snap.get("errands"))


def _threshold(value, wanted):
    if isinstance(wanted, dict):
        if "min" in wanted and value < wanted["min"]:
            return False
        if "max" in wanted and value > wanted["max"]:
            return False
        return True
    return value >= wanted


def check(cond, state, unknown="fail"):
    """True when `cond` holds in `state`.

    unknown: what an opaque {"code": ...} condition counts as: "fail", "pass" or "raise".
    """
    if not cond:
        return True
    if isinstance(cond, list):
        return all(check(c, state, unknown) for c in cond)
    for key, want in cond.items():
        if key.startswith("_"):
            continue
        if key == "all":
            ok = all(check(c, state, unknown) for c in want)
        elif key == "any":
            ok = any(check(c, state, unknown) for c in want)
        elif key == "not":
            ok = not check(want, state, unknown)
        elif key == "flag":
            ok = all(f in state.flags for f in as_list(want))
        elif key == "not_flag":
            ok = not any(f in state.flags for f in as_list(want))
        elif key == "done":
            ok = all(n in state.done for n in as_list(want))
        elif key == "done_any":
            ok = any(n in state.done for n in as_list(want))
        elif key == "not_done":
            ok = not any(n in state.done for n in as_list(want))
        elif key == "since":
            ok = all(n in state.done and state.turn - state.done_at.get(n, -10 ** 9) >= turns
                     for n, turns in want.items())
        elif key == "act_min":
            ok = state.act >= want
        elif key == "act_max":
            ok = state.act <= want
        elif key == "turn_min":
            ok = state.turn >= want
        elif key == "turn_max":
            ok = state.turn <= want
        elif key == "at":
            ok = state.place in as_list(want)
        elif key == "at_type":
            ok = state.place_type in as_list(want)
        elif key == "has":
            ok = all(set(as_list(items)) <= state.sets.get(name, set()) for name, items in want.items())
        elif key == "visiting_captain":
            ok = any(visitor_matches(v, want, state.player) for v in state.visitors)
        elif key == "player_origin":
            ok = state.origin is not None and visitor_matches(state.origin, want)
        elif key == "venue":
            ok = state.venue in as_list(want)
        elif key == "chapter":
            ok = state.chapter in as_list(want)
        elif key == "past":
            ok = captain_record.past_holds(state.past, want)
        elif key == "errand":
            ok = captain_record.errands_hold(state.errands, want)
        elif key == "code":
            if unknown == "raise":
                raise StoryError("opaque condition: %s" % want)
            ok = unknown == "pass"
        else:
            ok = _threshold(state.stats.get(key, 0), want)
        if not ok:
            return False
    return True


def visitor_matches(record, want, player=None):
    """Does a captain record match {"game", "ending", "flag", "same_name"}?

    same_name: true when the record carries the current captain's own name
    (the same captain grown old), false when it is someone else's.
    """
    if want.get("game") and record.get("origin", {}).get("game") != want["game"]:
        return False
    if "same_name" in want:
        same = player is not None and str(record.get("name", "")).strip().lower() == str(player).strip().lower()
        if same != bool(want["same_name"]):
            return False
    story = record.get("story", {})
    if want.get("ending") and story.get("ending") != want["ending"]:
        return False
    if want.get("flag") and want["flag"] not in story.get("flags", []):
        return False
    return True


def texts_of(node):
    """Every piece of text a node shows: title, text, variants, choices."""
    out = []
    for value in [node.get("title")] + as_list(node.get("text")):
        if isinstance(value, str):
            out.append(value)
    for variant in node.get("variants") or []:
        out.extend(t for t in as_list(variant.get("text")) if isinstance(t, str))
    for choice in node.get("choices") or []:
        if isinstance(choice.get("say"), str):
            out.append(choice["say"])
    return out


def walk_condition(cond, visit, path=()):
    """Call visit(key, value, path) for every leaf of a condition."""
    if not cond:
        return
    if isinstance(cond, list):
        for c in cond:
            walk_condition(c, visit, path)
        return
    for key, want in cond.items():
        if key.startswith("_"):
            continue
        if key in ("all", "any"):
            for c in want:
                walk_condition(c, visit, path + (key,))
        elif key == "not":
            walk_condition(want, visit, path + ("not",))
        else:
            visit(key, want, path)


def apply(effects, state):
    """Apply effects to a State (used by the simulator)."""
    for key, value in (effects or {}).items():
        if key.startswith("_"):
            continue
        if key == "set":
            state.flags.update(as_list(value))
        elif key == "clear":
            state.flags.difference_update(as_list(value))
        elif key == "give":
            for name, items in value.items():
                state.sets.setdefault(name, set()).update(as_list(items))
        elif key == "errand":
            for eid in as_list(value):
                state.errands.setdefault(eid, "open")
        elif key == "errand_done":
            for eid in as_list(value):
                state.errands[eid] = "done"
        elif key in ("start", "spawn", "code"):
            pass
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            state.stats[key] = state.stats.get(key, 0) + value


# ---------------------------------------------------------------------------
# Indexes the tools share
# ---------------------------------------------------------------------------

def node_conditions(node):
    """Every condition attached to a node (its own and its choices')."""
    yield node.get("requires")
    for choice in node.get("choices", []):
        yield choice.get("requires")
    for variant in node.get("variants", []):
        yield variant.get("requires")


def node_effects(node):
    yield node.get("effects")
    for choice in node.get("choices", []):
        yield choice.get("effects")


def references(node):
    """Node ids a node points at, with how: [(kind, target)]."""
    out = []
    for nid in as_list(node.get("next")):
        out.append(("next", nid))
    if node.get("in"):
        out.append(("in", node["in"]))
    for cond in node_conditions(node):
        def visit(key, want, path, out=out):
            if key in ("done", "done_any", "not_done"):
                for nid in as_list(want):
                    out.append((key, nid))
            elif key == "since":
                for nid in want:
                    out.append(("done", nid))
        walk_condition(cond, visit)
    for effects in node_effects(node):
        for nid in as_list((effects or {}).get("start")):
            out.append(("start", nid))
    for choice in node.get("choices", []):
        for nid in as_list(choice.get("next")):
            out.append(("next", nid))
    return out


def flags_read(node):
    found = set()
    for cond in node_conditions(node):
        def visit(key, want, path):
            if key in ("flag", "not_flag"):
                found.update(as_list(want))
        walk_condition(cond, visit)
    return found


def past_flags_read(node):
    """Flags of other eras a node reads through {"past": ...}: {(era or None, flag)}."""
    found = set()
    for cond in node_conditions(node):
        def visit(key, want, path):
            if key == "past" and isinstance(want, dict):
                for f in as_list(want.get("flag")) + as_list(want.get("not_flag")):
                    found.add((want.get("era"), f))
        walk_condition(cond, visit)
    return found


def errands_of(node):
    """The errands a node gives ("errand") and finishes ("errand_done")."""
    given, done = set(), set()
    for effects in node_effects(node):
        given.update(as_list((effects or {}).get("errand")))
        done.update(as_list((effects or {}).get("errand_done")))
    return given, done


def flags_set(node):
    found = set()
    for effects in node_effects(node):
        found.update(as_list((effects or {}).get("set")))
    return found


def characters_of(node):
    return set(as_list(node.get("who")))


def act_of(story, node_id, _seen=None):
    """The act a node belongs to: its own `act`, its parent's, or its act_min."""
    node = story["nodes"].get(node_id, {})
    if "act" in node:
        return node["act"]
    if node.get("in") and node["in"] in story["nodes"] and node["in"] != node_id:
        seen = _seen or set()
        if node_id not in seen:
            seen.add(node_id)
            return act_of(story, node["in"], seen)
    found = []
    walk_condition(node.get("requires"), lambda k, v, p: found.append(v) if k == "act_min" else None)
    return max(found) if found else None


def text_of(node):
    text = node.get("text", "")
    return " ".join(text) if isinstance(text, list) else str(text)


def route_place(route, turn):
    """Where a character's route puts them on this turn: {"places": [...], "stay": turns at each,
    "start": turns already gone when the game begins}. None without a route."""
    places = (route or {}).get("places") or []
    if not places:
        return None
    stay = max(1, int(route.get("stay", 1)))
    return places[((turn + int(route.get("start", 0))) // stay) % len(places)]
