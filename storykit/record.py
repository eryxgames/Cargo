"""The captain's record across the parts of the saga: the history it carries.

A captain record (format "cargo-captain", version 1) carries one captain between Cargo 1, 2 and
3. Each game writes the record of the part it is; this module adds the history that goes
along with every part the captain played:

- the captain's id and log, kept from part to part;
- lines (many worlds): every game started from a record begins a new line, branching from the
  record's. A save belongs to its line for good, so nothing done later rewrites it;
- the captain's own time (relativity): the turns lived, added up over every part; it only grows,
  whatever year the dock clocks say;
- the ledger: for each part (era), what this captain left there on this line: the flags, the
  ending, the game's version and line. A later part reads the past as the captain left it, with
  the conditions {"past": ...};
- errands: tasks a part gives the captain for another era (story effects "errand" and
  "errand_done", conditions {"errand": ...}); the saga file defines them;
- keys from newer games, kept as they came, so a record that passes through an older game
  (from this version on) loses nothing a newer one wrote.

The record's format stays 1: everything here is optional, and games that do not know it drop it
(Cargo 1.2.1, the first published Cargo, does, without an error). What such a game loses can be
joined back from the newer record in the shared folder (join).

Standard library only, and no game code: Cargo 2 and 3 copy this file into their game package
(tools/sync_story.py), Cargo 1 writes it into cargo.py (tools/build_story.py). Change it here,
in the Cargo repository, and copy it again.
"""
import json

ERAS = ("cargo1", "cargo2", "cargo3")
ERA_YEARS = {"cargo1": "2420", "cargo2": "2460", "cargo3": "2533"}
ERA_TITLES = {"cargo1": "Cargo 1", "cargo2": "Cargo 2", "cargo3": "Cargo 3"}
ERRAND_STATES = ("open", "done")
HISTORY_KEYS = ("line", "parent", "own_time", "ledger", "errands")
KEPT_MOST = 16              # keys from newer games kept: at most this many,
KEPT_SIZE = 8000            # each at most this long as JSON,
KEPT_DEPTH = 6              # and nested at most this deep


def _text(value, limit):
    text = "".join(ch for ch in str(value if value is not None else "") if ch.isprintable() and ch != "\x1b")
    return text[:limit]


def _number(value, low=0, high=10 ** 9):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return low
    return max(low, min(high, int(value)))


def _texts(values, limit=32, most=200):
    if not isinstance(values, (list, tuple)):
        return []
    return [_text(v, limit) for v in list(values)[:most] if isinstance(v, str)]


def _list(value):
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


# ---- versions ---------------------------------------------------------------------------------

def version_tuple(value):
    """'1.3.0' -> (1, 3, 0); '3.0.0-dev' counts as 3.0.0; anything unreadable as 0.0.0."""
    parts = []
    for piece in str(value or "").split("-")[0].split(".")[:3]:
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def at_least(version, need):
    return version_tuple(version) >= version_tuple(need)


# ---- cleaning what comes from outside -------------------------------------------------------------

def clean_era(era):
    era = era if isinstance(era, dict) else {}
    return {"flags": _texts(era.get("flags")), "ending": _text(era.get("ending", ""), 24),
            "version": _text(era.get("version", ""), 16), "line": _text(era.get("line", ""), 16),
            "turns": _number(era.get("turns"), 0, 10 ** 7)}


def clean_errand(errand):
    if not isinstance(errand, dict):
        return None
    eid = _text(errand.get("id", ""), 32)
    to = _text(errand.get("to", ""), 12)
    if not eid or to not in ERAS:
        return None
    came = _text(errand.get("from", ""), 12)
    state = errand.get("state") if errand.get("state") in ERRAND_STATES else "open"
    return {"id": eid, "from": came if came in ERAS else "", "to": to, "state": state,
            "needs": _text(errand.get("needs", ""), 16), "title": _text(errand.get("title", ""), 80),
            "line": _text(errand.get("line", ""), 16)}


def clean_history(record):
    """The record's history, cleaned: nothing in it is trusted. A record from a game that keeps
    no history gets an empty one."""
    ledger = record.get("ledger") if isinstance(record.get("ledger"), dict) else {}
    errands = record.get("errands") if isinstance(record.get("errands"), list) else []
    cleaned = [e for e in (clean_errand(e) for e in errands[:24]) if e]
    seen, unique = set(), []
    for errand in cleaned:
        if errand["id"] not in seen:
            seen.add(errand["id"])
            unique.append(errand)
    return {"line": _text(record.get("line", ""), 16), "parent": _text(record.get("parent", ""), 16),
            "own_time": _number(record.get("own_time"), 0, 10 ** 7),
            "ledger": {era: clean_era(ledger[era]) for era in ERAS if isinstance(ledger.get(era), dict)},
            "errands": unique}


def _depth(value, level=0):
    if level > KEPT_DEPTH:
        return level
    if isinstance(value, dict):
        return max([_depth(v, level + 1) for v in value.values()] or [level])
    if isinstance(value, list):
        return max([_depth(v, level + 1) for v in value] or [level])
    return level


