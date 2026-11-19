#!/usr/bin/env python3
"""The captain's history across the parts (storykit/record.py, written into cargo.py): the id,
log, line and the captain's own time carried on; the ledger of eras; errands, and Cargo 1's
own errand (level nine's thirteenth line); keys from newer games kept; a record from 1.2.1
joined back up; notes for versions too old; hostile histories cleaned.

    python3 tools/history.py [cargo.py]
"""
import json, os, random, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["CARGO_SAGA_HOME"] = tempfile.mkdtemp(prefix="cargo-history-")
import headless  # noqa: E402
from make_captain import make  # noqa: E402

cargo = headless.load(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "cargo.py"))
history = cargo.history
problems = []


def expect(ok, what):
    if not ok:
        problems.append(what)


def sealed(record):
    record["check"] = cargo._captain_check(record)
    return record


def from_cargo3(errand_state="open", needs="1.3.0", extra=None):
    """A record as Cargo 3 writes it: history, an errand for 2420, keys Cargo 1 does not know."""
    record = make(cargo, "cargo3", "Vega Orl", rank="Able Hand", flags=["the_pod"], turns=40, version="3.0.0")
    record.update({"id": "C1-0000BEEF", "line": "L-00000003", "parent": "L-00000002", "own_time": 300,
                   "ledger": {"cargo2": {"flags": ["vault_word_known"], "ending": "trade", "version": "2.3.0",
                                         "line": "L-00000002", "turns": 260}},
                   "errands": [{"id": "thirteenth_line", "from": "cargo3", "to": "cargo1", "state": errand_state,
                                "needs": needs, "title": "a name for the thirteenth line", "line": "L-00000003"}],
                   "achievements": ["no_more_deadheads"], "standing": {"hansa": 10, "mandate": 0, "concord": 0},
                   "devices": {"procrustes_analyzer": {"from": "the Kraal vault"}}})
    record.update(extra or {})
    return cargo.clean_captain(sealed(record))


def start_as(record):
    io = headless.IO()
    headless.patch(cargo, io)
    io.feed(["1", "2"] + [""] * 20)
    with headless.quiet() as out:
        game = cargo.Game(player_name=record["name"], origin=record)
    return game, io, " ".join(out.getvalue().replace("│", " ").replace("║", " ").split())


# ---- the record a new game writes ---------------------------------------------------------------
game, io = headless.new_game(cargo)
game.turn = 25
record = game.captain_record()
expect(record["line"].startswith("L-") and record["parent"] == "" and record["own_time"] == 25,
       "a fresh captain's record: a line of its own, no parent, its own time: %s" % {k: record[k] for k in ("line", "parent", "own_time")})
expect(set(record["ledger"]) == {"cargo1"} and record["ledger"]["cargo1"]["version"] == cargo.VERSION
       and record["ledger"]["cargo1"]["turns"] == 25, "the ledger holds this part: %s" % record["ledger"])
expect(record["errands"] == [], "no errands yet")

# ---- a captain from 2533 on an errand -------------------------------------------------------------
came = from_cargo3()
expect(came["devices"] == {"procrustes_analyzer": {"from": "the Kraal vault"}} and came["achievements"] == ["no_more_deadheads"],
       "keys Cargo 1 does not know are kept as they came")
game, io, text = start_as(came)
expect(game.captain_id == "C1-0000BEEF" and game.captain_start["parent"] == "L-00000003"
       and game.captain_start["line"] != "L-00000003", "the same captain, on a new line from the record's")
expect("intro.errand" in game.story.done and "a hundred and thirteen years early" in text,
       "a Cargo 3 captain on an errand gets the errand's intro")
expect(set(game.captain_start["ledger"]) == {"cargo2", "cargo3"} and
       "the_pod" in game.captain_start["ledger"]["cargo3"]["flags"], "the past: 2460 and 2533 as the captain left them")
snap = game.story.snapshot()
expect(game.story.check({"past": {"era": "cargo2", "flag": "vault_word_known"}}, snap)
       and not game.story.check({"past": {"era": "cargo2", "flag": "nothing"}}, snap)
       and game.story.check({"errand": {"thirteenth_line": "open"}}, snap)
       and game.story.check({"errand": {"vault_word": "none"}}, snap), "past and errand conditions")
