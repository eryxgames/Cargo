"""Load cargo.py as a module and build a Game without a terminal.

    from headless import load, new_game
    cargo = load("/path/to/cargo.py")
    game, io = new_game(cargo)          # io.feed([...]) queues answers for input()
"""
import builtins, importlib.util, io as _io, os, sys, time, contextlib


class IO:
    def __init__(self):
        self.queue = []
        self.default = ""
        self.asked = []
        self.strict = False

    def feed(self, items):
        self.queue.extend(items)

    def input(self, prompt=""):
        self.asked.append(prompt)
        if self.queue:
            return self.queue.pop(0)
        if self.strict:
            raise EOFError("input exhausted at prompt %r" % prompt)
        return self.default


def load(path, name="cargo"):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def patch(cargo, io):
    builtins.input = io.input
    time.sleep = lambda *a, **k: None
    os.system = lambda *a, **k: 0
    if hasattr(cargo, "time"):
        cargo.time.sleep = lambda *a, **k: None


@contextlib.contextmanager
def quiet():
    buf = _io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        yield buf
    finally:
        sys.stdout = old


def new_game(cargo, difficulty="1", name="Tester", silent=True):
    io = IO()
    patch(cargo, io)
    io.feed([difficulty, name])
    if silent:
        with quiet():
            game = cargo.Game()
    else:
        game = cargo.Game()
    return game, io
