"""Save/load round trip: play, save, load, compare the two worlds, keep playing the loaded one.

usage: roundtrip.py cargo.py <seed> <inputs_before> <inputs_after>
"""
import sys, os, io, json, random, shutil, traceback, tempfile, builtins
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import headless
from infuzz_pool import POOL

path, seed, n1, n2 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
home = tempfile.mkdtemp(prefix="cargo-rt-")
os.environ["CARGO_HOME"] = home
size = os.terminal_size((80, 40))
shutil.get_terminal_size = lambda fallback=(80, 24): size
cargo = headless.load(path)
headless.patch(cargo, headless.IO())
rng = random.Random(seed)
random.seed(seed)


class Stop(Exception):
    pass


budget = [0]
fed = [0]


def fake_input(prompt=""):
    fed[0] += 1
    if fed[0] > budget[0]:
        raise Stop()
    if fed[0] == 1:
        return "1"              # difficulty
    if fed[0] == 2:
        return "2"              # voyage
    if fed[0] == 3:
        return "Tester %d" % seed
    v = rng.choice(POOL)
    return v


builtins.input = fake_input


def run(game, n):
    budget[0] = fed[0] + n
    while True:
        try:
            game.play()
            return game, "ended"
        except Stop:
            return game, "stopped"
        except SystemExit:
            return game, "exit"
        except cargo.SwitchGame as sw:
            game = sw.game


out = io.StringIO()
real = sys.stdout
sys.stdout = out
result = {"seed": seed}
try:
    budget[0] = 3
    game = cargo.Game()
    game, how = run(game, n1)
    result["phase1"] = how
    result["turn"] = game.turn
    path1 = game.save_game("roundtrip")
    result["save_bytes"] = os.path.getsize(path1)
    a = json.dumps(cargo.encode_world(game), sort_keys=True)
    loaded = cargo.load_game("roundtrip")
    b = json.dumps(cargo.encode_world(loaded), sort_keys=True)
    result["identical"] = a == b
    if a != b:
        # find first difference for the report
        i = next(k for k in range(min(len(a), len(b))) if a[k] != b[k])
        result["diff_at"] = [a[max(0, i - 120):i + 80], b[max(0, i - 120):i + 80]]
    result["classes"] = sorted({type(v).__name__ for v in vars(loaded).values() if type(v).__module__ == cargo.__name__})[:3]
    # every object in the loaded world must point at the loaded game, not the old one
    stale = 0
    seen = set()
    stack = [loaded]
    while stack:
        v = stack.pop()
        if id(v) in seen or isinstance(v, (str, int, float, bool, type(None))):
            continue
        seen.add(id(v))
        if v is game:
            stale += 1
            continue
        if isinstance(v, dict):
            stack.extend(v.keys()); stack.extend(v.values())
        elif isinstance(v, (list, tuple, set, frozenset)):
            stack.extend(v)
        elif hasattr(v, "__dict__") and type(v).__module__ == cargo.__name__:
            stack.extend(vars(v).values())
    result["stale_refs_to_old_game"] = stale
    # captain record round trip
    p, code = loaded.export_captain()
    rec = cargo.captain_from_code(code)
    result["captain_code_len"] = len(code)
    result["captain_ok"] = rec["name"] == loaded.player_name and rec == cargo.read_captain_file(p)
    loaded, how = run(loaded, n2)
    result["phase2"] = how
    result["turn_after"] = loaded.turn
except Exception:
    result["traceback"] = traceback.format_exc()[-1500:]
finally:
    sys.stdout = real
    shutil.rmtree(home, ignore_errors=True)
print(json.dumps(result, ensure_ascii=False))
