"""Hostile and damaged save / captain files must be refused cleanly (SaveError), never crash
the game and never create anything but the game's own classes.

usage: test_files.py cargo.py
"""
import sys, os, json, zlib, base64, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import headless

home = tempfile.mkdtemp(prefix="cargo-files-")
os.environ["CARGO_SAGA_HOME"] = home
cargo = headless.load(sys.argv[1])
io = headless.IO()
headless.patch(cargo, io)
io.feed(["1", "2", "Filer"])
with headless.quiet():
    game = cargo.Game()
    good_path = game.save_game("good")
good = json.load(open(good_path, encoding="utf-8"))
results = []


def expect_refused(name, fn):
    try:
        with headless.quiet():
            fn()
        results.append((name, "FAIL: accepted"))
    except cargo.SaveError as e:
        results.append((name, "ok: " + str(e)[:50]))
    except BaseException as e:
        results.append((name, "FAIL: %s %s" % (type(e).__name__, str(e)[:60])))


def save_with(state=None, **over):
    data = dict(good)
    if state is not None:
        data["state"] = state
    data.update(over)
    path = os.path.join(cargo.save_folder(), "bad.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


def raw_save(text):
    path = os.path.join(cargo.save_folder(), "bad.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path

expect_refused("save: not JSON", lambda: cargo.load_game(raw_save("this is not json {")))
expect_refused("save: empty file", lambda: cargo.load_game(raw_save("")))
expect_refused("save: JSON list", lambda: cargo.load_game(raw_save("[1,2,3]")))
expect_refused("save: other game", lambda: cargo.load_game(save_with(game="cargo9")))
expect_refused("save: newer version", lambda: cargo.load_game(save_with(version=99)))
expect_refused("save: state is a number", lambda: cargo.load_game(save_with(state=5)))
expect_refused("save: unknown class", lambda: cargo.load_game(save_with(state={"~": "o", "c": "Popen", "i": 1, "s": {}})))
expect_refused("save: builtin class name", lambda: cargo.load_game(save_with(state={"~": "o", "c": "dict", "i": 1, "s": {}})))
expect_refused("save: wrong root class", lambda: cargo.load_game(save_with(state={"~": "o", "c": "Ship", "i": 1, "s": {}})))
expect_refused("save: dangling reference", lambda: cargo.load_game(save_with(state={"~": "o", "c": "Game", "i": 1, "s": {"ship": {"~": "r", "i": 77}}})))
expect_refused("save: unknown marker", lambda: cargo.load_game(save_with(state={"~": "zz"})))
deep = "[" * 100000 + "]" * 100000
expect_refused("save: 100000 nested lists", lambda: cargo.load_game(raw_save('{"format":"cargo-save","game":"cargo1","version":1,"state":%s}' % deep)))
expect_refused("save: missing file", lambda: cargo.load_game("nope-not-here"))

# a truncated but otherwise honest save
text = open(good_path, encoding="utf-8").read()
expect_refused("save: cut in half", lambda: cargo.load_game(raw_save(text[:len(text) // 2])))

# the good one still loads, and loading never ran a constructor with prompts
with headless.quiet():
    again = cargo.load_game("good")
results.append(("save: good file loads", "ok" if again.player_name == "Filer" else "FAIL"))

# ---------------------------------------------------------------- captain records
with headless.quiet():
    path, code = game.export_captain()
record = json.load(open(path, encoding="utf-8"))
expect_refused("captain: garbage code", lambda: cargo.captain_from_code("CARGO:hello world"))
expect_refused("captain: empty code", lambda: cargo.captain_from_code(""))
expect_refused("captain: code cut short", lambda: cargo.captain_from_code(code[:len(code) // 2]))
flipped = code[:40] + ("A" if code[40] != "A" else "B") + code[41:]
expect_refused("captain: one character changed", lambda: cargo.captain_from_code(flipped))
bomb = cargo.CAPTAIN_CODE_PREFIX + base64.urlsafe_b64encode(zlib.compress(b"0" * 50_000_000, 9)).decode()
expect_refused("captain: 50 MB decompression bomb", lambda: cargo.captain_from_code(bomb))
tampered = dict(record); tampered["rank"] = "Emperor"
expect_refused("captain: edited without checksum", lambda: cargo.clean_captain(tampered))
expect_refused("captain: wrong format", lambda: cargo.clean_captain({"format": "x"}))
expect_refused("captain: not a dict", lambda: cargo.clean_captain([1, 2]))

# a record that carries a valid checksum but hostile content is cleaned, not trusted
nasty = dict(record)
nasty["name"] = "\x1b[2J\x1b[31mEVIL" + "x" * 5000
nasty["career"] = {"money": 10 ** 40, "turns": "many", "trades": -5, "victories": float("nan")}
nasty["hold"] = {("item%d" % i): 10 ** 9 for i in range(500)}
nasty["story"] = {"flags": ["f" * 900] * 900, "completed": "notalist", "ending": {"a": 1}}
nasty["origin"] = {"game": "cargo2", "version": "9" * 99}
nasty["id"] = "C2-0BADF00D"
nasty["extra"] = {"anything": [1, 2, 3]}        # a key from a newer game: kept as it came (1.3)
nasty["bloat"] = "x" * 20000                      # but not one this big
nasty["check"] = cargo._captain_check(nasty)
try:
    clean = cargo.clean_captain(nasty)
    problems = []
    if "\x1b" in clean["name"] or len(clean["name"]) > 40: problems.append("name")
    if clean["career"]["money"] > 10 ** 12 or clean["career"]["trades"] < 0: problems.append("numbers")
    if clean["career"]["turns"] != 0 or clean["career"]["victories"] != 0: problems.append("types")
    if len(clean["hold"]) > 40 or max(clean["hold"].values()) > 999: problems.append("hold")
    if len(clean["story"]["flags"]) > 160 or len(clean["story"]["flags"][0]) > 32: problems.append("flags")
    if clean.get("extra") != {"anything": [1, 2, 3]}: problems.append("a newer game's key not kept")
    if "bloat" in clean: problems.append("an oversized key kept")
    with headless.quiet():
        msg = game.receive_captain(clean)
    results.append(("captain: hostile content cleaned", "ok" if not problems else "FAIL: " + ",".join(problems)))
    results.append(("captain: visitor recorded", "ok" if game.has_visiting_captain(game="cargo2") else "FAIL"))
except Exception as e:
    results.append(("captain: hostile content cleaned", "FAIL: %s %s" % (type(e).__name__, e)))

with headless.quiet():
    own = game.receive_captain(cargo.captain_from_code(code))
results.append(("captain: own record is not a visitor", "ok" if "own record" in own else "FAIL"))

# a save made while something had replaced one of the story's methods (a test tool silencing
# the scenes, say) must load with the method back, not with nothing in its place
try:
    game.story.tick = lambda: None
    with headless.quiet():
        patched_path = game.save_game("patched")
        loaded = cargo.load_game("patched")
    ok = callable(loaded.story.tick) and "tick" not in vars(loaded.story)
    results.append(("save: patched method comes back", "ok" if ok else "FAIL: %r" % vars(loaded.story).get("tick")))
except Exception as e:
    results.append(("save: patched method comes back", "FAIL: %s %s" % (type(e).__name__, e)))

# 1.2.0 kept its files in ~/.cargo (or CARGO_HOME), Rust's folder: the new default folder takes
# Cargo's own subfolders over once, and leaves everything else there alone
try:
    old_home, new_home = tempfile.mkdtemp(prefix="cargo-old-"), tempfile.mkdtemp(prefix="cargo-new-")
    os.makedirs(os.path.join(old_home, "cargo1", "saves"))
    os.makedirs(os.path.join(old_home, "captains"))
    os.makedirs(os.path.join(old_home, "bin"))                       # Rust's, not ours
    for name in ("cargo1/saves/autosave.json", "captains/Old_Hand.json"):
        with open(os.path.join(old_home, name), "w") as f:
            f.write("{}")
    target = os.path.join(new_home, "saga")
    saved = dict(os.environ)
    os.environ["CARGO_HOME"] = old_home
    cargo.adopt_old_files(target)
    os.environ.clear(); os.environ.update(saved)
    ok = (os.path.exists(os.path.join(target, "cargo1", "saves", "autosave.json"))
          and os.path.exists(os.path.join(target, "captains", "Old_Hand.json"))
          and not os.path.exists(os.path.join(target, "bin"))
          and os.path.exists(os.path.join(old_home, "captains", "Old_Hand.json")))
    results.append(("old ~/.cargo files copied over", "ok" if ok else "FAIL"))
    shutil.rmtree(old_home, ignore_errors=True); shutil.rmtree(new_home, ignore_errors=True)
except Exception as e:
    results.append(("old ~/.cargo files copied over", "FAIL: %s %s" % (type(e).__name__, e)))

shutil.rmtree(home, ignore_errors=True)
bad = [r for r in results if not r[1].startswith("ok")]
for name, res in results:
    print("%-40s %s" % (name, res))
print("%d checks, %d failed" % (len(results), len(bad)))
sys.exit(1 if bad else 0)
