#!/usr/bin/env python3
"""One captain through the whole saga, with the three games' real code: a Cargo 3 captain takes
three errands to the past, does the plaque and the samples in Cargo 1 and the vault word in
Cargo 2, and comes back to a new Cargo 3 that remembers. The record goes from game to game through the shared
captain folder, as it does for a player. A second trip goes through the published Cargo 1.2.1
(from the git tag) and is joined back up.

    python3 tools/saga_trip.py ../Cargo-2 ../Cargo-3

Each game runs in its own process (Cargo 2 and 3 are both a package called `game`). Without
the two checkouts the trip is skipped.
"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CARGO1 = os.path.dirname(HERE)
problems = []
played = [0]


def expect(ok, what):
    if not ok:
        problems.append(what)
        print("FAIL", what)


PRELUDE = r'''
import json, os, sys
sys.path.insert(0, "tools")
import headless
from headless import IO, patch, quiet
LOAD = %r
cargo = headless.load(LOAD)
io = IO()
patch(cargo, io)

def begin(path, answers=("1", "2")):
    rec = cargo.read_captain_file(path)
    io.queue[:] = list(answers) + [""] * 20
    with quiet() as out:
        game = cargo.Game(player_name=rec["name"], origin=rec)
    io.queue.clear()
    return game, " ".join(out.getvalue().replace("│", " ").replace("║", " ").split())

def at(game, place):
    game.current_location = next(loc for loc in game.locations if loc.name == place)

def play(game, nid, answer="1", place=None):
    if place:
        at(game, place)
    io.queue[:] = [answer] + [""] * 10
    with quiet() as out:
        game.story.play(nid)
    return " ".join(out.getvalue().replace("│", " ").replace("║", " ").split())

def done(result):
    print("RESULT " + json.dumps(result))
'''


def run(repo, load, body, home):
    env = dict(os.environ, CARGO_SAGA_HOME=home, CARGO_SOUND="0", PYTHONHASHSEED="0")
    code = (PRELUDE % load) + body
    proc = subprocess.run([sys.executable, "-c", code], cwd=repo, env=env, capture_output=True, text=True, timeout=300)
    played[0] += 1
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            return json.loads(line[7:])
    problems.append("%s crashed: %s" % (os.path.basename(repo), (proc.stderr or proc.stdout)[-800:]))
    print("FAIL", problems[-1])
    return None


def main(cargo2, cargo3):
    home = tempfile.mkdtemp(prefix="cargo-saga-trip-")

    # ---- 2533: a fresh captain, three errands --------------------------------------------------
    a = run(cargo3, "game/world.py", r'''
io.queue[:] = ["1", "2", "Tester"] + [""] * 10
with quiet():
    game = cargo.Game()
play(game, "opening.pod")
play(game, "hall.first")
play(game, "sight.gamma.plaque", "1", "Gamma")
game.story_manager.story_states["first_friend"] = True
play(game, "sight.delta.conte", "1", "Delta")
play(game, "sight.epsilon.notes", "1", "Epsilon")
game.turn = 30
path, _ = game.export_captain()
done({"path": path, "id": game.captain_id, "line": game.captain_start["line"],
      "errands": {e["id"]: e["state"] for e in game.errands}})
''', home)
    if not a:
        return
    expect(a["errands"] == {"thirteenth_line": "open", "vault_word": "open", "vertex_array": "open"},
           "2533: three errands open: %s" % a["errands"])

    # ---- 2420, Cargo 1: the plaque --------------------------------------------------------------------
    b = run(CARGO1, "cargo.py", r'''
game, text = begin(%r)
intro = sorted(n for n in game.story.done if n.startswith("intro"))
game.story_manager.story_states["saved_level_nine"] = True
game.story.done["gamma.collapse"] = 0
game.turn = 5
at(game, "Gamma")
plaque = play(game, "gamma.plaque", "1")
game.story_manager.story_states["carried_the_samples"] = True
game.current_location = next(l for l in game.locations + game.hidden_locations["ResearchColony"]
                             if l.name == "Stellar Institute")
vertex = play(game, "trail.vertex")
game.turn = 120
path, _ = game.export_captain()
done({"path": path, "id": game.captain_id, "intro": intro, "plaque": plaque, "vertex": vertex, "text": text,
      "line": game.captain_start["line"],
      "parent": game.captain_start["parent"], "errands": {e["id"]: e["state"] for e in game.errands}})
''' % a["path"], home)
    if not b:
        return
    expect(b["id"] == a["id"] and b["parent"] == a["line"], "2420: the same captain, on a line from 2533's")
    expect(b["intro"] == ["intro.errand"] and "two promises to keep" in b["text"] and "Tester" in b["plaque"],
           "2420: one opening for two errands, and the name cut")
    expect("For T.K." in b["vertex"], "2420: the samples measured before the fire")
    expect(b["errands"] == {"thirteenth_line": "done", "vault_word": "open", "vertex_array": "done"},
           "2420: the plaque and the samples done, the vault still open")

    # ---- 2460, Cargo 2: the vault word (the record now comes from Cargo 1) ---------------------------------
    c = run(cargo2, "game/world.py", r'''
game, text = begin(%r)
snap = game.story.snapshot()
thought = game.story.check(cargo.story_data()["nodes"]["thought.vault_word"]["requires"], snap)
game.turn = 14
play(game, "sleeper.wakes", "1", "Delta")
game.turn = 17
vault = play(game, "sleeper.vault", "3", "Delta")
game.turn = 80
path, _ = game.export_captain()
done({"path": path, "id": game.captain_id, "thought": thought, "vault": vault, "line": game.captain_start["line"],
      "parent": game.captain_start["parent"], "errands": {e["id"]: e["state"] for e in game.errands}})
''' % b["path"], home)
    if not c:
        return
    expect(c["id"] == a["id"] and c["parent"] == b["line"], "2460: the same captain, on a line from 2420's")
    expect(c["thought"] and "Tuesday" in c["vault"], "2460: reminded of the errand, and the word chosen")
    expect(c["errands"] == {"thirteenth_line": "done", "vault_word": "done", "vertex_array": "done"}, "2460: every errand done")

    # ---- 2533 again: the echoes ----------------------------------------------------------------------------
    d = run(cargo3, "game/world.py", r'''
game, text = begin(%r)
rec = cargo.read_captain_file(%r)
play(game, "opening.pod")
play(game, "hall.first")
plaque = play(game, "sight.gamma.plaque", "1", "Gamma")
game.story_manager.story_states["first_friend"] = True
conte = play(game, "sight.delta.conte", "1", "Delta")
notes = play(game, "sight.epsilon.notes", "1", "Epsilon")
done({"id": game.captain_id, "notes": notes, "array": game.person.items.get("vertex_array"), "parent": game.captain_start["parent"], "own_time": game.captain_start["own_time"],
      "eras": sorted(game.captain_start["ledger"]), "plaque": plaque, "conte": conte,
      "item": game.person.items.get("procrustes_analyzer"), "log": [e["game"] for e in rec["log"]]})
''' % (c["path"], c["path"]), home)
    if d:
        expect(d["id"] == a["id"] and d["parent"] == c["line"], "2533 again: the same captain, on a line from 2460's")
        expect(d["own_time"] == 30 + 120 + 80, "the captain's own time adds up: %s" % d["own_time"])
        expect(d["eras"] == ["cargo1", "cargo2", "cargo3"], "the past has every part: %s" % d["eras"])
        expect("It says Tester." in d["plaque"], "the plaque has the name")
        expect("It is a Tuesday" in d["conte"] and "The vault opens" in d["conte"] and d["item"] == 1,
               "the vault opens to the word, and the Procrustes Analyzer is the captain's")
        expect(d["log"] == ["cargo3", "cargo1", "cargo2"], "the log runs through every part: %s" % d["log"])
        expect("For T.K." in d["notes"] and d["array"] == 1, "Kren's notes hold the cartridge, and the captain takes it")

    # ---- through the published Cargo 1.2.1, and joined back up -------------------------------------------------
    old_home = tempfile.mkdtemp(prefix="cargo-saga-trip-121-")
    folder = os.path.join(old_home, "captains")
    os.makedirs(folder)
    with open(a["path"], encoding="utf-8") as handle:
        first = handle.read()
    with open(os.path.join(folder, "tester-cargo3.captain"), "w", encoding="utf-8") as handle:
        handle.write(first)
    published = os.path.join(old_home, "cargo121.py")
    try:
        source = subprocess.run(["git", "-C", CARGO1, "show", "v1.2.1:cargo.py"], capture_output=True, text=True,
                                check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        print("saga trip: no v1.2.1 tag here; the published version is not tried")
        source = None
    if source:
        with open(published, "w", encoding="utf-8") as handle:
            handle.write(source)
        e = run(CARGO1, published, r'''
game, text = begin(%r)
game.turn = 50
path, _ = game.export_captain()
rec = cargo.read_captain_file(path)
done({"path": path, "version": cargo.VERSION, "keys": sorted(rec), "id": rec["id"]})
''' % os.path.join(folder, "tester-cargo3.captain"), old_home)
        if e:
            expect(e["version"] == "1.2.1" and "ledger" not in e["keys"] and e["id"] != a["id"],
                   "1.2.1 takes the record, drops the history and gives a new id")
            f = run(cargo3, "game/world.py", r'''
from game import start as starting
rec = cargo.read_captain_file(%r)
io.queue[:] = ["yes"] + [""] * 5
with quiet() as out:
    rec = starting.join_and_tell(rec)
note = " ".join(out.getvalue().replace("│", " ").split())
done({"id": rec["id"], "errands": {x["id"]: x["state"] for x in rec["errands"]}, "note": note})
''' % e["path"], old_home)
            if f:
                expect(f["id"] == a["id"] and f["errands"] == {"thirteenth_line": "open", "vault_word": "open", "vertex_array": "open"},
                       "joined back up: the first id, and every errand still open")
                expect("Cargo 1 1.2.1" in f["note"] and "1.3.0" in f["note"], "the join says which version lost what")
    print("saga trip: %d games played, %s" % (played[0], "ok" if not problems else "%d problems" % len(problems)))


if __name__ == "__main__":
    paths = sys.argv[1:3] or [os.path.join(CARGO1, "..", "Cargo-2"), os.path.join(CARGO1, "..", "Cargo-3")]
    if not all(os.path.isdir(os.path.join(p, "game")) for p in paths):
        print("saga trip: skipped (needs Cargo-2 and Cargo-3 checkouts: %s)" % ", ".join(paths))
        sys.exit(0)
    main(*[os.path.abspath(p) for p in paths])
    sys.exit(1 if problems else 0)