# level nine: the plaque
plaque = cargo.story_data()["nodes"]["gamma.plaque"]
game.current_location = next(l for l in game.locations if l.name == "Gamma")
game.story_manager.story_states["saved_level_nine"] = True
game.story.done["gamma.collapse"] = 0
game.turn = 2
expect(not game.story.check(game.story.requires_of(plaque), game.story.snapshot()), "the plaque is cut a few turns after the rescue")
game.turn = 5
expect(game.story.check(game.story.requires_of(plaque), game.story.snapshot()), "then the plaque and its thirteenth line")
io.queue[:] = ["1"] + [""] * 10
with headless.quiet() as out:
    game.story.play("gamma.plaque")
expect(game.story_manager.story_states.get("thirteenth_name") and history.errand_state(game.errands, "thirteenth_line") == "done",
       "giving the name finishes the errand")
expect(game.player_name in out.getvalue(), "and the name is cut into the line")
game.turn = 60
record = game.captain_record()
expect(record["id"] == "C1-0000BEEF" and record["own_time"] == 360 and record["parent"] == "L-00000003",
       "the record goes on: same id, own time 300 + 60: %s" % record["own_time"])
expect(set(record["ledger"]) == {"cargo1", "cargo2", "cargo3"} and "thirteenth_name" in record["ledger"]["cargo1"]["flags"],
       "the ledger now has 2420, with the name on the plaque")
expect(record["errands"][0]["state"] == "done", "the errand travels back done")
expect(record["devices"] == {"procrustes_analyzer": {"from": "the Kraal vault"}} and record["standing"]["hansa"] == 10,
       "keys from newer games are written out again")
expect(cargo.clean_captain(json.loads(json.dumps(record))) == record, "the record reads back as it was written")
expect([e["game"] for e in record["log"]][-1] == "cargo1" and len(record["log"]) == 2, "the log goes on")
# a captain with no errand gets the plain intro, and no plaque
game, io, text = start_as(from_cargo3(errand_state="done"))
expect("intro.from_cargo3" in game.story.done, "a Cargo 3 captain with no errand open: the plain intro")

# ---- a version too old for an errand ---------------------------------------------------------------
old = from_cargo3(needs="1.4.0")
notes = history.import_notes(old, "cargo1", cargo.VERSION, cargo.story_data()["features"])
expect(len(notes) == 1 and "1.4.0 or newer" in notes[0] and "update" in notes[0], "an errand for a newer Cargo 1 is named at import")
game, io, text = start_as(old)
expect("intro.from_cargo3" in game.story.done or "intro.errand" in game.story.done, "and the game still starts")
expect(any("1.4.0" in n for n in history.export_notes(game.errands, "cargo1", cargo.VERSION)), "and is named again at export")
notes = history.import_notes(from_cargo3(), "cargo1", cargo.VERSION, cargo.story_data()["features"])
expect(notes == ["An errand from 2533 waits here: a name for the thirteenth line."], "a doable errand is named: %s" % notes)

# ---- a record that went through Cargo 1.2.1 ------------------------------------------------------------
older = make(cargo, "cargo1", "Vega Orl", rank="Commodore", ending="trade", flags=["hansa_founder"], turns=500, version="1.2.1")
expect(set(older) >= {"ledger", "errands"} and older["ledger"] == {} and older["errands"] == [], "1.2.1's record has no history")
newer = from_cargo3()
features = cargo.story_data()["features"]
expect(history.join_candidates(older, [older, newer], features) == [newer], "the newer record of the same captain is found")
expect(history.join_candidates(newer, [older, newer], features) == [], "a record that kept its history needs no join")
joined = history.join(older, newer)
expect(joined["id"] == newer["id"] and joined["own_time"] == 300 + 500 and joined["errands"] == newer["errands"],
       "joined: the newer id, time and errands")
start = history.start_from(joined, random.Random(1), known=cargo.CAPTAIN_KEYS)
expect(set(start["ledger"]) == {"cargo1", "cargo2", "cargo3"} and "hansa_founder" in start["ledger"]["cargo1"]["flags"],
       "and 1.2.1's own era on top of the newer ledger")