def kept_keys(record, known):
    """Keys a newer game wrote and this one does not know: kept as they came (JSON only, within
    limits), to be written out again."""
    kept = {}
    for key, value in record.items():
        if key in known or key in HISTORY_KEYS or not isinstance(key, str) or not 0 < len(key) <= 32:
            continue
        if not key.replace("_", "").replace("-", "").isalnum():
            continue
        try:
            blob = json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError, RecursionError):
            continue
        if len(blob) > KEPT_SIZE or _depth(value) > KEPT_DEPTH:
            continue
        kept[key] = json.loads(blob)
        if len(kept) >= KEPT_MOST:
            break
    return kept


# ---- aliases: flags that were renamed -------------------------------------------------------------

def with_aliases(flags, aliases):
    """Flags with their other names: a renamed flag reads under either name, and is written
    under both, so older and newer games each find the name they know."""
    out = list(flags)
    have = set(out)
    for old, new in (aliases or {}).items():
        if old in have and new not in have:
            out.append(new)
            have.add(new)
        elif new in have and old not in have:
            out.append(old)
            have.add(old)
    return out


# ---- the ledger --------------------------------------------------------------------------------

def own_era(record):
    """The part a record was written in, and that era as its own story tells it: always the
    latest word on that era."""
    origin = record.get("origin") if isinstance(record.get("origin"), dict) else {}
    story = record.get("story") if isinstance(record.get("story"), dict) else {}
    career = record.get("career") if isinstance(record.get("career"), dict) else {}
    return origin.get("game"), clean_era({"flags": story.get("flags"), "ending": story.get("ending", ""),
                                          "version": origin.get("version", ""), "line": record.get("line", ""),
                                          "turns": career.get("turns")})


def ledger_of(record, aliases=None):
    """Every era this captain has left a mark on, the record's own era from its story."""
    ledger = {era: dict(entry) for era, entry in clean_history(record)["ledger"].items()}
    game, era = own_era(record)
    if game in ERAS:
        ledger[game] = era
    for entry in ledger.values():
        entry["flags"] = with_aliases(entry["flags"], aliases)
    return ledger


def new_line(rng):
    return "L-%08X" % rng.getrandbits(32)


def start_from(record, rng, known=(), aliases=None):
    """What a new game takes from the record it begins as (None: a fresh captain): the id and
    log, a new line branching from the record's, the captain's own time so far, the ledger,
    the errands, and the keys it does not know."""
    if record is None:
        return {"id": None, "log": [], "line": new_line(rng), "parent": "", "own_time": 0, "ledger": {},
                "errands": [], "kept": {}}
    history = clean_history(record)
    career = record.get("career") if isinstance(record.get("career"), dict) else {}
    own = history["own_time"] or _number(career.get("turns"), 0, 10 ** 7)
    return {"id": _text(record.get("id", ""), 16) or None,
            "log": [dict(e) for e in (record.get("log") or []) if isinstance(e, dict)][-20:],
            "line": new_line(rng), "parent": history["line"], "own_time": own,
            "ledger": ledger_of(record, aliases), "errands": [dict(e) for e in history["errands"]],
            "kept": kept_keys(record, known)}


def write_history(record, start, game, version, turns, flags, ending, errands):
    """Fill in the history of a record a game is writing: this part's era replaces the one
    the captain came with, the others stay."""
    ledger = {era: dict(entry) for era, entry in start["ledger"].items()}
    ledger[game] = clean_era({"flags": flags, "ending": ending, "version": version, "line": start["line"],
                              "turns": turns})
    record["line"] = start["line"]
    record["parent"] = start["parent"]
    record["own_time"] = _number(start["own_time"] + _number(turns, 0, 10 ** 7), 0, 10 ** 7)
    record["ledger"] = ledger
    record["errands"] = [e for e in (clean_errand(e) for e in errands) if e]
    for key, value in start.get("kept", {}).items():
        record.setdefault(key, value)
    return record


# ---- errands -------------------------------------------------------------------------------------

def errand_state(errands, eid):
    for errand in errands or []:
        if errand.get("id") == eid:
            return errand.get("state", "open")
    return "none"


def errand_states(errands):
    return {e["id"]: e.get("state", "open") for e in errands or [] if e.get("id")}


def open_errand(errands, eid, definitions, game, line):
    """The story gives the captain an errand (effect "errand"): once only."""
    if errand_state(errands, eid) != "none":
        return False
    info = (definitions or {}).get(eid) or {}
    errands.append(clean_errand({"id": eid, "from": game, "to": info.get("to", ""), "state": "open",
                                 "needs": info.get("needs", ""), "title": info.get("title", eid), "line": line})
                   or {"id": eid, "from": game, "to": "", "state": "open", "needs": "", "title": eid, "line": line})
    return True


