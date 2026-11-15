"""In-process fuzzer: play cargo.py with random commands at a fixed terminal width.

usage: infuzz.py cargo.py <cols> <n_inputs> <seed> [--boxes]
Reports crashes (with traceback), lines wider than the terminal, and with --boxes the
multi-column tables that did not fit at their natural width.
"""
import sys, os, io, random, re, shutil, traceback, unicodedata, collections, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import headless

path, cols, n_inputs, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
want_boxes = "--boxes" in sys.argv

from infuzz_pool import POOL


class Stop(Exception):
    pass


size = os.terminal_size((cols, 40))
shutil.get_terminal_size = lambda fallback=(80, 24): size
os.get_terminal_size = lambda *a: size
import tempfile
os.environ["CARGO_HOME"] = tempfile.mkdtemp(prefix="cargo-fuzz-")

cargo = headless.load(path)
rng = random.Random(seed)
random.seed(seed)
count = [0]
last = []


def fake_input(prompt=""):
    count[0] += 1
    if count[0] > n_inputs:
        raise Stop()
    if count[0] == 1:
        v = "1"             # difficulty
    elif count[0] == 2:
        v = "2"             # voyage
    elif count[0] == 3:
        v = "Tester"
    else:
        v = rng.choice(POOL)
    last.append(v)
    del last[:-8]
    sys.stdout.write(prompt + v + "\n")
    return v


boxes = collections.Counter()
if want_boxes:
    orig = cargo.Game.create_box

    def spy(self, content, style="single", *a, **k):
        ncols = max(len(r) for r in content)
        if ncols > 1:
            nat = [0] * ncols
            for r in content:
                for i, c in enumerate(r):
                    nat[i] = max(nat[i], len(str(c)))
            need = sum(nat) + 3 * (ncols - 1) + 4
            f = sys._getframe(1)
            boxes[(f.f_code.co_name, f.f_lineno, ncols, k.get("narrow", ""))] = max(
                boxes[(f.f_code.co_name, f.f_lineno, ncols, k.get("narrow", ""))], need)
        return orig(self, content, style, *a, **k)
    cargo.Game.create_box = spy

headless.patch(cargo, headless.IO())
import builtins
builtins.input = fake_input
buf = io.StringIO()
old = sys.stdout
sys.stdout = buf
tb = None
exited = None
try:
    game = cargo.Game()
    while True:
        try:
            game.play()
            break
        except getattr(cargo, "SwitchGame", Stop) as switch:      # a load: play on in the loaded game
            if isinstance(switch, Stop):
                raise
            game = switch.game
except Stop:
    pass
except SystemExit as e:
    exited = "exit(%s)" % (e.code,)
except Exception:
    tb = traceback.format_exc()
finally:
    sys.stdout = old

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\r")
def wlen(s):
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)

over = {}
trunc = collections.Counter()
for ln in ANSI.sub("", buf.getvalue()).split("\n"):
    w = wlen(ln.rstrip())
    if w > cols and not ln.startswith("CARGO:"):     # the captain code is one unbroken line on purpose
        over[re.sub(r"\d+", "N", ln.strip())[:50]] = (w, ln.rstrip()[:110])
    if "..." in ln and ("│" in ln or "║" in ln):
        trunc[re.sub(r"\d+", "N", ln.strip())[:60]] += 1
res = {"cols": cols, "seed": seed, "inputs": min(count[0], n_inputs), "exited": exited,
       "overflow": sorted(over.values(), reverse=True)[:6], "overflow_kinds": len(over),
       "truncated_kinds": len(trunc), "truncated": [k for k, _ in trunc.most_common(6)],
       "traceback": tb, "last_inputs": last}
if want_boxes:
    res["boxes"] = sorted(((need, name, line, n, nar) for (name, line, n, nar), need in boxes.items()), reverse=True)
print(json.dumps(res, ensure_ascii=False))
if os.environ.get("DUMP"):
    open(os.environ["DUMP"], "w").write(buf.getvalue())