expect("1.2.1" in history.joined_note(older, features) and "1.3.0" in history.joined_note(older, features),
       "the note says which version dropped it and which keeps it")
cargo.write_json(os.path.join(cargo.captain_folder(), "vega-cargo3.captain"), newer)
cargo.write_json(os.path.join(cargo.captain_folder(), "vega-cargo1.captain"), older)
io = headless.IO()
headless.patch(cargo, io)
io.feed(["yes"])
with headless.quiet() as out:
    record = cargo.join_and_tell(older)
expect(record["id"] == newer["id"] and "joined" in out.getvalue(), "starting as the 1.2.1 record offers the join")

# ---- other lines of the same captain may visit; this very record may not -----------------------------------
game, io, text = start_as(from_cargo3())
mine = game.captain_record()
expect("own record" in game.receive_captain(mine), "a captain cannot take in this very record")
other = dict(mine)
other["line"] = "L-0000FFFF"
expect("crossed" in game.receive_captain(sealed(other)), "the same captain from another line can cross over")

# ---- hostile histories ---------------------------------------------------------------------------------------
junk = make(cargo, "cargo3", "Junk", version="3.0.0")
junk.update({"line": "x" * 500, "own_time": -5, "ledger": {"cargo1": "nope", "cargo9": {}, "cargo2": {"flags": ["a"] * 5000}},
             "errands": [{"id": "", "to": "cargo1"}, {"id": "e", "to": "mars"}, "x", {"id": "ok", "to": "cargo2", "state": "weird"}] * 10,
             "big": "x" * 20000, "deep": {"a": {"b": {"c": {"d": {"e": {"f": {"g": 1}}}}}}}, "bad key!": 1,
             **{"k%d" % i: i for i in range(40)}})
clean = cargo.clean_captain(sealed(junk))
expect(len(clean["line"]) <= 16 and clean["own_time"] == 0 and set(clean["ledger"]) == {"cargo2"}
       and len(clean["ledger"]["cargo2"]["flags"]) == 200, "a hostile ledger is cut down: %s" % list(clean["ledger"]))
expect(clean["errands"] == [{"id": "ok", "from": "", "to": "cargo2", "state": "open", "needs": "", "title": "", "line": ""}],
       "hostile errands are dropped or mended: %s" % clean["errands"][:2])
kept = [k for k in clean if k.startswith("k")]
expect("big" not in clean and "deep" not in clean and "bad key!" not in clean and len(kept) <= history.KEPT_MOST,
       "kept keys stay small and plain")
game, io, text = start_as(clean)
expect(game.captain_record()["format"] == "cargo-captain", "and a game still starts and writes its record")

# ---- saves from 1.2.1, and damaged history in a save -------------------------------------------------------------
game, io, text = start_as(from_cargo3())
del game.captain_start
del game.errands
with headless.quiet():
    game.save_game("old")
    loaded = cargo.load_game("old")
expect(isinstance(loaded.captain_start, dict) and set(loaded.captain_start["ledger"]) == {"cargo2", "cargo3"},
       "a save from before 1.3 gets a history, from the record it began as")
loaded.captain_start = "rubbish"
loaded.errands = [{"id": "x"}, 5]
loaded.bring_up_to_date()
expect(isinstance(loaded.captain_start, dict) and loaded.errands == [], "a damaged history in a save is mended")

# ---- versions and aliases -----------------------------------------------------------------------------------
expect(history.at_least("1.3.0", "1.3.0") and history.at_least("3.0.0-dev", "3.0.0") and not history.at_least("1.2.1", "1.3.0")
       and history.at_least("1.10.0", "1.9.9") and not history.at_least("", "1.0.0"), "versions compare by number")
expect(sorted(history.with_aliases(["varga_friend"], {"varga_friend": "convoy_friend"})) == ["convoy_friend", "varga_friend"]
       and sorted(history.with_aliases(["convoy_friend"], {"varga_friend": "convoy_friend"})) == ["convoy_friend", "varga_friend"],
       "a renamed flag reads and writes under both names")

for problem in problems:
    print("FAIL", problem)
print("history: %s" % ("ok" if not problems else "%d problems" % len(problems)))
sys.exit(1 if problems else 0)