def finish_errand(errands, eid, definitions=None, game="", line=""):
    """The errand is done here (effect "errand_done"). An errand the captain was never given
    (a fresh captain stumbling on it) is recorded as done too."""
    for errand in errands:
        if errand.get("id") == eid:
            if errand.get("state") == "done":
                return False
            errand["state"] = "done"
            return True
    info = (definitions or {}).get(eid) or {}
    errands.append({"id": eid, "from": info.get("from", ""), "to": info.get("to", game), "state": "done",
                    "needs": info.get("needs", ""), "title": info.get("title", eid), "line": line})
    return True


# ---- conditions -------------------------------------------------------------------------------------

def past_holds(ledger, want):
    """{"past": {"era": "cargo1", "flag": "x", "not_flag": "y", "ending": "trade"}}: what the
    captain left in that era (with no era: in any era)."""
    want = want if isinstance(want, dict) else {}
    eras = [want["era"]] if want.get("era") else list(ERAS)
    for era in eras:
        entry = (ledger or {}).get(era)
        if not entry:
            continue
        flags = set(entry.get("flags") or [])
        if not all(f in flags for f in _list(want.get("flag"))):
            continue
        if any(f in flags for f in _list(want.get("not_flag"))):
            continue
        if want.get("ending") and entry.get("ending") not in _list(want["ending"]):
            continue
        return True
    return False


def errands_hold(states, want):
    """{"errand": {"plaque": "open"}}: each errand in that state ("none", "open", "done", or a
    list of them)."""
    if isinstance(want, str):
        want = {want: "open"}
    for eid, wanted in (want or {}).items():
        if (states or {}).get(eid, "none") not in _list(wanted):
            return False
    return True


# ---- telling the player ---------------------------------------------------------------------------

def keeps_history(record, features):
    """Did the game that wrote this record keep a captain's history? (Older games drop it.)"""
    origin = record.get("origin") if isinstance(record.get("origin"), dict) else {}
    need = ((features or {}).get("ledger") or {}).get(origin.get("game"))
    return not need or at_least(origin.get("version", ""), need)


def join_candidates(record, others, features):
    """When a record comes from a game that drops history, the captain's newer records in the
    shared folder that kept it (same name), newest first as given."""
    if keeps_history(record, features):
        return []
    name = str(record.get("name", "")).strip().lower()
    return [other for other in others
            if other is not record and str(other.get("name", "")).strip().lower() == name
            and (other.get("ledger") or other.get("errands")) and keeps_history(other, features)]


def join(record, newer):
    """A record from a game that dropped the captain's history, joined with the newer record it
    came from: the newer one's id, log, ledger, errands and time, this record's own era on top."""
    joined = dict(record)
    history = clean_history(newer)
    career = record.get("career") if isinstance(record.get("career"), dict) else {}
    joined["id"] = newer.get("id") or record.get("id")
    joined["ledger"] = ledger_of(newer)
    joined["errands"] = history["errands"]
    joined["line"] = record.get("line") or history["line"]
    joined["parent"] = history["line"]
    joined["own_time"] = history["own_time"] + _number(career.get("turns"), 0, 10 ** 7)
    joined["log"] = [e for e in (newer.get("log") or []) if isinstance(e, dict)] + \
        [e for e in (record.get("log") or []) if isinstance(e, dict)]
    joined["log"] = joined["log"][-20:]
    return joined


def import_notes(record, game, version, features=None):
    """Plain lines for a player starting a game as this captain: errands that wait here, and
    errands this version is too old for."""
    notes = []
    for errand in clean_history(record)["errands"]:
        if errand["state"] != "open" or errand["to"] != game:
            continue
        title = errand["title"] or errand["id"]
        if errand["needs"] and not at_least(version, errand["needs"]):
            notes.append("Your record carries an errand for %s %s or newer: %s. This is %s %s; the errand "
                         "stays in your record until you update." % (ERA_TITLES[game], errand["needs"], title,
                                                                    ERA_TITLES[game], version))
        else:
            came = ERA_YEARS.get(errand["from"], "another time")
            notes.append("An errand from %s waits here: %s." % (came, title))
    return notes


def joined_note(record, features=None):
    origin = record.get("origin") if isinstance(record.get("origin"), dict) else {}
    game = origin.get("game")
    need = ((features or {}).get("ledger") or {}).get(game, "")
    return ("This record came back from %s %s, which keeps only its own part of a captain's history. It "
            "has been joined with your newer record; %s %s and newer keep all of it."
            % (ERA_TITLES.get(game, game), origin.get("version", "?"), ERA_TITLES.get(game, game), need))


def export_notes(errands, game, version):
    """Errands for this part that this version could not take on: they stay in the record."""
    notes = []
    for errand in errands or []:
        if errand.get("state") == "open" and errand.get("to") == game and errand.get("needs") \
                and not at_least(version, errand["needs"]):
            notes.append("Your record still carries an errand for %s %s or newer: %s. Update %s to take it on."
                         % (ERA_TITLES[game], errand["needs"], errand.get("title") or errand["id"], ERA_TITLES[game]))
    return notes
