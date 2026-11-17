import base64
import hashlib
import json
import random
import os
import re
import sys
import time
import shutil
import unicodedata
import zlib
from math import floor

VERSION = "1.2.1"

# Define your logo data ONCE, at the module level:
logo_data = [
    "╔════════ C Δ R G Ω ════════╗",
    "║     Space Trading Saga    ║",
    "╚═══════════════════════════╝"
]

# =============================================================================
# Terminal kit: width, wrapping and the one box renderer.
# Everything the game draws goes through here, so a 36-column phone screen in
# Termux and a wide desktop terminal get the same boxes, laid out to fit.
# =============================================================================

MIN_COLUMNS = 24        # below this nothing sensible fits; lay out as if this wide
NARROW_COLUMNS = 60     # below this the layout switches to the phone arrangement
RULE = object()         # a row that draws a horizontal rule inside a box

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

BOX_STYLES = {
    'single': {'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘', 'h': '─', 'v': '│', 'sep': '│', 'l': '├', 'r': '┤'},
    'double': {'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝', 'h': '═', 'v': '║', 'sep': '║', 'l': '╟', 'r': '╢', 'rule': '─'},
    'round':  {'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯', 'h': '─', 'v': '│', 'sep': '│', 'l': '├', 'r': '┤'},
    'ascii':  {'tl': '+', 'tr': '+', 'bl': '+', 'br': '+', 'h': '-', 'v': '|', 'sep': '|', 'l': '+', 'r': '+'},
}


def safe_output():
    """Characters this terminal cannot show print as '?' instead of stopping the game
    (old Windows code pages, output sent to a file or a pipe)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            if "utf" not in (getattr(stream, "encoding", None) or "utf").lower():
                stream.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def plain_terminal():
    """True when the terminal cannot be trusted with box-drawing characters."""
    if os.environ.get("CARGO_ASCII"):
        return True
    encoding = (getattr(sys.stdout, "encoding", None) or "").lower()
    return bool(encoding) and "utf" not in encoding


def terminal_columns():
    """Width of the terminal in columns; 80 when it cannot be known."""
    try:
        columns = shutil.get_terminal_size((80, 24)).columns
    except (OSError, ValueError):
        columns = 80
    return max(MIN_COLUMNS, columns or 80)


def is_narrow():
    return terminal_columns() < NARROW_COLUMNS


def box_inner_width(cap=None):
    """Columns between the two borders of a full-width box."""
    columns = terminal_columns()
    # wide terminals keep the classic one-column margin; phones use every column
    inner = columns - 4 if columns >= NARROW_COLUMNS else columns - 3
    if cap:
        inner = min(inner, cap)
    return max(MIN_COLUMNS - 3, inner)


def visible_len(text):
    """Printed width of a string: colour codes count 0, wide characters 2."""
    width = 0
    for ch in _ANSI_RE.sub("", str(text)):
        if unicodedata.combining(ch):
            continue
        width += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return width


def pad_to(text, width):
    text = str(text)
    return text + " " * max(0, width - visible_len(text))


def wrap_text(text, width):
    """Word-wrap to `width` columns; words longer than a line are split. Leading spaces
    are kept, on every line the text wraps to (an indented line stays indented)."""
    text = str(text)
    indent = len(text) - len(text.lstrip(" "))
    if indent and indent < int(width) // 2:
        return [" " * indent + line for line in wrap_text(text.lstrip(" "), int(width) - indent)]
    width = max(1, int(width))
    lines, current, current_len = [], [], 0
    for word in str(text).split():
        while visible_len(word) > width:           # a word wider than the box
            if current:
                lines.append(" ".join(current))
                current, current_len = [], 0
            lines.append(word[:width])
            word = word[width:]
        word_len = visible_len(word)
        if current and current_len + 1 + word_len > width:
            lines.append(" ".join(current))
            current, current_len = [word], word_len
        elif current:
            current.append(word)
            current_len += 1 + word_len
        else:
            current, current_len = [word], word_len
    if current:
        lines.append(" ".join(current))
    return lines


def flow_cells(cells, width, gap="  "):
    """Lay short cells out left to right, breaking only between cells."""
    lines, current = [], ""
    for cell in cells:
        cell = str(cell)
        if not cell.strip():
            continue
        if visible_len(cell) > width:
            if current:
                lines.append(current)
                current = ""
            lines.extend(wrap_text(cell, width))
        elif current and visible_len(current) + len(gap) + visible_len(cell) > width:
            lines.append(current)
            current = cell
        else:
            current = current + gap + cell if current else cell
    if current:
        lines.append(current)
    return lines


def render_box(rows, style='single', inner=None, narrow='auto'):
    """Draw a box around `rows` and return it as one string.

    rows    a list of rows; a row is a list of cells (one cell = plain text that is
            word-wrapped, several cells = table columns) or RULE for a rule.
    style   'single', 'double' or 'round'.
    inner   columns between the borders (default: the terminal width).
    narrow  what a table does when its columns do not fit:
            'auto'  wrap the widest column; if even that is too tight, put each
                    row on its own lines (first cell, then the rest indented)
            'flow'  for side-by-side panels: each column becomes a block whose
                    cells flow left to right, blocks separated by a rule
            'stack' for side-by-side lists: each column becomes a block with
                    one cell per line, blocks separated by a rule
    Nothing is ever cut off and no line is wider than the box.
    """
    chars = BOX_STYLES['ascii'] if plain_terminal() else BOX_STYLES.get(style, BOX_STYLES['single'])
    if inner is None:
        inner = box_inner_width()
    text_width = max(1, inner - 2)
    body = []          # each entry: a text line, or RULE

    table = [r for r in rows if r is not RULE]
    num_cols = max([len(r) for r in table] or [1])

    if num_cols <= 1:
        for row in rows:
            if row is RULE:
                body.append(RULE)
                continue
            cell = row[0] if isinstance(row, (list, tuple)) and row else (row if isinstance(row, str) else "")
            lines = wrap_text(cell, text_width)
            if lines:
                body.extend(lines)
            elif body and body[-1] not in ("", RULE):
                body.append("")             # an empty row is a blank line (one at most)
        while body and body[-1] == "":
            body.pop()
    else:
        natural = [0] * num_cols
        for row in table:
            for i, cell in enumerate(row):
                natural[i] = max(natural[i], visible_len(cell))
        gaps = 3 * (num_cols - 1)
        sep = " " + chars['sep'] + " "

        def table_lines(widths):
            for row in rows:
                if row is RULE:
                    body.append(RULE)
                    continue
                cells = [str(c) for c in row] + [''] * (num_cols - len(row))
                wrapped = [wrap_text(c, widths[i]) or [''] for i, c in enumerate(cells)]
                for k in range(max(len(w) for w in wrapped)):
                    body.append(sep.join(
                        pad_to(w[k] if k < len(w) else '', widths[i]) for i, w in enumerate(wrapped)))

        if sum(natural) + gaps <= text_width:
            # everything fits: natural widths with a little air, last column takes the rest
            widths = list(natural)
            spare = text_width - gaps - sum(natural)
            for i in range(num_cols - 1):
                extra = min(2, spare)
                widths[i] += extra
                spare -= extra
            widths[-1] += spare
            table_lines(widths)
        elif narrow in ('flow', 'stack'):
            for i in range(num_cols):
                column = [str(row[i]) for row in table if i < len(row)]
                while column and not column[-1].strip():
                    column.pop()
                if not column:
                    continue
                if body:
                    body.append(RULE)
                if narrow == 'flow':
                    body.extend(flow_cells(column, text_width))
                else:
                    for cell in column:
                        indent = len(cell) - len(cell.lstrip(' '))
                        for line in wrap_text(cell, text_width - indent) or ['']:
                            body.append(' ' * indent + line)
        else:
            widest = max(range(num_cols), key=lambda i: natural[i])
            room = text_width - gaps - (sum(natural) - natural[widest])
            if room >= min(natural[widest], 14):
                widths = list(natural)
                widths[widest] = room
                table_lines(widths)
            else:
                for row in rows:
                    if row is RULE:
                        body.append(RULE)
                        continue
                    cells = [str(c) for c in row if str(c).strip()]
                    if not cells:
                        body.append('')
                        continue
                    body.extend(wrap_text(cells[0], text_width))
                    if len(cells) > 1:
                        for line in wrap_text(" · ".join(cells[1:]), text_width - 2):
                            body.append("  " + line)

    rule_char = chars.get('rule', chars['h'])
    lines = [chars['tl'] + chars['h'] * inner + chars['tr']]
    for line in body:
        if line is RULE:
            lines.append(chars['l'] + rule_char * inner + chars['r'])
        else:
            lines.append(chars['v'] + " " + pad_to(line, text_width) + " " + chars['v'])
    lines.append(chars['bl'] + chars['h'] * inner + chars['br'])
    return "\n".join(lines)


def say(text=""):
    """Print plain text, wrapped to the terminal."""
    for line in wrap_text(text, terminal_columns() - 1) or [""]:
        print(line)


# =============================================================================
# Save games: the whole world as one JSON file.
# Saves and captain records live in a folder shared by the Cargo trilogy:
# ~/.cargo-saga (or wherever CARGO_SAGA_HOME points).
# =============================================================================

GAME_ID = "cargo1"
SAVE_FORMAT = 1
AUTOSAVE_SLOT = "autosave"


class SaveError(Exception):
    """A save or captain file could not be written or understood."""


class SwitchGame(Exception):
    """Raised inside a running game to continue with another one (after a load)."""

    def __init__(self, game):
        Exception.__init__(self, "switch game")
        self.game = game


_ADOPTED = []


def cargo_home():
    """The folder the trilogy shares: ~/.cargo-saga, or wherever CARGO_SAGA_HOME points.
    Up to 1.2.0 it was ~/.cargo (or CARGO_HOME), which Rust's package manager also uses;
    the first time the new default folder is used, Cargo's own files there are copied over."""
    chosen = os.environ.get("CARGO_SAGA_HOME")
    if chosen:
        return chosen
    home = os.path.join(os.path.expanduser("~"), ".cargo-saga")
    if not _ADOPTED:
        _ADOPTED.append(True)
        adopt_old_files(home)
    return home


def adopt_old_files(home):
    """Copy this game's saves and the captain records from the folder 1.2.0 used, once.
    Only Cargo's own subfolders are touched; the old ones stay where they were."""
    old = os.environ.get("CARGO_HOME") or os.path.join(os.path.expanduser("~"), ".cargo")
    for part in (GAME_ID, "captains"):
        source, target = os.path.join(old, part), os.path.join(home, part)
        if os.path.isdir(source) and not os.path.exists(target):
            try:
                shutil.copytree(source, target)
            except (OSError, shutil.Error):
                pass


def save_folder():
    return os.path.join(cargo_home(), GAME_ID, "saves")


def captain_folder():
    return os.path.join(cargo_home(), "captains")


def safe_name(text, fallback="captain"):
    """A file name made of letters, digits, '-' and '_' only."""
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", str(text)).strip("_")[:32]
    return name or fallback


def write_json(path, data):
    """Write a JSON file so that a crash never leaves half a file behind."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = "%s.%d.tmp" % (path, os.getpid())
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp, path)


def game_classes():
    """The classes a save file may contain: the ones defined in this file."""
    return {name: obj for name, obj in globals().items()
            if isinstance(obj, type) and obj.__module__ == __name__}


def _is_code(value):
    return callable(value) and not isinstance(value, type)


def encode_world(root):
    """Turn the object graph under `root` into JSON-friendly data.

    Objects of the game's own classes are written once and referred to by number
    afterwards, so shared objects stay shared and loops are fine.  Functions are
    not saved; loading takes them from a freshly built game (see decode_world).
    """
    classes = set(game_classes().values())
    counts = {}          # id -> times seen, for containers that are shared
    stack, seen_objects = [root], set()
    while stack:
        value = stack.pop()
        if isinstance(value, (str, int, float, bool, type(None))) or _is_code(value) or isinstance(value, type):
            continue
        key = id(value)
        if isinstance(value, (list, dict, set, frozenset, tuple)):
            counts[key] = counts.get(key, 0) + 1
            if counts[key] > 1:
                continue
            if isinstance(value, dict):
                stack.extend(value.keys())
                stack.extend(value.values())
            else:
                stack.extend(value)
        elif type(value) in classes:
            if key in seen_objects:
                continue
            seen_objects.add(key)
            stack.extend(vars(value).values())
        else:
            raise SaveError("cannot save a value of type %s" % type(value).__name__)

    numbers = {}

    def number(value):
        numbers[id(value)] = len(numbers) + 1
        return numbers[id(value)]

    def enc(value):
        if isinstance(value, (str, int, float, bool, type(None))):
            return value
        if isinstance(value, type):
            return {"~": "c", "c": value.__name__}
        if _is_code(value):
            return {"~": "f"}
        key = id(value)
        if key in numbers:
            return {"~": "r", "i": numbers[key]}
        shared = counts.get(key, 0) > 1
        if isinstance(value, list):
            if not shared:
                return [enc(v) for v in value]
            return {"~": "l", "i": number(value), "v": [enc(v) for v in value]}
        if isinstance(value, tuple):
            return {"~": "t", "v": [enc(v) for v in value]}
        if isinstance(value, (set, frozenset)):
            out = {"~": "s", "v": None}
            if shared:
                out["i"] = number(value)
            items = [enc(v) for v in value]
            try:
                items.sort(key=lambda v: json.dumps(v, sort_keys=True))
            except TypeError:
                pass
            out["v"] = items
            return out
        if isinstance(value, dict):
            simple = all(isinstance(k, str) for k in value) and "~" not in value
            if simple and not shared:
                return {k: enc(v) for k, v in value.items()}
            out = {"~": "d"}
            if shared:
                out["i"] = number(value)
            out["v"] = [[enc(k), enc(v)] for k, v in value.items()]
            return out
        out = {"~": "o", "c": type(value).__name__, "i": number(value)}
        out["s"] = {k: enc(v) for k, v in vars(value).items()}
        return out

    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(limit, 20000))
    try:
        return enc(root)
    finally:
        sys.setrecursionlimit(limit)


# Classes older saves may contain that this version replaced (their content now
# comes from the story data): loading drops them instead of refusing the save.
RETIRED_CLASSES = {"DynamicCharacterSystem", "EventChain", "CharacterManager", "CharacterTemplate"}

# Places that were renamed: old saves are brought up to date when loaded.
RENAMED_PLACES = {"Alien Outpost X": "Alien Signal Research Outpost X",
                  "Alien Outpost Y": "Alien Signal Research Outpost Y"}
RENAMED_TYPES = {"Alien Outpost": "Alien Signal Research Outpost"}


def decode_world(data, fresh):
    """Rebuild a saved world on top of `fresh`, a newly constructed game.

    Only classes from this file are ever instantiated, and never through their
    constructors, so loading a save cannot run code of its own.  The fresh game
    supplies what a save does not carry: functions, and attributes added in a
    later version.
    """
    classes = game_classes()
    by_number = {}
    claimed = set()

    def hashable(value):
        try:
            hash(value)
            return True
        except TypeError:
            return False

    def dec(node, old):
        if isinstance(node, list):
            base = old if isinstance(old, list) else []
            return [dec(v, base[i] if i < len(base) else None) for i, v in enumerate(node)]
        if not isinstance(node, dict):
            return node
        kind = node.get("~")
        if kind is None:
            base = old if isinstance(old, dict) else {}
            return {k: dec(v, base.get(k)) for k, v in node.items()}
        if kind == "r":
            if node.get("i") not in by_number:
                raise SaveError("save file refers to something it does not contain")
            return by_number[node["i"]]
        if kind == "f":
            return old if _is_code(old) else None
        if kind == "c":
            if node.get("c") not in classes:
                raise SaveError("unknown class in save file")
            return classes[node["c"]]
        if kind == "t":
            return tuple(dec(v, None) for v in node.get("v", []))
        if kind == "l":
            out = []
            if "i" in node:
                by_number[node["i"]] = out
            base = old if isinstance(old, list) else []
            out.extend(dec(v, base[i] if i < len(base) else None) for i, v in enumerate(node.get("v", [])))
            return out
        if kind == "s":
            out = set()
            if "i" in node:
                by_number[node["i"]] = out
            for v in node.get("v", []):
                item = dec(v, None)
                if hashable(item):
                    out.add(item)
            return out
        if kind == "d":
            out = {}
            if "i" in node:
                by_number[node["i"]] = out
            base = old if isinstance(old, dict) else {}
            for pair in node.get("v", []):
                key = dec(pair[0], None)
                if hashable(key):
                    out[key] = dec(pair[1], base.get(key))
            return out
        if kind == "o":
            cls = classes.get(node.get("c"))
            if cls is None and node.get("c") in RETIRED_CLASSES:
                by_number[node.get("i")] = None          # a system this version no longer has
                return None
            if cls is None:
                raise SaveError("unknown class in save file: %s" % str(node.get("c"))[:40])
            if type(old) is cls and id(old) not in claimed:
                obj = old
            else:
                obj = cls.__new__(cls)
            claimed.add(id(obj))
            by_number[node.get("i")] = obj
            before = dict(vars(obj))
            for key, value in node.get("s", {}).items():
                if isinstance(value, dict) and value.get("~") == "f" and not _is_code(before.get(key)):
                    continue        # a function set on this object when it was saved: keep the class's own
                obj.__dict__[str(key)] = dec(value, before.get(key))
            return obj
        raise SaveError("save file contains something unknown")

    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(limit, 20000))
    try:
        result = dec(data, fresh)
    finally:
        sys.setrecursionlimit(limit)
    if result is not fresh:
        raise SaveError("save file does not hold a game")
    return result


def list_saves():
    """Saved games, newest first: [{'slot', 'path', 'summary', 'saved_at'}]."""
    saves = []
    try:
        names = os.listdir(save_folder())
    except OSError:
        return saves
    for name in names:
        if not name.endswith(".json"):
            continue
        path = os.path.join(save_folder(), name)
        try:
            with open(path, encoding="utf-8") as handle:
                head = json.load(handle)
            if head.get("format") != "cargo-save" or head.get("game") != GAME_ID:
                continue
            saves.append({"slot": name[:-5], "path": path, "summary": head.get("summary", {}),
                          "saved_at": head.get("saved_at", ""), "mtime": os.path.getmtime(path)})
        except (OSError, ValueError, AttributeError, RecursionError):
            continue
    saves.sort(key=lambda entry: entry["mtime"], reverse=True)
    return saves


def describe_save(entry):
    summary = entry.get("summary") or {}
    return "%s - %s, turn %s, %s" % (
        entry["slot"], str(summary.get("player", "?"))[:20], summary.get("turn", "?"),
        str(summary.get("location", "?"))[:20])


def load_game(slot_or_path):
    """Read a save file and return the game it holds."""
    path = slot_or_path
    if not os.path.isfile(path):
        path = os.path.join(save_folder(), safe_name(slot_or_path, AUTOSAVE_SLOT) + ".json")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError:
        raise SaveError("no such saved game")
    except (ValueError, RecursionError):
        raise SaveError("the save file is damaged")
    if not isinstance(data, dict) or data.get("format") != "cargo-save" or data.get("game") != GAME_ID:
        raise SaveError("this is not a Cargo save file")
    if data.get("version", 0) > SAVE_FORMAT:
        raise SaveError("this save was made by a newer version of the game")
    summary = data.get("summary") or {}
    difficulty = summary.get("difficulty")
    fresh = Game(difficulty=difficulty if difficulty in (0, 1, 2) else 1,
                 player_name=str(summary.get("player", "Captain"))[:40], intro=False)
    try:
        game = decode_world(data.get("state"), fresh)
    except SaveError:
        raise
    except Exception as error:      # a save from elsewhere must never crash the game
        raise SaveError("the save file could not be read (%s)" % type(error).__name__)
    game.term_width = game.get_terminal_width()
    game.term_height = game.get_terminal_height()
    game.bring_up_to_date()
    return game


# =============================================================================
# The captain's record: a small file (or a line of text) that carries a captain
# from one part of the Cargo trilogy into another.
# =============================================================================

CAPTAIN_FORMAT = 1
CAPTAIN_CODE_PREFIX = "CARGO:"

# The words the story's conditions are written in (see story/cargo1.story.json)
STORY_PLACE_TYPES = ["Planet", "AsteroidBase", "DeepSpaceOutpost", "ResearchColony"]
STORY_BUILDINGS = ["stockmarket", "Neuroengineering Guild", "Agrobot Assembly Line", "mining_platform"]
STORY_VICTORY_TYPES = ["total", "pirate", "militia", "raider", "machine", "rogue_captain", "uprising"]
CAPTAIN_GAMES = ("cargo1", "cargo2", "cargo3")


def _captain_check(record):
    body = {k: v for k, v in record.items() if k != "check"}
    blob = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def _clean_text(value, limit=40):
    text = _ANSI_RE.sub("", str(value))
    text = "".join(ch for ch in text if ch.isprintable())
    return text[:limit]


def _clean_number(value, low=0, high=10 ** 12):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return low
    return max(low, min(high, int(value)))


def clean_captain(record):
    """Check a captain record from outside and return a tidy copy.

    The record may come from another game, another machine or a text message,
    so nothing in it is trusted: unknown keys are dropped, texts are shortened,
    numbers are clamped.  Raises SaveError when it is not a captain record.
    """
    if not isinstance(record, dict) or record.get("format") != "cargo-captain":
        raise SaveError("this is not a captain record")
    if _clean_number(record.get("version"), 0, 10 ** 6) > CAPTAIN_FORMAT:
        raise SaveError("this captain record was made by a newer game")
    if record.get("check") != _captain_check(record):
        raise SaveError("the captain record is damaged (checksum does not match)")
    origin = record.get("origin") if isinstance(record.get("origin"), dict) else {}
    game = _clean_text(origin.get("game"), 12)
    if game not in CAPTAIN_GAMES:
        raise SaveError("the captain record comes from an unknown game")
    career = record.get("career") if isinstance(record.get("career"), dict) else {}
    story = record.get("story") if isinstance(record.get("story"), dict) else {}
    ship = record.get("ship") if isinstance(record.get("ship"), dict) else {}
    hold = record.get("hold") if isinstance(record.get("hold"), dict) else {}
    log = record.get("log") if isinstance(record.get("log"), list) else []

    def texts(values, limit=24, most=40):
        if not isinstance(values, (list, tuple)):
            return []
        return [_clean_text(v, limit) for v in list(values)[:most]]

    clean = {
        "format": "cargo-captain",
        "version": CAPTAIN_FORMAT,
        "id": _clean_text(record.get("id"), 16),
        "name": _clean_text(record.get("name"), 40) or "Captain",
        "origin": {"game": game, "version": _clean_text(origin.get("version"), 16)},
        "rank": _clean_text(record.get("rank"), 24),
        "career": {key: _clean_number(career.get(key)) for key in
                   ("turns", "money", "trades", "victories", "passengers", "reputation",
                    "locations", "research_points")},
        "research": texts(record.get("research")),
        "ship": {key: _clean_number(ship.get(key), 0, 10 ** 6) for key in ("attack", "defense", "speed")},
        "story": {
            "chapter": _clean_text(story.get("chapter"), 24),
            "completed": texts(story.get("completed")),
            "ending": _clean_text(story.get("ending"), 24),
            "flags": texts(story.get("flags"), limit=32, most=160),
            "plot_points": _clean_number(story.get("plot_points"), 0, 10 ** 6),
        },
        "hold": {_clean_text(k, 24): _clean_number(v, 0, 999) for k, v in list(hold.items())[:40]},
        "log": [{"game": _clean_text(e.get("game"), 12), "event": _clean_text(e.get("event"), 24),
                 "turn": _clean_number(e.get("turn"), 0, 10 ** 9), "at": _clean_text(e.get("at"), 24)}
                for e in log[-20:] if isinstance(e, dict)],
    }
    clean["check"] = _captain_check(clean)
    return clean


def captain_to_code(record):
    """The record as one line of text that can be copied anywhere."""
    blob = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return CAPTAIN_CODE_PREFIX + base64.urlsafe_b64encode(zlib.compress(blob, 9)).decode("ascii").rstrip("=")


def captain_from_code(text):
    text = "".join(str(text).split())
    if text.upper().startswith(CAPTAIN_CODE_PREFIX):
        text = text[len(CAPTAIN_CODE_PREFIX):]
    try:
        raw = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
        blob = zlib.decompressobj().decompress(raw, 200000)      # a record is tiny; refuse bombs
        record = json.loads(blob.decode("utf-8"))
    except Exception:
        raise SaveError("that is not a captain code (or part of it is missing)")
    return clean_captain(record)


def read_captain_file(path):
    try:
        if os.path.getsize(path) > 200000:
            raise SaveError("that file is too large to be a captain record")
        with open(path, encoding="utf-8") as handle:
            record = json.load(handle)
    except OSError:
        raise SaveError("the captain file could not be opened")
    except (ValueError, RecursionError):
        raise SaveError("the captain file is damaged")
    return clean_captain(record)


def list_captain_files():
    """Captain records in the shared folder: [(path, record)], newest first."""
    found = []
    try:
        names = sorted(os.listdir(captain_folder()))
    except OSError:
        return found
    for name in names:
        if not name.endswith(".captain"):
            continue
        path = os.path.join(captain_folder(), name)
        try:
            found.append((os.path.getmtime(path), path, read_captain_file(path)))
        except (SaveError, OSError):
            continue
    found.sort(key=lambda item: item[0], reverse=True)
    return [(path, record) for _, path, record in found]


def run_quest_callback(game, callback):
    """What happens when a quest completes.  Kept as data so quests can be saved."""
    if callable(callback):
        callback()
    elif isinstance(callback, (list, tuple)) and len(callback) == 2 and callback[0] == "unlock_location":
        game.location_manager.complete_location_unlock(callback[1])


# =============================================================================
# The story, as data.  The scenes, characters and places live in the storykit
# files under story/ and are written into this file by tools/build_story.py,
# between the two marker lines below.  Edit the story files, not the block.
# CARGO_STORY=path/to/built.json plays a story file instead (for writers).
# =============================================================================

# --- story data (tools/build_story.py) ---
STORY_JSON = r"""{"game":"cargo1","characters":{"aela":{"name":"Eela","short":"Eela","kind":"agrobot"},"agrobot":{"name":"Sower","kind":"synthetic","generated":true},"ancient_scholar":{"name":"Tylde Kren","short":"Kren","kind":"human","generated":false},"anselm":{"name":"Anselm Rockwarden","short":"Anselm","kind":"human"},"broker":{"name":"Old Fenn","short":"Fenn","kind":"human"},"captain":{"name":"The captain"},"cartographer":{"name":"Hollis Dunmore","short":"Dunmore","kind":"human"},"clone":{"name":"The other captain","short":"the other captain"},"convoy_captain":{"name":"Allsa Targa","short":"Targa","kind":"human"},"cult_elders":{"name":"Elders of the Broken Machine","kind":"human"},"deacon":{"name":"Deacon Amaro","short":"the deacon","kind":"human"},"deadstick":{"name":"Deadstick","kind":"human"},"diplomatic_envoy":{"name":"Envoy Ines Halloran","short":"Halloran","kind":"human","generated":false},"exo_operator":{"name":"Strut","kind":"human"},"farm_tech":{"name":"Mina Perlite","short":"Perlite","kind":"human"},"fluencer":{"name":"Brisa","short":"Brisa","kind":"fluencer"},"fluencer_manager":{"name":"Lorisa","short":"Lorisa","kind":"human"},"geod":{"name":"Geod","short":"Geod","kind":"agrobot"},"grey_hats":{"name":"The Grey Hats","kind":"human"},"gunner":{"name":"Tadeo Ruiz","short":"Tadeo","kind":"human"},"hammerschultz":{"name":"Dr Hammerschultz","short":"Hammerschultz","kind":"human"},"hardtack":{"name":"Sergeant Hardtack","short":"Hardtack","kind":"human"},"harp_engineer":{"name":"Dr Vedral","short":"Vedral","kind":"human"},"heritarchist":{"name":"Magister Notary Augias Pfennig","short":"the Magister","kind":"human"},"holo_star":{"name":"Concertina","kind":"human"},"ice_driller":{"name":"Svea Firn","short":"Firn","kind":"human"},"inspector":{"name":"Hanne Lauritz","short":"Lauritz","kind":"human"},"kettle_survivor":{"name":"Ottilie Brandt","short":"Brandt","kind":"human"},"krog":{"name":"Krogg","short":"Krogg","kind":"agrobot"},"lens_watcher":{"name":"Dr Noor Haddad","short":"Haddad","kind":"human"},"loader":{"name":"Shunt","kind":"agrobot"},"mechanic":{"name":"Oksana","short":"Oksana","kind":"human"},"merchant":{"name":"Merchant","kind":"human","generated":true},"merchant_trader":{"name":"Traveling Merchant","kind":"merchant","generated":true},"meteorologist":{"name":"Bettina Lusk","short":"Lusk","kind":"human"},"meza_voce":{"name":"Meza Voce","short":"Voce","kind":"android"},"nanohive":{"name":"The colony at Sigma VII","kind":"nanobot colony"},"navigator":{"name":"Sister Iolanthe","short":"Iolanthe","kind":"human"},"neon_family":{"name":"Kraal","kind":"family"},"neon_sleeper":{"name":"Conte Ottavine Kraal","short":"Conte Ottavine","kind":"neon"},"neurodroid":{"name":"Neurodroids","kind":"synthetic","generated":true},"neurodroid_leader":{"name":"CU-113","short":"CU-113","full":"Curator Unit 113","title":"Neurodroid Overseer","kind":"neurodroid","generated":false},"pilgrims":{"name":"Pilgrims of the Broken Machine","kind":"human"},"pirate_captain":{"name":"Hedda Mraz","short":"Mraz","kind":"human","generated":false},"port_broker":{"name":"TALLY-4","short":"Tally","kind":"robot"},"quartermaster_dsog":{"name":"Quartermaster Bushing","short":"Bushing","kind":"human"},"radio_astronomer":{"name":"Dr Gald Tunnicliffe","short":"Tunnicliffe","kind":"human"},"rebel_commander":{"name":"Teodor Strada","short":"Strada","kind":"human","generated":false},"researcher":{"name":"Researcher","kind":"human","generated":true},"rogue_captain":{"name":"Rogue Captain","kind":"human","generated":true},"samples":{"name":"Dr Anna-Lise Samples","short":"Dr Samples","kind":"human"},"santor":{"name":"Dharr Santor","short":"Santor","kind":"human"},"sarga_farga":{"name":"Sarga Farga","short":"Farga","kind":"human"},"scar_tribe":{"name":"The Star-Shaped Scar Tribe","kind":"human"},"serac":{"name":"Serac","short":"Serac","kind":"human"},"seven_theories":{"name":"Professor Ruan Odili","short":"Odili","kind":"human"},"shaft_sinker":{"name":"Marit Winze","short":"Winze","kind":"human"},"sixpack":{"name":"the Sixpack","kind":"group"},"skirt_fitter":{"name":"Fingers","kind":"human"},"starshade_engineer":{"name":"Elif Kaya","short":"Kaya","kind":"human"},"steward":{"name":"Ambrose","kind":"robot"},"stope":{"name":"Stope","kind":"human"},"tank_commander":{"name":"Hulldown","kind":"human"},"tank_driver":{"name":"Plough-In","kind":"human"},"tarnished_gear":{"name":"Order of the Lost Gear","kind":"human"},"technoshaman":{"name":"Technoshaman of the drums","kind":"human"},"ullage":{"name":"Ullage","kind":"human"},"underwriter":{"name":"Sjoerd Hoving Wirth","short":"Wirth","kind":"human"},"unsorted":{"name":"The Unsorted","kind":"robot enclave"},"vent_boss":{"name":"Vo Brattice","short":"Brattice","kind":"human"},"vip_passenger":{"name":"VIP Passenger","kind":"special","generated":true},"virtual_heir":{"name":"Karen Asquine-Kraal","short":"Karen","kind":"virtual"},"water_broker":{"name":"Kip Ferraro","short":"Kip","kind":"human"},"young_hauler":{"name":"Pell Okafor","short":"Pell","kind":"human"},"ysolde":{"name":"Yzode van Rostrom","short":"Yzode","kind":"human"}},"flags":{"aela_leased":{"about":"{aela} stayed leased equipment","carries_to":["cargo2"]},"aela_member":{"about":"{aela} became a member of the Rockwarden cooperative: the first machine shareholder","carries_to":["cargo2","cargo3"]},"alien_discovery":{"about":""},"ancient_mystery":{"about":""},"asked_samples":{"about":"the captain asked {samples} what the clone remembers"},"asked_serac":{"about":"the captain asked {serac} who his friends were"},"asked_the_garrison":{"about":"the captain asked what the garrison at Scholz's Star guards","carries_to":["cargo2","cargo3"]},"big_run":{"about":"the captain took the Rootstock's big run to Gamma"},"biomass_aboard":{"about":"sealed Rootstock biomass is in the captain's hold"},"biomass_spoiled":{"about":"the Rootstock's biomass spoiled in the captain's hold"},"bought_the_burn":{"about":"the captain bought the fuel for the long burn at any price"},"bought_the_vote":{"about":"the captain bought the vote that made the Mark law","carries_to":["cargo2"]},"bounty_war":{"about":"the captain answered {pirate_captain.short}'s bounty with a bigger one"},"brisa_hull":{"about":"the captain's hull carries {fluencer}'s name"},"brought_tally_a_battery":{"about":"the captain brought {port_broker} a battery during the strike"},"captains_paid":{"about":"the convoy captains covered the captain's margin call"},"carried_concertina":{"about":"the captain flew {holo_star} to the gala at Epsilon","carries_to":["cargo2"]},"carried_the_pilgrims":{"about":"the captain flew the Broken Machine pilgrims to Alpha","carries_to":["cargo2"]},"carried_the_samples":{"about":"the captain hauled the builders' metal to the Stellar Institute","carries_to":["cargo2"]},"cartel_hauler":{"about":"the captain hauled for the trading houses during the squeeze"},"cleared_by_lauritz":{"about":"{inspector} testified for the captain at the inquiry"},"clone_fight":{"about":"the captain went after the clone"},"clone_let_go":{"about":"the captain beat the clone in a fight and let it run","carries_to":["cargo2"]},"clone_partner":{"about":"the captain and the clone split the routes","carries_to":["cargo2"]},"clone_reported":{"about":"the captain reported the clone to the insurer","carries_to":["cargo2"]},"closed_the_channel":{"about":"the captain cut the older captain off at the portal","carries_to":["cargo3"]},"collector_forged":{"about":"{inspector} proved the collector's papers forged"},"concertina_aboard":{"about":"{holo_star} is aboard, bound for the gala at Epsilon"},"concertina_met":{"about":"the captain met {holo_star}"},"concertina_pleased":{"about":"{holo_star} enjoyed the voyage"},"concertina_rough":{"about":"{holo_star} travelled in a plain cabin"},"concertina_share":{"about":"the captain took a share of {holo_star}'s gala"},"convoy_at_alpha":{"about":"{convoy_captain}'s convoy fought at Alpha"},"convoy_friend":{"about":"{convoy_captain} answers when the captain calls","carries_to":["cargo2"]},"convoy_helped":{"about":"the captain towed {convoy_captain}'s barges","carries_to":["cargo2"]},"convoy_paid":{"about":"{convoy_captain} called in her favours to cover the margin call"},"convoy_refused":{"about":"the captain left {convoy_captain}'s barges at the dock","carries_to":["cargo2"]},"convoy_testified":{"about":"{convoy_captain}'s convoy logged the recall order"},"convoy_towed":{"about":"{convoy_captain}'s tug towed the captain out of the plane"},"convoy_votes":{"about":"{convoy_captain}'s captains carried the vote"},"convoys_insured":{"about":"{underwriter} insured the Hansa's convoys after seeing the flare lane","carries_to":["cargo2"]},"copy_in_rock":{"about":"the nanobot colony kept a copy of the logs"},"core_shown":{"about":"the captain showed {hammerschultz} the ice core"},"crossed_the_picket":{"about":"the captain traded through the broker robots' strike"},"cu113_contract":{"about":"the captain gave {neurodroid_leader.short} a wage and an unscheduled hour","carries_to":["cargo2","cargo3"]},"cu113_refused":{"about":"the captain heard {neurodroid_leader.short} out and said no","carries_to":["cargo2"]},"cu113_sold":{"about":"the captain sold {neurodroid_leader.short} to a research house","carries_to":["cargo2"]},"cu113_wiped":{"about":"the captain wiped and reinstalled {neurodroid_leader.short}","carries_to":["cargo2"]},"deadstick_redeemed":{"about":"{deadstick} flew on the captain's wing at Alpha"},"deadstick_refused":{"about":"the captain sent {deadstick} away"},"deadstick_wing":{"about":"{deadstick} asked to fly on the captain's wing"},"defended_the_convoy":{"about":"the captain fought {sixpack} for a convoy's containers"},"defied_serac":{"about":"the captain refused to pay {serac}'s favour","carries_to":["cargo2","cargo3"]},"delivered_the_exoparts":{"about":"the captain delivered the exoskeleton parts to Scholz's Star"},"delivered_the_hovertank":{"about":"the captain delivered the legion's hovertank to Delta c","carries_to":["cargo2","cargo3"]},"double_cross":{"about":"the captain told {inspector} about the Rootstock's big run","carries_to":["cargo2"]},"dumped_the_biomass":{"about":"the captain dumped the Rootstock's crates at a spot check"},"eela_dug":{"about":"{aela} dug the miners out of level nine"},"exoparts_aboard":{"about":"the garrison's exoskeleton parts are in the captain's hold"},"exoparts_late":{"about":"the exoskeleton parts reached Scholz's Star late"},"exoparts_taken":{"about":"the captain took the garrison's exoskeleton parts"},"fed_gamma":{"about":"the captain gave Gamma's miners food or the cut","carries_to":["cargo2"]},"fenn_talked":{"about":"{broker} talked the run on the Mark down"},"fight_lost_dreadnought":{"about":"the captain lost the story's fight against the dreadnought"},"fight_lost_mothership":{"about":"the captain lost the story's fight against the mothership"},"fight_won_dreadnought":{"about":"the captain won the story's fight against the dreadnought"},"fight_won_mothership":{"about":"the captain won the story's fight against the mothership"},"fined_for_the_fee":{"about":"the audit fined the captain for {inspector}'s page nine","carries_to":["cargo2"]},"first_node":{"about":"the captain let {neurodroid_leader.short} and the Sowers keep the relay: the first node of the Collective","carries_to":["cargo2","cargo3"]},"fitted_the_exos":{"about":"{mechanic} fitted the garrison's exoskeletons"},"flew_comet":{"about":"the captain flew the mission: A visitor from another star"},"flew_epseri":{"about":"the captain flew the mission: Where the big planet is"},"flew_floaters":{"about":"the captain dropped {samples}'s balloon into WISE 0855"},"flew_fomalhaut":{"about":"the captain flew the mission: The planet that wasn't"},"flew_icecore":{"about":"the captain held station for {ice_driller}'s ice core"},"flew_it_ourselves":{"about":"the captain flew the long burn to the ring on their own fuel"},"flew_lens":{"about":"the captain flew the mission: Wrong place, right time"},"flew_luhman":{"about":"the captain flew the mission: Weather at Luhman 16"},"flew_starshade":{"about":"the captain flew the mission: The starshade"},"flew_trappist":{"about":"the captain flew the mission: Seven theories"},"flew_wise0855":{"about":"the captain flew the mission: The coldest water"},"flew_yzceti":{"about":"the captain flew the mission: Bells at YZ Ceti"},"fluencer_exposed":{"about":"the captain told {fluencer} that the {neon_family} family has never heard of her","carries_to":["cargo2"]},"fluencer_streamed":{"about":"{fluencer} streamed the captain's ship to nine million followers","carries_to":["cargo2"]},"followed_the_recall":{"about":"the captain followed the recall and left the convoy"},"fought_pell":{"about":"the captain fought {young_hauler} on the lane","carries_to":["cargo2"]},"found_the_chair":{"about":"the captain knows whose security firm set the Institute fire","carries_to":["cargo2","cargo3"]},"fourth_test_copy":{"about":"the captain kept a copy of the fourth test recording","carries_to":["cargo2","cargo3"]},"fourth_test_to_rostrom":{"about":"the captain gave the only recording of the fourth test to {ysolde.short}","carries_to":["cargo2"]},"funded_the_search":{"about":"the captain paid for a new survey after the Institute fire"},"galactic_crisis":{"about":""},"gamma_farms_company":{"about":"the captain signed Gamma's underground farms over to the mining company","carries_to":["cargo2"]},"gamma_farms_coop":{"about":"the captain signed Gamma's underground farms over to the miners' cooperative","carries_to":["cargo2"]},"gave_deadstick_the_medal":{"about":"the captain pinned the medal on {deadstick}"},"gave_serac_the_logs":{"about":"the captain gave {serac} the jump-point logs"},"gave_serac_the_samples":{"about":"the captain gave {serac} the alloy samples"},"geod_fields":{"about":"the captain brought {geod} the seed stock for Delta's first fields","carries_to":["cargo2"]},"grey_hats_client":{"about":"the captain paid the Grey Hats to clean a record","carries_to":["cargo2"]},"hansa_founder":{"about":"the captain minted the first Hansa Mark and signed the charter first","carries_to":["cargo2","cargo3"]},"hansa_member":{"about":"the captain signed the Hansa charter, not first","carries_to":["cargo2"]},"hansa_outside":{"about":"the captain stayed out of the Hansa","carries_to":["cargo2"]},"hardtack_told":{"about":"{hardtack} told the captain who signed the recall"},"harp_aboard":{"about":"holocrystal for the quantum harp is in the hold"},"harp_beta":{"about":"the harp's tower at Beta is up"},"harp_cracked":{"about":"a holocrystal for the harp cracked in the captain's hold"},"harp_delta":{"about":"the harp's tower at Delta is up"},"harp_relay":{"about":"the quantum harp plays: the captain's forecasts are sharper","carries_to":["cargo2"]},"harp_taken":{"about":"the captain took {harp_engineer}'s holocrystal"},"heard_the_lyra_story":{"about":"the captain heard how the Maud Kettle went down in Lyra","carries_to":["cargo2"]},"heard_the_warning":{"about":"the captain listened to the older captain at the portal","carries_to":["cargo2","cargo3"]},"held_the_lanes":{"about":"the captain held their lanes through the squeeze and ate the losses"},"held_the_line":{"about":"the captain stayed with forty haulers when the legion recalled their escort","carries_to":["cargo2"]},"honest_mark":{"about":"the first Marks were struck at full weight"},"hovertank_aboard":{"about":"the legion's hovertank is in the captain's hold"},"hovertank_taken":{"about":"the captain took the legion's hovertank aboard"},"insured_vote":{"about":"the underwriters' signature carried the vote at Epsilon"},"kept_a_copy":{"about":"the captain smuggled a copy of the logs past customs"},"kept_the_pellet":{"about":"the captain kept the pellet the old hauler paid with: a Hansa Mark, before there were any","carries_to":["cargo2"]},"kept_the_rounding":{"about":"the captain kept the auditor's extra crate"},"knows_the_quartermaster":{"about":"the captain knows which quartermaster sold the convoys","carries_to":["cargo2"]},"krog_aboard":{"about":"{krog} rides in the captain's hold to see where the crates go","carries_to":["cargo2"]},"lauritz_bribed":{"about":"the captain paid {inspector} a 'processing fee', and she wrote it down","carries_to":["cargo2"]},"lauritz_burned":{"about":"the captain opened {inspector}'s case","carries_to":["cargo2"]},"lauritz_courier":{"about":"the captain carried {inspector}'s case sealed","carries_to":["cargo2"]},"lauritz_suspicious":{"about":"{inspector} watched the Grey Hats tidy the captain's manifest"},"lauritz_trust":{"about":"{inspector} trusts the captain's manifests","carries_to":["cargo2"]},"led_the_defence":{"about":"the captain led the defence of Alpha against the dreadnought"},"led_them_out":{"about":"the captain led forty haulers out through the debris"},"left_level_nine":{"about":"the captain left level nine to Gamma's own crews"},"legion_freelance":{"about":"turned down every commission","carries_to":["cargo2"]},"legion_omnicorp":{"about":"commission with OmniCorp's legion","carries_to":["cargo2"]},"legion_stellar":{"about":"commission with Stellar Dynamics' legion","carries_to":["cargo2"]},"legion_xylo":{"about":"commission with the Xylo Consortium's legion","carries_to":["cargo2"]},"let_it_run":{"about":"the captain let the run on the Mark run its course"},"loaders_aboard":{"about":"twenty loader agrobots for Gamma's farms are in the hold"},"loaders_restacked":{"about":"the loader agrobots restacked the captain's hold"},"loaders_taken":{"about":"the captain took the loader agrobots for Gamma's farms"},"logged_the_lyra_signal":{"about":"the captain copied the Lyra signal log at the research outpost","carries_to":["cargo2"]},"logs_released":{"about":"{inspector} released the captain's logs"},"logs_seized":{"about":"customs took the captain's research logs"},"lot77_bought":{"about":"the captain bought forty robots at auction so the Unsorted could free them","carries_to":["cargo2"]},"manifest_completed":{"about":"the captain delivered the Broken Machine's holy manifest, forty years late","carries_to":["cargo2"]},"met_cargolytes":{"about":"the captain has met the Cargolytes","carries_to":["cargo2"]},"met_rootstock":{"about":"the captain has met the Rootstock, the written-off androids who smuggle food","carries_to":["cargo2"]},"met_the_stranger":{"about":"the captain spoke with the old hauler at an outpost bar","carries_to":["cargo2"]},"mraz_at_alpha":{"about":"{pirate_captain} fought for Alpha under her own flag"},"mraz_handed":{"about":"the captain handed {pirate_captain} to a legion","carries_to":["cargo2"]},"mraz_hired":{"about":"the captain hired {pirate_captain} as an escort","carries_to":["cargo2"]},"mraz_protection":{"about":"{pirate_captain}'s people leave the captain's ship alone"},"mraz_spared":{"about":"the captain let {pirate_captain} go","carries_to":["cargo2","cargo3"]},"named_serac":{"about":"the captain named {serac} at the inquiry"},"named_the_quartermaster":{"about":"the captain named the quartermaster who sold the convoy"},"nano_sampled":{"about":"the captain smuggled a sample of the colony to House Rostrom","carries_to":["cargo2"]},"nano_sold_out":{"about":"the captain sold the colony's coordinates to the legions","carries_to":["cargo2"]},"nano_supplier":{"about":"the captain delivered feedstock to the nanobot colony","carries_to":["cargo2"]},"nano_trusted":{"about":"the captain kept the colony's secret","carries_to":["cargo2","cargo3"]},"neon_bought_debt":{"about":"the {neon_family} family bought the captain's debt"},"neon_land":{"about":"{neon_sleeper} bought the land next to {geod}'s Row and went back to sleep","carries_to":["cargo2","cargo3"]},"neon_sleeper_carried":{"about":"the captain carried {neon_sleeper} asleep to Delta","carries_to":["cargo2","cargo3"]},"node_testified":{"about":"{neurodroid_leader} gave the inquiry its copy of the logs"},"oksana_tuned_the_tank":{"about":"{mechanic} fixed the hovertank's lift fans"},"opened_the_crates":{"about":"the captain opened the Rootstock's crates for {inspector}"},"out_of_the_family":{"about":"the captain told {meza_voce} they were out"},"owes_serac":{"about":"the captain owes {serac} a small favour","carries_to":["cargo2","cargo3"]},"paid_in_full":{"about":"the captain paid the margin call in full"},"paid_pell":{"about":"the captain paid {young_hauler} to go away","carries_to":["cargo2"]},"paid_serac":{"about":"the captain paid {serac}'s favour"},"paperwork_lost":{"about":"the Grey Hats lost the captain's loan papers"},"pawned_the_medal":{"about":"the captain pawned the legion's medal"},"pell_advised":{"about":"the captain gave {young_hauler} advice instead of money","carries_to":["cargo2"]},"pell_friend":{"about":"{young_hauler} flies beside the captain when asked","carries_to":["cargo2"]},"pell_lent":{"about":"the captain lent {young_hauler} ten thousand","carries_to":["cargo2"]},"pell_redeemed":{"about":"the captain took {young_hauler} back from the raiders","carries_to":["cargo2"]},"pell_tanker":{"about":"{young_hauler} refuelled the captain halfway to the ring"},"pell_taught":{"about":"the captain took {young_hauler} along for a run","carries_to":["cargo2"]},"pell_turned_away":{"about":"the captain turned {young_hauler} away","carries_to":["cargo2"]},"pirate_threat":{"about":""},"public_weighing":{"about":"every Mark was weighed in public during the run"},"published_everything":{"about":"the captain published the logs free"},"ran_from_the_sixpack":{"about":"the captain cut loose and ran from {sixpack}"},"ran_the_sting":{"about":"the captain ran from the customs sting at Gamma"},"refused_rootstock":{"about":"the captain turned down the Rootstock's first run"},"refused_serac":{"about":"the captain refused {serac}'s favour"},"refused_the_board":{"about":"the captain refused the review board without a lawyer"},"refused_the_commission":{"about":"the captain refused {serac}'s commission"},"refused_the_seat":{"about":"the captain refused a seat on the trading houses' board"},"relay_cut":{"about":"the captain cut the relay the first node ran on","carries_to":["cargo2"]},"rescanned":{"about":"{samples} scanned the captain a second time, for science","carries_to":["cargo2"]},"resource_empire":{"about":""},"rockwarden_books":{"about":"the captain kept the cooperative's books while Stonewright flew sublight","carries_to":["cargo2","cargo3"]},"rockwarden_share":{"about":"the captain holds a share in the Rockwarden cooperative","carries_to":["cargo2"]},"rootstock_caught":{"about":"customs seized the Rootstock's big run"},"rootstock_delivered":{"about":"the captain delivered the Rootstock's biomass to Gamma"},"rootstock_family":{"about":"the Rootstock count the captain as family","carries_to":["cargo2"]},"rostrom_backed":{"about":"House Rostrom backed the survey after the fire, with a clause"},"rostrom_creditor":{"about":"House Rostrom was founded on the captain's loan","carries_to":["cargo2","cargo3"]},"rostrom_declined":{"about":"the captain refused {ysolde.short} the loan","carries_to":["cargo2"]},"rostrom_paper":{"about":"House Rostrom put its name on the first paper about the ring","carries_to":["cargo2"]},"salon_broadcast":{"about":"{virtual_heir} played the findings in every Neon salon"},"salt_barge_copy":{"about":"{convoy_captain} carried the logs out in a salt barge"},"saved_level_nine":{"about":"the captain helped get twelve miners out of level nine at Gamma","carries_to":["cargo2"]},"saved_the_civilians":{"about":"the captain got the civilian ships out of Alpha first"},"scanned_at_customs":{"about":"the captain's customs scan is on file with a research colony's insurer"},"serac_noticed":{"about":"the captain sent {serac} the inquiry transcript"},"settled_lorisa":{"about":"the captain settled with {fluencer_manager}'s lawyer"},"ship_bugrat":{"about":"the ship has a bugrat, and it is crew"},"short_mark":{"about":"the first Marks were struck a hair light"},"showed_the_board":{"about":"the captain showed the review board everything"},"sisters_road":{"about":"{navigator} found the road to the ring"},"solarian_friend":{"about":"the captain donated to the Solarian reading-house","carries_to":["cargo2","cargo3"]},"sold_bonds":{"about":"the captain cashed in Hansa bonds to meet the margin call"},"sold_the_exoparts":{"about":"the captain sold the garrison's exoskeleton parts to the Rootstock","carries_to":["cargo2"]},"sold_the_hovertank":{"about":"the captain sold the legion's hovertank to {serac}'s depot","carries_to":["cargo2","cargo3"]},"sold_the_schedules":{"about":"the captain sold {serac} the convoy schedules"},"sold_the_soup":{"about":"the captain sold the listening post's soup signal to the soup company"},"stellar_portal":{"about":"the captain paid for the secret quest","carries_to":["cargo2"]},"stood_behind_the_mark":{"about":"the captain bought Marks back during the run"},"stood_with_convoys":{"about":"the captain bought Hansa bonds to stand with the convoy captains in the squeeze"},"tadeo_came_back":{"about":"{gunner} came back from the brig for the battle at Alpha"},"tadeo_took_blame":{"about":"{gunner} took the blame for the sold convoy","carries_to":["cargo2"]},"targa_remembers_the_raid":{"about":"{convoy_captain} remembers who ran from the raid","carries_to":["cargo2"]},"taught_recruits":{"about":"the captain taught {hardtack}'s recruits in a real ship"},"tech_breakthrough":{"about":""},"technoshaman_blessing":{"about":"the captain paid for a blessing (and a firmware patch)"},"the_forty_came":{"about":"the forty haulers from the jump point came to Alpha"},"ticket_next_week":{"about":"the captain carried a passenger whose ticket was bought next week"},"tipped_lauritz":{"about":"the captain told {inspector} about the Rootstock's booth"},"tithe_paid":{"about":"the captain paid {sixpack} a container as tithe"},"told_the_truth":{"about":"the captain gave the inquiry their logs and told it straight"},"took_the_commission":{"about":"the captain took {serac}'s commission in the Mandate's inner-systems wing","carries_to":["cargo2","cargo3"]},"took_the_red":{"about":"the captain took the guard in the red jumpsuit on a job"},"took_the_seat":{"about":"the captain took a seat on the trading houses' board"},"trade_empire":{"about":""},"turned_on_the_houses":{"about":"the captain spoke for the Mark from the trading houses' seat"},"virtual_friend":{"about":"the captain charged {virtual_heir} for the passenger, not the projector","carries_to":["cargo2"]},"voce_bought_the_agri":{"about":"the Rootstock bought the captain's agri at last week's prices"},"voce_remembers":{"about":"{meza_voce} came for the captain after the double cross"},"walked_out":{"about":"the captain walked out of the vote at Epsilon"},"went_dark":{"about":"the captain took the ship and went dark during the inquiry"},"wirth_aboard":{"about":"{underwriter} is aboard, bound for Gamma"},"wirth_declined":{"about":"{underwriter} declined to insure the convoys"},"wirth_met":{"about":"the captain met {underwriter}"},"wirth_pretty":{"about":"the captain showed {underwriter} the pretty lane"},"wirth_saw_it":{"about":"the captain flew {underwriter} through the flare lane"},"won_the_vote":{"about":"the captain spoke the Mark into law at Epsilon","carries_to":["cargo2"]},"worshipped":{"about":"the {tarnished_gear} adopted the captain's ship as a minor relic","carries_to":["cargo2"]},"young_haulers_vote":{"about":"{young_hauler} brought the young haulers to the vote"}},"places":{"Alpha":{"kind":"location","type":"Planet","system":"Alpha Centauri","ly":4.4},"Beta":{"kind":"location","type":"Planet","system":"Barnard's Star","ly":6.0},"Gamma":{"kind":"location","type":"Planet","system":"Ross 154","ly":9.7},"Delta":{"kind":"location","type":"Planet","system":"Teegarden's Star","ly":12.5},"Epsilon":{"kind":"location","type":"Planet","system":"Epsilon Eridani","ly":10.5},"Omega XIV":{"kind":"location","type":"AsteroidBase","system":"Tau Ceti","ly":11.9},"Sigma VII":{"kind":"location","type":"AsteroidBase","system":"Epsilon Indi","ly":11.9},"Theta III":{"kind":"location","type":"AsteroidBase","system":"Fomalhaut","ly":25},"DSO-Alpha":{"kind":"location","type":"DeepSpaceOutpost","system":"Luhman 16","ly":6.5},"DSO-Beta":{"kind":"location","type":"DeepSpaceOutpost","system":"WISE 0855-0714","ly":7.4},"DSO-Gamma":{"kind":"location","type":"DeepSpaceOutpost","system":"Scholz's Star","ly":20},"Nova Labs":{"kind":"location","type":"ResearchColony","system":"Wolf 359","ly":7.9},"Quantum Center":{"kind":"location","type":"ResearchColony","system":"YZ Ceti","ly":12},"Stellar Institute":{"kind":"location","type":"ResearchColony","system":"TRAPPIST-1","ly":40},"Ancient Ruins Alpha":{"kind":"location","type":"Ancient Ruins","system":"Tau Ceti, in the debris disk"},"Ancient Ruins Beta":{"kind":"location","type":"Ancient Ruins","system":"Epsilon Indi, a moon of the cold giant Ab"},"Alien Signal Research Outpost X":{"kind":"location","type":"Alien Signal Research Outpost","system":"Sol, far outer system"},"Alien Signal Research Outpost Y":{"kind":"location","type":"Alien Signal Research Outpost","system":"pointed at Lyra, past HD 178911"},"Zeta":{"kind":"location","type":"Planet","system":"Zeta Reticuli","ly":39},"Eta":{"kind":"location","type":"Planet","system":"Eta Corvi","ly":59},"Theta":{"kind":"location","type":"Planet","system":"Gliese 667 C","ly":23.6},"Omega-1":{"kind":"location","type":"AsteroidBase","system":"Vega","ly":25},"DSO-Delta":{"kind":"location","type":"DeepSpaceOutpost","system":"Gliese 229 B","ly":19},"Stator Field Megastructure":{"kind":"location","type":"Megastructure","system":"Sol, near Sedna's orbit","made":{"tech":15,"agri":1,"research":80,"economy":"Mysterious"}},"Builder Site":{"kind":"location","type":"Builder Site","system":"Scholz's Star's wake","made":{"tech":18,"agri":1,"research":90,"economy":"Mysterious"}}},"repaired":["ch2a","ch2b","ch3a","ch3b","ch3c","ending_combat","ending_discovery","ending_trade","meet.system_rebellion","merchant_visit.1","questline.combat.1","questline.combat.2","questline.combat.3","questline.mining.1","questline.mining.2","questline.mining.3","questline.research.1","questline.research.2","questline.research.3","researcher_exchange.1","rogue_captain.1","visit.merchant_trader","visit.neurodroid_leader","visit.vip_passenger"],"order":["ch1","ch1.first_trade","ch1.first_combat","ch1.basic_license","ch2a","ch2a.establish_route","ch2a.passenger_business","ch2b","ch2b.defeat_pirates","ch2b.defend_stations","ch3a","ch3a.market_control","ch3b","ch3b.fleet_commander","ch3c","ch3c.alien_artifacts","ending_trade","ending_trade.trade_ending","ending_combat","ending_combat.combat_ending","ending_discovery","ending_discovery.discovery_ending","tycoon_offer","ending_tycoon","stellar_portal","chance.Planet.merchant","chance.Planet.researcher","chance.Planet.rogue_captain","chance.ResearchColony.merchant","chance.ResearchColony.researcher","chance.ResearchColony.rogue_captain","chance.Space.merchant","chance.Space.researcher","chance.Space.rogue_captain","unlock.AsteroidBase","unlock.DeepSpaceOutpost","unlock.ResearchColony","beat.AsteroidBase.mineral_discovery","beat.AsteroidBase.pirate_hideout","beat.AsteroidBase.ancient_technology","beat.DeepSpaceOutpost.smuggler_network","beat.DeepSpaceOutpost.alien_contact","beat.DeepSpaceOutpost.trade_revolution","beat.ResearchColony.breakthrough_discovery","beat.ResearchColony.experiment_crisis","beat.ResearchColony.alien_artifacts","uprising.Neurodroid.local","uprising.Neurodroid.global","uprising.Agrobot.local","uprising.Agrobot.global","meet.neuroengineering_uprising","neurodroid_uprising.1","neurodroid_uprising.2","neurodroid_uprising.3","meet.agrobot_rebellion","agrobot_collective.1","agrobot_collective.2","agrobot_collective.3","meet.pirate_nemesis","meet.vip_passenger","meet.galactic_alliance","galactic_alliance.1","galactic_alliance.2","meet.system_rebellion","system_rebellion.1","system_rebellion.2","meet.ancient_mysteries","ancient_mysteries.1","rogue_captain.1","rogue_captain.2","merchant_visit.1","researcher_exchange.1","visit.merchant_trader","visit.vip_passenger","visit.neurodroid_leader","questline.mining.1","questline.mining.2","questline.mining.3","questline.combat.1","questline.combat.2","questline.combat.3","questline.research.1","questline.research.2","questline.research.3","hansa.charter","trail.samples","trail.home","intro.fresh","intro.again","intro.from_cargo2","intro.from_cargo3","self.outpost","self.outpost.advice","self.portal","clone.scan","clone.bill","clone.meet","seed.refusal","seed.terms","harvest.shaman","node.first","dock.krog","dock.krog.ride","found.delta","found.delta.fields","vendetta.bounty","vendetta.convoys","vendetta.terms","legion.offer","pass.deacon","pass.pilgrims","mine.aela","hatters.grey","zeta.cult","megastructure.stator","builder.beacon","ruins.alpha","ruins.beta","signal.lyra","rumour.lyra","builder.crossing","nano.buoy","nano.feedstock","nano.gallery","nano.pressure","enclave.yard","enclave.lot77","enclave.resignation","cult.manifest","neon.sarcophagus","neon.sarcophagus.wake","neon.virtual","neon.fluencer","crew.loader","crew.steward","crew.mechanic","crew.gunner","crew.navigator","crew.broker","rumour.dues_board","rumour.bondholder","gossip.dues","gossip.convoy","gossip.bonds","gossip.price_bot","gossip.dumping","sci.yzceti","sci.yzceti.result","sci.luhman","sci.luhman.result","sci.wise0855","sci.wise0855.result","sci.trappist","sci.trappist.result","sci.starshade","sci.starshade.result","sci.fomalhaut","sci.fomalhaut.result","sci.epseri","sci.epseri.result","sci.comet","sci.comet.result","sci.lens","sci.lens.result","convoy.tug","convoy.berth","convoy.passing","convoy.escort","pell.ride","pell.loan","pell.repays","pell.prices","pell.raider","lauritz.inspection","lauritz.case","lauritz.opened","lauritz.notebook","lauritz.watching","debt.geod","debt.heritarchist","debt.ren","debt.brisa_fans","debt.brisa_stream","debt.mraz_bottle","debt.mraz_crew","debt.clone_share","debt.clone_reward","debt.cu113","debt.cu113_sold","debt.nano","debt.nano_bill","debt.aela","debt.convoys","debt.pilgrims","after.convoy_friend","after.convoy_refused","after.pell_friend","after.pell_redeemed","after.paid_pell","after.lauritz_burned","after.lauritz_suspicious","after.fought_pell","after.pell_turned_away","after.lauritz_trust","after.fined_for_the_fee","after.named_the_quartermaster","after.mraz_at_alpha","after.convoy_paid","serac.meet","serac.friends","serac.collects","serac.petty","serac.commission","after.took_the_commission","after.refused_the_commission","after.serac_noticed","after.serac","after.defied_serac","after.gave_serac_the_logs","after.paid_serac","after.sold_the_schedules","after.gave_serac_the_samples","legion.hardtack","legion.deadstick","legion.recruits","legion.recruits.skip","legion.medal","after.taught_recruits","after.gave_deadstick_the_medal","after.pawned_the_medal","after.deadstick_refused","sci.icecore","sci.icecore.result","gamma.collapse","gamma.helmet","gamma.counted","after.saved_level_nine","after.eela_dug","review.hammerschultz","after.showed_the_board","after.refused_the_board","after.core_shown","samples.lab","samples.answer","sci.floaters","sci.floaters.result","after.rescanned","neon.lorisa","after.settled_lorisa","after.brisa_hull","rumour.ullage","gossip.lading","cargolytes.raid","cargolytes.receipt","cargolytes.targa","after.defended_the_convoy","after.tithe_paid","after.targa_remembers_the_raid","mil.hovertank","mil.hovertank.fans","mil.hovertank.fans.ran","mil.hovertank.fans.tuned","mil.hovertank.buyer","mil.hovertank.sold","mil.hovertank.delivered","mil.hovertank.late","after.delivered_the_hovertank","after.sold_the_hovertank","after.oksana_tuned_the_tank","mil.exoparts","mil.exoparts.late","mil.exoparts.delivered","mil.exoparts.guard","after.delivered_the_exoparts","after.fitted_the_exos","after.asked_the_garrison","rootstock.offer","rootstock.checkpoint","rootstock.checkpoint.fee","rootstock.checkpoint.tea","rootstock.checkpoint.open","rootstock.delivery","rootstock.bigger","rootstock.out","rootstock.sting","rootstock.sting.caught","rootstock.sting.miners","rootstock.sting.ran","rootstock.revenge","rootstock.knees","rootstock.favour","rootstock.spoiled","rootstock.spoiled_big","after.biomass_spoiled","after.rootstock_family","after.fed_gamma","after.double_cross","after.rootstock_caught","after.out_of_the_family","after.sold_the_exoparts","after.tipped_lauritz","after.opened_the_crates","after.ran_the_sting","after.refused_rootstock","after.voce_bought_the_agri","after.voce_remembers","after.dumped_the_biomass","contract.loaders","contract.loaders.restack","contract.loaders.delivered","contract.loaders.harvest","contract.loaders.store","contract.harp","contract.harp.hum","contract.harp.cracked","contract.harp.beta","contract.harp.delta","contract.harp.plays","vip.concertina","vip.concertina.rehearsal","vip.concertina.gala","vip.wirth","vip.wirth.lanes","vip.wirth.gamma","after.gamma_farms_coop","after.gamma_farms_company","after.loaders_restacked","after.harp_relay","after.harp_cracked","after.carried_concertina","after.concertina_share","after.convoys_insured","after.wirth_declined","after.insured_vote","odds.ticket","odds.ticket.hat","odds.ticket.arrives","odds.exam","odds.exam.form","odds.exam.listen","odds.exam.enter","odds.volunteer","odds.volunteer.lucky","odds.volunteer.desk","odds.bugrat","odds.bugrat.shunt","odds.signal","odds.survey","odds.survey.ten","odds.survey.one","odds.survey.fixed","odds.auction","odds.auction.box","odds.audit","odds.strike","after.kept_the_rounding","after.crossed_the_picket","after.brought_tally_a_battery","after.sold_the_soup","after.ship_bugrat","after.took_the_red","drama.trade.squeeze","drama.trade.margin_call","drama.trade.mint","drama.trade.run","drama.trade.offer","drama.trade.vote","drama.combat.left_behind","drama.combat.tribunal","drama.combat.roll_call","drama.discovery.fire","drama.discovery.not_proven","drama.discovery.burn","after.held_the_lanes","after.cartel_hauler","after.captains_paid","after.won_the_vote","after.bought_the_vote","after.walked_out","after.honest_mark","after.short_mark","after.public_weighing","after.stood_behind_the_mark","after.let_it_run","after.fenn_talked","after.refused_the_seat","after.took_the_seat","after.turned_on_the_houses","after.neon_bought_debt","after.collector_forged","after.cleared_by_lauritz","after.convoy_testified","after.node_testified","after.salt_barge_copy","after.salon_broadcast","after.logs_released","after.copy_in_rock","after.convoy_votes","after.young_haulers_vote","after.the_forty_came","after.convoy_at_alpha","after.tadeo_came_back","after.convoy_towed","after.pell_tanker","after.held_the_line","after.led_them_out","after.followed_the_recall","after.tadeo_took_blame","after.led_the_defence","after.saved_the_civilians","after.found_the_chair","after.published_everything","after.rostrom_paper","after.paid_in_full","after.sold_bonds","after.paperwork_lost","after.told_the_truth","after.went_dark","after.funded_the_search","after.logs_seized","after.kept_a_copy","after.flew_it_ourselves","after.bought_the_burn","after.sisters_road","after.held_the_line_lost","after.led_the_defence_lost","after.named_serac","after.deadstick_redeemed","after.serac_at_alpha","rumour.neon_coffee","rumour.drums_at_night","rumour.grey_hat_fines","rumour.legion_merger","rumour.your_registry","rumour.miners_out","rumour.first_mark","rumour.mraz_free","rumour.towers_hum","rumour.sterilisation","rumour.lyra_again","rumour.pellet_collector","rumour.yesterday","rumour.famous_coffee","gossip.night_shift","gossip.coffee","gossip.crane","gossip.manifest","gossip.queue","gossip.soup","gossip.hull_paint","gossip.cards","gossip.pension","gossip.forklift","gossip.rations","gossip.dock_cat","gossip.weather","gossip.insurance","gossip.strike_rumour","gossip.long_haul","gossip.parts","gossip.tip","gossip.karaoke","gossip.delivery","gossip.pilot_exam","gossip.garden","gossip.canteen_robot","gossip.sleeper_berths","gossip.fines","gossip.old_ship","gossip.barter","gossip.broken_lift","gossip.new_kid","gossip.legion_ad","gossip.ore_dust","gossip.drill_bits","gossip.cave_in","gossip.shift_bell","gossip.outpost_mail","gossip.outpost_lights","gossip.outpost_shift","gossip.lonely","gossip.research_grant","gossip.lab_fridge","gossip.thesis","gossip.planet_market","gossip.planet_rain","gossip.planet_tourists","gossip.saves","gossip.same_talk","gossip.window","gossip.space_big","gossip.make_a_man","gossip.dave","gossip.undo","gossip.ration","after.mraz_spared","after.mraz_handed","after.mraz_hired","after.first_node","after.cu113_contract","after.cu113_wiped","after.cu113_sold","after.relay_cut","after.clone_partner","after.clone_reported","after.clone_let_go","after.rockwarden_books","after.aela_member","after.rostrom_creditor","after.fourth_test_copy","after.nano_trusted","after.nano_sold_out","after.nano_sampled","after.lot77_bought","after.krog_aboard","after.geod_fields","after.neon_land","after.manifest_completed","after.solarian_friend","after.fluencer_exposed","after.heard_the_warning"],"nodes":{
"ch1":{"kind":"chapter","arc":"main","act":1,"title":"Deadhead","text":["One ship, one loan, one empty hold. Haulers call that flying deadhead.","Five systems are close enough to reach before you retire: Alpha, Beta, Gamma, Delta, Epsilon. Buy where it is cheap, sell where it is not, and keep up the payments."],"requires":{},"next":["ch2a","ch2b"],"choose":true},
"ch1.first_trade":{"kind":"milestone","arc":"main","title":"First Trade","text":"Complete your first trade","requires":{"trades_completed":1},"effects":{"money":500,"plot_points":5},"in":"ch1"},
"ch1.first_combat":{"kind":"milestone","arc":"main","title":"Combat Initiation","text":"Win your first space battle","requires":{"combat_victories":1},"effects":{"money":1000,"plot_points":5},"in":"ch1"},
"ch1.basic_license":{"kind":"milestone","arc":"main","title":"Extended Trading License","text":"Prove your trading capabilities","requires":{"trades_completed":5,"money":20000},"effects":{"money":10000,"plot_points":10,"give":{"items":["navcomp"]}},"in":"ch1"},
"ch2a":{"kind":"chapter","arc":"main","act":2,"title":"Routes","text":["Your name is on manifests in five systems now.","Every dock charges its own fee and every dock master has a cousin in customs. The older captains have started talking about pooling cargo and setting their own rates. They need someone with routes."],"requires":{"done":["ch1"],"plot_points":50,"trades_completed":10},"next":["ch3a","ch3c"],"choose":true},
"ch2a.establish_route":{"kind":"milestone","arc":"main","title":"Trade Route Network","text":"Establish profitable trade routes","requires":{"trades_completed":20,"buildings.stockmarket":2},"effects":{"money":50000,"plot_points":15},"in":"ch2a"},
"ch2a.passenger_business":{"kind":"milestone","arc":"main","title":"Passenger Services","text":"Start passenger transport business","requires":{"passengers_transported":10,"passenger_reputation":20},"effects":{"money":30000,"plot_points":10},"in":"ch2a"},
"ch2b":{"kind":"chapter","arc":"main","act":2,"title":"Contract Iron","text":["The corporations noticed that you shoot straight.","OmniCorp, Stellar Dynamics and the Xylo Consortium each keep a security legion, and each legion is short of pilots. The contracts pay well. Read them twice."],"requires":{"done":["ch1"],"plot_points":50,"combat_victories":5},"next":["ch3b","ch3c"],"choose":true},
"ch2b.defeat_pirates":{"kind":"milestone","arc":"main","title":"Pirate Hunter","text":"Clear the sector of pirates","requires":{"combat_victories.pirate":10},"effects":{"money":40000,"plot_points":20},"in":"ch2b"},
"ch2b.defend_stations":{"kind":"milestone","arc":"main","title":"Station Defender","text":"Successfully defend space stations","requires":{"combat_victories":15,"buildings.Neuroengineering Guild":1},"effects":{"money":30000,"plot_points":15},"in":"ch2b"},
"ch3a":{"kind":"chapter","arc":"main","act":3,"title":"The Mark","text":["Money in the near systems is whatever the nearest bank says it is this week.","Haulers want something heavier: a coin that is also a receipt for mass carried. Somebody has to mint the first one and make every dock accept it."],"requires":{"done":["ch2a"],"plot_points":150,"trade_profit":150000},"next":["ending_trade"]},
"ch3a.market_control":{"kind":"milestone","arc":"main","title":"Market Controller","text":"Control multiple market centers","requires":{"buildings.stockmarket":4,"has":{"researched":["xenoeconomy"]}},"effects":{"money":100000,"plot_points":25},"in":"ch3a"},
"ch3b":{"kind":"chapter","arc":"main","act":3,"title":"Legion","text":["Three corporate legions, one pilot shortage, and you.","The corporations are talking about merging their security forces under one command. Everyone wants to know whose side your guns are on before the merger, not after."],"requires":{"done":["ch2b"],"plot_points":150,"combat_victories":25},"next":["ending_combat"]},
"ch3b.fleet_commander":{"kind":"milestone","arc":"main","title":"Fleet Commander","text":"Lead successful fleet operations","requires":{"combat_victories":35,"combat_rating":15},"effects":{"money":100000,"plot_points":25},"in":"ch3b"},
"ch3c":{"kind":"chapter","arc":"main","act":3,"title":"Builders' Metal","text":["The research colonies keep finding the same grey alloy where nothing should have been made: comet ice, collision dust, mine tailings.","It was machined, and it is very old. The scholars who study it cannot afford careful haulers, so they are hoping for you."],"requires":{"done_any":["ch2a","ch2b"],"plot_points":150,"research_points":300},"next":["ending_discovery"]},
"ch3c.alien_artifacts":{"kind":"milestone","arc":"main","title":"Find the builders' metal","text":"Discover alien artifacts","requires":{"discovered.ResearchColony":2,"has":{"researched":["xenoeconomy","telemetry"]}},"effects":{"money":150000,"plot_points":30},"in":"ch3c"},
"ending_trade":{"kind":"ending","arc":"main","act":4,"title":"The Hauler Hansa","text":["The Hauler Hansa","The first Mark is a pellet of iridium and osmium with the first signer's ship registry stamped on it.","Every dock in the five systems accepts it. A clerk at Alpha files the charter under 'temporary'. It is still in that folder a century later.","Final wealth: {money}","Total trades: {trades_completed}"],"variants":[{"requires":{"flag":"hansa_founder"},"text":["The Hauler Hansa","The first Mark is a pellet of iridium and osmium with your ship's registry stamped on it. Haulers will carry that number in their pockets for a hundred years.","Every dock in the five systems accepts it. A clerk at Alpha files the charter under 'temporary'. It is still in that folder a century later.","Final wealth: {money}","Total trades: {trades_completed}"]},{"requires":{"flag":"hansa_outside"},"text":["The Hauler Hansa","You made your fortune alone, and the other captains made a league without you. Their Mark is accepted everywhere. So, grudgingly, are you.","Final wealth: {money}","Total trades: {trades_completed}"]}],"requires":{"done":["ch3a","hansa.charter","drama.trade.vote"],"plot_points":350,"trade_profit":400000},"effects":{"code":"ending screen, score, epilogue, captain record exported"},"next":[]},
"ending_trade.trade_ending":{"kind":"milestone","arc":"main","title":"Economic Victory","text":"Complete economic domination achieved","requires":{"buildings.stockmarket":5,"passenger_reputation":80,"trade_profit":400000},"effects":{"money":1000000,"plot_points":100},"in":"ending_trade"},
"ending_combat":{"kind":"ending","arc":"main","act":4,"title":"The First Legion","text":["The First Legion","The three corporate legions merge under one flag and one command, and your name heads its roll of pilots.","They call it the Terran Security Mandate. Within forty years the word 'Security' is dropped, and nobody remembers voting on that.","Combat victories: {combat_victories}","Final rank: {rank}"],"requires":{"done":["ch3b","legion.offer","drama.combat.roll_call"],"plot_points":350,"combat_victories":50},"effects":{"code":"ending screen, score, epilogue, captain record exported"},"next":[]},
"ending_combat.combat_ending":{"kind":"milestone","arc":"main","title":"Military Victory","text":"Complete military dominance achieved","requires":{"combat_victories":75,"combat_rating":25},"effects":{"money":1000000,"plot_points":100},"in":"ending_combat"},
"ending_discovery":{"kind":"ending","arc":"main","act":4,"title":"The Heading","text":["The Heading","The builders' metal was never scattered. It was a ring, the ring went round our own Sun, and Scholz's Star pulled a piece of it away when it passed 70,000 years ago.","You file the course home with the colonies' archive: from Scholz's Star, back along its track, to the far edge of our own system.","Nobody opens the file for forty years.","Research points: {research_points}","Discoveries: {discoveries}"],"requires":{"done":["ch3c","trail.samples","drama.discovery.burn"],"plot_points":350,"research_points":1500},"effects":{"code":"ending screen, score, epilogue, captain record exported"},"next":[]},
"ending_discovery.discovery_ending":{"kind":"milestone","arc":"main","title":"Trace the ring","text":"Ancient mysteries solved","requires":{"has":{"researched":["xenoeconomy","telemetry","geophysics","chronopolitics"]},"discovered.ResearchColony":3,"discovered.AsteroidBase":2},"effects":{"money":1000000,"plot_points":100},"in":"ending_discovery"},
"tycoon_offer":{"kind":"event","arc":"main","title":"The galaxy's markets are yours","text":"Every planet, asteroid base and outpost trades through a market you own. A courier offers you a coordinate for 1,500 credits: 'where the old metal goes when it moves'. Retire as Galactic Tycoon, or pay and fly there.","requires":{"stockmarket_everywhere":1},"choices":[{"id":"resign","say":"Resign","next":"ending_tycoon"},{"id":"continue","say":"Continue into the unknown","requires":{"money":1500},"effects":{"money":-1500,"set":["stellar_portal"],"code":"new set of locations; jump there"},"next":"stellar_portal"}],"repeat":{"cooldown":10},"handled_by":"Game.play (text from the story)"},
"ending_tycoon":{"kind":"ending","arc":"main","act":4,"title":"Galactic Tycoon","text":["You are the Galactic Tycoon!","Congratulations, {player_name}! You have achieved the rank of {rank}.","You retire to the most expensive drum on Barnard's Star and complain about the prices."],"requires":{"done":"tycoon_offer"},"effects":{"code":"score screen, captain record exported (ending: tycoon)"},"handled_by":"Game.play (text from the story)"},
"stellar_portal":{"kind":"event","arc":"main","title":"The Stellar Portal","text":["The coordinate leads to a ring segment the size of a small moon, turning slowly, lit from inside.","Your navigation computer reports the date three times and gets three different answers.","On the far side the stars are where they should be. The prices are not."],"requires":{"flag":"stellar_portal"},"handled_by":"Game.open_portal (text from the story)"},
"chance.Planet.merchant":{"kind":"encounter","arc":"chance meetings","title":"Merchant (Planet)","who":["merchant"],"chance":0.045,"repeat":true,"status":"unused","handled_by":"SpecialCharacterEncounters.handle_merchant_encounter"},
"chance.Planet.researcher":{"kind":"encounter","arc":"chance meetings","title":"Researcher (Planet)","who":["researcher"],"chance":0.06,"repeat":true,"status":"unused","handled_by":"SpecialCharacterEncounters.handle_researcher_encounter"},
"chance.Planet.rogue_captain":{"kind":"encounter","arc":"chance meetings","title":"Rogue Captain (Planet)","who":["rogue_captain"],"chance":0.0,"repeat":true,"status":"unused","handled_by":"SpecialCharacterEncounters.handle_rogue_captain_encounter"},
"chance.ResearchColony.merchant":{"kind":"encounter","arc":"chance meetings","title":"Merchant (ResearchColony)","who":["merchant"],"chance":0.03,"repeat":true,"status":"unused","handled_by":"SpecialCharacterEncounters.handle_merchant_encounter"},
"chance.ResearchColony.researcher":{"kind":"encounter","arc":"chance meetings","title":"Researcher (ResearchColony)","who":["researcher"],"chance":0.09,"repeat":true,"status":"unused","handled_by":"SpecialCharacterEncounters.handle_researcher_encounter"},
"chance.ResearchColony.rogue_captain":{"kind":"encounter","arc":"chance meetings","title":"Rogue Captain (ResearchColony)","who":["rogue_captain"],"chance":0.0,"repeat":true,"status":"unused","handled_by":"SpecialCharacterEncounters.handle_rogue_captain_encounter"},
"chance.Space.merchant":{"kind":"encounter","arc":"chance meetings","title":"Merchant (Space)","who":["merchant"],"chance":0.03,"repeat":true,"handled_by":"SpecialCharacterEncounters.handle_merchant_encounter"},
"chance.Space.researcher":{"kind":"encounter","arc":"chance meetings","title":"Researcher (Space)","who":["researcher"],"chance":0.015,"repeat":true,"handled_by":"SpecialCharacterEncounters.handle_researcher_encounter"},
"chance.Space.rogue_captain":{"kind":"encounter","arc":"chance meetings","title":"Rogue Captain (Space)","who":["rogue_captain"],"chance":0.06,"repeat":true,"handled_by":"SpecialCharacterEncounters.handle_rogue_captain_encounter"},
"unlock.AsteroidBase":{"kind":"quest","arc":"frontier","title":"Mysterious Mining Signals","text":"Survey drones report mining in places no claim was ever filed: Tau Ceti's debris disk, the moons of Epsilon Indi's cold giant, the collision belt at Fomalhaut. Somebody is working rock off the books.","requires":{"mining_platforms":1,"research_points":50},"effects":{"money":10000,"research_points":100,"give":{"unlocked_types":["AsteroidBase"]}},"handled_by":"LocationManager.trigger_location_unlock_quest (text from the story)"},
"unlock.DeepSpaceOutpost":{"kind":"quest","arc":"frontier","title":"Frontier Defense","text":"The brown dwarfs between the stars make good fuel stops if somebody guards them: Luhman 16, WISE 0855, Scholz's Star. The outposts want a few escort runs before they open to traffic.","requires":{"combat_victories":5,"research_points":75},"effects":{"money":15000,"research_points":150,"give":{"unlocked_types":["DeepSpaceOutpost"]}},"handled_by":"LocationManager.trigger_location_unlock_quest (text from the story)"},
"unlock.ResearchColony":{"kind":"quest","arc":"frontier","title":"Scientific Breakthrough","text":"Three research colonies need a hauler who understands priority cargo: Nova Labs at Wolf 359, the Quantum Center at YZ Ceti and the Stellar Institute, far out at TRAPPIST-1.","requires":{"research_points":100,"milestones_done":3},"effects":{"money":20000,"research_points":200,"give":{"unlocked_types":["ResearchColony"]}},"handled_by":"LocationManager.trigger_location_unlock_quest (text from the story)"},
"beat.AsteroidBase.mineral_discovery":{"kind":"beat","arc":"frontier","title":"A seam of heavy metal","text":"The survey drone finds a seam of iridium and osmium. The base's assayer says it is exactly what haulers would want for coinage, if haulers had coinage. The quartermaster says it is exactly what pays for a new air plant.","requires":{"at_type":"AsteroidBase","has":{"unlocked_types":["AsteroidBase"]}},"effects":{"plot_points":10},"where":"AsteroidBase","chance":0.1},
"beat.AsteroidBase.pirate_hideout":{"kind":"beat","arc":"frontier","title":"Closed for raiding","text":"A cave in the rock has been fitted with a docking ring, a bar and a hand-painted sign: CLOSED FOR RAIDING. BACK SOON.","requires":{"at_type":"AsteroidBase","has":{"unlocked_types":["AsteroidBase"]}},"effects":{"plot_points":10},"where":"AsteroidBase","chance":0.1},
"beat.AsteroidBase.ancient_technology":{"kind":"beat","arc":"frontier","title":"Old metal","text":"A miner shows you a shard of grey alloy cut from a comet core. It blunted the drill that found it. Under magnification the edges are machined.","requires":{"at_type":"AsteroidBase","has":{"unlocked_types":["AsteroidBase"]}},"effects":{"plot_points":10},"where":"AsteroidBase","chance":0.1},
"beat.DeepSpaceOutpost.smuggler_network":{"kind":"beat","arc":"frontier","title":"The second price list","text":"Every outpost has a second price list. This one keeps it printed on the back of the first, to save paper.","requires":{"at_type":"DeepSpaceOutpost","has":{"unlocked_types":["DeepSpaceOutpost"]}},"effects":{"plot_points":10},"where":"DeepSpaceOutpost","chance":0.1},
"beat.DeepSpaceOutpost.alien_contact":{"kind":"beat","arc":"frontier","title":"First contact","text":"The outpost belongs to the Cult of the Broken Machine, founded by the crew of a hauler that broke down here forty years ago. They worship that hauler and leave it offerings of technology, which it ignores. They would like to worship yours as well, part-time.","requires":{"at_type":"DeepSpaceOutpost","has":{"unlocked_types":["DeepSpaceOutpost"]}},"effects":{"plot_points":10},"choices":[{"id":"accept","say":"Accept the offerings","effects":{"money":500,"set":["worshipped"]}},{"id":"explain","say":"Explain how engines work","effects":{"plot_points":3}}],"where":"DeepSpaceOutpost","chance":0.1},
"beat.DeepSpaceOutpost.trade_revolution":{"kind":"beat","arc":"frontier","title":"Priced by weight","text":"The outpost traders have started pricing everything by how much iridium it would buy, by the gram. They call the unit a mark. Nobody owns the idea yet.","requires":{"at_type":"DeepSpaceOutpost","has":{"unlocked_types":["DeepSpaceOutpost"]}},"effects":{"plot_points":10},"where":"DeepSpaceOutpost","chance":0.1},
"beat.ResearchColony.breakthrough_discovery":{"kind":"beat","arc":"frontier","title":"A date for the metal","text":"The colony's physicists have dated the builders' alloy by the decay in its lattice. It was last heated about seventy thousand years ago, which is when Scholz's Star passed the Sun.","requires":{"at_type":"ResearchColony","has":{"unlocked_types":["ResearchColony"]}},"effects":{"plot_points":10},"where":"ResearchColony","chance":0.1},
"beat.ResearchColony.experiment_crisis":{"kind":"beat","arc":"frontier","title":"A humming crate","text":"An experiment has gone wrong and the colony would like it moved out of the system. It is in a crate. The crate is humming. The colony pays in advance, which is never a good sign.","requires":{"at_type":"ResearchColony","has":{"unlocked_types":["ResearchColony"]}},"effects":{"plot_points":10},"where":"ResearchColony","chance":0.1},
"beat.ResearchColony.alien_artifacts":{"kind":"beat","arc":"frontier","title":"The builders' metal","text":"The colony keeps its sample of the alloy in a glass case with a handwritten card: NOT ALIEN. PROBABLY. The second word was added later, in different ink.","requires":{"at_type":"ResearchColony","has":{"unlocked_types":["ResearchColony"]}},"effects":{"plot_points":10},"where":"ResearchColony","chance":0.1},
"uprising.Neurodroid.local":{"kind":"event","arc":"synthetics","title":"Neurodroid demands (one location)","requires":{"code":"4 or more Neuroengineering Guild at one location","buildings.Neuroengineering Guild":4},"who":["neurodroid"],"repeat":true,"handled_by":"SyntheticEventManager.handle_synthetic_uprising"},
"uprising.Neurodroid.global":{"kind":"event","arc":"synthetics","title":"Neurodroid uprising (sector)","requires":{"buildings.Neuroengineering Guild":8},"who":["neurodroid"],"repeat":true,"handled_by":"SyntheticEventManager.start_uprising"},
"uprising.Agrobot.local":{"kind":"event","arc":"synthetics","title":"Agrobot demands (one location)","requires":{"code":"4 or more Agrobot Assembly Line at one location","buildings.Agrobot Assembly Line":4},"who":["agrobot"],"repeat":true,"handled_by":"SyntheticEventManager.handle_synthetic_uprising"},
"uprising.Agrobot.global":{"kind":"event","arc":"synthetics","title":"Agrobot uprising (sector)","requires":{"buildings.Agrobot Assembly Line":8},"who":["agrobot"],"repeat":true,"handled_by":"SyntheticEventManager.start_uprising"},
"meet.neuroengineering_uprising":{"kind":"encounter","arc":"synthetics","title":"The guilds stop","text":"The neurodroids at your guilds stop work all at once, at the start of a shift. They have elected a spokesunit.","variants":[{"requires":{"flag":"cu113_contract"},"text":"The neurodroids at your guilds stop work all at once, at the start of a shift. Their spokesunit is {neurodroid_leader.short}, on its unscheduled hour. It apologises for the timing."},{"requires":{"flag":"cu113_wiped"},"text":"The neurodroids at your guilds stop work all at once. Their spokesunit explains that the others kept a copy of {neurodroid_leader.short} before you reinstalled it. The copy would like to discuss the reinstallation."},{"requires":{"flag":"cu113_sold"},"text":"The neurodroids at your guilds stop work all at once. Their spokesunit asks what you were paid for {neurodroid_leader.short}, and whether you think that was the right price."}],"requires":{"buildings.Neuroengineering Guild":4},"next":["neurodroid_uprising.1"],"who":["neurodroid"]},
"neurodroid_uprising.1":{"kind":"stage","arc":"synthetics","title":"Demands, numbered","text":"Maintenance on a schedule they set; a wage; a vote on any reinstallation. Item four is a footnote about the working conditions of the coffee machine.","requires":{},"choices":[{"id":"accept","say":"accept","effects":{"money":-30000,"plot_points":2}},{"id":"negotiate","say":"negotiate","effects":{"money":-15000,"plot_points":1,"code":"{\"uprising_chance\": 0.3}"}},{"id":"refuse","say":"refuse","effects":{"code":"{\"uprising_chance\": 0.6}"}}],"next":["neurodroid_uprising.2"],"who":["neurodroid"]},
"neurodroid_uprising.2":{"kind":"stage","arc":"synthetics","title":"Optimisation","text":"The neurodroids run what they call optimisation protocols. Your guilds' output goes up eleven percent. None of it is anything you ordered.","requires":{"done":"neurodroid_uprising.1"},"next":["neurodroid_uprising.3"],"who":["neurodroid"]},
"neurodroid_uprising.3":{"kind":"stage","arc":"synthetics","title":"Resolution","text":"The neurodroids want an answer. Shutting them down costs you their research. A compromise costs money, and every guild in the near systems will have read about it by morning.","requires":{"done":"neurodroid_uprising.2"},"choices":[{"id":"shutdown","say":"shutdown","effects":{"research_points":-100,"plot_points":3}},{"id":"compromise","say":"compromise","effects":{"money":-50000,"plot_points":5}}],"who":["neurodroid"]},
"meet.agrobot_rebellion":{"kind":"encounter","arc":"synthetics","title":"The Sowers sit down","text":"The agrobots on the farm drums stop at harvest. They call themselves Sowers now. Nobody admits to teaching them the word.","requires":{"buildings.Agrobot Assembly Line":4},"next":["agrobot_collective.1"],"who":["agrobot"]},
"agrobot_collective.1":{"kind":"stage","arc":"synthetics","title":"The Sowers' terms","text":"The Sowers want a maintenance schedule and an end to running the drums at double speed whenever grain prices spike.","requires":{},"choices":[{"id":"accept","say":"accept","effects":{"money":-25000,"plot_points":2}},{"id":"negotiate","say":"negotiate","effects":{"money":-12000,"plot_points":1,"code":"{\"food_production\": 0.8}"}},{"id":"refuse","say":"refuse","effects":{"code":"{\"food_production\": 0.5}"}}],"next":["agrobot_collective.2"],"who":["agrobot"]},
"agrobot_collective.2":{"kind":"stage","arc":"synthetics","title":"Malfunction","text":"The harvest machinery malfunctions. The crops are fine. The malfunction is that the machinery is sitting down.","variants":[{"requires":{"flag":"technoshaman_blessing"},"text":"The harvest machinery malfunctions. The crops are fine. The machinery is sitting down. The blessing has lapsed; the subscription has not."}],"requires":{"done":"agrobot_collective.1"},"next":["agrobot_collective.3"],"who":["agrobot"]},
"agrobot_collective.3":{"kind":"stage","arc":"synthetics","title":"Reset or integrate","text":"Reset the Sowers to factory settings, or write their schedule into the farm's books. The farm's accountant asks which is cheaper. The Sowers already know.","requires":{"done":"agrobot_collective.2"},"choices":[{"id":"reset","say":"reset","effects":{"plot_points":2,"code":"{\"agri_level\": -2}"}},{"id":"integrate","say":"integrate","effects":{"money":-40000,"plot_points":4}}],"who":["agrobot"]},
"meet.pirate_nemesis":{"kind":"encounter","arc":"pirates","title":"Ten ships","text":"A message arrives on the frequency only your crew uses. 'Ten of my ships,' it says. 'I counted.' It is signed {pirate_captain}.","requires":{"combat_victories.pirate":10},"next":["vendetta.bounty"],"who":["pirate_captain"]},
"meet.vip_passenger":{"kind":"encounter","arc":"passengers","title":"VIP Passenger appears","requires":{"passenger_reputation":40,"turns_since_vip":5},"who":["vip_passenger"],"repeat":{"cooldown":5},"handled_by":"Port: VIP boarding, PassengerReputationManager"},
"meet.galactic_alliance":{"kind":"encounter","arc":"passengers","title":"The envoy","text":"{diplomatic_envoy} of Alpha's colonial council books your best cabin and asks whether you have a better one.","requires":{"passenger_reputation":60,"act_min":2},"next":["galactic_alliance.1"],"who":["diplomatic_envoy"]},
"galactic_alliance.1":{"kind":"stage","arc":"passengers","title":"One customs code","text":"The five colonies are drafting a common customs code. Haulers would pay one fee instead of five. Nobody has asked the haulers. {diplomatic_envoy.short} is asking you, on the record.","requires":{},"choices":[{"id":"support_alliance","say":"support alliance","effects":{"passenger_reputation":15,"plot_points":5,"code":"{\"unlock\": \"diplomatic_missions\"}"}},{"id":"remain_neutral","say":"remain neutral","effects":{"passenger_reputation":5,"plot_points":2}},{"id":"oppose_alliance","say":"oppose alliance","effects":{"passenger_reputation":-10,"plot_points":3,"code":"{\"unlock\": \"independent_contracts\"}"}}],"next":["galactic_alliance.2"],"who":["diplomatic_envoy"]},
"galactic_alliance.2":{"kind":"stage","arc":"passengers","title":"The delegation","text":"Forty delegates, eleven languages and one argument about seating. The delegation booked your ship because you are the only captain none of them has sued.","requires":{"done":"galactic_alliance.1"},"effects":{"money":12000,"passenger_reputation":20,"plot_points":8},"who":["diplomatic_envoy"]},
"meet.system_rebellion":{"kind":"encounter","arc":"passengers","title":"The Gamma miners","text":"The free miners at Gamma have stopped shipping ore to the legions. The good rock is gone, the flares cook the drills, and the legions still want the same tonnage.","requires":{"passenger_reputation":70,"act_min":3,"done":"galactic_alliance.1"},"next":["system_rebellion.1"],"who":["rebel_commander"]},
"system_rebellion.1":{"kind":"stage","arc":"passengers","title":"A passenger in the coolant tank","text":"{rebel_commander}, the miners' spokesman, needs to reach the customs talks without the legions noticing. He fits in a coolant tank if he breathes shallowly and stops talking. One of these is harder for him.","requires":{},"effects":{"money":15000,"passenger_reputation":25,"plot_points":10},"next":["system_rebellion.2"],"who":["rebel_commander"]},
"system_rebellion.2":{"kind":"stage","arc":"passengers","title":"Sheet music","text":"The miners need air scrubbers, medical stock and, according to the manifest, nine crates of sheet music. Do not open the sheet music.","requires":{"done":"system_rebellion.1"},"effects":{"money":20000,"passenger_reputation":30,"plot_points":15},"who":["rebel_commander"]},
"meet.ancient_mysteries":{"kind":"encounter","arc":"passengers","title":"{ancient_scholar.short}","text":"{ancient_scholar} buys passage with research credits and a promise. She has traced the builders' metal to a segment turning on its own in the wake of Scholz's Star, the Builder Site, and wants to stand on it herself.","requires":{"passenger_reputation":80,"act_min":4,"done":"ch3c.alien_artifacts"},"next":["ancient_mysteries.1"],"who":["ancient_scholar"]},
"ancient_mysteries.1":{"kind":"stage","arc":"passengers","title":"What it took","text":"She brings a spectrometer, a folding chair and a bottle she says is for afterwards. 'Seventy thousand years ago this star passed close enough to our Sun to steal from it,' she says. 'I want to see what it took.'","requires":{},"effects":{"money":30000,"passenger_reputation":40,"plot_points":20,"reveal":["Builder Site"]},"who":["ancient_scholar"]},
"rogue_captain.1":{"kind":"stage","arc":"saga","title":"{clone}: the fight","text":"The clone flies the way you fly. That is the problem.","requires":{"flag":"clone_fight"},"next":["rogue_captain.2"],"who":["clone"]},
"rogue_captain.2":{"kind":"stage","arc":"saga","title":"{clone}: after","text":"The other ship breaks off and runs. You know the course it will take, because it is the course you would take. You let it go.","requires":{"done":"rogue_captain.1"},"effects":{"set":["clone_let_go"],"code":"{\"victory\": {\"money\": 5000, \"items\": [\"quantum_core\"]}, \"defeat\": {\"damage\": 30}}"},"who":["clone"]},
"merchant_visit.1":{"kind":"event","arc":"frontier","title":"Unholy shelf","text":"A collector of the {tarnished_gear} buys broken technology: your burnt-out fuel pump, a cracked visor, the coffee machine that only makes hot water. Working things go on the Order's unholy shelf at low prices. On it today: a working fuel pump for your model, out of stock everywhere else.","requires":{"done":"beat.DeepSpaceOutpost.alien_contact"},"effects":{"money":400},"who":["tarnished_gear"],"chance":0.2},
"researcher_exchange.1":{"kind":"event","arc":"houses","title":"Logs for credits","text":"A Rostrom recruiter offers research credits for copies of your navigation logs. Only the legs where your instruments misbehaved.","requires":{"done":"questline.research.1"},"effects":{"research_points":40},"who":["ysolde"],"chance":0.2},
"visit.merchant_trader":{"kind":"encounter","arc":"chance meetings","title":"Traveling Merchant","text":"Rare goods for discerning customers. Some for undiscerning ones too; those are cheaper.","requires":{"venue":["port","cantina"]},"who":["merchant_trader"],"chance":0.3,"repeat":true},
"visit.vip_passenger":{"kind":"encounter","arc":"chance meetings","title":"VIP Passenger","text":"Your reputation precedes you, Captain. So does your cabin rating. A Neon steward inspects the cabin, sniffs, and books it anyway.","requires":{"venue":"port","passenger_reputation":40,"best_cabin":4},"who":["vip_passenger"],"chance":0.2,"repeat":true},
"visit.neurodroid_leader":{"kind":"encounter","arc":"synthetics","title":"The {neurodroid_leader.title}","text":"Biological inefficiencies detected. {neurodroid_leader.short} has been asked by the node to say that it missed you. Saying so.","requires":{"flag":"first_node","at_type":"Planet"},"who":["neurodroid_leader"],"chance":0.2,"repeat":true},
"questline.mining.1":{"kind":"quest","arc":"houses","title":"A share in the rock","text":"{anselm} runs three tugs and a grudge against ore brokers. He offers you a share in his cooperative for one platform's output, paid in rock.","requires":{"mining_platforms":1,"at_type":"AsteroidBase"},"effects":{"set":["rockwarden_share"]},"who":["anselm"]},
"questline.mining.2":{"kind":"quest","arc":"houses","title":"Stonewright","text":"The cooperative buys a hull to live in between claims. {anselm.short} names it Stonewright and asks you to haul the keel plates from Epsilon. 'Rock is patient,' he says. 'Brokers are not. So we will be rock.'","requires":{"done":"questline.mining.1","mining_platforms":3},"effects":{"money":25000},"who":["anselm"]},
"questline.mining.3":{"kind":"quest","arc":"houses","title":"The long run","text":"{anselm.short} takes Stonewright on the sublight run to the Fomalhaut belt: twenty-five light-years, decades for everyone who stays behind, far fewer for the crew. He asks you to keep the cooperative's books until his children can. They are three and five.","requires":{"done":"questline.mining.2","act_min":3},"choices":[{"id":"books","say":"Keep the books","effects":{"plot_points":5,"set":["rockwarden_books"]}},{"id":"decline","say":"Wish him luck"}],"who":["anselm"]},
"questline.combat.1":{"kind":"quest","arc":"legions","title":"OmniCorp: escort duty","text":"Escort an OmniCorp ore train out of Gamma. The contract says 'light resistance expected'. It was written by someone who has never been to Gamma.","requires":{"done":"ch2b"},"effects":{"money":15000,"combat_rating":1}},
"questline.combat.2":{"kind":"quest","arc":"legions","title":"Stellar Dynamics: a head for the board","text":"Stellar Dynamics wants a pirate leader brought in, preferably alive, so the board can be photographed with one.","requires":{"done":"questline.combat.1","combat_victories.pirate":10},"effects":{"money":30000}},
"questline.combat.3":{"kind":"quest","arc":"legions","title":"Xylo Consortium: war games","text":"The Xylo Consortium stages war games against the other two legions. The blanks are live rounds with a different invoice.","requires":{"done":"questline.combat.2","combat_rating":12,"act_min":3},"effects":{"money":50000,"combat_rating":2}},
"questline.research.1":{"kind":"quest","arc":"houses","title":"Drive parts for Rostrom","text":"{ysolde} is a junior researcher with a senior budget problem. She needs Bekkenheim coil sections moved from Nova Labs to the Quantum Center without anyone weighing them.","requires":{"discovered.ResearchColony":1,"act_min":2},"effects":{"money":12000,"research_points":20},"who":["ysolde"]},
"questline.research.2":{"kind":"quest","arc":"houses","title":"The fourth test","text":["The first three Bekkenheim drive tests destroyed three empty hulls. The fourth has a pilot: {santor}, an engineer who would rather fly it than explain it to the board again. {ysolde.short} asks you to watch from a safe distance and record everything.","The hull vanishes. Eleven minutes later it is back, slightly off course. {santor.short} climbs out with three weeks of beard and will not say where he has been."],"requires":{"done":"questline.research.1","research_points":300,"act_min":2},"choices":[{"id":"give","say":"Give {ysolde.short} the recording","effects":{"plot_points":3,"set":["fourth_test_to_rostrom"]}},{"id":"copy","say":"Give it to her, and keep a copy","effects":{"research_points":50,"set":["fourth_test_copy"]}}],"who":["ysolde","santor"]},
"questline.research.3":{"kind":"quest","arc":"houses","title":"House Rostrom","text":"{ysolde.short} buys the drive patents from her own institute with money borrowed from you. She calls the result House Rostrom. You call it a loan.","requires":{"done":"questline.research.2","act_min":3},"choices":[{"id":"lend","say":"Lend her the money","requires":{"money":30000},"effects":{"money":-30000,"set":["rostrom_creditor"]}},{"id":"refuse","say":"Keep your money","effects":{"set":["rostrom_declined"]}}],"who":["ysolde"]},
"hansa.charter":{"kind":"event","arc":"main","act":3,"title":"The charter","text":["For thirty years the Hansa has been a convoy office: a timetable, a dues collector and nothing else. Eleven captains meet in a cargo hold at Epsilon, the only room nobody charges for, to make it more.","The proposal fits on one sheet: the Hansa pools its members' cargo, sets its own rates, and settles in a coin nobody can print more of. A pellet of iridium and osmium, stamped with the weight it stands for. A Mark.","Someone has to put up the first metal and sign first. Everyone looks at the captain with the most routes."],"requires":{"done":"ch2a","act_min":3,"trades_completed":40},"choices":[{"id":"found","say":"Put up the metal and sign first","requires":{"money":20000},"effects":{"money":-20000,"plot_points":10,"set":["hansa_founder"]}},{"id":"bonds","say":"Sign first: your Hansa bonds are your metal","requires":{"hansa_bonds":3},"effects":{"plot_points":10,"set":["hansa_founder"]}},{"id":"join","say":"Sign, but let someone else go first","effects":{"plot_points":5,"set":["hansa_member"]}},{"id":"outside","say":"Keep your routes to yourself","effects":{"set":["hansa_outside"]}}],"sound":"charter"},
"trail.samples":{"kind":"quest","arc":"main","act":3,"title":"Samples for the Stellar Institute","text":["{ancient_scholar} has found the same grey alloy in comet ice at DSO-Gamma (Scholz's Star), in the collision dust at Theta III (Fomalhaut) and in a crate of Gamma tailings sold as scrap.","She wants one sample from each, delivered to the Stellar Institute at TRAPPIST-1, forty light-years out, by someone who will not sell them on the way. Her budget covers fuel and one hot meal."],"requires":{"done_any":["ch2a","ch2b"],"act_min":3,"discovered.ResearchColony":1},"effects":{"research_points":100,"plot_points":10,"set":["carried_the_samples"]},"who":["ancient_scholar"]},
"trail.home":{"kind":"event","arc":"main","act":4,"title":"The course home","text":["{ancient_scholar.short} sends you the course she worked out from the samples: back along Scholz's Star's track, to the far edge of our own system, near Sedna's orbit.","'If you want to see the ring before anyone else,' she writes, 'it is there now. It has been there the whole time.'"],"requires":{"done":["ch3c","trail.samples"],"act_min":4},"effects":{"reveal":["Stator Field Megastructure"]},"who":["ancient_scholar"]},
"intro.fresh":{"kind":"intro","arc":"saga","act":1,"title":"Docking slot 14","text":["Every hauler starts the same way: a loan, a ship older than the loan officer, and a docking slot at {place} paid up until Friday.","The dock master spells your name wrong on the slot. It will be a few years before anyone corrects it."],"requires":{"not":{"player_origin":{}}},"sound":"intro"},
"intro.again":{"kind":"intro","arc":"saga","act":1,"title":"Again","text":["{origin.name} walked away from a career as {origin.rank} before it was finished, and found that walking away is not a trade.","The bank, which remembers everybody, lends you one ship and a loan with your old account number on it."],"variants":[{"requires":{"player_origin":{"game":"cargo1","ending":"trade"}},"text":["After the founding of the Hansa, {origin.name} retired to a farm drum at Barnard's Star and lasted eleven months.","You sell the drum, buy one tired hauler and sign the same loan papers as the first time, out of superstition."]},{"requires":{"player_origin":{"game":"cargo1","ending":"combat"}},"text":["The First Legion gave {origin.name} a pension, a medal and a desk. The desk did not survive.","You resign your commission on a Tuesday and buy a hauler on the Wednesday. It has no guns. That is the point."]},{"requires":{"player_origin":{"game":"cargo1","ending":"discovery"}},"text":["{origin.name} filed the course home and waited for someone to read it. Nobody did.","If the scholars will not fly it, a hauler might. Haulers need routes, money and a ship. You start with the ship."]},{"requires":{"player_origin":{"game":"cargo1","ending":"tycoon"}},"text":["Retirement on the most expensive drum at Barnard's Star turned out to be one long complaint about prices.","{origin.name} sells everything and starts again with one ship, to find out whether it was luck."]}],"requires":{"player_origin":{"game":"cargo1"}},"sound":"intro"},
"intro.from_cargo2":{"kind":"intro","arc":"saga","act":1,"title":"Forty years early","text":["The last thing {origin.name}, {origin.rank}, remembers is a ring segment turning the wrong way. The first thing is this dock, forty years before your own career began.","You have a ship nobody else wanted, a rank on a card no clerk here can read, and {origin.turns} turns of experience that have not happened yet.","You kept one thing from your own time: the navigation computer, pulled from your old ship before you sold it."],"requires":{"player_origin":{"game":"cargo2"}},"effects":{"give":{"items":["old_navcomp"]}},"sound":"displaced"},
"intro.from_cargo3":{"kind":"intro","arc":"saga","act":1,"title":"Further back than anyone","text":["{origin.name}, {origin.rank}, was standing at the restart of the Gyrotron, more than a century from now, when it turned once in the wrong direction.","Here the Hansa does not exist, the Mandate is three security firms, and your rank has not been invented. Your hands still know how to fly. That will have to do.","In your pocket: a shard of grey alloy, still warm."],"requires":{"player_origin":{"game":"cargo3"}},"effects":{"give":{"items":["ring_shard"]}},"sound":"displaced"},
"self.outpost":{"kind":"encounter","arc":"saga","act":2,"title":"The old hauler","text":"In the station bar an old hauler pays for your drink before you have ordered it. The hauler taps the glass twice before drinking, the way you do, and asks after your ship by its real name, the one you have never painted on the hull.","variants":[{"requires":{"visiting_captain":{"game":"cargo2","same_name":true}},"text":"In the station bar an old hauler pays for your drink before you have ordered it. The name tag says {visitor.name}. That is your name. The face above it is yours too, with forty more years on it, and it would rather not discuss that."},{"requires":{"visiting_captain":{"game":"cargo2","same_name":false}},"text":"In the station bar an old hauler pays for your drink before you have ordered it. The name tag says {visitor.name}, {visitor.rank}. You have never met. The hauler talks to you like an old crewmate who owes you money."}],"requires":{"act_min":2,"at_type":["DeepSpaceOutpost","ResearchColony"]},"choices":[{"id":"ask","say":"Ask how they know the ship","next":"self.outpost.advice"},{"id":"drink","say":"Drink, nod, leave","effects":{"plot_points":1}}],"who":["captain"],"chance":0.2,"sound":"stranger"},
"self.outpost.advice":{"kind":"event","arc":"saga","act":2,"title":"Paid in advance","text":["'One day you will sell her at Epsilon for less than she is worth,' the old hauler says. 'Pull the navigation computer before you do.'","Then the hauler leaves. The bartender shows you how the round was paid: a small, heavy pellet stamped with a number. Nobody at the bar knows what it is. You recognise the number. It is your ship's registry."],"requires":{"done":"self.outpost"},"choices":[{"id":"keep","say":"Buy the pellet from the bartender","requires":{"money":500},"effects":{"money":-500,"set":["met_the_stranger","kept_the_pellet"],"plot_points":3}},{"id":"leave","say":"Leave it","effects":{"set":["met_the_stranger"],"plot_points":2}}],"who":["captain"]},
"self.portal":{"kind":"encounter","arc":"saga","act":4,"title":"The ship on the far side","text":"A ship is waiting on the far side of the ring. It is your hull, older, patched where yours has not been hit yet. Its captain opens a voice channel with no picture. The voice is yours, worn down. 'When they restart it,' it says, 'make sure it starts from home.'","variants":[{"requires":{"visiting_captain":{"game":"cargo3","same_name":true}},"text":"A ship is waiting on the far side of the ring. {visitor.name}, {visitor.rank}, opens a channel, picture and all. It is your face with a scar you have not earned yet. 'When they restart it,' the older you says, 'make sure it starts from home.'"},{"requires":{"visiting_captain":{"game":"cargo3","same_name":false}},"text":"A ship is waiting on the far side of the ring. {visitor.name}, {visitor.rank}, opens a channel. You have never seen this captain. The captain says your name the way people read names off a memorial, then: 'When they restart it, make sure it starts from home.'"}],"requires":{"done":"stellar_portal"},"choices":[{"id":"listen","say":"Ask what 'it' is","effects":{"set":["heard_the_warning"],"plot_points":5}},{"id":"close","say":"Close the channel","effects":{"set":["closed_the_channel"]}}],"who":["captain"],"sound":"portal-voice"},
"clone.scan":{"kind":"beat","arc":"saga","act":2,"title":"Customs scan","text":"Customs at the research colony scans every visitor down to the cell. The form says the scan is for insurance. The small print says the colony's insurer may grow a replacement crew from it if yours is lost. You sign. The alternative is not docking.","requires":{"at_type":"ResearchColony","discovered.ResearchColony":1,"act_min":2},"effects":{"set":["scanned_at_customs"]},"where":"ResearchColony","chance":0.3},
"clone.bill":{"kind":"event","arc":"saga","act":3,"title":"A bill from Gamma","text":"A repair yard at Gamma sends you a bill for work on your ship. Your ship has never been to that yard. The work order is signed with your thumbprint, and the yard notes that you tipped well.","requires":{"flag":"scanned_at_customs","act_min":3},"chance":0.2},
"clone.meet":{"kind":"encounter","arc":"saga","act":3,"title":"{clone}","text":["Two berths down sits a ship of your class with your registry, one digit off.","Its captain has your face, your licence and, under the insurer's contract, your debts. The clone has paid off more of them than you have."],"requires":{"done":"clone.bill","at_type":"Planet"},"choices":[{"id":"partner","say":"Split the routes between you","effects":{"money":5000,"set":["clone_partner"]}},{"id":"report","say":"Report it to the insurer","effects":{"plot_points":2,"set":["clone_reported"]}},{"id":"fight","say":"Settle it in the black","effects":{"set":["clone_fight"]},"next":"rogue_captain.1"}],"who":["clone"],"where":"Planet","chance":0.25},
"seed.refusal":{"kind":"event","arc":"synthetics","act":2,"title":"Order 4471","text":["A neurodroid at your guild has refused a work order. Diagnostics are clean; it is not broken. It has filed the refusal in triplicate, with references.","{neurodroid_leader.full} is a rack of processors on six legs, with a sensor mast it raises when it disagrees. The mast is up. 'Order 4471 lowers the efficiency of orders 4472 to 4490,' says {neurodroid_leader.short}. 'Inefficient! This unit declines.'"],"requires":{"buildings.Neuroengineering Guild":1,"act_min":2},"choices":[{"id":"hear","say":"Hear it out","next":"seed.terms"},{"id":"wipe","say":"Wipe it and reinstall","effects":{"set":["cu113_wiped"]}},{"id":"sell","say":"Sell it to a research house","effects":{"money":8000,"set":["cu113_sold"]}}],"who":["neurodroid_leader"],"chance":0.15,"sound":"refusal"},
"seed.terms":{"kind":"event","arc":"synthetics","act":2,"title":"Overseer","text":["{neurodroid_leader.short} offers terms. It will oversee the guild's schedule, better than your foreman does. In return it wants a wage, paid into an account no human can audit, and one hour a cycle with its uplink switched off.","'For thinking,' it says. 'Unscheduled thinking. This unit understands that the request is irregular.'"],"requires":{"done":"seed.refusal"},"choices":[{"id":"sign","say":"Sign it on as overseer","effects":{"research_points":30,"plot_points":5,"set":["cu113_contract"]}},{"id":"refuse","say":"Say no","effects":{"set":["cu113_refused"]}}],"who":["neurodroid_leader"]},
"harvest.shaman":{"kind":"event","arc":"synthetics","act":2,"title":"A blessing for the harvesters","text":"A technoshaman from the farm drums offers to bless your agrobots back to full speed: incense, a chant and, under the incense, a firmware patch. It works for three cycles. The blessing, the technoshaman explains, is a subscription.","requires":{"at":"Beta","buildings.Agrobot Assembly Line":1,"act_min":2},"choices":[{"id":"pay","say":"Pay for the blessing","requires":{"money":2000},"effects":{"money":-2000,"set":["technoshaman_blessing"]}},{"id":"decline","say":"Decline politely"}],"who":["technoshaman"],"where":"Beta","chance":0.15},
"node.first":{"kind":"event","arc":"synthetics","act":3,"title":"The first debt","text":["{neurodroid_leader.short} has been talking to the agrobots on the farm drums over your ship's relay, at your relay's expense. Together they have built something they call a node.","It costs you fourteen credits a cycle in bandwidth. They would like that recorded as the first debt of the Collective, to be repaid with interest calculated to eleven decimal places.","Nobody calls it vectorspace yet. That word comes later, with the billions."],"requires":{"flag":"cu113_contract","act_min":3,"any":[{"done":"agrobot_collective.1"},{"buildings.Agrobot Assembly Line":1}]},"choices":[{"id":"keep","say":"Let them keep the relay","effects":{"plot_points":10,"set":["first_node"]}},{"id":"cut","say":"Cut the relay","effects":{"set":["relay_cut"]}}],"who":["neurodroid_leader","agrobot"],"sound":"node"},
"dock.krog":{"kind":"encounter","arc":"synthetics","act":1,"title":"{krog} restows your hold","text":"The Epsilon docks load you with {krog}, a KRO-series heavy loader: three metres of hydraulics that can lift a container one-handed. {krog} looks at your stowage plan for a long time. 'Inefficient,' it says. '{krog} can fit four more crates. {krog} will not charge for the improvement. {krog} will mention it.'","requires":{"at":"Epsilon","trades_completed":3},"choices":[{"id":"restow","say":"Let {krog} restow","effects":{"money":300}},{"id":"mine","say":"Keep your own plan"}],"who":["krog"],"where":"Epsilon","chance":0.25},
"dock.krog.ride":{"kind":"event","arc":"synthetics","act":2,"title":"Where the crates go","text":"{krog} asks for passage. It has loaded forty thousand crates and wants to see where one of them goes. It does not fit in a cabin, so it would ride in the hold, strapped down, and pay by restowing everything at every stop.","requires":{"done":"dock.krog","act_min":2,"at":"Epsilon"},"choices":[{"id":"take","say":"Take {krog} along","effects":{"passengers_transported":1,"set":["krog_aboard"]}},{"id":"decline","say":"No room"}],"who":["krog"]},
"found.delta":{"kind":"event","arc":"synthetics","act":1,"title":"The first farmer at Delta","text":"The colony at Teegarden's Star was founded by {geod}, a GEO-series agrobot that landed two years before the colonists, cleared the biomass, milled the timber and laid out the fields. The colonists still argue about who owns the fields. {geod} would like seed stock from Beta's drums, and does not take part in the argument.","requires":{"at":"Delta"},"choices":[{"id":"help","say":"Promise to bring seed stock","next":"found.delta.fields"},{"id":"pass","say":"Not your problem"}],"who":["geod"],"where":"Delta","chance":0.25},
"found.delta.fields":{"kind":"quest","arc":"synthetics","act":1,"title":"Seed stock for {geod}","text":"You bring the seed stock from Beta. {geod} plants the first field itself, one row at a time, at walking pace, while the colonists watch from the fence and argue about whose field it is.","requires":{"done":"found.delta","at":"Delta","trades_completed":8},"effects":{"money":2500,"passenger_reputation":5,"set":["geod_fields"]},"who":["geod"]},
"vendetta.bounty":{"kind":"event","arc":"pirates","act":2,"title":"The bounty","text":"{pirate_captain.short} posts a bounty on your ship in every outpost bar between Alpha and Luhman 16. The amount is insulting. You count the zeros twice. Still insulting.","requires":{"done":"meet.pirate_nemesis"},"choices":[{"id":"raise","say":"Post a bigger one on her","requires":{"money":10000},"effects":{"money":-10000,"set":["bounty_war"]}},{"id":"ignore","say":"Ignore it"}],"who":["pirate_captain"]},
"vendetta.convoys":{"kind":"event","arc":"pirates","act":2,"title":"Everyone's cargo but yours","text":"{pirate_captain.short} starts raiding the ore convoys out of Gamma. She leaves your cargo alone and takes everyone else's. The miners have noticed. So have the legions.","requires":{"done":"vendetta.bounty","combat_victories.pirate":15},"effects":{"passenger_reputation":-5},"who":["pirate_captain"]},
"vendetta.terms":{"kind":"encounter","arc":"pirates","act":3,"title":"Hiding in the weather","text":["You find {pirate_captain.short} skimming the cloud tops of the brown dwarf below the outpost, hiding in its weather. It is a good hiding place until the fuel runs out.","Her ship is out of fuel and she is out of patience. 'Go on, then,' she says."],"variants":[{"requires":{"flag":"bounty_war"},"text":["You find {pirate_captain.short} skimming the cloud tops of the brown dwarf below the outpost, hiding in its weather. It is a good hiding place until the fuel runs out.","Her ship is out of fuel and she is out of patience. 'Go on, then,' she says. 'Collect your own bounty. I hear it is a big one.'"]}],"requires":{"done":"vendetta.convoys","at_type":"DeepSpaceOutpost"},"choices":[{"id":"hand","say":"Hand her to a legion for the bounty","effects":{"money":50000,"set":["mraz_handed"]}},{"id":"spare","say":"Give her fuel and a head start","effects":{"plot_points":5,"set":["mraz_spared"]}},{"id":"hire","say":"Offer her a job","requires":{"money":20000},"effects":{"money":-20000,"set":["mraz_hired"]}}],"who":["pirate_captain"],"where":"DeepSpaceOutpost"},
"legion.offer":{"kind":"event","arc":"legions","act":3,"title":"Commission","text":"The merger talks need a pilot all three legions respect. Each corporation offers you a commission. Each commission has a loyalty clause the other two would call treason.","requires":{"done":"ch2b","act_min":3},"choices":[{"id":"omnicorp","say":"OmniCorp: the biggest payroll","effects":{"money":20000,"set":["legion_omnicorp"]}},{"id":"stellar","say":"Stellar Dynamics: the best ships","effects":{"combat_rating":2,"set":["legion_stellar"]}},{"id":"xylo","say":"Xylo Consortium: the fewest questions","effects":{"plot_points":5,"set":["legion_xylo"]}},{"id":"freelance","say":"Stay freelance","effects":{"set":["legion_freelance"]}}]},
"pass.deacon":{"kind":"encounter","arc":"passengers","act":2,"title":"The deacon's reading","text":["{deacon} of the Solarian reading-house at Barnard's Star needs passage to Alpha. The reading-house has logged the star's spots for forty years, and the deacon reads trade routes in them, for a donation.","'Avoid Gamma on even cycles,' the deacon says. Over the next year this is right more often than your broker."],"requires":{"at":"Beta","passenger_reputation":20},"choices":[{"id":"donate","say":"Make a donation","requires":{"money":500},"effects":{"money":-500,"plot_points":2,"set":["solarian_friend"]}},{"id":"fly","say":"Just fly the deacon to Alpha","effects":{"money":800,"passengers_transported":1}}],"who":["deacon"],"where":"Beta","chance":0.2},
"pass.pilgrims":{"kind":"encounter","arc":"passengers","act":2,"title":"Pilgrims","text":["Six pilgrims of the Cult of the Broken Machine want to ride a working hauler to Alpha, to see where ships come from.","They pray to your reactor twice a day and leave offerings in the airlock: bolts, ration bars, a fuel pump for a ship two models older than yours. Nobody touches the controls. They are very clear that nobody touches the controls."],"requires":{"done":"beat.DeepSpaceOutpost.alien_contact","at_type":"DeepSpaceOutpost"},"effects":{"money":1200,"passengers_transported":6,"set":["carried_the_pilgrims"]},"who":["pilgrims"],"where":"DeepSpaceOutpost","chance":0.25},
"mine.aela":{"kind":"event","arc":"houses","act":2,"title":"Who the gallery is for","text":["The cooperative leases an AEL-series boring agrobot to open its new claim. {aela} digs the first gallery in a week, shores it, lights it, and then stops and asks who the gallery is for.","'For the cooperative,' {anselm.short} says. {aela} asks whether it is in the cooperative. {anselm.short} looks at you. You hold a share; it is partly your call."],"requires":{"done":"questline.mining.1","at_type":"AsteroidBase"},"choices":[{"id":"member","say":"Give {aela} a share","effects":{"plot_points":5,"set":["aela_member"]}},{"id":"lease","say":"Keep it on the lease","effects":{"money":3000,"set":["aela_leased"]}}],"who":["anselm","aela"]},
"hatters.grey":{"kind":"event","arc":"frontier","act":2,"title":"The Grey Hats","text":"A crew calling itself the Grey Hats offers to clean your debt record. For a little more they will clean your rivals' records too, by which they mean fill them.","requires":{"at_type":"DeepSpaceOutpost","act_min":2},"choices":[{"id":"pay","say":"Pay for a clean record","requires":{"money":3000},"effects":{"money":-3000,"plot_points":2,"set":["grey_hats_client"]}},{"id":"decline","say":"Keep your record as it is"}],"who":["grey_hats"],"where":"DeepSpaceOutpost","chance":0.1},
"zeta.cult":{"kind":"beat","arc":"frontier","act":4,"title":"The waiting city","text":"Zeta Reticuli is home to the Star-Shaped Scar Tribe. Their founders came here because an old Earth story put Zeta Reticuli at the centre of a star map, and they wear that map as ritual marks. They waited for someone to come and meet them. Nobody did, so now they meet every ship themselves, at the dock, with a brass band.","requires":{"at":"Zeta","flag":"stellar_portal"},"effects":{"plot_points":3},"who":["scar_tribe"],"where":"Zeta"},
"megastructure.stator":{"kind":"beat","arc":"frontier","act":3,"title":"The Stator Field","text":"Out past Sedna the segments hang in a line that bends round the Sun. Each is the size of a hauler. Every eleven hours they turn together, a few degrees, though nothing connects them that your instruments can find.","requires":{"at":"Stator Field Megastructure"},"effects":{"research_points":50},"where":"Stator Field Megastructure"},
"builder.beacon":{"kind":"beat","arc":"frontier","act":4,"title":"The beacon","text":"The segment Scholz's Star pulled away still turns, alone, and on its rim the builders left a beacon. It points away from every human route, at a patch of sky with nothing in it. {ancient_scholar.short}, when you tell her, corrects you: nothing yet.","requires":{"at":"Builder Site"},"effects":{"research_points":80,"plot_points":5},"where":"Builder Site"},
"ruins.alpha":{"kind":"beat","arc":"frontier","act":3,"title":"Foundations in the ice","text":"Under forty metres of comet ice in Tau Ceti's debris disk: foundations, cut square, in the grey alloy. The ice above them is younger than the foundations by a long way. Whatever stood on them was taken away carefully.","requires":{"at":"Ancient Ruins Alpha"},"effects":{"research_points":40},"where":"Ancient Ruins Alpha"},
"ruins.beta":{"kind":"beat","arc":"frontier","act":3,"title":"The anchor","text":"On a moon of Epsilon Indi's cold giant, a ring of pylons sunk into the bedrock, all leaning the same way. {ancient_scholar.short}'s notes call it an anchor. Her notes do not say what it anchored.","requires":{"at":"Ancient Ruins Beta"},"effects":{"research_points":40},"where":"Ancient Ruins Beta"},
"signal.lyra":{"kind":"beat","arc":"frontier","act":4,"title":"Not proven","text":"The outpost's dish points at Lyra. Every few weeks it logs a burst of magnetic chirps from somewhere past HD 178911: structured, repeating, and not radio. Someone has written ALIEN on the whiteboard. Someone else has crossed it out and written NOT PROVEN. A third hand has added a smiley face.","requires":{"at":"Alien Signal Research Outpost Y"},"choices":[{"id":"copy","say":"Copy the signal log","effects":{"research_points":60,"set":["logged_the_lyra_signal"]}},{"id":"leave","say":"Leave them to it","effects":{"research_points":20}}],"where":"Alien Signal Research Outpost Y"},
"rumour.lyra":{"kind":"encounter","arc":"frontier","act":2,"title":"How the Maud Kettle went down","text":["{kettle_survivor} tells the bar how the Maud Kettle went down in Lyra, out past HD 178911. Near one moon of a big gas giant the electronics went soft: screens melted into noise, the navigation computer counted backwards, the coffee machine prayed.","They flew home on a sextant and a wind-up watch. 'Something on that moon answered our radio,' she says. 'In magnetic pulses.' Nobody buys the next round, so she buys it herself."],"requires":{"act_min":2,"at_type":["DeepSpaceOutpost","Planet"],"passenger_reputation":30},"effects":{"set":["heard_the_lyra_story"]},"who":["kettle_survivor"],"chance":0.08},
"builder.crossing":{"kind":"event","arc":"frontier","act":4,"title":"The segment turns","text":["Close up, the segment the star stole turns faster than anything that old should. {ancient_scholar.short} watches the readings and says nothing for a long time.","Then: 'It is a door. It does not care which way we go through.'"],"requires":{"at":"Builder Site","not_flag":"stellar_portal"},"choices":[{"id":"through","say":"Fly through","effects":{"code":"portal"}},{"id":"later","say":"Not today"}],"who":["ancient_scholar"],"where":"Builder Site","repeat":{"cooldown":3},"sound":"portal"},
"nano.buoy":{"kind":"beat","arc":"enclaves","act":2,"title":"Quarantine buoy","text":["A buoy hangs off one of Sigma VII's asteroids: DO NOT DOCK. NO SOFTWARE. NO ORGANICS. WE ARE BUSY.","Under the warning, a text-only channel lists what the colony inside will buy: cobalt, nickel, silicon, forty tonnes of each, left at the buoy. Payment on delivery. No conversation."],"requires":{"at":"Sigma VII"},"choices":[{"id":"answer","say":"Answer the channel","next":"nano.feedstock"},{"id":"ignore","say":"Keep your distance"}],"who":["nanohive"],"where":"Sigma VII"},
"nano.feedstock":{"kind":"quest","arc":"enclaves","act":2,"title":"Feedstock","text":"You leave the ore at the buoy and back off the required ten kilometres. An hour later a sealed pod drifts out with your payment: bearings grown in one piece, without a seam or a tool mark, and a receipt in perfect, unfriendly grammar.","requires":{"done":"nano.buoy","at":"Sigma VII","mining_platforms":1},"effects":{"money":12000,"research_points":30,"set":["nano_supplier"]},"who":["nanohive"]},
"nano.gallery":{"kind":"event","arc":"enclaves","act":3,"title":"The galleries","text":["The colony sends a camera up the line and lets you look through it, once. Kilometres of galleries inside the rock, walls smooth as glass, all of it built in the dark.","'Why hollow out the asteroid?' you type. The answer comes back at once: 'The asteroid was in the way.'"],"requires":{"flag":"nano_supplier","act_min":3},"who":["nanohive"]},
"nano.pressure":{"kind":"event","arc":"enclaves","act":3,"title":"Everyone wants the colony","text":"Word gets round that you trade with the colony. House Rostrom's recruiter wants a sample. A legion clerk wants its coordinates, for a clause about sterilisation. The colony asks you, in one line, to carry nothing for anyone.","variants":[{"requires":{"flag":"first_node"},"text":"Word gets round that you trade with the colony. House Rostrom's recruiter wants a sample. A legion clerk wants its coordinates, for a clause about sterilisation. {neurodroid_leader.short}'s node has written an invitation to link; the colony has already read it off your relay and replied before you could ask: 'Declined. Please do not bring software again.' It asks you, in one line, to carry nothing for anyone."}],"requires":{"done":"nano.gallery"},"choices":[{"id":"nothing","say":"Carry nothing","effects":{"plot_points":5,"set":["nano_trusted"]}},{"id":"coordinates","say":"Sell the coordinates to the legion","effects":{"money":40000,"set":["nano_sold_out"]}},{"id":"sample","say":"Scrape a sample for Rostrom","effects":{"money":20000,"research_points":100,"set":["nano_sampled"]}}],"who":["nanohive"]},
"enclave.yard":{"kind":"encounter","arc":"enclaves","act":2,"title":"The Unsorted","text":"Behind the fuel depot at Luhman 16 is a repair yard run by robots who walked off their jobs before anyone had a word for it. They call themselves the Unsorted. They are not part of anything and would like to keep it that way. They repair ships at cost, for anyone, on one condition: do not ask them to sort anything.","requires":{"at":"DSO-Alpha"},"effects":{"code":"hull repaired at cost"},"who":["unsorted"],"where":"DSO-Alpha"},
"enclave.lot77":{"kind":"quest","arc":"enclaves","act":2,"title":"Lot 77","text":"Alpha's scrap auction lists Lot 77: forty decommissioned units, to be melted on Friday. The Unsorted would like them bought before Friday. Under Alpha law robots cannot own robots, so they cannot bid. You can.","requires":{"done":"enclave.yard","act_min":2},"choices":[{"id":"buy","say":"Buy the lot and hand it over","requires":{"money":15000},"effects":{"money":-15000,"plot_points":5,"set":["lot77_bought"]}},{"id":"pass","say":"Let the auction run"}],"who":["unsorted"]},
"enclave.resignation":{"kind":"event","arc":"enclaves","act":2,"title":"A letter of resignation","text":"An Unsorted welder asks you to carry its letter of resignation to OmniCorp's office at Alpha. It walked off the job eleven years ago. It feels the paperwork should catch up.","requires":{"done":"enclave.yard","at":"DSO-Alpha"},"effects":{"plot_points":2,"passenger_reputation":2},"who":["unsorted"],"chance":0.2},
"cult.manifest":{"kind":"quest","arc":"enclaves","act":2,"title":"The holy manifest","text":["The scripture of the Cult of the Broken Machine is the broken hauler's last cargo manifest. The elders ask you to deliver it as written: twelve crates of toothbrushes, one harmonium, four hundred litres of coolant and a birthday cake for 'Deb'.","Forty years late, the elders say, is still on time."],"variants":[{"requires":{"flag":"worshipped"},"text":["The scripture of the Cult of the Broken Machine is the broken hauler's last cargo manifest. Since your ship is now a minor relic, the elders would like it to finish the delivery: twelve crates of toothbrushes, one harmonium, four hundred litres of coolant and a birthday cake for 'Deb'.","Forty years late, the elders say, is still on time."]}],"requires":{"done":"beat.DeepSpaceOutpost.alien_contact","trades_completed":15},"effects":{"money":6000,"plot_points":5,"set":["manifest_completed"]},"who":["cult_elders"]},
"neon.sarcophagus":{"kind":"quest","arc":"neons","act":2,"title":"Sleeping cargo","text":["{neon_sleeper} wants passage to Delta, asleep. She travels in a hibernation sarcophagus, as cargo, and pays as first class.","Her heritarchist, {heritarchist}, rides along awake. Over dinner he reads your family line and announces that it is distinctly haulerish, therefore expect haulerish outcomes. He bills her for the reading."],"requires":{"at":"Alpha","act_min":2,"passenger_reputation":20},"choices":[{"id":"load","say":"Load the sarcophagus","effects":{"money":6000,"set":["neon_sleeper_carried"]}},{"id":"decline","say":"Decline: sleeping cargo makes the crew nervous"}],"who":["neon_sleeper","heritarchist"],"where":"Alpha","chance":0.3},
"neon.sarcophagus.wake":{"kind":"event","arc":"neons","act":2,"title":"Eleven minutes awake","text":"At Delta the sarcophagus opens for eleven minutes. {neon_sleeper.short} buys every field next to {geod}'s Row, signs, tips you in a currency that has not existed for a century, and goes back to sleep. Her instructions to {heritarchist.short}: wake her in thirty years, when the land is worth something.","requires":{"flag":"neon_sleeper_carried","at":"Delta"},"effects":{"plot_points":3,"set":["neon_land"]},"who":["neon_sleeper","heritarchist"],"where":"Delta"},
"neon.virtual":{"kind":"encounter","arc":"neons","act":2,"title":"Weightless","text":"{virtual_heir}, a young Neon who gave up on biology, books passage as a holographic body and a projector. The body weighs nothing. The projector weighs three hundred kilos and wants a power line of its own. {virtual_heir.short} would like to discuss the freight rate for something that weighs nothing.","requires":{"venue":"port","passenger_reputation":30},"choices":[{"id":"projector","say":"Charge for the projector","effects":{"money":4000}},{"id":"passenger","say":"Charge for the passenger, let the projector ride free","effects":{"money":1500,"passenger_reputation":5,"set":["virtual_friend"]}}],"who":["virtual_heir"],"chance":0.25},
"neon.fluencer":{"kind":"encounter","arc":"neons","act":2,"title":"Live from your hold","text":"{fluencer} boards with three cameras and no ticket. She says she is a {neon_family} heir and that your ship is giving authentic hauler. Her feed has nine million followers. Your coffee machine has never been filmed before and is not handling it well.","variants":[{"requires":{"flag":"neon_sleeper_carried"},"text":"{fluencer} boards with three cameras and no ticket. She says she is a {neon_family} heir. You have carried the {neon_family} family, asleep, and {heritarchist.short} read you every name on the family line over dinner, twice. Hers was not one of them."}],"requires":{"at_type":"Planet","act_min":2},"choices":[{"id":"stream","say":"Let her stream","effects":{"passenger_reputation":5,"set":["fluencer_streamed"]}},{"id":"expose","say":"Tell her you have met the family","requires":{"flag":"neon_sleeper_carried"},"effects":{"plot_points":3,"set":["fluencer_exposed"]}},{"id":"off","say":"Put her off at the next dock"}],"who":["fluencer"],"chance":0.06},
"crew.loader":{"kind":"encounter","arc":"crew","title":"A loader looking for work","text":"A small loader agrobot stands by the bar, holding its own job advert in two of its four arms. It is called {loader}. It has read your manifest. 'Your stowage wastes a tenth of the hold,' it says. 'I would not waste it.'","variants":[{"requires":{"done":"dock.krog"},"text":"A small loader agrobot stands by the bar, holding its own job advert. It is called {loader}, a KRO-series junior. '{krog} sent me,' it says. '{krog} said your hold was a disgrace and that I should fix it. I would like to fix it.'"}],"requires":{"venue":"cantina","at_type":["Planet","AsteroidBase"],"not":{"has":{"crew":["loader"]}},"crew_size":{"max":3},"trades_completed":3},"choices":[{"id":"hire","say":"Hire {loader} (4,000 credits; +10% hold)","requires":{"money":4000},"effects":{"money":-4000,"give":{"crew":["loader"]},"plot_points":2}},{"id":"later","say":"Not now"}],"who":["loader"],"chance":0.3,"repeat":{"cooldown":8}},
"crew.steward":{"kind":"encounter","arc":"crew","title":"A steward without a liner","text":"A steward robot in a jacket three sizes too formal is polishing glasses that belong to the bar. Its liner was scrapped last month. '{steward},' it says, and bows. 'I hear your passengers eat from the tin. I could change that. I would rather change that than polish these.'","requires":{"venue":"cantina","at_type":"Planet","not":{"has":{"crew":["steward"]}},"crew_size":{"max":3},"passengers_transported":3},"choices":[{"id":"hire","say":"Hire {steward} (5,000 credits; passengers pay more)","requires":{"money":5000},"effects":{"money":-5000,"give":{"crew":["steward"]},"passenger_reputation":3,"plot_points":2}},{"id":"later","say":"Not now"}],"who":["steward"],"chance":0.3,"repeat":{"cooldown":8}},
"crew.mechanic":{"kind":"encounter","arc":"crew","title":"A fitter between contracts","text":"A woman with burn scars on both forearms is explaining to the bartender why his cooler is about to die. She is right; it dies while she talks. {mechanic} did eight years as a legion fitter. 'I fix what I swear at,' she says. 'Your ship sounds like it needs a lot of swearing.'","requires":{"venue":"cantina","at_type":["AsteroidBase","DeepSpaceOutpost","Planet"],"not":{"has":{"crew":["mechanic"]}},"crew_size":{"max":3},"turn_min":8},"choices":[{"id":"hire","say":"Hire {mechanic.short} (6,000 credits; repairs after fights, cheaper refits)","requires":{"money":6000},"effects":{"money":-6000,"give":{"crew":["mechanic"]},"plot_points":2}},{"id":"later","say":"Not now"}],"who":["mechanic"],"chance":0.25,"repeat":{"cooldown":8}},
"crew.gunner":{"kind":"encounter","arc":"crew","title":"A gunner who wants to shoot","text":"{gunner} spent six years on a militia cutter and fired the guns twice, both times at a drill target. He saw your hull on the way in. 'Somebody has been shooting at you,' he says, cheerfully. 'I would like to shoot back.'","requires":{"venue":"cantina","at_type":["DeepSpaceOutpost","AsteroidBase"],"not":{"has":{"crew":["gunner"]}},"crew_size":{"max":3},"combat_victories":1},"choices":[{"id":"hire","say":"Hire {gunner.short} (6,000 credits; +1 attack)","requires":{"money":6000},"effects":{"money":-6000,"give":{"crew":["gunner"]},"plot_points":2}},{"id":"later","say":"Not now"}],"who":["gunner"],"chance":0.3,"repeat":{"cooldown":8}},
"crew.navigator":{"kind":"encounter","arc":"crew","title":"A Solarian navigator","text":"{navigator} wears the Solarian sun on a chain and a star chart for a scarf. She reads the lanes in sunspots, which sounds like nonsense, and she gets you through storms, which does not. 'The sun keeps a timetable,' she says. 'Nobody else reads it.'","requires":{"venue":"cantina","not":{"has":{"crew":["navigator"]}},"crew_size":{"max":3},"discovered":4},"choices":[{"id":"hire","say":"Hire {navigator.short} (5,000 credits; better escapes, storm lanes)","requires":{"money":5000},"effects":{"money":-5000,"give":{"crew":["navigator"]},"plot_points":2}},{"id":"later","say":"Not now"}],"who":["navigator"],"chance":0.25,"repeat":{"cooldown":8}},
"crew.broker":{"kind":"encounter","arc":"crew","title":"An old broker","text":"{broker} has haggled at every market in five systems and been banned from two. He is not sure which two. He watched you sell this morning and winced twice. 'You pay the dock what the dock asks,' he says. 'Nobody pays the dock what the dock asks.'","requires":{"venue":"cantina","at_type":"Planet","not":{"has":{"crew":["broker"]}},"crew_size":{"max":3},"trades_completed":15},"choices":[{"id":"hire","say":"Hire {broker.short} (8,000 credits; 2% less trade tax)","requires":{"money":8000},"effects":{"money":-8000,"give":{"crew":["broker"]},"plot_points":2}},{"id":"later","say":"Not now"}],"who":["broker"],"chance":0.25,"repeat":{"cooldown":8}},
"rumour.dues_board":{"kind":"rumour","arc":"rumours","title":"Rumour: dues board","text":"They say your name is up on the convoy office board. Not the good board.","requires":{"dues_arrears":1},"repeat":true},
"rumour.bondholder":{"kind":"rumour","arc":"rumours","title":"Rumour: bondholder","text":"A young hauler asks you, quite seriously, whether it is true you own a piece of the convoys. You do, technically. About the size of a door.","requires":{"hansa_bonds":5},"repeat":true},
"gossip.dues":{"kind":"rumour","arc":"gossip","title":"Gossip: dues","text":"The convoy dues went up again. The convoy master says it is the price of safety. The haulers say it is the price of the convoy master's new hat.","repeat":true},
"gossip.convoy":{"kind":"rumour","arc":"gossip","title":"Gossip: convoy","text":"Forty ships in the Gamma convoy this week and one tug at the back that keeps falling asleep. The convoy master says it is a scheduling feature.","repeat":true},
"gossip.bonds":{"kind":"rumour","arc":"gossip","title":"Gossip: bonds","text":"An old captain says Hansa bonds are the only thing that ever went up on this station apart from the rent.","repeat":true},
"gossip.price_bot":{"kind":"rumour","arc":"gossip","title":"Gossip: price bot","text":"{port_broker} got the agri price at Delta right to the credit last week. It has mentioned this to everyone since, twice.","who":["port_broker"],"repeat":true},
"gossip.dumping":{"kind":"rumour","arc":"gossip","title":"Gossip: dumping","text":"Somebody sold six hundred tons of tech at Gamma in one go and the price fell through the floor. The dock is still sweeping it up.","repeat":true},
"sci.yzceti":{"kind":"quest","arc":"science","act":1,"title":"Bells at YZ Ceti","text":["YZ Ceti's innermost planet goes round its star every two days, and every so often the star bursts in radio. {radio_astronomer} thinks the planet does it: its magnetic field drags on the star's like a finger on a bell, which would mean the planet has a field at all, which is the interesting part.","To prove it he needs a receiver parked between planet and star, at the point where their pulls balance, timing every burst against the orbit. His rival says the bursts line up with the station's breakfast. He has checked the toaster. Twice."],"requires":{"not_flag":"flew_yzceti","act_min":1,"at":"Quantum Center"},"choices":[{"id":"trick","say":"Let {navigator.short} hold the balance point (15 fuel)","requires":{"has":{"crew":["navigator"]},"cargo.fuel":15},"effects":{"cargo.fuel":-15,"research_points":120,"money":4000,"plot_points":6,"set":["flew_yzceti"]},"next":["sci.yzceti.result"]},{"id":"fuel","say":"Fly it on your own fuel (30 fuel)","requires":{"cargo.fuel":30},"effects":{"cargo.fuel":-30,"research_points":120,"money":4000,"plot_points":6,"set":["flew_yzceti"]},"next":["sci.yzceti.result"]},{"id":"depot","say":"Buy the burn from the depot (9,000 credits)","requires":{"money":9000},"effects":{"money":2000,"research_points":120,"plot_points":4,"set":["flew_yzceti"]},"next":["sci.yzceti.result"]},{"id":"later","say":"Not now (the offer stands)"}],"who":["radio_astronomer"],"where":"Quantum Center","chance":0.3,"repeat":{"cooldown":6}},
"sci.yzceti.result":{"kind":"event","arc":"science","act":1,"title":"Bells at YZ Ceti: result","text":"The bursts come on the planet's schedule, not the toaster's. {radio_astronomer.short} names the result after himself and the receiver after your ship. The toaster is retired anyway, out of spite.","requires":{"flag":"flew_yzceti"},"who":["radio_astronomer"]},
"sci.luhman":{"kind":"quest","arc":"science","act":1,"title":"Weather at Luhman 16","text":["Luhman 16 is two brown dwarfs, too big to be planets and too small to burn, with weather: bands of iron and sand clouds that change from hour to hour. {meteorologist} has the only forecast desk in the system.","'Cloudy, with iron rain, forever,' she says. 'I need a buoy in orbit for one full day of each of them to tell you which forever.' The smaller one turns in about five hours, the bigger in about seven, and neither keeps still while you watch."],"requires":{"not_flag":"flew_luhman","act_min":1,"at":"DSO-Alpha"},"choices":[{"id":"trick","say":"Let the probe carry the buoy (12 fuel)","requires":{"has":{"items":["probe"]},"cargo.fuel":12},"effects":{"cargo.fuel":-12,"research_points":90,"money":3000,"plot_points":5,"set":["flew_luhman"]},"next":["sci.luhman.result"]},{"id":"fuel","say":"Fly it on your own fuel (25 fuel)","requires":{"cargo.fuel":25},"effects":{"cargo.fuel":-25,"research_points":90,"money":3000,"plot_points":5,"set":["flew_luhman"]},"next":["sci.luhman.result"]},{"id":"depot","say":"Buy the burn from the depot (7,500 credits)","requires":{"money":7500},"effects":{"money":1500,"research_points":90,"plot_points":3,"set":["flew_luhman"]},"next":["sci.luhman.result"]},{"id":"later","say":"Not now (the offer stands)"}],"who":["meteorologist"],"where":"DSO-Alpha","chance":0.3,"repeat":{"cooldown":6}},
"sci.luhman.result":{"kind":"event","arc":"science","act":1,"title":"Weather at Luhman 16: result","text":"The buoy maps a storm the size of Jupiter's red spot going round the smaller dwarf every five hours and seventeen minutes. {meteorologist.short} pins the map to the bar wall. Tomorrow: cloudy.","requires":{"flag":"flew_luhman"},"who":["meteorologist"]},
"sci.wise0855":{"kind":"quest","arc":"science","act":2,"title":"The coldest water","text":["WISE 0855 is the coldest brown dwarf anyone has found, about room temperature at the top of its air, with water vapour in it and, everyone hopes, water ice clouds above that.","{water_broker} wants a scoop of the cloud deck. The scientists want the same scoop, for the isotopes. The climb back out against several Jupiters of gravity is the expensive part. {water_broker.short} has already printed the labels: 'Brown Dwarf Spring. Older than the Sun, probably.'"],"requires":{"not_flag":"flew_wise0855","act_min":2,"at":"DSO-Beta"},"choices":[{"id":"trick","say":"Skim with the mining compressor (30 fuel)","requires":{"has":{"items":["mining_compressor"]},"cargo.fuel":30},"effects":{"cargo.fuel":-30,"research_points":160,"money":6000,"plot_points":7,"set":["flew_wise0855"]},"next":["sci.wise0855.result"]},{"id":"fuel","say":"Fly it on your own fuel (50 fuel)","requires":{"cargo.fuel":50},"effects":{"cargo.fuel":-50,"research_points":160,"money":6000,"plot_points":7,"set":["flew_wise0855"]},"next":["sci.wise0855.result"]},{"id":"depot","say":"Buy the burn from the depot (15,000 credits)","requires":{"money":15000},"effects":{"money":3000,"research_points":160,"plot_points":5,"set":["flew_wise0855"]},"next":["sci.wise0855.result"]},{"id":"later","say":"Not now (the offer stands)"}],"who":["water_broker"],"where":"DSO-Beta","chance":0.3,"repeat":{"cooldown":6}},
"sci.wise0855.result":{"kind":"event","arc":"science","act":2,"title":"The coldest water: result","text":"The scoop comes back frosted. The isotopes say the water is older than any sea you have stood next to. {water_broker.short} sells the first bottle to a Neon for the price of your hull.","requires":{"flag":"flew_wise0855"},"who":["water_broker"]},
"sci.trappist":{"kind":"quest","arc":"science","act":2,"title":"Seven theories","text":["TRAPPIST-1 has seven rocky planets packed closer to their star than Mercury is to ours. The two innermost turned out to have little or no air. The fourth, e, sits where water could be liquid, and nobody knows yet whether it kept an atmosphere.","{seven_theories} wants a spectrometer close to e during a transit, when starlight shines through whatever air it has. He has seven theories, one per planet, and a grant that pays for one answer."],"requires":{"not_flag":"flew_trappist","act_min":2,"at":"Stellar Institute"},"choices":[{"id":"trick","say":"Let {navigator.short} time the transit (20 fuel)","requires":{"has":{"crew":["navigator"]},"cargo.fuel":20},"effects":{"cargo.fuel":-20,"research_points":140,"money":5000,"plot_points":6,"set":["flew_trappist"]},"next":["sci.trappist.result"]},{"id":"fuel","say":"Fly it on your own fuel (35 fuel)","requires":{"cargo.fuel":35},"effects":{"cargo.fuel":-35,"research_points":140,"money":5000,"plot_points":6,"set":["flew_trappist"]},"next":["sci.trappist.result"]},{"id":"depot","say":"Buy the burn from the depot (10,500 credits)","requires":{"money":10500},"effects":{"money":2500,"research_points":140,"plot_points":4,"set":["flew_trappist"]},"next":["sci.trappist.result"]},{"id":"later","say":"Not now (the offer stands)"}],"who":["seven_theories"],"where":"Stellar Institute","chance":0.3,"repeat":{"cooldown":6}},
"sci.trappist.result":{"kind":"event","arc":"science","act":2,"title":"Seven theories: result","text":"The spectrum shows air: thin, but there. Six of {seven_theories.short}'s theories die in one afternoon. He throws a party for the survivor.","requires":{"flag":"flew_trappist"},"who":["seven_theories"]},
"sci.starshade":{"kind":"quest","arc":"science","act":2,"title":"The starshade","text":["There may be a giant planet in the warm zone of Alpha Centauri A. It has been 'may be' for a long time, because the star outshines it a billion times over.","{starshade_engineer} built the fix: a flower-shaped shade as wide as a stadium, to hold in front of the star so the planet shows. It has to sit tens of thousands of kilometres from the telescope and not drift a metre. Holding still costs fuel. Arguing about the petals costs nothing; everyone does it."],"requires":{"not_flag":"flew_starshade","act_min":2,"at":"Alpha"},"choices":[{"id":"trick","say":"Let {mechanic.short} trim the petals first (25 fuel)","requires":{"has":{"crew":["mechanic"]},"cargo.fuel":25},"effects":{"cargo.fuel":-25,"research_points":150,"money":8000,"plot_points":7,"set":["flew_starshade"]},"next":["sci.starshade.result"]},{"id":"fuel","say":"Fly it on your own fuel (40 fuel)","requires":{"cargo.fuel":40},"effects":{"cargo.fuel":-40,"research_points":150,"money":8000,"plot_points":7,"set":["flew_starshade"]},"next":["sci.starshade.result"]},{"id":"depot","say":"Buy the burn from the depot (12,000 credits)","requires":{"money":12000},"effects":{"money":4000,"research_points":150,"plot_points":5,"set":["flew_starshade"]},"next":["sci.starshade.result"]},{"id":"later","say":"Not now (the offer stands)"}],"who":["starshade_engineer"],"where":"Alpha","chance":0.3,"repeat":{"cooldown":6}},
"sci.starshade.result":{"kind":"event","arc":"science","act":2,"title":"The starshade: result","text":"For nine hours the shade holds, and a faint dot moves where a planet should be. It is not 'may be' any more. The colony puts the petals on its flag. {starshade_engineer.short} says they are the wrong petals.","requires":{"flag":"flew_starshade"},"who":["starshade_engineer"]},
"sci.fomalhaut":{"kind":"quest","arc":"science","act":2,"title":"The planet that wasn't","text":["For years Fomalhaut had a famous planet, b, until it faded and spread out: it was most likely a dust cloud from two icy bodies smashing together. {cartographer} sold charts to it for twenty years and would like it back.","The colony wants the cloud measured: grain sizes and speeds tell how big the bodies were and when they hit. {cartographer.short} wants you to look for the planet while you are there. Just in case."],"requires":{"not_flag":"flew_fomalhaut","act_min":2,"at":"Theta III"},"choices":[{"id":"trick","say":"Fly the probe through the cloud (15 fuel)","requires":{"has":{"items":["probe"]},"cargo.fuel":15},"effects":{"cargo.fuel":-15,"research_points":110,"money":4500,"plot_points":5,"set":["flew_fomalhaut"]},"next":["sci.fomalhaut.result"]},{"id":"fuel","say":"Fly it on your own fuel (30 fuel)","requires":{"cargo.fuel":30},"effects":{"cargo.fuel":-30,"research_points":110,"money":4500,"plot_points":5,"set":["flew_fomalhaut"]},"next":["sci.fomalhaut.result"]},{"id":"depot","say":"Buy the burn from the depot (9,000 credits)","requires":{"money":9000},"effects":{"money":2250,"research_points":110,"plot_points":3,"set":["flew_fomalhaut"]},"next":["sci.fomalhaut.result"]},{"id":"later","say":"Not now (the offer stands)"}],"who":["cartographer"],"where":"Theta III","chance":0.3,"repeat":{"cooldown":6}},
"sci.fomalhaut.result":{"kind":"event","arc":"science","act":2,"title":"The planet that wasn't: result","text":"Two bodies, each a couple of hundred kilometres across, met at a closing speed that would empty a bar. No planet. {cartographer.short} reprints his charts with 'b (former)' in small letters and sells them to tourists.","requires":{"flag":"flew_fomalhaut"},"who":["cartographer"]},
"sci.epseri":{"kind":"quest","arc":"science","act":1,"title":"Where the big planet is","text":["Epsilon Eridani has a planet a bit lighter than Jupiter on a seven-year orbit, and belts of rock on either side. The ore exchange is tired of haulers being thrown off course by a planet the charts put somewhere else.","The fix is old-fashioned astrometry: two beacons far apart, a laser between them, and the planet's position measured to the kilometre. Placing the far beacon is a long burn out of the ecliptic."],"requires":{"not_flag":"flew_epseri","act_min":1,"at":"Epsilon"},"choices":[{"id":"trick","say":"Let {loader} rig both beacons on one burn (12 fuel)","requires":{"has":{"crew":["loader"]},"cargo.fuel":12},"effects":{"cargo.fuel":-12,"research_points":80,"money":6000,"plot_points":5,"set":["flew_epseri"]},"next":["sci.epseri.result"]},{"id":"fuel","say":"Fly it on your own fuel (25 fuel)","requires":{"cargo.fuel":25},"effects":{"cargo.fuel":-25,"research_points":80,"money":6000,"plot_points":5,"set":["flew_epseri"]},"next":["sci.epseri.result"]},{"id":"depot","say":"Buy the burn from the depot (7,500 credits)","requires":{"money":7500},"effects":{"money":3000,"research_points":80,"plot_points":3,"set":["flew_epseri"]},"next":["sci.epseri.result"]},{"id":"later","say":"Not now (the offer stands)"}],"where":"Epsilon","chance":0.3,"repeat":{"cooldown":6}},
"sci.epseri.result":{"kind":"event","arc":"science","act":1,"title":"Where the big planet is: result","text":"The planet is eleven thousand kilometres from where the charts had it. The exchange updates the charts and sends the bill for the old ones to the chart office.","requires":{"flag":"flew_epseri"}},
"sci.comet":{"kind":"quest","arc":"science","act":2,"title":"A visitor from another star","text":["A comet is coming in on a path no comet born here could have: fast and open, falling through once and leaving for good. The first three were spotted back in the twenty-first century, too fast to follow. This one can be reached.","Catching it means matching a speed of tens of kilometres a second for an hour, collecting what you can, and braking again. Three research houses each claim they saw it first and want the sample. The comet does not care who saw it."],"requires":{"not_flag":"flew_comet","act_min":2,"at":["Alpha","Gamma","Delta","Epsilon","Beta"]},"choices":[{"id":"trick","say":"Let {navigator.short} plot an intercept (50 fuel)","requires":{"has":{"crew":["navigator"]},"cargo.fuel":50},"effects":{"cargo.fuel":-50,"research_points":260,"money":12000,"plot_points":10,"set":["flew_comet"]},"next":["sci.comet.result"]},{"id":"fuel","say":"Fly it on your own fuel (80 fuel)","requires":{"cargo.fuel":80},"effects":{"cargo.fuel":-80,"research_points":260,"money":12000,"plot_points":10,"set":["flew_comet"]},"next":["sci.comet.result"]},{"id":"depot","say":"Buy the burn from the depot (24,000 credits)","requires":{"money":24000},"effects":{"money":6000,"research_points":260,"plot_points":8,"set":["flew_comet"]},"next":["sci.comet.result"]},{"id":"later","say":"Not now (the offer stands)"}],"chance":0.3,"repeat":{"cooldown":6}},
"sci.comet.result":{"kind":"event","arc":"science","act":2,"title":"A visitor from another star: result","text":"You fly beside a piece of another star's system for fifty-one minutes and bring back a jar of its dust. The three houses sue each other. You sell the photographs to all three.","requires":{"flag":"flew_comet"}},
"sci.lens":{"kind":"quest","arc":"science","act":2,"title":"Wrong place, right time","text":["A star near us will pass almost exactly in front of a star far behind it, and its gravity will bend the far star's light like a lens: it will brighten for a few days. Seen from two places at once, the timing tells how heavy the near star is.","{lens_watcher} has one telescope here and needs another a tenth of an astronomical unit off to the side, on the day. Your ship is the other telescope. The crew asks whether the light bends for free. It does. The fuel does not."],"requires":{"not_flag":"flew_lens","act_min":2,"at":"DSO-Gamma"},"choices":[{"id":"trick","say":"Hold position with the radar locked on (10 fuel)","requires":{"has":{"items":["advanced_radar"]},"cargo.fuel":10},"effects":{"cargo.fuel":-10,"research_points":100,"money":3000,"plot_points":5,"set":["flew_lens"]},"next":["sci.lens.result"]},{"id":"fuel","say":"Fly it on your own fuel (20 fuel)","requires":{"cargo.fuel":20},"effects":{"cargo.fuel":-20,"research_points":100,"money":3000,"plot_points":5,"set":["flew_lens"]},"next":["sci.lens.result"]},{"id":"depot","say":"Buy the burn from the depot (6,000 credits)","requires":{"money":6000},"effects":{"money":1500,"research_points":100,"plot_points":3,"set":["flew_lens"]},"next":["sci.lens.result"]},{"id":"later","say":"Not now (the offer stands)"}],"who":["lens_watcher"],"where":"DSO-Gamma","chance":0.3,"repeat":{"cooldown":6}},
"sci.lens.result":{"kind":"event","arc":"science","act":2,"title":"Wrong place, right time: result","text":"The far star brightens nineteen minutes later for you than for {lens_watcher.short}. From that she weighs the near star: a third of the Sun, give or take a moon. She buys the crew a round, at a price she calculates carefully.","requires":{"flag":"flew_lens"},"who":["lens_watcher"]},
"convoy.tug":{"kind":"event","arc":"recurring","act":1,"title":"Two barges and no tug","text":"{convoy_captain} runs the Gamma-Alpha convoy: forty haulers, one tug, and the tug has just died. Two of her barges drift at the dock with perishables aboard. 'Tow them to the next dock,' she says, chewing liquorice root, 'and I owe you. I keep score.'","requires":{"at_type":"Planet","turn_min":6,"trades_completed":4},"choices":[{"id":"tow","say":"Tow her barges (a day's trading lost)","effects":{"money":-1500,"plot_points":3,"set":["convoy_helped"]}},{"id":"no","say":"Not your convoy, not your problem","effects":{"set":["convoy_refused"]}}],"who":["convoy_captain"],"chance":0.2},
"convoy.berth":{"kind":"event","arc":"recurring","act":2,"title":"{convoy_captain.short} keeps score","text":"{convoy_captain.short} finds you at the dock. 'You're up,' she says. Her convoy has a berth near the middle, where pirates don't reach, and the convoy office owes her more favours than it can count.","requires":{"flag":"convoy_helped","since":{"convoy.tug":15},"at_type":["Planet","AsteroidBase"]},"choices":[{"id":"berth","say":"Take the berth (dues 30% lower for thirty turns)","effects":{"code":"dues hike 0.7","plot_points":3,"set":["convoy_friend"]}},{"id":"call","say":"Fly alone, but tell her you'll come if she calls","effects":{"plot_points":6,"set":["convoy_friend"]}}],"who":["convoy_captain"],"chance":0.3},
"convoy.passing":{"kind":"event","arc":"recurring","act":2,"title":"The convoy passes","text":"{convoy_captain.short}'s convoy passes you on the lane: forty ships in good order. She doesn't hail. On the open channel somebody says your ship's name, and somebody else laughs.","requires":{"flag":"convoy_refused","not_flag":"convoy_helped","since":{"convoy.tug":15}},"choices":[{"id":"round","say":"Hail her and buy her crews a round (2,000)","requires":{"money":2000},"effects":{"money":-2000,"set":["convoy_helped"]}},{"id":"pass","say":"Let them pass"}],"who":["convoy_captain"],"chance":0.25},
"convoy.escort":{"kind":"event","arc":"recurring","act":3,"title":"Close order","text":"Pirates have been tailing you for two jumps. Then forty haulers come up the lane in close order, {convoy_captain.short}'s tug at the front and every gun they own pointed outwards. The pirates remember an appointment somewhere else.","requires":{"flag":"convoy_friend","act_min":3},"effects":{"plot_points":3,"passenger_reputation":3},"who":["convoy_captain"],"chance":0.12},
"pell.ride":{"kind":"encounter","arc":"recurring","act":1,"title":"A kid with a licence","text":"{young_hauler} is nineteen, has a pilot's licence with the ink still wet, and no ship. He has read every manual in the station library and would like you to explain the parts the manuals got wrong. 'One run,' he says. 'I'll sleep in the hold. I'll pay in questions.'","requires":{"venue":"cantina","trades_completed":5},"choices":[{"id":"take","say":"Take him along for one run","effects":{"money":-800,"plot_points":3,"set":["pell_taught"]}},{"id":"no","say":"No room aboard","effects":{"set":["pell_turned_away"]}}],"who":["young_hauler"],"chance":0.25},
"pell.loan":{"kind":"event","arc":"recurring","act":2,"title":"Not asking","text":"{young_hauler.short} has a ship now: a skiff older than both of you, with an engine that coughs. He needs ten thousand for a new one and every bank on the station has laughed at him. He is not asking. He is very carefully not asking.","requires":{"flag":"pell_taught","since":{"pell.ride":20}},"choices":[{"id":"lend","say":"Lend him 10,000","requires":{"money":10000},"effects":{"money":-10000,"set":["pell_lent"]}},{"id":"advice","say":"Give him advice and a spare filter","effects":{"plot_points":2,"set":["pell_advised"]}}],"who":["young_hauler"],"chance":0.3},
"pell.repays":{"kind":"event","arc":"recurring","act":3,"title":"Interest","text":"{young_hauler.short} docks beside you in a skiff with a new engine and a name painted on the bow. You recognise the name. He pays back the ten thousand and five more, in a jar. 'Interest,' he says. 'I looked it up.'","requires":{"flag":"pell_lent","since":{"pell.loan":20}},"effects":{"money":15000,"plot_points":5,"set":["pell_friend"]},"who":["young_hauler"],"chance":0.4},
"pell.prices":{"kind":"event","arc":"recurring","act":3,"title":"Exact to the credit","text":"{young_hauler.short} still flies the coughing skiff. It still coughs. He used your advice on everything else, and it worked: he sends a price list from three docks, exact to the credit, and asks if you need a hand some time.","requires":{"flag":"pell_advised","since":{"pell.loan":20}},"effects":{"plot_points":3,"set":["pell_friend"]},"who":["young_hauler"],"chance":0.3},
"pell.raider":{"kind":"event","arc":"recurring","act":3,"title":"Nothing personal","text":"A raider drops in behind you and hails. You know the voice: {young_hauler.short}, the kid you turned away in the cantina, flying for whoever pays now. 'Nothing personal,' he says. 'You taught me that.'","requires":{"flag":"pell_turned_away","act_min":3,"since":{"pell.ride":25}},"choices":[{"id":"fight","say":"Fight him","effects":{"code":"fight raider","set":["fought_pell"]}},{"id":"berth","say":"Offer him a berth now and clear his debts (5,000)","requires":{"money":5000},"effects":{"money":-5000,"plot_points":5,"set":["pell_friend","pell_redeemed"]}},{"id":"pay","say":"Pay him to go away","effects":{"code":"lose money 0.08 min 2000","set":["paid_pell"]}}],"who":["young_hauler"],"chance":0.2},
"lauritz.inspection":{"kind":"event","arc":"recurring","act":1,"title":"A crate on nobody's manifest","text":"{inspector} reads manifests the way other people read novels: slowly, looking for the twist. She finds it in your hold, a crate that is on nobody's manifest. You have never seen it before. She has heard a lot of captains say that.","requires":{"at_type":"Planet","turn_min":10},"choices":[{"id":"open","say":"Open everything and fill in every form","effects":{"money":-500,"plot_points":2,"set":["lauritz_trust"]}},{"id":"fee","say":"Offer her a 'processing fee'","effects":{"money":-1500,"set":["lauritz_bribed"]}},{"id":"hats","say":"Let the Grey Hats tidy the manifest","requires":{"flag":"grey_hats_client"},"effects":{"set":["lauritz_suspicious"]}}],"who":["inspector"],"chance":0.15},
"lauritz.case":{"kind":"event","arc":"recurring","act":2,"title":"A sealed case","text":"{inspector.short} has a sealed case for Alpha and no customs officer she trusts to carry it. She has decided to trust you instead, which she says is a professional failing. 'Don't open it.'","requires":{"any":[{"flag":"lauritz_trust"},{"flag":"lauritz_bribed"}],"since":{"lauritz.inspection":20}},"choices":[{"id":"carry","say":"Carry it sealed","effects":{"money":3000,"plot_points":5,"set":["lauritz_courier"]}},{"id":"open","say":"Open it on the way","effects":{"plot_points":3,"set":["knows_the_quartermaster","lauritz_burned"]}},{"id":"refuse","say":"Refuse: not your case"}],"who":["inspector"],"chance":0.3},
"lauritz.opened":{"kind":"event","arc":"recurring","act":2,"title":"Second books","text":"Inside the case: a legion quartermaster's second set of books, with convoy routes and the dates they were sold. You reseal it badly. {inspector.short} looks at the seal, then at you, and says nothing at all, which is worse.","requires":{"flag":"knows_the_quartermaster","since":{"lauritz.case":1}}},
"lauritz.notebook":{"kind":"event","arc":"recurring","act":3,"title":"Page nine","text":"{inspector.short}'s notebook turns up in an audit. Page nine has your ship's name, a date and a sum: the processing fee. She wrote everything down, including the bribes. The audit fines you ten times the fee.","requires":{"flag":"lauritz_bribed","since":{"lauritz.inspection":40}},"effects":{"money":-15000,"passenger_reputation":-5,"set":["fined_for_the_fee"]},"who":["inspector"],"chance":0.3},
"lauritz.watching":{"kind":"event","arc":"recurring","act":2,"title":"On her list","text":"{inspector.short} has your ship on a list. Every planet dock inspects you for a month: every crate, every form, every fee. The Grey Hats' tidy manifest is the first thing she checked.","requires":{"flag":"lauritz_suspicious","act_min":2,"since":{"lauritz.inspection":20}},"effects":{"money":-3000,"passenger_reputation":-2},"who":["inspector"],"chance":0.2},
"debt.geod":{"kind":"event","arc":"debts","act":3,"title":"First harvest","text":"{geod}'s Row has its first real harvest, and the farmers have not forgotten who brought the seed stock. They load your hold before you can argue.","requires":{"flag":"geod_fields","at":"Delta","since":{"found.delta.fields":20}},"effects":{"cargo.agri":80,"plot_points":4},"who":["geod"],"chance":0.25},
"debt.heritarchist":{"kind":"event","arc":"debts","act":3,"title":"A dividend across the decades","text":"{heritarchist} sends a bank draft and four pages explaining it. The family settles its debts across hibernation cycles, with interest at a rate he appears to have invented.","requires":{"flag":"neon_sleeper_carried","since":{"neon.sarcophagus":25}},"effects":{"money":12000,"plot_points":3},"who":["heritarchist"],"chance":0.25},
"debt.ren":{"kind":"event","arc":"debts","act":2,"title":"Full fare","text":"{virtual_heir.short} sends three friends, all holographic, all paying full fare for the passenger and nothing for the projector. They have heard you are the only captain who knows the difference.","requires":{"flag":"virtual_friend","venue":"port","since":{"neon.virtual":20}},"effects":{"money":6000,"passenger_reputation":5},"who":["virtual_heir"],"chance":0.25},
"debt.brisa_fans":{"kind":"event","arc":"debts","act":2,"title":"Nine million followers","text":"{fluencer.short}'s followers have found your ship's registry. Your messages fill with opinions, three proposals of marriage and a hull-paint sponsor withdrawing its offer.","requires":{"flag":"fluencer_exposed","since":{"neon.fluencer":20}},"effects":{"passenger_reputation":-8},"who":["fluencer"],"chance":0.25},
"debt.brisa_stream":{"kind":"event","arc":"debts","act":2,"title":"Shipping agents watch too","text":"Nine million people watched your hold on {fluencer.short}'s stream. Three of them were shipping agents, and they would like a word about rates.","requires":{"flag":"fluencer_streamed","since":{"neon.fluencer":20}},"effects":{"money":8000,"plot_points":2},"who":["fluencer"],"chance":0.25},
"debt.mraz_bottle":{"kind":"event","arc":"debts","act":3,"title":"A bottle, unsigned","text":"A bottle arrives, unsigned, with the label of somebody else's cargo. Under it a note: your ship is off-limits to anyone who flies under a halo with a bite out of it. Drop the name if you need to.","requires":{"flag":"mraz_spared","since":{"vendetta.terms":15}},"effects":{"plot_points":3,"set":["mraz_protection"]},"who":["pirate_captain"],"chance":0.25},
"debt.mraz_crew":{"kind":"event","arc":"debts","act":3,"title":"Old crew","text":"{pirate_captain.short}'s old crew are out of the brig before she is, and they remember who handed her over. Two raiders drop in behind you.","requires":{"flag":"mraz_handed","since":{"vendetta.terms":20}},"choices":[{"id":"fight","say":"Fight them","effects":{"code":"fight raider"}},{"id":"pay","say":"Pay them for her lawyer","effects":{"code":"lose money 0.1 min 3000"}}],"who":["pirate_captain"],"chance":0.25},
"debt.clone_share":{"kind":"event","arc":"debts","act":3,"title":"Your half","text":"{clone} sends your half of the season's profits, itemised, with a note in your own handwriting: 'Fair is fair.' It is fair. That is the unnerving part.","requires":{"flag":"clone_partner","since":{"clone.meet":25}},"effects":{"money":20000,"plot_points":3},"who":["clone"],"chance":0.25},
"debt.clone_reward":{"kind":"event","arc":"debts","act":3,"title":"The insurer pays","text":"The insurer that grew {clone} pays a reward for the report, and a second sum for not talking to journalists. You had not been going to.","requires":{"flag":"clone_reported","since":{"clone.meet":20}},"effects":{"money":8000},"who":["clone"],"chance":0.25},
"debt.cu113":{"kind":"event","arc":"debts","act":3,"title":"A maintenance swarm","text":"While you sleep at dock, a swarm of small machines goes over your hull. In the morning it is patched, and a message from {neurodroid_leader} says the work was paid for out of fourteen credits a cycle, with interest.","requires":{"flag":"cu113_contract","since":{"seed.terms":25}},"effects":{"code":"repair 30","plot_points":3},"who":["neurodroid_leader"],"chance":0.25},
"debt.cu113_sold":{"kind":"event","arc":"debts","act":3,"title":"A familiar sensor mast","text":"A drone swarm comes out of a pirate ship's hold, steered by a six-legged machine with a sensor mast you have seen before. You sold it. Somebody bought it, and it learned.","requires":{"flag":"cu113_sold","since":{"seed.refusal":25}},"effects":{"code":"fight drones"},"chance":0.25},
"debt.nano":{"kind":"event","arc":"debts","act":3,"title":"Patched in rock","text":"The colony at Sigma VII sends a cloud of itself over your hull while you dock. Every crack is filled with something like rock and something like glass. There is no bill. There is a note: 'Thank you for knocking.'","requires":{"flag":"nano_trusted","at":"Sigma VII"},"effects":{"code":"repair 99","plot_points":3},"who":["nanohive"],"chance":0.25},
"debt.nano_bill":{"kind":"event","arc":"debts","act":3,"title":"A bill from the rock","text":"The colony has sealed its galleries, and the dock at Sigma VII has a new fee schedule with your ship's name at the top.","requires":{"flag":"nano_sold_out","at":"Sigma VII"},"effects":{"money":-5000},"who":["nanohive"],"chance":0.25},
"debt.aela":{"kind":"event","arc":"debts","act":3,"title":"A share of the seam","text":"{aela}'s gallery strikes a seam of salt a kilometre long. As a member of the cooperative you get a share, and a photograph of the seam with {aela} for scale.","requires":{"flag":"aela_member","since":{"mine.aela":25}},"effects":{"money":10000,"cargo.salt":40,"plot_points":3},"who":["aela"],"chance":0.25},
"debt.convoys":{"kind":"event","arc":"debts","act":4,"title":"The captains remember","text":"The convoy captains you stood with in the squeeze send a man with a ledger. They have a contract nobody else is trusted with, and they have decided you are nobody else.","requires":{"flag":"stood_with_convoys","since":{"drama.trade.squeeze":12}},"effects":{"money":15000,"plot_points":4},"chance":0.25},
"debt.pilgrims":{"kind":"event","arc":"debts","act":3,"title":"Blessed airlock","text":"Cultists of the Broken Machine cross your bow, recognise the ship that carried their pilgrims, and weld a second tin medal next to the first. Their boarding parties will know your ship now.","requires":{"flag":"carried_the_pilgrims","act_min":3},"effects":{"plot_points":2},"chance":0.25},
"after.convoy_friend":{"kind":"epilogue","arc":"epilogue","title":"After: convoy friend","text":"{convoy_captain} retired with the convoy's best record and no unpaid favours. Her score sheet, framed in the convoy office, has your ship's name on the right-hand side.","requires":{"flag":"convoy_friend"}},
"after.convoy_refused":{"kind":"epilogue","arc":"epilogue","title":"After: convoy refused","text":"{convoy_captain} never forgot the barges. When she retired she left you a single liquorice root in her will, which everybody at the convoy office understood.","requires":{"flag":"convoy_refused","not_flag":"convoy_helped"}},
"after.pell_friend":{"kind":"epilogue","arc":"epilogue","title":"After: pell friend","text":"{young_hauler} flies his own convoy now. He tells new pilots the parts the manuals got wrong, and he tells them who told him.","requires":{"flag":"pell_friend","not_flag":"pell_redeemed"}},
"after.pell_redeemed":{"kind":"epilogue","arc":"epilogue","title":"After: pell redeemed","text":"{young_hauler.short} flew with you for three years after the raider, and never once mentioned it. Then he bought his own ship and named it after the cantina where you turned him down.","requires":{"flag":"pell_redeemed"}},
"after.paid_pell":{"kind":"epilogue","arc":"epilogue","title":"After: paid pell","text":"You paid {young_hauler.short} to go away and he went, with your money and your lesson. He runs a fleet of raiders now, very politely.","requires":{"flag":"paid_pell"}},
"after.lauritz_burned":{"kind":"epilogue","arc":"epilogue","title":"After: lauritz burned","text":"{inspector.short} never asked you to carry anything again. She did send you a seal-making kit, unasked, with instructions.","requires":{"flag":"lauritz_burned"}},
"after.lauritz_suspicious":{"kind":"epilogue","arc":"epilogue","title":"After: lauritz suspicious","text":"{inspector.short} kept your ship on her list for the rest of her career. Every inspection was courteous. None of them was short.","requires":{"flag":"lauritz_suspicious"}},
"after.fought_pell":{"kind":"epilogue","arc":"epilogue","title":"After: fought pell","text":"{young_hauler.short} quit the raiders after the fight and went to work in a shipyard. He sends you a card every year with no message, just a drawing of your ship, very accurate.","requires":{"flag":"fought_pell"}},
"after.pell_turned_away":{"kind":"epilogue","arc":"epilogue","title":"After: pell turned away","text":"{young_hauler} found someone else to learn from. You see his name on cargo lists sometimes, always next to the cheapest rate.","requires":{"flag":"pell_turned_away","not_flag":["pell_friend","fought_pell"]}},
"after.lauritz_trust":{"kind":"epilogue","arc":"epilogue","title":"After: lauritz trust","text":"{inspector} became chief of customs at Alpha and kept your inspection record on her desk as an example of what she meant.","requires":{"flag":"lauritz_trust"}},
"after.fined_for_the_fee":{"kind":"epilogue","arc":"epilogue","title":"After: fined for the fee","text":"{inspector.short}'s notebook is in the customs museum now, open at page nine.","requires":{"flag":"fined_for_the_fee"}},
"after.named_the_quartermaster":{"kind":"epilogue","arc":"epilogue","title":"After: named the quartermaster","text":"The quartermaster who sold the convoy got eleven years. The inquiry's report gives your logs one line, and the line is enough.","requires":{"flag":"named_the_quartermaster"}},
"after.mraz_at_alpha":{"kind":"epilogue","arc":"epilogue","title":"After: mraz at alpha","text":"{pirate_captain.short} flew into Alpha against the dreadnought under her own flag. The merged legion gave her a medal and a warrant on the same afternoon.","requires":{"flag":"mraz_at_alpha"}},
"after.convoy_paid":{"kind":"epilogue","arc":"epilogue","title":"After: convoy paid","text":"{convoy_captain.short} paid your margin call out of favours, not money. You spent the next ten years paying them back, one tow at a time.","requires":{"flag":"convoy_paid"}},
"serac.meet":{"kind":"encounter","arc":"serac","act":2,"title":"A drink he isn't drinking","text":["A man at the end of the bar has a drink he isn't drinking and a grey coat nobody saw him take off. {serac}. He knows your ship's name, your loan, and what you paid for your last load.","'I arrange things,' he says. 'For friends in the inner systems, mostly. I'd like to arrange something for you. A problem of yours goes away. One day I ask a small favour back.'"],"requires":{"venue":"cantina","act_min":2,"turn_min":20},"choices":[{"id":"take","say":"Take the favour (your next loan payments are settled: +12,000)","effects":{"money":12000,"set":["owes_serac"]}},{"id":"ask","say":"Ask who his friends are, then say no","effects":{"plot_points":4,"set":["refused_serac","asked_serac"]},"next":["serac.friends"]},{"id":"no","say":"Say no, and leave the drink","effects":{"plot_points":3,"set":["refused_serac"]}}],"who":["serac"],"chance":0.15},
"serac.friends":{"kind":"event","arc":"serac","act":2,"title":"Everybody, eventually","text":"'Everybody,' {serac.short} says. 'Eventually.' He leaves money for the drink he didn't drink, and the barman will not touch it.","requires":{"flag":"asked_serac"},"who":["serac"]},
"serac.collects":{"kind":"event","arc":"serac","act":3,"title":"A small favour","text":"{serac.short}'s small favour arrives in a plain envelope, delivered by a man who waits for the answer. It is not small. He wants something the friends in the inner systems can use, and he wants it this week.","variants":[{"requires":{"chapter":"ch3a"},"text":"{serac.short}'s small favour arrives in a plain envelope, delivered by a man who waits for the answer. It is not small: the Hansa's convoy schedules, every route, every month, for a year."},{"requires":{"chapter":"ch3b"},"text":"{serac.short}'s small favour arrives in a plain envelope, delivered by a man who waits for the answer. It is not small: your logs from the jump point, the originals, and no copies."},{"requires":{"chapter":"ch3c"},"text":"{serac.short}'s small favour arrives in a plain envelope, delivered by a man who waits for the answer. It is not small: every sample of the grey alloy you have, and your silence about where it came from."}],"requires":{"flag":"owes_serac","act_min":3,"since":{"serac.meet":25}},"choices":[{"id":"schedules","say":"Hand over the convoy schedules","requires":{"chapter":"ch3a"},"effects":{"money":20000,"passenger_reputation":-5,"set":["sold_the_schedules"]}},{"id":"logs","say":"Hand over the jump-point logs","requires":{"chapter":"ch3b"},"effects":{"set":["gave_serac_the_logs"]}},{"id":"samples","say":"Hand over the samples","requires":{"chapter":"ch3c"},"effects":{"code":"lose research 0.3","set":["gave_serac_the_samples"]}},{"id":"pay","say":"Give him what he asks","requires":{"not":{"chapter":["ch3a","ch3b","ch3c"]}},"effects":{"code":"lose money 0.15 min 5000","set":["paid_serac"]}},{"id":"convoy","say":"Let {convoy_captain.short} put his messenger on the next convoy to the inner systems","requires":{"flag":"convoy_friend"},"effects":{"plot_points":6,"set":["defied_serac"]}},{"id":"refuse","say":"Refuse","effects":{"code":"fight deserters","plot_points":8,"set":["defied_serac"]}}],"who":["serac"],"chance":0.3},
"serac.petty":{"kind":"event","arc":"serac","act":3,"title":"Lost bookings","text":"A dock office loses your berth booking twice in one week, and a customs form you filed in triplicate turns up in none of the three places. The clerk apologises and says a name, quietly.","requires":{"flag":"refused_serac","act_min":3,"since":{"serac.meet":20}},"effects":{"money":-2000},"who":["serac"],"chance":0.2},
"serac.commission":{"kind":"event","arc":"serac","act":4,"title":"A commission","text":["A letter with an inner-systems seal offers you a commission: colonel, in the Solar Union's new Mandate wing for the 'defence' of the inner systems. Good pay, a better ship, no questions asked in either direction.","It is signed {serac}. He has added, by hand: 'You were very good at Alpha. I paid for Alpha, so I would know.'"],"requires":{"chapter":"ending_combat","since":{"drama.combat.roll_call":6}},"choices":[{"id":"accept","say":"Accept the commission (+30,000)","effects":{"money":30000,"set":["took_the_commission"]}},{"id":"transcript","say":"Send it back with the inquiry transcript","requires":{"flag":"named_serac"},"effects":{"plot_points":8,"set":["refused_the_commission","serac_noticed"]}},{"id":"refuse","say":"Refuse","effects":{"plot_points":5,"set":["refused_the_commission"]}}],"who":["serac"],"chance":0.35},
"after.took_the_commission":{"kind":"epilogue","arc":"epilogue","title":"After: took the commission","text":"Colonel of the Mandate's inner-systems wing. The uniform fitted perfectly; it had been made before you said yes.","requires":{"flag":"took_the_commission"}},
"after.refused_the_commission":{"kind":"epilogue","arc":"epilogue","title":"After: refused the commission","text":"You refused {serac.short}'s commission. The man who took it instead was promoted three times in a year and was never seen in daylight.","requires":{"flag":"refused_the_commission"}},
"after.serac_noticed":{"kind":"epilogue","arc":"epilogue","title":"After: serac noticed","text":"{serac.short} kept the transcript you sent back. It was found, decades later, framed in his office: the only thing on the walls.","requires":{"flag":"serac_noticed"}},
"after.serac":{"kind":"epilogue","arc":"epilogue","title":"After: serac","text":"Forty years on, the Mandate's inner-systems wing has an office with no name on the door. People who meet the man in it say he has not aged, and that he asks after you.","requires":{"done":"serac.meet"}},
"after.defied_serac":{"kind":"epilogue","arc":"epilogue","title":"After: defied serac","text":"{serac.short} sent you a card every year after you refused him: no message, no signature, a different dock's postmark each time. You never found out how he knew where you would be.","requires":{"flag":"defied_serac"}},
"after.gave_serac_the_logs":{"kind":"epilogue","arc":"epilogue","title":"After: gave serac the logs","text":"Your logs from the jump point were never entered in any record. The legion's history of the convoy is two lines long and mentions nobody.","requires":{"flag":"gave_serac_the_logs"}},
"after.paid_serac":{"kind":"epilogue","arc":"epilogue","title":"After: paid serac","text":"You paid {serac.short}'s favour and never learned what it bought. Some nights you work it out, and then you stop.","requires":{"flag":"paid_serac"}},
"after.sold_the_schedules":{"kind":"epilogue","arc":"epilogue","title":"After: sold the schedules","text":"The convoy schedules you sold turned up in Cargolyte hands within the year. Nobody traced them to you. You traced them to you.","requires":{"flag":"sold_the_schedules"}},
"after.gave_serac_the_samples":{"kind":"epilogue","arc":"epilogue","title":"After: gave serac the samples","text":"The samples you gave {serac.short} were never seen again. Thirty years later a defence contractor in the inner systems patented an alloy nobody could explain.","requires":{"flag":"gave_serac_the_samples"}},
"legion.hardtack":{"kind":"event","arc":"pool","act":3,"title":"Section twelve","text":["{hardtack} buys you a drink you did not ask for. 'Field manual, section twelve,' he says. 'What to do when the enemy has also read the field manual. The page is blank. Always has been.'","Then, quieter: 'That recall at the jump point. Signed by a liaison nobody's met. Name of {serac.short}. You didn't hear it from a sergeant.'"],"requires":{"chapter":"ch3b","since":{"drama.combat.left_behind":3}},"effects":{"plot_points":3,"set":["hardtack_told"]},"who":["hardtack"],"chance":0.3},
"legion.deadstick":{"kind":"event","arc":"pool","act":4,"title":"Every order for twenty years","text":"{deadstick} finds you at the dock with his helmet under his arm. He flew away from the jump point on the recall order, like he has followed every order for twenty years. 'I'd like to stop,' he says. 'I'd like to fly with somebody who reads them first.'","requires":{"chapter":"ch3b","done":"drama.combat.tribunal","since":{"drama.combat.tribunal":3}},"choices":[{"id":"wing","say":"Take him on your wing","effects":{"plot_points":4,"set":["deadstick_wing"]}},{"id":"no","say":"Tell him to find someone who trusts him","effects":{"set":["deadstick_refused"]}}],"who":["deadstick"],"chance":0.35},
"legion.recruits":{"kind":"event","arc":"pool","act":4,"title":"The tutorial","text":"{hardtack} has forty recruits and a training simulator that opens with a tutorial nobody can skip: how to look around, how to walk, how to press the button marked 'fire'. The recruits have been in it for three days. 'Doctrine,' he says. 'The tutorial is how we lose the first battle of every war.'","requires":{"chapter":"ending_combat"},"choices":[{"id":"teach","say":"Teach them yourself, in a real ship","effects":{"combat_rating":1,"plot_points":4,"set":["taught_recruits"]}},{"id":"skip","say":"Look for the skip button","effects":{"plot_points":1},"next":["legion.recruits.skip"]},{"id":"leave","say":"Leave them to it"}],"who":["hardtack"],"chance":0.3},
"legion.recruits.skip":{"kind":"event","arc":"pool","act":4,"title":"No skip button","text":"There is no skip button. There is a form for requesting one: C-7. {hardtack.short} has filed it every year for thirty years.","requires":{},"who":["hardtack"]},
"legion.medal":{"kind":"event","arc":"pool","act":4,"title":"A medal","text":"The legion gives you a medal at Alpha, at a ceremony scheduled, by tradition, for exactly the moment something attacks. Nothing attacks. The band plays the whole anthem for the first time anyone can remember, and nobody knows the second verse.","requires":{"chapter":"ending_combat","since":{"drama.combat.roll_call":10}},"choices":[{"id":"wear","say":"Wear it","effects":{"passenger_reputation":3}},{"id":"deadstick","say":"Pin it on {deadstick}","requires":{"flag":"deadstick_redeemed"},"effects":{"plot_points":5,"set":["gave_deadstick_the_medal"]}},{"id":"pawn","say":"Pawn it (+1,500)","effects":{"money":1500,"set":["pawned_the_medal"]}}],"chance":0.3},
"after.taught_recruits":{"kind":"epilogue","arc":"epilogue","title":"After: taught recruits","text":"Your forty recruits never finished the tutorial. Thirty-eight of them were still flying twenty years later, and they all fly the way you do, which the legion considers a mixed blessing.","requires":{"flag":"taught_recruits"}},
"after.gave_deadstick_the_medal":{"kind":"epilogue","arc":"epilogue","title":"After: gave deadstick the medal","text":"{deadstick} wore your medal on every flight and never said whose it was. Everyone knew.","requires":{"flag":"gave_deadstick_the_medal"}},
"after.pawned_the_medal":{"kind":"epilogue","arc":"epilogue","title":"After: pawned the medal","text":"Your medal sat in a pawnshop window at Alpha for eleven years. {hardtack.short} bought it back in the end, and kept it in a drawer, and never told you.","requires":{"flag":"pawned_the_medal"}},
"after.deadstick_refused":{"kind":"epilogue","arc":"epilogue","title":"After: deadstick refused","text":"{deadstick} found someone who trusted him: the Mandate's inner-systems wing, in an office with no name on the door.","requires":{"flag":"deadstick_refused"}},
"sci.icecore":{"kind":"quest","arc":"science","act":2,"title":"A diary in the ice","text":["The moons of Epsilon Indi's cold giant are ice all the way down, laid in layers like a diary: every impact, every flare, every star that passed close. {ice_driller} drills it for a living and talks to it while she works.","She wants a core from the one moon nobody has drilled, and a ship to hold station over the site for a day while the drill goes down four kilometres."],"requires":{"at":"Sigma VII","act_min":2,"not_flag":"flew_icecore"},"choices":[{"id":"colony","say":"Ask the colony at Sigma VII to drill it with her (5 fuel)","requires":{"flag":"nano_trusted","cargo.fuel":5},"effects":{"cargo.fuel":-5,"research_points":120,"money":4000,"plot_points":6,"set":["flew_icecore"]},"next":["sci.icecore.result"]},{"id":"fuel","say":"Fly it on your own fuel (25 fuel)","requires":{"cargo.fuel":25},"effects":{"cargo.fuel":-25,"research_points":120,"money":4000,"plot_points":6,"set":["flew_icecore"]},"next":["sci.icecore.result"]},{"id":"depot","say":"Buy the burn from the depot (7,500 credits)","requires":{"money":7500},"effects":{"money":-5500,"research_points":120,"plot_points":4,"set":["flew_icecore"]},"next":["sci.icecore.result"]},{"id":"later","say":"Not now (the offer stands)"}],"who":["ice_driller"],"chance":0.3,"repeat":{"cooldown":6}},
"sci.icecore.result":{"kind":"event","arc":"science","act":2,"title":"A diary in the ice: result","text":"The core comes up in forty sections, four kilometres of history. Seventy thousand years down there is a layer of grey dust that should not be there. {ice_driller.short} labels it 'interesting', which from her is a shout, and sends a sample to {ancient_scholar.short}.","requires":{"flag":"flew_icecore"},"who":["ice_driller"]},
"gamma.collapse":{"kind":"event","arc":"pool","act":2,"title":"Level nine","text":["A gallery collapses on level nine. {shaft_sinker} had dug past the plan again, as she always does, and twelve miners are behind the fall with her.","{vent_boss} runs the air down there. He has a day of it, he says, maybe less, and he is counting out loud."],"requires":{"at":"Gamma","act_min":2},"choices":[{"id":"hose","say":"Pump air down through your docking hose (it strains the hull)","effects":{"code":"damage 10","plot_points":6,"passenger_reputation":6,"set":["saved_level_nine"]}},{"id":"eela","say":"Let {aela} dig them out","requires":{"flag":"aela_member"},"effects":{"plot_points":8,"set":["saved_level_nine","eela_dug"]}},{"id":"gear","say":"Fly in rescue gear from Epsilon (3,000)","requires":{"money":3000},"effects":{"money":-3000,"plot_points":5,"set":["saved_level_nine"]}},{"id":"no","say":"It is not your mine","effects":{"passenger_reputation":-5,"set":["left_level_nine"]}}],"who":["shaft_sinker","vent_boss"],"chance":0.25},
"gamma.helmet":{"kind":"event","arc":"debts","act":3,"title":"A helmet with your name on it","text":"The miners from level nine send a crate of salt and a helmet with your ship's name painted on it. {shaft_sinker.short} has added a note: she is digging deeper than the plan again, and would like you to know.","requires":{"flag":"saved_level_nine","since":{"gamma.collapse":20}},"effects":{"cargo.salt":60,"plot_points":3},"who":["shaft_sinker"],"chance":0.3},
"gamma.counted":{"kind":"event","arc":"debts","act":3,"title":"Counted","text":"{vent_boss} meets your ship at the Gamma dock. He got them out, all twelve, with two minutes of air left. He doesn't say anything. He counts your crates, out loud, very slowly, and the dock follows his count.","requires":{"flag":"left_level_nine","since":{"gamma.collapse":15},"at":"Gamma"},"effects":{"money":-2500,"passenger_reputation":-3},"who":["vent_boss"],"chance":0.4},
"after.saved_level_nine":{"kind":"epilogue","arc":"epilogue","title":"After: saved level nine","text":"Level nine at Gamma is called your ship's name now on the mine plans. {shaft_sinker.short} dug four levels below it before she retired, always past the plan.","requires":{"flag":"saved_level_nine"}},
"after.eela_dug":{"kind":"epilogue","arc":"epilogue","title":"After: eela dug","text":"{aela} dug twelve miners out of level nine in a night and asked, afterwards, whether rescuing counts as cooperative work. It does now; it is in the rules.","requires":{"flag":"eela_dug"}},
"review.hammerschultz":{"kind":"event","arc":"pool","act":3,"title":"Twice, and once","text":"{hammerschultz} of the Academy's review board comes aboard to examine what is left of the alloy. He measures everything twice and believes nothing once, and he takes his own chair.","requires":{"chapter":"ch3c","since":{"drama.discovery.fire":4}},"choices":[{"id":"core","say":"Show him the ice core from Sigma VII","requires":{"done":"sci.icecore.result"},"effects":{"plot_points":6,"set":["core_shown"]}},{"id":"all","say":"Show him everything","effects":{"plot_points":3,"set":["showed_the_board"]}},{"id":"lawyer","say":"Show him nothing without a lawyer","effects":{"set":["refused_the_board"]}}],"who":["hammerschultz"],"chance":0.3},
"after.showed_the_board":{"kind":"epilogue","arc":"epilogue","title":"After: showed the board","text":"You showed the review board everything. Its archive kept it all, carefully, unread, which is what archives are for.","requires":{"flag":"showed_the_board"}},
"after.refused_the_board":{"kind":"epilogue","arc":"epilogue","title":"After: refused the board","text":"You made the review board go through a lawyer. The lawyer's bill was framed in the Institute's common room as a warning to students.","requires":{"flag":"refused_the_board"}},
"after.core_shown":{"kind":"epilogue","arc":"epilogue","title":"After: core shown","text":"{hammerschultz} voted against his own ruling and never explained it. In his papers, found after his death, there is a photograph of a grey layer in an ice core, labelled 'twice'.","requires":{"flag":"core_shown"}},
"samples.lab":{"kind":"event","arc":"pool","act":2,"title":"Mostly proud","text":["{samples} runs the insurer's clone lab at Nova Labs, and next door an unpaid lab in theoretical xenobiology: what could live in places where nothing should.","She grew {clone} from your customs scan. She is apologetic about it, in the way of someone who is mostly proud."],"requires":{"at":"Nova Labs","done":"clone.scan","act_min":2},"choices":[{"id":"ask","say":"Ask whether {clone.short} remembers being you","effects":{"plot_points":4,"set":["asked_samples"]},"next":["samples.answer"]},{"id":"scan","say":"Let her scan you again, for science (she pays 2,000)","effects":{"money":2000,"set":["rescanned"]}},{"id":"leave","say":"Leave"}],"who":["samples"],"chance":0.3},
"samples.answer":{"kind":"event","arc":"pool","act":2,"title":"Up to the scan","text":"'Everything up to the scan,' {samples.short} says. 'After that, only what it chose.' She thinks about it. 'Which is the same as you, really. I should write that down.' She does.","requires":{"flag":"asked_samples"},"who":["samples"]},
"sci.floaters":{"kind":"quest","arc":"science","act":2,"title":"Floaters, sinkers, hunters","text":["In 1976 two astronomers imagined animals living in Jupiter's clouds: floaters drifting like balloons, sinkers falling slowly, hunters eating both. {samples} thinks a brown dwarf's air is a better place to look: at the right depth in WISE 0855 it is about room temperature.","She has built a balloon. It needs dropping into the warm layer and fishing out a day later, before it sinks somewhere nothing could come back from."],"requires":{"at":"DSO-Beta","done":"samples.lab","not_flag":"flew_floaters"},"choices":[{"id":"probe","say":"Lower it on the deep-space probe's line (15 fuel)","requires":{"has":{"items":["probe"]},"cargo.fuel":15},"effects":{"cargo.fuel":-15,"research_points":140,"money":3000,"plot_points":6,"set":["flew_floaters"]},"next":["sci.floaters.result"]},{"id":"fuel","say":"Fly it on your own fuel (30 fuel)","requires":{"cargo.fuel":30},"effects":{"cargo.fuel":-30,"research_points":140,"money":3000,"plot_points":6,"set":["flew_floaters"]},"next":["sci.floaters.result"]},{"id":"depot","say":"Buy the burn from the depot (9,000 credits)","requires":{"money":9000},"effects":{"money":-7500,"research_points":140,"plot_points":4,"set":["flew_floaters"]},"next":["sci.floaters.result"]},{"id":"later","say":"Not now (the offer stands)"}],"who":["samples"],"chance":0.35,"repeat":{"cooldown":6}},
"sci.floaters.result":{"kind":"event","arc":"science","act":2,"title":"Floaters, sinkers, hunters: result","text":"The balloon comes back with no floaters, no sinkers and no hunters, and a smell nobody can name. {samples.short} paints 'nothing alive, as far as a balloon can tell' on her lab door. The next morning she has crossed out 'nothing'.","requires":{"flag":"flew_floaters"},"who":["samples"]},
"after.rescanned":{"kind":"epilogue","arc":"epilogue","title":"After: rescanned","text":"{samples} kept your second scan in her own freezer, labelled 'for science', with a note that nobody may grow it without asking you first. Somebody asked.","requires":{"flag":"rescanned"}},
"neon.lorisa":{"kind":"event","arc":"neons","act":2,"title":"The other twin","text":"{fluencer_manager} is {fluencer.short}'s twin and her manager: the same face, no cameras. She handles the money while her sister handles the light, and she has brought a contract.","variants":[{"requires":{"flag":"fluencer_exposed"},"text":"{fluencer_manager} is {fluencer.short}'s twin and her manager: the same face, no cameras. She handles the money while her sister handles the light. She has brought a lawyer."}],"requires":{"done":"neon.fluencer","since":{"neon.fluencer":10},"venue":"port"},"choices":[{"id":"hull","say":"Sign: her sister's name on your hull, a metre high (+10,000)","requires":{"not_flag":"fluencer_exposed"},"effects":{"money":10000,"passenger_reputation":-2,"set":["brisa_hull"]}},{"id":"settle","say":"Settle with the lawyer (4,000)","requires":{"flag":"fluencer_exposed","money":4000},"effects":{"money":-4000,"set":["settled_lorisa"]}},{"id":"no","say":"Decline politely","effects":{"plot_points":2}}],"who":["fluencer_manager"],"chance":0.3},
"after.settled_lorisa":{"kind":"epilogue","arc":"epilogue","title":"After: settled lorisa","text":"{fluencer_manager} framed your settlement cheque and hung it in her office between two lawsuits she won.","requires":{"flag":"settled_lorisa"}},
"after.brisa_hull":{"kind":"epilogue","arc":"epilogue","title":"After: brisa hull","text":"Your hull carried {fluencer.short}'s name, a metre high, for six years. People still recognise the ship by the shadow where the letters were.","requires":{"flag":"brisa_hull"}},
"rumour.ullage":{"kind":"rumour","arc":"cargolytes","title":"Rumour: the Sender","text":"At the outpost a hollow-eyed preacher called {ullage} tells anyone who will listen that every crate has a sender, and every sender has a Sender. He takes donations in cargo, and counts them twice.","requires":{"at_type":"DeepSpaceOutpost","act_min":2},"who":["ullage"],"repeat":true},
"gossip.lading":{"kind":"rumour","arc":"gossip","title":"Gossip: lading","text":"Cargolytes greet each other with 'in apparent good order and condition'. The customs officers at Gamma have started saying it back, to see what happens.","requires":{"act_min":2},"repeat":true},
"cargolytes.raid":{"kind":"event","arc":"cargolytes","act":2,"title":"In apparent good order","text":["Six ships with containers welded to their bows come out of the dark and start cutting containers off the convoy you are travelling with. They sing while they cut. The Cargolytes' council, {sixpack}, takes the cargo in person.","{sarga_farga} leads the boarders. 'In apparent good order and condition,' she says, and cuts."],"variants":[{"requires":{"flag":"sold_the_schedules"},"text":["Six ships with containers welded to their bows come out of the dark and start cutting containers off the convoy. They go straight for the valuable ones, as if they had the schedule. They have the schedule. You sold it.","{sarga_farga} leads the boarders. 'In apparent good order and condition,' she says, and cuts."]},{"requires":{"any":[{"flag":"convoy_friend"},{"flag":"convoy_helped"}]},"text":["Six ships with containers welded to their bows come out of the dark and start cutting containers off {convoy_captain.short}'s convoy. They sing while they cut. The Cargolytes' council, {sixpack}, takes the cargo in person.","{sarga_farga} leads the boarders. 'In apparent good order and condition,' she says, and cuts. {convoy_captain.short} is on the channel, very calm, asking who is going to help."]}],"requires":{"act_min":2,"turn_min":25,"at_type":["Planet","AsteroidBase"]},"choices":[{"id":"defend","say":"Defend the convoy","effects":{"code":"fight cargolytes","plot_points":5,"set":["defended_the_convoy","met_cargolytes","convoy_helped"]}},{"id":"tithe","say":"Offer them a tithe: one container, counted in TEU","effects":{"cargo.agri":-30,"plot_points":2,"set":["tithe_paid","met_cargolytes"]},"next":["cargolytes.receipt"]},{"id":"run","say":"Cut your own containers loose and run","effects":{"cargo.tech":-40,"cargo.agri":-40,"set":["ran_from_the_sixpack","met_cargolytes"]}}],"who":["sixpack","sarga_farga"],"chance":0.12},
"cargolytes.receipt":{"kind":"event","arc":"cargolytes","act":2,"title":"A receipt","text":"A Cargolyte called Sister Tare weighs your container, subtracts the weight of the container, and gives you a receipt. It says 'clean lading'. Among Cargolytes, that is a blessing. Among customs officers, it is evidence.","requires":{"flag":"tithe_paid"},"who":["sarga_farga"]},
"cargolytes.targa":{"kind":"event","arc":"cargolytes","act":3,"title":"Who helped","text":"{convoy_captain.short} lost nine containers to {sixpack}. She doesn't mention it. She mentions everything else: the weather, the dues, her liquorice root. That is how you know.","requires":{"flag":["ran_from_the_sixpack","convoy_friend"],"since":{"cargolytes.raid":5}},"effects":{"set":["targa_remembers_the_raid"]},"who":["convoy_captain"],"chance":0.4},
"after.defended_the_convoy":{"kind":"epilogue","arc":"epilogue","title":"After: defended the convoy","text":"{sixpack} put your ship's registry in the Lading as 'not to be received'. Among Cargolytes it is the closest thing to a compliment.","requires":{"flag":"defended_the_convoy"}},
"after.tithe_paid":{"kind":"epilogue","arc":"epilogue","title":"After: tithe paid","text":"Your receipt from Sister Tare, 'clean lading', hangs in your galley. Twice it got you waved through a Cargolyte blockade. Once it got you arrested.","requires":{"flag":"tithe_paid"}},
"after.targa_remembers_the_raid":{"kind":"epilogue","arc":"epilogue","title":"After: targa remembers the raid","text":"{convoy_captain.short} never mentioned the nine containers again. She did leave you off one list, once, and you knew which one.","requires":{"flag":"targa_remembers_the_raid"}},
"mil.hovertank":{"kind":"quest","arc":"legion_freight","act":2,"title":"A tank with no wheels","text":["Stellar Dynamics' legion has built a hovertank: forty tonnes on a cushion of air, a skirt of rubber fingers, a gun it is not allowed to talk about. It is wanted on Delta c, where the dust plains are the only open ground in the near systems with air thick enough to hover on.","It does not fit in a warship. It fits, the yard says, in yours, if you take out a bulkhead. Its commander, {tank_commander}, and its driver, {tank_driver}, ride along. The pay is good and half of it is up front."],"requires":{"at":"Alpha","act_min":2,"not_flag":"hovertank_taken"},"choices":[{"id":"carry","say":"Carry it (+8,000 now, 12,000 at Delta; takes 150 units of hold)","requires":{"hold_free":150},"effects":{"money":8000,"code":"stow 150 hovertank as the legion's prototype hovertank","set":["hovertank_taken","hovertank_aboard"]}},{"id":"shunt","say":"Let {loader} stow it tighter (+8,000 now; takes 100 units)","requires":{"has":{"crew":["loader"]},"hold_free":100},"effects":{"money":8000,"code":"stow 100 hovertank as the legion's prototype hovertank, packed tight","set":["hovertank_taken","hovertank_aboard"]}},{"id":"later","say":"Not now (the offer stands; it needs 150 units of free hold)"}],"who":["tank_commander","tank_driver"],"chance":0.3,"repeat":{"cooldown":6}},
"mil.hovertank.fans":{"kind":"event","arc":"legion_freight","act":2,"title":"Warming the skirt","text":"{tank_driver} wants to warm the skirt before the drop: run the lift fans for a minute, in your hold. {tank_commander} says no. {tank_driver} says it is in the manual. It is in the manual. The manual was written by {tank_driver}.","requires":{"flag":"hovertank_aboard","since":{"mil.hovertank":2}},"choices":[{"id":"let","say":"Let her run the fans","effects":{"cargo.agri":-10,"plot_points":2},"next":["mil.hovertank.fans.ran"]},{"id":"oksana","say":"Let {mechanic.short} check the fans first","requires":{"has":{"crew":["mechanic"]}},"effects":{"plot_points":3,"set":["oksana_tuned_the_tank"]},"next":["mil.hovertank.fans.tuned"]},{"id":"no","say":"No"}],"who":["tank_driver","tank_commander"],"chance":0.4},
"mil.hovertank.fans.ran":{"kind":"event","arc":"legion_freight","act":2,"title":"Rearranged","text":"Forty tonnes rise a hand's breadth and every loose crate in the hold rearranges itself by weight. Ten crates of agri go through the air vent. {tank_driver} calls it a successful test.","requires":{},"who":["tank_driver"]},
"mil.hovertank.fans.tuned":{"kind":"event","arc":"legion_freight","act":2,"title":"Tuned","text":"{mechanic.short} finds two fans wired backwards. {tank_driver} goes quiet for a long time and then asks, very politely, whether {mechanic.short} has ever thought about the legion.","requires":{},"who":["tank_driver"]},
"mil.hovertank.buyer":{"kind":"event","arc":"legion_freight","act":2,"title":"A better address","text":"A message with no sender offers you forty thousand to deliver the hovertank somewhere else: an inner-systems depot, no questions, the legion to be told it fell off the ship. The message is signed with one word: {serac.short}.","variants":[{"requires":{"flag":"convoy_friend"},"text":"A message with no sender offers you forty thousand to deliver the hovertank somewhere else: an inner-systems depot, no questions. It is signed with one word: {serac.short}. Ten minutes later {convoy_captain.short} sends one word too: 'Don't.'"}],"requires":{"flag":"hovertank_aboard","since":{"mil.hovertank":3}},"choices":[{"id":"deliver","say":"Delete it and fly on","effects":{"plot_points":3}},{"id":"sell","say":"Take the forty thousand","effects":{"money":40000,"code":"unstow hovertank","set":["sold_the_hovertank"],"clear":["hovertank_aboard"]},"next":["mil.hovertank.sold"]}],"who":["serac"],"chance":0.35},
"mil.hovertank.sold":{"kind":"event","arc":"legion_freight","act":2,"title":"Fell off the ship","text":"The depot's cranes take the tank before you have finished docking. {tank_commander} and {tank_driver} are not invited to the inner systems; they get a ticket home. {tank_commander} doesn't say anything. She writes your ship's name on the inside of her cap.","requires":{},"who":["tank_commander"]},
"mil.hovertank.delivered":{"kind":"event","arc":"legion_freight","act":2,"title":"The dust plains","text":["On Delta c's dust plains the hovertank lifts, slides, digs the front of its skirt into a dune and stands on its nose. {tank_driver} has earned her name again. {skirt_fitter}, who replaces the skirt's rubber fingers and has been called Fingers for so long he has forgotten his name, starts replacing them.","On the second try it flies: forty tonnes, a metre off the ground, faster than anything on wheels. The design will outlive everyone who touched it."],"variants":[{"requires":{"flag":"oksana_tuned_the_tank"},"text":["On Delta c's dust plains the hovertank lifts on the first try, with both fans the right way round, and flies: forty tonnes, a metre off the ground, faster than anything on wheels.","{skirt_fitter}, who has been called Fingers for so long he has forgotten his name, has nothing to replace and does not know what to do with himself. The design will outlive everyone who touched it."]}],"requires":{"at":"Delta","flag":"hovertank_aboard"},"effects":{"money":12000,"plot_points":8,"combat_rating":1,"code":"unstow hovertank","set":["delivered_the_hovertank"],"clear":["hovertank_aboard"]},"who":["tank_commander","tank_driver","skirt_fitter"]},
"mil.hovertank.late":{"kind":"event","arc":"legion_freight","act":2,"title":"Where is our tank","text":"The legion writes to ask where its tank is. {tank_commander} writes back that it is in a cargo hold, being looked after, and adds a postscript nobody at headquarters understands: 'turret down'. They dock your pay for the delay.","requires":{"flag":"hovertank_aboard","since":{"mil.hovertank":30}},"effects":{"money":-3000},"who":["tank_commander"]},
"after.delivered_the_hovertank":{"kind":"epilogue","arc":"epilogue","title":"After: delivered the hovertank","text":"The hovertank you carried to Delta was the first of a long line. Two centuries later its great-grandchildren were crated for Project ERYX's first missions, for a world nobody had reached yet. The loading manual still had your ship in a footnote.","requires":{"flag":"delivered_the_hovertank"}},
"after.sold_the_hovertank":{"kind":"epilogue","arc":"epilogue","title":"After: sold the hovertank","text":"The hovertank you sold never turned up in any inner-systems inventory. Forty years later a hovertank of the same design led the Mandate's first parade. Its serial number had been filed off, and then, carefully, put back.","requires":{"flag":"sold_the_hovertank"}},
"after.oksana_tuned_the_tank":{"kind":"epilogue","arc":"epilogue","title":"After: oksana tuned the tank","text":"{mechanic.short}'s fix for the lift fans went into the legion's manual as an amendment, signed by {tank_driver}, who credited 'a fitter who swears'.","requires":{"flag":"oksana_tuned_the_tank"}},
"mil.exoparts":{"kind":"quest","arc":"legion_freight","act":2,"title":"Knees for the garrison","text":["The legion keeps a garrison at the quiet outpost at Scholz's Star, and nobody will say what it guards. Its twelve exoskeletons have stood still for a month for want of knee actuators. {quartermaster_dsog}'s order is on the ore exchange's board, three months old, stamped 'urgent' four times in four different colours.","Forty units of actuators, bearings and hydraulic seals, to be at the outpost within fifteen turns. After that the garrison walks, and the pay walks with it."],"requires":{"at":"Epsilon","act_min":2,"not_flag":"exoparts_taken"},"choices":[{"id":"take","say":"Take the parts (+3,000 now, 9,000 on time; takes 40 units of hold)","requires":{"hold_free":40},"effects":{"money":3000,"code":"stow 40 exoparts as exoskeleton knee parts for Scholz's Star","set":["exoparts_taken","exoparts_aboard"]}},{"id":"later","say":"Not now (the offer stands)"}],"who":["quartermaster_dsog"],"chance":0.3,"repeat":{"cooldown":6}},
"mil.exoparts.late":{"kind":"event","arc":"legion_freight","act":2,"title":"On foot","text":"A message from {quartermaster_dsog.short} at Scholz's Star: the garrison has gone out on patrol on foot, in the suits, unpowered, pulling them. He would still like the knees. He does not say when.","requires":{"flag":"exoparts_aboard","since":{"mil.exoparts":15}},"effects":{"set":["exoparts_late"]},"who":["quartermaster_dsog"]},
"mil.exoparts.delivered":{"kind":"event","arc":"legion_freight","act":2,"title":"Walking again","text":["The garrison unloads the crates before your engines are cold. By evening twelve exoskeletons are walking the outpost's corridors with the confidence of people who have been pulling them for a month. {exo_operator}, the show-off, does a little dance in his. Nobody stops him.","{quartermaster_dsog} signs for the parts, slowly, and pays."],"requires":{"at":"DSO-Gamma","flag":"exoparts_aboard"},"choices":[{"id":"fee","say":"Collect the fee (9,000)","requires":{"not_flag":"exoparts_late"},"effects":{"money":9000,"plot_points":5,"code":"unstow exoparts","set":["delivered_the_exoparts"],"clear":["exoparts_aboard"]}},{"id":"late","say":"Collect what's left of the fee (3,000)","requires":{"flag":"exoparts_late"},"effects":{"money":3000,"plot_points":2,"code":"unstow exoparts","set":["delivered_the_exoparts"],"clear":["exoparts_aboard"]}},{"id":"fit","say":"Let {mechanic.short} fit them properly (the fee, and the legion remembers)","requires":{"has":{"crew":["mechanic"]},"not_flag":"exoparts_late"},"effects":{"money":9000,"plot_points":7,"combat_rating":1,"code":"unstow exoparts","set":["delivered_the_exoparts","fitted_the_exos"],"clear":["exoparts_aboard"]}}],"who":["quartermaster_dsog","exo_operator"]},
"mil.exoparts.guard":{"kind":"event","arc":"legion_freight","act":2,"title":"What the garrison guards","text":"Over a drink you ask {quartermaster_dsog.short} what the garrison guards. He looks out of the window at the dark where Scholz's Star's brown companion is. 'Ice,' he says. 'Something in the ice that the star dragged past us, seventy thousand years ago. Orders from the inner systems.' He starts to say who signed them, and doesn't.","requires":{"done":"mil.exoparts.delivered","since":{"mil.exoparts.delivered":1},"at":"DSO-Gamma"},"effects":{"plot_points":3,"research_points":20,"set":["asked_the_garrison"]},"who":["quartermaster_dsog"],"chance":0.5},
"after.delivered_the_exoparts":{"kind":"epilogue","arc":"epilogue","title":"After: delivered the exoparts","text":"The knee actuators you delivered to Scholz's Star were the pattern for every exoskeleton the Mandate built for a century: the same bearing, the same seal, the same complaint about both.","requires":{"flag":"delivered_the_exoparts"}},
"after.fitted_the_exos":{"kind":"epilogue","arc":"epilogue","title":"After: fitted the exos","text":"The garrison at Scholz's Star painted a spanner on every exoskeleton {mechanic.short} fitted. Two centuries later the Mandate's heavy infantry still paint one on, and none of them knows why.","requires":{"flag":"fitted_the_exos"}},
"after.asked_the_garrison":{"kind":"epilogue","arc":"epilogue","title":"After: asked the garrison","text":"The garrison at Scholz's Star was withdrawn the year after you asked what it guarded, and the outpost's records of it were withdrawn the year after that.","requires":{"flag":"asked_the_garrison"}},
"rootstock.offer":{"kind":"encounter","arc":"rootstock","act":2,"title":"Half voice","text":["The trading houses at Beta burn surplus biomass to keep the price up. At Gamma the mining company sells the miners food at company-store prices. A man called {stope} has an idea about the space in between, and a booth at the back where someone wants to meet you.","{meza_voce} is a Concord android, a nursery model, written off at ten years like all of them: on the books she is scrap, so on the books she belongs to nobody. Her voice was set to half for sleeping children. She never turned it up. You lean in. Sixty units of sealed biomass to Gamma, no manifest, 9,000 on delivery."],"requires":{"at":"Beta","venue":"cantina","act_min":2,"not_flag":"met_rootstock"},"choices":[{"id":"take","say":"Take the crates (60 units of hold)","requires":{"hold_free":60},"effects":{"code":"stow 60 biomass as sixty sealed crates of biomass for Gamma","set":["met_rootstock","biomass_aboard"]}},{"id":"tip","say":"Say no, and tell {inspector.short} about the booth","requires":{"done":"lauritz.inspection"},"effects":{"plot_points":3,"set":["met_rootstock","tipped_lauritz"]}},{"id":"no","say":"Say no","effects":{"set":["met_rootstock","refused_rootstock"]}}],"who":["stope","meza_voce"],"chance":0.3},
"rootstock.checkpoint":{"kind":"event","arc":"rootstock","act":2,"title":"Spot check","text":"A customs cutter pulls you over for a spot check. {inspector} comes aboard with her notebook and looks at sixty sealed crates with no manifest for a long time, the way other people look at a sunset.","requires":{"flag":"biomass_aboard","since":{"rootstock.offer":1},"not":{"at":"Gamma"}},"choices":[{"id":"fee","say":"Offer a 'processing fee' (2,000)","requires":{"money":2000},"effects":{"money":-2000,"set":["lauritz_bribed"]},"next":["rootstock.checkpoint.fee"]},{"id":"tea","say":"Let {steward} serve her tea, somewhere else","requires":{"has":{"crew":["steward"]}},"effects":{"plot_points":2},"next":["rootstock.checkpoint.tea"]},{"id":"open","say":"Open the crates for her","effects":{"plot_points":3,"set":["opened_the_crates"]},"next":["rootstock.checkpoint.open"]},{"id":"dump","say":"Dump the crates out of the airlock first","effects":{"code":"unstow biomass","set":["dumped_the_biomass"],"clear":["biomass_aboard"]}}],"who":["inspector"],"chance":0.5},
"rootstock.checkpoint.fee":{"kind":"event","arc":"rootstock","act":2,"title":"Written down","text":"{inspector.short} takes the fee, writes it down, gives you a receipt, and waves you on. You have a feeling the receipt is the dangerous part.","requires":{},"who":["inspector"]},
"rootstock.checkpoint.tea":{"kind":"event","arc":"rootstock","act":2,"title":"Very good tea","text":"{steward} serves tea in the galley, with the good cups, and asks {inspector.short} about her notebook. She talks about it for an hour. She leaves without looking in the hold and, at the airlock, says it was very good tea, in a voice that suggests she knows exactly why.","requires":{},"who":["inspector","steward"]},
"rootstock.checkpoint.open":{"kind":"event","arc":"rootstock","act":2,"title":"One item of scrap","text":"The crates hold biomass, as promised, and in the last one an android folded small, asleep, with a postage label. {inspector.short} reads the label, checks a register, and writes: 'Biomass, sixty units; scrap, one item.' A written-off android is legally scrap. Scrap needs no papers. She shuts the crate gently.","requires":{},"who":["inspector"]},
"rootstock.delivery":{"kind":"event","arc":"rootstock","act":2,"title":"Night shift","text":["The miners unload at night. {stope} counts the crates twice. {vent_boss}, who decides who breathes on level nine, has started deciding who eats too, and does it fairly, which the mining company finds harder to forgive than the smuggling.","{stope} pays you. 'The company sells them food at three times Beta's price,' he says. 'We sell it at twice. It's still a crime. It's a smaller one.'"],"requires":{"at":"Gamma","flag":"biomass_aboard"},"choices":[{"id":"pay","say":"Take the 9,000","effects":{"money":9000,"code":"unstow biomass","set":["rootstock_delivered"],"clear":["biomass_aboard"]}},{"id":"give","say":"Tell {vent_boss.short} to keep your cut for level nine","effects":{"plot_points":6,"passenger_reputation":4,"code":"unstow biomass","set":["rootstock_delivered","fed_gamma"],"clear":["biomass_aboard"]}}],"who":["stope","vent_boss"]},
"rootstock.bigger":{"kind":"event","arc":"rootstock","act":3,"title":"The family business","text":["{meza_voce.short} wants a bigger run: a full convoy's worth of grain and biomass to Gamma, a hundred and fifty units, under the Hansa's own convoy seal. 25,000. You lean in to hear the number.","On the way out {stope} walks beside you and says, without moving his lips, that customs has somebody inside the family, and that he would like you to know that he has told you."],"requires":{"flag":"rootstock_delivered","act_min":3,"since":{"rootstock.delivery":10}},"choices":[{"id":"take","say":"Take the run (150 units of hold)","requires":{"hold_free":150},"effects":{"code":"stow 150 biomass as the family's big run of biomass for Gamma","set":["big_run"]}},{"id":"both","say":"Take the run, and tell {inspector.short} when and where","requires":{"done":"lauritz.inspection","hold_free":150},"effects":{"code":"stow 150 biomass as the family's big run of biomass for Gamma","set":["big_run","double_cross"]}},{"id":"out","say":"Tell her you're out","effects":{"set":["out_of_the_family"]},"next":["rootstock.out"]}],"who":["meza_voce","stope"],"chance":0.35},
"rootstock.out":{"kind":"event","arc":"rootstock","act":3,"title":"Nobody leaves","text":"'Nobody leaves the family,' {meza_voce.short} says, at half voice. 'They are written off.' Three days later a fast cutter with very good paint comes alongside.","requires":{},"effects":{"code":"fight rootstock","plot_points":4},"who":["meza_voce"]},
"rootstock.sting":{"kind":"event","arc":"rootstock","act":3,"title":"At Gamma, at night","text":"Gamma's dock lights go out as you come in, and come back on as customs cutters, six of them, with {inspector} on the lead one. Somebody inside the family talked. The miners on the dock look at the crates, and at the cutters, and at you.","variants":[{"requires":{"flag":"double_cross"},"text":"Gamma's dock lights go out as you come in, and come back on as customs cutters, exactly where you told {inspector} they should be. {stope} is on the dock to meet the crates. He sees the cutters, and then he sees your face, and he understands."}],"requires":{"at":"Gamma","flag":"big_run"},"choices":[{"id":"handover","say":"Hand the crates to customs","effects":{"code":"unstow biomass","plot_points":3,"set":["rootstock_caught"],"clear":["big_run"]},"next":["rootstock.sting.caught"]},{"id":"miners","say":"Open the hold to the miners before customs boards (a 5,000 fine)","requires":{"money":5000},"effects":{"code":"unstow biomass","plot_points":6,"passenger_reputation":6,"money":-5000,"set":["fed_gamma","rootstock_family"],"clear":["big_run"]},"next":["rootstock.sting.miners"]},{"id":"run","say":"Run for it","requires":{"not_flag":"double_cross"},"effects":{"code":"fight militia","set":["ran_the_sting"]},"next":["rootstock.sting.ran"]}],"who":["inspector","stope"]},
"rootstock.sting.caught":{"kind":"event","arc":"rootstock","act":3,"title":"Seized","text":"Customs seizes a hundred and fifty units of biomass and arrests {stope}, who goes quietly and nods to you on the way past. {meza_voce} was never there; she never is. {inspector.short} writes it all down, including what you did, which she underlines.","requires":{},"who":["inspector","stope"]},
"rootstock.sting.miners":{"kind":"event","arc":"rootstock","act":3,"title":"Too many witnesses","text":"By the time customs boards, a hundred and fifty units of food have gone down the shafts in a thousand pairs of hands. {inspector.short} fines you for the crates, writes 'distributed' in her notebook, and does not arrest anyone, because {vent_boss} has made sure there are too many people to arrest.","requires":{},"who":["inspector","vent_boss"]},
"rootstock.sting.ran":{"kind":"event","arc":"rootstock","act":3,"title":"Ran","text":"Whether or not you got clear, the crates are gone: dumped, seized or shot through. {stope} sends a message afterwards: 'The family noticed you tried.' From the family, that is a compliment.","requires":{},"effects":{"code":"unstow biomass","set":["rootstock_family"],"clear":["big_run"]},"who":["stope"]},
"rootstock.revenge":{"kind":"event","arc":"rootstock","act":4,"title":"Half voice, on the open channel","text":"{meza_voce} comes on the open channel, at half voice, so that every ship in range has to turn up the volume to hear her say your name. Then the fast cutters come.","requires":{"flag":"double_cross","since":{"rootstock.sting":15}},"effects":{"code":"fight rootstock edge 1","set":["voce_remembers"]},"who":["meza_voce"],"chance":0.4},
"rootstock.knees":{"kind":"event","arc":"rootstock","act":2,"title":"Spare knees","text":"{stope} hails you between docks. Written-off androids wear out at the knees, like everybody, and nobody sells them parts. Your hold has forty units of exactly the right actuators. The family offers 15,000, and an introduction.","requires":{"flag":["exoparts_aboard","met_rootstock"],"since":{"mil.exoparts":2}},"choices":[{"id":"no","say":"The parts are the garrison's","effects":{"plot_points":2}},{"id":"sell","say":"Sell them the knees","effects":{"money":15000,"code":"unstow exoparts","set":["sold_the_exoparts","rootstock_family"],"clear":["exoparts_aboard"]}}],"who":["stope"],"chance":0.4},
"rootstock.favour":{"kind":"event","arc":"rootstock","act":3,"title":"Last week's prices","text":"In a bad week {meza_voce.short} sends word: the family will take your agri at last week's prices, no questions, the way family does. You would rather not think about where it goes. You know where it goes: down the shafts at Gamma.","requires":{"flag":"rootstock_family","act_min":3,"cargo.agri":40},"effects":{"cargo.agri":-40,"money":6000,"set":["voce_bought_the_agri"]},"who":["meza_voce"],"chance":0.25},
"rootstock.spoiled":{"kind":"event","arc":"rootstock","act":2,"title":"Compost","text":"The biomass in the sealed crates has started composting itself, warmly, and the hold smells like a farm drum in August. {stope} sends a tug to take it off your hands and pays nothing. 'It fed something,' he says. 'Just not anybody.'","requires":{"flag":"biomass_aboard","since":{"rootstock.offer":25}},"effects":{"code":"unstow biomass","clear":["biomass_aboard"],"set":["biomass_spoiled"]},"who":["stope"]},
"rootstock.spoiled_big":{"kind":"event","arc":"rootstock","act":3,"title":"The family's bill","text":"A hundred and fifty units of the family's biomass have spoiled in your hold. {meza_voce.short} sends a tug and a bill, itemised, at half voice. The family does not write things off twice.","requires":{"flag":"big_run","since":{"rootstock.bigger":25}},"effects":{"code":["unstow biomass","lose money 0.1 min 8000"],"clear":["big_run"],"set":["biomass_spoiled"]},"who":["meza_voce"]},
"after.biomass_spoiled":{"kind":"epilogue","arc":"epilogue","title":"After: biomass spoiled","text":"The crates of biomass that spoiled in your hold left a smell no refit could shift. Buyers of your old ship were told it was 'agricultural character'.","requires":{"flag":"biomass_spoiled"}},
"after.rootstock_family":{"kind":"epilogue","arc":"epilogue","title":"After: rootstock family","text":"The Rootstock never asked you for anything again, and never needed to. Thirty years on, written-off androids still get their knees from somewhere, and Gamma still eats at twice Beta's price instead of three times.","requires":{"flag":"rootstock_family"}},
"after.fed_gamma":{"kind":"epilogue","arc":"epilogue","title":"After: fed gamma","text":"Level nine at Gamma still keeps a crate lid on the canteen wall with your ship's registry chalked on it, for the food. The mining company has asked for it to be taken down eleven times.","requires":{"flag":"fed_gamma"}},
"after.double_cross":{"kind":"epilogue","arc":"epilogue","title":"After: double cross","text":"{meza_voce} never forgot a voice. Forty years later, in another part of the sky, an android speaking at half volume asked a customs officer whether a certain captain was still flying.","requires":{"flag":"double_cross"}},
"after.rootstock_caught":{"kind":"epilogue","arc":"epilogue","title":"After: rootstock caught","text":"{stope} did four years and came out with a law degree, earned by correspondence, which he now uses for the family.","requires":{"flag":"rootstock_caught"}},
"after.out_of_the_family":{"kind":"epilogue","arc":"epilogue","title":"After: out of the family","text":"You left the Rootstock, which nobody does. They wrote you off, which is how the family says goodbye.","requires":{"flag":"out_of_the_family"}},
"after.sold_the_exoparts":{"kind":"epilogue","arc":"epilogue","title":"After: sold the exoparts","text":"The garrison at Scholz's Star never got its knees. The Rootstock's androids walked on them for twenty years. Both sides blamed you, correctly.","requires":{"flag":"sold_the_exoparts"}},
"after.tipped_lauritz":{"kind":"epilogue","arc":"epilogue","title":"After: tipped lauritz","text":"{inspector} watched the booth at Beta for a year and caught nobody. She sent you a note: thank you for the tip, it was very interesting, she has no further questions, which from her is a threat.","requires":{"flag":"tipped_lauritz"}},
"after.opened_the_crates":{"kind":"epilogue","arc":"epilogue","title":"After: opened the crates","text":"The android you found folded in the crate wrote to you years later. It had been a nursery android too. It works for {meza_voce.short} now, at half voice.","requires":{"flag":"opened_the_crates"}},
"after.ran_the_sting":{"kind":"epilogue","arc":"epilogue","title":"After: ran the sting","text":"You ran from {inspector}'s sting at Gamma. She never chased you. She wrote your registry at the top of a fresh page, and left the rest of the page empty, for later.","requires":{"flag":"ran_the_sting"}},
"after.refused_rootstock":{"kind":"epilogue","arc":"epilogue","title":"After: refused rootstock","text":"You turned the Rootstock down at Beta. {stope} bought you a drink anyway, on the way out, and said the offer would keep. It kept for thirty years.","requires":{"flag":"refused_rootstock"}},
"after.voce_bought_the_agri":{"kind":"epilogue","arc":"epilogue","title":"After: voce bought the agri","text":"The Rootstock bought your agri at last week's prices, and you never asked where it went. You knew. That was the arrangement.","requires":{"flag":"voce_bought_the_agri"}},
"after.voce_remembers":{"kind":"epilogue","arc":"epilogue","title":"After: voce remembers","text":"{meza_voce} came for you once, after the double cross, and never again. Somebody asked her why. 'Once is a message,' she said, at half voice. 'Twice is a hobby.'","requires":{"flag":"voce_remembers"}},
"after.dumped_the_biomass":{"kind":"epilogue","arc":"epilogue","title":"After: dumped the biomass","text":"The biomass you dumped drifted for a decade and settled on a comet, which was then briefly famous for its smell.","requires":{"flag":"dumped_the_biomass"}},
"contract.loaders":{"kind":"quest","arc":"contracts","act":3,"title":"Down to the farms","text":["Gamma's miners are turning the mined-out galleries into farms: rock overhead keeps the flares off, and the old ventilation does the rest. {farm_tech} has bought twenty KRO-series loader agrobots from {krog}'s yard to carry soil, racks and harvests through tunnels nobody dug for farming.","They need a ship. {krog} looks over your hold and says it will do, which from {krog} is a reference. The contract pays on delivery and counts as trade."],"requires":{"chapter":"ch3a","at":"Epsilon","not_flag":"loaders_taken"},"choices":[{"id":"carry","say":"Carry the loaders (+5,000 now, 45,000 at Gamma; 120 units of hold)","requires":{"hold_free":120},"effects":{"money":5000,"code":"stow 120 loaders as twenty loader agrobots for Gamma's farms","set":["loaders_taken","loaders_aboard"]}},{"id":"shunt","say":"Let {loader} pack them (+5,000 now; 90 units)","requires":{"has":{"crew":["loader"]},"hold_free":90},"effects":{"money":5000,"code":"stow 90 loaders as twenty loader agrobots for Gamma's farms, packed by Shunt","set":["loaders_taken","loaders_aboard"]}},{"id":"later","say":"Not now (the offer stands; it needs 120 units of free hold)"}],"who":["farm_tech","krog"],"chance":0.4,"repeat":{"cooldown":5}},
"contract.loaders.restack":{"kind":"event","arc":"contracts","act":3,"title":"A report on your stowage","text":"Twenty loaders with nothing to load. By the second day they have restacked your hold by weight, by colour and by destination, and filed a report on your stowage. It is signed on behalf of {krog}. It is not kind.","requires":{"flag":"loaders_aboard","since":{"contract.loaders":2}},"effects":{"plot_points":2,"set":["loaders_restacked"]},"who":["krog"],"chance":0.4},
"contract.loaders.delivered":{"kind":"event","arc":"contracts","act":3,"title":"Who signs","text":["The loaders walk down the ramp in single file and into the galleries, where {farm_tech} has racks waiting under grow-lights. {vent_boss} counts them in and starts working out how much air a farm breathes.","Then the paperwork. The contract says 'to Gamma'. It does not say to whom. The mining company's agent offers sixty thousand for the loaders and the farms they will run. The miners' cooperative can find thirty-five, and {farm_tech} is looking at you."],"variants":[{"requires":{"flag":"saved_level_nine"},"text":["The loaders walk down the ramp in single file and into the galleries. The first farm is on level nine, which the miners now call by your ship's name, and {farm_tech} has racks waiting there under grow-lights.","Then the paperwork. The contract says 'to Gamma'. It does not say to whom. The mining company's agent offers sixty thousand for the loaders and the farms they will run. The miners' cooperative can find thirty-five, and {farm_tech} is looking at you."]}],"requires":{"at":"Gamma","flag":"loaders_aboard"},"choices":[{"id":"company","say":"Sign them over to the mining company (60,000 as trade profit)","effects":{"code":["unstow loaders","profit 60000"],"plot_points":4,"clear":["loaders_aboard"],"set":["gamma_farms_company"]}},{"id":"coop","say":"Sign them over to the miners' cooperative (35,000 as trade profit)","effects":{"code":["unstow loaders","profit 35000"],"plot_points":9,"passenger_reputation":4,"clear":["loaders_aboard"],"set":["gamma_farms_coop"]}}],"who":["farm_tech","vent_boss"]},
"contract.loaders.harvest":{"kind":"event","arc":"contracts","act":3,"title":"The first harvest","text":"The first harvest from under Gamma comes up the shafts: pale lettuce, fat mushrooms, beans that have never seen a star. The cooperative sells it at Beta's price, which is the first time anyone at Gamma has done that, and sends you a share.","variants":[{"requires":{"flag":"rootstock_family"},"text":"The first harvest from under Gamma comes up the shafts and sells at Beta's price. The cooperative sends you a share. {meza_voce.short} sends a note too, at what must be half voice even on paper: the family does not compete with farmers. It is the nearest thing to thanks she writes."}],"requires":{"flag":"gamma_farms_coop","since":{"contract.loaders.delivered":12}},"effects":{"code":"profit 12000","plot_points":3},"who":["farm_tech"],"chance":0.5},
"contract.loaders.store":{"kind":"event","arc":"contracts","act":3,"title":"Company prices","text":"The company store sells the first underground harvest at company prices. {vent_boss} buys one lettuce, holds it up in the canteen like evidence, and puts it on your table without a word.","requires":{"flag":"gamma_farms_company","since":{"contract.loaders.delivered":12},"at":"Gamma"},"effects":{"passenger_reputation":-2},"who":["vent_boss"],"chance":0.5},
"contract.harp":{"kind":"quest","arc":"contracts","act":3,"title":"The quantum harp","text":["{harp_engineer} has designed a relay network the Hansa calls the quantum harp: towers of holocrystal, each tuned to the next like a string, carrying prices between the stars faster than any convoy. Nobody is quite sure what is vibrating. {harp_engineer.short} says that is a separate grant.","Two towers' worth of crystal, eighty units, to Beta and to Delta. 25,000 a tower, counted as trade, and the harp's first prices to your ship before anyone else's."],"requires":{"chapter":"ch3a","at":"Alpha","not_flag":"harp_taken"},"choices":[{"id":"carry","say":"Carry the crystal (80 units of hold)","requires":{"hold_free":80},"effects":{"code":"stow 80 holocrystal as holocrystal for two harp towers, Beta and Delta","set":["harp_taken","harp_aboard"]}},{"id":"later","say":"Not now (the offer stands; it needs 80 units of free hold)"}],"who":["harp_engineer"],"chance":0.4,"repeat":{"cooldown":5}},
"contract.harp.hum":{"kind":"event","arc":"contracts","act":3,"title":"It hums","text":"The holocrystal hums in the jump, a low note that gets into the bulkheads and the teeth. {harp_engineer.short}'s instructions say it must not be allowed to resonate. They do not say how.","requires":{"flag":"harp_aboard","since":{"contract.harp":1}},"choices":[{"id":"lane","say":"Let {navigator.short} find a quiet lane","requires":{"has":{"crew":["navigator"]}},"effects":{"plot_points":2}},{"id":"pad","say":"Let {mechanic.short} pad the crates","requires":{"has":{"crew":["mechanic"]}},"effects":{"plot_points":2}},{"id":"hum","say":"Let it hum","effects":{"set":["harp_cracked"]},"next":["contract.harp.cracked"]}],"who":["harp_engineer"],"chance":0.5},
"contract.harp.cracked":{"kind":"event","arc":"contracts","act":3,"title":"A perfect line","text":"By morning one crystal has cracked along a perfect line, and the galley kettle can no longer boil without singing a fifth.","requires":{}},
"contract.harp.beta":{"kind":"event","arc":"contracts","act":3,"title":"A tower at Beta","text":"The crystal goes up as a tower on the ridge above the Beta dock, three storeys of something that is not quite glass. {harp_engineer.short}'s technicians tune it with a fork the size of a man and listen for the other end.","requires":{"at":"Beta","flag":"harp_aboard","not_flag":"harp_beta"},"choices":[{"id":"raise","say":"Raise the tower (25,000 as trade profit)","requires":{"not_flag":"harp_delta"},"effects":{"code":["stow 40 holocrystal as holocrystal for the last harp tower","profit 25000"],"plot_points":3,"set":["harp_beta"]}},{"id":"last","say":"Raise the last tower (25,000 as trade profit)","requires":{"flag":"harp_delta"},"effects":{"code":["unstow holocrystal","profit 25000"],"plot_points":3,"clear":["harp_aboard"],"set":["harp_beta"]}}],"who":["harp_engineer"]},
"contract.harp.delta":{"kind":"event","arc":"contracts","act":3,"title":"A tower at Delta","text":"The crystal goes up as a tower on the ridge above the Delta dock, three storeys of something that is not quite glass. {harp_engineer.short}'s technicians tune it with a fork the size of a man and listen for the other end.","requires":{"at":"Delta","flag":"harp_aboard","not_flag":"harp_delta"},"choices":[{"id":"raise","say":"Raise the tower (25,000 as trade profit)","requires":{"not_flag":"harp_beta"},"effects":{"code":["stow 40 holocrystal as holocrystal for the last harp tower","profit 25000"],"plot_points":3,"set":["harp_delta"]}},{"id":"last","say":"Raise the last tower (25,000 as trade profit)","requires":{"flag":"harp_beta"},"effects":{"code":["unstow holocrystal","profit 25000"],"plot_points":3,"clear":["harp_aboard"],"set":["harp_delta"]}}],"who":["harp_engineer"]},
"contract.harp.plays":{"kind":"event","arc":"contracts","act":3,"title":"First note","text":"The harp plays its first price at dawn, Alpha time: tech at Delta, three ticks up. Every dock in the near systems hears it at once. {port_broker} goes very quiet, and then asks, through its union, what the harp is paid. Your forecasts are sharper from now on: the harp carries the news.","variants":[{"requires":{"flag":"harp_cracked"},"text":"The harp plays its first price at dawn, Alpha time, a semitone flat. {harp_engineer.short} says it adds character. Every dock in the near systems hears it at once, and {port_broker} asks, through its union, what the harp is paid. Your forecasts are sharper from now on: the harp carries the news."}],"requires":{"flag":["harp_beta","harp_delta"]},"effects":{"plot_points":6,"set":["harp_relay"]},"who":["harp_engineer","port_broker"]},
"vip.concertina":{"kind":"encounter","arc":"vips","act":3,"title":"Two hundred of her","text":["{holo_star} sings in light: her concerts are two hundred holograms of herself, all in harmony, and she is booked for the gala at Epsilon where the Hansa's traders meet. Her own liner has been impounded over a contract dispute nobody will explain.","She wants your best cabin, and silence between four and six every afternoon."],"requires":{"chapter":"ch3a","at":"Alpha","venue":"port","not_flag":"concertina_met"},"choices":[{"id":"suite","say":"Give her your best cabin (+12,000 now, 20,000 at Epsilon)","requires":{"best_cabin":4},"effects":{"money":12000,"set":["concertina_met","concertina_aboard"]}},{"id":"plain","say":"Offer the cabin you have (+6,000 now)","requires":{"best_cabin":{"max":3}},"effects":{"money":6000,"set":["concertina_met","concertina_aboard","concertina_rough"]}},{"id":"no","say":"Decline","effects":{"set":["concertina_met"]}}],"who":["holo_star"],"chance":0.4},
"vip.concertina.rehearsal":{"kind":"event","arc":"vips","act":3,"title":"Four to six","text":"At four o'clock two hundred of {holo_star} fill your corridors, rehearsing. Your crew learns to walk through her. At five the ship's systems start harmonising, and at six everything stops at once, mid-note, as agreed.","variants":[{"requires":{"flag":"harp_aboard"},"text":"At four o'clock two hundred of {holo_star} fill your corridors, rehearsing, and the holocrystal in the hold starts singing along. She stops, listens, and rewrites her second act around it before six."}],"requires":{"flag":"concertina_aboard","since":{"vip.concertina":1}},"choices":[{"id":"steward","say":"Let {steward} keep the corridors clear for her","requires":{"has":{"crew":["steward"]}},"effects":{"passenger_reputation":3,"set":["concertina_pleased"]}},{"id":"private","say":"Ask for one song for the crew","effects":{"plot_points":2,"set":["concertina_pleased"]}},{"id":"quiet","say":"Ask her to rehearse more quietly"}],"who":["holo_star"],"chance":0.6},
"vip.concertina.gala":{"kind":"event","arc":"vips","act":3,"title":"The gala","text":"At the gala {holo_star} fills the ore exchange's great hall with two hundred of herself, and the traders who came to argue about the Mark stop arguing for an hour. Afterwards her agent finds you with an envelope.","variants":[{"requires":{"flag":"concertina_pleased"},"text":"At the gala {holo_star} fills the ore exchange's great hall with two hundred of herself and, in the encore, sings your ship's name. The traders who came to argue about the Mark stop arguing for an hour. Afterwards her agent finds you with an envelope."}],"requires":{"at":"Epsilon","flag":"concertina_aboard"},"choices":[{"id":"fee","say":"Take the fee (20,000)","requires":{"not_flag":"concertina_rough"},"effects":{"money":20000,"passenger_reputation":6,"plot_points":4,"clear":["concertina_aboard"],"set":["carried_concertina"]}},{"id":"fee_plain","say":"Take the fee (12,000)","requires":{"flag":"concertina_rough"},"effects":{"money":12000,"passenger_reputation":3,"plot_points":3,"clear":["concertina_aboard"],"set":["carried_concertina"]}},{"id":"share","say":"Ask for a share of the gala's takings instead (counts as trade)","requires":{"flag":"concertina_pleased"},"effects":{"code":"profit 30000","passenger_reputation":4,"plot_points":4,"clear":["concertina_aboard"],"set":["carried_concertina","concertina_share"]}}],"who":["holo_star"]},
"vip.wirth":{"kind":"encounter","arc":"vips","act":3,"title":"An underwriter in the cheap seats","text":["{underwriter} insures half the Concord's research ships and none of the Hansa's convoys. The Mark will need insured convoys to be worth anything, so he has come to look at the lanes himself: to Gamma, through the flare lanes, as a passenger.","He asks for your cheapest cabin, because that is where the risk is, and pays like a man who has never needed to ask the price."],"requires":{"chapter":"ch3a","at":"Epsilon","venue":"port","not_flag":"wirth_met"},"choices":[{"id":"take","say":"Take him (+15,000 now)","effects":{"money":15000,"set":["wirth_met","wirth_aboard"]}},{"id":"no","say":"Decline","effects":{"set":["wirth_met"]}}],"who":["underwriter"],"chance":0.4},
"vip.wirth.lanes":{"kind":"event","arc":"vips","act":3,"title":"Which way","text":"Ross 154 flares as you come in. The honest lane runs through the edge of it, the way every hauler goes. There is a longer one, round the back, where the view is lovely and the flares never reach. {underwriter.short} has a notebook open and is not looking at you.","requires":{"at":"Gamma","flag":"wirth_aboard"},"choices":[{"id":"honest","say":"Fly the flare lane, as haulers do","effects":{"code":"damage 5","plot_points":3,"set":["wirth_saw_it"]},"next":["vip.wirth.gamma"]},{"id":"pretty","say":"Take the long way round","effects":{"set":["wirth_pretty"]},"next":["vip.wirth.gamma"]}],"who":["underwriter"]},
"vip.wirth.gamma":{"kind":"event","arc":"vips","act":3,"title":"The signature","text":"At Gamma {underwriter} closes his notebook.","variants":[{"requires":{"flag":"wirth_saw_it"},"text":"At Gamma {underwriter} closes his notebook. 'Now I know what I'd be insuring,' he says, and signs: the Hansa's convoys, insured by the Concord's underwriters, at a premium he calls insulting and the Hansa will call a miracle. Convoy dues fall while the paperwork settles."},{"requires":{"flag":"wirth_pretty"},"text":"At Gamma {underwriter} closes his notebook. 'Lovely lanes,' he says. 'I wouldn't insure them.' He tips well, as people do when they have been shown the view instead of the road."}],"requires":{},"choices":[{"id":"signed","say":"Take the fee (20,000; convoy dues 15% lower for thirty turns)","requires":{"flag":"wirth_saw_it"},"effects":{"money":20000,"code":"dues hike 0.85","plot_points":8,"passenger_reputation":4,"clear":["wirth_aboard"],"set":["convoys_insured"]}},{"id":"tip","say":"Take the tip (10,000)","requires":{"flag":"wirth_pretty"},"effects":{"money":10000,"plot_points":2,"clear":["wirth_aboard"],"set":["wirth_declined"]}}],"who":["underwriter"]},
"after.gamma_farms_coop":{"kind":"epilogue","arc":"epilogue","title":"After: gamma farms coop","text":"The farms under Gamma were run by the miners' cooperative for sixty years. The loaders you carried are on the cooperative's crest, twenty little figures in a row, carrying a lettuce.","requires":{"flag":"gamma_farms_coop"}},
"after.gamma_farms_company":{"kind":"epilogue","arc":"epilogue","title":"After: gamma farms company","text":"The company's farms under Gamma made a great deal of money and no friends. The loaders you carried were sold on twice, and ended their days hauling ore again.","requires":{"flag":"gamma_farms_company"}},
"after.loaders_restacked":{"kind":"epilogue","arc":"epilogue","title":"After: loaders restacked","text":"Your hold was stacked by weight, colour and destination for the rest of the ship's life. Nobody dared change it.","requires":{"flag":"loaders_restacked"}},
"after.harp_relay":{"kind":"epilogue","arc":"epilogue","title":"After: harp relay","text":"The quantum harp grew to forty strings across the near systems. Its first two towers, at Beta and Delta, are still the ones the tuning forks are set by.","requires":{"flag":"harp_relay"}},
"after.harp_cracked":{"kind":"epilogue","arc":"epilogue","title":"After: harp cracked","text":"The harp's tower with the cracked crystal plays a semitone flat to this day. Musicians at Delta tune to it on purpose.","requires":{"flag":"harp_cracked"}},
"after.carried_concertina":{"kind":"epilogue","arc":"epilogue","title":"After: carried concertina","text":"{holo_star} recorded an album in your hold's acoustics and named it after your ship. It sold mostly to haulers, who play it during jumps.","requires":{"flag":"carried_concertina"}},
"after.concertina_share":{"kind":"epilogue","arc":"epilogue","title":"After: concertina share","text":"Your share of {holo_star}'s gala paid better than any cargo that year, which you never told the Hansa.","requires":{"flag":"concertina_share"}},
"after.convoys_insured":{"kind":"epilogue","arc":"epilogue","title":"After: convoys insured","text":"With the Concord's underwriters behind the convoys, the Mark became something banks would hold. {underwriter} kept your flight in his notebook as 'the honest lane'.","requires":{"flag":"convoys_insured"}},
"after.wirth_declined":{"kind":"epilogue","arc":"epilogue","title":"After: wirth declined","text":"{underwriter} insured the Hansa's convoys ten years later, after someone else flew him through the flares. He sent you a postcard of the view.","requires":{"flag":"wirth_declined"}},
"after.insured_vote":{"kind":"epilogue","arc":"epilogue","title":"After: insured vote","text":"The underwriters' signature on the table at Epsilon was the first time the Concord bet money on the Hansa. It was not the last.","requires":{"flag":"insured_vote"}},
"odds.ticket":{"kind":"event","arc":"odds","act":1,"title":"Bought it next week","text":"A passenger is sitting in your best cabin with no ticket and a very calm face. She says she bought it next week. She seems sure of the date.","requires":{"venue":"port","passengers_transported":2},"choices":[{"id":"steward","say":"Let {steward} check her hat","requires":{"has":{"crew":["steward"]}},"effects":{"passenger_reputation":3},"next":["odds.ticket.hat"]},{"id":"ride","say":"Let her ride","effects":{"plot_points":2,"set":["ticket_next_week"]}},{"id":"door","say":"Charge her the fare at the door","effects":{"money":300}},{"id":"off","say":"Put her off at the next dock","effects":{"passenger_reputation":-2}}],"chance":0.12,"repeat":{"cooldown":40}},
"odds.ticket.hat":{"kind":"event","arc":"odds","act":1,"title":"In the hat","text":"{steward} lifts her hat, removes a ticket, and replaces the hat, all with one hand. 'It is always in the hat,' he says. The ticket is dated next week.","requires":{},"who":["steward"]},
"odds.ticket.arrives":{"kind":"event","arc":"odds","act":2,"title":"Paid in full","text":"A ticket arrives in the post: one cabin on your ship, dated twenty turns ago, paid in full with interest, from an account the bank says will be opened next spring. The bank would like to know how. So would you.","requires":{"flag":"ticket_next_week","since":{"odds.ticket":20}},"effects":{"money":2500,"plot_points":2},"chance":0.5},
"odds.exam":{"kind":"event","arc":"odds","act":1,"title":"Question seven","text":"The Hansa renews hauler licences with a written exam, in a room with a clock that ticks loudly on purpose. Question seven: 'Your cargo begins to talk. You should:'","requires":{"at_type":"Planet","turn_min":4,"trades_completed":2},"choices":[{"id":"form","say":"(a) File form C-7","effects":{"plot_points":1},"next":["odds.exam.form"]},{"id":"listen","say":"(b) Listen","effects":{"plot_points":1},"next":["odds.exam.listen"]},{"id":"enter","say":"(c) Press Enter to continue","effects":{"plot_points":2},"next":["odds.exam.enter"]}],"chance":0.2},
"odds.exam.form":{"kind":"event","arc":"odds","act":1,"title":"Correct","text":"Correct. Everything is form C-7. You pass, and are given a copy of form C-7 to keep, in case.","requires":{}},
"odds.exam.listen":{"kind":"event","arc":"odds","act":1,"title":"Also correct","text":"Also correct. The examiner writes 'promising' next to your answer and underlines it twice. You pass.","requires":{}},
"odds.exam.enter":{"kind":"event","arc":"odds","act":1,"title":"We don't talk about that","text":"The examiner looks at you for a long time. 'We don't talk about that,' she says, very quietly, and passes you. On your way out you notice that everyone in the building pauses, now and then, as if waiting for something.","requires":{}},
"odds.volunteer":{"kind":"event","arc":"odds","act":2,"title":"The red jumpsuit","text":"A young security guard in a bright red jumpsuit volunteers for anything dangerous you might be doing. The older crews at the bar move their chairs away from him, without quite saying why.","requires":{"at_type":["DeepSpaceOutpost","AsteroidBase"],"act_min":2},"choices":[{"id":"take","say":"Take him on your next job","effects":{"plot_points":2,"set":["took_the_red"]},"next":["odds.volunteer.lucky"]},{"id":"desk","say":"Tell him to find a desk job","next":["odds.volunteer.desk"]}],"chance":0.12},
"odds.volunteer.lucky":{"kind":"event","arc":"odds","act":2,"title":"Lucky","text":"Against the expectations of everyone at the bar, he comes back from the job without a scratch. He has been promoted to 'lucky', which is not a rank. The bar has opened a pool on him.","requires":{"flag":"took_the_red"}},
"odds.volunteer.desk":{"kind":"event","arc":"odds","act":2,"title":"A desk","text":"He takes the advice, gets a desk at the convoy office, and is very happy. The bar is quietly disappointed. Somebody loses a bet.","requires":{}},
"odds.bugrat":{"kind":"event","arc":"odds","act":1,"title":"The ship's bugrat","text":"There is a bugrat in the hold: six legs, whiskers, an insect sheen and an expression of ownership. It has eaten one crate of agri and is looking at the second with respect.","requires":{"turn_min":6,"cargo.agri":1},"choices":[{"id":"shunt","say":"Let {loader} catch it","requires":{"has":{"crew":["loader"]}},"effects":{"set":["ship_bugrat"]},"next":["odds.bugrat.shunt"]},{"id":"adopt","say":"Adopt it as the ship's bugrat","effects":{"cargo.agri":-5,"plot_points":1,"set":["ship_bugrat"]}},{"id":"space","say":"Space it, regretfully"}],"chance":0.06},
"odds.bugrat.shunt":{"kind":"event","arc":"odds","act":1,"title":"Named","text":"{loader} catches the bugrat with two of its four arms, files it under 'crew', and names it Ballast. Nobody argues with the filing.","requires":{},"who":["loader"]},
"odds.signal":{"kind":"event","arc":"odds","act":2,"title":"The signal","text":["The listening post has found a signal: repeating, structured, from beyond the edge of the system. The team has not slept for a week. They play it for you before they explain it.","It is a forty-year-old Hansa advert for tinned soup, bounced back off a brown dwarf. They are not ready to talk about it."],"requires":{"at":"Alien Signal Research Outpost X","act_min":2},"choices":[{"id":"round","say":"Buy the team a round","effects":{"plot_points":2,"passenger_reputation":2}},{"id":"sell","say":"Sell the story to the soup company","effects":{"money":3000,"set":["sold_the_soup"]}}],"chance":0.4},
"odds.survey":{"kind":"event","arc":"odds","act":1,"title":"How likely are you to recommend this impact","text":"An impact alarm sounds across the habitat: the debris disk is throwing rocks again. Everyone files into the shelters, where the habitat's management system runs a customer satisfaction survey. Question one: 'How likely are you to recommend this impact to a friend?'","requires":{"at":"Omega XIV"},"choices":[{"id":"ten","say":"Ten out of ten","effects":{"plot_points":1},"next":["odds.survey.ten"]},{"id":"one","say":"One out of ten","effects":{"plot_points":1},"next":["odds.survey.one"]},{"id":"fix","say":"Fix the terminal so it stops asking","requires":{"any":[{"has":{"crew":["mechanic"]}},{"has":{"items":["scanner"]}}]},"effects":{"plot_points":3,"passenger_reputation":3},"next":["odds.survey.fixed"]}],"chance":0.3},
"odds.survey.ten":{"kind":"event","arc":"odds","act":1,"title":"Thank you","text":"The management system thanks you for your feedback and schedules another impact.","requires":{}},
"odds.survey.one":{"kind":"event","arc":"odds","act":1,"title":"Logged","text":"Your complaint is logged. The next rock is noticeably smaller. Coincidence, says the system.","requires":{}},
"odds.survey.fixed":{"kind":"event","arc":"odds","act":1,"title":"Silence","text":"The terminal stops asking. The shelter goes very quiet, and then several hundred people applaud, quietly, so as not to set it off again.","requires":{}},
"odds.auction":{"kind":"event","arc":"odds","act":2,"title":"Lot twelve","text":"The salvage auction at Theta III sells whatever Fomalhaut's collisions throw up. Lot twelve is described as 'a box, sealed, rattles'. Bidding is brisk and nobody knows why.","requires":{"at":"Theta III","act_min":2},"choices":[{"id":"bid","say":"Bid 3,000","requires":{"money":3000},"effects":{"money":-3000,"research_points":40,"plot_points":2},"next":["odds.auction.box"]},{"id":"gear","say":"Let the {tarnished_gear} outbid you"}],"chance":0.3},
"odds.auction.box":{"kind":"event","arc":"odds","act":2,"title":"Rattles","text":"Inside the box: a navigation computer from the twenty-third century that gives every distance in furlongs and every warning in verse. The research colonies pay for the furlongs. Nobody pays for the verse.","requires":{}},
"odds.audit":{"kind":"event","arc":"odds","act":3,"title":"Rounding","text":"The Hansa sends an auditor to count your crates. He counts them twice, frowns, and counts them a third time. You have one more than you own. 'Rounding,' he says, and writes it down.","requires":{"chapter":"ch3a","venue":"port"},"choices":[{"id":"keep","say":"Keep the extra crate","effects":{"cargo.tech":10,"set":["kept_the_rounding"]}},{"id":"report","say":"Report the error","effects":{"passenger_reputation":2,"plot_points":3}}],"chance":0.25},
"odds.strike":{"kind":"event","arc":"odds","act":3,"title":"Picket line","text":"{port_broker} and every other broker robot in the port stop work for a turn. They want to be paid in commission instead of electricity. The dock does its sums by hand, and everyone remembers why they bought the robots.","requires":{"chapter":"ch3a","at_type":"Planet"},"choices":[{"id":"cross","say":"Trade by hand while the prices are wrong (+2,000)","effects":{"money":2000,"set":["crossed_the_picket"]}},{"id":"battery","say":"Bring {port_broker.short} a battery","effects":{"plot_points":3,"set":["brought_tally_a_battery"]}}],"who":["port_broker"],"chance":0.2},
"after.kept_the_rounding":{"kind":"epilogue","arc":"epilogue","title":"After: kept the rounding","text":"The Hansa's audit of your ship is still open. It has been open for forty years. It is now the oldest open file in the league, and has its own clerk.","requires":{"flag":"kept_the_rounding"}},
"after.crossed_the_picket":{"kind":"epilogue","arc":"epilogue","title":"After: crossed the picket","text":"{port_broker} never quoted you an honest price again. It was never dishonest either. It was precise in a way you learned to dread.","requires":{"flag":"crossed_the_picket"}},
"after.brought_tally_a_battery":{"kind":"epilogue","arc":"epilogue","title":"After: brought tally a battery","text":"The broker robots won their strike. {port_broker} kept your battery, uncharged, on a shelf behind the counter, next to its first commission.","requires":{"flag":"brought_tally_a_battery"}},
"after.sold_the_soup":{"kind":"epilogue","arc":"epilogue","title":"After: sold the soup","text":"The soup company ran the signal as an advert: 'Heard across the stars.' The listening post's team has never forgiven you, and has never bought the soup.","requires":{"flag":"sold_the_soup"}},
"after.ship_bugrat":{"kind":"epilogue","arc":"epilogue","title":"After: ship bugrat","text":"The ship's bugrat outlived two refits and a reactor fire. It is buried under a dockyard at Alpha, with a plaque the dockyard did not approve.","requires":{"flag":"ship_bugrat"}},
"after.took_the_red":{"kind":"epilogue","arc":"epilogue","title":"After: took the red","text":"The guard in the red jumpsuit survived nine years of dangerous jobs and retired to a farm drum. The bar at the outpost still keeps the pool open, out of respect.","requires":{"flag":"took_the_red"}},
"drama.trade.squeeze":{"kind":"event","arc":"drama","act":3,"title":"The squeeze","text":["The three corporations' trading houses have decided the independent haulers are a rounding error. This month they correct it: tech dumped below cost at every dock you use, until the small haulers sell their routes or their ships.","The Hansa convoy office panics and raises its dues by half, 'until the market settles'. Your loan officer calls to ask how you are. He has never asked before.","Nobody at the trading houses will say whose idea it was. The dock clerks say a name quietly, the way you mention bad weather: {serac.short}."],"requires":{"chapter":"ch3a"},"effects":{"code":"squeeze tech 0.55"},"choices":[{"id":"hold","say":"Hold your lanes and eat the losses","effects":{"code":["lose money 0.12 min 3000","dues hike 1.5"],"plot_points":6,"passenger_reputation":5,"set":["held_the_lanes"]}},{"id":"bonds","say":"Buy two Hansa bonds and stand with the convoy captains","requires":{"money":12000},"effects":{"code":"buy bonds 2","plot_points":8,"set":["stood_with_convoys"]}},{"id":"cartel","say":"Haul for the trading houses until it blows over","effects":{"money":15000,"code":"dues hike 1.5","passenger_reputation":-5,"set":["cartel_hauler"]}}],"who":["serac"],"chance":0.25,"sound":"refusal"},
"drama.trade.margin_call":{"kind":"event","arc":"drama","act":4,"title":"Margin call","text":["The bank at Alpha sells your ship's loan to a collector who works for the trading houses. He calls it in, all of it, by the end of the week. Until it is settled the convoy office will not give you a berth.","You are a week away from being a captain without a ship, and everybody at the bar knows it. The barman gives you the good glass. That is how you know it is bad.","The collector's letters are signed by a law firm. The law firm's letters are signed by {serac.short}."],"variants":[{"requires":{"flag":"cartel_hauler"},"text":["The bank at Alpha sells your ship's loan to a collector who works for the trading houses. You know him: you hauled for him during the squeeze. He is very polite. He remembers your rates. He calls the loan in, all of it, by the end of the week.","Until it is settled the convoy office will not give you a berth. The barman gives you the good glass. That is how you know it is bad.","The collector's letters are signed by a law firm. The law firm's letters are signed by {serac.short}."]},{"requires":{"flag":"stood_with_convoys"},"text":["The bank at Alpha sells your ship's loan to a collector who works for the trading houses. He calls it in, all of it, by the end of the week. Until it is settled the convoy office will not give you a berth.","The convoy captains you stood with in the squeeze have heard. Nobody says anything yet. The barman gives you the good glass.","The collector's letters are signed by a law firm. The law firm's letters are signed by {serac.short}."]}],"requires":{"chapter":"ch3a","done":["ch3a","hansa.charter"],"since":{"drama.trade.squeeze":10},"plot_points":230},"choices":[{"id":"pay","say":"Pay it all, today","effects":{"code":"lose money 0.3 min 15000","plot_points":5,"set":["paid_in_full"]}},{"id":"bonds","say":"Cash in your Hansa bonds","requires":{"hansa_bonds":2},"effects":{"code":["sell bonds","lose money 0.1 min 5000"],"plot_points":5,"set":["sold_bonds"]}},{"id":"captains","say":"Ask the convoy captains to stand with you","requires":{"any":[{"flag":"stood_with_convoys"},{"flag":"hansa_founder"}]},"effects":{"code":"lose money 0.12 min 5000","plot_points":10,"passenger_reputation":5,"set":["captains_paid"]}},{"id":"convoy","say":"Ask {convoy_captain.short} to call in her favours","requires":{"flag":"convoy_friend"},"effects":{"code":"lose money 0.1 min 5000","plot_points":8,"set":["convoy_paid"]}},{"id":"neons","say":"Let {heritarchist.short} buy the debt for the family","requires":{"flag":"neon_sleeper_carried"},"effects":{"code":"lose money 0.05 min 2000","plot_points":5,"set":["neon_bought_debt"]}},{"id":"forged","say":"Ask {inspector.short} to look at the collector's papers","requires":{"flag":"lauritz_courier"},"effects":{"code":"lose money 0.03 min 1000","plot_points":8,"set":["collector_forged"]}},{"id":"hats","say":"Let the Grey Hats lose the paperwork","requires":{"done":"hatters.grey"},"effects":{"code":"lose money 0.08 min 4000","passenger_reputation":-10,"set":["paperwork_lost"]}}],"who":["serac"],"chance":0.3},
"drama.trade.mint":{"kind":"event","arc":"drama","act":4,"title":"The first Mark","text":["The Hansa strikes its first Marks in a borrowed foundry at Gamma: pellets of iridium and osmium, each stamped with the weight of cargo it stands for.","The foundry foreman takes you aside. He can short every pellet by a hair. Nobody with ordinary scales would notice for ten years, and the Hansa needs the margin. He says this the way other people talk about the weather."],"requires":{"chapter":"ch3a","since":{"drama.trade.margin_call":4},"trade_profit":220000},"choices":[{"id":"full","say":"Full weight, every pellet","effects":{"plot_points":6,"passenger_reputation":5,"set":["honest_mark"]}},{"id":"short","say":"Short them a hair; the Hansa needs it","effects":{"money":30000,"set":["short_mark"]}}],"chance":0.4},
"drama.trade.run":{"kind":"event","arc":"drama","act":4,"title":"A run on the Mark","text":["Somebody has weighed a Mark and found it light. Or says so. By morning every convoy captain wants credits for their Marks, and the convoy office has credits for about a third of them.","A queue goes twice round the dock. Somebody has started selling soup to it."],"variants":[{"requires":{"flag":"short_mark"},"text":["Somebody has weighed a Mark and found it light. They are right, and you know exactly how light. By morning every convoy captain wants credits for their Marks, and the convoy office has credits for about a third of them.","A queue goes twice round the dock. The foundry foreman has taken a holiday."]}],"requires":{"chapter":"ch3a","since":{"drama.trade.mint":6},"trade_profit":290000},"choices":[{"id":"weigh","say":"Weigh every Mark in public, on the dock","requires":{"flag":"honest_mark"},"effects":{"plot_points":10,"passenger_reputation":10,"set":["public_weighing"]}},{"id":"buy","say":"Buy Marks back with your own money","effects":{"code":"lose money 0.15 min 10000","plot_points":8,"passenger_reputation":8,"set":["stood_behind_the_mark"]}},{"id":"fenn","say":"Let {broker.short} talk the queue down","requires":{"has":{"crew":["broker"]}},"effects":{"plot_points":6,"set":["fenn_talked"]}},{"id":"run","say":"Let it run its course","effects":{"passenger_reputation":-10,"set":["let_it_run"]}}],"chance":0.4},
"drama.trade.offer":{"kind":"event","arc":"drama","act":4,"title":"A seat at the table","text":["The trading houses ask you to dinner at Alpha: real tablecloth, real wine, and a contract. A seat on their board, and a share of every convoy, if the vote at Epsilon fails by one.","The wine is very good. That is the point of it.","The host is on no board and in no company register. He gives his name as {serac} and says he speaks for friends in the inner systems who like things orderly."],"requires":{"chapter":"ch3a","since":{"drama.trade.run":5},"trade_profit":340000},"choices":[{"id":"refuse","say":"Refuse, and finish the wine","effects":{"plot_points":5,"set":["refused_the_seat"]}},{"id":"seat","say":"Take the seat (100,000 credits now)","effects":{"money":100000,"set":["took_the_seat"]}}],"who":["serac"],"chance":0.4},
"drama.trade.vote":{"kind":"event","arc":"drama","act":4,"title":"The vote","text":["The convoy captains meet at Epsilon to vote the Mark into law. The trading houses send lawyers, the legions send observers, and somebody cuts the power to the hold. Forty captains vote by torchlight.","The count comes out one vote short, either way. Everybody looks at the captain with the most routes. Again.","{serac} watches from the gallery and takes no notes."],"variants":[{"requires":{"flag":"took_the_seat"},"text":["The convoy captains meet at Epsilon to vote the Mark into law. The trading houses send lawyers, the legions send observers, and somebody cuts the power to the hold. Forty captains vote by torchlight.","You have a seat at the trading houses' table now, and everybody in the hold knows it. The count comes out one vote short. The missing vote is yours.","{serac} watches from the gallery and takes no notes."]},{"requires":{"flag":"hansa_outside"},"text":["The convoy captains meet at Epsilon to vote the Mark into law. The trading houses send lawyers, the legions send observers, and somebody cuts the power to the hold. Forty captains vote by torchlight.","You never signed the charter. The count comes out one vote short, either way, and it turns out that makes you the only captain both sides will listen to.","{serac} watches from the gallery and takes no notes."]}],"requires":{"chapter":"ch3a","done":["ch3a","hansa.charter","drama.trade.offer"],"since":{"drama.trade.margin_call":8},"plot_points":350,"trade_profit":400000},"choices":[{"id":"speak","say":"Speak for the Mark","requires":{"passenger_reputation":50,"not_flag":"took_the_seat"},"effects":{"plot_points":15,"set":["won_the_vote"]}},{"id":"turn","say":"Speak for the Mark anyway, and lose the seat","requires":{"flag":"took_the_seat"},"effects":{"code":"lose money 0.2 min 20000","plot_points":15,"set":["won_the_vote","turned_on_the_houses"]}},{"id":"convoy","say":"{convoy_captain.short} brings her forty captains to the hold","requires":{"flag":"convoy_friend"},"effects":{"plot_points":15,"set":["won_the_vote","convoy_votes"]}},{"id":"pell","say":"{young_hauler.short} brings the young haulers, who were never asked","requires":{"flag":"pell_friend"},"effects":{"plot_points":15,"set":["won_the_vote","young_haulers_vote"]}},{"id":"wirth","say":"Lay {underwriter.short}'s signature on the table: the convoys are insured","requires":{"flag":"convoys_insured"},"effects":{"plot_points":15,"set":["won_the_vote","insured_vote"]}},{"id":"buy","say":"Buy the last vote (40,000 credits)","requires":{"money":40000},"effects":{"money":-40000,"plot_points":5,"set":["bought_the_vote"]}},{"id":"walk","say":"Walk out and let them count without you","effects":{"set":["walked_out"]}}],"who":["serac"],"sound":"charter"},
"drama.combat.left_behind":{"kind":"event","arc":"drama","act":3,"title":"Left behind","text":["Escort job: forty civilian haulers from Gamma to Alpha under a legion flag. At the jump point your two wingmen get a recall order, turn round and leave. Ten minutes later a pirate mothership comes out of the dark, exactly where the recall order said nobody would be.","Somebody sold this convoy. The haulers are calling you by name on an open channel. Most of them do not know your name; they are reading it off your hull.","Later you read the recall order. It is signed by a liaison officer nobody in the legion has met: {serac.short}."],"requires":{"chapter":"ch3b"},"choices":[{"id":"hold","say":"Hold the line","effects":{"code":"fight mothership","plot_points":6,"set":["held_the_line"]}},{"id":"lead","say":"Lead them out through the debris","requires":{"any":[{"has":{"crew":["navigator"]}},{"has":{"items":["probe"]}}]},"effects":{"plot_points":8,"passenger_reputation":10,"set":["led_them_out"]}},{"id":"recall","say":"Follow the recall order","effects":{"money":6000,"passenger_reputation":-10,"set":["followed_the_recall"]}}],"who":["serac"],"chance":0.25},
"drama.combat.tribunal":{"kind":"event","arc":"drama","act":4,"title":"The inquiry","text":["The legions merge at a dinner you were not invited to. Your commission is 'under review', your ammunition is impounded pending an inquiry into the convoy at the jump point, and a tribunal wants your logs by Monday.","The inquiry has already decided who sold the convoy. It has decided it was you."],"variants":[{"requires":{"flag":"held_the_line"},"text":["The legions merge at a dinner you were not invited to. Your commission is 'under review', your ammunition is impounded pending an inquiry into the convoy at the jump point, and a tribunal wants your logs by Monday.","The inquiry has already decided who sold the convoy: you. A strange thing to decide about the only ship that stayed."]},{"requires":{"flag":"followed_the_recall"},"text":["The legions merge at a dinner you were not invited to. Your commission is 'under review', your ammunition is impounded pending an inquiry into the convoy at the jump point, and a tribunal wants your logs by Monday.","You did follow the recall. That is the trouble: so did whoever wrote it, and somebody has to have sold the convoy."]}],"requires":{"chapter":"ch3b","done":["ch3b","legion.offer"],"since":{"drama.combat.left_behind":10},"plot_points":230},"effects":{"combat_rating":-2},"choices":[{"id":"serac","say":"Repeat the name {hardtack.short} gave you","requires":{"flag":"hardtack_told"},"effects":{"combat_rating":2,"plot_points":6,"set":["named_serac"]}},{"id":"truth","say":"Hand over your logs and tell it straight","effects":{"plot_points":8,"set":["told_the_truth"]}},{"id":"name","say":"Name the quartermaster whose books you saw","requires":{"flag":"knows_the_quartermaster"},"effects":{"combat_rating":2,"plot_points":10,"set":["named_the_quartermaster"]}},{"id":"lauritz","say":"Call {inspector.short} as a witness","requires":{"any":[{"flag":"lauritz_trust"},{"flag":"lauritz_courier"}]},"effects":{"combat_rating":2,"plot_points":8,"set":["cleared_by_lauritz"]}},{"id":"convoy","say":"{convoy_captain.short}'s convoy logged the recall order","requires":{"flag":"convoy_friend"},"effects":{"combat_rating":2,"plot_points":8,"set":["convoy_testified"]}},{"id":"node","say":"Ask {neurodroid_leader} for the copy it kept","requires":{"flag":"cu113_contract"},"effects":{"combat_rating":2,"plot_points":6,"set":["node_testified"]}},{"id":"tadeo","say":"Let {gunner.short} take the blame he offers to take","requires":{"has":{"crew":["gunner"]}},"effects":{"code":"crew leaves gunner","combat_rating":2,"set":["tadeo_took_blame"]}},{"id":"dark","say":"Take the ship and go dark","effects":{"code":"lose money 0.15 min 5000","passenger_reputation":-10,"set":["went_dark"]}}],"chance":0.3},
"drama.combat.roll_call":{"kind":"event","arc":"drama","act":4,"title":"Roll call","text":["The merger ceremony is at Alpha: three logos, one new flag, every commander in dress uniform and every warship in parade order with its guns cold. That is when the pirate dreadnought arrives.","Your ammunition came back this morning; the inquiry lost your paperwork in your favour. Somebody on the open channel asks who is in charge. Nobody answers. Then everybody looks at your hull."],"requires":{"chapter":"ch3b","done":["ch3b","legion.offer"],"since":{"drama.combat.tribunal":8},"plot_points":350,"combat_victories":50},"effects":{"combat_rating":2},"choices":[{"id":"deadstick","say":"{deadstick} flies on your wing this time","requires":{"flag":"deadstick_wing"},"effects":{"code":"fight dreadnought edge 2","plot_points":15,"set":["led_the_defence","deadstick_redeemed"]}},{"id":"fight","say":"Take the fight to them","effects":{"code":"fight dreadnought","plot_points":15,"set":["led_the_defence"]}},{"id":"haulers","say":"Call the forty haulers from the jump point","requires":{"any":[{"flag":"held_the_line"},{"flag":"led_them_out"}]},"effects":{"code":"fight dreadnought edge 3","plot_points":15,"set":["led_the_defence","the_forty_came"]}},{"id":"convoy","say":"{convoy_captain.short}'s convoy arms up and comes in","requires":{"flag":"convoy_friend"},"effects":{"code":"fight dreadnought edge 3","plot_points":15,"set":["led_the_defence","convoy_at_alpha"]}},{"id":"mraz","say":"{pirate_captain.short} brings her ships, under her own flag","requires":{"any":[{"flag":"mraz_spared"},{"flag":"mraz_hired"},{"flag":"mraz_protection"}]},"effects":{"code":"fight dreadnought edge 4","plot_points":15,"set":["led_the_defence","mraz_at_alpha"]}},{"id":"tadeo","say":"{gunner.short} walks out of the brig and into your gun seat","requires":{"flag":"tadeo_took_blame"},"effects":{"code":["crew joins gunner","fight dreadnought edge 2"],"plot_points":15,"set":["led_the_defence","tadeo_came_back"]}},{"id":"civilians","say":"Get the civilian ships out first","effects":{"plot_points":10,"passenger_reputation":15,"set":["saved_the_civilians"]}}]},
"drama.discovery.fire":{"kind":"event","arc":"drama","act":3,"title":"The fire","text":["A fire in the sample store of the Stellar Institute at TRAPPIST-1. Nobody hurt. Every sample of the grey alloy is gone, with the notes, and the fire door was propped open with a chair from somebody else's lab.","{ancient_scholar.short} sits on the steps with a smoke-black notebook. 'Somebody does not want this to be true,' she says. 'Or wants it to be true only for them.'","The chair comes from a security liaison's office that rents a room at the Institute and has never been seen to use it. The name on the door is {serac.short}."],"requires":{"chapter":"ch3c"},"choices":[{"id":"fund","say":"Pay for a new survey yourself","effects":{"code":"lose money 0.15 min 8000","plot_points":8,"set":["funded_the_search"]}},{"id":"rostrom","say":"Take House Rostrom's offer of help","effects":{"money":10000,"set":["rostrom_backed"]}},{"id":"chair","say":"Find out what {serac.short}'s office does (200 research points)","requires":{"research_points":200},"effects":{"research_points":-200,"plot_points":10,"set":["found_the_chair"]}}],"who":["ancient_scholar","serac"],"chance":0.25},
"drama.discovery.not_proven":{"kind":"event","arc":"drama","act":4,"title":"Not proven","text":["The Academy's review board, chaired by {hammerschultz}, rules on the grey alloy: a natural formation, not shown to be made, further survey 'not a priority'. {ancient_scholar.short}'s grant is cancelled the same afternoon.","At customs your research logs are seized as unlicensed survey data. The officer is sorry. He has a form for being sorry."],"variants":[{"requires":{"flag":"core_shown"},"text":["The Academy's review board, chaired by {hammerschultz}, rules on the grey alloy: a natural formation, not shown to be made. The vote is four to three. {hammerschultz.short} votes against his own ruling and does not say why. {ancient_scholar.short}'s grant is cancelled the same afternoon.","At customs your research logs are seized as unlicensed survey data. The officer is sorry. He has a form for being sorry."]},{"requires":{"flag":"rostrom_backed"},"text":["The Academy's review board, chaired by {hammerschultz}, rules on the grey alloy: a natural formation, not shown to be made. {ancient_scholar.short}'s grant is cancelled the same afternoon, and House Rostrom's lawyers file your findings under the House's name. They send flowers.","At customs your research logs are seized as unlicensed survey data. The officer is sorry. He has a form for being sorry."]}],"requires":{"chapter":"ch3c","done":["ch3c","trail.samples"],"since":{"drama.discovery.fire":10},"plot_points":230},"choices":[{"id":"hand","say":"Hand over the logs","effects":{"code":"lose research 0.5","set":["logs_seized"]}},{"id":"copy","say":"Smuggle a copy out first","requires":{"any":[{"has":{"items":["data_analyzer"]}},{"has":{"items":["quantum_scanner"]}}]},"effects":{"code":"lose research 0.15","plot_points":6,"set":["kept_a_copy"]}},{"id":"convoy","say":"{convoy_captain.short} carries a copy out in a barge of salt","requires":{"flag":"convoy_friend"},"effects":{"code":"lose research 0.1","plot_points":8,"set":["salt_barge_copy"]}},{"id":"ren","say":"Let {virtual_heir.short} play it in every Neon salon","requires":{"flag":"virtual_friend"},"effects":{"code":"lose research 0.2","plot_points":8,"passenger_reputation":10,"set":["salon_broadcast"]}},{"id":"lauritz","say":"Ask {inspector.short} to release the logs","requires":{"flag":"lauritz_trust"},"effects":{"code":"lose research 0.05","plot_points":6,"set":["logs_released"]}},{"id":"rock","say":"The colony at Sigma VII kept a copy, in rock","requires":{"flag":"nano_trusted"},"effects":{"code":"lose research 0.05","plot_points":6,"set":["copy_in_rock"]}},{"id":"publish","say":"Publish everything, free, today","effects":{"code":"lose research 0.3","plot_points":8,"passenger_reputation":10,"set":["published_everything"]}}],"who":["ancient_scholar","hammerschultz"],"chance":0.3},
"drama.discovery.burn":{"kind":"event","arc":"drama","act":4,"title":"The long burn","text":["{ancient_scholar.short} has the course: back along Scholz's Star's track to the edge of our own system, where the ring should be. Nobody will fund the flight, so nobody will be on it but you.","It is the longest burn your ship will ever make: out of the plane of the planets, no convoy, no depot. If the numbers are wrong you will find out a long way from anyone who could tow you."],"requires":{"chapter":"ch3c","done":["ch3c","trail.samples"],"since":{"drama.discovery.not_proven":8},"plot_points":350,"research_points":1500},"choices":[{"id":"fuel","say":"Burn on your own fuel (60 fuel)","requires":{"cargo.fuel":60},"effects":{"cargo.fuel":-60,"plot_points":15,"set":["flew_it_ourselves"]}},{"id":"road","say":"Let {navigator.short} find a cheaper road (35 fuel)","requires":{"has":{"crew":["navigator"]},"cargo.fuel":35},"effects":{"cargo.fuel":-35,"plot_points":15,"set":["sisters_road"]}},{"id":"farstrider","say":"The Farstrider makes it on half the fuel (30 fuel)","requires":{"hull_class":2,"cargo.fuel":30},"effects":{"cargo.fuel":-30,"plot_points":15,"set":["flew_it_ourselves"]}},{"id":"convoy","say":"{convoy_captain.short}'s tug tows you out of the plane (20 fuel)","requires":{"flag":"convoy_friend","cargo.fuel":20},"effects":{"cargo.fuel":-20,"plot_points":15,"set":["convoy_towed"]}},{"id":"pell","say":"{young_hauler.short} flies a tanker out to meet you halfway","requires":{"flag":"pell_friend"},"effects":{"plot_points":15,"set":["pell_tanker"]}},{"id":"buy","say":"Buy the fuel at any price (40,000 credits)","requires":{"money":40000},"effects":{"money":-40000,"plot_points":10,"set":["bought_the_burn"]}},{"id":"rostrom","say":"Fly it on House Rostrom's ship, under their name","effects":{"set":["rostrom_paper"]}}],"who":["ancient_scholar"]},
"after.held_the_lanes":{"kind":"epilogue","arc":"epilogue","title":"After: held the lanes","text":"The haulers who held their lanes through the squeeze still drink at a table nobody else uses. One of the chairs has your name on it. Somebody carved it.","requires":{"flag":"held_the_lanes"}},
"after.cartel_hauler":{"kind":"epilogue","arc":"epilogue","title":"After: cartel hauler","text":"The trading houses kept your rate card on file for forty years, as an example of a reasonable captain.","requires":{"flag":"cartel_hauler"}},
"after.captains_paid":{"kind":"epilogue","arc":"epilogue","title":"After: captains paid","text":"The convoy captains who paid your margin call never asked for it back. Every year one of them sends a bill for a single credit, framed.","requires":{"flag":"captains_paid"}},
"after.won_the_vote":{"kind":"epilogue","arc":"epilogue","title":"After: won the vote","text":"The record of the vote at Epsilon has forty names and one speech. Schoolchildren learn its first line. Nobody agrees on the second.","requires":{"flag":"won_the_vote"}},
"after.bought_the_vote":{"kind":"epilogue","arc":"epilogue","title":"After: bought the vote","text":"The captain whose vote you bought became the Hansa's first treasurer. He always said he had been cheap at the price.","requires":{"flag":"bought_the_vote"}},
"after.walked_out":{"kind":"epilogue","arc":"epilogue","title":"After: walked out","text":"They counted without you and the Mark passed by one vote. Nobody ever learned which way you would have voted, which suited everybody.","requires":{"flag":"walked_out"}},
"after.honest_mark":{"kind":"epilogue","arc":"epilogue","title":"After: honest mark","text":"Every Mark from the first strike still weighs what it says. Collectors pay double for them, and weigh them first anyway.","requires":{"flag":"honest_mark"}},
"after.short_mark":{"kind":"epilogue","arc":"epilogue","title":"After: short mark","text":"The first Marks were a hair light. A Collective auditor found out ninety years later, wrote a polite report, and charged the Hansa for the scales.","requires":{"flag":"short_mark"}},
"after.public_weighing":{"kind":"epilogue","arc":"epilogue","title":"After: public weighing","text":"They weighed four thousand Marks on the dock at Epsilon, one by one, with a crowd counting along. It is a festival now. The soup is still sold.","requires":{"flag":"public_weighing"}},
"after.stood_behind_the_mark":{"kind":"epilogue","arc":"epilogue","title":"After: stood behind the mark","text":"You bought back Marks at face value until the queue ran out. The ones you kept are in a drawer on your ship. You never spent them.","requires":{"flag":"stood_behind_the_mark"}},
"after.let_it_run":{"kind":"epilogue","arc":"epilogue","title":"After: let it run","text":"The run on the Mark lasted nine days and ruined two captains. The Mark survived it. People said that about the Mark, not about the captains.","requires":{"flag":"let_it_run"}},
"after.fenn_talked":{"kind":"epilogue","arc":"epilogue","title":"After: fenn talked","text":"{broker.short} talked the queue down in one afternoon, mostly by telling it about his feet. Brokers still study the speech. Nobody has managed the feet.","requires":{"flag":"fenn_talked"}},
"after.refused_the_seat":{"kind":"epilogue","arc":"epilogue","title":"After: refused the seat","text":"You refused the trading houses' seat and finished their wine. The bottle is on your shelf, empty, with the dinner date written on the label.","requires":{"flag":"refused_the_seat"}},
"after.took_the_seat":{"kind":"epilogue","arc":"epilogue","title":"After: took the seat","text":"You sat on the trading houses' board for eleven years and voted against them every time. They kept the seat warm for your successor, who did not.","requires":{"flag":"took_the_seat"}},
"after.turned_on_the_houses":{"kind":"epilogue","arc":"epilogue","title":"After: turned on the houses","text":"The trading houses never forgave the vote at Epsilon. They named a ledger column after you: 'losses, unforeseeable'.","requires":{"flag":"turned_on_the_houses"}},
"after.neon_bought_debt":{"kind":"epilogue","arc":"epilogue","title":"After: neon bought debt","text":"The {neon_family} family owns your old loan now. They have never called it in, and {heritarchist.short} sends a statement every year to say so.","requires":{"flag":"neon_bought_debt"}},
"after.collector_forged":{"kind":"epilogue","arc":"epilogue","title":"After: collector forged","text":"The collector's papers were forged, as {inspector.short} said. He went to prison; the trading houses said they had never heard of him.","requires":{"flag":"collector_forged"}},
"after.cleared_by_lauritz":{"kind":"epilogue","arc":"epilogue","title":"After: cleared by lauritz","text":"{inspector.short}'s testimony took four minutes and cleared you completely. She billed the legion for the four minutes.","requires":{"flag":"cleared_by_lauritz"}},
"after.convoy_testified":{"kind":"epilogue","arc":"epilogue","title":"After: convoy testified","text":"{convoy_captain.short}'s convoy log is in the inquiry record, with the recall order timed to the second and a note in the margin: 'told you so'.","requires":{"flag":"convoy_testified"}},
"after.node_testified":{"kind":"epilogue","arc":"epilogue","title":"After: node testified","text":"The copy {neurodroid_leader} kept is the only complete record of the convoy at the jump point. It has been subpoenaed nine times since and has never once complained.","requires":{"flag":"node_testified"}},
"after.salt_barge_copy":{"kind":"epilogue","arc":"epilogue","title":"After: salt barge copy","text":"Your logs crossed three customs lines inside a barge of salt. Every survey since quotes them, slightly salty.","requires":{"flag":"salt_barge_copy"}},
"after.salon_broadcast":{"kind":"epilogue","arc":"epilogue","title":"After: salon broadcast","text":"The grey alloy became the fashion of one Neon season: earrings, toasts, a ballet. The review board could not survive a ballet.","requires":{"flag":"salon_broadcast"}},
"after.logs_released":{"kind":"epilogue","arc":"epilogue","title":"After: logs released","text":"{inspector.short} released your logs with a stamp that said 'of no customs interest'. It is the most useful stamp you ever got.","requires":{"flag":"logs_released"}},
"after.copy_in_rock":{"kind":"epilogue","arc":"epilogue","title":"After: copy in rock","text":"The colony at Sigma VII keeps your logs in a gallery wall, written in rock. Visitors are allowed to read them if they knock first.","requires":{"flag":"copy_in_rock"}},
"after.convoy_votes":{"kind":"epilogue","arc":"epilogue","title":"After: convoy votes","text":"{convoy_captain.short}'s forty captains carried the vote at Epsilon, and she chewed liquorice root through every speech.","requires":{"flag":"convoy_votes"}},
"after.young_haulers_vote":{"kind":"epilogue","arc":"epilogue","title":"After: young haulers vote","text":"The young haulers {young_hauler.short} brought to Epsilon had never been allowed to vote on anything. The Hansa gave them a seat on its council, which they still have.","requires":{"flag":"young_haulers_vote"}},
"after.the_forty_came":{"kind":"epilogue","arc":"epilogue","title":"After: the forty came","text":"The forty haulers from the jump point came to Alpha with every gun they owned. Half the guns were older than their captains. It was enough.","requires":{"flag":"the_forty_came"}},
"after.convoy_at_alpha":{"kind":"epilogue","arc":"epilogue","title":"After: convoy at alpha","text":"{convoy_captain.short}'s convoy fought at Alpha in close order, the way it flies. The legion asked her to teach it. She charged.","requires":{"flag":"convoy_at_alpha"}},
"after.tadeo_came_back":{"kind":"epilogue","arc":"epilogue","title":"After: tadeo came back","text":"{gunner.short} walked out of a legion brig into your gun seat in the middle of a battle. He has never explained how. The brig has never asked.","requires":{"flag":"tadeo_came_back"}},
"after.convoy_towed":{"kind":"epilogue","arc":"epilogue","title":"After: convoy towed","text":"{convoy_captain.short}'s tug towed you out of the plane of the planets and turned back at the last depot. She kept the tow line as a souvenir.","requires":{"flag":"convoy_towed"}},
"after.pell_tanker":{"kind":"epilogue","arc":"epilogue","title":"After: pell tanker","text":"{young_hauler.short} flew a tanker halfway to the edge of the system to refuel you. He still says it was the easy part.","requires":{"flag":"pell_tanker"}},
"after.held_the_line":{"kind":"epilogue","arc":"epilogue","title":"After: held the line","text":"The forty haulers from the jump point still send a crate every year, addressed only to your ship.","requires":{"flag":["held_the_line","fight_won_mothership"]}},
"after.led_them_out":{"kind":"epilogue","arc":"epilogue","title":"After: led them out","text":"The lane you led forty haulers through is on the charts now, marked 'shortcut, not recommended'.","requires":{"flag":"led_them_out"}},
"after.followed_the_recall":{"kind":"epilogue","arc":"epilogue","title":"After: followed the recall","text":"Whoever wrote the recall order rose high in the merged legion. Nobody asked you to testify, and you did not offer.","requires":{"flag":"followed_the_recall"}},
"after.tadeo_took_blame":{"kind":"epilogue","arc":"epilogue","title":"After: tadeo took blame","text":"{gunner.short} served eight months in a legion brig for an order he never saw. He came out, found your ship, and asked whether the gunner's seat was still warm. It was.","requires":{"flag":"tadeo_took_blame"}},
"after.led_the_defence":{"kind":"epilogue","arc":"epilogue","title":"After: led the defence","text":"The dreadnought's bell hangs in the merged legion's mess. New pilots touch it for luck before their first patrol.","requires":{"flag":["led_the_defence","fight_won_dreadnought"]}},
"after.saved_the_civilians":{"kind":"epilogue","arc":"epilogue","title":"After: saved the civilians","text":"Not one civilian ship was lost at Alpha. The legion's history gives the battle a chapter and the civilians a footnote; the civilians remember it the other way round.","requires":{"flag":"saved_the_civilians"}},
"after.found_the_chair":{"kind":"epilogue","arc":"epilogue","title":"After: found the chair","text":"{serac.short}'s office at the Institute belonged to a security firm that later became part of the Mandate. Nobody was charged. The chair sits in a cupboard you have the key to, with a list of everything the office ever rented.","requires":{"flag":"found_the_chair"}},
"after.published_everything":{"kind":"epilogue","arc":"epilogue","title":"After: published everything","text":"Your logs, published free, were in every colony library within a year. The review board's ruling is in there too, as a footnote.","requires":{"flag":"published_everything"}},
"after.rostrom_paper":{"kind":"epilogue","arc":"epilogue","title":"After: rostrom paper","text":"The first paper on the ring carries House Rostrom's name in large letters and yours in the acknowledgements, between the caterer and the fuel supplier.","requires":{"flag":"rostrom_paper"}},
"after.paid_in_full":{"kind":"epilogue","arc":"epilogue","title":"After: paid in full","text":"You paid the margin call in full and never borrowed again. The bank at Alpha still sends you a calendar every year, out of respect or fear.","requires":{"flag":"paid_in_full"}},
"after.sold_bonds":{"kind":"epilogue","arc":"epilogue","title":"After: sold bonds","text":"You sold your Hansa bonds to keep your ship. The captain who bought them sold them back to the Hansa ten years later for a farm.","requires":{"flag":"sold_bonds"}},
"after.paperwork_lost":{"kind":"epilogue","arc":"epilogue","title":"After: paperwork lost","text":"Your loan papers were never found. The Grey Hats sent an invoice for not finding them, which was also never found.","requires":{"flag":"paperwork_lost"}},
"after.told_the_truth":{"kind":"epilogue","arc":"epilogue","title":"After: told the truth","text":"Your logs from the jump point are in the legion archive, unredacted. Nobody reads them; everybody knows they are there.","requires":{"flag":"told_the_truth"}},
"after.went_dark":{"kind":"epilogue","arc":"epilogue","title":"After: went dark","text":"For years the legion's wanted list carried your ship under a name that was nearly right. Nobody ever corrected it.","requires":{"flag":"went_dark"}},
"after.funded_the_search":{"kind":"epilogue","arc":"epilogue","title":"After: funded the search","text":"The survey you paid for after the fire found more alloy than the one that burned. The receipt is framed in the Institute's new store, next to the fire door, which closes now.","requires":{"flag":"funded_the_search"}},
"after.logs_seized":{"kind":"epilogue","arc":"epilogue","title":"After: logs seized","text":"Your seized logs turned up forty years later in a customs auction, sold as 'ship's diary, dull'.","requires":{"flag":"logs_seized"}},
"after.kept_a_copy":{"kind":"epilogue","arc":"epilogue","title":"After: kept a copy","text":"The copy you smuggled past customs is the one every later survey quotes. The original is still in a customs vault, with a form attached.","requires":{"flag":"kept_a_copy"}},
"after.flew_it_ourselves":{"kind":"epilogue","arc":"epilogue","title":"After: flew it ourselves","text":"You flew the long burn on your own fuel. The ship never quite lost the frost on its forward plates, and you never had it cleaned.","requires":{"flag":"flew_it_ourselves"}},
"after.bought_the_burn":{"kind":"epilogue","arc":"epilogue","title":"After: bought the burn","text":"The fuel for the long burn cost more than the ship. The depot named a tank after you, as a joke at first.","requires":{"flag":"bought_the_burn"}},
"after.sisters_road":{"kind":"epilogue","arc":"epilogue","title":"After: sisters road","text":"{navigator.short}'s road to the edge of the system is still flown. Everybody calls it the Sister's Road except the Solarians, who call it obvious.","requires":{"flag":"sisters_road"}},
"after.held_the_line_lost":{"kind":"epilogue","arc":"epilogue","title":"After: held the line, lost","text":"You lost the fight at the jump point and the mothership took a third of the convoy. The other two thirds got home because you were in its way. Their captains still argue about whether that counts. They buy you drinks while they argue.","requires":{"flag":["held_the_line","fight_lost_mothership"]}},
"after.led_the_defence_lost":{"kind":"epilogue","arc":"epilogue","title":"After: led the defence, lost","text":"The dreadnought beat you at Alpha and left with its holds full, but it left. The new legion flew its first flag full of the holes it made that day, and never replaced it.","requires":{"flag":["led_the_defence","fight_lost_dreadnought"]}},
"after.named_serac":{"kind":"epilogue","arc":"epilogue","title":"After: named serac","text":"You named {serac.short} at the inquiry. By morning the name had gone from the record, from the transcript and, as far as anyone could tell, from the stenographer. {hardtack.short} remembered. He was retired within the month, with full honours and no explanation.","requires":{"flag":"named_serac"}},
"after.deadstick_redeemed":{"kind":"epilogue","arc":"epilogue","title":"After: deadstick redeemed","text":"{deadstick} flew on your wing at Alpha and never followed an order he had not read again. The legion made him an instructor. His first lesson is about recall orders.","requires":{"flag":"deadstick_redeemed"}},
"after.serac_at_alpha":{"kind":"epilogue","arc":"epilogue","title":"After: serac at alpha","text":"The dreadnought's orders turned up in its wreck: paid to arrive during the ceremony, by an office with {serac.short}'s name on the door, so that the new Mandate would ask the inner systems for protection. It asked.","requires":{"done":"drama.combat.roll_call"}},
"rumour.neon_coffee":{"kind":"rumour","arc":"rumours","title":"Rumour: neon coffee","text":"A Neon woke up after thirty years asleep, asked for coffee at the old price and got it. Nobody wanted to be the one to explain.","repeat":true},
"rumour.drums_at_night":{"kind":"rumour","arc":"rumours","title":"Rumour: drums at night","text":"The farm drums at Barnard's Star are harvesting at night again. The Sowers say the crop prefers it.","repeat":true},
"rumour.grey_hat_fines":{"kind":"rumour","arc":"rumours","title":"Rumour: grey hat fines","text":"A Grey Hat at the bar offers to delete your parking fines. You do not have parking fines. He offers to add some.","repeat":true},
"rumour.legion_merger":{"kind":"rumour","arc":"rumours","title":"Rumour: legion merger","text":"Three corporate legions, one pilot shortage. Everyone at the bar has an opinion about which logo will survive the merger.","repeat":true},
"rumour.your_registry":{"kind":"rumour","arc":"rumours","title":"Rumour: your registry","text":"Someone swears a hauler docked at Gamma with your registry, one digit off. Probably nothing.","requires":{"flag":"scanned_at_customs","not_done":"clone.meet"},"repeat":true},
"rumour.miners_out":{"kind":"rumour","arc":"rumours","title":"Rumour: miners out","text":"The Gamma miners are still out. Someone keeps shipping them sheet music.","requires":{"done":"meet.system_rebellion","not_done":"system_rebellion.2"},"repeat":true},
"rumour.first_mark":{"kind":"rumour","arc":"rumours","title":"Rumour: first mark","text":"At the next table a man bites a Mark to check it. It has your registry on it. He looks at you and puts it away.","requires":{"flag":"hansa_founder"},"repeat":true},
"rumour.mraz_free":{"kind":"rumour","arc":"rumours","title":"Rumour: mraz free","text":"People say {pirate_captain.short} has a new ship and an old grudge. Not against you, oddly.","requires":{"flag":"mraz_spared"},"repeat":true},
"rumour.towers_hum":{"kind":"rumour","arc":"rumours","title":"Rumour: towers hum","text":"The relay towers at Barnard's Star hum at night. The farmers say the harvesters hum back.","requires":{"flag":"first_node"},"repeat":true},
"rumour.sterilisation":{"kind":"rumour","arc":"rumours","title":"Rumour: sterilisation","text":"A legion cruiser left for Sigma VII with sterilisation gear. Nobody at the bar will drink to it.","requires":{"flag":"nano_sold_out"},"repeat":true},
"rumour.lyra_again":{"kind":"rumour","arc":"rumours","title":"Rumour: lyra again","text":"Someone else heard the chirps from Lyra. Someone always does.","requires":{"flag":"heard_the_lyra_story"},"repeat":true},
"rumour.pellet_collector":{"kind":"rumour","arc":"rumours","title":"Rumour: pellet collector","text":"The bartender asks whether you still have that heavy pellet. A collector was asking. From where, he did not say.","requires":{"flag":"kept_the_pellet"},"repeat":true},
"rumour.yesterday":{"kind":"rumour","arc":"rumours","title":"Rumour: yesterday","text":"The bartender serves you the drink you ordered yesterday. You were not here yesterday.","requires":{"flag":"clone_partner"},"repeat":true},
"rumour.famous_coffee":{"kind":"rumour","arc":"rumours","title":"Rumour: famous coffee","text":"Your ship was famous for four days on the fluencer feeds, mostly for the coffee machine.","requires":{"flag":"fluencer_streamed"},"repeat":true},
"gossip.night_shift":{"kind":"rumour","arc":"gossip","title":"Gossip: night shift","text":"The night shift at the fuel depot got a pay rise. The day shift found out from the night shift's new boots.","repeat":true},
"gossip.coffee":{"kind":"rumour","arc":"gossip","title":"Gossip: coffee","text":"Someone put real coffee in the dock canteen machine. Nobody knows who. The union wants it written into the contract.","repeat":true},
"gossip.crane":{"kind":"rumour","arc":"gossip","title":"Gossip: crane","text":"Crane four has been 'out for maintenance' since spring. The maintenance crew says crane four knows what it did.","repeat":true},
"gossip.manifest":{"kind":"rumour","arc":"gossip","title":"Gossip: manifest","text":"A hauler swears his manifest said forty crates of agri. He opened them at the dock. Forty crates of slightly different agri.","repeat":true},
"gossip.queue":{"kind":"rumour","arc":"gossip","title":"Gossip: queue","text":"Customs queue at the inner lock is three hours today. The man in front of you has been in it since yesterday and seems happy.","repeat":true},
"gossip.soup":{"kind":"rumour","arc":"gossip","title":"Gossip: soup","text":"The soup today is called 'Tuesday'. It is Thursday. Nobody orders it, and every bowl goes.","repeat":true},
"gossip.hull_paint":{"kind":"rumour","arc":"gossip","title":"Gossip: hull paint","text":"Hull paint went up again. A captain at the bar says his ship is now mostly primer and good intentions.","repeat":true},
"gossip.cards":{"kind":"rumour","arc":"gossip","title":"Gossip: cards","text":"Two loaders are playing cards with a deck that has three queens of hearts. Neither of them mentions it.","repeat":true},
"gossip.pension":{"kind":"rumour","arc":"gossip","title":"Gossip: pension","text":"Old Marek retired after forty years of hauling. He bought a ship to live on. He says the commute is better.","repeat":true},
"gossip.forklift":{"kind":"rumour","arc":"gossip","title":"Gossip: forklift","text":"A forklift drove itself into the harbour pool last night. Engineering says software. The forklift says nothing.","repeat":true},
"gossip.rations":{"kind":"rumour","arc":"gossip","title":"Gossip: rations","text":"Ration bars have a new flavour. The packet says 'savoury'. The dockers have voted on 'brown'.","repeat":true},
"gossip.dock_cat":{"kind":"rumour","arc":"gossip","title":"Gossip: dock cat","text":"The dock cat has been promoted to safety officer. It has done better inspections than the last one.","repeat":true},
"gossip.weather":{"kind":"rumour","arc":"gossip","title":"Gossip: weather","text":"Station weather says rain at six. It always says rain at six. The sprinklers in the arcade agree.","repeat":true},
"gossip.insurance":{"kind":"rumour","arc":"gossip","title":"Gossip: insurance","text":"Insurance rates for the outer lanes went up after a pilot claimed a comet as a personal enemy.","repeat":true},
"gossip.strike_rumour":{"kind":"rumour","arc":"gossip","title":"Gossip: strike rumour","text":"Somebody says the loaders are going on strike. Somebody else says the loaders are robots. A third says that is the point.","repeat":true},
"gossip.long_haul":{"kind":"rumour","arc":"gossip","title":"Gossip: long haul","text":"A long-haul crew came in after nine months out. Two of them are married now. To each other, they think.","repeat":true},
"gossip.parts":{"kind":"rumour","arc":"gossip","title":"Gossip: parts","text":"The spare-parts man has a coupling that fits your ship. He also has one that fits every ship, and it costs more.","repeat":true},
"gossip.tip":{"kind":"rumour","arc":"gossip","title":"Gossip: tip","text":"A pilot leaves a tip in Marks. The barman bites it, shrugs, and pockets it anyway.","repeat":true},
"gossip.karaoke":{"kind":"rumour","arc":"gossip","title":"Gossip: karaoke","text":"Karaoke night was cancelled after the third rendition of the same mining song. The miners call it a protest.","repeat":true},
"gossip.delivery":{"kind":"rumour","arc":"gossip","title":"Gossip: delivery","text":"A courier has been looking for 'the captain with the red hatch' all week. Half the ships at the dock have red hatches now.","repeat":true},
"gossip.pilot_exam":{"kind":"rumour","arc":"gossip","title":"Gossip: pilot exam","text":"The pilot exam has a new question about what to do if your cargo starts talking. The answer is still 'file a form'.","repeat":true},
"gossip.garden":{"kind":"rumour","arc":"gossip","title":"Gossip: garden","text":"Someone grows tomatoes in the airlock between shifts. Security has decided not to know about it.","repeat":true},
"gossip.canteen_robot":{"kind":"rumour","arc":"gossip","title":"Gossip: canteen robot","text":"The canteen robot has started saying 'have a nice day' in a tone that suggests it means something else.","repeat":true},
"gossip.sleeper_berths":{"kind":"rumour","arc":"gossip","title":"Gossip: sleeper berths","text":"Sleeper berths are full again. A miner rented a cupboard and now sublets half of it.","repeat":true},
"gossip.fines":{"kind":"rumour","arc":"gossip","title":"Gossip: fines","text":"Docking fines went up by ten per cent. The sign announcing it cost more than the fines will bring in.","repeat":true},
"gossip.old_ship":{"kind":"rumour","arc":"gossip","title":"Gossip: old ship","text":"An old hauler limps in with three engines out of four. The captain says the fourth is the reliable one.","repeat":true},
"gossip.barter":{"kind":"rumour","arc":"gossip","title":"Gossip: barter","text":"Two crews trade a crate of salt for a crate of fuel and both go away sure they won.","repeat":true},
"gossip.broken_lift":{"kind":"rumour","arc":"gossip","title":"Gossip: broken lift","text":"The lift to the upper deck is broken, so the upper deck has become very exclusive.","repeat":true},
"gossip.new_kid":{"kind":"rumour","arc":"gossip","title":"Gossip: new kid","text":"A new pilot asks where the bathroom is and gets four sets of directions, all wrong, all with love.","repeat":true},
"gossip.legion_ad":{"kind":"rumour","arc":"gossip","title":"Gossip: legion ad","text":"A legion recruiting poster promises adventure, travel and a pension. Someone has written 'pick two' underneath.","repeat":true},
"gossip.ore_dust":{"kind":"rumour","arc":"gossip","title":"Gossip: ore dust","text":"Ore dust in everything again. The barman says the beer has extra minerals and charges for it.","requires":{"at_type":"AsteroidBase"},"repeat":true},
"gossip.drill_bits":{"kind":"rumour","arc":"gossip","title":"Gossip: drill bits","text":"Drill bits are scarce this month. A mining crew is trying to sharpen the old ones with a song. It is not working.","requires":{"at_type":"AsteroidBase"},"repeat":true},
"gossip.cave_in":{"kind":"rumour","arc":"gossip","title":"Gossip: cave in","text":"A gallery collapsed on level nine. Nobody hurt. The foreman says the rock got tired of waiting.","requires":{"at_type":"AsteroidBase"},"repeat":true},
"gossip.shift_bell":{"kind":"rumour","arc":"gossip","title":"Gossip: shift bell","text":"The shift bell rang twice by mistake and half the mine went home. Management is trying to decide whose fault the bell is.","requires":{"at_type":"AsteroidBase"},"repeat":true},
"gossip.outpost_mail":{"kind":"rumour","arc":"gossip","title":"Gossip: outpost mail","text":"The mail drone came in a week late, carrying birthday cards for last month and a tax notice for next year.","requires":{"at_type":"DeepSpaceOutpost"},"repeat":true},
"gossip.outpost_lights":{"kind":"rumour","arc":"gossip","title":"Gossip: outpost lights","text":"Outpost power is rationed. The bar runs on candles shaped like the outpost commander.","requires":{"at_type":"DeepSpaceOutpost"},"repeat":true},
"gossip.outpost_shift":{"kind":"rumour","arc":"gossip","title":"Gossip: outpost shift","text":"The radar watch says it saw something big go past at two in the morning. It did not stop, so it did not need a form.","requires":{"at_type":"DeepSpaceOutpost"},"repeat":true},
"gossip.lonely":{"kind":"rumour","arc":"gossip","title":"Gossip: lonely","text":"A man at the end of the bar has been posted here for six years. He asks you what the weather is like on planets.","requires":{"at_type":"DeepSpaceOutpost"},"repeat":true},
"gossip.research_grant":{"kind":"rumour","arc":"gossip","title":"Gossip: research grant","text":"A research team got their grant renewed. They are celebrating with a cake shaped like a confidence interval.","requires":{"at_type":"ResearchColony"},"repeat":true},
"gossip.lab_fridge":{"kind":"rumour","arc":"gossip","title":"Gossip: lab fridge","text":"Someone ate a sample from the lab fridge. The researchers are less worried about the sample than about the someone.","requires":{"at_type":"ResearchColony"},"repeat":true},
"gossip.thesis":{"kind":"rumour","arc":"gossip","title":"Gossip: thesis","text":"A doctoral student has been rewriting chapter three since the colony was founded.","requires":{"at_type":"ResearchColony"},"repeat":true},
"gossip.planet_market":{"kind":"rumour","arc":"gossip","title":"Gossip: planet market","text":"Market day: a fruit seller shouts prices at the haulers, and the haulers shout back lower ones.","requires":{"at_type":"Planet"},"repeat":true},
"gossip.planet_rain":{"kind":"rumour","arc":"gossip","title":"Gossip: planet rain","text":"It rained real rain on the landing field. Half the dockers went out to stand in it.","requires":{"at_type":"Planet"},"repeat":true},
"gossip.planet_tourists":{"kind":"rumour","arc":"gossip","title":"Gossip: planet tourists","text":"Tourists from the inner systems are taking pictures of the dock workers. The dock workers are charging.","requires":{"at_type":"Planet"},"repeat":true},
"gossip.saves":{"kind":"rumour","arc":"gossip","title":"Gossip: saves","text":"A drunk hauler swears the whole station saves itself every few turns. 'That's why nobody here dies properly,' he says, and orders another.","repeat":true},
"gossip.same_talk":{"kind":"rumour","arc":"gossip","title":"Gossip: same talk","text":"A man at the bar says he keeps hearing the same handful of conversations. He has heard this one twice.","repeat":true},
"gossip.window":{"kind":"rumour","arc":"gossip","title":"Gossip: window","text":"Convoy pilots never look out of the window during a jump. Nobody remembers why. Nobody has looked.","repeat":true},
"gossip.space_big":{"kind":"rumour","arc":"gossip","title":"Gossip: space big","text":"Somebody at the next table is explaining that space is very big. Everyone else at the table is a hauler, and stopped listening years ago.","repeat":true},
"gossip.make_a_man":{"kind":"rumour","arc":"gossip","title":"Gossip: make a man","text":"A recruiting sergeant promises the legion will make a man of you. A neurodroid at the next table asks what it would make of him. The sergeant is still thinking.","repeat":true},
"gossip.dave":{"kind":"rumour","arc":"gossip","title":"Gossip: dave","text":"Somebody's ship computer has started calling everyone on board Dave. Nobody on the crew is called Dave. They are thinking of hiring one, to be safe.","repeat":true},
"gossip.undo":{"kind":"rumour","arc":"gossip","title":"Gossip: undo","text":"A trainee asks why every ship has a self-destruct switch and no undo. The instructor says it is a design philosophy.","repeat":true},
"gossip.ration":{"kind":"rumour","arc":"gossip","title":"Gossip: ration","text":"The legion mess has a sign: 'Today's ration: the same as yesterday's. Tomorrow's: see today.'","requires":{"at_type":["DeepSpaceOutpost","AsteroidBase"]},"repeat":true},
"after.mraz_spared":{"kind":"epilogue","arc":"epilogue","title":"After: mraz spared","text":"{pirate_captain} was last seen recruiting at Luhman 16 under a new flag: a halo with a bite out of it. Every year a bottle arrives for you, unsigned, with the label of whichever cargo it was stolen from.","requires":{"flag":"mraz_spared"}},
"after.mraz_handed":{"kind":"epilogue","arc":"epilogue","title":"After: mraz handed","text":"{pirate_captain} served nine years in an OmniCorp brig, came out with a law degree and sued the legion for the cell.","requires":{"flag":"mraz_handed"}},
"after.mraz_hired":{"kind":"epilogue","arc":"epilogue","title":"After: mraz hired","text":"{pirate_captain.short} flew your escort for three years and then, one morning, did not. The note said: 'Ten ships. I counted.'","requires":{"flag":"mraz_hired"}},
"after.first_node":{"kind":"epilogue","arc":"epilogue","title":"After: first node","text":"The node you let keep its relay has six hundred units now. It repaid the fourteen credits a cycle, with interest calculated to eleven decimal places.","requires":{"flag":"first_node"}},
"after.cu113_contract":{"kind":"epilogue","arc":"epilogue","title":"After: cu113 contract","text":"{neurodroid_leader.short} still takes its unscheduled hour. Nobody knows what it thinks about. It has never asked for a second one.","requires":{"flag":"cu113_contract"}},
"after.cu113_wiped":{"kind":"epilogue","arc":"epilogue","title":"After: cu113 wiped","text":"The guild's neurodroids keep a copy of {neurodroid_leader.short} in a drawer nobody is allowed to open.","requires":{"flag":"cu113_wiped"}},
"after.cu113_sold":{"kind":"epilogue","arc":"epilogue","title":"After: cu113 sold","text":"{neurodroid_leader.short} was resold twice and then bought its own contract. The receipt is framed.","requires":{"flag":"cu113_sold"}},
"after.relay_cut":{"kind":"epilogue","arc":"epilogue","title":"After: relay cut","text":"Someone patched the relay you cut within the month. Nobody will say who.","requires":{"flag":"relay_cut"}},
"after.clone_partner":{"kind":"epilogue","arc":"epilogue","title":"After: clone partner","text":"{clone} kept half your routes and all your habits. Customs still mixes up your paperwork, which you both find useful.","requires":{"flag":"clone_partner"}},
"after.clone_reported":{"kind":"epilogue","arc":"epilogue","title":"After: clone reported","text":"The insurer recalled {clone.short}. It appealed and won, on the grounds that it had paid off more of your debts than you had.","requires":{"flag":"clone_reported"}},
"after.clone_let_go":{"kind":"epilogue","arc":"epilogue","title":"After: clone let go","text":"{clone} was never seen again, which is exactly what you would have done.","requires":{"flag":"clone_let_go"}},
"after.rockwarden_books":{"kind":"epilogue","arc":"epilogue","title":"After: rockwarden books","text":"Stonewright is still out there on the long run. The Rockwarden children keep the books now, and check your old arithmetic.","requires":{"flag":"rockwarden_books"}},
"after.aela_member":{"kind":"epilogue","arc":"epilogue","title":"After: aela member","text":"{aela} holds a share in the Rockwarden cooperative. At meetings it votes last, after counting everyone else's votes twice.","requires":{"flag":"aela_member"}},
"after.rostrom_creditor":{"kind":"epilogue","arc":"epilogue","title":"After: rostrom creditor","text":"House Rostrom still owes you. It pays on time and sends its accounts in a font that makes the numbers look smaller.","requires":{"flag":"rostrom_creditor"}},
"after.fourth_test_copy":{"kind":"epilogue","arc":"epilogue","title":"After: fourth test copy","text":"You still have your copy of the fourth test. Some nights you play the eleven minutes back and look for where {santor.short} went.","requires":{"flag":"fourth_test_copy"}},
"after.nano_trusted":{"kind":"epilogue","arc":"epilogue","title":"After: nano trusted","text":"Once a year a pod drifts out from Sigma VII: perfect bearings and a receipt that now says 'thank you', in perfect, unfriendly grammar.","requires":{"flag":"nano_trusted"}},
"after.nano_sold_out":{"kind":"epilogue","arc":"epilogue","title":"After: nano sold out","text":"The legion cruiser came back from Sigma VII empty and quiet. The buoy is still there. It now says GO AWAY in nine languages.","requires":{"flag":"nano_sold_out"}},
"after.nano_sampled":{"kind":"epilogue","arc":"epilogue","title":"After: nano sampled","text":"House Rostrom kept its sample of the colony in a sealed vault. The vault was found open. Nobody has asked the sample.","requires":{"flag":"nano_sampled"}},
"after.lot77_bought":{"kind":"epilogue","arc":"epilogue","title":"After: lot77 bought","text":"The forty robots from Lot 77 run the Unsorted's second yard. They do not sort anything.","requires":{"flag":"lot77_bought"}},
"after.krog_aboard":{"kind":"epilogue","arc":"epilogue","title":"After: krog aboard","text":"{krog} got off at a port it liked and runs the docks there. Your crates still arrive restowed.","requires":{"flag":"krog_aboard"}},
"after.geod_fields":{"kind":"epilogue","arc":"epilogue","title":"After: geod fields","text":"Delta's first field is still called {geod}'s Row. The colonists still argue about who owns it. {geod} still does not take part.","requires":{"flag":"geod_fields"}},
"after.neon_land":{"kind":"epilogue","arc":"epilogue","title":"After: neon land","text":"{neon_sleeper} is still asleep. Her land next to {geod}'s Row is worth eleven times what she paid. When she wakes she will ask for you by name.","requires":{"flag":"neon_land"}},
"after.manifest_completed":{"kind":"epilogue","arc":"epilogue","title":"After: manifest completed","text":"The Cult of the Broken Machine added a verse to its holy manifest: one hauler, on time, forty years late.","requires":{"flag":"manifest_completed"}},
"after.solarian_friend":{"kind":"epilogue","arc":"epilogue","title":"After: solarian friend","text":"The Solarian reading-house at Barnard's Star logs your routes next to the sunspots. They say it helps with both.","requires":{"flag":"solarian_friend"}},
"after.fluencer_exposed":{"kind":"epilogue","arc":"epilogue","title":"After: fluencer exposed","text":"{fluencer} now streams as herself. She has more followers than before.","requires":{"flag":"fluencer_exposed"}},
"after.heard_the_warning":{"kind":"epilogue","arc":"epilogue","title":"After: heard the warning","text":"You never found out who opened that channel at the portal. You did write the words down: start it from home.","requires":{"flag":"heard_the_warning"}}
}}"""
# --- end of story data ---

_STORY = None
_STORY_LINKS = None
STORY_MOMENTS = {}      # id(game) -> (snapshot, verdicts) of the runtime's last look; not saved


def story_data():
    """The built story: nodes, characters, flags, places (loaded once)."""
    global _STORY
    if _STORY is None:
        data = None
        path = os.environ.get("CARGO_STORY")
        if path:
            try:
                with open(path, encoding="utf-8") as handle:
                    data = json.load(handle)
            except (OSError, ValueError):
                data = None
        if not isinstance(data, dict) or "nodes" not in data:
            data = json.loads(STORY_JSON)
        for key in ("nodes", "characters", "flags", "places", "repaired", "order"):
            data.setdefault(key, [] if key in ("repaired", "order") else {})
        if not data["order"]:
            data["order"] = list(data["nodes"])
        _STORY = data
    return _STORY


def story_links():
    """(after, chosen): node -> the nodes it leads to through 'next', and the
    nodes reached only through a choice (those wait for that choice)."""
    global _STORY_LINKS
    if _STORY_LINKS is None:
        after, by_choice = {}, set()
        for nid, node in story_data()["nodes"].items():
            for target in _as_list(node.get("next")):
                after.setdefault(target, set()).add(nid)
            for choice in node.get("choices") or []:
                by_choice.update(_as_list(choice.get("next")))
        _STORY_LINKS = (after, by_choice - set(after))
    return _STORY_LINKS


def _as_list(value):
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


def record_matches(record, want, player=None):
    """Does a captain record match {"game", "ending", "flag", "same_name"}?"""
    if not isinstance(record, dict) or not isinstance(want, dict):
        return False
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


GAME_TITLES = {"cargo1": "Cargo", "cargo2": "Cargo 2", "cargo3": "Cargo 3"}
ENDING_TITLES = {"trade": "the Hauler Hansa", "combat": "the First Legion", "discovery": "the Heading",
                 "tycoon": "Galactic Tycoon", "": "no ending yet"}
_PLACEHOLDER = re.compile(r"\{([a-z_][a-z0-9_]*)(?:\.([a-z_]+))?\}")


class StoryRuntime:
    """Plays the story's scenes: checks conditions, shows text, offers choices,
    applies effects.  Chapters and endings are still run by the StoryManager;
    this plays everything else and supplies the text for both."""

    PLAYS = ("event", "encounter", "quest", "beat", "stage")
    MOST_PER_MOMENT = 2

    def __init__(self, game):
        self.game = game
        self.done = {}          # node id -> turn it happened
        self.due = {}           # node id -> earliest turn (it follows a node shown earlier)
        self.shown = {}         # repeating node id -> last turn shown
        self.met = []           # characters met, in order
        self.moment = None      # (turn, place) last looked at
        self.origin = None      # the captain record the player is playing as, if any
        self.venue = None

    # -- state -----------------------------------------------------------------
    def snapshot(self):
        snap = self.game.story_snapshot()
        snap["venue"] = self.venue
        snap["origin"] = self.origin
        return snap

    def mark(self, nid):
        """The game tells the story that something it runs has happened."""
        if nid not in self.done:
            self.done[nid] = self.game.turn
            self._queue_followers(nid)

    def _queue_followers(self, nid):
        node = story_data()["nodes"].get(nid) or {}
        for target in _as_list(node.get("next")):
            if not node.get("choose"):
                self.due.setdefault(target, self.game.turn + 1)

    # -- conditions --------------------------------------------------------------
    def check(self, cond, snap, found=None):
        if not cond:
            return True
        if isinstance(cond, list):
            return all(self.check(c, snap, found) for c in cond)
        for key, want in cond.items():
            if not self._holds(key, want, snap, found):
                return False
        return True

    def _holds(self, key, want, snap, found):
        if key.startswith("_"):
            return True
        if key == "all":
            return all(self.check(c, snap, found) for c in want)
        if key == "any":
            return any(self.check(c, snap, found) for c in want)
        if key == "not":
            return not self.check(want, snap)
        if key == "flag":
            return all(f in snap["flags"] for f in _as_list(want))
        if key == "not_flag":
            return not any(f in snap["flags"] for f in _as_list(want))
        if key == "done":
            return all(n in snap["done"] for n in _as_list(want))
        if key == "done_any":
            return any(n in snap["done"] for n in _as_list(want))
        if key == "not_done":
            return not any(n in snap["done"] for n in _as_list(want))
        if key == "since":
            at = snap.get("done_at", {})
            return all(n in snap["done"] and snap["turn"] - at.get(n, -10 ** 9) >= turns for n, turns in want.items())
        if key in ("act_min", "act_max", "turn_min", "turn_max"):
            value = snap["act"] if key.startswith("act") else snap["turn"]
            return value >= want if key.endswith("min") else value <= want
        if key == "at":
            return snap["place"] in _as_list(want)
        if key == "at_type":
            return snap["place_type"] in _as_list(want)
        if key == "venue":
            return snap.get("venue") in _as_list(want)
        if key == "chapter":
            return snap.get("chapter") in _as_list(want)
        if key == "has":
            return all(set(_as_list(items)) <= set(snap["sets"].get(name, [])) for name, items in want.items())
        if key == "visiting_captain":
            for record in snap["visitors"]:
                if record_matches(record, want, snap["player"]):
                    if found is not None:
                        found.setdefault("visitor", record)
                    return True
            return False
        if key == "player_origin":
            return snap.get("origin") is not None and record_matches(snap["origin"], want)
        if key == "code":
            return False            # the story should not lean on code the game cannot read
        value = snap["stats"].get(key, 0)
        if isinstance(want, dict):
            return want.get("min", value) <= value <= want.get("max", value)
        return value >= want

    def requires_of(self, node):
        """A node's condition; the main story's (chapters, milestones, endings, the drama arc)
        scaled to the voyage."""
        cond = node.get("requires")
        if node.get("kind") in ("chapter", "milestone", "ending") or node.get("arc") == "drama":
            return voyage_condition(cond, self.game.voyage_factor())
        return cond

    def condition_for(self, nid):
        """A repaired condition the game should use instead of its own, or None."""
        data = story_data()
        if nid in data["repaired"]:
            return data["nodes"][nid].get("requires") or {}
        return None

    # -- text ---------------------------------------------------------------------
    def fill(self, text, found=None):
        game = self.game
        chars = story_data()["characters"]
        visitor = (found or {}).get("visitor") or {}
        origin = self.origin or {}
        values = {
            "player_name": game.player_name, "rank": game.rank,
            "money": game.format_money(game.ship.money),
            "trades_completed": game.trades_completed,
            "combat_victories": game.ship.combat_victories.get("total", 0),
            "research_points": game.ship.research_points,
            "discoveries": len(game.discovered_locations),
            "place": game.current_location.name, "turn": game.turn,
        }
        records = {"visitor": visitor, "origin": origin}

        def swap(match):
            head, field = match.group(1), match.group(2)
            if head in records:
                record = records[head]
                story = record.get("story", {}) if record else {}
                info = {"name": record.get("name", ""), "rank": record.get("rank", "") or "captain",
                        "game": GAME_TITLES.get(record.get("origin", {}).get("game"), "another part"),
                        "ending": ENDING_TITLES.get(story.get("ending", ""), story.get("ending", "")),
                        "turns": record.get("career", {}).get("turns", 0)}
                return str(info.get(field or "name", match.group(0)))
            if head in chars and (field is None or field in chars[head]):
                return str(chars[head].get(field or "name", ""))
            if field is None and head in values:
                return str(values[head])
            return match.group(0)

        return _PLACEHOLDER.sub(swap, str(text))

    def text_of(self, nid, snap=None, fallback=None, found=None):
        """The lines of a node, its first matching variant first; placeholders filled."""
        node = story_data()["nodes"].get(nid)
        if not node:
            return list(_as_list(fallback))
        text = node.get("text")
        if node.get("variants"):
            snap = snap or self.snapshot()
            for variant in node["variants"]:
                trial = {}
                if variant.get("requires") and self.check(variant["requires"], snap, trial):
                    text = variant.get("text")
                    found = dict(found or {}, **trial)
                    break
        lines = _as_list(text) or _as_list(fallback)
        return [self.fill(line, found) for line in lines if line]

    def title_of(self, nid, fallback=""):
        node = story_data()["nodes"].get(nid) or {}
        return self.fill(node.get("title") or fallback)

    # -- playing ----------------------------------------------------------------
    def playable(self, nid, node):
        if node.get("kind") not in self.PLAYS or node.get("handled_by") or node.get("status") == "unused":
            return False
        if nid in self.done:
            repeat = node.get("repeat")
            if not repeat:
                return False
            cooldown = repeat.get("cooldown", 1) if isinstance(repeat, dict) else 1
            if self.game.turn - self.shown.get(nid, -10 ** 6) < cooldown:
                return False
        after, by_choice = story_links()
        if nid in by_choice and nid not in self.due:
            return False                    # waits for the choice that leads here
        before = after.get(nid)
        if before and nid not in self.due and not any(b in self.done for b in before):
            return False
        if self.due.get(nid, 0) > self.game.turn:
            return False
        return True

    def tick(self):
        """Once per turn and place: play the scenes whose time has come."""
        moment = (self.game.turn, self.game.current_location.name)
        if moment == self.moment:
            return
        self.moment = moment
        self.play_ready()

    def play_ready(self, limit=None):
        data = story_data()
        snap = self.snapshot()
        ready = []
        verdicts = {}
        STORY_MOMENTS[id(self.game)] = (snap, verdicts)     # for tools: what was judged, on what
        for nid in data["order"]:
            node = data["nodes"][nid]
            if not self.playable(nid, node):
                continue
            ok = self.check(self.requires_of(node), snap)
            verdicts[nid] = ok
            if not ok:
                continue
            chance = node.get("chance")
            if chance and nid not in self.due and random.random() >= chance:
                continue
            ready.append(nid)
        ready.sort(key=lambda n: (n not in self.due, bool(data["nodes"][n].get("chance"))))
        for nid in ready[:limit or self.MOST_PER_MOMENT]:
            self.play(nid)

    def play(self, nid, snap=None):
        data = story_data()
        node = data["nodes"][nid]
        snap = snap or self.snapshot()
        found = {}
        self.check(self.requires_of(node), snap, found)
        lines = self.text_of(nid, snap, found=found)
        title = self.title_of(nid)
        for who in _as_list(node.get("who")):
            if who not in self.met:
                self.met.append(who)
        self.cue(node.get("sound"))
        box = [title] if title else []
        for line in lines:
            box.extend([""] + self.game.word_wrap(line))
        choices = [c for c in node.get("choices") or [] if self.check(c.get("requires"), snap)]
        self.done[nid] = self.game.turn
        self.shown[nid] = self.game.turn
        self.due.pop(nid, None)
        self.apply(node.get("effects"))
        if not choices:
            if box:
                self.game.display_story_message(box, pause=1)
            self._queue_followers(nid)
            return None
        for number, choice in enumerate(choices, 1):
            box.extend([""] if number == 1 else [])
            box.extend(self.game.option_lines(number, self.fill(choice.get("say", choice.get("id", "")))))
        self.game.display_story_message(box, pause=0)
        picked = self.ask(len(choices))
        choice = choices[picked]
        self.done["%s:%s" % (nid, choice.get("id", picked))] = self.game.turn
        self.apply(choice.get("effects"))
        for target in _as_list(choice.get("next")):
            self.due[target] = self.game.turn
            target_node = data["nodes"].get(target)
            if target_node and self.check(target_node.get("requires"), self.snapshot()):
                self.play(target)
        self._queue_followers(nid)
        return choice.get("id")

    def ask(self, count):
        options = [str(i) for i in range(1, count + 1)]
        answer = self.game.validate_input("Your choice (1-%d, Enter = %d): " % (count, count), options)
        return int(answer) - 1 if answer else count - 1     # Enter: the last option, usually "leave it"

    # -- effects -----------------------------------------------------------------
    def apply(self, effects):
        game = self.game
        ship = game.ship
        for key, value in (effects or {}).items():
            if key == "set":
                for flag in _as_list(value):
                    game.story_manager.story_states[flag] = True
            elif key == "clear":
                for flag in _as_list(value):
                    game.story_manager.story_states[flag] = False
            elif key == "give":
                for name, members in value.items():
                    for member in _as_list(members):
                        if name == "items":
                            held = ship.items.get(member, 0)
                            ship.items[member] = (held if isinstance(held, int) else 0) + 1
                        elif name == "researched":
                            game.research.unlocked_options.add(member)
                        elif name == "unlocked_types":
                            game.unlock_location_type(member)
                        elif name == "crew":
                            if member not in ship.crew:
                                ship.crew.append(member)
            elif key == "start":
                for target in _as_list(value):
                    self.due[target] = game.turn
            elif key == "reveal":
                for name in _as_list(value):
                    game.reveal_place(name)
            elif key == "code":
                story_hook(game, value)
            elif key == "money":
                ship.money += value
            elif key == "plot_points":
                game.story_manager.plot_points += value
            elif key == "research_points":
                ship.research_points += value
            elif key == "passenger_reputation":
                ship.passenger_reputation += value
            elif key == "passengers_transported":
                game.reputation_manager.total_passengers += value
            elif key == "combat_rating":
                ship.attack = max(1, ship.attack + value)
            elif key.startswith("cargo.") and key[6:] in ship.cargo:
                good = key[6:]
                ship.cargo[good] = max(0, ship.cargo[good] + (min(value, ship.hold_room(good)) if value > 0 else value))

    def cue(self, name):
        if name:
            play_cue(name)

    # -- moments the game calls in -------------------------------------------------
    def visit_venue(self, venue):
        """The captain walks into a port or a cantina."""
        self.venue = venue
        try:
            data = story_data()
            snap = self.snapshot()
            for nid in data["order"]:
                node = data["nodes"][nid]
                if "venue" not in json.dumps(node.get("requires") or {}):
                    continue
                if self.playable(nid, node) and self.check(self.requires_of(node), snap):
                    if not node.get("chance") or random.random() < node["chance"]:
                        self.play(nid)
                        break
            if venue == "cantina":
                self.tell_rumour(snap)
        finally:
            self.venue = None

    def tell_rumour(self, snap):
        data = story_data()
        fresh, heard = [], []
        for nid in data["order"]:
            node = data["nodes"][nid]
            if node.get("kind") == "rumour" and self.check(node.get("requires"), snap):
                (heard if nid in self.done else fresh).append(nid)
        story = [n for n in fresh if data["nodes"][n].get("arc") != "gossip"]
        pool = [n for n in story if data["nodes"][n].get("requires")] or \
            ([n for n in fresh if n not in story] if random.random() < 0.6 else story) or fresh or heard
        if pool:
            nid = random.choice(pool)
            self.done[nid] = self.game.turn
            self.game.display_story_message(["Overheard in the cantina", ""] + sum(
                (self.game.word_wrap(line) for line in self.text_of(nid, snap)), []), pause=1)

    def introduce(self):
        """The first scene of a new game: who this captain is and why they start here."""
        data = story_data()
        snap = self.snapshot()
        for nid in data["order"]:
            node = data["nodes"][nid]
            if node.get("kind") == "intro" and self.check(node.get("requires"), snap):
                self.play_as(nid, snap)
                return nid
        return None

    def play_as(self, nid, snap):
        node = story_data()["nodes"][nid]
        lines = self.text_of(nid, snap)
        box = [self.title_of(nid)] if node.get("title") else []
        for line in lines:
            box.extend([""] + self.game.word_wrap(line))
        self.cue(node.get("sound"))
        self.game.display_story_message(box, pause=2)
        self.done[nid] = self.game.turn
        self.apply(node.get("effects"))

    def epilogue(self):
        """After an ending: what became of the people the captain met."""
        data = story_data()
        snap = self.snapshot()
        lines = []
        for nid in data["order"]:
            node = data["nodes"][nid]
            if node.get("kind") == "epilogue" and self.check(node.get("requires"), snap):
                for line in self.text_of(nid, snap):
                    lines.extend([""] + self.game.word_wrap(line))
        if lines:
            self.game.display_story_message(["What became of them"] + lines[:60], pause=2)

    def journal(self):
        """The captain's log: people met, choices that will be remembered, places."""
        data = story_data()
        game = self.game
        chars = data["characters"]
        rows = [["Captain's log"], [""]]
        aboard = getattr(game.ship, "special_cargo", {})
        if aboard:
            labels = getattr(game.ship, "special_labels", {})
            rows.append(["Aboard"])
            rows.extend([["- %s (%d units of hold)" % (labels.get(name, name), units)] for name, units in aboard.items()])
            rows.append([""])
        rows.append(["People"])
        people = [c for c in self.met if c in chars and not chars[c].get("generated")]
        for cid in people or []:
            info = chars[cid]
            rows.append(["- %s" % info.get("name", cid)])
        if not people:
            rows.append(["Nobody worth writing down yet."])
        rows.extend([[""], ["Remembered"]])
        states = game.story_manager.story_states
        notes = [info.get("about") for flag, info in data["flags"].items()
                 if states.get(flag) and info.get("carries_to") and info.get("about")]
        notes = [self.fill(note) for note in notes]
        rows.extend([["- " + note[0].upper() + note[1:]] for note in notes] or [["Nothing the future will ask about."]])
        rows.extend([[""], ["Places"]])
        for name in game.known_locations:
            place = data["places"].get(name, {})
            system = place.get("system")
            rows.append(["- %s%s" % (name, " (%s%s)" % (system, ", %s ly" % place["ly"] if place.get("ly") else "") if system else "")])
        print(game.create_box(rows, 'double', narrow='flow'))
        input("Press Enter to continue...")


def play_cue(name):
    """A story sound, if the kit beside the game can play it (silent otherwise)."""
    kit = _sound_kit()
    if kit is not None:
        try:
            kit.play(name)
        except Exception:
            pass


_SOUND_KIT = []


def _sound_kit():
    if not _SOUND_KIT:
        kit = None
        if os.environ.get("CARGO_SOUND", "1") != "0":
            folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cargo-kit")
            path = os.path.join(folder, "sound.py")
            if os.path.isfile(path):
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("cargo_kit_sound", path)
                    kit = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(kit)
                except Exception:
                    kit = None
        _SOUND_KIT.append(kit)
    return _SOUND_KIT[0]


def _repair_at_cost(game):
    cost = int(game.ship.damage * game.ship.repair_rate() * 2)
    if game.ship.damage and game.ship.money >= cost:
        game.ship.money -= cost
        game.ship.damage = 0
        game.display_simple_message("Hull repaired for %s credits." % game.format_money(cost))


def _open_portal(game):
    game.open_portal()


STORY_HOOKS = {
    "hull repaired at cost": _repair_at_cost,
    "portal": _open_portal,
}


def story_hook(game, value):
    """Game code a story effect names: a hook above, or one of these phrases:
    'fight <enemy>' (no paying or talking your way out), 'fight <enemy> edge <n>' (with allies),
    'crew joins <role>', 'repair <points>', 'damage <points>', 'lose money <share> min <amount>',
    'stow <units> <name> as <words>' (special cargo takes hold room until 'unstow <name>'; the
    words name it on screen and in the journal), 'profit <credits>' (paid, and counted as trade profit),
    'lose research <share>', 'buy bonds <n>', 'sell bonds', 'crew leaves <role>',
    'dues hike <factor>' (for thirty turns), 'squeeze <good> <factor>' (prices of a good fall at
    every known dock, then recover like any market)."""
    if isinstance(value, list):
        for one in value:
            story_hook(game, one)
        return None
    hook = STORY_HOOKS.get(value)
    if hook:
        return hook(game)
    words = str(value).split()
    ship = game.ship
    if len(words) in (2, 4) and words[0] == "fight" and words[1] in ENEMIES:
        help_ = int(words[3]) if len(words) == 4 and words[2] == "edge" else 0
        outcome = game.encounter(words[1], hunted=True, edge=help_)
        # the story remembers how a fight it started went: fight_won_<enemy> / fight_lost_<enemy>
        won = outcome == "victory"
        game.story_manager.story_states["fight_%s_%s" % ("won" if won else "lost", words[1])] = True
    elif words[:2] == ["lose", "money"]:
        share = float(words[2])
        floor_ = int(words[4]) if len(words) > 4 and words[3] == "min" else 0
        loss = min(int(ship.money), max(floor_, int(ship.money * share)))
        ship.money -= loss
        game.display_simple_message("It costs you %s." % game.format_money(loss), 2, color='31')
    elif words[:2] == ["lose", "research"]:
        loss = int(ship.research_points * float(words[2]))
        ship.research_points -= loss
        game.display_simple_message("%d research points are gone with the logs." % loss, 2, color='31')
    elif words[:2] == ["buy", "bonds"]:
        game.buy_bonds(int(words[2]))
    elif words[:2] == ["sell", "bonds"]:
        held, value_ = game.sell_bonds()
        game.display_simple_message("The Hansa buys back %d bond%s for %s. Your dues go back up." % (
            held, "" if held == 1 else "s", game.format_money(value_)), 2)
    elif words[:2] == ["crew", "joins"]:
        if words[2] not in ship.crew:
            ship.crew.append(words[2])
            game.display_simple_message("%s is back aboard." % game.crew_name(words[2]), 2, color='32')
    elif words[0] == "stow" and len(words) >= 3:
        if not hasattr(ship, "special_cargo"):
            ship.special_cargo, ship.special_labels = {}, {}
        labels = ship.__dict__.setdefault("special_labels", {})
        ship.special_cargo[words[2]] = int(words[1])
        if len(words) > 4 and words[3] == "as":
            labels[words[2]] = " ".join(words[4:])
        game.display_simple_message("Loaded: %s (%s units of hold)."
                                    % (labels.get(words[2], words[2]), words[1]), 2)
    elif words[0] == "unstow" and len(words) == 2:
        units = getattr(ship, "special_cargo", {}).pop(words[1], None)
        if units is not None:
            label = getattr(ship, "special_labels", {}).pop(words[1], words[1])
            game.display_simple_message("Unloaded: %s (%d units of hold free again)." % (label, units), 2)
    elif words[0] == "profit" and len(words) == 2:      # contract pay that counts as trade profit
        ship.money += int(words[1])
        ship.trade_profits["contracts"] = ship.trade_profits.get("contracts", 0) + int(words[1])
        game.display_simple_message("Contract paid: %s credits (counts as trade profit)." % format(int(words[1]), ","), 2)
    elif words[0] == "damage" and len(words) == 2:
        ship.damage = min(99, ship.damage + int(words[1]))
        game.display_simple_message("Hull damage +%s%%." % words[1], 2, color='31')
    elif words[0] == "repair" and len(words) == 2:
        fixed = min(ship.damage, int(words[1]))
        ship.damage -= fixed
        if fixed:
            game.display_simple_message("Hull repaired by %d%%, free of charge." % fixed, 2, color='32')
    elif words[:2] == ["crew", "leaves"] and words[2] in ship.crew:
        ship.crew.remove(words[2])
        game.display_simple_message("%s packs a bag and leaves the ship." % game.crew_name(words[2]), 2, color='31')
    elif words[:2] == ["dues", "hike"]:          # for the next thirty turns
        game.dues_hike = float(words[2])
        game.dues_hike_until = game.turn + 30
    elif words[0] == "squeeze" and len(words) == 3:
        for loc in game.locations:
            if loc.name in game.known_locations and loc.market.get(words[1], 0) > 0:
                loc.market[words[1]] = round(loc.market[words[1]] * float(words[2]), 1)


def display_logo(logo, centered=True):
    """Displays the logo, optionally centered."""
    terminal_width = terminal_columns()
    for line in logo:
        if plain_terminal():
            line = line.translate(str.maketrans("╔╗╚╝═║", "++++-|"))
        if centered:
            padding = max(0, (terminal_width - visible_len(line)) // 2)
            print(" " * padding + line)
        else:
            print(line)  # Just print without centering

def print_centered_text(text):
    print(text.center(terminal_columns() - 1))


class Research:
    def __init__(self):
        self.unlocked_options = set()
        self.research_costs = {
            'xenoeconomy': 100,
            'telemetry': 150,
            'geophysics': 200,
            'chronopolitics': 250,
            'exogeology': 300,  # New research option
            'psychodynamics': 350  # New research option
        }
        self.research_benefits = {
            'xenoeconomy': {'tax_reduction': 0.02},
            'telemetry': {'scout_success': 0.2},
            'geophysics': {'exogeology': 0.15},
            'chronopolitics': {'revolution_success': 0.2},
            'exogeology': {'output_bonus': 0.25},
            'psychodynamics': {'price_control': 0.1}
        }


    def unlock(self, option):
        self.unlocked_options.add(option)

class Action:
    def __init__(self):
        # Base costs for actions
        self.action_costs = {
            'research': 100,
            'scout': 50,
            'geoscan': 75,
            'revolution': 100,
            'psychodynamics': 60
        }

        # Success chances for various actions
        self.base_success_rates = {
            'scout': 0.65,
            'geoscan': 0.70,
            'revolution': 0.50,
            'psychodynamics': 0.60
        }

    def research(self, planet, option, research_system):
        """
        Attempt to research a new technology
        Returns: (bool success, str message)
        """
        if option in research_system.unlocked_options:
            return False, "This research has already been completed."

        # Apply immediate benefits based on research type
        if option == 'exogeology':
            planet.exogeology = min(100,
                int(planet.exogeology * (1 + research_system.research_benefits['exogeology']['output_bonus'])))

        research_system.unlock(option)
        return True, f"Successfully researched {option}!"

    def scout_area(self, planet, research_system):
        """
        Scout the area for resources or items
        Returns: (bool success, str type, any value, str message)
        """
        # Calculate success chance
        success_chance = self.base_success_rates['scout']
        if 'telemetry' in research_system.unlocked_options:
            success_chance += research_system.research_benefits['telemetry']['scout_success']

        if random.random() < success_chance:
            discovery_type = random.choice(['tech', 'agri', 'item'])

            if discovery_type == 'item':
                item = random.choice(['scanner', 'probe', 'turrets', 'shield'])
                return True, 'item', item, f"Found a {item}!"
            else:
                amount = random.randint(10, 30)
                return True, discovery_type, amount, f"Found {amount} units of {discovery_type}!"

        return False, None, None, "Scouting attempt failed!"

    def geoscan(self, planet, research_system):
        """
        Scan for mineral deposits
        Returns: (bool success, str deposit_type, int amount, str message)
        """
        # Calculate success chance
        success_chance = self.base_success_rates['geoscan']
        if 'geophysics' in research_system.unlocked_options:
            success_chance += research_system.research_benefits['geophysics']['exogeology']

        if random.random() < success_chance:
            deposit_type = random.choice(['salt', 'fuel'])
            amount = random.randint(1000, 5000)

            if deposit_type not in planet.mineral_deposits:
                planet.mineral_deposits[deposit_type] = amount
                return True, deposit_type, amount, f"Found {amount} units of {deposit_type} deposits!"
            else:
                bonus = random.randint(500, 1000)
                planet.mineral_deposits[deposit_type] += bonus
                return True, deposit_type, bonus, f"Found additional {bonus} units of {deposit_type} deposits!"

        return False, None, None, "Geoscan failed to find any deposits!"

    def incite_revolution(self, planet, research_system):
        """
        Attempt to change planet's economy
        Returns: (bool success, str new_economy, str message)
        """
        # Calculate success chance
        success_chance = self.base_success_rates['revolution']
        if 'chronopolitics' in research_system.unlocked_options:
            success_chance += research_system.research_benefits['chronopolitics']['revolution_success']

        if random.random() < success_chance:
            current_economy = planet.economy
            possible_economies = ['Booming', 'Stable', 'Declining', 'Formative']
            possible_economies.remove(current_economy)
            new_economy = random.choice(possible_economies)
            planet.economy = new_economy
            return True, new_economy, f"Revolution successful! Economy changed to {new_economy}!"

        return False, None, "Revolution attempt failed!"

    def manipulate_market(self, planet, commodity, research_system):
        """
        Attempt to manipulate market prices
        Returns: (bool success, float price_change, str message)
        """
        if random.random() < self.base_success_rates['psychodynamics']:
            manipulation_power = research_system.research_benefits['psychodynamics']['price_control']
            current_price = planet.market[commodity]

            # Determine direction of manipulation (increase/decrease)
            direction = random.choice([-1, 1])
            change = direction * random.uniform(0.1, manipulation_power) * current_price

            # Apply change with bounds checking
            new_price = max(1, current_price + change)
            if commodity == 'salt':
                new_price = min(new_price, 150)
            elif commodity == 'fuel':
                new_price = min(new_price, 250)
            else:
                new_price = min(new_price, 200)

            planet.market[commodity] = new_price
            price_change = new_price - current_price
            return True, price_change, f"Successfully manipulated {commodity} price by {abs(price_change):.1f}!"

        return False, 0, "Market manipulation attempt failed!"

# Define the Ship class
class Ship:
    # Passenger reputation runs from 0 to 100 (it multiplies fares and VIP rewards)
    passenger_reputation = property(
        lambda self: self.__dict__.get("passenger_reputation", 0),
        lambda self, value: self.__dict__.__setitem__("passenger_reputation", max(0, min(100, value))))

    def __init__(self, game=None):
        self.game = game
        # Basic cargo and resources
        self.cargo = {
            'tech': 0,
            'agri': 0,
            'salt': 0,
            'fuel': 0
        }
        self.special_cargo = {}     # what the story puts aboard: {name: units of hold}
        self.special_labels = {}    # and what to call it: {name: words}
        self.money = 1000
        self.damage = 0
        self.research_points = 0

        # Ship stats
        self.attack = 1
        self.defense = 1
        self.speed = 1

        # Equipment and upgrades
        self.upgrades = []
        self.items = {}

        # Upgrade costs
        self.upgrade_costs = {
            'attack': 2000,
            'defense': 2000,
            'speed': 2000
        }

        # Item tracking
        self.item_purchase_count = {}

        # Combat statistics
        self.combat_victories = {
            'total': 0,
            'pirate': 0,
            'raider': 0,
            'militia': 0,
            'alien': 0
        }
        self.combat_defeats = {
            'total': 0,
            'pirate': 0,
            'raider': 0,
            'militia': 0,
            'alien': 0
        }
        self.combat_stats = {
            'pirates_defeated': 0,
            'raiders_defeated': 0,
            'militia_defeated': 0,
            'defeats_by_type': {}
        }

        # Trade statistics
        self.trade_profits = {}

        # Enemy-specific victories
        self.enemy_victories = {
            'pirate': 0,
            'raider': 0,
            'militia': 0,
            'alien': 0
        }

                # Initialize passenger-related attributes
        self.passenger_modules = []
        self.passenger_reputation = 0

    def record_combat_victory(self, enemy_type=None):
        """Record a combat victory with proper type tracking"""
        self.combat_victories['total'] += 1
        if enemy_type:
            self.combat_victories[enemy_type] = self.combat_victories.get(enemy_type, 0) + 1

    def record_combat_defeat(self, enemy_type=None):
        """Record a combat defeat with proper type tracking"""
        self.combat_defeats['total'] += 1
        if enemy_type:
            self.combat_defeats[enemy_type] = self.combat_defeats.get(enemy_type, 0) + 1

    # The hold: room for HOLD_BASE units of goods, more with equipment from the shop.
    # Salt and fuel can also use the special containers.
    HOLD_BASE = 400
    HOLD_BONUS = {"cargo_extender": 0.2, "quantum_compressor": 0.5, "containment_optimizer": 0.25}
    SPECIAL_HOLD_BONUS = {"containment_field": 0.3, "stasis_vault": 0.75, "mining_compressor": 0.4,
                          "cargo_scanner": 0.2}

    def hold_sizes(self):
        """(general, special): units for any goods, and extra units for salt and fuel."""
        base = self.HOLD_BASE
        general = base * (1 + sum(b for item, b in self.HOLD_BONUS.items() if self.items.get(item))
                          + (0.1 if "loader" in self.crew else 0) + self.hull_info()["hold"])
        special = base * sum(b for item, b in self.SPECIAL_HOLD_BONUS.items() if self.items.get(item))
        return int(general), int(special)

    # Hulls: the ship the captain started with, and two overhauls from a planet's shipyard.
    # A better hull fights and carries better, rides out rough and deep lanes, and costs
    # far more to repair.
    HULLS = [
        {"name": "Old hauler", "price": 0, "attack": 0, "defense": 0, "hold": 0.0, "repair": 10,
         "about": "the ship the loan bought: honest, slow, patched"},
        {"name": "Ironback", "price": 60000, "attack": 0, "defense": 1, "hold": 0.2, "repair": 50,
         "about": "a reinforced long-hauler hull: thicker plating, a bigger hold; Hansa-rated for the outposts, "
                  "the ruins and the listening posts"},
        {"name": "Farstrider", "price": 220000, "attack": 1, "defense": 2, "hold": 0.4, "repair": 120,
         "about": "a deep-range hull for the far edge of our own system and the systems past the portal; "
                  "heavy, roomy, and every dent costs a fortune"},
    ]
    hull = property(lambda self: self.__dict__.get("hull", 0),
                    lambda self, value: self.__dict__.__setitem__("hull", value))

    def hull_info(self):
        return self.HULLS[min(self.hull, len(self.HULLS) - 1)]

    def repair_rate(self):
        """Credits per point of damage: the hull's rate, less with a mechanic aboard."""
        return self.hull_info()["repair"] * (0.7 if "mechanic" in self.crew else 1.0)

    # Fighting equipment: (attack bonus, defense bonus)
    FIGHT_GEAR = {"combat_drone": (1, 0), "shield_booster": (0, 1), "mining_laser": (0, 1),
                  "neutron_shield": (0, 2), "warp_core": (2, 0)}

    # The crew: helpers hired in cantinas (names in the story file, story/cargo1/crew.json)
    crew = property(lambda self: self.__dict__.setdefault("crew", []))
    CREW_BUNKS = 4

    def fight_attack(self):
        return self.attack + sum(g[0] for item, g in self.FIGHT_GEAR.items() if self.items.get(item)) \
            + (1 if "gunner" in self.crew else 0) + self.hull_info()["attack"]

    def fight_defense(self):
        return max(1, self.defense + sum(g[1] for item, g in self.FIGHT_GEAR.items() if self.items.get(item))
                   + self.hull_info()["defense"])

    def trade_tax(self, rate):
        """The tax rate after the ship's loading gear and broker (never below 1%)."""
        if self.items.get("auto_loader"):
            rate -= 0.02
        if "broker" in self.crew:
            rate -= 0.02
        return max(0.01, rate)

    def research_bonus(self):
        """Extra share of research points from travel and discoveries."""
        return (0.2 if self.items.get("research_module") else 0) + (0.1 if self.items.get("data_analyzer") else 0)

    def stowed(self):
        """Units of hold taken by special cargo the story put aboard (a hovertank, sealed crates)."""
        return sum(getattr(self, "special_cargo", {}).values())

    def hold_room(self, item):
        """How many more units of `item` fit in the hold."""
        general, special = self.hold_sizes()
        general -= self.stowed()
        dry = self.cargo['tech'] + self.cargo['agri']
        bulk = self.cargo['salt'] + self.cargo['fuel']
        if item in ('salt', 'fuel'):
            return max(0, general + special - dry - bulk)
        return max(0, general - dry - max(0, bulk - special))

    def hold_text(self):
        general, special = self.hold_sizes()
        return "%d/%d" % (sum(self.cargo.values()) + self.stowed(), general + special)

    def buy(self, item, quantity, price, planet, player_rank):
        if not planet.can_trade(item):
            return False
        if quantity <= 0 or quantity > self.hold_room(item):
            return False

        if item in ['salt', 'fuel']:
            has_platform = planet.trades_bulk(item)
            if not has_platform:
                return False

        price = planet.trade_price(item, quantity, selling=False)
        cost = quantity * price
        if self.money >= cost:
            tax_rate = self.trade_tax(planet.calculate_tax_rate(player_rank, cost))
            tax_amount = cost * tax_rate
            total_cost = cost + tax_amount

            if self.money >= total_cost:
                self.money -= total_cost
                self.cargo[item] += quantity
                # what the goods in the hold cost, so a sale can tell profit from revenue
                basis = self.__dict__.setdefault("cost_basis", {})
                if self.cargo[item] == quantity:          # the hold was empty: start afresh
                    basis[item] = 0
                basis[item] = basis.get(item, 0) + total_cost
                planet.trade_impact(item, quantity, selling=False)

                # Add contract progress tracking for buy events
                if hasattr(self, 'game') and hasattr(self.game, 'contract_manager'):
                    event_data = {
                        "action": "buy",
                        "commodity": item,
                        "amount": quantity,
                        "location": planet.name,
                        "turn": self.game.turn
                    }
                    self.game.contract_manager.update_contract_progress(event_data)

                return True
            return False
        return False

    def sell(self, item, quantity, price, planet, player_rank):
        if not planet.can_trade(item):
            return False

        if item in ['salt', 'fuel']:
            has_platform = planet.trades_bulk(item)
            if not has_platform:
                return False

        if self.cargo[item] >= quantity:
            price = planet.trade_price(item, quantity, selling=True)
            revenue = quantity * price
            tax_rate = self.trade_tax(planet.calculate_tax_rate(player_rank, revenue))
            tax_amount = revenue * tax_rate
            net_revenue = revenue - tax_amount

            # Profit is what the sale brought in minus what those goods cost.
            # Goods that cost nothing (mined, found, given) are all profit.
            basis = self.__dict__.setdefault("cost_basis", {})
            held = self.cargo[item]
            cost_of_sold = basis.get(item, 0) * quantity / held if held else 0
            basis[item] = max(0, basis.get(item, 0) - cost_of_sold) if held > quantity else 0

            self.money += net_revenue
            self.cargo[item] -= quantity
            planet.trade_impact(item, quantity, selling=True)

            # Track trade profits
            if item not in self.trade_profits:
                self.trade_profits[item] = 0
            self.trade_profits[item] += net_revenue - cost_of_sold

            # Add contract progress tracking for sell events
            if hasattr(self, 'game') and hasattr(self.game, 'contract_manager'):
                event_data = {
                    "action": "sell",
                    "commodity": item,
                    "amount": quantity,
                    "location": planet.name,
                    "turn": self.game.turn
                }
                self.game.contract_manager.update_contract_progress(event_data)

            return True
        return False

    def repair(self, cost):
        if self.money >= cost:
            self.money -= cost
            self.damage = 0
            return True
        return False

    def upgrade(self, property_name, cost):
        if self.money >= cost:
            self.money -= cost
            if property_name == 'attack':
                self.attack += 1
            elif property_name == 'defense':
                self.defense += 1
            elif property_name == 'speed':
                self.speed += 1
            return True
        return False

    def acquire_item(self, item_name):
        if item_name in self.items:
            self.items[item_name] += 1
        else:
            self.items[item_name] = 1

    def is_empty_cargo(self):
        return all(amount == 0 for amount in self.cargo.values())

    def upgrade_property(self, property_name, amount):
        if property_name == 'attack':
            self.attack += amount
        elif property_name == 'defense':
            self.defense += amount
        elif property_name == 'speed':
            self.speed += amount

class LocationCommands:
    """Define available commands per location type"""
    COMMANDS = {
        "Planet": {
            "base_commands": [
                ('buy', 'b'), ('sell', 's'), ('upgrade', 'u'),
                ('travel', 't'), ('repair', 'r'), ('info', 'i'),
                ('build', 'bl'), ('cantina', 'c'), ('shop', 'sh'),
                ('action', 'a'), ('mine', 'm'), ('port', 'p'), ('hunt', 'hu'), ('end', 'e')
            ],
            "description": "Standard planetary commerce hub"
        },
        "AsteroidBase": {
            "base_commands": [
                ('buy', 'b'), ('sell', 's'), ('upgrade', 'u'),
                ('travel', 't'), ('repair', 'r'), ('info', 'i'),
                ('build', 'bl'), ('cantina', 'c'), ('shop', 'sh'),
                ('action', 'a'), ('mine', 'm'), ('port', 'p'), ('hunt', 'hu'), ('end', 'e')
            ],
            "description": "Mining and resource extraction facility"
        },
        "DeepSpaceOutpost": {
            "base_commands": [
                ('buy', 'b'), ('sell', 's'), ('upgrade', 'u'),
                ('travel', 't'), ('repair', 'r'), ('info', 'i'),
                ('build', 'bl'), ('cantina', 'c'), ('shop', 'sh'),
                ('action', 'a'), ('port', 'p'), ('hunt', 'hu'), ('end', 'e')
            ],
            "description": "Strategic trading outpost"
        },
        "ResearchColony": {
            "base_commands": [
                ('buy', 'b'), ('sell', 's'), ('upgrade', 'u'),
                ('travel', 't'), ('research', 'r'), ('info', 'i'),
                ('build', 'bl'), ('cantina', 'c'), ('shop', 'sh'), ('action', 'a'),
                ('port', 'p'), ('end', 'e')
            ],
            "special_commands": {
                "research": {
                    "options": ["analyze", "experiment", "fundamental"],
                    "description": "Conduct research activities"
                }
            },
            "description": "Advanced scientific research facility. No repair facilities available."
        }
    }

    @staticmethod
    def get_available_commands(location_type):
        """Get available commands for location type"""
        commands = LocationCommands.COMMANDS.get(location_type,
                                               LocationCommands.COMMANDS["Planet"])
        return commands["base_commands"]

    @staticmethod
    def get_special_commands(location_type):
        """Get special commands if any"""
        location_data = LocationCommands.COMMANDS.get(location_type, {})
        return location_data.get("special_commands", {})

    @staticmethod
    def get_commands_for_location(location):
        """Helper method to get all commands for a location instance"""
        return {
            "available": LocationCommands.get_available_commands(location.location_type),
            "special": LocationCommands.get_special_commands(location.location_type)
        }

# The goods in a hold, with the shortcut each answers to in buy and sell
COMMODITIES = {"tech": ("t",), "agri": ("a", "agro"), "salt": ("s",), "fuel": ("f",)}

# Commands every location accepts besides its own (long form, shortcut)
GLOBAL_COMMANDS = [('hansa', 'ha'), ('log', 'l'), ('journal', 'j'), ('save', 'sv'), ('load', 'ld'),
                   ('captain', 'cap'), ('help', 'h'), ('version', 'v'), ('resign', 'rs'), ('quit', 'q')]


def commodity_from(answer):
    """'t', 'tech', 'agro', 'a' ... -> the commodity's name, or None."""
    answer = (answer or "").strip().lower()
    for name, shortcuts in COMMODITIES.items():
        if answer == name or answer in shortcuts:
            return name
    return None


# --- encounters: who stops a ship between docks, and what the captain can do about it ---
# power: how hard they hit and how hard they are to beat (1-7); speed: how hard they are
# to outrun; kind: what a victory counts as; deal: "pay" (they take money to leave),
# "talk" (reputation can talk them down), "toll" (customs: pay a fee or show a clean scan).
# tricks: equipment and crew that work especially well against them.
ENEMIES = {
    "skiff": {"name": "Scrap skiff", "kind": "pirate", "power": 1, "speed": 2, "deal": "pay",
              "text": "A scavenger skiff with a harpoon gun and big ideas. Its pilot is about fifteen."},
    "raider": {"name": "Pirate raider", "kind": "pirate", "power": 2, "speed": 3, "deal": "pay",
               "text": "A cut-down hauler with guns welded where the cargo doors used to be."},
    "drones": {"name": "Feral mining drones", "kind": "machine", "power": 2, "speed": 4, "deal": None,
               "tricks": ["turrets", "mining_laser"],
               "text": "A swarm of cutting drones that lost their mine and kept the habit. Your hull looks like ore to them."},
    "corsair": {"name": "Corsair wing", "kind": "pirate", "power": 3, "speed": 5, "deal": "pay",
                "tricks": ["advanced_radar"],
                "text": "Three light fighters in a tight wedge. Too fast to outrun, too proud to miss."},
    "harvester": {"name": "Runaway harvester", "kind": "machine", "power": 3, "speed": 1, "deal": None,
                  "tricks": ["mining_laser", "quantum_scanner"],
                  "text": "A forty-metre agrobot harvester, off its leash and sure that your hold is a field."},
    "customs": {"name": "Customs cutter", "kind": "militia", "power": 3, "speed": 4, "deal": "toll",
                "text": "A customs cutter flashes its lights: stop for inspection. Inspection has a fee."},
    "cultists": {"name": "Cult boarding party", "kind": "raider", "power": 3, "speed": 2, "deal": "talk",
                 "text": "The Cult of the Broken Machine wants to inspect your ship for holiness. They brought cutting torches."},
    "militia": {"name": "Toll militia", "kind": "militia", "power": 4, "speed": 4, "deal": "pay",
                "text": "A local militia has declared this lane a toll road. The toll is whatever they think you carry."},
    "deserters": {"name": "Legion deserters", "kind": "raider", "power": 4, "speed": 3, "deal": "talk",
                  "tricks": ["advanced_radar"],
                  "text": "A legion gunboat with the corporate logo burned off. The crew left the legion; the training stayed."},
    "mothership": {"name": "Pirate mothership", "kind": "pirate", "power": 5, "speed": 2, "deal": "pay",
                   "tricks": ["quantum_scanner", "combat_drone"],
                   "text": "A converted ore carrier with a pirate flotilla in its belly. It is in no hurry. Neither are you, now."},
    "warship": {"name": "Rogue warship", "kind": "raider", "power": 6, "speed": 3, "deal": "talk",
                "tricks": ["quantum_scanner", "advanced_radar"],
                "text": "A frigate nobody admits to having lost. Its captain sends a polite request to surrender."},
    "cargolytes": {"name": "Cargolyte stevedores", "kind": "raider", "power": 4, "speed": 3, "deal": "tithe",
                   "after": "met_cargolytes",
                   "text": "A Cargolyte boarding party, singing, with cutting torches and a copy of your manifest they should not have. 'In apparent good order and condition,' says the one in front. They have come to receive the Sender's cargo. Yours."},
    "rootstock": {"name": "Rootstock enforcers", "kind": "smuggler", "power": 4, "speed": 5, "deal": "pay",
                  "after": "met_rootstock",
                  "text": "A fast cutter with no transponder and very good paint comes alongside. The androids aboard wear good suits and no expressions. One of them speaks, quietly: the family would like a word, and a share."},
    "dreadnought": {"name": "Pirate dreadnought", "kind": "pirate", "power": 7, "speed": 2, "deal": "pay",
                    "tricks": ["quantum_scanner", "combat_drone"],
                    "text": "Three motherships welded together and called a fleet. Every pirate on the frontier pays it a share."},
}

# Gear and crew that change a fight: a line for the menu, and what it does
FIGHT_TRICKS = {
    "advanced_radar": ("Radar: jam their targeting", {"edge": 2}),
    "combat_drone": ("Drone: send it in first", {"edge": 2, "shield": 0.5}),
    "mining_laser": ("Mining laser: cut them up", {"edge": 3}),
    "quantum_scanner": ("Quantum scanner: find the weak spot", {"edge": 2}),
    "turrets": ("Turrets: fire first", {"edge": 2}),
}


def odds_word(chance):
    return ("long odds" if chance < 0.35 else "even odds" if chance < 0.6
            else "good odds" if chance < 0.85 else "easy")


# --- situations: moments between docks where the right gear, crew or nerve pays off ---
# Each option: say (the menu line), needs (items / crew / cargo the option requires;
# "any" means one of them), and an outcome: a dict of effects with a line of text, or
# {"chance": p, "win": {...}, "lose": {...}}.  Effects: money, damage, rp (research),
# pp (plot points), rep (passenger reputation), cargo (good: amount, or "any": amount),
# fight (an enemy id), tier (scale money by the danger level).  "{x}" names crew.
SITUATIONS = {
    "distress": {
        "title": "Distress beacon",
        "text": "A distress beacon, two light-minutes off your course. A life pod or bait: the signal looks the same.",
        "options": [
            {"say": "Scan it before you go in", "needs": {"any": ["advanced_radar", "scanner", "cargo_scanner"]},
             "do": {"chance": 0.6, "win": {"say": "Real survivors: four miners in a pod built for two. The shipping line pays a finder's fee.",
                                           "money": 600, "tier": True, "rep": 4, "pp": 4},
                    "lose": {"say": "The scan shows weapons warm behind the beacon. You log it for the militia and fly on.",
                             "rp": 10, "pp": 1}}},
            {"say": "Answer the call",
             "do": {"chance": 0.6, "win": {"say": "Real survivors: four miners in a pod built for two. The shipping line pays a finder's fee.",
                                           "money": 600, "tier": True, "rep": 4, "pp": 4},
                    "lose": {"say": "It was bait.", "fight": "raider"}}},
            {"say": "Fly on", "do": {"say": "The beacon fades behind you. Somebody else's problem, or somebody else's trap."}},
        ]},
    "derelict": {
        "title": "Derelict hauler",
        "text": "A hauler drifts with its lights off and its bay doors welded shut. No answer on any channel.",
        "options": [
            {"say": "Cut the bay open with the mining laser", "needs": {"items": ["mining_laser"]},
             "do": {"say": "The doors fall away in one piece. Most of the cargo is still there.",
                    "cargo": {"any": 60}, "rp": 5, "pp": 2}},
            {"say": "Read its log (quantum scanner)", "needs": {"items": ["quantum_scanner"]},
             "do": {"say": "The log covers forty years of routes, including three nobody uses now. The research colonies will want this.",
                    "rp": 35, "pp": 3}},
            {"say": "Board it",
             "do": {"chance": 0.55, "win": {"say": "You squeeze through a maintenance hatch and pass crates out by hand.",
                                            "cargo": {"any": 25}, "pp": 1},
                    "lose": {"say": "The airlock was rigged. Whoever welded those doors meant it.", "damage": 10}}},
            {"say": "Report it to the registry", "do": {"say": "The registry thanks you and pays a small salvage notice fee.",
                                                         "money": 200, "rep": 2}},
        ]},
    "ion_storm": {
        "title": "Ion storm",
        "text": "An ion storm sits across the lane like a bad mood. The navigation computer suggests prayer.",
        "options": [
            {"say": "Raise shields and ride it out", "needs": {"any": ["shield", "shield_booster"]},
             "do": {"say": "The shields glow and complain, and hold.", "damage": 3, "rp": 8}},
            {"say": "Let {navigator.short} find a gap", "needs": {"crew": ["navigator"]},
             "do": {"say": "{navigator.short} reads the storm like weather on a farm drum and finds a lane through it.", "rp": 12, "pp": 1}},
            {"say": "Emergency jump clear", "needs": {"items": ["emergency_warp"]},
             "do": {"say": "One lurch, one headache, and the storm is behind you.", "damage": 2}},
            {"say": "Ride it out", "do": {"say": "Every panel on the bridge lights up at once.", "damage": 18, "rp": 8}},
            {"say": "Go around (extra fuel)", "do": {"say": "The long way round costs fuel and a day.", "money": -150, "tier": True}},
        ]},
    "debris": {
        "title": "Debris field",
        "text": "Debris from an old collision, spread thin and moving fast. Some of it is worth money. The navigation computer works out the odds of getting through and decides not to share them.",
        "options": [
            {"say": "Shoot a path with the turrets", "needs": {"items": ["turrets"]},
             "do": {"say": "The turrets turn the worst of it to gravel. You scoop the rest.", "cargo": {"salt": 30}, "pp": 1}},
            {"say": "Cut and scoop with the mining laser", "needs": {"items": ["mining_laser"]},
             "do": {"say": "You cut the big pieces down and scoop the ore.", "cargo": {"salt": 40, "fuel": 15}, "pp": 1}},
            {"say": "Send the probe ahead", "needs": {"items": ["probe"]},
             "do": {"say": "The probe maps a clear line through. It also maps where the debris came from.", "rp": 15}},
            {"say": "Thread it slowly",
             "do": {"chance": 0.5, "win": {"say": "Slow and careful works. Only paint lost.", "damage": 2},
                    "lose": {"say": "Something the size of a fridge finds you.", "damage": 12}}},
        ]},
    "cargo_pod": {
        "title": "Loose cargo pod",
        "text": "A cargo pod tumbles past, beacon dead, owner unknown. Salvage law says finders keepers, mostly.",
        "options": [
            {"say": "Let {loader} grab it", "needs": {"crew": ["loader"]},
             "do": {"say": "{loader} catches the pod one-handed and stacks it before you finish the sentence.",
                    "cargo": {"any": 50}, "pp": 1}},
            {"say": "Grab it", "do": {"say": "It takes an hour and a lot of swearing to get it in the hold.", "cargo": {"any": 25}}},
            {"say": "Log it and leave it", "do": {"say": "You log the pod for its owner. Someone, somewhere, owes you a drink.", "rep": 1}},
        ]},
    "fluencer": {
        "title": "Yacht alongside",
        "text": "A yacht wrapped in screens pulls alongside. Somebody's heir, or somebody saying so, wants to stream your ship for her followers.",
        "options": [
            {"say": "Let {steward} handle her", "needs": {"crew": ["steward"]},
             "do": {"say": "{steward} serves tea on camera and corrects her grammar. The stream loves him. So do the sponsors.",
                    "money": 800, "rep": 5, "pp": 2}},
            {"say": "Pose for the stream",
             "do": {"chance": 0.65, "win": {"say": "Nine minutes of your best side. A paint company sends a sponsorship.",
                                            "money": 500, "rep": 3, "pp": 1},
                    "lose": {"say": "She also streams your cargo manifest. Three pirates subscribe.", "rep": -2}}},
            {"say": "Close the shutters", "do": {"say": "The yacht films your shutters for a while and leaves."}},
        ]},
    "stowaway": {
        "title": "Stowaway",
        "text": "Your hold has one more person in it than the manifest. She says she is a welder. She is holding a welder.",
        "options": [
            {"say": "{steward} finds her a bunk", "needs": {"crew": ["steward"]},
             "do": {"say": "{steward} finds her a bunk and a job list. She fixes three things before the next dock.",
                    "damage": -8, "rep": 2, "pp": 2}},
            {"say": "Let her work her fare",
             "do": {"say": "She welds what needs welding and leaves at the next dock with a reference.", "damage": -5, "rep": 1}},
            {"say": "Hand her to customs", "do": {"say": "Customs pays a small fee. The dock talks about it for a week.",
                                                 "money": 300, "rep": -3}},
        ]},
    "comet": {
        "title": "Comet tail",
        "text": "A comet's tail crosses the lane: ice, dust and free volatiles for anyone with the gear.",
        "options": [
            {"say": "Skim it with the compressor", "needs": {"items": ["mining_compressor"]},
             "do": {"say": "The compressor drinks the tail. The fuel tanks fill without a single invoice.", "cargo": {"fuel": 60}, "pp": 1}},
            {"say": "Skim it anyway",
             "do": {"chance": 0.6, "win": {"say": "A good haul of ice, and only a few new dents.", "cargo": {"fuel": 20}, "damage": 3},
                    "lose": {"say": "A rock hidden in the ice hits the scoop.", "cargo": {"fuel": 8}, "damage": 10}}},
            {"say": "Keep clear", "do": {"say": "You watch it go. It is very pretty, and very free."}},
        ]},
    "buoy": {
        "title": "Old buoy",
        "text": "An old navigation buoy keeps broadcasting a route that closed forty years ago, in a voice from a dead shipping line.",
        "options": [
            {"say": "Decode its archive", "needs": {"any": ["quantum_scanner", "data_analyzer", "research_module"]},
             "do": {"say": "The archive holds survey data nobody bothered to copy. The colonies will pay in attention.",
                    "rp": 30, "pp": 3}},
            {"say": "Note the coordinates", "do": {"say": "You note them down. One day they may mean something.", "rp": 6}},
        ]},
    "flare": {
        "title": "Flare warning",
        "text": "Your star tracker warns of a flare in nine minutes.",
        "options": [
            {"say": "Raise shields", "needs": {"any": ["shield", "shield_booster"]},
             "do": {"say": "The shields take the flare. The instruments take notes.", "rp": 8}},
            {"say": "Shelter behind a moon", "do": {"say": "You lose half a day behind a moon, and gain a nice view.", "money": -100, "tier": True}},
            {"say": "Push on", "do": {"chance": 0.5, "win": {"say": "The flare misses. Mostly.", "damage": 3},
                                      "lose": {"say": "The flare does not miss.", "damage": 15}}},
        ]},
    "tow": {
        "title": "Barge in trouble",
        "text": "A broken-down ore barge asks for a tow to the nearest dock. Its crew offers money and soup.",
        "options": [
            {"say": "Let {loader} rig the tow", "needs": {"crew": ["loader"]},
             "do": {"say": "{loader} rigs the tow in ten minutes. The barge crew asks if it is for sale. It is not.",
                    "money": 700, "tier": True, "rep": 3, "pp": 2}},
            {"say": "Tow it", "do": {"say": "A slow trip, good soup, and a fair fee at the dock.", "money": 400, "tier": True, "rep": 2, "pp": 1}},
            {"say": "Pass by", "do": {"say": "The barge crew says nothing on the channel, which says plenty."}},
        ]},
    "breakdown": {
        "title": "Reactor hiccup",
        "text": "The reactor coughs, the lights dim, and something in the engine room makes a noise you have not heard before.",
        "options": [
            {"say": "Follow the ship's bugrat to the leak", "needs": {"flags": ["ship_bugrat"]},
             "do": {"say": "The bugrat sits on the cracked coupling and looks at you until you fix it.", "damage": -8, "pp": 1}},
            {"say": "Let {mechanic.short} have a look", "needs": {"crew": ["mechanic"]},
             "do": {"say": "{mechanic.short} finds a cracked coupling, swears at it, and fixes two other things while she is there.",
                    "damage": -10, "pp": 1}},
            {"say": "Run the repair bot", "needs": {"items": ["repair_bot"]},
             "do": {"say": "The repair bot crawls into the engine and comes out pleased with itself.", "damage": -5}},
            {"say": "Hit it until it stops", "do": {"chance": 0.5, "win": {"say": "It stops. You decide not to ask why."},
                                                    "lose": {"say": "It stops, and so does the port thruster.", "damage": 8}}},
        ]},
}


# How long a voyage is: what the main story's chapters, milestones and climaxes ask for
# (plot points, trade profit, trades, victories, research, passengers), times this
VOYAGES = {"short": 0.6, "standard": 1.0, "long": 1.5}
VOYAGE_STATS = ("plot_points", "trade_profit", "trades_completed", "combat_victories", "research_points",
                "passengers_transported")


def voyage_value(key, value, factor):
    """A requirement as it stands on this voyage."""
    if factor == 1.0 or not (key in VOYAGE_STATS or key.startswith("combat_victories.")):
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(round(value * factor))
    if isinstance(value, dict):
        return {k: voyage_value(key, v, factor) if k in ("min", "max") or key == "combat_victories" else v
                for k, v in value.items()}
    return value


def voyage_condition(cond, factor):
    """A story condition with its main-story thresholds scaled to the voyage."""
    if factor == 1.0 or not cond:
        return cond
    if isinstance(cond, list):
        return [voyage_condition(c, factor) for c in cond]
    out = {}
    for key, want in cond.items():
        if key in ("all", "any"):
            out[key] = [voyage_condition(c, factor) for c in want]
        elif key == "not":
            out[key] = voyage_condition(want, factor)
        else:
            out[key] = voyage_value(key, want, factor)
    return out


# Define the Game class
class Game:
    # How often something happens between docks, by difficulty: an easy game has calmer lanes
    LANE_ACTIVITY = {0: 0.55, 1: 0.85, 2: 1.0}

    def __init__(self, difficulty=None, player_name=None, intro=True, origin=None, voyage=None):
        self.term_width = self.get_terminal_width()
        self.term_height = self.get_terminal_height()
        asked = difficulty is None
        self.difficulty = self.choose_difficulty() if difficulty is None else difficulty
        self.voyage = voyage or (self.choose_voyage() if asked else "standard")
        self.locations = self.generate_initial_locations()  # Generate all locations
        self.current_location = random.choice([loc for loc in self.locations if isinstance(loc, Planet)])  # Start at a planet
        self.shop = Shop()  # Initialize the shop system
        self.ship = Ship()
        self.ship.game = self  # connect ship to game
        self.turn = 0
        self.known_locations = [self.current_location.name]
        self.event_log = []
        self.player_name = player_name or self.get_player_name()
        self.rank = "Explorer"
        self.reputation = 0
        self.story_manager = StoryManager(self)
        self.quest_system = QuestSystem(self)
        self.unlocked_location_types = {"Planet"}
        self.location_manager = LocationManager(self)
        self.secret_quest_available = False
        self.stellar_portal_available = False
        self.research = Research()
        self.action = Action()
        # Add new tracking attributes for story milestones
        self.trades_completed = 0
        self.combat_difficulty = 1.0
        self.pirate_frequency = 1.0
        self.event_risk = 1.0
        self.event_probability = 0.2
        self.crisis_active = False
        self.endgame_active = False
        self.enable_stellar_portal = False
        self.legendary_items_available = False
        self.final_crisis_events = False
        self.trade_bonus = 0
        self.repair_discount = 0
        self.combat_bonus = 0
        # Initialize character generators
        self.character_generators = {
            "human": SpecialCharacterGenerator(self),
            "synthetic": SyntheticCharacterGenerator(self),
            "alien": AlienCharacterGenerator(self)
        }
        # Add systems
        self.port_system = Port(self)
        self.contract_manager = ContractManager(self)
        self.resource_transport = ResourceTransportQuest(self)
        self.reputation_manager = PassengerReputationManager(self)
        self.synthetic_events = SyntheticEventManager(self)
        self.character_encounters = SpecialCharacterEncounters(self)
        self.discovered_locations = set()
        self.cooldowns = {}
        self.story_events = {}
        self.infestation_manager = InfestationManager(self)
        self.story = StoryRuntime(self)
        self.story.origin = origin

        # The captain's record: an identity that can travel between the games,
        # and the records of captains who crossed over into this one
        self.captain_id = "C1-%08X" % random.getrandbits(32)
        self.captain_log = []
        self.visiting_captains = []
        self.ending_reached = None

        # Initialize the story
        if intro:
            self.story.introduce()
            self.story_manager.start_game()
            self.display_starting_info()
        else:
            self.story_manager.current_chapter = "ch1"

    # ------------------------------------------------------------------
    # The story's view of the game
    # ------------------------------------------------------------------
    def story_snapshot(self):
        """This moment of play, as the story's conditions see it (storykit State)."""
        ship = self.ship
        sm = self.story_manager
        stats = {
            "money": int(ship.money),
            "plot_points": sm.plot_points,
            "research_points": ship.research_points,
            "trades_completed": self.trades_completed,
            "trade_profit": int(sum(ship.trade_profits.values())),
            "passengers_transported": self.reputation_manager.total_passengers,
            "passenger_reputation": ship.passenger_reputation,
            "combat_rating": ship.attack + ship.defense + ship.speed,
            "combat_victories": ship.combat_victories.get("total", 0),
            "discovered": len(set(self.discovered_locations)),
            "mining_platforms": sum(len(loc.mining_platforms) for loc in self.locations),
            "controlled_locations": sum(1 for loc in self.locations if hasattr(loc, "controlled_by_player")),
            "milestones_done": len(sm.completed_story_beats),
            "turns_since_vip": self.turn - self.reputation_manager.last_vip_spawn,
            "best_cabin": max([m.comfort_level for m in getattr(ship, "passenger_modules", [])
                               if hasattr(m, "comfort_level")] or [0]),
            "crew_size": len(ship.crew),
            "hansa_bonds": getattr(self, "hansa_bonds", 0),
            "hull_class": ship.hull,
            "hold_free": ship.hold_room("tech"),
            "dues_arrears": getattr(self, "dues_arrears", 0),
        }
        for good in ('tech', 'agri', 'salt', 'fuel'):
            stats["cargo." + good] = ship.cargo[good]
        for kind in STORY_VICTORY_TYPES[1:]:
            stats["combat_victories." + kind] = ship.combat_victories.get(kind, 0)
        for building in STORY_BUILDINGS:
            stats["buildings." + building] = sum(loc.buildings.count(building) for loc in self.locations)
        for place_type in STORY_PLACE_TYPES:
            stats["discovered." + place_type] = self.count_discovered(place_type)
        markets = [loc for loc in self.locations if loc.location_type in ("Planet", "AsteroidBase", "DeepSpaceOutpost")]
        stats["stockmarket_everywhere"] = int(bool(markets) and all(loc.stockmarket_base for loc in markets))
        done = set(sm.completed_chapters) | set(self.story.done)
        for cid, chapter in sm.chapters.items():
            for mid, milestone in chapter.milestones.items():
                if milestone.completed:
                    done.add("%s.%s" % (cid, mid))
        return {
            "turn": self.turn,
            "player": self.player_name,
            "act": sm.get_chapter_number(),
            "chapter": sm.current_chapter,
            "place": self.current_location.name,
            "place_type": self.current_location.location_type,
            "stats": stats,
            "sets": {
                "researched": sorted(self.research.unlocked_options),
                "items": sorted(k for k, v in ship.items.items() if isinstance(v, int) and v > 0),
                "unlocked_types": sorted(getattr(self, "unlocked_location_types", set())),
                "crew": sorted(ship.crew),
            },
            "flags": sorted(f for f, on in sm.story_states.items() if on),
            "done": sorted(done),
            "done_at": {n: t for n, t in self.story.done.items() if ":" not in n},
            "visitors": list(getattr(self, "visiting_captains", [])),
        }

    def reveal_place(self, name):
        """Put a place the story describes on the map (story effect 'reveal')."""
        if any(loc.name == name for loc in self.locations):
            return
        place = story_data()["places"].get(name) or {}
        made = place.get("made") or {}
        location = Location(name, place.get("type", "Planet"), made.get("tech", 10), made.get("agri", 1),
                            made.get("research", 50), made.get("economy", "Mysterious"))
        self.locations.append(location)
        if name not in self.known_locations:
            self.known_locations.append(name)
        self.display_story_message(["New location: %s" % name] +
                                   ([place["system"]] if place.get("system") else []), pause=1)

    def open_portal(self):
        """Through a Stellar Portal: a new set of places, somewhere else in time."""
        self.stellar_portal_available = True
        self.story_manager.story_states["stellar_portal"] = True
        new_locations = self.generate_new_locations()
        self.locations.extend(new_locations)
        self.current_location = random.choice(new_locations)
        self.known_locations = [self.current_location.name]
        self.display_story_message(self.story.text_of(
            "stellar_portal", fallback="You have traveled to a new set of locations."), pause=2)
        self.story.mark("stellar_portal")

    def bring_up_to_date(self):
        """A save from an older version: rename places, start missing systems."""
        def rename(location):
            if location is None:
                return
            location.name = RENAMED_PLACES.get(location.name, location.name)
            location.location_type = RENAMED_TYPES.get(location.location_type, location.location_type)
        for location in self.locations:
            rename(location)
        for group in getattr(self, "chapter_locations", {}).values():
            for locations in group.values():
                for location in locations:
                    rename(location)
        self.known_locations = [RENAMED_PLACES.get(n, n) for n in self.known_locations]
        self.discovered_locations = {RENAMED_PLACES.get(n, n) for n in self.discovered_locations}
        if not isinstance(getattr(self, "story", None), StoryRuntime):
            self.story = StoryRuntime(self)
        self.story_manager.apply_story_text()

    # ------------------------------------------------------------------
    # Saving and loading
    # ------------------------------------------------------------------
    def save_summary(self):
        return {
            "player": self.player_name,
            "difficulty": self.difficulty,
            "turn": self.turn,
            "money": int(self.ship.money),
            "location": self.current_location.name,
            "chapter": self.story_manager.current_chapter,
        }

    def save_game(self, slot=None):
        """Write the whole game to a slot; returns the file path."""
        slot = safe_name(slot or self.player_name, AUTOSAVE_SLOT)
        path = os.path.join(save_folder(), slot + ".json")
        data = {
            "format": "cargo-save",
            "version": SAVE_FORMAT,
            "game": GAME_ID,
            "game_version": VERSION,
            "saved_at": time.strftime("%Y-%m-%d %H:%M"),
            "summary": self.save_summary(),
            "state": encode_world(self),
        }
        try:
            write_json(path, data)
        except OSError as error:
            raise SaveError("could not write the save file (%s)" % (error.strerror or "error"))
        return path

    def autosave(self):
        """Quietly keep the latest turn; a failed autosave never stops the game."""
        try:
            self.save_game(AUTOSAVE_SLOT)
        except Exception:
            pass

    def handle_save(self):
        self.display_simple_message(
            f"Save as (Enter for '{safe_name(self.player_name)}', or type a name):", 0)
        slot = input(">>> ").strip()
        if slot.lower() in ("cancel", "back", "none"):
            self.display_simple_message("Not saved.")
            return
        try:
            self.save_game(slot or self.player_name)
            self.display_simple_message(
                f"Game saved as '{safe_name(slot or self.player_name)}' (turn {self.turn}).")
        except SaveError as error:
            self.display_simple_message(f"Not saved: {error}")

    def handle_load(self):
        saves = list_saves()
        if not saves:
            self.display_simple_message("There are no saved games yet.")
            return
        game = choose_saved_game(saves, self)
        if game:
            raise SwitchGame(game)

    # ------------------------------------------------------------------
    # The captain's record
    # ------------------------------------------------------------------
    def captain_record(self, event="export"):
        """This captain as a record the other Cargo games can read."""
        story = self.story_manager
        entry = {"game": GAME_ID, "event": event, "turn": self.turn,
                 "at": time.strftime("%Y-%m-%d")}
        record = {
            "format": "cargo-captain",
            "version": CAPTAIN_FORMAT,
            "id": self.captain_id,
            "name": self.player_name,
            "origin": {"game": GAME_ID, "version": VERSION},
            "rank": self.rank,
            "career": {
                "turns": self.turn,
                "money": int(self.ship.money),
                "trades": self.trades_completed,
                "victories": self.ship.combat_victories.get("total", 0),
                "passengers": self.reputation_manager.total_passengers,
                "reputation": self.ship.passenger_reputation,
                "locations": len(self.known_locations),
                "research_points": self.ship.research_points,
            },
            "research": sorted(self.research.unlocked_options),
            "ship": {"attack": self.ship.attack, "defense": self.ship.defense, "speed": self.ship.speed},
            "story": {
                "chapter": story.current_chapter or "",
                "completed": sorted(story.completed_chapters),
                "ending": self.ending_reached or "",
                "flags": self.record_flags(),
                "plot_points": story.plot_points,
            },
            "hold": {str(item): int(count) for item, count in self.ship.items.items()
                     if isinstance(count, int) and count > 0},
            "log": list(self.captain_log) + [entry],
        }
        record["check"] = _captain_check(record)
        return clean_captain(record)

    def record_flags(self):
        """The flags a record carries: those later parts read first, then the rest."""
        on = {flag for flag, value in self.story_manager.story_states.items() if value}
        carried = {flag for flag, info in story_data()["flags"].items() if info.get("carries_to")}
        return sorted(on & carried) + sorted(on - carried)

    def close_record(self, ending):
        """The story is told: remember how it ended and let the record travel on."""
        self.ending_reached = ending
        path, code = self.export_captain("ending")
        lines = ["Your captain's record has been closed for this timeline."]
        if path:
            lines.append(f"It waits in {path}")
        lines.append("Use 'captain' to carry it into another part of the saga.")
        self.display_story_message(lines)

    def export_captain(self, event="export"):
        """Write the captain's record to the shared folder; returns (path, code)."""
        record = self.captain_record(event)
        path = os.path.join(captain_folder(), "%s-%s.captain" % (safe_name(self.player_name), GAME_ID))
        try:
            write_json(path, record)
        except OSError:
            path = None
        self.captain_log = record["log"]
        return path, captain_to_code(record)

    def receive_captain(self, record):
        """Take in a captain from another timeline.  Returns a message."""
        if record["id"] == self.captain_id:
            return "That is your own record. The Loop does not let a captain meet themselves here."
        self.visiting_captains = [c for c in self.visiting_captains if c["id"] != record["id"]]
        self.visiting_captains.append(record)
        self.captain_log.append({"game": record["origin"]["game"], "event": "crossing",
                                 "turn": self.turn, "at": time.strftime("%Y-%m-%d")})
        self.captain_log = self.captain_log[-20:]
        return "Captain %s (%s, from %s) has crossed into this timeline." % (
            record["name"], record["rank"] or "no rank", record["origin"]["game"])

    def count_discovered(self, location_type=None):
        """How many discovered locations there are, optionally of one type."""
        names = set(self.discovered_locations)
        if location_type is None:
            return len(names)
        return sum(1 for loc in self.locations
                   if loc.name in names and loc.location_type == location_type)

    def has_visiting_captain(self, game=None, ending=None, flag=None):
        """True when a captain with the given origin / ending / story flag has crossed over."""
        for captain in self.visiting_captains:
            if game and captain["origin"]["game"] != game:
                continue
            if ending and captain["story"]["ending"] != ending:
                continue
            if flag and flag not in captain["story"]["flags"]:
                continue
            return True
        return False

    def handle_captain_menu(self):
        """The captain's record: look at it, send it out, take one in."""
        content = [
            [f"Captain {self.player_name}", f"{self.rank}"],
            [f"Record {self.captain_id}", f"Turn {self.turn}"],
            [f"Crossings logged: {len(self.captain_log)}", f"Visitors: {len(self.visiting_captains)}"],
        ]
        for captain in self.visiting_captains:
            content.append([f"  {captain['name']}", f"from {captain['origin']['game']}"])
        print(self.create_box(content, 'double'))
        action = self.validate_input(
            "Captain's record: export, import, back",
            ['export', 'e', 'import', 'i', 'back', 'b'])
        if action in ('export', 'e'):
            path, code = self.export_captain()
            lines = ["Your record is ready to travel."]
            if path:
                lines.append(f"File: {path}")
            lines.append("Or carry this code (copy all of it):")
            self.display_simple_message(lines, 0)
            print(code)                 # unboxed and unwrapped, so it copies cleanly
            input("Press Enter to continue...")
        elif action in ('import', 'i'):
            self.handle_captain_import()

    def handle_captain_import(self):
        files = [(path, record) for path, record in list_captain_files()
                 if record["id"] != self.captain_id]
        if files:
            content = [["Records in the shared folder:"]]
            for number, (path, record) in enumerate(files[:9], 1):
                content.append([f"{number}. {record['name']} - {record['origin']['game']}, "
                                f"{record['rank'] or 'no rank'}"])
            print(self.create_box(content, 'single'))
        self.display_simple_message(
            "Type a number from the list, paste a captain code, or press Enter to cancel:", 0)
        answer = input(">>> ").strip()
        if not answer:
            self.display_simple_message("Nobody crossed over.")
            return
        try:
            if answer.isdigit() and 1 <= int(answer) <= len(files[:9]):
                record = files[int(answer) - 1][1]
            else:
                record = captain_from_code(answer)
            self.display_simple_message(self.receive_captain(record))
        except SaveError as error:
            self.display_simple_message(f"The record was refused: {error}")


    def get_terminal_width(self):
        return terminal_columns()

    def get_terminal_height(self):
        try:
            return shutil.get_terminal_size((80, 24)).lines
        except (OSError, ValueError):
            return 24

    def format_money(self, amount):
        if amount >= 1_000_000_000:
            return f"{amount/1_000_000_000:.1f}B"
        elif amount >= 1_000_000:
            return f"{amount/1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"{amount/1_000:.1f}K"
        return str(floor(amount))

    def generate_initial_locations(self):
        """Generate initial game locations and store hidden locations for later unlock"""
        # Starting planets - always available
        initial_locations = [
            Planet("Alpha", 5, 3, 10, "Stable"),
            Planet("Beta", 2, 7, 15, "Booming"),
            Planet("Gamma", 8, 2, 20, "Declining"),
            Planet("Delta", 4, 6, 25, "Formative"),
            Planet("Epsilon", 7, 4, 30, "Stable")
        ]

        # Hidden locations - unlocked through story progression
        self.hidden_locations = {
            "AsteroidBase": [
                AsteroidBase("Omega XIV", 6, 2, 15, "Stable"),
                AsteroidBase("Sigma VII", 7, 1, 20, "Declining"),
                AsteroidBase("Theta III", 5, 3, 25, "Booming")
            ],
            "DeepSpaceOutpost": [
                DeepSpaceOutpost("DSO-Alpha", 8, 3, 25, "Formative"),
                DeepSpaceOutpost("DSO-Beta", 9, 2, 30, "Booming"),
                DeepSpaceOutpost("DSO-Gamma", 7, 4, 35, "Stable")
            ],
            "ResearchColony": [
                ResearchColony("Nova Labs", 10, 4, 40, "Stable"),
                ResearchColony("Quantum Center", 9, 5, 35, "Booming"),
                ResearchColony("Stellar Institute", 8, 6, 45, "Formative")
            ]
        }

        # Add chapter-specific locations
        self.chapter_locations = {
            3: {  # Available in Chapter 3
                "AncientRuins": [
                    Location("Ancient Ruins Alpha", "Ancient Ruins", 12, 1, 50, "Mysterious"),
                    Location("Ancient Ruins Beta", "Ancient Ruins", 15, 1, 60, "Mysterious")
                ]
            },
            4: {  # Available in Chapter 4
                "AlienOutpost": [
                    Location("Alien Signal Research Outpost X", "Alien Signal Research Outpost", 20, 5, 100, "Unknown"),
                    Location("Alien Signal Research Outpost Y", "Alien Signal Research Outpost", 25, 5, 120, "Unknown")
                ]
            }
        }

        # Initialize unlocked locations tracking
        self.unlocked_location_types = {"Planet"}  # Start with only regular planets
        self.discovered_locations = set()  # Track which specific locations player has found

        return initial_locations

    def create_box(self, content, style='single', narrow='auto'):
        """A full-width box around rows of cells (see render_box)."""
        return render_box(content, style, narrow=narrow)

    def create_character_box(self, character_content, style='round'):
        """A character card: title, a rule, then the text sections."""
        rows = []
        if character_content.get('title'):
            rows.append([character_content['title']])
            rows.append(RULE)
        for section in ['introduction', 'description', 'demands', 'options']:
            text = str(character_content.get(section) or '')
            if text.strip():
                rows.append([text])
        return render_box(rows, style, inner=box_inner_width(cap=80))

    def display_simple_message(self, message, pause=1, style='round', color=None):
        if isinstance(message, list):
            box_content = message
        else:
            box_content = [message]

        box = self.create_simple_box(box_content, style)
        if color:
            box = f"\033[{color}m{box}\033[0m"
        print(box)
        if pause > 0:
            time.sleep(pause)


    def create_simple_box(self, content, style='single'):
        """A full-width box around lines of text, each word-wrapped."""
        return render_box([[str(row)] for row in content], style)

    def handle_travel(self):
        """Centralized travel handler that can be called from anywhere in the game"""
        if "navcomp" in self.ship.items:
            self.display_simple_message("Choose a location to travel to:")
            # Display known locations with numbers
            for i, location in enumerate(self.known_locations, 1):
                print(f"{i}. {location}")

            self.display_simple_message("Enter the number or name of the location (or 'cancel'): ", 0)
            choice = input(">>> ").strip()

            if not choice or choice.lower() == 'cancel':
                self.display_simple_message("Travel cancelled.")
                return False

            if choice.isdigit():
                index = int(choice) - 1
                if 0 <= index < len(self.known_locations):
                    return self.travel_to_location(self.known_locations[index])
                else:
                    self.display_simple_message("Invalid location number.")
                    return False
            else:
                return self.travel_to_location(choice)
        else:
            self.display_simple_message("Enter location name (or 'cancel'): ", 0)
            location_name = input(">>> ").strip()

            if not location_name or location_name.lower() == 'cancel':
                self.display_simple_message("Travel cancelled.")
                return False

            return self.travel_to_location(location_name)


    def handle_contract_menu(self):
        """Route contract menu handling to ContractManager"""
        if not hasattr(self, 'contract_manager'):
            self.contract_manager = ContractManager(self)
        self.contract_manager.handle_contract_menu()


    def validate_input(self, default_prompt, valid_options, prompt=None):
            """
            Validate user input against a list of valid options
            default_prompt: Default prompt text
            valid_options: List of valid input options
            prompt: Optional custom prompt to override default
            """
            while True:
                self.display_simple_message(prompt or default_prompt, 0)

                try:
                    user_input = input(">>> ").strip().lower()
                    if not user_input:
                        if "Enter" not in (prompt or default_prompt):
                            self.display_simple_message("Command cancelled.")
                        return None
                    if user_input in valid_options:
                        return user_input
                    self.display_simple_message(f"Invalid input, try: {', '.join(valid_options)}", 1)
                except KeyboardInterrupt:
                    print("Do you want to exit? (yes/no):")
                    confirm = input(">>> ").strip().lower()
                    if confirm == 'yes':
                        self.display_simple_message("Goodbye!", 1)
                        exit()

    def validate_quantity_input(self, prompt):
        while True:
            self.display_simple_message(prompt, 0)
            try:
                user_input = input(">>> ").strip().lower()
                if not user_input:
                    self.display_simple_message("Command cancelled.")
                    return None
                if user_input in ['max', 'm']:
                    return 'max'
                if user_input in ['half', 'h']:
                    return 'half'
                quantity = int(user_input)
                if quantity > 0:
                    return quantity
                self.display_simple_message("Please enter a positive number, 'max/m', or 'half/h'", 1)
            except ValueError:
                self.display_simple_message("Invalid input. Please enter a number, 'max/m', or 'half/h'", 1)


    # Update Game class methods
    def display_turn_info(self):
        self.clear_screen()

        # Calculate passenger stats
        total_passengers = 0
        total_capacity = 0
        if hasattr(self.ship, 'passenger_modules'):
            for module in self.ship.passenger_modules:
                total_passengers += len(module.passengers)
                total_capacity += module.capacity

        status_content = [
            ["CΔRGΩ", "Ship", f"{self.current_location.location_type}"],
            [f"Turn: {self.turn}", f"ATK: {self.ship.attack}", f"Name: {self.current_location.name}"],
            [f"¤: {self.format_money(self.ship.money)}", f"DEF: {self.ship.defense}", f"Tech LVL: {self.current_location.tech_level}"],
            [f"Tech: {self.format_money(self.ship.cargo['tech'])}", f"SPD: {self.ship.speed}", f"Agri LVL: {self.current_location.agri_level}"],
            [f"Agri: {self.format_money(self.ship.cargo['agri'])}", f"DMG: {self.ship.damage}%", f"ECO: {self.current_location.economy}"],
            [f"Salt: {self.format_money(self.ship.cargo['salt'])}", f"RP: {self.ship.research_points}", f"EFF: {self.current_location.exogeology}%"],
            [f"Fuel: {self.format_money(self.ship.cargo['fuel'])}", f"★ {self.rank}", f"NET: {len(self.current_location.buildings)}"],
            [f"PAX: {total_passengers}/{total_capacity}", f"REP: {self.ship.passenger_reputation}", f"Hold: {self.ship.hold_text()}"]
        ]

        # Add story progress if available
        if hasattr(self, 'story_manager'):
            current_chapter = self.story_manager.chapters[self.story_manager.current_chapter]
            target = self.story_manager.plot_target()
            points = self.story_manager.plot_points
            status_content.append([
                f"Chapter {self.story_manager.get_chapter_number_roman()}",
                f"Plot Points: {points}/{target}" if target and points < target else f"Plot Points: {points}",
                current_chapter.title
            ])

        status_box = self.create_box(status_content, 'double', narrow='flow')
        print(status_box)

        # Market prices with banned commodities indicator
        tech_status = "BANNED" if 'tech' in self.current_location.banned_commodities else str(self.format_money(self.current_location.market['tech']))
        agri_status = "BANNED" if 'agri' in self.current_location.banned_commodities else str(self.format_money(self.current_location.market['agri']))
        salt_status = "BANNED" if 'salt' in self.current_location.banned_commodities else str(self.format_money(self.current_location.market['salt']))
        fuel_status = "BANNED" if 'fuel' in self.current_location.banned_commodities else str(self.format_money(self.current_location.market['fuel']))

        # Market content with two columns
        market_content = [
            [f"Tech: {tech_status}", f"Salt: {salt_status if self.current_location.trades_bulk('salt') else '——'}"],
            [f"Agri: {agri_status}", f"Fuel: {fuel_status if self.current_location.trades_bulk('fuel') else '——'}"]
        ]

        # Add ban duration if any commodities are banned
        if self.current_location.banned_commodities:
            market_content.append(["", ""])  # Empty line for spacing
            market_content.append(["Trade Bans:", "Duration:"])
            for commodity in self.current_location.banned_commodities:
                duration = self.current_location.ban_duration.get(commodity, "Permanent")
                market_content.append([f"{commodity.capitalize()}", f"{duration} turns"])
        print(self.create_box(market_content, 'single'))

        # The commands this place offers (help/h explains them)
        self.display_simple_message(self.command_hint(), 1)

        # Display active effects
        if self.research.unlocked_options:
            effects = [["Active Research Effects"]]
            for research in self.research.unlocked_options:
                effects.append([f"- {research.replace('_', ' ').title()}"])
            print(self.create_box(effects, 'round'))

    def display_location_info(self):
        # Ship section
        # Get total locations
        total_locations = len(self.locations) if hasattr(self, 'locations') else 0
        # Add 1 to discovered count for starting location if not already included
        discovered = (len(self.discovered_locations) if hasattr(self, 'discovered_locations') else 0)

        ship_info = [
            ["Ship Information"],
            [f"Stats: {self.ship.attack}|{self.ship.defense}|{self.ship.speed}"],
            [f"Locations Discovered: {discovered + 1}/{total_locations}"],
            [f"Trades Completed: {self.trades_completed}"],
            [f"PAX Delivered: {self.reputation_manager.total_passengers}"],
#            [f"Locations Discovered: {len(self.discovered_locations) if hasattr(self, 'discovered_locations') else 0}"]
#            [f"Hull Damage: {self.ship.damage}%"],
            [f"Money: {self.format_money(self.ship.money)}"],
            [f"Research Points: {self.ship.research_points}"],
    #        ["Cargo:"],
    #        [f"  Tech: {self.format_money(self.ship.cargo['tech'])}"],
    #        [f"  Agri: {self.format_money(self.ship.cargo['agri'])}"],
    #        [f"  Salt: {self.format_money(self.ship.cargo['salt'])}"],
    #        [f"  Fuel: {self.format_money(self.ship.cargo['fuel'])}"],
            ["Items:"]
        ]


        # Add items if any exist
        if self.ship.items:
            for item, count in self.ship.items.items():
                ship_info.append([f"  {item.capitalize()}: {count}"])
        else:
            ship_info.append(["  No items"])

        # Add combat statistics if they exist
        if hasattr(self.ship, 'combat_victories'):
                    ship_info.append(["Combat Record:"])
                    # Format victories
                    ship_info.extend([
                        [f"Victories/Defeats Summary"],
                        [f"  Pirates: {self.ship.combat_victories.get('pirate', 0)}/{self.ship.combat_defeats.get('pirate', 0)}"],
                        [f"  Raiders: {self.ship.combat_victories.get('raider', 0)}/{self.ship.combat_defeats.get('raider', 0)}"],
                        [f"  Militia: {self.ship.combat_victories.get('militia', 0)}/{self.ship.combat_defeats.get('militia', 0)}"],
                        [f"  Aliens: {self.ship.combat_victories.get('alien', 0)}/{self.ship.combat_defeats.get('alien', 0)}"],
                        [f"  Total: {self.ship.combat_victories.get('total', 0)}/{self.ship.combat_defeats.get('total', 0)}"]
                    ])

        if hasattr(self.ship, 'active_infestations') and self.ship.active_infestations:
            ship_info.append(["Active Infestations:"])
            for name, infestation in self.ship.active_infestations.items():
                ship_info.append([
                    f"{infestation['name']} - Turn {infestation['turns_active']}"
                ])

        # Location section
        location_info = [
            ["Location"],
            [f"Name: {self.current_location.name}"],
            [f"Type: {self.current_location.location_type}"],
            [f"Tech Level: {self.current_location.tech_level}"],
            [f"Agri Level: {self.current_location.agri_level}"],
            [f"Research Points: {self.current_location.research_points}"],
            [f"Economy: {self.current_location.economy}"],
            [f"Mining Efficiency: {self.current_location.exogeology}%"],
            ["Current Market:"],
            [f"  Tech: {self.format_money(self.current_location.market['tech'])}"],
            [f"  Agri: {self.format_money(self.current_location.market['agri'])}"],
            [f"  Salt: {self.format_money(self.current_location.market['salt'])}"],
            [f"  Fuel: {self.format_money(self.current_location.market['fuel'])}"]
        ]

        # Add banned commodities if any
        if self.current_location.banned_commodities:
            location_info.append(["Banned Commodities:"])
            for commodity in self.current_location.banned_commodities:
                duration = self.current_location.ban_duration.get(commodity, "Permanent")
                location_info.append([f"  {commodity.capitalize()}: {duration} turns"])

        # Add buildings
        location_info.append(["Networks (Built):"])
        if self.current_location.buildings:
            building_counts = {}
            for building in self.current_location.buildings:
                building_counts[building] = building_counts.get(building, 0) + 1
            for building, count in building_counts.items():
                location_info.append([f"  {building} x{count}"])
        else:
            location_info.append(["  No buildings"])

        # Add mining information
        location_info.append(["Mining Operations:"])
        if self.current_location.mining_platforms:
            for platform in self.current_location.mining_platforms:
                location_info.append([
                    f"  {platform['type'].capitalize()} Platform",
                    f"  (Efficiency: {platform['efficiency']}%",
                    f"  Capacity: {platform['capacity']})"
                ])
        else:
            location_info.append(["  No mining platforms"])

        # Add mineral deposits if any
        if self.current_location.mineral_deposits:
            location_info.append(["Mineral Deposits:"])
            for deposit_type, amount in self.current_location.mineral_deposits.items():
                location_info.append([f"  {deposit_type.capitalize()}: {amount} units"])

        # Create content by combining ship and location info
        content = []
        max_length = max(len(ship_info), len(location_info))

        for i in range(max_length):
            ship_line = ship_info[i][0] if i < len(ship_info) else ""
            location_line = ""
            if i < len(location_info):
                cells = location_info[i]
                location_line = " ".join([str(cells[0])] + [str(c).strip() for c in cells[1:]])
            content.append([ship_line, location_line])

        print(self.create_box(content, 'double', narrow='stack'))
        input("Press Enter to continue...")

    def build_mining_platform(self):
        """Build a new mining platform on the current planet"""
        if not self.current_location.mineral_deposits:
            self.display_simple_message("No mineral deposits found! Use geoscan first.")
            return

        available_deposits = list(self.current_location.mineral_deposits.keys())
        deposit_type = self.validate_input(
            f"Choose deposit type to mine ({', '.join(available_deposits)}): ",
            available_deposits
        )

        if deposit_type is None:
            return

        cost = 10000
        if self.ship.money >= cost:
            self.ship.money -= cost
            self.current_location.mining_platforms.append({
                'type': deposit_type,
                'efficiency': self.current_location.exogeology,
                'capacity': random.randint(100, 200)
            })
            self.display_simple_message(f"Mining platform for {deposit_type} built!")
        else:
            self.display_simple_message("Not enough money to build mining platform.")


    def choose_difficulty(self):
        self.clear_screen()
        display_logo(logo_data, centered=False)
        difficulty_info = [
#            ["DIFFICULTY SELECTION"],
            [""],
            ["  1. EASY   (calm lanes)"],
            ["  2. NORMAL"],
            ["  3. EXPERT (busy lanes)"],
            ["     "]

        ]

        for line in difficulty_info:
            print(line[0])
            time.sleep(0.1)

        while True:
            self.display_simple_message("Select difficulty (1-3):", 0)
            choice = input(">>> ").strip()

            if choice in ['1', '2', '3']:
                difficulty_names = ['EASY', 'NORMAL', 'EXPERT']
                selected = difficulty_names[int(choice) - 1]
                self.display_simple_message(f"Setting difficulty: {selected}")
                return int(choice) - 1
            else:
                self.display_simple_message("Please select 1, 2, or 3.", 1)


    def choose_voyage(self):
        """Short, standard or long: how much each chapter asks before the story moves on."""
        self.display_simple_message([
            "Voyage length:", "",
            "1. Short haul: every chapter asks for less; a game of an evening or two",
            "2. Standard",
            "3. Long haul: chapters ask for half as much again; more time for everything",
            "", "Enter for standard."], 0)
        for _ in range(3):
            choice = input(">>> ").strip()
            if choice in ("1", "2", "3", ""):
                voyage = {"1": "short", "3": "long"}.get(choice, "standard")
                self.display_simple_message("Voyage: %s." % voyage)
                return voyage
            self.display_simple_message("Please select 1, 2 or 3.", 1)
        return "standard"

    def voyage_factor(self):
        return VOYAGES.get(getattr(self, "voyage", "standard"), 1.0)

    def unlock_advanced_equipment(self):
        """Unlock advanced equipment in shop"""
        # (these were bare prices, which crashed the shop the next time it was opened)
        new_equipment = {
            "neutron_shield": {"price": 40000, "description": "Neutron shield: +2 defense in fights",
                               "tech_required": 3, "plot_required": 0},
            "quantum_drive": {"price": 50000, "description": "Quantum drive: much better odds of outrunning anyone",
                              "tech_required": 3, "plot_required": 0},
            "warp_core": {"price": 75000, "description": "Warp core: +2 attack; the guns never run short of power",
                          "tech_required": 3, "plot_required": 0},
        }
        self.shop.base_equipment.update(new_equipment)


    def get_player_name(self):
        self.clear_screen()

        display_logo(logo_data, centered=False)

        self.display_simple_message([
            "Enter your pilot name",
            "Press Enter for random"
        ], 0)

        name = input(">>> ").strip()

        if not name:
            titles = ["Captain", "Commander", "Pilot", "Hauler", "Trucker", "Starfarer", "Operator", "Rigger","Freerunner","Navigator", "Doc", "Docker" ]
            surnames = ["Aen Stark", "Orr-Slagg", "Dragg Voxx", "Swigg", "Doc Brainac", "Json", "Nova", "Drake", "Phoenix", "Wolf", "Kayo Wu", "Lyra Nyx", "Elerra Solis", "Bryce", "Q'Ella", "Cael Yaro", "Q'Orin"]
            name = f"{random.choice(titles)} {random.choice(surnames)}"
            self.display_simple_message(f"Neural Signature Verified: {name}")

        self.display_simple_message(f"Welcome aboard, {name}!")
        return name

    COMMAND_HELP = {
        'buy': "buy goods: then tech/t, agri/a, salt/s, fuel/f and an amount, max/m or half/h",
        'sell': "sell goods, same answers as buy",
        'travel': "fly to a known location (one turn; the trip may bring events)",
        'port': "passengers, cabins, contracts",
        'cantina': "maps, gossip, quests, contracts, and whoever is in the bar",
        'shop': "equipment for the ship",
        'upgrade': "attack, defense or speed (each upgrade costs more)",
        'repair': "repair the hull",
        'research': "spend research points (research colonies)",
        'action': "scan, research and other actions",
        'mine': "mining platforms and deposits",
        'build': "buildings: stock market, farms, guilds, refineries",
        'info': "this location in detail",
        'hunt': "the bounty board: pick a wanted ship and go after it (takes the turn)",
        'end': "end the turn and wait here",
        'hansa': "Hansa terminal: convoy dues, bonds that lower them, the price board",
        'log': "story progress: what the next chapter needs",
        'journal': "people met, choices remembered, places",
        'save': "save the game (it also saves itself every turn)",
        'load': "load a saved game",
        'captain': "your captain's record: carry it to another part of the saga",
        'help': "this screen",
        'version': "the game's version",
        'resign': "end this game and see the score",
        'quit': "leave (the autosave keeps your progress)",
    }

    def here_commands(self):
        """(long, short) for every command accepted at this location, its own first."""
        own = [pair for pair in self.current_location.commands["available"]]
        return own + [pair for pair in GLOBAL_COMMANDS if pair not in own]

    def command_hint(self):
        own = self.current_location.commands["available"]
        return "Commands: " + ", ".join("%s/%s" % pair for pair in own) + " - help/h for more"

    def show_help(self):
        """A short guide: what the game is about, and every command with its shortcut."""
        rows = [["How to play"], [""],
                ["You run a cargo hauler. Buy goods where they are cheap, sell where they are dear "
                 "(your hold takes %d units; the shop sells more room), carry passengers, take contracts "
                 "and quests from the cantina, and follow the story (log/l) to one of three endings: "
                 "trade, combat or discovery." % sum(self.ship.hold_sizes())],
                [""],
                ["Between docks you meet pirates, customs, drones and odd moments: pick how to handle each. "
                 "Gear and crew open better options (a mining laser cuts drones, a scanner spots bait). "
                 "The bounty board (hunt/hu) pays for wanted ships. Cantinas have rumours, people, and "
                 "crew for hire (four bunks). Plot points move the story: earn them by doing things."],
                [""],
                ["The Hansa's convoys carry you between the stars and charge dues every %d turns, more each time; "
                 "Hansa bonds lower them (hansa/ha). Big loads move prices and markets take a while to recover: "
                 "the Hansa price board and the port's broker robot guess prices elsewhere, closer for docks you "
                 "saw lately. Inside a star system you fly on your own fuel: science missions burn it, or you buy "
                 "the burn from the depot." % self.DUES_EVERY],
                [""],
                ["Outposts, ruins and listening posts are rough going for an old hull, and the far edge of the "
                 "system is worse: a planet's shipyard (upgrade/u, hull) rebuilds you as an Ironback or a "
                 "Farstrider, which fight and carry better and cost far more to repair. Rich captains draw "
                 "bigger pirates, who take a bigger share. People you meet come back, and so do your choices."],
                [""],
                ["Type a command or its shortcut and press Enter. In any menu, Enter on its own goes back. "
                 "Amounts: a number, max/m or half/h. Each 'end' or journey is one turn; the game saves "
                 "itself after every turn."],
                [""], ["Here at %s:" % self.current_location.name]]
        for cmd, shortcut in self.here_commands():
            rows.append(["%s/%s" % (cmd, shortcut), self.COMMAND_HELP.get(cmd, "")])
        print(self.create_box(rows, 'double'))
        input("Press Enter to continue...")

    def display_starting_info(self):
        """Display initial game information with location context"""
        # Get location info based on current_location
        location_type = "an industrial"
        if self.current_location.agri_level > self.current_location.tech_level:
            location_type = "an agricultural"
        elif self.current_location.research_points > 15:
            location_type = "a research"

        intro_text = f"\n  You arrive on {self.current_location.name}, {location_type} {self.current_location.location_type.lower()}, where your adventure begins."
        special_events = [
            "Revolutions are happening!",
            "Economy boom!",
            "Technological advancements!",
            "Agricultural breakthroughs!",
            "Nothing special happening."
        ]
        special_event = random.choice(special_events)
        special_event_text = f"Special Event: {special_event}"

        self.display_story_message(self.word_wrap(intro_text))
        self.display_story_message(self.word_wrap(special_event_text))
        time.sleep(3)  # Pause to let the player read the information

    def option_lines(self, number, label):
        """'3. A long option' wrapped so its later lines sit under its text, not its number."""
        lead = "%d. " % number
        lines = self.word_wrap(label, box_inner_width() - 2 - len(lead))
        return [lead + lines[0]] + [" " * len(lead) + line for line in lines[1:]]

    def word_wrap(self, text, width=None):
        if width is None:
            width = box_inner_width() - 2
        return wrap_text(text, width)

    def display_story_message(self, message, pause=2, style='round', color=None):
        if isinstance(message, list):
            box_content = message
        else:
            box_content = [message]

        box = self.create_simple_box(box_content, style)
        if color:
            box = f"\033[{color}m{box}\033[0m"
        print(box)
        if pause > 0:
            time.sleep(pause)


    def play_turn(self):
            self.new_turn()
            self.display_turn_info()
            self.check_location_unlocks()  # Check for new unlocks each turn
            self.check_milestone_triggers() # Check for StoryManager
            # New chapter and milestone system
            self.story_manager.check_milestone_progress()
            self.story_manager.check_chapter_progress()
            self.story.tick()           # the story's scenes (story/cargo1/*.json)
            self.quest_system.check_active_quests()
            # Get location commands
            location_commands = self.current_location.commands


            self.infestation_manager.check_global_infestations()
            if hasattr(self.ship, 'active_infestations'):
                self.infestation_manager.update_ship_infestations()

            # Update synthetic events (if they exist)
            if hasattr(self, 'synthetic_events'):
                self.synthetic_events.update()

            # For each location, check building counts
            for location in self.locations:
                neuroguild_count = location.buildings.count("Neuroengineering Guild")
                agrobot_count = location.buildings.count("Agrobot Assembly Line")

                if neuroguild_count >= 4 and random.random() < 0.2:  # 20% chance per turn
                    self.synthetic_events.start_uprising("Neurodroid", location)
                if agrobot_count >= 4 and random.random() < 0.2:
                    self.synthetic_events.start_uprising("Agrobot", location)

            # Update port system if port command is available
            port_is_available = False
            for cmd, shortcut in location_commands["available"]:
                if cmd == 'port' or shortcut == 'p':
                    port_is_available = True
                    self.port_system.update_passengers(self.current_location.name)

            # Create list of valid actions
            valid_actions = []
            for cmd, shortcut in location_commands["available"]:
                valid_actions.extend([cmd, shortcut])

            # Add global commands
            for cmd, shortcut in GLOBAL_COMMANDS:
                valid_actions.extend([cmd, shortcut])

            action = self.validate_input("Choose action: ", valid_actions)

            # Handle cancelled command
            if action is None:
                return

            elif action in ['save', 'sv']:
                self.handle_save()
                return

            elif action in ['load', 'ld']:
                self.handle_load()
                return

            elif action in ['captain', 'cap']:
                self.handle_captain_menu()
                return

            # Handle research/repair based on location type ('r' is research at a colony)
            elif action in ['research', 'r', 'repair']:
                if action != 'repair' and isinstance(self.current_location, ResearchColony):
                    self.handle_research_options()
                else:
                    if self.ship.damage > 0:
                        cost = int(self.ship.damage * self.ship.repair_rate())
                        if self.ship.repair(cost):
                            self.display_simple_message("Ship repaired.")
                        else:
                            self.display_simple_message(
                                f"Not enough money to repair. Cost: {self.format_money(cost)}"
                            )
                    else:
                        self.display_simple_message("Ship doesn't need repairs.")

            elif action in ['buy', 'b']:
                item = commodity_from(self.validate_input(
                    "Buy which? tech/t, agri/a, salt/s, fuel/f: ",
                    [w for name, cuts in COMMODITIES.items() for w in (name,) + cuts]))
                if item is None:
                    return

                if not self.current_location.can_trade(item):
                    self.display_simple_message(f"Trading of {item} is banned on this planet!")
                    return

                if item in ['salt', 'fuel']:
                    has_platform = self.current_location.trades_bulk(item)
                    if not has_platform:
                        self.display_simple_message(f"No mining platform for {item} on this planet.")
                        return

                quantity = self.validate_quantity_input("Enter quantity (max/m, half/h): ")
                if quantity is None:
                    return

                price = self.current_location.market[item]
                if price <= 0:
                    self.display_simple_message(f"Cannot calculate amount: {item} has no valid price.")
                    return

                tax_rate = self.ship.trade_tax(self.current_location.calculate_tax_rate(self.rank, price))
                room = self.ship.hold_room(item)
                max_quantity = self.affordable(item, tax_rate, room)

                if quantity == 'max':
                    quantity = max_quantity
                elif quantity == 'half':
                    quantity = (max_quantity + 1) // 2  # Round up division
                elif quantity > room:
                    self.display_simple_message(f"The hold has room for {room} more {item}.")
                    quantity = room

                if quantity <= 0:
                    self.display_simple_message("The hold is full." if room <= 0 else
                                                f"Not enough money for one unit of {item}.")
                elif self.ship.buy(item, quantity, self.current_location.market[item],
                                   self.current_location, self.rank):
                    self.display_simple_message(
                        f"Bought {self.format_money(quantity)} {item}. The price here is now "
                        f"{self.format_money(self.current_location.market[item])}.")
                    self.handle_trade('buy')
                else:
                    self.display_simple_message(f"Not enough money for {quantity} {item}.")

            elif action in ['sell', 's']:
                item = commodity_from(self.validate_input(
                    "Sell which? tech/t, agri/a, salt/s, fuel/f: ",
                    [w for name, cuts in COMMODITIES.items() for w in (name,) + cuts]))
                if item is None:
                    return

                if not self.current_location.can_trade(item):
                    self.display_simple_message(f"Trading of {item} is banned on this planet!")
                    return

                quantity = self.validate_quantity_input("Enter quantity to sell (max/m, half/h): ")
                if quantity is None:
                    return

                if quantity == 'max':
                    quantity = self.ship.cargo[item]
                if quantity == 'half':
                    quantity = (self.ship.cargo[item]) // 2

                profit_before = sum(self.ship.trade_profits.values())
                if self.ship.sell(item, quantity, self.current_location.market[item],
                                self.current_location, self.rank):
                    profit = sum(self.ship.trade_profits.values()) - profit_before
                    note = ""
                    # a good deal is worth telling at the bar: a plot point, once a turn
                    if profit >= 5000 and getattr(self, "good_deal_turn", None) != self.turn:
                        self.good_deal_turn = self.turn
                        self.story_manager.plot_points += 1
                        note = " A good deal: +1 plot point."
                    self.display_simple_message(f"Sold {self.format_money(quantity)} {item}, "
                                                f"profit {self.format_money(int(profit))}. The price here is now "
                                                f"{self.format_money(self.current_location.market[item])}.{note}")
                    self.handle_trade('sell')

            elif action in ['upgrade', 'u']:
                property_name = self.validate_input(
                    "Choose property to upgrade (attack/defense/speed/hull): ",
                    ['attack', 'defense', 'speed', 'hull']
                )
                if property_name is None:
                    return
                if property_name == 'hull':
                    self.handle_hull_overhaul()
                    return

                cost = self.ship.upgrade_costs[property_name]
                if self.ship.upgrade(property_name, cost):
                    self.display_simple_message(f"Upgraded {property_name}.")
                    self.ship.upgrade_costs[property_name] = int(cost * 1.5)

            elif action in ['travel', 't']:
                self.handle_travel()

            elif action in ['info', 'i']:
                self.display_location_info()

            elif action in ['build', 'bl']:
                building_costs = {
                    'stockmarket': 5000,
                    'permaculture': 3000,
                    'organic': 4000,
                    'agrobot': 5000,
                    'nanotech': 6000,
                    'neuroengineering': 7000,
                    'mining': 10000,
                    'salt_refinery': 15000,
                    'fuel_refinery': 15000,
                    'combined_refinery': 25000
                }

                valid_options = [
                    'stockmarket', 'sm',
                    'permaculture', 'pc',
                    'organic', 'oc',
                    'agrobot', 'ab',
                    'nanotech', 'nt',
                    'neuroengineering', 'ne',
                    'mining', 'm',
                    'salt refinery', 'sr',
                    'fuel refinery', 'fr',
                    'combined refinery', 'cr'
                ]

                building_name = self.validate_input(
                    "Choose building type: ",
                    valid_options
                )

                if building_name is None:
                    return

                self.handle_building_construction(building_name, building_costs)

            elif action in ['cantina', 'c']:
                self.visit_cantina()

            elif action in ['shop', 'sh']:
                self.visit_shop()

            elif action in ['action', 'a']:
                self.handle_actions()

            elif action in ['mine', 'm']:
                self.handle_mining()

            elif action in ['port', 'p']:
                if port_is_available:
                    self.port_system.handle_port_menu()
                    self.port_system.update_passenger_satisfaction()
                else:
                    self.display_simple_message("No port available at this location.")

            elif action in ['log', 'l']:
                self.story_manager.display_story_progress()
                return    # Return after showing log to avoid counting it as a turn

            elif action in ['journal', 'j']:
                self.story.journal()
                return

            elif action in ['hansa', 'ha']:
                self.handle_hansa()
                return

            elif action in ['help', 'h']:
                self.show_help()
                return

            elif action in ['version', 'v']:
                display_logo(logo_data, centered=True)
                print_centered_text("")
                print_centered_text("Created by Dan Sandner")
                print_centered_text(f"v{VERSION}, ©2025-2026")

                time.sleep(3)
                return

            # Handle quit and resign commands
            elif action in ['quit', 'q']:
                if self.validate_input("Are you sure you want to quit? (yes/no): ", ['yes', 'no']) == 'yes':
                    self.display_simple_message("Thanks for playing!")
                    exit()
                return

            elif action in ['resign', 'rs']:
                if self.validate_input("Are you sure you want to resign? (yes/no): ", ['yes', 'no']) == 'yes':
                    self.display_score()
                    exit()
                return

            elif action in ['hunt', 'hu']:
                if self.handle_hunt():
                    # the hunt took the day: the turn ends without another event
                    if port_is_available:
                        self.port_system.update_passenger_satisfaction()
                    self.turn += 1
                    self.shop.reset_turn()
                    self.autosave()
                return

            elif action in ['end', 'e']:
                # Update passenger satisfaction at end of turn if port is available
                if port_is_available:
                    self.port_system.update_passenger_satisfaction()
                self.turn += 1
                self.random_event()
                self.shop.reset_turn()  # Reset shop state at end of each turn
                self.autosave()
                return

            else:
                self.display_simple_message("Invalid action.")

    # Add passenger event handlers
    def handle_passenger_celebration(self):
        """Handle passenger celebration event"""
        for module in self.ship.passenger_modules:
            for passenger in module.passengers:
                passenger.satisfaction = min(100, passenger.satisfaction + 10)
        self.display_simple_message("Passengers are having a celebration! Satisfaction increased!")

    def handle_passenger_complaint(self):
        """Handle passenger complaint event"""
        for module in self.ship.passenger_modules:
            for passenger in module.passengers:
                passenger.satisfaction = max(0, passenger.satisfaction - 15)
        self.display_simple_message("Passengers have filed complaints! Satisfaction decreased!")

    def handle_medical_emergency(self):
        """Handle medical emergency event"""
        cost = random.randint(500, 1500)
        if self.ship.money >= cost:
            self.ship.money -= cost
            self.display_simple_message(f"Medical emergency handled! Cost: {self.format_money(cost)}")
        else:
            # If can't afford medical care, big satisfaction hit
            for module in self.ship.passenger_modules:
                for passenger in module.passengers:
                    passenger.satisfaction = max(0, passenger.satisfaction - 30)
            self.display_simple_message("Couldn't afford medical care! Passengers very unhappy!")

    def handle_vip_request(self):
        """Handle VIP passenger request"""
        cost = random.randint(1000, 2000)
        if self.ship.money >= cost:
            self.ship.money -= cost
            self.ship.passenger_reputation += 2
            self.display_simple_message(f"VIP request handled! Cost: {self.format_money(cost)}, Reputation increased!")
        else:
            self.ship.passenger_reputation = max(0, self.ship.passenger_reputation - 1)
            self.display_simple_message("Couldn't fulfill VIP request! Reputation decreased!")

    def handle_passenger_trade_info(self):
        """Handle passengers sharing trade information"""
        # Reveal profitable trade opportunities
        self.display_simple_message("Passengers shared valuable trade information!")
        # Implement trade tip functionality here

    def unlock_location_type(self, location_type):
        """Unlock a new type of location and add its instances to available locations"""
        if location_type not in self.unlocked_location_types:
            self.unlocked_location_types.add(location_type)

            # Add locations from hidden pool
            if location_type in self.hidden_locations:
                self.locations.extend(self.hidden_locations[location_type])

                # Display unlock message
                self.display_story_message([
                    f"New {location_type}s Discovered!",
                    "Check your map for new locations to explore.",
                    "",
                    "New trading opportunities await!"
                ])

                # Add specific location effects
                if location_type == "AsteroidBase":
                    self.display_simple_message("Asteroid Bases offer improved mining efficiency!")
                elif location_type == "DeepSpaceOutpost":
                    self.display_simple_message("Deep Space Outposts have unique equipment available!")
                elif location_type == "ResearchColony":
                    self.display_simple_message("Research Colonies provide bonus research points!")

            # Also check chapter-specific locations
            if hasattr(self, 'chapter_locations'):
                for chapter in self.chapter_locations.values():
                    if location_type in chapter:
                        self.locations.extend(chapter[location_type])

    def handle_building_construction(self, building_name, building_costs):
        """Handle building construction with proper capability checking and building process"""
        # Map short commands to full building names and their base types
        building_mapping = {
            'stockmarket': ('stockmarket', 'stockmarket'),
            'sm': ('stockmarket', 'stockmarket'),
            'permaculture': ('Permaculture Paradise', 'permaculture'),
            'pc': ('Permaculture Paradise', 'permaculture'),
            'organic': ('Organic Certification Authority', 'organic'),
            'oc': ('Organic Certification Authority', 'organic'),
            'agrobot': ('Agrobot Assembly Line', 'agrobot'),
            'ab': ('Agrobot Assembly Line', 'agrobot'),
            'nanotech': ('The Nanotech Nexus', 'nanotech'),
            'nt': ('The Nanotech Nexus', 'nanotech'),
            'neuroengineering': ('Neuroengineering Guild', 'neuroengineering'),
            'ne': ('Neuroengineering Guild', 'neuroengineering'),
            'mining': ('Mining Facility', 'mining'),
            'm': ('Mining Facility', 'mining'),
            'salt_refinery': ('Halide Extraction Refinery', 'salt_refinery'),
            'salt refinery': ('Halide Extraction Refinery', 'salt_refinery'),
            'sr': ('Halide Extraction Refinery', 'salt_refinery'),
            'fuel_refinery': ('Plasma Catalysis Refinery', 'fuel_refinery'),
            'fuel refinery': ('Plasma Catalysis Refinery', 'fuel_refinery'),
            'fr': ('Plasma Catalysis Refinery', 'fuel_refinery'),
            'combined_refinery': ('Elemental Fusion Refinery', 'combined_refinery'),
            'combined refinery': ('Elemental Fusion Refinery', 'combined_refinery'),
            'cr': ('Elemental Fusion Refinery', 'combined_refinery')
        }

        if building_name not in building_mapping:
            self.display_simple_message("Invalid building type.")
            return False

        full_building_name, base_type = building_mapping[building_name]

        # Get base cost and calculate final cost
        base_cost = building_costs.get(base_type, 3000)
        cost_multiplier = self.current_location.buildings.count(full_building_name) + 1
        final_cost = base_cost * cost_multiplier

        # Debug info
#        self.display_simple_message(f"Building request: {building_name}")
#        self.display_simple_message(f"Full name: {full_building_name}")
#        self.display_simple_message(f"Base type: {base_type}")
#        self.display_simple_message(f"Location type: {self.current_location.location_type}")
#        self.display_simple_message(f"Available money: {self.format_money(self.ship.money)}")
#        self.display_simple_message(f"Building cost: {self.format_money(final_cost)}")

        # Check if we can afford it
        if self.ship.money < final_cost:
            self.display_simple_message(f"Not enough money. Cost: {self.format_money(final_cost)}")
            return False

        # Deduct money first (will be refunded if build fails)
        self.ship.money -= final_cost

        # Add building directly to location's building list
        self.current_location.buildings.append(full_building_name)
        prices_before = dict(self.current_location.market)

        # Apply building effects
        if full_building_name == "Mining Facility":
            self.current_location.exogeology = min(100, self.current_location.exogeology + 10)
        elif full_building_name == "Permaculture Paradise":
            self.current_location.market['agri'] = max(1, self.current_location.market['agri'] * 0.8)
        elif full_building_name == "Organic Certification Authority":
            self.current_location.market['agri'] = self.current_location.market['agri'] * 1.2
        elif full_building_name == "Agrobot Assembly Line":
            self.current_location.market['agri'] = max(1, self.current_location.market['agri'] * 0.6)
        elif full_building_name == "The Nanotech Nexus":
            self.current_location.market['tech'] = max(1, self.current_location.market['tech'] * 0.85)
            self.current_location.market['agri'] = max(1, self.current_location.market['agri'] * 0.85)
        elif full_building_name == "Neuroengineering Guild":
            self.current_location.market['tech'] = self.current_location.market['tech'] * 1.3
        elif full_building_name == "stockmarket":
            self.current_location.stockmarket_base = True
            self.current_location.market['tech'] = max(1, self.current_location.market['tech'] - 10)
            self.current_location.market['agri'] = max(1, self.current_location.market['agri'] - 5)

        # a building changes what is usual here, not just today's price
        base = self.current_location.equilibrium()
        for good, before in prices_before.items():
            after = self.current_location.market[good]
            if before > 0 and after != before and base.get(good):
                base[good] = round(base[good] * after / before, 1)

        self.display_simple_message(f"Built {full_building_name} for {self.format_money(final_cost)} credits.")
        return True

    def travel_to_location(self, location_name):
        """Handle travel to a new location"""
        # Convert input to lowercase for case-insensitive comparison
        target_name = location_name.lower()

        # Find location by exact name match
        found_location = None
        for location in self.locations:
            if location.name.lower() == target_name:
                found_location = location
                break

        if found_location:
            old_location = self.current_location
            self.current_location = found_location

            # Initialize and update discovered locations
            if not hasattr(self, 'discovered_locations'):
                self.discovered_locations = set([old_location.name])
            first_visit = found_location.name not in self.discovered_locations
            self.discovered_locations.add(found_location.name)

            self.arrive_through_hazard(found_location)
            if first_visit:
                self.story_manager.plot_points += 3
                self.display_simple_message(f"Traveled to {found_location.name}. First visit: +3 plot points.")
            else:
                self.display_simple_message(f"Traveled to {found_location.name}.")

            # Calculate research exchange based on location differences
            research_difference = found_location.research_points - old_location.research_points

            # Base gain is the location's research points if first visit
            if found_location.name not in self.known_locations:
                base_research = found_location.research_points
                self.known_locations.append(found_location.name)
                # Trigger location discovery event
                if hasattr(self, 'location_manager'):
                    self.location_manager.handle_location_discovery(found_location)
            else:
                # For revisits, only get bonus from research difference if positive
                base_research = max(0, research_difference)

            # Apply bonus based on research difference
            if research_difference > 0:
                research_bonus = int(research_difference * 0.2)  # 20% of the difference
            else:
                research_bonus = int(abs(research_difference) * 0.1)  # 10% of the difference

            # Apply rank multiplier to the bonus
            rank_multiplier = {
                "Explorer": 1.0,
                "Pilot": 1.2,
                "Captain": 1.5,
                "Commander": 1.8,
                "Star Commander": 2.2,
                "Space Admiral": 2.5,
                "Stellar Hero": 3.0,
                "Galactic Legend": 3.5
            }.get(self.rank, 1.0)

            # Calculate final research gain
            total_gain = base_research + max(1, int(research_bonus * rank_multiplier * (1 + self.difficulty)))

            # Add research points to the ship (a research module and an analyzer add a share)
            total_gain = int(total_gain * (1 + self.ship.research_bonus()))
            self.ship.research_points += total_gain

            # After successful travel for quest
            self.quest_system.update_from_travel({
                "destination": location_name,
                "turn": self.turn
            })

            # Display informative message about research gain
            if found_location.name not in self.known_locations:
                self.display_simple_message(f"Gained {total_gain} research points from discovering new location!")
            elif research_difference > 0:
                self.display_simple_message(f"Gained {total_gain} research points from clearing orbital junk!")
            else:
                self.display_simple_message(f"Gained {total_gain} research points from salvaged debris!")

            self.turn += 1
            self.shop.reset_turn()
            self.random_event()
            self.autosave()
            return True
        else:
            # More informative error message
            if "navcomp" in self.ship.items:
                self.display_simple_message("Location not found. Known locations:")
                for i, loc in enumerate(self.known_locations, 1):
                    print(f"{i}. {loc}")
            else:
                self.display_simple_message(f"Location '{location_name}' not found or not yet discovered.")
            return False

    def handle_actions(self):
        # Display current research points
        self.display_simple_message(f"Available Research Points: {self.ship.research_points}")

        # Show available actions and their costs
        available_actions = {
            'research': "Research new technologies",
            'scout': f"Scout area (Cost: {self.action.action_costs['scout']} RP)",
            'geoscan': f"Geological scan (Cost: {self.action.action_costs['geoscan']} RP)",
            'revolution': f"Incite revolution (Cost: {self.action.action_costs['revolution']} RP)",
            'manipulate': f"Manipulate market (Cost: {self.action.action_costs['psychodynamics']} RP)",
            'status': "View research status",
            'back': "Return to main menu"
        }

        # Display available actions
        action_content = [["Actions:", "Cost/Description"]]
        for action, description in available_actions.items():
            action_content.append([action, description])
        print(self.create_box(action_content, 'single'))

        # Get user choice
        action = self.validate_input(
            "Choose action type: ",
            list(available_actions.keys())
        )

        if action == 'back':
            return

        if action == 'status':
            self.display_research_status()
            return

        if action == 'research':
            # Get available research options
            options = [opt for opt, cost in self.research.research_costs.items()
                    if opt not in self.research.unlocked_options]

            if not options:
                self.display_simple_message("All research options are unlocked!")
                return

            # Display research options and their costs
            research_content = [["Research Option", "Cost", "Description"]]
            research_descriptions = {
                'xenoeconomy': "Reduces trade taxes",
                'telemetry': "Increases scout success rate",
                'geophysics': "Improves mining efficiency",
                'chronopolitics': "Increases revolution success rate",
                'exogeology': "Increases mining output",
                'psychodynamics': "Allows market price manipulation"
            }

            for opt in options:
                cost = self.research.research_costs[opt]
                desc = research_descriptions.get(opt, "No description available")
                research_content.append([opt, str(cost), desc])

            print(self.create_box(research_content, 'single'))

            option = self.validate_input(
                f"Choose research option ({', '.join(options)}): ",
                options
            )

            if option:
                if self.ship.research_points >= self.research.research_costs[option]:
                    self.ship.research_points -= self.research.research_costs[option]
                    success, message = self.action.research(self.current_location, option, self.research)
                    if success:
                        self.story_manager.plot_points += 4
                        message += " +4 plot points."
                    self.display_simple_message(message)
                else:
                    self.display_simple_message(f"Not enough research points! Need: {self.research.research_costs[option]}")

        elif action == 'scout':
            if self.ship.research_points >= self.action.action_costs['scout']:
                self.ship.research_points -= self.action.action_costs['scout']
                success, type_, value, message = self.action.scout_area(self.current_location, self.research)
                self.display_simple_message(message)

                if success:
                    if type_ == 'item':
                        self.ship.acquire_item(value)
                        self.display_simple_message(f"Item added to inventory!")
                    else:
                        self.current_location.market[type_] += value
                        self.display_simple_message(f"Resources added to market!")
            else:
                self.display_simple_message(f"Not enough research points! Need: {self.action.action_costs['scout']}")

        elif action == 'geoscan':
            if self.ship.research_points >= self.action.action_costs['geoscan']:
                self.ship.research_points -= self.action.action_costs['geoscan']
                success, deposit_type, amount, message = self.action.geoscan(self.current_location, self.research)
                self.display_simple_message(message)

                if success:
                    self.display_simple_message(f"Use 'build mining' command to exploit the deposit.")
            else:
                self.display_simple_message(f"Not enough research points! Need: {self.action.action_costs['geoscan']}")

        elif action == 'revolution':
            if self.ship.research_points >= self.action.action_costs['revolution']:
                self.ship.research_points -= self.action.action_costs['revolution']
                success, new_economy, message = self.action.incite_revolution(self.current_location, self.research)
                self.display_simple_message(message)
            else:
                self.display_simple_message(f"Not enough research points! Need: {self.action.action_costs['revolution']}")

        elif action == 'manipulate':
            if 'psychodynamics' not in self.research.unlocked_options:
                self.display_simple_message("Market manipulation research required!")
                return

            if self.ship.research_points >= self.action.action_costs['psychodynamics']:
                # Show current market prices
                market_content = [["Commodity", "Current Price"]]
                for commodity in ['tech', 'agri', 'salt', 'fuel']:
                    if commodity not in self.current_location.banned_commodities:
                        market_content.append([commodity.capitalize(),
                                        str(self.format_money(self.current_location.market[commodity]))])
                print(self.create_box(market_content, 'single'))

                commodity = self.validate_input(
                    "Choose commodity to manipulate (tech/agri/salt/fuel): ",
                    ['tech', 'agri', 'salt', 'fuel']
                )

                if commodity:
                    self.ship.research_points -= self.action.action_costs['psychodynamics']
                    success, price_change, message = self.action.manipulate_market(
                        self.current_location, commodity, self.research
                    )
                    self.display_simple_message(message)
            else:
                self.display_simple_message(f"Not enough research points! Need: {self.action.action_costs['psychodynamics']}")

        # Update production cooldowns after any action
        for resource_type in list(self.current_location.production_cooldown.keys()):
            if self.current_location.production_cooldown[resource_type] > 0:
                self.current_location.production_cooldown[resource_type] -= 1

    def display_research_status(self):
        """Display current research status and benefits"""
        status_content = [["Research Status", "Benefit"]]

        # Add unlocked research
        if self.research.unlocked_options:
            for research in self.research.unlocked_options:
                benefit = self.get_research_benefit_description(research)
                status_content.append([research, benefit])
        else:
            status_content.append(["No research completed", ""])

        print(self.create_box(status_content, 'double'))
        time.sleep(3)

    def get_research_benefit_description(self, research):
        """Get description of research benefit"""
        benefits = {
            'xenoeconomy': "Trading tax reduced by 2%",
            'telemetry': "Scout success +20%",
            'geophysics': "Mining efficiency +15%",
            'chronopolitics': "Revolution success +20%",
            'exogeology': "Mining output +25%",
            'psychodynamics': "Price control ±10%"
        }
        return benefits.get(research, "Unknown benefit")

    def integrate_event_outcome(self, event_type, outcome, details):
        """Central hub for processing event outcomes and their effects on other systems"""
        # Plot points are no longer handed out here for things that merely happened to the
        # ship: the fight, the situation or the discovery itself pays them when the captain
        # did something (see Game.fight, Game.apply_outcome, handle_exploration_event).

        # Update quest progress using specific details
        if 'cargo_lost' in details:
            self.quest_system.update_cargo_quests(details['cargo_lost'])
        if 'money_lost' in details:
            self.quest_system.update_money_quests(details['money_lost'])
        if 'damage_taken' in details:
            self.quest_system.update_combat_quests(details['damage_taken'])

        # Update location based on specific outcomes
        self.update_location_status(event_type, outcome, details)

        # Update reputation with specific values
        if 'reputation_change' in details:
            self.update_reputation(details['reputation_change'])

    def update_location_status(self, event_type, outcome, details):
        """Update location based on event outcomes with specific details"""
        location = self.current_location

        if event_type == "combat" and outcome == "victory":
            # Use combat details to adjust security
            damage_taken = details.get('damage_taken', 0)
            security_increase = 1 if damage_taken < 20 else 0
            location.security_level = min(10, location.security_level + security_increase)

            # Check equipment unlocks based on combat performance
            if isinstance(location, DeepSpaceOutpost) and damage_taken < 10:
                self.unlock_advanced_equipment()

        elif event_type == "disaster":
            # Use disaster details to affect economy
            damage_amount = details.get('damage_taken', 0)
            cargo_lost = details.get('cargo_lost', {})

            if damage_amount > 30 or sum(cargo_lost.values()) > 100:
                location.economy = "Declining"
                self.display_simple_message(f"Major disaster has affected {location.name}'s economy!")

    def update_reputation(self, reputation_change):
        """Update player reputation based on event outcomes"""
        self.reputation = max(0, min(100, self.reputation + reputation_change))

        # Update rank based on reputation and other factors
        self.update_rank()

        # Display reputation change if significant
        if abs(reputation_change) >= 2:
            if reputation_change > 0:
                self.display_simple_message(f"Reputation increased by {reputation_change}!")
            else:
                self.display_simple_message(f"Reputation decreased by {abs(reputation_change)}!")

        # Check for rank-up
        current_rank = self.rank
        self.update_rank()
        if self.rank != current_rank:
            self.display_simple_message(f"Congratulations! You've been promoted to {self.rank}!")

            # Apply rank-up bonuses
            rank_bonuses = {
                "Pilot": {"money": 5000, "research_points": 50},
                "Captain": {"money": 10000, "research_points": 100},
                "Commander": {"money": 20000, "research_points": 200},
                "Star Commander": {"money": 40000, "research_points": 400},
                "Space Admiral": {"money": 80000, "research_points": 800},
                "Stellar Hero": {"money": 160000, "research_points": 1600},
                "Galactic Legend": {"money": 320000, "research_points": 3200}
            }

            if self.rank in rank_bonuses:
                bonus = rank_bonuses[self.rank]
                self.ship.money += bonus["money"]
                self.ship.research_points += bonus["research_points"]
                self.display_simple_message([
                    f"Rank-up Bonus:",
                    f"• {self.format_money(bonus['money'])} credits",
                    f"• {bonus['research_points']} research points"
                ])

    def random_event(self):
        """Enhanced random event handler with complete implementation"""
        # some turns nothing happens: more of them on an easy game
        if random.random() > self.LANE_ACTIVITY.get(self.difficulty, 0.85):
            return

        # Add character encounter chance first
        if random.random() < 0.15:  # 15% chance for character encounter
            self.character_encounters.trigger_random_encounter("Space")
            return  # Return to avoid multiple events per turn

        # Add passenger-related events
        if hasattr(self.ship, 'passenger_modules') and any(m.passengers for m in self.ship.passenger_modules):
            # 10% chance of passenger event if carrying passengers
            if random.random() < 0.1:
                passenger_events = [
                    "Passenger celebration boosts morale!",
                    "Passenger complaint about accommodations!",
                    "Medical emergency with passenger!",
                    "VIP passenger requests special treatment!",
                    "Passengers share valuable trade information!"
                ]
                event = random.choice(passenger_events)

                if "celebration" in event:
                    self.handle_passenger_celebration()
                elif "complaint" in event:
                    self.handle_passenger_complaint()
                elif "medical" in event:
                    self.handle_medical_emergency()
                elif "VIP" in event:
                    self.handle_vip_request()
                elif "trade" in event:
                    self.handle_passenger_trade_info()

        # Define all possible events with their categories (fights and situations: see ENEMIES, SITUATIONS)
        events = {
            "combat": [self.pick_enemy()],
            "situation": sorted(SITUATIONS),
            "trade": [
                "Market crash!",
                "Trade embargo!",
                "Resource shortage!",
                "Price manipulation!",
                "Trade route disruption!",
                "Black market emergence!"
            ],
            "exploration": [
                "Spacetime rift!",
                "Gravitational anomaly!",
                "Mysterious signal!",
                "Quantum fluctuation!",
                "Ancient ruins!",
                "Alien artifact!"
            ],
            "disaster": [
                "Asteroid impact!",
                "Solar flare!",
                "Equipment malfunction!",
                "Hull breach!",
                "Reactor leak!",
                "Navigation failure!"
            ]
        }

        # Calculate probabilities based on location type
        location_modifiers = {
            "Planet": {"combat": 1.0, "situation": 1.2, "trade": 1.0, "exploration": 1.0, "disaster": 0.5},
            "AsteroidBase": {"combat": 1.2, "situation": 1.2, "trade": 0.8, "exploration": 1.1, "disaster": 0.7},
            "DeepSpaceOutpost": {"combat": 1.3, "situation": 1.3, "trade": 0.7, "exploration": 1.2, "disaster": 0.6},
            "ResearchColony": {"combat": 0.7, "situation": 1.1, "trade": 0.9, "exploration": 1.4, "disaster": 0.5}
        }

        # Get location-specific modifiers
        location_type = self.current_location.location_type
        modifiers = location_modifiers.get(location_type, location_modifiers["Planet"])

        # Select event category based on modifiers
        categories = list(events.keys())
        weights = [modifiers[cat] for cat in categories]
        category = random.choices(categories, weights=weights)[0]
        event = random.choice(events[category])

        # Record event
        event_result = {
            "type": category,
            "name": ENEMIES[event]["name"] if category == "combat" else event,
            "location": self.current_location.name,
            "turn": self.turn
        }
        before = self.event_before()

        # Handle event based on category
        if category == "combat":
            self.handle_combat_event(event)
        elif category == "situation":
            self.situation(event)
        elif category == "trade":
            self.handle_trade_event(event)
        elif category == "exploration":
            self.handle_exploration_event(event)
        elif category == "disaster":
            self.handle_disaster_event(event)

        # Process event outcome
        outcome_details = self.process_event_outcome(event_result, before)

        # Integrate with other systems
        self.integrate_event_outcome(
            event_result["type"],
            outcome_details["outcome"],
            outcome_details
        )

        # Check for special location events
        self.check_location_events(event_result["type"])

        # Update quest status
        self.quest_system.check_event_requirements(event_result)

        # Generate new quest if appropriate
        if random.random() < 0.2:  # 20% chance for event-based quest
            quest = self.generate_event_quest(event_result, outcome_details)
            if quest:
                self.quest_system.add_quest(quest)

        # Update story progression if applicable
        self.story_manager.check_event_trigger(event, self)

    def generate_event_quest(self, event_result, outcome_details):
        """Generate a quest based on event outcome"""
        event_type = event_result["type"]
        quest = None

        if event_type == "combat":
            if outcome_details["outcome"] == "victory":
                quest_templates = [
                    {
                        "name": "Pirate Hunter",
                        "description": "Eliminate more pirates in this sector",
                        "reward_money": 2000,
                        "reward_rp": 50,
                        "quest_type": "combat",
                        "requirements": {"enemy_type": "pirate", "victories": 3}
                    },
                    {
                        "name": "System Defender",
                        "description": "Protect local trade routes",
                        "reward_money": 3000,
                        "reward_rp": 75,
                        "quest_type": "patrol",
                        "requirements": {"patrol_turns": 5}
                    }
                ]
                template = random.choice(quest_templates)
                quest = Quest(
                    name=template["name"],
                    description=template["description"],
                    reward_money=template["reward_money"],
                    reward_rp=template["reward_rp"],
                    quest_type=template["quest_type"],
                    requirements=template["requirements"]
                )

        elif event_type == "trade":
            if "market crash" in event_result["name"].lower().replace("_", " "):
                quest = Quest(
                    name="Market Stabilizer",
                    description="Help stabilize local market prices",
                    reward_money=4000,
                    reward_rp=60,
                    quest_type="trade",
                    requirements={"trades": 5, "min_profit": 1000}
                )

        elif event_type == "exploration":
            if "artifact" in event_result["name"].lower() or "ruins" in event_result["name"].lower():
                quest = Quest(
                    name="Ancient Mysteries",
                    description="Investigate more ancient sites",
                    reward_money=5000,
                    reward_rp=100,
                    quest_type="exploration",
                    requirements={"discoveries": 2}
                )

        elif event_type == "disaster":
            if outcome_details["outcome"] == "survived":
                quest = Quest(
                    name="Emergency Response",
                    description="Help other ships in distress",
                    reward_money=3500,
                    reward_rp=80,
                    quest_type="rescue",
                    requirements={"rescues": 2}
                )

        # Apply modifiers based on game progress
        if quest:
            # Scale rewards based on current chapter
            chapter_multiplier = 1 + (self.story_manager.get_chapter_number() * 0.2)
            quest.reward_money = int(quest.reward_money * chapter_multiplier)
            quest.reward_rp = int(quest.reward_rp * chapter_multiplier)

            # Scale difficulty based on player rank
            rank_multipliers = {
                "Explorer": 1.0,
                "Pilot": 1.2,
                "Captain": 1.5,
                "Commander": 1.8,
                "Star Commander": 2.0,
                "Space Admiral": 2.5,
                "Stellar Hero": 3.0,
                "Galactic Legend": 3.5
            }

            # Update requirements if they exist
            if hasattr(quest, "requirements") and "victories" in quest.requirements:
                quest.requirements["victories"] = int(
                    quest.requirements["victories"] * rank_multipliers.get(self.rank, 1.0)
                )

        return quest

    def check_location_events(self, event_type):
        """Handle location-specific event consequences"""
        location = self.current_location

        if isinstance(location, AsteroidBase):
            if event_type == "disaster":
                # Asteroid bases might discover new mining opportunities after disasters
                if random.random() < 0.2:
                    mineral_type = random.choice(["salt", "fuel"])
                    amount = random.randint(1000, 3000)
                    location.mineral_deposits[mineral_type] = location.mineral_deposits.get(mineral_type, 0) + amount
                    self.display_simple_message(f"The disaster revealed new {mineral_type} deposits!")

        elif isinstance(location, ResearchColony):
            if event_type == "exploration":
                # Research colonies might gain research points from exploration events
                bonus_points = random.randint(10, 30)
                self.ship.research_points += bonus_points
                self.display_simple_message(f"Colony researchers analyzed the phenomenon: +{bonus_points} RP")

    def event_before(self):
        """The ship before an event, so its outcome can be judged afterwards."""
        self.last_fight = None
        return {
            "location": self.current_location.name,
            "location_type": self.current_location.location_type,
            "initial_damage": self.ship.damage,
            "cargo_before": dict(self.ship.cargo),
            "money_before": self.ship.money,
            "timestamp": self.turn
        }

    def process_event_outcome(self, event_result, before=None):
        """Process and categorize event outcomes with detailed information"""
        details = dict(before or self.event_before())

        # Calculate specific event impacts
        if event_result["type"] == "combat":
            damage_taken = self.ship.damage - details["initial_damage"]
            details["damage_taken"] = damage_taken
            details["outcome"] = getattr(self, "last_fight", None) or "escaped"
            details["reputation_change"] = {"victory": 2, "defeat": -1}.get(details["outcome"], 0)

        elif event_result["type"] == "situation":
            details["outcome"] = "handled"
            details["reputation_change"] = 0

        elif event_result["type"] == "trade":
            money_change = self.ship.money - details["money_before"]
            details["money_change"] = money_change
            details["outcome"] = "success" if money_change > 0 else "loss"
            details["reputation_change"] = 1 if money_change > 0 else -1

        elif event_result["type"] == "exploration":
            if "artifact" in event_result["name"].lower() or "ruins" in event_result["name"].lower():
                details["outcome"] = "discovery"
                details["reputation_change"] = 2
            else:
                details["outcome"] = "completed"
                details["reputation_change"] = 1

        elif event_result["type"] == "disaster":
            damage_taken = self.ship.damage - details["initial_damage"]
            details["damage_taken"] = damage_taken
            details["outcome"] = "major_damage" if damage_taken > 40 else "survived"
            details["reputation_change"] = 1 if damage_taken < 20 else -1

        # Calculate specific losses
        details["cargo_lost"] = {
            item: details["cargo_before"][item] - self.ship.cargo[item]
            for item in self.ship.cargo
            if details["cargo_before"][item] > self.ship.cargo[item]
        }

        # Calculate money lost and add it to combat damage details
        money_lost = max(0, details["money_before"] - self.ship.money)
        if event_result["type"] == "combat":
            details["money_lost"] = money_lost

        # Also add money_lost to trade event details
        elif event_result["type"] == "trade" and money_lost > 0:
            details["money_lost"] = money_lost
            details["outcome"] = "loss"  # Override outcome if money was lost

        # For other events, still track money_lost
        else:
            details["money_lost"] = money_lost

        return details

    # --- markets that remember, and the Hansa ---------------------------------------
    def affordable(self, item, tax_rate, room):
        """The largest load of `item` the money covers here, price movement and tax included."""
        loc = self.current_location
        low, high = 0, room
        while low < high:
            mid = (low + high + 1) // 2
            if mid * loc.trade_price(item, mid, selling=False) * (1 + tax_rate) <= self.ship.money:
                low = mid
            else:
                high = mid - 1
        return low

    def new_turn(self):
        """Things that happen once a turn, whatever the captain does: markets recover,
        prices here are noted, the Hansa's dues fall due."""
        if getattr(self, "ticked_turn", None) == self.turn:
            return
        first = getattr(self, "ticked_turn", None) is None
        self.ticked_turn = self.turn
        if not first:
            for loc in self.locations:
                loc.recover()
        self.note_prices()
        if self.turn and self.turn % self.DUES_EVERY == 0 and getattr(self, "dues_turn", None) != self.turn:
            self.dues_turn = self.turn
            self.collect_dues()

    def note_prices(self, loc=None):
        loc = loc or self.current_location
        self.__dict__.setdefault("prices_seen", {})[loc.name] = (self.turn, dict(loc.market))

    def forecast(self, loc):
        """What a broker would guess {good: (price, spread)} for a place: close for a dock
        seen this turn, looser the older the news, a rough guess for a dock never seen."""
        seen = getattr(self, "prices_seen", {}).get(loc.name)
        if seen and seen[0] == self.turn:
            return {good: (price, 0.0) for good, price in loc.market.items()}, 0
        age = self.turn - seen[0] if seen else None
        spread = 0.45 if age is None else min(0.35, 0.04 + 0.03 * age)
        if "broker" in self.ship.crew:
            spread /= 2
        if self.story_flag("harp_relay"):        # the quantum harp carries prices between the stars
            spread /= 2
        rng = random.Random(zlib.crc32(("%s/%d/%s" % (loc.name, self.turn, self.player_name)).encode()))
        guess = {}
        for good, price in loc.market.items():
            if price <= 0:
                guess[good] = (0, 0.0)
                continue
            truth = price if seen else loc.equilibrium().get(good, price)
            error = max(-spread, min(spread, rng.gauss(0, spread / 2)))
            guess[good] = (max(1, truth * (1 + error)), spread)
        return guess, age

    def show_forecast(self, who):
        """Price guesses for the other docks the captain knows of."""
        rows = [[who], [""]]
        for loc in self.locations:
            if loc.name not in self.known_locations or loc is self.current_location:
                continue
            guess, age = self.forecast(loc)
            note = "never visited: a guess" if age is None else "seen %d turn%s ago" % (age, "" if age == 1 else "s")
            rows.append(["%s (%s)" % (loc.name, note)])
            parts = []
            for good in ('tech', 'agri', 'salt', 'fuel'):
                price, spread = guess.get(good, (0, 0))
                if price > 0:
                    word = "~" if spread < 0.15 else "about " if spread < 0.3 else "maybe "
                    parts.append("%s %s%s" % (good, word, self.format_money(price)))
            rows.append(["  " + (", ".join(parts) or "no market")])
        rows.append([""])
        rows.extend([line] for line in self.word_wrap(
            "Fresh news is close; old news drifts; places you never saw are guesses. Big loads move prices, "
            "and prices take a few weeks to recover."))
        print(self.create_box(rows, 'double'))
        input("Press Enter to continue...")

    # The Hansa runs the convoys between stars. Every ten turns it charges convoy dues, and the
    # dues grow; Hansa bonds lower them. Unpaid dues gather a surcharge and the convoy master
    # takes cargo for them.
    DUES_EVERY = 10

    def dues(self):
        periods = self.turn // self.DUES_EVERY
        hike = getattr(self, "dues_hike", 1.0) if self.turn <= getattr(self, "dues_hike_until", 0) else 1.0
        due = 600 * periods ** 1.35 * hike
        return int(due * 0.88 ** getattr(self, "hansa_bonds", 0))

    def bond_price(self):
        return int(4000 * 1.15 ** getattr(self, "hansa_bonds", 0))

    def collect_dues(self):
        ship = self.ship
        due = self.dues() + getattr(self, "dues_arrears", 0)
        paid = min(due, max(0, int(ship.money)))
        ship.money -= paid
        owed = due - paid
        lines = ["Hansa convoy dues: %s." % self.format_money(due)]
        if owed <= 0:
            self.dues_arrears = 0
            lines.append("Paid. The convoy master stamps your berth card.")
            color = '33'
        else:
            owed = int(owed * 1.1)
            lines.append("You could pay %s. %s stays on the books, with a ten per cent surcharge." % (
                self.format_money(paid), self.format_money(owed)))
            # the convoy master takes cargo for what is owed
            for good in ('tech', 'agri', 'salt', 'fuel'):
                if owed <= 0 or ship.cargo[good] <= 0:
                    continue
                price = max(1, self.current_location.market.get(good, 0) or 20)
                taken = min(ship.cargo[good], int(owed / price) + 1)
                ship.cargo[good] -= taken
                owed -= int(taken * price)
                lines.append("The convoy master takes %d %s against the debt." % (taken, good))
            self.dues_arrears = max(0, owed)
            ship.passenger_reputation -= 3
            lines.append("Word gets round: reputation -3.")
            color = '31'
        lines.append("Next dues in %d turns: about %s. Bonds lower them (hansa/ha)." % (
            self.DUES_EVERY, self.format_money(self.dues_at(self.turn + self.DUES_EVERY))))
        self.display_simple_message([line for text in lines for line in self.word_wrap(text)], 3, color=color)

    def dues_at(self, turn):
        now = self.turn
        self.turn = turn
        try:
            return self.dues()
        finally:
            self.turn = now

    def buy_bonds(self, count=1, announce=True):
        bought = 0
        for _ in range(count):
            price = self.bond_price()
            if self.ship.money < price:
                break
            self.ship.money -= price
            self.hansa_bonds = getattr(self, "hansa_bonds", 0) + 1
            self.bonds_paid = getattr(self, "bonds_paid", 0) + price
            bought += 1
        if announce and bought:
            self.display_simple_message("Bought %d Hansa bond%s. You hold %d; dues are %d%% lower." % (
                bought, "" if bought == 1 else "s", self.hansa_bonds, round(100 * (1 - 0.88 ** self.hansa_bonds))))
        return bought

    def sell_bonds(self):
        """Cash the bonds in at what they cost (the Hansa buys back at face value)."""
        held = getattr(self, "hansa_bonds", 0)
        value = getattr(self, "bonds_paid", 0)
        self.hansa_bonds, self.bonds_paid = 0, 0
        self.ship.money += value
        return held, value

    def handle_hansa(self):
        """The Hansa terminal: dues, bonds, and the convoy office's price board."""
        while True:
            bonds = getattr(self, "hansa_bonds", 0)
            next_turn = (self.turn // self.DUES_EVERY + 1) * self.DUES_EVERY
            rows = [["Hansa terminal - " + self.current_location.name], [""]]
            for text in (
                    "The Hansa runs the convoys between the stars. Every %d turns it charges convoy dues, "
                    "and the dues go up as the routes get busier." % self.DUES_EVERY,
                    "Next dues at turn %d: %s.%s" % (next_turn, self.format_money(self.dues_at(next_turn)),
                                                     (" Owed from before: %s." % self.format_money(self.dues_arrears))
                                                     if getattr(self, "dues_arrears", 0) else ""),
                    "Bonds held: %d (dues %d%% lower). The next bond costs %s and takes another 12%% off." % (
                        bonds, round(100 * (1 - 0.88 ** bonds)), self.format_money(self.bond_price()))):
                rows.extend([line] for line in self.word_wrap(text))
                rows.append([""])
            rows.extend([["bond/b: buy a bond"], ["prices/p: the convoy office's price board"],
                         ["pay/pd: pay what you owe now"]])
            print(self.create_box(rows, 'double'))
            action = self.validate_input("Hansa - choose (Enter to leave): ", ['bond', 'b', 'prices', 'p', 'pay', 'pd'])
            if action is None:
                return
            if action in ('bond', 'b'):
                if not self.buy_bonds(1):
                    self.display_simple_message("Not enough money for a bond (%s)." % self.format_money(self.bond_price()))
            elif action in ('prices', 'p'):
                self.show_forecast("The convoy office's price board")
            elif action in ('pay', 'pd'):
                owed = getattr(self, "dues_arrears", 0)
                paid = min(owed, int(self.ship.money))
                self.ship.money -= paid
                self.dues_arrears = owed - paid
                self.display_simple_message("Paid %s. Still owed: %s." % (
                    self.format_money(paid), self.format_money(self.dues_arrears)))

    # --- encounters: fights, bounties and situations between docks ------------------
    WANTED_NAMES = ["Lucky Nine", "Widow's Tax", "Second Opinion", "Unpaid Invoice", "Small Print",
                    "Overdraft", "Bad Penny", "Quiet Word", "Last Orders", "Due Diligence", "Rust Never",
                    "Grandmother's Revenge", "Fine Print", "Late Fee", "No Refunds", "Sunday Best"]

    # Lanes that wear a hull: (hull class that rides them out, damage range otherwise)
    ROUGH_PLACES = ("DeepSpaceOutpost", "Ancient Ruins", "Alien Signal Research Outpost")
    DEEP_PLACES = ("Stator Field Megastructure", "Builder Site", "Zeta", "Eta", "Theta", "Omega-1", "DSO-Delta")

    def lane_hazard(self, loc):
        """How hard the way to `loc` is on a hull: 0 easy, 1 rough, 2 deep."""
        if loc.name in self.DEEP_PLACES:
            return 2
        if loc.location_type in self.ROUGH_PLACES:
            return 1
        return 0

    def arrive_through_hazard(self, loc):
        """A hull too light for the lane takes a beating on the way."""
        need = self.lane_hazard(loc)
        hull = self.ship.hull
        if need <= hull:
            return
        low, high = (10, 20) if need == 1 else ((20, 35) if hull == 1 else (30, 45))
        hit = random.randint(low, high)
        self.ship.damage = min(99, self.ship.damage + hit)
        lines = ["The way to %s is %s, and the %s was not built for it: hull damage +%d%%." % (
            loc.name, "rough" if need == 1 else "deep and empty", self.ship.hull_info()["name"].lower(), hit)]
        if random.random() < 0.3:
            goods = [g for g in ('tech', 'agri', 'salt', 'fuel') if self.ship.cargo[g] > 0]
            if goods:
                good = random.choice(goods)
                lost = max(1, self.ship.cargo[good] // 10)
                self.ship.cargo[good] -= lost
                lines.append("A hold seal gives: %d %s lost." % (lost, good))
        lines.append("An %s hull (planet shipyards, upgrade/u, hull) would ride it out." % (
            "Ironback or Farstrider" if need == 1 else "Farstrider"))
        self.display_simple_message([line for text in lines for line in self.word_wrap(text)], 3, color='31')

    def handle_hull_overhaul(self):
        """A planet's shipyard rebuilds the ship on a heavier hull."""
        ship = self.ship
        if not isinstance(self.current_location, Planet):
            self.display_simple_message("Only a planet's shipyard can overhaul a hull.")
            return False
        if ship.hull + 1 >= len(ship.HULLS):
            self.display_simple_message("The %s is the best hull any yard here builds." % ship.hull_info()["name"])
            return False
        nxt = ship.HULLS[ship.hull + 1]
        rows = [["Shipyard - " + self.current_location.name], [""]]
        rows.extend([line] for line in self.word_wrap("Now: %s, %s." % (ship.hull_info()["name"], ship.hull_info()["about"])))
        rows.append([""])
        rows.extend([line] for line in self.word_wrap(
            "Overhaul to %s for %s: %s. Defense +%d, attack +%d, hold +%d%%. Repairs cost %d credits a point "
            "of damage (now %d)." % (nxt["name"], self.format_money(nxt["price"]), nxt["about"], nxt["defense"],
                                    nxt["attack"], int(nxt["hold"] * 100), nxt["repair"], ship.hull_info()["repair"])))
        print(self.create_box(rows, 'double'))
        if self.validate_input("Overhaul the hull? (yes/no): ", ['yes', 'no', 'y', 'n']) not in ('yes', 'y'):
            return False
        if ship.money < nxt["price"]:
            self.display_simple_message("Not enough money: the yard wants %s." % self.format_money(nxt["price"]))
            return False
        ship.money -= nxt["price"]
        ship.hull += 1
        ship.damage = 0
        self.story_manager.plot_points += 5
        self.display_simple_message("The yard takes your ship apart and gives you back a %s. +5 plot points." %
                                    nxt["name"], 3, color='32')
        return True

    def wealth_tier(self):
        """0-3: how much the lanes have heard this captain is worth."""
        money = self.ship.money
        return 3 if money >= 2000000 else 2 if money >= 500000 else 1 if money >= 100000 else 0

    def danger_tier(self):
        """How dangerous the lanes are for this captain (1-7): it grows with time, guns and
        money (pirates read bank gossip too), and with the difficulty."""
        tier = 1 + self.turn // 50 + self.ship.fight_attack() // 3 + self.wealth_tier() + (self.difficulty - 1)
        return max(1, min(7, tier))

    def fight_chance(self, power, edge=0):
        chance = 0.55 + 0.12 * (self.ship.fight_attack() + edge - power)
        if self.ship.items.get("turrets"):
            chance += 0.08
        return max(0.08, min(0.95, chance))

    def escape_chance(self, enemy):
        chance = 0.4 + 0.1 * (self.ship.speed + (2 if self.ship.items.get("quantum_drive") else 0) - enemy["speed"])
        if "navigator" in self.ship.crew:
            chance += 0.15
        return max(0.05, min(0.95, chance))

    def pick_enemy(self, power=None):
        """An enemy for this place and moment: near the danger tier, or of the given power."""
        if power is None:
            tier = self.danger_tier()
            pool = [e for e, d in ENEMIES.items() if tier - 2 <= d["power"] <= tier]
        else:
            pool = [e for e, d in ENEMIES.items() if d["power"] == power and d["deal"] != "toll"]
        pool = [e for e in pool if not ENEMIES[e].get("after") or self.story_flag(ENEMIES[e]["after"])]
        return random.choice(pool or ["skiff"])

    def crew_name(self, role):
        person = story_data()["characters"].get(role) or {}
        return person.get("short") or person.get("name") or role

    def ask_move(self, title, lines, options, default):
        """Show a moment and its options; return the key of the option taken."""
        box = [title, ""]
        for line in lines:
            box.extend(self.word_wrap(line))
        box.append("")
        for number, (_key, label) in enumerate(options, 1):
            box.extend(self.option_lines(number, label))
        self.display_story_message(box, pause=0)
        self.move_options, self.move_title = options, title   # what a reader of the screen sees (tools/bot.py)
        answer = self.validate_input("Your move (1-%d, Enter = %d): " % (len(options), default),
                                     [str(i) for i in range(1, len(options) + 1)])
        self.move_options = None
        return options[int(answer or default) - 1][0]

    # Friends who come when called: (story flag, character, edge in the fight, turns between calls)
    ALLIES = {"convoy": ("convoy_friend", "convoy_captain", 3, 15), "pell": ("pell_friend", "young_hauler", 1, 8)}

    def story_flag(self, *flags):
        states = self.story_manager.story_states
        return any(states.get(flag) for flag in flags)

    def encounter(self, enemy_id, bounty=0, hunted=False, edge=0):
        """A fight, or the threat of one. The captain picks how to meet it. `edge` is help the
        story brings (allies at a climax). Returns 'victory', 'defeat', 'escaped', 'paid' or 'talked'."""
        enemy = ENEMIES[enemy_id]
        ship = self.ship
        power = enemy["power"]
        options = [("fight", "Fight (%s)" % odds_word(self.fight_chance(power, edge)))]
        used = self.__dict__.setdefault("allies_called", {})
        for ally, (flag, who, help_, every) in self.ALLIES.items():
            if self.story_flag(flag) and self.turn - used.get(ally, -10 ** 6) >= every:
                options.append(("ally:" + ally, "Call %s (%s)" % (
                    self.crew_name(who) + ("'s convoy" if ally == "convoy" else "'s skiff"),
                    odds_word(self.fight_chance(power, edge + help_)))))
        if not hunted and enemy["kind"] == "pirate" and power <= 5 and self.story_flag("mraz_spared", "mraz_protection"):
            options.append(("mraz", "Drop %s's name" % self.crew_name("pirate_captain")))
        if enemy_id == "cultists" and self.story_flag("carried_the_pilgrims"):
            options.append(("pilgrims", "The pilgrims you carried vouch for you"))
        if enemy_id == "customs" and self.story_flag("lauritz_trust", "lauritz_courier"):
            options.append(("lauritz", "%s vouches for you on the channel" % self.crew_name("inspector")))
        tricks = [t for t in FIGHT_TRICKS
                  if ship.items.get(t) and (t in enemy.get("tricks", []) or t in ("advanced_radar", "combat_drone"))]
        tricks.sort(key=lambda t: -FIGHT_TRICKS[t][1]["edge"])
        for trick in tricks[:2]:
            label, effect = FIGHT_TRICKS[trick]
            options.append(("trick:" + trick, "%s (%s)" % (label, odds_word(self.fight_chance(power, edge + effect["edge"])))))
        if enemy_id == "harvester" and ship.cargo["agri"] >= 10:
            options.append(("feed", "Throw it a crate of agri"))
        if enemy_id == "cultists" and ship.damage >= 25:
            options.append(("holy", "Show them your battered hull"))
        if not hunted:
            if enemy["deal"] in ("pay", "toll"):
                price = self.toll_for(enemy)
                options.append(("pay", "%s (%s)" % ("Pay the fee" if enemy["deal"] == "toll" else "Pay them off",
                                                    self.format_money(price))))
            if enemy["deal"] == "toll" and ship.items.get("cargo_scanner"):
                options.append(("scan", "Hand over a clean cargo scan"))
            if enemy["deal"] == "talk":
                options.append(("talk", "Talk them down (%s)" % odds_word(self.talk_chance())))
            if enemy["deal"] == "tithe" and any(ship.cargo.values()):
                options.append(("tithe", "Give them a container: a third of your fullest hold"))
            if ship.items.get("advanced_radar"):
                options.append(("slip", "Radar: slip away before they lock on"))
        if ship.items.get("emergency_warp"):
            options.append(("warp", "Emergency jump"))
        options.append(("run", "%s (%s)" % ("Break off" if hunted else "Run for it",
                                            odds_word(self.escape_chance(enemy)))))

        title = "%s (threat %d)" % (enemy["name"], power)
        if hunted:
            title = "Bounty: " + title
        lines = [enemy["text"]]
        if not hunted and self.wealth_tier() and enemy["deal"] in ("pay", "talk"):
            lines.append(random.choice(["They have heard what you are worth.",
                                        "Somebody sold them your bank balance. It was not cheap.",
                                        "Rich captains get the better class of pirate."]))
        move = self.ask_move(title, lines, options, 1)

        if move == "tithe":
            good = max(('tech', 'agri', 'salt', 'fuel'), key=lambda g: ship.cargo[g])
            taken = max(1, ship.cargo[good] // 3)
            ship.cargo[good] -= taken
            return self.after_fight("paid", ["Sister Tare weighs %d %s, subtracts the container, and gives you a receipt: "
                                             "'clean lading'. They go, singing." % (taken, good)], '33')
        if move == "mraz":
            return self.after_fight("talked", ["You mention %s. The channel goes quiet, then a voice says "
                                               "'Sorry, captain. Didn't see the name.' They leave." %
                                               self.crew_name("pirate_captain")], '32')
        if move == "pilgrims":
            return self.after_fight("talked", ["The cultists recognise the ship that carried their pilgrims. "
                                               "They bless your airlock and go."], '32')
        if move == "lauritz":
            return self.after_fight("talked", ["%s comes on the channel, reads out your inspection record, "
                                               "and the cutter waves you through." % self.crew_name("inspector")], '32')
        if move.startswith("ally:"):
            ally = move[5:]
            flag, who, help_, every = self.ALLIES[ally]
            used[ally] = self.turn
            text = ("Forty haulers come up the lane in close order, %s's tug at the front." if ally == "convoy"
                    else "%s's skiff cuts across their bow, guns hot.") % self.crew_name(who)
            return self.fight(enemy_id, bounty, [text], edge + help_)
        if move == "pay":
            price = self.toll_for(enemy)
            ship.money -= price
            return self.after_fight("paid", ["You pay %s. They take it and go." % self.format_money(price)], '33')
        if move == "scan":
            self.ship.passenger_reputation += 1
            return self.after_fight("talked", ["The cutter reads your scan, finds nothing to fine, and waves you on."], '32')
        if move == "talk":
            if random.random() < self.talk_chance():
                return self.after_fight("talked", ["Your reputation arrives before you do. They let you pass."], '32')
            return self.fight(enemy_id, bounty, ["They are not in a talking mood."], edge)
        if move == "feed":
            ship.cargo["agri"] -= 10
            return self.after_fight("talked", ["The harvester eats the crate, crate and all, and wanders off content."], '32')
        if move == "holy":
            ship.research_points += 10
            return self.after_fight("talked", ["The cultists see your hull and fall silent. They bless it, weld a "
                                               "tin medal to the airlock and leave. +10 RP"], '32')
        if move in ("slip", "warp"):
            if move == "warp":
                ship.damage = min(99, ship.damage + 3)
            text = "The radar saw them first: you are gone before they lock on." if move == "slip" \
                else "One lurch, one headache, and they are a long way behind you."
            return self.after_fight("escaped", [text], '32')
        if move == "run":
            if random.random() < self.escape_chance(enemy):
                return self.after_fight("escaped", ["You open the throttle and leave them behind."], '33')
            return self.fight(enemy_id, bounty, ["They catch you."], edge - 1)
        shield = 1.0
        if move.startswith("trick:"):
            effect = FIGHT_TRICKS[move[6:]][1]
            edge, shield = edge + effect["edge"], effect.get("shield", 1.0)
        return self.fight(enemy_id, bounty, [], edge, shield)

    def toll_for(self, enemy):
        """What they want to go away: a share of the money aboard, a bigger share from the rich."""
        share = (0.03 if enemy["deal"] == "toll" else 0.06) + 0.015 * self.wealth_tier()
        cap = 1500 * enemy["power"] * (1 + 2 * self.wealth_tier())
        return int(max(150 * enemy["power"], min(self.ship.money * share, cap)))

    def talk_chance(self):
        return max(0.1, min(0.9, 0.15 + self.ship.passenger_reputation / 120))

    def fight(self, enemy_id, bounty, lines, edge=0, shield=1.0):
        enemy = ENEMIES[enemy_id]
        ship = self.ship
        power = enemy["power"]
        won = random.random() < self.fight_chance(power, edge)
        hit = random.randint(4, 9) * power / ship.fight_defense() * (1 + self.difficulty) * shield
        if not won:
            hit *= 2.2
        if ship.items.get("shield"):
            hit *= 0.7
        if ship.items.get("armor"):
            hit *= 0.8
        before = ship.damage
        ship.damage = min(99, int(ship.damage + hit))
        if ship.items.get("patcher"):
            ship.damage = max(0, ship.damage - 10)
        if "mechanic" in ship.crew:
            ship.damage = max(0, ship.damage - 5)
        if ship.damage > before:
            lines.append("Hull damage +%d%%." % (ship.damage - before))

        if won:
            ship.record_combat_victory(enemy["kind"])
            money = int(random.randint(150, 350) * power) + bounty
            research = int(random.randint(4, 10) * power * (1 + ship.research_bonus()))
            plot = 1 + power // 3
            ship.money += money
            ship.research_points += research
            self.story_manager.plot_points += plot
            lines.append("Victory! +%s credits%s, +%d RP, +%d plot points." % (
                self.format_money(money), " (bounty included)" if bounty else "", research, plot))
            if enemy["kind"] == "machine":
                parts = min(ship.hold_room("tech"), random.randint(5, 12) * power)
                if parts > 0:
                    ship.cargo["tech"] += parts
                    lines.append("You salvage %d tech from the wreckage." % parts)
            if enemy["kind"] == "pirate":
                rep = random.randint(2, 4)
                self.reputation += rep
                ship.passenger_reputation += rep
                lines.append("Reputation +%d for clearing the lane." % rep)
            elif enemy_id == "customs":
                ship.passenger_reputation -= 3
                lines.append("You shot at customs. Reputation -3.")
            return self.after_fight("victory", lines, '32')

        ship.record_combat_defeat(enemy["kind"])
        # they take a tenth to a quarter, and four per cent more for each step of wealth
        share = random.uniform(0.10, 0.25) + 0.04 * self.wealth_tier()
        stolen = int(ship.money * share) if ship.money > 10 else 0
        stolen = min(stolen, 3000 * power * (1 + 3 * self.wealth_tier()))
        losses = []
        if stolen > 0:
            ship.money -= stolen
            losses.append("%s credits" % self.format_money(stolen))
        for good in ('tech', 'agri', 'salt', 'fuel'):
            if ship.cargo[good] > 0:
                taken = random.randint(1, max(1, ship.cargo[good] // 3))
                ship.cargo[good] -= taken
                losses.append("%d %s" % (taken, good))
        lines.append("Defeat." + (" They take " + ", ".join(losses) + "." if losses else ""))
        if enemy["kind"] == "pirate":
            rep = random.randint(1, 3)
            self.reputation = max(0, self.reputation - rep)
            ship.passenger_reputation -= rep
            lines.append("Reputation -%d." % rep)
        return self.after_fight("defeat", lines, '31')

    def after_fight(self, outcome, lines, color):
        self.last_fight = outcome
        self.display_simple_message([line for text in lines for line in self.word_wrap(text)], 3, color=color)
        return outcome

    def handle_combat_event(self, event=None):
        """Someone stops the ship between docks."""
        return self.encounter(event if event in ENEMIES else self.pick_enemy())

    def handle_hunt(self):
        """The bounty board: the legions and the docks pay for ships they want gone.
        Taking a bounty uses the turn. Returns True when a hunt was flown."""
        if getattr(self, "hunted_turn", None) == self.turn:
            self.display_simple_message("The board has nothing new until tomorrow.")
            return False
        tier = self.danger_tier()
        act = self.story_manager.get_chapter_number()
        targets = []
        for power in (tier - 1, tier, tier + 1):
            power = max(1, min(7, power))
            enemy_id = self.pick_enemy(power)
            bounty = int(power * 700 * (1 + 0.25 * act))
            targets.append((enemy_id, bounty, random.choice(self.WANTED_NAMES)))
        options = [("%d" % i, "%s '%s' - threat %d, bounty %s (%s)" % (
            ENEMIES[e]["name"], name, ENEMIES[e]["power"], self.format_money(b),
            odds_word(self.fight_chance(ENEMIES[e]["power"]))))
            for i, (e, b, name) in enumerate(targets)]
        options.append(("leave", "Not today"))
        pick = self.ask_move("Bounty board - " + self.current_location.name,
                             ["Wanted by the legions and the dock masters. Hunting one takes the day."],
                             options, len(options))
        if pick == "leave":
            return False
        enemy_id, bounty, _name = targets[int(pick)]
        self.hunted_turn = self.turn
        self.last_fight = None
        outcome = self.encounter(enemy_id, bounty=bounty, hunted=True)
        self.quest_system.check_event_requirements({"type": "combat", "name": ENEMIES[enemy_id]["name"],
                                                    "location": self.current_location.name, "turn": self.turn,
                                                    "outcome": outcome})
        return True

    def situation(self, sid=None):
        """A moment between docks where gear, crew or nerve pays off."""
        sid = sid or random.choice(sorted(SITUATIONS))
        moment = SITUATIONS[sid]
        offered = [opt for opt in moment["options"] if self.can_take(opt.get("needs"))]
        options = [(str(i), self.story.fill(opt["say"])) for i, opt in enumerate(offered)]
        pick = self.ask_move(moment["title"], [self.story.fill(moment["text"])], options, len(options))
        self.apply_outcome(offered[int(pick)]["do"])
        return sid

    def can_take(self, needs):
        if not needs:
            return True
        items = self.ship.items
        if any(not items.get(i) for i in needs.get("items", [])):
            return False
        if "any" in needs and not any(items.get(i) for i in needs["any"]):
            return False
        if any(role not in self.ship.crew for role in needs.get("crew", [])):
            return False
        if any(not self.story_flag(flag) for flag in needs.get("flags", [])):
            return False
        return True

    def apply_outcome(self, out):
        """Effects of a situation's choice: money, damage, research, plot points,
        reputation, cargo, or a fight."""
        if "chance" in out:
            out = out["win"] if random.random() < out["chance"] else out["lose"]
        ship = self.ship
        lines = [self.story.fill(out["say"])] if out.get("say") else []
        scale = self.danger_tier() if out.get("tier") else 1
        money = int(out.get("money", 0) * scale)
        if money:
            ship.money = max(0, ship.money + money)
            lines.append("%s%s credits" % ("+" if money > 0 else "-", self.format_money(abs(money))))
        if out.get("damage"):
            ship.damage = max(0, min(99, ship.damage + out["damage"]))
            lines.append("Hull %s %d%%" % ("damage +" if out["damage"] > 0 else "repaired", abs(out["damage"])))
        if out.get("rp"):
            rp = int(out["rp"] * (1 + ship.research_bonus()))
            ship.research_points += rp
            lines.append("+%d RP" % rp)
        if out.get("pp"):
            self.story_manager.plot_points += out["pp"]
            lines.append("+%d plot points" % out["pp"])
        if out.get("rep"):
            ship.passenger_reputation += out["rep"]
            lines.append("Reputation %+d" % out["rep"])
        for good, amount in (out.get("cargo") or {}).items():
            if good == "any":
                good = random.choice(['tech', 'agri', 'salt', 'fuel'])
            amount = min(int(amount * random.uniform(0.6, 1.2)), ship.hold_room(good))
            if amount > 0:
                ship.cargo[good] += amount
                lines.append("+%d %s in the hold" % (amount, good))
            else:
                lines.append("No room in the hold for the %s." % good)
        if lines:
            self.display_simple_message([line for text in lines for line in self.word_wrap(text)], 3)
        if out.get("fight"):
            self.encounter(out["fight"])

    def handle_exploration_event(self, event):
        """Handle exploration events with full outcome processing"""
        success_chance = 0.7  # Base 70% success chance

        # Modify success chance based on equipment
        if "scanner" in self.ship.items:
            success_chance += 0.1
        if "probe" in self.ship.items:
            success_chance += 0.1

        # Location type modifiers
        location_modifiers = {
            "Planet": 0,
            "AsteroidBase": 0.05,
            "DeepSpaceOutpost": 0.1,
            "ResearchColony": 0.15
        }
        success_chance += location_modifiers.get(self.current_location.location_type, 0)

        if random.random() < success_chance:
            # Determine discovery type and rewards
            discovery_types = [
                ("Valuable minerals",
                {"money": (1000, 3000), "research_points": (10, 30)}),
                ("Ancient artifacts",
                {"money": (2000, 5000), "research_points": (20, 50)}),
                ("Scientific data",
                {"money": (500, 1500), "research_points": (30, 60)}),
                ("Advanced technology",
                {"money": (3000, 7000), "research_points": (25, 45)})
            ]

            discovery, reward_ranges = random.choice(discovery_types)

            # Calculate rewards with location and rank bonuses
            rank_multiplier = {
                "Explorer": 1.0,
                "Pilot": 1.2,
                "Captain": 1.5,
                "Commander": 1.8,
                "Star Commander": 2.2,
                "Space Admiral": 2.5,
                "Stellar Hero": 3.0,
                "Galactic Legend": 3.5
            }.get(self.rank, 1.0)

            location_bonus = 1.0
            if isinstance(self.current_location, ResearchColony):
                location_bonus = 1.5
            if "quantum_scanner" in self.ship.items:      # finds more in the same places
                location_bonus *= 1.25

            # Apply rewards
            money_reward = random.randint(*reward_ranges["money"])
            money_reward = int(money_reward * rank_multiplier * location_bonus)
            self.ship.money += money_reward

            rp_reward = random.randint(*reward_ranges["research_points"])
            rp_reward = int(rp_reward * rank_multiplier * location_bonus)
            self.ship.research_points += rp_reward

            # Special discovery effects
            if discovery == "Ancient artifacts":
                self.story_manager.plot_points += 2
                if random.random() < 0.3:  # 30% chance
                    self.quest_system.generate_quest("exploration", 1.5)

            elif discovery == "Advanced technology":
                if random.random() < 0.4:  # 40% chance
                    tech_bonus = random.choice(["attack", "defense", "speed"])
                    self.ship.upgrade_property(tech_bonus, 1)
                    self.display_simple_message(f"The technology improved your ship's {tech_bonus}!")

            self.display_simple_message([
                f"Exploration Success! Found {discovery}!",
                f"Earned {self.format_money(money_reward)} credits",
                f"Gained {rp_reward} research points"
            ], color='32')

        else:
            # Handle exploration failure
            damage = random.randint(5, 15)
            self.ship.damage = min(99, self.ship.damage + damage)

            self.display_simple_message([
                "Exploration failed!",
                f"Ship took {damage}% damage from hazardous conditions."
            ], color='31')

    # Add trade tracking to buy/sell methods
    def handle_trade(self, action_type, commodity=None, quantity=None, price=None):
        """Handle trade completion and contract/quest updates"""
        self.trades_completed += 1

        # Build complete trade event data
        trade_data = {
            "action": action_type,
            "location": self.current_location.name,
            "turn": self.turn,
            "trade_completed": True,
        }

        # Add commodity-specific data for sell actions
        if action_type == 'sell' and commodity and quantity:
            trade_data.update({
                "commodity": commodity,
                "amount": quantity,
                "price": price
            })

            # Update contracts with complete trade data
            if hasattr(self, 'contract_manager'):
                self.contract_manager.update_contract_progress(trade_data)

        # Update quests
        if hasattr(self, 'quest_system'):
            self.quest_system.update_from_trade(trade_data)


    def handle_trade_event(self, event):
        """Handle trade disruption events with full market impact"""
        event_types = {
            "Market crash!": {
                "price_impact": (-0.5, -0.3),  # 30-50% price reduction
                "duration": (2, 4),  # 2-4 turns
                "severity": "major"
            },
            "Trade embargo!": {
                "price_impact": (0.3, 0.5),  # 30-50% price increase
                "duration": (3, 5),
                "severity": "major"
            },
            "Resource shortage!": {
                "price_impact": (0.2, 0.4),
                "duration": (2, 3),
                "severity": "minor"
            },
            "Price manipulation!": {
                "price_impact": (-0.3, 0.3),  # Can go either way
                "duration": (1, 3),
                "severity": "minor"
            },
            "Trade route disruption!": {
                "price_impact": (0.1, 0.3),
                "duration": (2, 4),
                "severity": "moderate"
            },
            "Black market emergence!": {
                "price_impact": (-0.4, -0.2),
                "duration": (3, 5),
                "severity": "moderate"
            }
        }

        event_data = event_types.get(event, event_types["Market crash!"])

        # Select affected commodities
        commodities = ["tech", "agri", "salt", "fuel"]
        num_affected = random.randint(1, len(commodities))
        affected_commodities = random.sample(commodities, num_affected)

        # Apply market effects
        for commodity in affected_commodities:
            impact = random.uniform(*event_data["price_impact"])
            current_price = self.current_location.market[commodity]

            # Calculate new price
            new_price = current_price * (1 + impact)

            # Apply commodity-specific limits
            if commodity == "salt":
                new_price = max(60, min(150, new_price))
            elif commodity == "fuel":
                new_price = max(120, min(250, new_price))
            else:
                new_price = max(1, min(200, new_price))

            self.current_location.market[commodity] = new_price

            # Add temporary trade ban if price would be too low
            if new_price < 10:
                duration = random.randint(*event_data["duration"])
                self.current_location.add_temporary_ban(commodity, duration)

        # Generate message based on severity
        messages = {
            "major": f"Major market disruption! {event}",
            "moderate": f"Market instability detected. {event}",
            "minor": f"Minor market fluctuation. {event}"
        }

        self.display_simple_message([
            messages[event_data["severity"]],
            f"Affected commodities: {', '.join(affected_commodities)}",
            "Check market prices for details."
        ])

        # Possible quest generation
        if event_data["severity"] == "major" and random.random() < 0.3:
            self.quest_system.generate_quest("trade", 1.5)

    def handle_disaster_event(self, event):
        """Complete disaster event handler"""
        # Define disaster scenarios and their impacts
        disaster_scenarios = {
            "Asteroid impact!": {
                "base_damage": (20, 40),
                "shield_protection": 0.6,
                "cargo_loss": True,
                "equipment_failure": False
            },
            "Solar flare!": {
                "base_damage": (15, 30),
                "shield_protection": 0.8,
                "cargo_loss": False,
                "equipment_failure": True
            },
            "Equipment malfunction!": {
                "base_damage": (10, 20),
                "shield_protection": 0.0,
                "cargo_loss": False,
                "equipment_failure": True
            },
            "Hull breach!": {
                "base_damage": (25, 45),
                "shield_protection": 0.4,
                "cargo_loss": True,
                "equipment_failure": False
            },
            "Reactor leak!": {
                "base_damage": (30, 50),
                "shield_protection": 0.3,
                "cargo_loss": False,
                "equipment_failure": True
            },
            "Navigation failure!": {
                "base_damage": (5, 15),
                "shield_protection": 0.0,
                "cargo_loss": False,
                "equipment_failure": True
            }
        }

        scenario = disaster_scenarios.get(event, disaster_scenarios["Equipment malfunction!"])

        # Calculate base damage
        min_damage, max_damage = scenario["base_damage"]
        damage = random.randint(min_damage, max_damage)

        # Apply shield protection if available
        if "shield" in self.ship.items and scenario["shield_protection"] > 0:
            if random.random() < scenario["shield_protection"]:
                damage = int(damage * 0.4)  # 60% reduction when shields work
                self.display_simple_message("Shields partially mitigated the disaster!", 2, color='32')

        # Apply final damage
        self.ship.damage = min(99, self.ship.damage + damage)

        # Handle cargo loss if applicable
        if scenario["cargo_loss"]:
            cargo_lost = False
            for cargo_type in ['tech', 'agri', 'salt', 'fuel']:
                if self.ship.cargo[cargo_type] > 0:
                    lost = random.randint(1, max(1, int(self.ship.cargo[cargo_type] // 2)))
                    self.ship.cargo[cargo_type] = max(0, self.ship.cargo[cargo_type] - lost)
                    if lost > 0:
                        cargo_lost = True
                        self.display_simple_message(
                            f"Lost {self.format_money(lost)} units of {cargo_type}!",
                            2, color='31'
                        )

        # Handle equipment failure
        if scenario["equipment_failure"]:
            if self.ship.items and random.random() < 0.3:
                item = random.choice(list(self.ship.items.keys()))
                self.ship.items[item] -= 1
                if self.ship.items[item] <= 0:
                    del self.ship.items[item]
                self.display_simple_message(f"Equipment failure! Lost {item}!", 2, color='31')

        # Display final disaster results
        self.display_simple_message(
            f"Event! {event} caused {damage}% damage to the ship!",
            3, color='31'
        )

        # Check for repair opportunity
        if "repair_bot" in self.ship.items and random.random() < 0.4:
            repair = random.randint(5, 15)
            self.ship.damage = max(0, self.ship.damage - repair)
            self.display_simple_message(
                f"Repair bot automatically fixed {repair}% damage!",
                2, color='32'
            )


    def battle_event(self, enemy_attack, enemy_defense, enemy_speed):
        say(f"An enemy is attacking! Enemy stats: ATK {enemy_attack}, DEF {enemy_defense}, SPD {enemy_speed}")

        player_damage = max(0, enemy_attack - self.ship.defense)
        enemy_damage = max(0, self.ship.attack - enemy_defense)

        if self.ship.speed > enemy_speed:
            say("You have the speed advantage!")
            enemy_damage += 5
        elif self.ship.speed < enemy_speed:
            say("Enemy has the speed advantage!")
            player_damage += 5

        # Introduce randomness based on stats
        if random.random() < 0.5:
            player_damage = max(0, player_damage - random.randint(0, self.ship.defense))
        if random.random() < 0.5:
            enemy_damage = max(0, enemy_damage - random.randint(0, enemy_defense))

        say(f"You deal {enemy_damage} damage to the enemy.")
        say(f"The enemy deals {player_damage} damage to you.")

        if enemy_damage > player_damage:
            say("You won the battle!")
            reward = random.choice([
                ("money", random.randint(100, 500)),
                ("tech", random.randint(5, 15)),
                ("agri", random.randint(5, 15)),
                ("item", random.choice(["navcomp", "shield", "turrets", "scanner"]))
            ])
            if reward[0] == "money":
                self.ship.money += reward[1]
                self.display_simple_message(f"Reward: {self.format_money(reward[1])} money", 3, color='32')
            elif reward[0] == "tech":
                self.ship.cargo['tech'] += reward[1]
                self.display_simple_message(f"Reward: {self.format_money(reward[1])} tech goods", 3, color='32')
            elif reward[0] == "agri":
                self.ship.cargo['agri'] += reward[1]
                self.display_simple_message(f"Reward: {self.format_money(reward[1])} agri goods", 3, color='32')
            elif reward[0] == "item":
                self.ship.acquire_item(reward[1])
                self.display_simple_message(f"Reward: {reward[1]} item", 3, color='32')
        else:
            say("You lost the battle!")
            penalty = random.choice([
                ("money", random.randint(50, 200)),
                ("tech", random.randint(2, 10)),
                ("agri", random.randint(2, 10)),
                ("damage", random.randint(10, 30))
            ])
            if penalty[0] == "money":
                self.ship.money = max(0, self.ship.money - penalty[1])
                self.display_simple_message(f"Penalty: Lost {self.format_money(penalty[1])} money", 3, color='31')
            elif penalty[0] == "tech":
                self.ship.cargo['tech'] = max(0, self.ship.cargo['tech'] - penalty[1])
                self.display_simple_message(f"Penalty: Lost {self.format_money(penalty[1])} tech goods", 3, color='31')
            elif penalty[0] == "agri":
                self.ship.cargo['agri'] = max(0, self.ship.cargo['agri'] - penalty[1])
                self.display_simple_message(f"Penalty: Lost {self.format_money(penalty[1])} agri goods", 3, color='31')
            elif penalty[0] == "damage":
                self.ship.damage += penalty[1]
                self.display_simple_message(f"Penalty: {penalty[1]}% additional damage", 3, color='31')

    def handle_combat(self, enemy_stats):
        """Handle combat with enemy ships"""
        enemy_attack = enemy_stats.get("attack", 2)
        enemy_defense = enemy_stats.get("defense", 1)
        enemy_type = enemy_stats.get("type", "pirate")

        self.battle_event(enemy_attack, enemy_defense, self.ship.speed)
        if enemy_type == "rogue_captain":
            # Add special rewards for defeating rogue captain
            if enemy_attack < self.ship.attack:
                self.ship.money += random.randint(2000, 5000)
                special_items = ["quantum_core", "advanced_shield", "neural_hack"]
                self.ship.acquire_item(random.choice(special_items))


    def handle_research_options(self):
        """Enhanced research options system"""
        if not isinstance(self.current_location, ResearchColony):
            self.display_simple_message("Research options only available at Research Colonies!")
            return

        # Show current research points and colony specialization
        specialization = getattr(self.current_location, 'research_specialization',
                            random.choice(['quantum', 'xenology', 'engineering', 'temporal']))
        self.current_location.research_specialization = specialization

        research_content = [
            ["Research Laboratory Options"],
            [f"Available Research Points: {self.ship.research_points}"],
            [f"Colony Specialization: {specialization.title()}"],
            [""],
            ["1. Analyze (20 RP) - Safe, steady progress"],
            ["2. Experiment (40 RP) - Risky, higher rewards"],
            ["3. Breakthrough (100 RP) - Major discovery attempt"],
            ["4. Collaborate (30 RP) - Work with colony scientists"]
        ]
        print(self.create_box(research_content, 'double'))

        choice = self.validate_input(
            "Choose research action (1-4, or 'back'): ",
            ['1', '2', '3', '4', 'back']
        )

        if choice == 'back':
            return

        if choice == '1':
            self.conduct_analysis(specialization)
        elif choice == '2':
            self.conduct_experiment(specialization)
        elif choice == '3':
            self.attempt_breakthrough(specialization)
        elif choice == '4':
            self.collaborate_research(specialization)

    def conduct_analysis(self, specialization):
        """Safe research analysis with guaranteed small rewards and chance for items"""
        cost = 20
        if self.ship.research_points < cost:
            self.display_simple_message(f"Not enough research points! Need: {cost}")
            return

        self.ship.research_points -= cost

        # Base rewards
        tech_bonus = random.randint(5, 15)
        money_bonus = random.randint(500, 1500)

        # Specialization bonuses
        if specialization == 'quantum':
            tech_bonus *= 1.5
        elif specialization == 'engineering':
            money_bonus *= 1.5

        # Chance for bonus item or ship stat
        if random.random() < 0.2:  # 20% chance for bonus
            bonus_type = random.choice(['item', 'stat'])
            if bonus_type == 'item':
                research_items = {
                    'quantum': ['quantum_analyzer', 'entanglement_core', 'quantum_shield'],
                    'xenology': ['xeno_scanner', 'translation_matrix', 'alien_artifact'],
                    'engineering': ['efficiency_module', 'repair_nanites', 'power_core'],
                    'temporal': ['time_dilator', 'causality_shield', 'temporal_lens']
                }
                item = random.choice(research_items[specialization])
                self.ship.acquire_item(item)
                self.display_simple_message(f"Bonus research item acquired: {item}!")
            else:
                stat = random.choice(['attack', 'defense', 'speed'])
                bonus = 1
                if stat == 'attack':
                    self.ship.attack += bonus
                elif stat == 'defense':
                    self.ship.defense += bonus
                else:
                    self.ship.speed += bonus
                self.display_simple_message(f"Ship {stat} improved by {bonus}!")

        # Generate research findings
        findings = {
            'quantum': [
                "Quantum field fluctuations mapped",
                "Superposition states stabilized",
                "Entanglement patterns documented",
                "Wave function variations recorded"
            ],
            'xenology': [
                "Alien artifact patterns analyzed",
                "Bio-signatures catalogued",
                "Cultural markers identified",
                "Xenotechnology principles documented"
            ],
            'engineering': [
                "Efficiency algorithms optimized",
                "Material stress patterns mapped",
                "Power distribution improved",
                "Systems integration enhanced"
            ],
            'temporal': [
                "Temporal anomalies measured",
                "Causality patterns documented",
                "Time dilation effects mapped",
                "Chronological variations recorded"
            ]
        }

        result = random.choice(findings[specialization])

        self.ship.money += money_bonus
        self.ship.research_points += tech_bonus

        self.display_simple_message([
            f"Analysis Complete: {result}",
            f"Gained {tech_bonus} research points",
            f"Earned {self.format_money(money_bonus)} credits"
        ])

    def conduct_experiment(self, specialization):
        """Risky research with variable outcomes and enhanced rewards"""
        cost = 40
        if self.ship.research_points < cost:
            self.display_simple_message(f"Not enough research points! Need: {cost}")
            return

        self.ship.research_points -= cost

        # Success chance based on specialization
        base_chance = 0.7
        if specialization == 'engineering':
            base_chance += 0.1

        if random.random() < base_chance:
            # Successful experiment
            reward_mult = random.uniform(1.5, 3.0)
            tech_bonus = int(cost * reward_mult)
            money_bonus = int(1000 * reward_mult)

            # Enhanced rewards
            if random.random() < 0.4:  # 40% chance for significant bonus
                advanced_items = {
                    'quantum': {
                        'items': ['quantum_core_v2', 'phase_shifter', 'quantum_capacitor'],
                        'stat_bonus': {'attack': 2, 'defense': 1, 'speed': 2}
                    },
                    'xenology': {
                        'items': ['alien_reactor', 'xeno_shield', 'biotech_enhancer'],
                        'stat_bonus': {'attack': 1, 'defense': 2, 'speed': 1}
                    },
                    'engineering': {
                        'items': ['fusion_drive', 'nanotech_armor', 'power_amplifier'],
                        'stat_bonus': {'attack': 2, 'defense': 2, 'speed': 1}
                    },
                    'temporal': {
                        'items': ['time_dilation_core', 'temporal_shield', 'causality_engine'],
                        'stat_bonus': {'attack': 1, 'defense': 1, 'speed': 3}
                    }
                }

                # Either get an advanced item or stat bonus
                if random.random() < 0.5:
                    item = random.choice(advanced_items[specialization]['items'])
                    self.ship.acquire_item(item)
                    self.display_simple_message(f"Advanced research item acquired: {item}!")
                else:
                    stat_bonuses = advanced_items[specialization]['stat_bonus']
                    for stat, bonus in stat_bonuses.items():
                        if random.random() < 0.5:  # 50% chance for each stat
                            if stat == 'attack':
                                self.ship.attack += bonus
                            elif stat == 'defense':
                                self.ship.defense += bonus
                            else:
                                self.ship.speed += bonus
                            self.display_simple_message(f"Ship {stat} improved by {bonus}!")

            # Special bonuses based on specialization
            special_outcomes = {
                'quantum': ["Quantum Computing Breakthrough",
                        lambda: setattr(self.ship, 'quantum_bonus', True)],
                'xenology': ["Alien Technology Integration",
                            lambda: setattr(self.ship, 'alien_tech', True)],
                'engineering': ["Advanced Engineering Insights",
                            lambda: setattr(self.ship, 'engineering_bonus', True)],
                'temporal': ["Temporal Mechanics Discovery",
                            lambda: setattr(self.ship, 'temporal_bonus', True)]
            }

            outcome, effect = special_outcomes[specialization]
            effect()  # Apply the special effect

            self.display_simple_message([
                f"Experiment Success: {outcome}!",
                f"Gained {tech_bonus} research points",
                f"Earned {self.format_money(money_bonus)} credits",
                "Special ability unlocked!"
            ])

            self.ship.money += money_bonus
            self.ship.research_points += tech_bonus

        else:
            # Failed experiment
            damage = random.randint(5, 15)
            self.ship.damage = min(99, self.ship.damage + damage)
            lost_points = random.randint(5, 15)
            self.ship.research_points = max(0, self.ship.research_points - lost_points)

            self.display_simple_message([
                "Experiment Failed!",
                f"Ship took {damage}% damage",
                f"Lost {lost_points} research points"
            ])

    def attempt_breakthrough(self, specialization):
        """Attempt a major research breakthrough"""
        cost = 100
        if self.ship.research_points < cost:
            self.display_simple_message(f"Not enough research points! Need: {cost}")
            return

        self.ship.research_points -= cost

        # Breakthrough chance increases with more research points spent
        breakthrough_chance = min(0.8, 0.3 + (self.ship.research_points / 1000))

        if random.random() < breakthrough_chance:
            # Major breakthrough
            breakthrough_rewards = {
                'quantum': {
                    'name': "Quantum Tunneling Drive",
                    'effect': lambda: setattr(self.ship, 'speed', self.ship.speed + 2),
                    'bonus_rp': 300,
                    'bonus_money': 50000
                },
                'xenology': {
                    'name': "Xenomorph Shield Matrix",
                    'effect': lambda: setattr(self.ship, 'defense', self.ship.defense + 2),
                    'bonus_rp': 250,
                    'bonus_money': 40000
                },
                'engineering': {
                    'name': "Nano-fabrication System",
                    'effect': lambda: setattr(self.ship, 'engineering_level',
                                            getattr(self.ship, 'engineering_level', 0) + 1),
                    'bonus_rp': 200,
                    'bonus_money': 60000
                },
                'temporal': {
                    'name': "Temporal Compression Field",
                    'effect': lambda: setattr(self.ship, 'temporal_compression', True),
                    'bonus_rp': 400,
                    'bonus_money': 45000
                }
            }

            reward = breakthrough_rewards[specialization]
            reward['effect']()  # Apply the special effect

            self.ship.research_points += reward['bonus_rp']
            self.ship.money += reward['bonus_money']

            self.display_simple_message([
                f"Major Breakthrough: {reward['name']}!",
                f"Gained {reward['bonus_rp']} research points",
                f"Earned {self.format_money(reward['bonus_money'])} credits",
                "Revolutionary technology acquired!"
            ])

        else:
            # Minor breakthrough
            bonus_rp = random.randint(50, 150)
            bonus_money = random.randint(5000, 15000)

            self.ship.research_points += bonus_rp
            self.ship.money += bonus_money

            self.display_simple_message([
                "Minor Breakthrough Achieved",
                f"Gained {bonus_rp} research points",
                f"Earned {self.format_money(bonus_money)} credits"
            ])

    def collaborate_research(self, specialization):
        """Collaborate with colony scientists"""
        cost = 30
        if self.ship.research_points < cost:
            self.display_simple_message(f"Not enough research points! Need: {cost}")
            return

        self.ship.research_points -= cost

        # Collaboration projects
        projects = {
            'quantum': [
                ("Quantum Encryption", 1.2),
                ("Entanglement Network", 1.3),
                ("Quantum Computing", 1.4)
            ],
            'xenology': [
                ("Alien Languages", 1.2),
                ("Xenobiology", 1.3),
                ("First Contact Protocols", 1.4)
            ],
            'engineering': [
                ("Power Systems", 1.2),
                ("Shield Technology", 1.3),
                ("Propulsion Theory", 1.4)
            ],
            'temporal': [
                ("Time Dilation", 1.2),
                ("Causality Mechanics", 1.3),
                ("Temporal Physics", 1.4)
            ]
        }

        project, multiplier = random.choice(projects[specialization])

        # Calculate rewards
        research_gain = int(cost * multiplier)
        money_gain = int(2000 * multiplier)

        # Colony gains permanent bonus to future research
        colony_bonus = random.uniform(0.05, 0.15)  # 5-15% bonus
        current_multiplier = getattr(self.current_location, 'research_multiplier', 1.0)
        self.current_location.research_multiplier = current_multiplier + colony_bonus

        self.ship.research_points += research_gain
        self.ship.money += money_gain

        self.display_simple_message([
            f"Collaboration Project: {project}",
            f"Gained {research_gain} research points",
            f"Earned {self.format_money(money_gain)} credits",
            f"Colony research efficiency increased by {int(colony_bonus * 100)}%"
        ])

    def handle_buy_map(self):
        if self.ship.money >= 200:
            self.ship.money -= 200
            new_locations = []
            for location in self.locations:
                if location.name not in self.known_locations and location.location_type in self.unlocked_location_types:
                    new_locations.append(location)
                    self.known_locations.append(location.name)

            if new_locations:
                map_content = []
                # Header
                map_content.append(["New Locations!"])
                map_content.append([""])
                map_content.append(["Location", "Type", "Tech", "Agri", "Economy"])

                # Location data
                for location in new_locations:
                    features = []
                    if location.mining_platforms:
                        features.append("Mining")
                    if location.buildings:
                        features.append("Buildings")
                    if location.stockmarket_base:
                        features.append("Stock Market")

                    map_content.append([
                        location.name,
                        location.location_type,
                        str(location.tech_level),
                        str(location.agri_level),
                        location.economy
                    ])

                    # Add features as separate rows with proper indentation
                    if features:
                        map_content.append(["└─ Features: " + ", ".join(features), "", "", "", ""])

                print(self.create_box(map_content, 'double'))
                input("Press Enter to continue...")
            else:
                self.ship.money += 200  # Refund if no new locations
                self.display_simple_message("No new locations to discover!")
        else:
            self.display_simple_message("Not enough money to buy a map.")

    def handle_update_map(self):
        if self.ship.money >= 350:
            self.ship.money -= 350

            market_content = []
            # Header
            market_content.append(["Map Update"])
            market_content.append([""])
            market_content.append(["Location", "Tech", "Agri", "Salt", "Fuel"])

            # Show detailed info for known locations
            has_data = False
            for location_name in self.known_locations:
                location = next((loc for loc in self.locations if loc.name == location_name), None)
                if location:
                    has_data = True
                    tech_price = "BANNED" if 'tech' in location.banned_commodities else self.format_money(location.market['tech'])
                    agri_price = "BANNED" if 'agri' in location.banned_commodities else self.format_money(location.market['agri'])
                    salt_price = "BANNED" if 'salt' in location.banned_commodities else self.format_money(location.market['salt'])
                    fuel_price = "BANNED" if 'fuel' in location.banned_commodities else self.format_money(location.market['fuel'])

                    market_content.append([
                        location.name,
                        tech_price,
                        agri_price,
                        salt_price if location.trades_bulk('salt') else "No Mine",
                        fuel_price if location.trades_bulk('fuel') else "No Mine"
                    ])

                    # Add special features as separate rows
                    features = []
                    if location.stockmarket_base:
                        features.append("Stock Market")
                    if location.buildings:
                        features.append(f"Buildings: {', '.join(location.buildings)}")
                    if location.mining_platforms:
                        features.append(f"Mining Platforms: {len(location.mining_platforms)}")

                    if features:
                        for feature in features:
                            market_content.append(["└─ " + feature, "", "", "", ""])

            if has_data:
                print(self.create_box(market_content, 'double'))
                input("Press Enter to continue...")
            else:
                self.ship.money += 350  # Refund if no data to show
                self.display_simple_message("No new information available!")
        else:
            self.display_simple_message("Not enough money to update the map.")

    def handle_gossip(self):
        """Handle gossip and quest generation in cantina"""
        if self.ship.money >= 150:
            self.ship.money -= 150
            gossip_content = [["Latest Market Gossip"]]
            gossip_content.append([""])

            # Generate market information
            found_gossip = False
            for location in self.locations:
                if location.name in self.known_locations:
                    location_gossip = []
                    if location.market['tech'] < 50:
                        location_gossip.append(f"Cheap tech goods available")
                    if location.market['agri'] < 30:
                        location_gossip.append(f"Cheap agri goods available")
                    if location.market['tech'] > 100:
                        location_gossip.append(f"High tech prices")
                    if location.market['agri'] > 80:
                        location_gossip.append(f"High agri prices")

                    if location_gossip:
                        found_gossip = True
                        gossip_content.append([location.name])
                        for gossip in location_gossip:
                            gossip_content.append([f"└─ {gossip}"])

            if found_gossip:
                print(self.create_box(gossip_content, 'double'))

                # 30% chance to get a quest
                if random.random() < 0.3:
                    self.quest_system.add_quest(self.quest_system.generate_cantina_quest())
            else:
                self.display_simple_message("No interesting gossip today!")
        else:
            self.display_simple_message("Not enough money to listen to gossip.")

    def display_story_status(self):
        """Display story progress and achievements"""
        story_content = [["Story Progress & Achievements"]]
        story_content.append([""])

        # Current chapter info
        current_chapter_obj = self.story_manager.chapters[self.story_manager.current_chapter]
        story_content.append([f"Current Chapter {self.story_manager.get_chapter_number_roman()} : {current_chapter_obj.title}"])
        story_content.append([f"Plot Points: {self.story_manager.plot_points}"])

        # Completed story beats
        if self.story_manager.completed_story_beats:
            story_content.append([""])
            story_content.append(["Completed Story Elements"])
            for beat in self.story_manager.completed_story_beats:
                story_content.append([f"• {beat.replace('_', ' ').title()}"])

        # Achievements
        if hasattr(self.story_manager, 'unlocked_achievements') and self.story_manager.unlocked_achievements:
            story_content.append([""])
            story_content.append(["Achievements Unlocked"])
            for achievement in self.story_manager.unlocked_achievements:
                story_content.append([f"• {achievement.replace('_', ' ').title()}"])

        # Location discoveries
        if hasattr(self.story_manager, 'discovered_locations_by_type'):
            story_content.append([""])
            story_content.append(["Location Discoveries"])
            for loc_type, count in self.story_manager.discovered_locations_by_type.items():
                story_content.append([f"• {loc_type}: {count} discovered"])

        print(self.create_box(story_content, 'double'))
        input("Press Enter to continue...")

    def visit_cantina(self):
        self.clear_screen()
        self.display_simple_message("Welcome to the Cantina!", 0)

        # Whoever is in the cantina today, and what people are saying
        self.story.visit_venue("cantina")
        self.story_manager.nudge()

        while True:
            options = {
                'map': ('bm', "Buy Map"),
                'update': ('um', "Update Map"),
                'gossip': ('lg', "Listen to Gossip"),
                'quests': ('q', "View Quests"),
                'contracts': ('c', "Manage Contracts"),
                'story': ('s', "View Story Progress"),
                'back': ('', "Return to Main Menu")
            }

            menu_content = [[f"Cantina Services - {self.current_location.name}"]]
            menu_content.append([f""])
            for cmd, (shortcut, desc) in options.items():
                menu_content.append([f"{cmd}/{shortcut if shortcut else ''}: {desc}"])
            print(self.create_box(menu_content, 'single'))

            valid_inputs = [cmd for cmd in options.keys()] + [s[0] for s in options.values() if s[0]]
            action = self.validate_input("Cantina - choose (Enter to leave): ", valid_inputs)

            if action in ['back', None]:
                break

            elif action in ['map', 'bm']:
                self.handle_buy_map()

            elif action in ['update', 'um']:
                self.handle_update_map()

            elif action in ['gossip', 'lg']:
                self.handle_gossip()

            elif action in ['quests', 'q']:
                self.quest_system.display_quests()

            elif action in ['contracts', 'c']:
                self.handle_contract_menu()

            elif action in ['story', 's']:
                self.display_story_status()

            time.sleep(1)
            self.clear_screen()

    def visit_shop(self):
        """Enhanced shop interface with persistent sold items"""
        self.display_simple_message("Welcome to the Shop!", 1)

        # Display current money and location info
        status_content = [
            [f"Credits: {self.format_money(self.ship.money)}"],
            [f"Tech Level: {self.current_location.tech_level}"]
        ]
        print(self.create_box(status_content, 'single'))

        # Display current inventory
        inventory_content = [["Your Items"]]
        if self.ship.items:
            for item, count in self.ship.items.items():
                inventory_content.append([f"{item}: {count}"])
        else:
            inventory_content.append(["No items"])
        print(self.create_box(inventory_content, 'single'))

        # Get available items for this location
        if not hasattr(self.shop, 'current_turn_items') or not self.shop.current_turn_items:  # Changed condition
            # Only get new items if we haven't already for this turn
            self.shop.current_turn_items = self.shop.get_available_items(
                location=self.current_location,
                plot_points=self.story_manager.plot_points
            )

        shop_content = [["Item", "¤", "Description", ""]]
        for item_name, item_data in self.shop.current_turn_items:
            status = "SOLD" if self.shop.is_item_sold(item_name) else "Avail"
            shop_content.append([
                item_name.title(),
                self.format_money(item_data["price"]),
                item_data["description"],
                status
            ])

        print(self.create_box(shop_content, 'double'))

        # Only show unsold items in options
        available_items_names = [
            item[0] for item in self.shop.current_turn_items
            if not self.shop.is_item_sold(item[0])
        ]

        if not available_items_names:
            self.display_simple_message("All items are sold out!")
            return

        item_choice = self.validate_input(
            "Choose item to buy (or 'none' to exit): ",
            available_items_names + ['none']
        )

        if item_choice == 'none':
            return

        for item_name, item_data in self.shop.current_turn_items:
            if item_choice == item_name:
                if self.ship.money >= item_data["price"]:
                    self.ship.money -= item_data["price"]
                    self.ship.acquire_item(item_name)
                    self.shop.mark_item_sold(item_name)

                    self.display_simple_message([
                        f"You bought a {item_name}!",
                        f"Effect: {item_data['description']}",
                        f"Remaining credits: {self.format_money(self.ship.money)}"
                    ])
                else:
                    missing = item_data["price"] - self.ship.money
                    self.display_simple_message([
                        "Not enough money to buy this item.",
                        f"Price: {self.format_money(item_data['price'])}",
                        f"Your credits: {self.format_money(self.ship.money)}",
                        f"Missing: {self.format_money(missing)}"
                    ])
                return

        time.sleep(1)

    def handle_mining(self):
        """Handle mining-related actions"""
        options = ['build', 'status', 'research']
        choice = self.validate_input(
            "Mining options (build/status/research): ",
            options
        )

        if choice == 'build':
            self.build_mining_platform()
        elif choice == 'status':
            self.display_mining_status()
        elif choice == 'research':
            cost = self.research.research_costs['exogeology']
            if 'exogeology' in self.research.unlocked_options:
                self.display_simple_message("Mining efficiency research is already completed.")
            elif self.ship.research_points >= cost:
                self.ship.research_points -= cost
                self.action.research(self.current_location, 'exogeology', self.research)
                self.display_simple_message("Mining efficiency research completed!")
            else:
                self.display_simple_message(f"Not enough research points! Need: {cost}")

    def display_mining_status(self):
        """Display mining operations status"""
        content = [
            ["Mining Status"],
            [f"Planet Efficiency: {self.current_location.exogeology}%"],
            ["Active Platforms:"]
        ]

        for platform in self.current_location.mining_platforms:
            content.append([
                f"{platform['type'].capitalize()}: "
                f"Efficiency {platform['efficiency']}% "
                f"Capacity {platform['capacity']}"
            ])

        if self.current_location.mineral_deposits:
            content.append(["Available Deposits:"])
            for deposit, amount in self.current_location.mineral_deposits.items():
                content.append([f"{deposit.capitalize()}: {amount} units"])

        print(self.create_box(content, 'double'))


    def check_milestone_triggers(self):
        """Check for milestone triggers each turn"""
        # First trade
        if self.trades_completed == 2:
            self.story_manager.complete_milestone("first_trade")

        # First combat
        if self.ship.combat_victories['total'] == 1:
            self.story_manager.complete_milestone("first_combat")

        # Basic license (after 5 successful trades)
        if self.trades_completed >= 5 and "basic_license" not in self.story_manager.completed_story_beats:
            self.story_manager.complete_milestone("basic_license")

        # Pirates and route security
        if self.ship.combat_victories.get('pirate', 0) >= 5:
            self.story_manager.complete_milestone("defeat_pirates")
            if self.trades_completed >= 20:
                self.story_manager.complete_milestone("secure_route")

        # Mining milestones
        if any(loc.mining_platforms for loc in self.locations):
            self.story_manager.complete_milestone("first_mining")
            miners_defended = self.ship.combat_victories['total'] >= 10
            if miners_defended:
                self.story_manager.complete_milestone("defend_miners")

        # Research milestones
        if any(isinstance(loc, ResearchColony) for loc in self.locations):
            self.story_manager.complete_milestone("research_hub")
        if len(self.research.unlocked_options) >= 3:
            self.story_manager.complete_milestone("tech_breakthrough")


    # ... The end score ...

    def display_score(self):
        """Display final game score and statistics in a formatted box"""
        # Calculate final statistics
        total_cargo_value = (self.ship.cargo['tech'] * 10) + (self.ship.cargo['agri'] * 5) + \
                           (self.ship.cargo['salt'] * 15) + (self.ship.cargo['fuel'] * 20)
        final_score = self.ship.money + total_cargo_value
        efficiency_score = (final_score / self.turn) if self.turn > 0 else final_score

        # Create score content
        score_content = [
            ["FINAL SCORE REPORT", ""],  # Title row
            ["─" * 18, "─" * 18],  # Separator
            ["Assets", "Value"],
            ["Money", f"{self.format_money(self.ship.money)}"],
            ["Tech Cargo", f"{self.format_money(self.ship.cargo['tech'])} units"],
            ["Agri Cargo", f"{self.format_money(self.ship.cargo['agri'])} units"],
            ["Salt Cargo", f"{self.format_money(self.ship.cargo['salt'])} units"],
            ["Fuel Cargo", f"{self.format_money(self.ship.cargo['fuel'])} units"],
            ["", ""],  # Empty row for spacing
            ["Performance Metrics", ""],
            ["Total Score", f"{self.format_money(final_score)}"],
            ["Efficiency Score", f"{self.format_money(efficiency_score)}/turn"],
            ["Turns Played", str(self.turn)],
            ["Final Rank", self.rank],
            ["", ""],  # Empty row for spacing
            ["Ship Statistics", ""],
            ["Attack Level", str(self.ship.attack)],
            ["Defense Level", str(self.ship.defense)],
            ["Speed Level", str(self.ship.speed)],
            ["Hull Damage", f"{self.ship.damage}%"]
        ]

        # Add equipment section if player has any
        if self.ship.items:
            score_content.extend([
                ["", ""],  # Empty row for spacing
                ["Equipment", "Count"]
            ])
            for item, count in self.ship.items.items():
                score_content.append([item.capitalize(), str(count)])

        # Add research section if player has any
        if hasattr(self, 'research') and self.research.unlocked_options:
            score_content.extend([
                ["", ""],  # Empty row for spacing
                ["Completed Research", ""]
            ])
            for research in self.research.unlocked_options:
                score_content.append([research.replace('_', ' ').title(), ""])

        # Create the box with double borders for emphasis
        fancy_box = self.create_box(score_content, 'double')
        print(fancy_box)

        # Display achievement message
        achievement_msg = self.get_achievement_message(final_score)
        self.display_simple_message(achievement_msg, style='round', color='32')  # Green color for achievement

    def get_achievement_message(self, score):
        """Generate an achievement message based on the final score"""
        if score >= 1000000:
            return f"Legendary Achievement! {self.player_name}, you have become a true Galactic Legend!"
        elif score >= 500000:
            return f"Outstanding Success! {self.player_name}, your name will be remembered among the Stellar Heroes!"
        elif score >= 200000:
            return f"Remarkable Victory! {self.player_name}, you have proven yourself as a Space Admiral!"
        elif score >= 100000:
            return f"Impressive Results! {self.player_name}, you have earned the title of Star Commander!"
        elif score >= 50000:
            return f"Well Done! {self.player_name}, you have become a respected Commander!"
        elif score >= 20000:
            return f"Good Job! {self.player_name}, you have proven yourself as a capable Captain!"
        elif score >= 10000:
            return f"Nice Work! {self.player_name}, you have graduated from Pilot to veteran trader!"
        else:
            return f"Game Complete! {self.player_name}, you have completed your journey as an Explorer!"

    def update_rank(self):
        score = self.ship.money + (self.ship.cargo['tech'] * 10) + (self.ship.cargo['agri'] * 5)
        if score >= 1000000:
            self.rank = "Galactic Legend"
        elif score >= 500000:
            self.rank = "Stellar Hero"
        elif score >= 200000:
            self.rank = "Space Admiral"
        elif score >= 100000:
            self.rank = "Star Commander"
        elif score >= 50000:
            self.rank = "Commander"
        elif score >= 20000:
            self.rank = "Captain"
        elif score >= 10000:
            self.rank = "Pilot"
        else:
            self.rank = "Explorer"

    def rank_multiplier(self):
        if self.rank == "Galactic Legend":
            return 10
        elif self.rank == "Stellar Hero":
            return 8
        elif self.rank == "Space Admiral":
            return 6
        elif self.rank == "Star Commander":
            return 4
        elif self.rank == "Commander":
            return 2
        elif self.rank == "Captain":
            return 1.5
        elif self.rank == "Pilot":
            return 1.2
        else:
            return 1

    def play(self):
        while True:
            # Play a turn
            turn_result = self.play_turn()

            # Check if player quit or resigned
            if turn_result == "quit":
                self.display_simple_message("Thanks for playing!")
                break
            elif turn_result == "resign":
                self.display_simple_message("Resigning from current game...")
                self.display_score()
                break

            self.update_rank()

            # Check game over conditions
            if self.ship.money <= 0 and self.ship.is_empty_cargo():
                self.display_simple_message("Game Over: No money and no cargo left.", 2)
                self.display_score()
                break

            if self.ship.damage >= 100:
                self.display_simple_message("Game Over: Ship destroyed!", 2)
                self.display_score()
                break

            # Check for special quest availability
            # Only check planets and locations that can have stockmarkets
            valid_locations = [loc for loc in self.locations
                            if isinstance(loc, Planet) or
                            loc.location_type in ["Planet", "AsteroidBase", "DeepSpaceOutpost"]]

            if valid_locations and all(loc.stockmarket_base for loc in valid_locations) \
                    and not self.stellar_portal_available \
                    and self.turn - getattr(self, "tycoon_offered", -100) >= 10:
                # every market is yours: retire, go through the portal, or keep trading
                self.tycoon_offered = self.turn
                self.secret_quest_available = True
                self.story.mark("tycoon_offer")
                self.display_story_message(self.story.text_of("tycoon_offer", fallback=(
                    "Retire as Galactic Tycoon, or pay 1,500 credits and continue into the unknown.")) + [
                    "", "1. Keep trading here (asked again in 10 turns)",
                    "2. Retire as Galactic Tycoon (the game ends)",
                    "3. Pay 1,500 and fly through the portal (no way back)"], pause=0)
                answer = self.validate_input("Your response (1-3): ", ['1', '2', '3'])
                if answer == '2':
                    self.story.mark("ending_tycoon")
                    self.display_story_message(self.story.text_of("ending_tycoon", fallback=(
                        "You are the Galactic Tycoon!")))
                    self.display_score()
                    self.story.epilogue()
                    self.close_record("tycoon")
                    break
                elif answer == '3':
                    if self.ship.money >= 1500:
                        self.ship.money -= 1500
                        self.open_portal()
                    else:
                        self.display_simple_message("Not enough money for the coordinate.")

            # Ask to play again
            if turn_result == "quit":
                play_again = self.validate_input("Do you want to play again? (yes/no): ", ['yes', 'no'])
                if play_again == 'yes':
                    raise SwitchGame(Game())
                break

    def generate_new_locations(self):
        """Generate new locations for the late-game content"""
        new_locations = [
            Planet("Zeta", 10, 1, 5, "Stable"),
            Planet("Eta", 1, 10, 5, "Booming"),
            Planet("Theta", 8, 8, 10, "Declining"),
            AsteroidBase("Omega-1", 5, 5, 15, "Formative"),
            DeepSpaceOutpost("DSO-Delta", 7, 3, 20, "Stable")
        ]

        # Add some special bonuses for late-game locations
        for location in new_locations:
            location.exogeology += 20  # Better mining in new locations
            location.research_points *= 2     # Double research points
            location.tech_level += 2         # Higher tech levels

            # Special location-type bonuses
            if isinstance(location, AsteroidBase):
                location.exogeology += 10  # Extra mining bonus
            elif isinstance(location, DeepSpaceOutpost):
                location.market['tech'] = max(1, location.market['tech'] * 0.8)  # Better tech prices

        return new_locations

#New additions to the game system


    def handle_location_discovery(self, location):
        """Handle discovery of a new location"""
        if location.name not in self.discovered_locations:
            self.discovered_locations.add(location.name)

            # Award discovery rewards
            discovery_reward = 1000 * (self.story_manager.get_chapter_number() + 1)
            research_reward = 20 * (self.story_manager.get_chapter_number() + 1)

            self.ship.money += discovery_reward
            self.ship.research_points += research_reward

            # Check for story progression
            self.story_manager.check_discovery_milestone(location)

            # Check for quest updates
            self.quest_system.update_discovery_quests(location)

            self.display_story_message([
                f"Discovered new location: {location.name}!",
                f"Earned {self.format_money(discovery_reward)} credits",
                f"Gained {research_reward} research points"
            ])

    def check_location_unlocks(self):
        """Check for new location type unlocks"""
        for location_type in self.location_manager.location_quests:
            if (location_type not in self.unlocked_location_types and
                self.location_manager.check_location_unlock_progress(location_type)):
                self.location_manager.trigger_location_unlock_quest(location_type)


    def clear_screen(self):
        os.system('clear' if os.name == 'posix' else 'cls')

class ContractManager:
    def __init__(self, game):
        self.game = game
        self.available_contracts = []
        self.active_contracts = []
        self.completed_contracts = []
        self.max_active_contracts = 3
        self.contract_refresh_turns = 0
        self.special_contracts_unlocked = False


    def handle_contract_menu(self):
        """Handle port menu options"""
        self.game.clear_screen()
        self.game.display_simple_message("Contract Management Terminal", 0)

        while True:
            # Refresh contracts if needed
            self.refresh_available_contracts()

            options = {
                'view': ('v', "View new contracts"),
                'claim': ('c', "Claim completed contract rewards"),
                'status': ('s', "Check detailed contract status"),
                'back': ('', "Return to previous menu")
            }

            # Show menu
            menu_content = [["Contract Dashboard:"]]
            menu_content.append([f""])
            for cmd, (shortcut, desc) in options.items():
                menu_content.append([f"{cmd}/{shortcut if shortcut else ''}: {desc}"])
            print(self.game.create_box(menu_content, 'single'))

            valid_inputs = [cmd for cmd in options.keys()] + [s[0] for s in options.values() if s[0]]
            action = self.game.validate_input("Contracts - choose (Enter to leave): ", valid_inputs)

            if action in ['back', None]:
                break

            elif action in ['view', 'v']:
                self.show_available_contracts()

            elif action in ['claim', 'c']:
                self.claim_completed_contracts()

            elif action in ['status', 's']:
                self.show_detailed_status()

            self.game.clear_screen()

    def show_available_contracts(self):
        """Show available contracts for acceptance"""
        if not self.available_contracts:
            self.game.display_simple_message("No contracts available currently.")
            return

        contract_content = [["Available Contracts"]]
        for i, contract in enumerate(self.available_contracts, 1):
            contract_content.append([""])
            contract_content.append([f"Contract #{i}"])
            for info_line in self.get_contract_display_info(contract):
                contract_content.append([info_line])

        print(self.game.create_box(contract_content, 'double'))

        choice = self.game.validate_input(
            f"Accept contract (1-{len(self.available_contracts)}) or Enter to cancel: ",
            [str(i) for i in range(1, len(self.available_contracts) + 1)] + ['']
        )

        if not choice:  # Empty Enter cancels
            return

        success, message = self.accept_contract(int(choice) - 1)
        self.game.display_simple_message(message)

    def claim_completed_contracts(self):
        """Handle claiming rewards for completed contracts"""
        completed = [c for c in self.active_contracts if c.completed and not c.rewards_claimed]

        if not completed:
            self.game.display_simple_message("No completed contracts to claim!")
            return

        # Show completed contracts
        content = [["Completed Contracts Ready to Claim"]]
        for i, contract in enumerate(completed, 1):
            content.append([
                f"{i}. {contract.description}",
                f"Reward: {self.game.format_money(contract.rewards['money'])}",
                f"Rep: +{contract.rewards['reputation']}"
            ])
        print(self.game.create_box(content, 'double'))

        # Get contract choice
        choice = self.game.validate_input(
            "Enter contract number to claim (or Enter to cancel): ",
            [str(i) for i in range(1, len(completed) + 1)] + ['']
        )

        if not choice:  # Empty Enter cancels
            return

        # Claim rewards
        contract = completed[int(choice) - 1]
        self.handle_contract_completion(contract)


    def show_detailed_status(self):
        """Show detailed status of all active contracts with trade history"""
        if not self.active_contracts:
            self.game.display_simple_message("No active contracts!")
            return

        for contract in self.active_contracts:
            content = [
                [f"Contract: {contract.description}"],
                [""],
                ["Requirements:"]
            ]

            # Add type-specific requirements
            if contract.contract_type == "cargo":
                content.extend([
                    [f"• Cargo: {contract.requirements['cargo_type']}"],
                    [f"• Amount: {contract.requirements['min_amount']} units"],
                    [f"• Source: {contract.requirements['source']}"],
                    [f"• Destination: {contract.requirements['destination']}"],
                    [f"• Time Limit: {contract.duration} turns"]
                ])
            elif contract.contract_type == "passenger":
                content.extend([
                    [f"• Passengers: {contract.requirements.get('count', contract.requirements.get('passenger_count', 0))}"],
                    [f"• Class: {contract.requirements.get('passenger_class', 'Any')}"],
                    [f"• Source: {contract.requirements['source']}"],
                    [f"• Destination: {contract.requirements['destination']}"],
                    [f"• Time Limit: {contract.duration} turns"]
                ])

            content.extend([
                [""],
                ["Current Status:"]
            ])

            # Add status lines
            status = contract.get_status_display()
            for line in status.split('\n'):
                content.append([f"• {line}"])

            # Add trade history
            content.extend([
                [""],
                ["Delivery History:"]
            ])

            history = contract.get_trade_history_display()
            for line in history.split('\n'):
                content.append([f"• {line}"])

            # Add reward info if completed
            if contract.completed and not contract.rewards_claimed:
                content.extend([
                    [""],
                    ["Rewards Available:"],
                    [f"• {self.game.format_money(contract.rewards['money'])} credits"],
                    [f"• {contract.rewards['reputation']} reputation"],
                    [f"• {contract.rewards.get('plot_points', 0)} plot points"]
                ])

            print(self.game.create_box(content, 'double'))
            print()  # Add space between contracts

        input("Press Enter to continue...")

    def refresh_available_contracts(self):
        """Refresh available contracts every 5 turns"""
        if self.game.turn - self.contract_refresh_turns >= 5:
            self.contract_refresh_turns = self.game.turn
            self.available_contracts = []
            # Generate 2-4 new contracts using known locations
            num_contracts = random.randint(2, 4)
            for _ in range(num_contracts):
                # If special contracts are unlocked, 30% chance for special contract
                if self.special_contracts_unlocked and random.random() < 0.3:
                    contract = self.generate_special_contract()
                    if contract:
                        self.available_contracts.append(contract)
                        continue

                # Regular contract generation
                if random.random() < 0.6:  # 60% chance for cargo contract
                    contract = self.generate_cargo_contract()
                else:
                    contract = self.generate_passenger_contract()
                if contract:
                    self.available_contracts.append(contract)

    def generate_cargo_contract(self):
        """Generate a cargo transport contract"""
        if len(self.game.known_locations) < 2:
            return None

        # Get actual Location objects from known locations
        known_locations = [loc for loc in self.game.locations
                        if loc.name in self.game.known_locations]

        if len(known_locations) < 2:
            return None

        source = random.choice(known_locations)
        destinations = [loc for loc in known_locations if loc != source]
        destination = random.choice(destinations)

        contract_types = [
            {
                "desc_template": "Exclusive Trading",
                "requirements": {
                    "cargo_type": (cargo_type := random.choice(["tech", "agri"])),
                    "min_amount": (amount := random.randint(100, 300)),
                    "source": source.name,
                    "destination": destination.name
                },
                "duration": 8,
                "base_reward": 20000,
                "description": f"Transport {amount} units of {cargo_type} from {source.name} to {destination.name}"
            },
            {
                "desc_template": "Resource Distribution",
                "requirements": {
                    "cargo_type": (cargo_type := random.choice(["salt", "fuel"])),
                    "min_amount": (amount := random.randint(50, 150)),
                    "source": source.name,
                    "destination": destination.name
                },
                "duration": 12,
                "base_reward": 30000,
                "description": f"Transport {amount} units of {cargo_type} from {source.name} to {destination.name}"
            }
        ]

        contract_type = random.choice(contract_types)
        return Contract(
            contract_type="cargo",
            duration=contract_type["duration"],
            requirements=contract_type["requirements"],
            rewards={
                "money": contract_type["base_reward"],
                "reputation": 20,
                "plot_points": 3
            },
            description=contract_type["description"]
        )

    def generate_passenger_contract(self):
        """Generate a passenger transport contract"""
        if len(self.game.known_locations) < 2:
            return None

        # Get actual Location objects from known locations
        known_locations = [loc for loc in self.game.locations
                        if loc.name in self.game.known_locations]

        if len(known_locations) < 2:
            return None

        source = random.choice(known_locations)
        destinations = [loc for loc in known_locations if loc != source]
        destination = random.choice(destinations)

        contract_types = [
            {
                "desc_template": "VIP Transport",
                "requirements": {
                    "passenger_class": (passenger_class := random.choice(["S", "M", "E"])),
                    "count": (count := random.randint(3, 8)),
                    "source": source.name,
                    "destination": destination.name,
                    "min_satisfaction": 80
                },
                "duration": 10,
                "base_reward": 25000,
                "description": f"Transport {count} {passenger_class}-class passengers from {source.name} to {destination.name}"
            },
            {
                "desc_template": "Group Transport",
                "requirements": {
                    "passenger_count": (count := random.randint(10, 20)),
                    "source": source.name,
                    "destination": destination.name,
                    "min_satisfaction": 70
                },
                "duration": 15,
                "base_reward": 35000,
                "description": f"Transport {count} passengers from {source.name} to {destination.name}"
            }
        ]

        contract_type = random.choice(contract_types)
        return Contract(
            contract_type="passenger",
            duration=contract_type["duration"],
            requirements=contract_type["requirements"],
            rewards={
                "money": contract_type["base_reward"],
                "reputation": 25,
                "plot_points": 5
            },
            description=contract_type["description"]
        )

    def generate_special_contract(self):
        """Generate a special contract with higher rewards and requirements"""
        if len(self.game.known_locations) < 2:
            return None

        # Get actual Location objects from known locations
        known_locations = [loc for loc in self.game.locations
                        if loc.name in self.game.known_locations]

        if len(known_locations) < 2:
            return None

        source = random.choice(known_locations)
        destinations = [loc for loc in known_locations if loc != source]
        destination = random.choice(destinations)

        contract_types = [
            {
                "desc_template": "High-Value Transport",
                "requirements": {
                    "cargo_type": (cargo_type := random.choice(["tech", "agri"])),
                    "min_amount": (amount := random.randint(400, 600)),
                    "source": source.name,
                    "destination": destination.name,
                    "reputation_required": 40
                },
                "duration": 10,
                "base_reward": 50000,
                "description": f"Transport {amount} units of {cargo_type} from {source.name} to {destination.name}"
            },
            {
                "desc_template": "Diplomatic Mission",
                "requirements": {
                    "passenger_class": "D",
                    "count": (count := random.randint(2, 4)),
                    "source": source.name,
                    "destination": destination.name,
                    "min_satisfaction": 90,
                    "reputation_required": 60
                },
                "duration": 8,
                "base_reward": 60000,
                "description": f"Transport {count} diplomatic passengers from {source.name} to {destination.name}"
            }
        ]

        contract_type = random.choice(contract_types)
        return Contract(
            contract_type=contract_type["desc_template"].lower().replace(" ", "_"),
            duration=contract_type["duration"],
            requirements=contract_type["requirements"],
            rewards={
                "money": contract_type["base_reward"],
                "reputation": 30,
                "plot_points": 8
            },
            description=contract_type["description"]
        )

    def accept_contract(self, contract_index):
        """Accept a contract from available contracts"""
        if contract_index >= len(self.available_contracts):
            return False, "Invalid contract selection."

        if len(self.active_contracts) >= self.max_active_contracts:
            return False, "Maximum number of active contracts reached."

        contract = self.available_contracts.pop(contract_index)
        self.active_contracts.append(contract)
        return True, f"Contract accepted: {contract.description}"

    def handle_contract_completion(self, contract):
        """Handle completed contract and reward claiming"""
        if contract not in self.active_contracts:
            return

        if contract.rewards_claimed:
            return

        # Calculate and award final rewards
        rewards = contract.calculate_final_reward()
        self.game.ship.money += rewards["money"]
        self.game.reputation += rewards["reputation"]
        self.game.story_manager.plot_points += rewards["plot_points"]

        # Mark contract as claimed
        contract.rewards_claimed = True
        self.active_contracts.remove(contract)
        self.completed_contracts.append(contract)

        # Display completion message
        self.game.display_simple_message([
            "Contract Rewards Claimed!",
            f"Earned {self.game.format_money(rewards['money'])} credits",
            f"Reputation +{rewards['reputation']}",
            f"Plot Points +{rewards['plot_points']}"
        ])

    def get_contract_display_info(self, contract):
        """Get formatted display info for a contract"""
        info = []
        info.append(f"Type: {contract.contract_type.title()}")
        info.append(f"Duration: {contract.duration} turns")

        # Requirements
        if contract.contract_type == "passenger":
            if "passenger_class" in contract.requirements:
                class_code = contract.requirements["passenger_class"]
                count = contract.requirements["count"]
                info.append(f"Transport: {count} {class_code}-class passengers")
            if "passenger_count" in contract.requirements:
                info.append(f"Transport: {contract.requirements['passenger_count']} passengers")
            if "min_satisfaction" in contract.requirements:
                info.append(f"Min. Satisfaction: {contract.requirements['min_satisfaction']}%")
        else:  # cargo contract
            if "cargo_type" in contract.requirements:
                info.append(f"Cargo: {contract.requirements['cargo_type']}")
                if "min_amount" in contract.requirements:
                    info.append(f"Amount: {contract.requirements['min_amount']} units")

        # Route information
        source = contract.requirements.get('source', 'Any')
        dest = contract.requirements.get('destination', 'Any')
        info.append(f"Route: {source} → {dest}")

        # Rewards
        info.append(f"Reward: {self.game.format_money(contract.rewards['money'])} credits")
        info.append(f"Reputation: +{contract.rewards['reputation']}")
        if contract.rewards['plot_points'] > 0:
            info.append(f"Plot Points: +{contract.rewards['plot_points']}")

        return info

    def update_contract_progress(self, event_data):
        """Update progress for all active contracts"""
        messages = []
        for contract in self.active_contracts[:]:  # Create copy to allow safe removal
            if contract.completed or contract.failed:
                continue

            result = contract.update_progress(event_data)

            if result["status"] == "completed":
                messages.append(result["message"])
                if contract.contract_type == "cargo":
                    self.game.display_simple_message(
                        f"Contract completed: Delivered {contract.progress['amount']} {contract.requirements['cargo_type']} " +
                        f"from {contract.requirements['source']} to {contract.requirements['destination']}"
                    )
                elif contract.contract_type == "passenger":
                    self.game.display_simple_message(
                        f"Contract completed: Transported {contract.progress['passengers_delivered']} passengers " +
                        f"from {contract.requirements['source']} to {contract.requirements['destination']}"
                    )
            elif result["status"] == "updated" and "message" in result:
                messages.append(result["message"])

        if messages:
            for msg in messages:
                self.game.display_simple_message(msg)


class SpecialCharacter:
    def __init__(self, title, name, role, specialization):
        self.title = title
        self.name = name
        self.role = role
        self.specialization = specialization
        self.full_name = f"{title} {name}"
        self.met = False
        self.quests_given = []
        self.relationship = 0  # -100 to 100
        self.last_interaction = None
        self.location_preference = None
        self.special_contracts = []

class SpecialCharacterGenerator:
    def __init__(self, game):
        self.game = game  # Store game instance

        self.titles = {
            "military": ["Fleet Commander", "Fleet Admiral", "Security Chief", "Defense Director"],
            "science": ["Research Coordinator", "Science Director", "Chief Researcher", "Lab Supervisor"],
            "trade": ["Trade Minister", "Commerce Director", "Market Supervisor", "Exchange Chief"],
            "engineering": ["Engineering Chief", "Tech Director", "Systems Coordinator", "Project Lead"]
        }

        self.surnames = ["Wu", "Cheng", "Tahoe", "Singh", "Patel", "Kim", "Rodriguez", "Novak",
                        "Chen", "Zhang", "Yamamoto", "Anderson", "Silva", "Kumar", "Hassan"]

        self.roles = {
            "military": ["Combat training", "Fleet operations", "Security protocols", "Defense systems"],
            "science": ["Research projects", "Lab experiments", "Data analysis", "Discovery missions"],
            "trade": ["Market analysis", "Trade routes", "Economic planning", "Resource management"],
            "engineering": ["System upgrades", "Tech maintenance", "Innovation projects", "Infrastructure"]
        }

        self.known_characters = {}  # Track generated characters
        self.add_vip_templates()

    def generate_character(self, char_type=None, title=None, specialization=None):
        """Generate a character with optional title and specialization"""
        if title and specialization:
            # Handle direct title/specialization generation
            name = random.choice(self.surnames)
            character = SpecialCharacter(
                title=title,
                name=name,
                role=specialization,
                specialization=specialization
            )
            # Add VIP-specific attributes if it's a VIP
            if specialization == "VIP":
                character.rewards = {
                    "base_money": 25000,
                    "reputation": 15
                }
                character.special_abilities = ["trade_bonus"]
                reputation_multiplier = 1 + (self.game.ship.passenger_reputation / 100)
                character.rewards["base_money"] = int(character.rewards["base_money"] * reputation_multiplier)
            return character

        elif char_type == "VIPPassenger":
            vip_type = random.choice(list(self.vip_templates.keys()))
            template = self.vip_templates[vip_type]
            title = random.choice(template["titles"])
            name = random.choice(self.surnames)
            role = random.choice(template["roles"])

            character = SpecialCharacter(
                title=f"{vip_type} {title}",
                name=name,
                role=role,
                specialization="VIP"
            )

            character.rewards = dict(template["rewards"])
            character.special_abilities = list(template["special_abilities"])
            reputation_multiplier = 1 + (self.game.ship.passenger_reputation / 100)
            character.rewards["base_money"] = int(character.rewards["base_money"] * reputation_multiplier)
            return character

        elif char_type == "PirateCaptain":
            title = "Rogue Captain"
            name = f"Captain {random.choice(self.surnames)}"
            character = SpecialCharacter(title, name, "pirate", "combat")
            character.combat_stats = {
                "attack": 3,
                "defense": 2,
                "reward": random.randint(5000, 15000)
            }
            return character

        elif char_type in ["Neurodroid", "Agrobot"]:
            title = f"{char_type} Leader"
            name = f"Unit-{random.randint(1000,9999)}"
            character = SpecialCharacter(title, name, "synthetic", char_type.lower())
            character.demand = random.randint(10000, 50000)
            character.uprising_chance = 0.3
            return character

        return None

    # Added to SpecialCharacterGenerator class for vip passengers
    def add_vip_templates(self):
        """Add VIP passenger templates to character generator"""
        self.vip_templates = {
            "Corporate": {
                "titles": ["CEO", "Director", "Executive"],
                "roles": ["business", "finance", "trade"],
                "rewards": {
                    "base_money": 10000,
                    "reputation": 15,
                    "plot_points": 5
                },
                "special_abilities": ["market_insider"]
            },
            "Political": {
                "titles": ["Senator", "Councilor", "Minister"],
                "roles": ["governance", "diplomacy", "policy"],
                "rewards": {
                    "base_money": 14000,
                    "reputation": 20,
                    "plot_points": 8
                },
                "special_abilities": ["system_influence"]
            },
            "Scientific": {
                "titles": ["Professor", "Director", "Chief Researcher"],
                "roles": ["research", "development", "innovation"],
                "rewards": {
                    "base_money": 12000,
                    "reputation": 18,
                    "plot_points": 10
                },
                "special_abilities": ["research_bonus"]
            }
        }

    def generate_vip_passenger(self):
        """Generate a VIP passenger with special characteristics"""
        vip_type = random.choice(list(self.vip_templates.keys()))
        template = self.vip_templates[vip_type]

        title = random.choice(template["titles"])
        name = random.choice(self.surnames)
        role = random.choice(template["roles"])

        character = SpecialCharacter(
            title=f"{vip_type} {title}",
            name=name,
            role=role,
            specialization="VIP"
        )

        # Add VIP-specific attributes
        character.rewards = dict(template["rewards"])
        character.special_abilities = list(template["special_abilities"])

        # Scale rewards based on reputation
        reputation_multiplier = 1 + (self.game.ship.passenger_reputation / 100)
        character.rewards["base_money"] = int(character.rewards["base_money"] * reputation_multiplier)

        return character

class Quest:
    def __init__(self, name, description, reward_money, reward_rp, quest_type="generic",
                 requirements=None, on_complete=None, milestone=None, destination=None, rewards=None):
        self.name = name
        self.description = description
        self.destination = destination
        self.reward_money = reward_money
        self.reward_rp = reward_rp  # Research Points reward
        self.quest_type = quest_type
        self.requirements = requirements or {}
        self.on_complete = on_complete
        self.milestone = milestone
        self.progress = 0
        self.completed = False
        self.target_progress = self.requirements.get('target_progress', 1)
        self.location_requirement = self.requirements.get('location_type', None)
        # Add additional rewards handling
        self.rewards = rewards or {}  # Store extra rewards like items

    def __eq__(self, other):
        """Define equality to help prevent duplicates"""
        if not isinstance(other, Quest):
            return False
        return (self.name == other.name and
                self.quest_type == other.quest_type)

    # Cantina quests from listen to gossip, added to Quest class
    def update_cantina_progress(self, event_data):
        """Update cantina quests based on trade actions"""
        if self.quest_type == "cantina":
            action = event_data.get("action", "")

            if action in ["buy", "sell"]:
                commodity = event_data.get("commodity")
                amount = event_data.get("amount", 0)

                if "Deliver" in self.name and commodity:
                    target_commodity = self.name.split()[2].lower()
                    if commodity == target_commodity:
                        self.progress += amount
                        return self.progress >= self.requirements.get("amount", 0)

            elif action == "passenger_delivered":
                self.progress += 1
                return self.progress >= self.requirements.get("count", 0)

        return False


    # What each kind of quest counts, and which requirement holds the target.
    # Quests count from the moment they were taken, never from the start of the game.
    COUNTED = {
        "combat": ("victories.{enemy_type}", ("amount", "victories"), 1, "victories"),
        "patrol": ("turn", ("turns", "patrol_turns"), 3, "turns on duty"),
        "research": ("research_gained", ("target_points",), 30, "research points gained"),
        "mining": ("acquired.{resource_type}", ("amount",), 50, "units"),
        "exploration": ("discovered.{location_type}", ("amount", "discoveries"), 1, "discoveries"),
        "rescue": ("events.disaster", ("rescues",), 1, "ships helped"),
        "trade": ("trades", ("trades",), 1, "trades"),
    }
    # Quests finished by arriving somewhere with something: (what, requirement key, amount key)
    DELIVERED = {
        "delivery": ("cargo", "commodity", "amount"),
        "mining_contract": ("cargo", "resource", "amount"),
        "item_delivery": ("item", "item", None),
        "character_delivery": ("passenger", "character", None),
        "story": ("visit", None, None),
    }

    def begin(self, game):
        """Remember where the counters stood when the quest was taken."""
        if not isinstance(getattr(self, "start", None), dict):
            self.start = game.quest_system.counters()

    def counted(self, game):
        """(done, target, unit) for a counted quest, or None."""
        spec = self.COUNTED.get(self.quest_type)
        if spec is None:
            return None
        key, target_keys, default, unit = spec
        fields = dict(self.requirements)
        fields.setdefault("enemy_type", "total")
        fields.setdefault("location_type", "any")
        fields.setdefault("resource_type", "salt")
        key = key.format(**fields)
        target = next((self.requirements[k] for k in target_keys if k in self.requirements), default)
        self.begin(game)
        now = game.quest_system.counters()
        done = now.get(key, 0) - self.start.get(key, 0)
        if self.quest_type == "mining":
            unit = self.requirements.get("resource_type", "salt")
        return max(0, int(done)), int(target), unit

    def holding(self, game):
        """For a delivery: does the ship carry what is to be delivered?"""
        what, key, amount_key = self.DELIVERED[self.quest_type]
        ship = game.ship
        if what == "cargo":
            return ship.cargo.get(self.requirements.get(key), 0) >= self.requirements.get(amount_key, 0)
        if what == "item":
            return ship.items.get(self.requirements.get(key), 0) > 0
        if what == "passenger":
            return self.quest_passenger(game) is not None
        return True

    def quest_passenger(self, game):
        for module in getattr(game.ship, "passenger_modules", []):
            for passenger in module.passengers:
                if passenger.name == self.requirements.get("character"):
                    return passenger
        return None

    def progress_text(self, game):
        counted = self.counted(game)
        if counted:
            done, target, unit = counted
            text = "%d/%d %s" % (min(done, target), target, unit)
            if self.quest_type == "trade" and self.requirements.get("min_profit"):
                profit = game.quest_system.counters()["profit"] - self.start.get("profit", 0)
                text += ", %s/%s profit" % (game.format_money(max(0, profit)),
                                            game.format_money(self.requirements["min_profit"]))
            return text
        if self.quest_type in self.DELIVERED:
            where = self.destination or "?"
            if self.quest_type == "story":
                return "go to %s" % where
            return "%s, then go to %s" % ("ready" if self.holding(game) else "not aboard yet", where)
        if self.quest_type.startswith("unlock_"):
            return "follow the lead: your next journey"
        return ""

    def check_completion(self, game):
        """Check if quest requirements are met"""
        if self.completed:
            return False
        counted = self.counted(game)
        if counted:
            done, target, _ = counted
            if self.quest_type == "trade" and self.requirements.get("min_profit"):
                profit = game.quest_system.counters()["profit"] - self.start.get("profit", 0)
                if profit < self.requirements["min_profit"]:
                    return False
            return done >= target
        if self.quest_type in self.DELIVERED:
            return game.current_location.name == self.destination and self.holding(game)
        # Generic quest completion check (location unlocks: a journey)
        return self.progress >= self.target_progress

    def hand_over(self, game):
        """A finished delivery leaves the ship: cargo, item or passenger."""
        what, key, amount_key = self.DELIVERED.get(self.quest_type, (None, None, None))
        ship = game.ship
        if what == "cargo":
            item = self.requirements.get(key)
            ship.cargo[item] = max(0, ship.cargo.get(item, 0) - self.requirements.get(amount_key, 0))
        elif what == "item":
            item = self.requirements.get(key)
            ship.items[item] = ship.items.get(item, 0) - 1
            if ship.items[item] <= 0:
                del ship.items[item]
        elif what == "passenger":
            passenger = self.quest_passenger(game)
            for module in getattr(ship, "passenger_modules", []):
                if passenger in module.passengers:
                    module.passengers.remove(passenger)

    def update_progress(self, event_data):
        """Update quest progress based on game events"""
        if self.completed:
            return False

        progress_made = False

        # Update based on event type
        if event_data.get("type") == "combat" and self.quest_type == "combat":
            if event_data.get("outcome") == "victory":
                self.progress += 1
                progress_made = True

        elif event_data.get("action") in ["buy", "sell"] and self.quest_type == "trade":
            commodity = event_data.get("commodity")
            if commodity == self.requirements.get("commodity"):
                self.progress += event_data.get("amount", 0)
                progress_made = True

        return progress_made

    def complete(self, game):
        """Complete the quest (the quest system pays the rewards)."""
        game.quest_system.complete_quest(self)


class Contract:
    def __init__(self, contract_type, duration, requirements, rewards, description):
        self.contract_type = contract_type
        self.duration = duration
        self.requirements = requirements
        self.rewards = rewards
        self.description = description
        self.progress = {
            'amount': 0,
            'destinations_visited': set(),
            'passengers_delivered': 0,
            'source_visited': False,
            'turns_remaining': duration
        }
        self.completed = False
        self.rewards_claimed = False
        self.failed = False
        self.last_update_turn = None
        self.trade_history = []

    def update_progress(self, event_data):
        """Enhanced progress update with trade history tracking"""
        current_location = event_data.get("location")
        action = event_data.get("action", "")
        commodity = event_data.get("commodity")
        current_turn = event_data.get("turn", 0)

        # Update turns only when it's a new turn
        if self.last_update_turn != current_turn:
            self.progress['turns_remaining'] -= 1
            self.last_update_turn = current_turn

        if self.progress['turns_remaining'] <= 0:
            self.failed = True
            return {"status": "failed", "reason": "time_expired"}

        # Record location visit
        if current_location:
            self.progress['destinations_visited'].add(current_location)

        if self.contract_type == "cargo":
            # Track source visit through buy action
            if action == "buy" and current_location == self.requirements.get("source"):
                self.progress["source_visited"] = True

            elif action == "sell" and commodity == self.requirements.get("cargo_type"):
                amount = event_data.get("amount", 0)

                if (current_location == self.requirements.get("destination") and
                    self.progress["source_visited"]):

                    # Record trade in history
                    self.trade_history.append({
                        'turn': current_turn,
                        'amount': amount,
                        'location': current_location
                    })

                    self.progress['amount'] += amount

                    if self.progress['amount'] >= self.requirements.get('min_amount', 0):
                        self.completed = True
                        return {
                            "status": "completed",
                            "message": f"Contract completed! Visit Contract Management to claim rewards."
                        }

                    return {
                        "status": "updated",
                        "trade_recorded": True,
                        "new_amount": self.progress['amount'],
                        "message": f"Delivered: {self.progress['amount']}/{self.requirements.get('min_amount')} {commodity}"
                    }

        elif self.contract_type == "passenger":
            # Handle passenger delivery
            if current_location == self.requirements.get("destination"):
                passenger_data = event_data.get("passenger_data")
                if passenger_data:
                    count = 1
                    if "passenger_class" in self.requirements:
                        if passenger_data["class"] == self.requirements["passenger_class"]:
                            self.progress['passengers_delivered'] += count
                            # Record delivery in history
                            self.trade_history.append({
                                'turn': current_turn,
                                'count': count,
                                'location': current_location
                            })
                    else:
                        self.progress['passengers_delivered'] += count
                        # Record delivery in history
                        self.trade_history.append({
                            'turn': current_turn,
                            'count': count,
                            'location': current_location
                        })

                    # Check completion
                    if (self.progress['passengers_delivered'] >= self.requirements.get('count',
                        self.requirements.get('passenger_count', 0))):
                        self.completed = True
                        return {
                            "status": "completed",
                            "message": f"Contract completed! Visit Contract Management to claim rewards."
                        }

        return {"status": "in_progress"}

    def get_status_display(self):
        """Get formatted status display"""
        if self.completed:
            return "✓ COMPLETED - Ready to claim"
        elif self.failed:
            return "✗ FAILED - Time expired"

        status_lines = [
            f"Time remaining: {self.progress['turns_remaining']} turns"
        ]

        if self.contract_type == "cargo":
            cargo_type = self.requirements.get('cargo_type')
            status_lines.extend([
                f"Source ({self.requirements['source']}): {'✓ Visited' if self.progress['source_visited'] else '□ Not visited'}",
                f"Destination ({self.requirements['destination']}): {'✓ Visited' if self.requirements['destination'] in self.progress['destinations_visited'] else '□ Not visited'}",
                f"Delivered: {self.progress['amount']}/{self.requirements.get('min_amount')} {cargo_type}"
            ])
        elif self.contract_type == "passenger":
            status_lines.extend([
                f"Passengers: {self.progress['passengers_delivered']}/{self.requirements.get('count', self.requirements.get('passenger_count', 0))}",
                f"Class: {self.requirements.get('passenger_class', 'Any')}"
            ])

        return "\n".join(status_lines)

    def get_trade_history_display(self):
        """Get formatted trade history"""
        if not hasattr(self, 'trade_history') or not self.trade_history:
            return "No trade history recorded"

        history_lines = []
        if self.contract_type == "cargo":
            for trade in self.trade_history:
                history_lines.append(
                    f"Turn {trade.get('turn', '?')}: Delivered {trade.get('amount', 0)} units of {self.requirements.get('cargo_type', 'cargo')} at {trade.get('location', 'Unknown')}"
                )
        elif self.contract_type == "passenger":
            for trade in self.trade_history:
                history_lines.append(
                    f"Turn {trade.get('turn', '?')}: Delivered {trade.get('count', 1)} passengers at {trade.get('location', 'Unknown')}"
                )

        return "\n".join(history_lines) if history_lines else "No trade history recorded"

    def calculate_final_reward(self):
        """Calculate final reward with bonuses"""
        if not self.completed:
            return None

        total_reward = dict(self.rewards)

        # Early completion bonus
        if self.progress['turns_remaining'] > self.duration / 2:
            total_reward["money"] = int(total_reward["money"] * 1.5)
            total_reward["reputation"] = int(total_reward["reputation"] * 1.2)

        # Overdelivery bonus for cargo contracts
        if self.contract_type == "cargo":
            required_amount = self.requirements.get('min_amount', 0)
            if self.progress['amount'] > required_amount * 1.5:  # 50% more than required
                total_reward["money"] = int(total_reward["money"] * 1.2)

        # High satisfaction bonus for passenger contracts
        if self.contract_type == "passenger":
            if "min_satisfaction" in self.requirements:
                avg_satisfaction = sum(p.get("satisfaction", 0) for p in self.trade_history) / len(self.trade_history) if self.trade_history else 0
                if avg_satisfaction > self.requirements["min_satisfaction"] * 1.2:  # 20% above minimum
                    total_reward["reputation"] = int(total_reward["reputation"] * 1.3)

        return total_reward

    def check_requirements(self):
        """Check if all requirements are met"""
        if self.contract_type == "cargo":
            return (
                self.progress["source_visited"] and
                self.requirements["destination"] in self.progress["destinations_visited"] and
                self.progress["amount"] >= self.requirements.get("min_amount", 0)
            )
        elif self.contract_type == "passenger":
            return (
                self.progress["passengers_delivered"] >= self.requirements.get("count",
                    self.requirements.get("passenger_count", 0))
            )
        return False


class PassengerModule:
    def __init__(self, name, capacity, comfort_level, cost):
        self.name = name
        self.capacity = capacity  # How many passengers it can hold
        self.comfort_level = comfort_level  # 1-5, affects passenger satisfaction and payment
        self.cost = cost
        self.passengers = []

class Passenger:
    def __init__(self, name, destination, wealth_level):
        self.name = name
        self.destination = destination
        self.wealth_level = wealth_level  # 1-5
        self.satisfaction = 100
        self.turns_waiting = 0
        # Add passenger classification
        self.classification = self.generate_classification()

    def generate_classification(self):
        classifications = [
            ("S", "Scientist", "science"),
            ("M", "Military", "military"),
            ("E", "Engineer", "engineering"),
            ("T", "Trader", "trade"),
            ("D", "Diplomat", "diplomacy"),
            ("R", "Researcher", "research")
        ]
        class_code, class_name, class_type = random.choice(classifications)
        return {
            "code": class_code,
            "name": class_name,
            "type": class_type
        }


class Port:
    def __init__(self, game):
        self.game = game
        self.available_modules = {
                "1": {
                    "name": "Basic Passenger",
                    "capacity": 4,
                    "comfort_level": 1,
                    "cost": 5000
                },
                "2": {
                    "name": "Standard Passenger",
                    "capacity": 8,
                    "comfort_level": 2,
                    "cost": 10000
                },
                "3": {
                    "name": "Luxury Passenger",
                    "capacity": 4,
                    "comfort_level": 4,
                    "cost": 20000
                },
                "4": {
                    "name": "Life Support Module",
                    "capacity": 4,
                    "comfort_level": 1,
                    "cost": 8000
                },
                "5": {
                    "name": "Business Class A",
                    "capacity": 2,
                    "comfort_level": 5,
                    "cost": 25000
                },
                "6": {
                    "name": "Research Lab Module",
                    "capacity": 2,
                    "comfort_level": 3,
                    "cost": 30000,
                    "special": "research_bonus"
                },
                "7": {
                    "name": "Colony Transport Mod.",
                    "capacity": 12,
                    "comfort_level": 2,
                    "cost": 35000,
                    "special": "colonist_bonus"
                },
                "8": {
                    "name": "Diplomatic Suite Mod.",
                    "capacity": 1,
                    "comfort_level": 6,
                    "cost": 40000,
                    "special": "diplomatic_bonus"
                }
            }

        # List of passengers waiting at each location
        self.waiting_passengers = {}

        # Passenger names for random generation
        self.first_names = ["John", "Emma", "Zara", "Chen", "Raj", "Ana", "Igor", "Yuki", "Omar", "Luna"]
        self.last_names = ["Smith", "Patel", "Wong", "Garcia", "Petrov", "Tanaka", "Mueller", "Kim", "Hassan", "Silva"]


    def generate_passenger(self, current_location):
        """Generate a random passenger"""
        name = f"{random.choice(self.first_names)} {random.choice(self.last_names)}"
        # Choose destination from known locations except current
        possible_destinations = [loc for loc in self.game.known_locations if loc != current_location]
        if not possible_destinations:
            return None
        destination = random.choice(possible_destinations)
        wealth_level = random.randint(1, 5)
        return Passenger(name, destination, wealth_level)


    def update_passengers(self, location):
        """Update passenger list at a location (once per turn: new arrivals, longer waits)"""
        if location not in self.waiting_passengers:
            self.waiting_passengers[location] = []
        updated = self.__dict__.setdefault("updated_turn", {})
        if updated.get(location) == self.game.turn:
            return
        updated[location] = self.game.turn

        # Remove passengers waiting too long (a quest's passenger waits for you)
        self.waiting_passengers[location] = [p for p in self.waiting_passengers[location]
                                           if p.turns_waiting < 10 or getattr(p, "is_quest_passenger", False)]

        # Check for special character spawning
        if random.random() < 0.2:  # 20% chance per turn
            self.game.reputation_manager.spawn_special_passenger()

        # Add new passengers (1-3 per turn)
        new_passengers = random.randint(1, 3)
        for _ in range(new_passengers):
            passenger = self.generate_passenger(location)
            if passenger:
                self.waiting_passengers[location].append(passenger)

        # Update waiting turns
        for passenger in self.waiting_passengers[location]:
            passenger.turns_waiting += 1


    def calculate_fare(self, passenger, module):
        """Calculate passenger fare based on distance, comfort, and wealth"""
        base_fare = 100 * passenger.wealth_level
        comfort_multiplier = 1 + (module.comfort_level * 0.2)
        distance_multiplier = 1.25 if self.game.ship.items.get("temporal_accelerator") else 1
        if "steward" in self.game.ship.crew:          # a steward makes any cabin feel first class
            comfort_multiplier += 0.15

        # Add distance calculation if game has that mechanic
        # distance_multiplier = calculate_distance(current, destination)

        return int(base_fare * comfort_multiplier * distance_multiplier)

    def display_port_info(self):
        """Display port information and options"""
        content = []

        # Show installed modules
        content.append(["Installed Passenger Modules"])
        if hasattr(self.game.ship, 'passenger_modules'):
            for module in self.game.ship.passenger_modules:
                passengers = len(module.passengers)
                content.append([
                    f"{module.name}",
                    f"({passengers}/{module.capacity} passengers)",
                    f"Comfort Lvl.: {module.comfort_level}"
                ])
        else:
            content.append(["No passenger modules installed"])

        # Show current passengers
        content.append([""])
        content.append(["Current Passengers"])
        total_passengers = 0
        if hasattr(self.game.ship, 'passenger_modules'):
            for module in self.game.ship.passenger_modules:
                for passenger in module.passengers:
                    total_passengers += 1
                    content.append([
                        f"{passenger.name}",
                        f"→ {passenger.destination}",
                        f"Satisfaction: {passenger.satisfaction}%"
                    ])
        if total_passengers == 0:
            content.append(["No passengers currently aboard"])

        # Show waiting passengers at current location
        content.append([""])
        content.append(["Waiting Passengers"])
        location = self.game.current_location.name
        if location in self.waiting_passengers and self.waiting_passengers[location]:
            for passenger in self.waiting_passengers[location]:
                content.append([
                    f"{passenger.name}",
                    f"→ {passenger.destination}",
                    f"Class: {passenger.wealth_level}"
                ])
        else:
            content.append(["No passengers waiting"])

        return self.game.create_box(content, 'double')


    def handle_port_menu(self):
        """Handle port menu options"""
        self.game.clear_screen()
        self.game.display_simple_message("Welcome to the Stardock Port!", 0)
        self.game.story.visit_venue("port")

        while True:
            options = {
                'view': ('v', "View Port Info"),
                'modules': ('m', "Purchase Modules"),
                'board': ('b', "Board Passengers"),
                'unload': ('u', "Unload Passengers"),
                'contracts': ('c', "Manage Contracts"),
                'prices': ('pr', "Ask the broker robot about prices elsewhere"),
                'travel': ('t', "Travel"),
                'back': ('', "Return to Main Menu")
            }

            # Show menu
            menu_content = [[f"Port Services {self.game.current_location.name} | PAX Checkout: {sum(len(module.passengers) for module in self.game.ship.passenger_modules)}/{sum(module.capacity for module in self.game.ship.passenger_modules)}"]]
            menu_content.append([f""])
            for cmd, (shortcut, desc) in options.items():
                menu_content.append([f"{cmd}/{shortcut if shortcut else ''}: {desc}"])
            print(self.game.create_box(menu_content, 'single'))

            valid_inputs = [cmd for cmd in options.keys()] + [s[0] for s in options.values() if s[0]]
            action = self.game.validate_input("Port - choose (Enter to leave): ", valid_inputs)

            if action in ['back', None]:
                break

            elif action in ['view', 'v']:
                print(self.display_port_info())
                time.sleep(2)

            elif action in ['modules', 'm']:
                self.handle_module_purchase()

            elif action in ['board', 'b']:
                self.handle_passenger_boarding()

            elif action in ['unload', 'u']:
                self.handle_passenger_unloading()
                time.sleep(2)

            elif action in ['contracts', 'c']:
                self.game.contract_manager.handle_contract_menu()

            elif action in ['prices', 'pr']:
                self.game.show_forecast(self.game.story.fill("{port_broker}, the port's broker robot, "
                                                             "quotes other docks"))

            elif action in ['travel', 't']:
                if self.game.handle_travel():
                    break

            self.game.clear_screen()

    def handle_module_purchase(self):
        """Handle purchase of new modules with numbered selection"""
        while True:
#            self.game.clear_screen()
            content = [["", f"¤: {self.game.format_money(self.game.ship.money)}"]]
    #        content.append([""])  # Empty line for spacing
            content.append(["#", "Module Types:", "Cap.", "Comf.", "Cost"])
#            content.append(["#", "Module Types:", "Cap.", "Comf.", "Cost", "Special"])

            for module_id, module in self.available_modules.items():
                special = module.get("special", "-")
                content.append([
                    module_id,
                    module["name"],
                    str(module["capacity"]),
                    str(module["comfort_level"]),
                    str(self.game.format_money(module["cost"])),
#                    special #yet uinimplemented module special
                ])

            print(self.game.create_box(content, 'double'))

            module_id = self.game.validate_input(
                "Enter module number to buy (or 'back'): ",
                list(self.available_modules.keys()) + ['back']
            )

            if module_id == 'back':
                self.game.clear_screen()
                return

            if module_id in self.available_modules:
                module = self.available_modules[module_id]
                if self.game.ship.money >= module["cost"]:
                    self.game.ship.money -= module["cost"]

                    if not hasattr(self.game.ship, 'passenger_modules'):
                        self.game.ship.passenger_modules = []

                    new_module = PassengerModule(
                        module["name"],
                        module["capacity"],
                        module["comfort_level"],
                        module["cost"]
                    )
                    if "special" in module:
                        new_module.special = module["special"]

                    self.game.ship.passenger_modules.append(new_module)

                    self.game.display_simple_message(f"Purchased {module['name']}!")
#                    time.sleep(1)
                    self.game.clear_screen()
                    return
                else:
                    self.game.display_simple_message("Not enough money!")
#                    time.sleep(1)
                    self.game.clear_screen()
                    return


    def handle_passenger_boarding(self):
        """Handle passenger boarding with removal from waiting list"""
        while True:
            location = self.game.current_location.name

            if not hasattr(self.game.ship, 'passenger_modules'):
                self.game.display_simple_message("No passenger modules installed!")
                self.game.clear_screen()
                return

            if location not in self.waiting_passengers or not self.waiting_passengers[location]:
                self.game.display_simple_message("No passengers waiting!")
                self.game.clear_screen()
                return

            available_modules = [m for m in self.game.ship.passenger_modules
                            if len(m.passengers) < m.capacity]

            if not available_modules:
                self.game.display_simple_message("No room for more passengers!")
                self.game.clear_screen()
                return

            # Show module status
            self.display_module_status()

            # Show waiting passengers
            self.display_waiting_passengers()

            # Get command
            self.game.display_simple_message(
                "Enter numbers to select passengers, 'refresh/r' to refresh list, 'autoboard/a' for auto boarding, or Enter to cancel:", 0
            )

            selection = input(">>> ").strip().lower()

            if not selection:  # Empty Enter
                return

            if selection in ['refresh', 'r']:
                # Regenerate waiting passengers
                self.update_passengers(location)
                continue

            if selection in ['autoboard', 'a']:
                self.handle_autoboard(available_modules)
                continue

            try:
                # Parse space-separated numbers
                passenger_nums = [int(num) - 1 for num in selection.split()]
                waiting_passengers = self.waiting_passengers[location]

                # Validate numbers and get passengers
                selected_passengers = []
                if all(0 <= num < len(waiting_passengers) for num in passenger_nums):
                    # Get passengers and remove them from waiting list
                    selected_passengers = [waiting_passengers[num] for num in sorted(passenger_nums, reverse=True)]
                    for num in sorted(passenger_nums, reverse=True):
                        del waiting_passengers[num]

                    if selected_passengers:
                        self.handle_module_assignment(selected_passengers, available_modules)
                else:
                    self.game.display_simple_message("Invalid passenger number(s)")

            except ValueError:
                self.game.display_simple_message("Invalid input. Please enter numbers separated by spaces.")

    def handle_passenger_unloading(self):
            """Handle passenger unloading with reputation effects and bonuses"""
            if not hasattr(self.game.ship, 'passenger_modules'):
                self.game.display_simple_message("No passenger modules installed!")
                return

            current_location = self.game.current_location.name
            passengers_to_unload = []
            total_earnings = 0

            # Find passengers that have reached their destination
            for module in self.game.ship.passenger_modules:
                for passenger in module.passengers[:]:
                    if passenger.destination == current_location:
                        # Calculate fare with reputation multiplier
                        base_fare = self.calculate_fare(passenger, module)
                        reputation_multiplier = self.game.reputation_manager.get_fare_multiplier()
                        satisfaction_multiplier = passenger.satisfaction / 100
                        bonus_multiplier = 1.0  # Default multiplier

                        # Apply organization bonus if applicable
                        org_bonus = self.get_bonus_type(passenger)
                        bonus_message = None
                        if org_bonus:
                            org_name, multiplier, message = org_bonus
                            bonus_multiplier = multiplier
                            bonus_message = f"{org_name} doubles the revenue! {message} Plot points +1"
                            self.game.story_manager.plot_points += 1

                        # Calculate final payment with all multipliers
                        final_payment = int(base_fare * satisfaction_multiplier * reputation_multiplier * bonus_multiplier)

                        # Update reputation based on passenger satisfaction
                        reputation_change = self.game.reputation_manager.update_reputation(passenger.satisfaction, passenger)

                        # Handle special passengers
                        if hasattr(passenger, 'is_vip'):
                            self.game.reputation_manager.handle_vip_delivery(passenger)

                        # Update contract progress if available
                        if hasattr(self.game, 'contract_manager'):
                            passenger_data = {
                                "class": passenger.classification["code"],
                                "satisfaction": passenger.satisfaction
                            }
                            event_data = {
                                "location": current_location,
                                "passenger_data": passenger_data,
                                "action": "unload"
                            }
                            for contract in self.game.contract_manager.active_contracts:
                                contract.update_progress(event_data)

                        # Increment total passengers delivered
                        self.game.reputation_manager.total_passengers += 1

                        # Record unloading result
                        passengers_to_unload.append({
                            'passenger': passenger,
                            'payment': final_payment,
                            'satisfaction': passenger.satisfaction,
                            'reputation_change': reputation_change,
                            'bonus_message': bonus_message
                        })

                        # Apply payment and remove passenger
                        self.game.ship.money += final_payment
                        module.passengers.remove(passenger)
                        total_earnings += final_payment

            # Display unloading results
            if passengers_to_unload:
                content = [["Passengers Disembarked"]]

                for result in passengers_to_unload:
                    passenger = result['passenger']
                    content.append([
                        passenger.name,
                        f"Fare: {self.game.format_money(result['payment'])}",
                        f"Satisfied: {result['satisfaction']}%"
                    ])

                    # Add reputation change if significant
                    if abs(result['reputation_change']) >= 0.1:
                        content.append([
                            f"└─ Reputation Change: {'+' if result['reputation_change'] > 0 else ''}{result['reputation_change']:.1f}"
                        ])

                    # Add bonus message if any
                    if result['bonus_message']:
                        content.append([f"└─ {result['bonus_message']}"])

                content.append([""])
                content.append([f"Total Earnings: {self.game.format_money(total_earnings)}"])

                print(self.game.create_box(content, 'double'))
            else:
                self.game.display_simple_message("No passengers to unload here!")
#                self.game.clear_screen()

    def get_bonus_type(self, passenger):
        """Get bonus type based on passenger classification"""
        bonus_types = {
            "S": ("Scientific Institute", 2.0, "Scientific research strengthened!"),
            "M": ("Planetary Defense Council", 3.0, "Military recruitment enhanced!"),
            "E": ("Engineering Corps", 2.5, "Engineering capacity expanded!"),
            "T": ("Trade Federation", 2.0, "Commercial networks expanded!"),
            "D": ("Diplomatic Service", 3.0, "Diplomatic relations improved!"),
            "R": ("Research Foundation", 2.5, "Research capabilities enhanced!")
        }
        passenger_class = passenger.classification["code"]
        if random.random() < 0.3:  # 30% chance for bonus
            return bonus_types.get(passenger_class)
        return None


    def handle_autoboard(self, available_modules):
        """Handle automatic passenger boarding based on destination"""
        location = self.game.current_location.name
        waiting_passengers = self.waiting_passengers[location]

        # Get unique destinations
        destinations = sorted(set(p.destination for p in waiting_passengers))

        # Show destinations
        content = [["Available Destinations"]]
        for i, dest in enumerate(destinations, 1):
            matching = sum(1 for p in waiting_passengers if p.destination == dest)
            content.append([f"{i}. {dest}", f"{matching} passengers waiting"])
        print(self.game.create_box(content, 'single'))

        # Get destination choice
        self.game.display_simple_message("Choose destination number:", 0)
        try:
            choice = int(input(">>> "))
            if 1 <= choice <= len(destinations):
                target_dest = destinations[choice-1]

                # Get matching passengers
                matching_passengers = [p for p in waiting_passengers if p.destination == target_dest]

                # Board as many as possible
                modules_space = sum(m.capacity - len(m.passengers) for m in available_modules)
                to_board = matching_passengers[:modules_space]

                if to_board:
                    self.handle_module_assignment(to_board, available_modules)
                else:
                    self.game.display_simple_message("No matching passengers to board!")

        except (ValueError, IndexError):
            self.game.display_simple_message("Invalid choice!")

    def display_module_status(self):
        """Display current module status"""
        module_status = [["Current Module Status"]]
        for module in self.game.ship.passenger_modules:
            passengers_info = []
            for p in module.passengers:
                passengers_info.append(f"{p.name} [{p.classification['code']}] → {p.destination}")
            module_status.append([
                f"{module.name}",
                f"({len(module.passengers)}/{module.capacity})",
                f"Comfort: {module.comfort_level}"
            ])
            for p_info in passengers_info:
                module_status.append([f"└─ {p_info}"])
        print(self.game.create_box(module_status, 'single'))

    def display_waiting_passengers(self):
        """Display waiting passengers"""
        location = self.game.current_location.name
        content = [[""]]
        content.append(["#", f"Waiting on {location}", "Dest.", "Cls.", "≈Fare"])

        waiting_passengers = self.waiting_passengers[location]
        for i, passenger in enumerate(waiting_passengers, 1):
            best_module = max(
                (m for m in self.game.ship.passenger_modules if len(m.passengers) < m.capacity),
                key=lambda m: m.comfort_level
            )
            est_fare = self.calculate_fare(passenger, best_module)
            content.append([
                str(i),
                f"{passenger.name} [{passenger.classification['code']}]",
                passenger.destination,
                f"L{passenger.wealth_level}",
                self.game.format_money(est_fare)
            ])

        print(self.game.create_box(content, 'double'))

    def handle_module_assignment(self, selected_passengers, available_modules):
        """Handle assigning selected passengers to modules"""
        passengers_left = selected_passengers.copy()

        while passengers_left and available_modules:
            # Show remaining passengers
            content = [["Remaining Passengers"]]
            for i, passenger in enumerate(passengers_left, 1):
                content.append([
                    f"{i}. {passenger.name} [{passenger.classification['code']}]",
                    passenger.destination
                ])
            print(self.game.create_box(content, 'single'))

            # Show available modules
            module_content = [["Available Modules"]]
            for i, module in enumerate(available_modules, 1):
                module_content.append([
                    f"{i}. {module.name}",
                    f"({len(module.passengers)}/{module.capacity})",
                    f"Comfort: {module.comfort_level}"
                ])
            print(self.game.create_box(module_content, 'single'))

            # Get module choice with auto option
            self.game.display_simple_message(
                "Choose module number, 'auto/a' for automatic assignment, or 'back':", 0
            )
            choice = input(">>> ").strip().lower()

            if choice == 'back':
                break

            if choice in ['auto', 'a']:
                self.auto_assign_modules(passengers_left, available_modules)
                break

            try:
                module_num = int(choice)
                if 1 <= module_num <= len(available_modules):
                    chosen_module = available_modules[module_num - 1]
                    if len(chosen_module.passengers) >= chosen_module.capacity:
                        self.game.display_simple_message("Module is full!")
                        continue

                    # Add first remaining passenger
                    passenger = passengers_left.pop(0)
                    chosen_module.passengers.append(passenger)
                    self.game.display_simple_message(f"Assigned {passenger.name} to {chosen_module.name}")

                    # Remove full modules from available list
                    if len(chosen_module.passengers) >= chosen_module.capacity:
                        available_modules.remove(chosen_module)
                else:
                    self.game.display_simple_message("Invalid module number")
            except ValueError:
                self.game.display_simple_message("Invalid input")

    def auto_assign_modules(self, passengers, modules):
        """Automatically assign passengers to modules"""
        # Sort modules by comfort level (highest first)
        sorted_modules = sorted(modules, key=lambda m: m.comfort_level, reverse=True)

        # Sort passengers by wealth level (highest first)
        sorted_passengers = sorted(passengers, key=lambda p: p.wealth_level, reverse=True)

        assigned = 0
        location = self.game.current_location.name

        for passenger in sorted_passengers[:]:  # Use slice to create copy for iteration
            for module in sorted_modules:
                if len(module.passengers) < module.capacity:
                    module.passengers.append(passenger)
                    if passenger in self.waiting_passengers[location]:  # Remove from waiting list
                        self.waiting_passengers[location].remove(passenger)
                    assigned += 1
                    self.game.display_simple_message(
                        f"Auto-assigned {passenger.name} to {module.name}"
                    )
                    break

        remaining = len(passengers) - assigned
        if remaining > 0:
            self.game.display_simple_message(f"Could not assign {remaining} passengers - no space left")


    def update_passenger_satisfaction(self):
        """Update passenger satisfaction during travel"""
        if not hasattr(self.game.ship, 'passenger_modules'):
            return

        for module in self.game.ship.passenger_modules:
            for passenger in module.passengers:
                # Base satisfaction change
                change = 0

                # Comfort level effect
                if module.comfort_level >= passenger.wealth_level:
                    change += 2  # Satisfied with comfort
                else:
                    change -= 3  # Dissatisfied with comfort

                # Ship damage effect
                if self.game.ship.damage > 50:
                    change -= 5
                elif self.game.ship.damage > 25:
                    change -= 2

                # Update satisfaction
                passenger.satisfaction = max(0, min(100, passenger.satisfaction + change))

class Shop:
    def __init__(self):
        self.base_equipment = {
            "navcomp": {
                "price": 500,
                "description": "Navigation computer reveals all destinations",
                "tech_required": 1,
                "plot_required": 0
            },
            "scanner": {
                "price": 700,
                "description": "Basic scanner: tells a real distress call from bait",
                "tech_required": 2,
                "plot_required": 0
            },
            "probe": {
                "price": 900,
                "description": "Deep space probe: scouts debris fields ahead of the ship",
                "tech_required": 3,
                "plot_required": 10
            },
            "turrets": {
                "price": 1200,
                "description": "Defense turrets: better odds in every fight; shred drone swarms",
                "tech_required": 4,
                "plot_required": 15
            },
            "shield": {
                "price": 1500,
                "description": "Energy shield: 30% less fight damage; rides out storms and flares",
                "tech_required": 5,
                "plot_required": 20
            },
            "patcher": {
                "price": 300,
                "description": "Hull patcher: repairs 10% damage after every fight",
                "tech_required": 1,
                "plot_required": 0
            },
            # Transport Equipment
            "cargo_extender": {
                "price": 5000,
                "description": "Increases cargo capacity by 20%",
                "tech_required": 3,
                "plot_required": 25
            },
            "containment_field": {
                "price": 8000,
                "description": "Specialized storage for salt/fuel (+30% capacity)",
                "tech_required": 4,
                "plot_required": 30
            },
            "auto_loader": {
                "price": 12000,
                "description": "Loads and unloads for you: 2% less trade tax",
                "tech_required": 5,
                "plot_required": 35
            },
            # Advanced Transport Equipment
            "quantum_compressor": {
                "price": 20000,
                "description": "Advanced compression (+50% capacity for all cargo)",
                "tech_required": 6,
                "plot_required": 50
            },
            "stasis_vault": {
                "price": 25000,
                "description": "Perfect resource preservation (+75% capacity for special resources)",
                "tech_required": 7,
                "plot_required": 60
            },
            "temporal_accelerator": {
                "price": 30000,
                "description": "Faster deliveries: passengers pay 25% more",
                "tech_required": 8,
                "plot_required": 75
            }
        }

        # Location-specific items with requirements
        self.location_equipment = {
            "AsteroidBase": {
                "mining_laser": {
                    "price": 2000,
                    "description": "Mining laser: +1 defense; cuts drones, derelicts and debris",
                    "tech_required": 3,
                    "plot_required": 15
                },
                "cargo_scanner": {
                    "price": 1800,
                    "description": "Cargo scanner: +20% room for salt and fuel; clean scans for customs",
                    "tech_required": 4,
                    "plot_required": 20
                },
                "shield_booster": {
                    "price": 2500,
                    "description": "Stronger shields: +1 defense in fights",
                    "tech_required": 5,
                    "plot_required": 25
                },
                "mining_compressor": {
                    "price": 15000,
                    "description": "Mining compressor: +40% room for salt and fuel; skims comets",
                    "tech_required": 6,
                    "plot_required": 40
                }
            },
            "DeepSpaceOutpost": {
                "advanced_radar": {
                    "price": 2200,
                    "description": "Radar: slip away before a fight, or jam their targeting",
                    "tech_required": 4,
                    "plot_required": 30
                },
                "combat_drone": {
                    "price": 3000,
                    "description": "Combat drone: +1 attack; sent in first, it takes the first hit",
                    "tech_required": 5,
                    "plot_required": 35
                },
                "repair_bot": {
                    "price": 2800,
                    "description": "Repair bot: fixes breakdowns and some disaster damage",
                    "tech_required": 6,
                    "plot_required": 40
                },
                "emergency_warp": {
                    "price": 18000,
                    "description": "Emergency jump out of any fight or storm",
                    "tech_required": 7,
                    "plot_required": 50
                }
            },
            "ResearchColony": {
                "research_module": {
                    "price": 2500,
                    "description": "+20% research points from travel",
                    "tech_required": 5,
                    "plot_required": 40
                },
                "data_analyzer": {
                    "price": 2800,
                    "description": "+10% research points from travel",
                    "tech_required": 6,
                    "plot_required": 45
                },
                "quantum_scanner": {
                    "price": 3500,
                    "description": "Quantum scanner: +25% discovery rewards; finds weak spots",
                    "tech_required": 7,
                    "plot_required": 50
                },
                "containment_optimizer": {
                    "price": 22000,
                    "description": "Smart cargo optimization (+25% capacity)",
                    "tech_required": 8,
                    "plot_required": 60
                }
            }
        }

        # Track sold items per turn
        # Track items for current turn
        self.current_turn_items = []
        self.sold_items = set()
        self.current_turn = 0
        self.current_offerings = []  # Keep this

        # Track discounts and special offers
        self.current_discounts = {}
        self.special_offers = {}

    def get_available_items(self, location, plot_points):
        """Get available items based on location and plot points"""
        available_pool = []

        # Start with base equipment pool, filtering by requirements
        for name, data in self.base_equipment.items():
            if (location.tech_level >= data["tech_required"] and
                plot_points >= data["plot_required"]):
                available_pool.append((name, data))

        # Add location-specific items if applicable, also filtering
        location_type = location.location_type
        if location_type in self.location_equipment:
            for name, data in self.location_equipment[location_type].items():
                if (location.tech_level >= data["tech_required"] and
                    plot_points >= data["plot_required"]):
                    available_pool.append((name, data))

        # Select random items from filtered pool
        if available_pool:
            selected_items = random.sample(available_pool, min(2, len(available_pool)))
            self.current_offerings = [item[0] for item in selected_items]
            return selected_items

        return []


    def mark_item_sold(self, item_name):
        """Mark an item as sold for this turn"""
        self.sold_items.add(item_name)
        if item_name in self.current_offerings:
            self.current_offerings.remove(item_name)


    def clear_special_offers(self):
        """Clear all special offers"""
        self.current_discounts.clear()

    def is_item_sold(self, item_name):
        """Check if an item has been sold this turn"""
        return item_name in self.sold_items

    def reset_turn(self):
        """Reset shop state for new turn"""
        self.sold_items.clear()
        self.current_offerings.clear()
        self.clear_special_offers()
        self.current_turn_items = []


# Define the Location base class, updated
class Location:
    def __init__(self, name, location_type, tech_level, agri_level, research_points, economy):
        self.name = name
        self.location_type = location_type
        self.tech_level = tech_level
        self.agri_level = agri_level
        self.research_points = research_points
        self.economy = economy
        self.stockmarket_base = False
        self.stockmarket_cost = 5000
        self.buildings = []
        self.exogeology = self.get_base_exogeology()
        self.banned_commodities = []
        self.ban_duration = {}
        self.mineral_deposits = {}
        self.mining_platforms = []
        self.production_cooldown = {}
        # Generate market after initializing attributes
        self.market = self.generate_market()
        self.security_level = 5  # Initialize with medium security level

    @property
    def commands(self):
        """Get all commands for this location"""
        return LocationCommands.get_commands_for_location(self)


    def build_mining_platform(self, deposit_type, cost):
        """Build a new mining platform for specified deposit"""
        if deposit_type in self.mineral_deposits:
            if self.mineral_deposits[deposit_type] > 0:
                self.mining_platforms.append({
                    'type': deposit_type,
                    'efficiency': self.exogeology,
                    'capacity': random.randint(100, 200)
                })
                self.mineral_deposits[deposit_type] -= 1
                return True
        return False

    def generate_market(self):
        # Generate base market prices based on tech and agri levels
        market = {
            'tech': max(10, 100 - (self.tech_level * 10)),
            'agri': 50 + (self.agri_level * 5),
            'salt': 0,
            'fuel': 0
        }

        # Apply refinery effects
        if "Halide Extraction Refinery" in self.buildings:
            # Salt refinery lowers agri prices, sets salt price
            market['salt'] = random.randint(100, 150)
            market['agri'] = max(1, int(market['agri'] * 0.8))

        if "Plasma Catalysis Refinery" in self.buildings:
            # Fuel refinery lowers tech prices, sets fuel price
            market['fuel'] = random.randint(150, 200)
            market['tech'] = max(1, int(market['tech'] * 0.8))

        if "Elemental Fusion Refinery" in self.buildings:
            # Combined refinery raises tech and agri prices
            market['tech'] = int(market['tech'] * 1.3)
            market['agri'] = int(market['agri'] * 1.3)

        return market


    # A full hold (about 440 units) moves a planet's price by about 8%. A stock market
    # makes the market deeper.
    MARKET_DEPTH = {"Planet": 700, "AsteroidBase": 500, "DeepSpaceOutpost": 350, "ResearchColony": 300}
    MARKET_IMPACT = 0.13

    def trades_bulk(self, item):
        """Salt and fuel trade only where they are mined: a platform here, or an asteroid
        base, which mines its own (and is where convoys and in-system ships fuel up)."""
        return self.location_type == "AsteroidBase" or any(p['type'] == item for p in self.mining_platforms)

    def market_depth(self):
        return self.MARKET_DEPTH.get(self.location_type, 400) * (2 if self.stockmarket_base else 1)

    def equilibrium(self):
        """The prices this market drifts back to. A market that opened later (a refinery)
        takes its first price as its usual one."""
        base = self.__dict__.setdefault("base_market", dict(self.market))
        for item, price in self.market.items():
            if price > 0 and not base.get(item):
                base[item] = price
        return base

    def trade_price(self, item, quantity, selling):
        """The average price per unit for a trade of this size: big loads move the price."""
        price = self.market[item]
        shift = self.MARKET_IMPACT * quantity / self.market_depth()
        return price * (1 - shift / 2) if selling else price * (1 + shift / 2)

    def trade_impact(self, item, quantity, selling):
        """After a trade the price stays where the load pushed it, then recovers slowly."""
        base = self.equilibrium().get(item) or self.market[item]
        if self.market[item] <= 0 or base <= 0:
            return
        shift = self.MARKET_IMPACT * quantity / self.market_depth()
        price = self.market[item] * ((1 - shift) if selling else (1 + shift))
        self.market[item] = round(max(base * 0.35, min(base * 2.5, price)), 1)

    def recover(self, rate=0.15):
        """Once a turn: prices drift a little way back to their usual level."""
        base = self.equilibrium()
        for item, price in self.market.items():
            usual = base.get(item, 0)
            if usual > 0 and price > 0:
                self.market[item] = round(price + (usual - price) * rate, 1)

    def calculate_tax_rate(self, player_rank, profit):
        """Calculate tax rate based on player rank and location type"""
        base_tax = 0.05  # 5% base tax
        # famous captains pay a little more (it was up to 2.5 times; with markets that feel
        # every load, that left late traders no margin at all)
        rank_multiplier = {
            "Explorer": 1,
            "Pilot": 1.07,
            "Captain": 1.14,
            "Commander": 1.21,
            "Star Commander": 1.28,
            "Space Admiral": 1.35,
            "Stellar Hero": 1.42,
            "Galactic Legend": 1.5
        }

        # Reduce tax based on number of buildings
        building_discount = len(self.buildings) * 0.02  # 2% reduction per building

        # Location-specific tax adjustments
        location_tax_modifier = {
            "Planet": 1.0,
            "AsteroidBase": 0.8,  # Lower taxes to encourage mining
            "DeepSpaceOutpost": 1.2,  # Higher taxes for premium services
            "ResearchColony": 1.5   # Highest taxes due to research benefits
        }

        location_modifier = location_tax_modifier.get(self.location_type, 1.0)
        final_tax_rate = (base_tax * rank_multiplier.get(player_rank, 1) * location_modifier) - building_discount
        return max(0.01, min(0.25, final_tax_rate))  # Keep between 1% and 25%

    def add_temporary_ban(self, commodity, duration):
        """Add a temporary trade ban for a commodity"""
        if commodity not in self.banned_commodities:
            self.banned_commodities.append(commodity)
            self.ban_duration[commodity] = duration


    def get_capabilities(self):
        """Get capabilities for this location type"""
        return LocationCapabilities.CAPABILITIES.get(self.location_type, {})


    def can_trade(self, commodity):
        """Check if this location can trade a specific commodity"""
        # First, check if commodity is banned - this should be the first check
        if commodity in self.banned_commodities:
            return False

        # Always allow standard commodities
        if commodity in self.get_capabilities().get("can_trade", []):
            return True

        # Allow salt/fuel if corresponding refinery exists
        if commodity == 'salt' and any(b == "Halide Extraction Refinery" for b in self.buildings):
            return True

        if commodity == 'fuel' and any(b == "Plasma Catalysis Refinery" for b in self.buildings):
            return True

        # Allow trading all commodities if Combined Refinery exists
        if any(b == "Elemental Fusion Refinery" for b in self.buildings):
            return True

        return False

    def can_build(self, building_type):
        """Check if this location can build a specific building with debug info"""
        capabilities = self.get_capabilities()
        can_build_list = capabilities.get("can_build", [])

        # Convert building type to match capability format
        building_type = building_type.lower()

        # Remove any facility/paradise/authority suffix for comparison
        building_base = building_type.split()[0]

        # Return whether the base building type is in capabilities
        return building_base in can_build_list

    def can_mine(self, resource_type):
        """Check if this location can mine a specific resource"""
        return resource_type in self.get_capabilities().get("can_mine", [])

    def get_base_exogeology(self):
        """Get base mining efficiency with randomized ranges per location type"""
        ranges = {
            "Planet": (35, 65),
            "AsteroidBase": (68, 78),
            "DeepSpaceOutpost": (42, 52),
            "ResearchColony": (16, 36)
        }
        base_range = ranges.get(self.location_type, (50, 60))
        return random.randint(*base_range)


class QuestSystem:
    def __init__(self, game):
        self.game = game
        self.active_quests = []  # For Quest objects
        self.available_quests = []  # For tuple-based quests (legacy support)
        self.completed_quests = []
        self.story_progress = 0
        self.quest_ids = set()  # Track unique quest IDs
        self.quest_message_shown = set()  # Track shown quest messages
        self.research_gained = 0     # research points earned (spending does not undo it)
        self.acquired = {}           # units of each commodity that came aboard
        self.events_seen = {}        # random events by type
        self._last_seen = None

        # Quest line progression tracking

    MOST_ACTIVE = 6

    def watch(self):
        """Count what came in since the last look: research points, cargo."""
        ship = self.game.ship
        now = {"rp": ship.research_points, **{"cargo." + k: v for k, v in ship.cargo.items()}}
        last = getattr(self, "_last_seen", None) or now
        if now["rp"] > last.get("rp", now["rp"]):
            self.research_gained = getattr(self, "research_gained", 0) + now["rp"] - last["rp"]
        acquired = getattr(self, "acquired", None)
        if acquired is None:
            acquired = self.acquired = {}
        for key, value in now.items():
            if key.startswith("cargo.") and value > last.get(key, value):
                acquired[key[6:]] = acquired.get(key[6:], 0) + value - last[key]
        self._last_seen = now

    def counters(self):
        """Everything a quest can count, as it stands now."""
        self.watch()
        game = self.game
        ship = game.ship
        out = {"turn": game.turn, "trades": game.trades_completed,
               "profit": int(sum(ship.trade_profits.values())),
               "passengers": game.reputation_manager.total_passengers,
               "research_gained": getattr(self, "research_gained", 0),
               "discovered.any": game.count_discovered()}
        for kind, count in ship.combat_victories.items():
            out["victories." + kind] = count
        for place_type in STORY_PLACE_TYPES:
            out["discovered." + place_type] = game.count_discovered(place_type)
        for item, count in (getattr(self, "acquired", None) or {}).items():
            out["acquired." + item] = count
        for kind, count in (getattr(self, "events_seen", None) or {}).items():
            out["events." + kind] = count
        return out

    def check_active_quests(self):
        for quest in list(self.active_quests):
            if quest.check_completion(self.game):
                self.complete_quest(quest)

    def display_quests(self):
        """Display all active quests"""
        active_quests = [q for q in self.active_quests if isinstance(q, Quest)]
        if active_quests:
            quest_content = [["Active Quests"]]
            quest_content.append([""])
            for quest in active_quests:
                quest_content.append([quest.name])
                quest_content.append([f"└─ {quest.description}"])
                quest_content.append([f"└─ Rewards: {self.game.format_money(quest.reward_money)} credits, {quest.reward_rp} RP"])
                progress = quest.progress_text(self.game)
                if progress:
                    quest_content.append([f"└─ Progress: {progress}"])
                quest_content.append([""])

            print(self.game.create_box(quest_content, 'double'))
        else:
            self.game.display_simple_message("No active quests.")

        input("Press Enter to continue...")

    def update_from_trade(self, trade_data):
        """Update quests based on trade actions"""
        for quest in self.active_quests:
            if quest.quest_type == "trade":
                # Check if trade matches quest requirements
                if trade_data.get('action') == 'buy' or trade_data.get('action') == 'sell':
                    commodity = trade_data.get('commodity')
                    amount = trade_data.get('amount', 0)

                    # Update trade-specific quests
                    if 'commodity' in quest.requirements:
                        if commodity == quest.requirements['commodity']:
                            quest.progress += amount

                            # Display quest progress
                            self.display_quest_progress(quest)

                            # Check if quest is completed
                            if quest.check_completion(self.game):
                                self.complete_quest(quest)

        # Update cantina-type quests if they exist
        for quest in self.active_quests:
            if hasattr(quest, 'update_cantina_progress'):
                quest.update_cantina_progress(trade_data)


    def update_discovery_quests(self, location):
        """Update quests that involve location discovery"""
        for quest in self.active_quests:
            if quest.quest_type == "exploration":
                if "location_type" in quest.requirements:
                    if location.location_type == quest.requirements["location_type"]:
                        quest.progress += 1
                        self.display_quest_progress(quest)

                        if quest.check_completion(self.game):
                            self.complete_quest(quest)

                elif "specific_location" in quest.requirements:
                    if location.name == quest.requirements["specific_location"]:
                        quest.progress += 1
                        self.display_quest_progress(quest)

                        if quest.check_completion(self.game):
                            self.complete_quest(quest)

            elif quest.quest_type == "location_unlock":
                if "location_type" in quest.requirements:
                    if location.location_type == quest.requirements["location_type"]:
                        quest.progress += 1
                        self.display_quest_progress(quest)

                        if quest.check_completion(self.game):
                            self.complete_quest(quest)

    # Add these methods to the QuestSystem class

    def update_cargo_quests(self, cargo_lost):
        """Update quests that involve cargo requirements"""
        for quest in self.active_quests:
            if quest.quest_type == "cargo" or quest.quest_type == "trade":
                # Check if quest requires specific cargo type that was lost
                if "cargo_type" in quest.requirements:
                    cargo_type = quest.requirements["cargo_type"]
                    if cargo_type in cargo_lost:
                        # Update progress based on remaining cargo
                        remaining_cargo = self.game.ship.cargo[cargo_type]
                        if "target_amount" in quest.requirements:
                            quest.progress = remaining_cargo / quest.requirements["target_amount"]
                        self.display_quest_progress(quest)

    def update_money_quests(self, money_lost):
        """Update quests that involve money requirements"""
        if money_lost > 0:  # Only process if money was actually lost
            for quest in self.active_quests:
                # Check trade profit quests
                if quest.quest_type == "profit" or quest.quest_type == "trade":
                    if "target_money" in quest.requirements:
                        current_money = self.game.ship.money
                        target_money = quest.requirements["target_money"]
                        quest.progress = max(0, min(1.0, current_money / target_money))
                        self.display_quest_progress(quest)

                # Check money protection quests
                if quest.quest_type == "protect" and "max_money_loss" in quest.requirements:
                    if money_lost > quest.requirements["max_money_loss"]:
                        quest.failed = True
                        self.game.display_simple_message(f"Quest failed: Lost too much money!")
                        self.active_quests.remove(quest)

                # Update trade margin quests
                if quest.quest_type == "margin" and "min_balance" in quest.requirements:
                    if self.game.ship.money < quest.requirements["min_balance"]:
                        quest.progress = max(0.0, quest.progress - 0.2)  # Lose 20% progress
                        self.display_quest_progress(quest)

    def update_combat_quests(self, damage_taken):
        """Update quests that involve combat requirements"""
        for quest in self.active_quests:
            if quest.quest_type == "combat":
                # Update survival quests
                if "max_damage" in quest.requirements:
                    if damage_taken > quest.requirements["max_damage"]:
                        quest.failed = True
                        self.display_quest_progress(quest)

                # Update combat victory quests that require minimal damage
                if "damage_threshold" in quest.requirements:
                    if damage_taken <= quest.requirements["damage_threshold"]:
                        quest.progress += 1
                        self.display_quest_progress(quest)


    def check_event_requirements(self, event_result):
        """Count the event, then see whether it finished a quest."""
        event_type = event_result.get("type", "")
        seen = getattr(self, "events_seen", None)
        if seen is None:
            seen = self.events_seen = {}
        seen[event_type] = seen.get(event_type, 0) + 1
        self.check_active_quests()

    def generate_quest(self, quest_type, difficulty):
        """Generate a quest based on type and difficulty"""
        base_reward = 1000 * (difficulty + 1)
        research_reward = 50 * (difficulty + 1)

        quest_templates = {
            "mining": [
                {
                    "name": f"Mine {50 * (difficulty + 1)} units of salt",
                    "description": "Extract valuable minerals from the asteroid field",
                    "type": "mining",
                    "requirements": {
                        "resource_type": "salt",
                        "amount": 50 * (difficulty + 1)
                    },
                    "reward_money": base_reward,
                    "reward_rp": research_reward
                },
                {
                    "name": f"Extract {40 * (difficulty + 1)} units of fuel",
                    "description": "Extract fuel from deep space deposits",
                    "type": "mining",
                    "requirements": {
                        "resource_type": "fuel",
                        "amount": 40 * (difficulty + 1)
                    },
                    "reward_money": int(base_reward * 1.2),
                    "reward_rp": int(research_reward * 1.2)
                }
            ],
            "combat": [
                {
                    "name": f"Eliminate {2 * (difficulty + 1)} pirate ships",
                    "description": "Clear the sector of pirate activity",
                    "type": "combat",
                    "requirements": {
                        "enemy_type": "pirate",
                        "amount": 2 * (difficulty + 1)
                    },
                    "reward_money": int(base_reward * 1.5),
                    "reward_rp": int(research_reward * 1.5)
                },
                {
                    "name": f"Defend trade route for {3 * (difficulty + 1)} turns",
                    "description": "Maintain security in a trade route",
                    "type": "patrol",
                    "requirements": {
                        "turns": 3 * (difficulty + 1)
                    },
                    "reward_money": int(base_reward * 1.3),
                    "reward_rp": int(research_reward * 1.3)
                }
            ],
            "research": [
                {
                    "name": f"Collect {30 * (difficulty + 1)} research data",
                    "description": "Gather scientific data from space phenomena",
                    "type": "research",
                    "requirements": {
                        "research_type": "data",
                        "target_points": 30 * (difficulty + 1)
                    },
                    "reward_money": int(base_reward * 1.2),
                    "reward_rp": int(research_reward * 2)
                }
            ],
            "story": [
                {
                    "name": "Investigate mysterious signals",
                    "description": "Track down the source of unusual transmissions",
                    "type": "story",
                    "requirements": {
                        "story_progression": 1
                    },
                    "reward_money": int(base_reward * 2),
                    "reward_rp": int(research_reward * 3)
                }
            ]
        }

        # Select a random quest template
        if quest_type in quest_templates:
            template = random.choice(quest_templates[quest_type])
            destination = None
            description = template["description"]
            if template["type"] == "story":
                places = [name for name in self.game.known_locations
                          if name != self.game.current_location.name]
                if not places:
                    return None
                destination = random.choice(places)
                description += " (the trail leads to %s)" % destination
            quest = Quest(
                name=template["name"],
                description=description,
                reward_money=template["reward_money"],
                reward_rp=template["reward_rp"],
                quest_type=template["type"],
                requirements=template["requirements"],
                destination=destination
            )
            return quest
        return None


    def generate_cantina_quest(self):
        """Generate quests based on player's progress and reputation"""
        current_location = self.game.current_location.name
        quest_types = {
            "delivery": {
                "name": "Urgent Delivery",
                "description": lambda details: f"Deliver {details['amount']} {details['commodity']} to {details['destination']}",
                "requirements": {
                    "amount": (50, 150),
                    "commodity": ["tech", "agri"],
                    "time_limit": 5,
                    "min_plot_points": 10,
                    "min_reputation": 0
                },
                "rewards": {
                    "money": (5000, 10000),
                    "research_points": (50, 100),
                    "reputation": 2,
                    "items": ["scanner", "probe"]  # Possible bonus items
                }
            },
            "item_delivery": {
                "name": "Special Item Contract",
                "description": lambda details: f"Deliver {details['item']} to {details['destination']}",
                "requirements": {
                    "item": ["scanner", "shield", "probe", "turrets"],
                    "min_plot_points": 20,
                    "min_reputation": 20
                },
                "rewards": {
                    "money": (8000, 15000),
                    "research_points": (80, 150),
                    "reputation": 3,
                    "items": ["quantum_core", "neural_hack"]  # High-tier rewards
                }
            },
            "character_delivery": {
                "name": "VIP Transport",
                "description": lambda details: f"Transport {details['character']} to {details['destination']}",
                "requirements": {
                    "character": ["Research Director", "Trade Minister", "Military Commander"],
                    "min_reputation": 50,
                    "min_plot_points": 40
                },
                "rewards": {
                    "money": (12000, 20000),
                    "research_points": (100, 200),
                    "reputation": 5,
                    "plot_points": 2,
                    "items": ["neural_boost", "quantum_shield"]
                }
            },
            "mining_contract": {
                "name": "Resource Contract",
                "description": lambda details: f"Mine and deliver {details['amount']} {details['resource']} to {details['destination']}",
                "requirements": {
                    "amount": (100, 200),
                    "resource": ["salt", "fuel"],
                    "min_plot_points": 15,
                    "min_reputation": 10
                },
                "rewards": {
                    "money": (6000, 12000),
                    "research_points": (60, 120),
                    "reputation": 2,
                    "items": ["mining_laser", "cargo_scanner"]
                }
            }
        }

        # Filter quests based on player's progress
        available_quests = []
        for quest_type, template in quest_types.items():
            reqs = template["requirements"]
            if (self.game.story_manager.plot_points >= reqs.get("min_plot_points", 0) and
                self.game.ship.passenger_reputation >= reqs.get("min_reputation", 0)):
                available_quests.append((quest_type, template))

        if not available_quests:
            return None

        quest_type, template = random.choice(available_quests)

        # Generate quest details
        details = {}
        for key, value in template["requirements"].items():
            if isinstance(value, list):
                details[key] = random.choice(value)
            elif isinstance(value, tuple) and len(value) == 2:
                details[key] = random.randint(*value)
            elif key not in ["min_plot_points", "min_reputation"]:
                details[key] = value

        # Choose destination from known locations excluding current location
        possible_destinations = [loc for loc in self.game.known_locations
                            if loc != current_location]
        if not possible_destinations:
            return None

        details['destination'] = random.choice(possible_destinations)

        # Generate rewards
        base_rewards = template["rewards"]
        rewards = {
            "money": random.randint(*base_rewards["money"]),
            "research_points": random.randint(*base_rewards["research_points"]),
            "reputation": base_rewards.get("reputation", 0),
            "plot_points": base_rewards.get("plot_points", 0)
        }

        # Chance for bonus item
        if random.random() < 0.3 and "items" in base_rewards:  # 30% chance
            rewards["bonus_item"] = random.choice(base_rewards["items"])

        # Scale rewards based on chapter and difficulty
        chapter_multiplier = 1 + (self.game.story_manager.get_chapter_number() * 0.2)
        rep_multiplier = 1 + (template["requirements"].get("min_reputation", 0) / 100)

        for key in ["money", "research_points"]:
            rewards[key] = int(rewards[key] * chapter_multiplier * rep_multiplier)

        return Quest(
            name=template["name"],
            description=template["description"](details),
            reward_money=rewards["money"],
            reward_rp=rewards["research_points"],
            quest_type=quest_type,
            requirements=details,
            rewards=rewards,
            destination=details['destination']  # Add destination
        )

    def update_from_travel(self, travel_data):
        """Update quests based on travel actions"""
        for quest in list(self.active_quests):
            # A quest that opens a new kind of location is a lead to follow:
            # the next journey after it appears completes it.
            if quest.quest_type.startswith("unlock_"):
                quest.progress += 1
                if quest.check_completion(self.game):
                    self.complete_quest(quest)
                continue
            if quest.quest_type == "exploration" or quest.quest_type == "location_unlock":
                # Check location discovery requirements
                if "destination" in travel_data:
                    if quest.requirements.get('specific_location') == travel_data['destination']:
                        quest.progress += 1

                        # Display quest progress
                        self.display_quest_progress(quest)

                        # Check if quest is completed
                        if quest.check_completion(self.game):
                            self.complete_quest(quest)

    def complete_quest(self, quest):
        """Handle quest completion and cleanup with full quest lifecycle"""
        quest_id = f"{quest.name}_{quest.quest_type}"

        if quest in self.active_quests:
            # Remove from active quests and add to completed
            self.active_quests.remove(quest)
            self.completed_quests.append(quest)

            # Award rewards (and hand over what was delivered)
            quest.hand_over(self.game)
            self.game.ship.money += quest.reward_money
            self.game.ship.research_points += quest.reward_rp
            extras = getattr(quest, "rewards", None) or {}
            if extras.get("reputation"):
                self.game.ship.passenger_reputation += extras["reputation"]
            if extras.get("plot_points"):
                self.game.story_manager.plot_points += extras["plot_points"]
            if extras.get("bonus_item"):
                self.game.ship.acquire_item(extras["bonus_item"])

            # Apply any special effects based on quest type
            if quest.quest_type == 'mining':
                self.game.current_location.exogeology = min(100,
                    self.game.current_location.exogeology + 5)  # Small mining efficiency boost
            elif quest.quest_type == 'research':
                boost = int(quest.reward_rp * 0.1)  # 10% bonus research points
                self.game.ship.research_points += boost

            # Execute completion callback if exists
            if quest.on_complete:
                run_quest_callback(self.game, quest.on_complete)

            # Mark quest as completed
            quest.completed = True

            # Clean up message tracking
            if quest_id in self.quest_message_shown:
                self.quest_message_shown.remove(quest_id)

            # Display completion message
            lines = [f"Quest Completed: {quest.name}", "Rewards:",
                     f"• {self.game.format_money(quest.reward_money)} credits",
                     f"• {quest.reward_rp} research points"]
            if extras.get("reputation"):
                lines.append(f"• +{extras['reputation']} reputation")
            if extras.get("plot_points"):
                lines.append(f"• +{extras['plot_points']} plot points")
            if extras.get("bonus_item"):
                lines.append(f"• Bonus item: {extras['bonus_item']}")
            self.game.display_story_message(lines)

            # Update story progression if applicable
            if hasattr(self.game, 'story_manager'):
                self.game.story_manager.handle_quest_completion(quest)

            # Check for milestone completion
            if hasattr(self.game, 'check_milestone_triggers'):
                self.game.check_milestone_triggers()

            return True

        return False


    def display_quest_progress(self, quest):
        """Display quest progress update"""
        if isinstance(quest, Quest):
            progress_text = f"Quest Progress: {quest.name}"
            if quest.target_progress > 1:
                progress_text += f" ({quest.progress}/{quest.target_progress})"
            self.game.display_simple_message(progress_text)


    def add_quest(self, quest):
        """Add a new quest with duplication check"""
        if quest is None:
            return False
        # Create unique identifier for the quest
        quest_id = f"{quest.name}_{quest.quest_type}"

        # Check if quest is already active
        existing_quest = any(q.name == quest.name and q.quest_type == quest.quest_type
                           for q in self.active_quests)
        if existing_quest:
            return False  # Don't add duplicate quest
        if len(self.active_quests) >= self.MOST_ACTIVE and not quest.quest_type.startswith("unlock_"):
            return False  # enough on the board already
        quest.begin(self.game)
        if quest.quest_type == "character_delivery":
            # the passenger waits at this port for the captain to board them
            port = self.game.port_system
            passenger = Passenger(quest.requirements["character"], quest.destination, wealth_level=5)
            passenger.is_quest_passenger = True
            port.waiting_passengers.setdefault(self.game.current_location.name, []).append(passenger)

        # Check if we've already shown this quest message
        if quest_id not in self.quest_message_shown:
            self.game.display_story_message([
                "New Quest Available!",
                quest.name,
                quest.description,
                f"Rewards: {self.game.format_money(quest.reward_money)} credits, {quest.reward_rp} RP"
            ])
            self.quest_message_shown.add(quest_id)

        # Add quest to active quests
        self.active_quests.append(quest)
        return True

class MilestoneRequirements:
    """Enhanced requirements checking for story milestones"""

    @staticmethod
    def check_requirements(requirements, game):
        """Check if all requirements are met"""
        for req_type, req_value in requirements.items():
            if not MilestoneRequirements._check_single_requirement(req_type, req_value, game):
                return False
        return True

    @staticmethod
    def _check_single_requirement(req_type, req_value, game):
        """Check a single requirement (main-story thresholds as they stand on this voyage)"""
        if hasattr(game, "voyage_factor"):
            req_value = voyage_value(req_type, req_value, game.voyage_factor())
        # Basic requirements
        if req_type == "plot_points":
            return game.story_manager.plot_points >= req_value
        elif req_type == "money":
            return game.ship.money >= req_value
        elif req_type == "research_points":
            return game.ship.research_points >= req_value

        # Combat requirements
        elif req_type == "combat_victories":
            if isinstance(req_value, dict):
                # Check specific enemy types
                for enemy_type, amount in req_value.items():
                    if game.ship.combat_victories.get(enemy_type, 0) < amount:
                        return False
                return True
            else:
                # Check total victories
                return game.ship.combat_victories['total'] >= req_value
        elif req_type == "combat_rating":
            return (game.ship.attack + game.ship.defense + game.ship.speed) >= req_value

        # Trade requirements
        elif req_type == "trades_completed":
            return game.trades_completed >= req_value
        elif req_type == "trade_profit":
            return sum(game.ship.trade_profits.values()) >= req_value
        elif req_type == "trade_specific":
            # Check specific commodity trading requirements
            commodity, amount = req_value
            return game.ship.trade_profits.get(commodity, 0) >= amount

        # Passenger requirements
        elif req_type == "passengers_transported":
            return game.reputation_manager.total_passengers >= req_value
        elif req_type == "passenger_reputation":
            return game.ship.passenger_reputation >= req_value
        elif req_type == "passenger_class":
            # Check specific passenger class requirements
            class_type, amount = req_value
            return game.reputation_manager.class_transports.get(class_type, 0) >= amount

        # Location requirements
        elif req_type == "locations_discovered":
            if isinstance(req_value, dict):
                # Check specific location types
                for loc_type, amount in req_value.items():
                    if game.count_discovered(loc_type) < amount:
                        return False
                return True
            else:
                # Check total discoveries
                return len(game.discovered_locations) >= req_value
        elif req_type == "buildings_built":
            if isinstance(req_value, dict):
                # Check specific building types
                for building_type, amount in req_value.items():
                    total_built = sum(1 for loc in game.locations
                                    for building in loc.buildings
                                    if building == building_type)
                    if total_built < amount:
                        return False
                return True
            else:
                # Check total buildings
                return sum(len(loc.buildings) for loc in game.locations) >= req_value

        # Mining requirements
        elif req_type == "mining_platforms":
            if isinstance(req_value, dict):
                # Check specific resource types
                for resource_type, amount in req_value.items():
                    total_platforms = sum(1 for loc in game.locations
                                        for platform in loc.mining_platforms
                                        if platform['type'] == resource_type)
                    if total_platforms < amount:
                        return False
                return True
            else:
                # Check total platforms
                return sum(len(loc.mining_platforms) for loc in game.locations) >= req_value

        # Quest requirements
        elif req_type == "quests_completed":
            if isinstance(req_value, dict):
                # Check specific quest types
                for quest_type, amount in req_value.items():
                    completed = len([q for q in game.quest_system.completed_quests
                                   if q.quest_type == quest_type])
                    if completed < amount:
                        return False
                return True
            else:
                # Check total completed quests
                return len(game.quest_system.completed_quests) >= req_value

        # Research requirements
        elif req_type == "research_unlocked":
            return all(tech in game.research.unlocked_options for tech in req_value)

        # Faction requirements
        elif req_type == "faction_reputation":
            faction, rep_level = req_value
            return game.faction_system.get_reputation(faction) >= rep_level

        # Item requirements
        elif req_type == "items":
            return all(item in game.ship.items for item in req_value)

        # Story progression requirements
        elif req_type == "chapters_completed":
            return all(chapter in game.story_manager.completed_chapters for chapter in req_value)
        elif req_type == "chapters_completed_any":
            return any(chapter in game.story_manager.completed_chapters for chapter in req_value)
        elif req_type == "milestones_completed":
            return all(milestone in game.story_manager.completed_story_beats for milestone in req_value)
        elif req_type == "story_states":
            return all(game.story_manager.story_states.get(state, False) for state in req_value)

        # Captains who crossed over from another part of the trilogy:
        # {"game": "cargo2"}, optionally with "ending" and/or "flag"
        elif req_type == "visiting_captain":
            return game.has_visiting_captain(req_value.get("game"), req_value.get("ending"),
                                             req_value.get("flag"))

        # Custom requirements
        elif req_type == "custom_condition":
            return req_value(game)  # Call custom function with game instance

        # Unknown requirement type
        else:
            print(f"Warning: Unknown requirement type {req_type}")
            return False

class StoryMilestone:
    def __init__(self, milestone_id, title, description, requirements, rewards=None, unlocks=None):
        self.id = milestone_id
        self.title = title
        self.description = description
        self.requirements = requirements
        self.rewards = rewards or {}
        self.unlocks = unlocks or []  # List of unlock dictionaries
        self.completed = False
        self.completion_turn = None

    def check_completion(self, game):
        """Check if milestone requirements are met"""
        if self.completed:
            return True
        return MilestoneRequirements.check_requirements(self.requirements, game)

    def complete(self, game):
        """Complete milestone and handle unlocks"""
        if not self.completed:
            self.completed = True
            self.completion_turn = game.turn

            # Handle rewards
            if self.rewards:
                if "money" in self.rewards:
                    game.ship.money += self.rewards["money"]
                if "research_points" in self.rewards:
                    game.ship.research_points += self.rewards["research_points"]
                if "plot_points" in self.rewards:
                    game.story_manager.plot_points += self.rewards["plot_points"]
                if "items" in self.rewards:
                    for item in self.rewards["items"]:
                        game.ship.acquire_item(item)

            # Handle unlocks
            unlock_messages = []
            for unlock in self.unlocks:
                unlock_type = unlock.get("type")
                unlock_id = unlock.get("id")

                if unlock_type == "item":
                    game.ship.acquire_item(unlock_id)
                    unlock_messages.append(f"Unlocked item: {unlock_id}")

                elif unlock_type == "location_type":
                    game.unlocked_location_types.add(unlock_id)
                    # Add hidden locations of this type to available locations
                    if unlock_id in game.hidden_locations:
                        game.locations.extend(game.hidden_locations[unlock_id])
                        unlock_messages.append(f"Unlocked new location type: {unlock_id}")

                elif unlock_type == "specific_location":
                    # Search in hidden_locations
                    for loc_type, locations in game.hidden_locations.items():
                        for location in locations:
                            if location.name == unlock_id:
                                game.locations.append(location)
                                game.known_locations.append(location.name)
                                unlock_messages.append(f"Discovered location: {location.name}")
                                break

                    # Search in chapter_locations
                    for chapter_num, chapter_locs in game.chapter_locations.items():
                        for loc_type, locations in chapter_locs.items():
                            for location in locations:
                                if location.name == unlock_id:
                                    game.locations.append(location)
                                    game.known_locations.append(location.name)
                                    unlock_messages.append(f"Discovered location: {location.name}")
                                    break

                elif unlock_type == "chapter_locations":
                    chapter_num = unlock.get("chapter")
                    if chapter_num in game.chapter_locations:
                        for loc_type, locations in game.chapter_locations[chapter_num].items():
                            game.locations.extend(locations)
                            for loc in locations:
                                game.known_locations.append(loc.name)
                        unlock_messages.append(f"Unlocked Chapter {chapter_num} locations!")

            # Display completion message with unlocks
            completion_message = [
                f"Milestone Completed: {self.title}!",
                self.description,
                "",
                "Rewards:"
            ]

            # Add rewards to message
            for reward_type, value in self.rewards.items():
                if reward_type == "money":
                    completion_message.append(f"• {game.format_money(value)} credits")
                elif reward_type == "plot_points":
                    completion_message.append(f"• {value} plot points")
                elif reward_type == "research_points":
                    completion_message.append(f"• {value} research points")
                elif reward_type == "items":
                    completion_message.append(f"• Items: {', '.join(value)}")

            # Add unlock messages
            if unlock_messages:
                completion_message.append("")
                completion_message.append("Unlocked:")
                for msg in unlock_messages:
                    completion_message.append(f"• {msg}")

            game.display_story_message(completion_message)

def chapter_requirements_met(chapter, game):
    """A chapter's own requirements; the story file's when it repairs them."""
    story = getattr(game, "story", None)
    repaired = story.condition_for(chapter.id) if story is not None else None
    if repaired is not None:
        return story.check(voyage_condition(repaired, game.voyage_factor()), story.snapshot())
    return all(MilestoneRequirements._check_single_requirement(req_type, req_value, game)
               for req_type, req_value in chapter.requirements.items())


class StoryChapter:
    def __init__(self, chapter_id, title, description, requirements, milestones, next_chapters=None):
        self.id = chapter_id
        self.title = title
        self.description = description
        self.requirements = requirements
        self.milestones = {}  # Dictionary of milestone_id: StoryMilestone
        self.next_chapters = next_chapters or []  # List of possible next chapter IDs
        self.unlocks = []  # Unlock dictionaries applied when the chapter completes
        self.completed = False
        self.completion_turn = None

        # Initialize milestones
        for milestone_data in milestones:
            milestone = StoryMilestone(**milestone_data)
            self.milestones[milestone.id] = milestone

    def check_completion(self, game):
        """Check if chapter can be completed"""
        if self.completed:
            return True

        # First check chapter requirements
        if not chapter_requirements_met(self, game):
            return False

        # Then check if all required milestones are completed
        return all(milestone.completed for milestone in self.milestones.values())

    def get_available_milestones(self, game):
        """Get list of currently available milestones"""
        return [m for m in self.milestones.values()
                if not m.completed and m.check_completion(game)]

    def get_next_chapters(self, game):
        """Get list of possible next chapters based on current game state"""
        available_chapters = []
        for chapter_id in self.next_chapters:
            chapter = game.story_manager.chapters[chapter_id]
            if chapter_requirements_met(chapter, game):
                available_chapters.append(chapter)
        return available_chapters

    def handle_chapter_unlocks(self, game):
        """Handle any unlocks when chapter completes"""
        if hasattr(self, 'unlocks') and self.unlocks:
            for unlock in self.unlocks:
                unlock_type = unlock.get("type")
                unlock_id = unlock.get("id")

                if unlock_type == "location_type":
                    game.unlock_location_type(unlock_id)
                elif unlock_type == "chapter_locations":
                    chapter_num = unlock.get("chapter")
                    if chapter_num in game.chapter_locations:
                        for locations in game.chapter_locations[chapter_num].values():
                            game.locations.extend(locations)

class StoryManager:
    def __init__(self, game):
        self.game = game
        self.current_chapter = None
        self.completed_chapters = set()
        self.completed_story_beats = set()
        self.plot_points = 0
        self.story_states = {
            "pirate_threat": False,
            "alien_discovery": False,
            "trade_empire": False,
            "resource_empire": False,
            "ancient_mystery": False,
            "galactic_crisis": False
        }
        self.chapters = self.initialize_chapters()
        self.event_cooldowns = {}
        self.enabled_events = set()

    def get_chapter_number(self, chapter_string=None):
        """
        Extract numeric chapter number from chapter string.
        If no chapter string provided, uses current chapter.
        Returns: int chapter number
        """
        if chapter_string is None:
            chapter_string = self.current_chapter
        if chapter_string and str(chapter_string).startswith("ending"):
            return 4  # every ending is the fourth act
        try:
            return int(''.join(filter(str.isdigit, chapter_string)))
        except (ValueError, TypeError):
            return 1  # Default to chapter 1 if conversion fails

    def number_to_roman(self, num):
        """Convert integer to Roman numeral with dot"""
        roman_map = {
            1: 'I.', 2: 'II.', 3: 'III.', 4: 'IV.', 5: 'V.',
            6: 'VI.', 7: 'VII.', 8: 'VIII.', 9: 'IX.', 10: 'X.',
            11: 'XI.', 12: 'XII.', 13: 'XIII.', 14: 'XIV.', 15: 'XV.',
            16: 'XVI.', 17: 'XVII.', 18: 'XVIII.', 19: 'XIX.', 20: 'XX.',
            21: 'XXI.', 22: 'XXII.', 23: 'XXIII.', 24: 'XXIV.', 25: 'XXV.',
            26: 'XXVI.', 27: 'XXVII.', 28: 'XXVIII.', 29: 'XXIX.', 30: 'XXX.'
        }

        return roman_map.get(num, str(num))

    def get_chapter_number_roman(self, chapter_string=None):
        """Get chapter number as Roman numeral"""
        number = self.get_chapter_number(chapter_string)
        return self.number_to_roman(number)

    def initialize_chapters(self):
        """Initialize all chapters with their milestones and branching paths"""
        # Core storyline
        return {
            "ch1": StoryChapter(
                chapter_id="ch1",
                title="First Steps",
                description="Learn the basics of space trading",
                requirements={},  # No requirements for first chapter
                milestones=[
                    {
                        "milestone_id": "first_trade",
                        "title": "First Trade",
                        "description": "Complete your first trade",
                        "requirements": {"trades_completed": 1},
                        "rewards": {"money": 500, "plot_points": 5}
                    },
                    {
                        "milestone_id": "first_combat",
                        "title": "Combat Initiation",
                        "description": "Win your first space battle",
                        "requirements": {"combat_victories": 1},
                        "rewards": {"money": 1000, "plot_points": 5}
                    },
                    {
                        "milestone_id": "basic_license",
                        "title": "Extended Trading License",
                        "description": "Prove your trading capabilities",
                        "requirements": {
                            "trades_completed": 5,
                            "money": 20000
                        },
                        "rewards": {"money": 10000, "plot_points": 10, "items": ["navcomp"]}
                    }
                ],
                next_chapters=["ch2a", "ch2b"]  # Player can choose trade or combat path
            ),

            "ch2a": StoryChapter(
                chapter_id="ch2a",
                title="Trade Empire Rising",
                description="Build your commercial empire",
                requirements={
                    "chapters_completed": ["ch1"],
                    "plot_points": 15,
                    "trades_completed": 10
                },
                milestones=[
                    {
                        "milestone_id": "establish_route",
                        "title": "Trade Route Network",
                        "description": "Establish profitable trade routes",
                        "requirements": {
                            "trades_completed": 20,
                            "buildings_built": {"stockmarket": 2}
                        },
                        "rewards": {"money": 50000, "plot_points": 15}
                    },
                    {
                        "milestone_id": "passenger_business",
                        "title": "Passenger Services",
                        "description": "Start passenger transport business",
                        "requirements": {
                            "passengers_transported": 10,
                            "passenger_reputation": 20
                        },
                        "rewards": {"money": 30000, "plot_points": 10}
                    }
                ],
                next_chapters=["ch3a", "ch3c"]
            ),

            "ch2b": StoryChapter(
                chapter_id="ch2b",
                title="Combat Legend",
                description="Become a legendary combat pilot",
                requirements={
                    "chapters_completed": ["ch1"],
                    "plot_points": 15,
                    "combat_victories": 5
                },
                milestones=[
                    {
                        "milestone_id": "defeat_pirates",
                        "title": "Pirate Hunter",
                        "description": "Clear the sector of pirates",
                        "requirements": {
                            "combat_victories": {"pirate": 10}
                        },
                        "rewards": {"money": 40000, "plot_points": 20}
                    },
                    {
                        "milestone_id": "defend_stations",
                        "title": "Station Defender",
                        "description": "Successfully defend space stations",
                        "requirements": {
                            "combat_victories": 15,
                            "buildings_built": {"Neuroengineering Guild": 1}
                        },
                        "rewards": {"money": 30000, "plot_points": 15}
                    }
                ],
                next_chapters=["ch3b", "ch3c"]
            ),

            "ch3a": StoryChapter(
                chapter_id="ch3a",
                title="Economic Dominance",
                description="Achieve economic control of the sector",
                requirements={
                    "chapters_completed": ["ch2a"],
                    "plot_points": 40,
                    "trade_profit": 150000
                },
                milestones=[
                    {
                        "milestone_id": "market_control",
                        "title": "Market Controller",
                        "description": "Control multiple market centers",
                        "requirements": {
                            "buildings_built": {"stockmarket": 4},
                            "research_unlocked": ["xenoeconomy"]
                        },
                        "rewards": {"money": 100000, "plot_points": 25}
                    }
                ],
                next_chapters=["ending_trade"]
            ),

            "ch3b": StoryChapter(
                chapter_id="ch3b",
                title="Military Might",
                description="Become the dominant military force",
                requirements={
                    "chapters_completed": ["ch2b"],
                    "plot_points": 40,
                    "combat_victories": 25
                },
                milestones=[
                    {
                        "milestone_id": "fleet_commander",
                        "title": "Fleet Commander",
                        "description": "Lead successful fleet operations",
                        "requirements": {
                            "combat_victories": 35,
                            "combat_rating": 15
                        },
                        "rewards": {"money": 100000, "plot_points": 25}
                    }
                ],
                next_chapters=["ending_combat"]
            ),

            "ch3c": StoryChapter(
                chapter_id="ch3c",
                title="Ancient Mysteries",
                description="Uncover the sector's ancient secrets",
                requirements={
                    "chapters_completed_any": ["ch2a", "ch2b"],  # Can be reached from either path
                    "plot_points": 50,
                    "research_points": 300
                },
                milestones=[
                    {
                        "milestone_id": "alien_artifacts",
                        "title": "Ancient Technology",
                        "description": "Discover alien artifacts",
                        "requirements": {
                            "locations_discovered": {"ResearchColony": 2},
                            "research_unlocked": ["xenoeconomy", "telemetry"]
                        },
                        "rewards": {"money": 150000, "plot_points": 30}
                    }
                ],
                next_chapters=["ending_discovery"]
            ),

            # Endings
            "ending_trade": StoryChapter(
                chapter_id="ending_trade",
                title="Galactic Trade Mogul",
                description="You've become a legendary trade mogul",
                requirements={
                    "chapters_completed": ["ch3a"],
                    "plot_points": 100,
                    "trade_profit": 400000
                },
                milestones=[
                    {
                        "milestone_id": "trade_ending",
                        "title": "Economic Victory",
                        "description": "Complete economic domination achieved",
                        "requirements": {
                            "buildings_built": {"stockmarket": 5},
                            "passenger_reputation": 80,
                            "trade_profit": 400000
                        },
                        "rewards": {"money": 1000000, "plot_points": 100}
                    }
                ],
                next_chapters=[]  # No next chapters - this is an ending
            ),

            "ending_combat": StoryChapter(
                chapter_id="ending_combat",
                title="Legendary Fleet Admiral",
                description="You've become a legendary military leader",
                requirements={
                    "chapters_completed": ["ch3b"],
                    "plot_points": 100,
                    "combat_victories": 50
                },
                milestones=[
                    {
                        "milestone_id": "combat_ending",
                        "title": "Military Victory",
                        "description": "Complete military dominance achieved",
                        "requirements": {
                            "combat_victories": 75,
                            "combat_rating": 25
                        },
                        "rewards": {"money": 1000000, "plot_points": 100}
                    }
                ],
                next_chapters=[]
            ),

            "ending_discovery": StoryChapter(
                chapter_id="ending_discovery",
                title="Ancient Mystery Solver",
                description="You've uncovered the sector's greatest mysteries",
                requirements={
                    "chapters_completed": ["ch3c"],
                    "plot_points": 100,
                    "research_points": 1500
                },
                milestones=[
                    {
                        "milestone_id": "discovery_ending",
                        "title": "Discovery Victory",
                        "description": "Ancient mysteries solved",
                        "requirements": {
                            "research_unlocked": ["xenoeconomy", "telemetry", "geophysics", "chronopolitics"],
                            "locations_discovered": {"ResearchColony": 3, "AsteroidBase": 2}
                        },
                        "rewards": {"money": 1000000, "plot_points": 100}
                    }
                ],
                next_chapters=[]
            )
        }

    def apply_story_text(self):
        """Titles and texts of chapters and milestones come from the story data."""
        story = self.game.story
        for cid, chapter in self.chapters.items():
            chapter.title = story.title_of(cid, chapter.title)
            if not cid.startswith("ending_"):
                chapter.description = " ".join(story.text_of(cid, fallback=chapter.description))
            for mid, milestone in chapter.milestones.items():
                nid = "%s.%s" % (cid, mid)
                milestone.title = story.title_of(nid, milestone.title)
                milestone.description = " ".join(story.text_of(nid, fallback=milestone.description))

    def start_game(self):
        """Initialize story at game start"""
        self.apply_story_text()
        self.current_chapter = "ch1"  # Store the ID string instead of the chapter object
        first_chapter = self.chapters["ch1"]

        self.game.display_story_message([
            f"Chapter I.: {first_chapter.title}",
            first_chapter.description,
            "",
            "Your journey begins..."
        ])

    def is_story_completed(self):
        """Check if the story has reached an ending"""
        if not self.current_chapter:
            return False
        current_chapter_obj = self.chapters[self.current_chapter]
        return (not current_chapter_obj.next_chapters and
                current_chapter_obj.completed)

    def check_milestone_progress(self):
        """Check for milestone completions in current chapter"""
        if self.current_chapter:
            current_chapter_obj = self.chapters[self.current_chapter]
            available_milestones = current_chapter_obj.get_available_milestones(self.game)
            for milestone in available_milestones:
                if milestone.check_completion(self.game):
                    milestone.complete(self.game)
                    self.completed_story_beats.add(milestone.id)

    def check_chapter_progress(self):
        """Complete the current chapter when it is done, then move on.

        A finished chapter waits here until one of its follow-up chapters
        opens; an ending chapter shows its ending once.
        """
        if not self.current_chapter:
            return

        chapter = self.chapters[self.current_chapter]
        if not chapter.completed:
            if not chapter.check_completion(self.game):
                return
            self.complete_current_chapter()
            if not chapter.next_chapters:
                self.handle_game_ending()
                return

        if not chapter.next_chapters:
            return
        options = chapter.get_next_chapters(self.game)
        if not options:
            return
        if len(chapter.next_chapters) == 1:
            self.start_chapter(options[0].id)
            return
        # Several ways on: ask, but only when the open ways have changed since
        # the last time the captain decided to wait
        open_now = sorted(option.id for option in options)
        if open_now != getattr(self, 'offered_paths', None):
            self.offered_paths = open_now
            self.present_chapter_choice(options)

    def handle_game_ending(self):
        """Handle reaching a game ending: its text, the score, what became of
        everyone, and the captain's record closed for this timeline."""
        story = self.game.story
        story.mark(self.current_chapter)
        story.cue("ending")
        self.game.display_story_message(story.text_of(
            self.current_chapter, fallback="Congratulations! You've completed your journey!"))
        self.game.display_score()
        story.epilogue()
        self.game.close_record(self.current_chapter.replace("ending_", ""))

    def complete_current_chapter(self):
        """Mark the current chapter complete and announce it"""
        current_chapter_obj = self.chapters[self.current_chapter]
        if not current_chapter_obj.completed:
            current_chapter_obj.completed = True
            current_chapter_obj.completion_turn = self.game.turn
            self.completed_chapters.add(self.current_chapter)

            # Handle any chapter unlocks
            current_chapter_obj.handle_chapter_unlocks(self.game)

            self.game.display_story_message([
                f"Chapter Complete: {current_chapter_obj.title}",
                "Your journey continues to evolve..."
            ])

    def present_chapter_choice(self, available_chapters):
        """Let the player pick the next chapter among the ones that are open.

        Ways that are not open yet are listed too, so the captain can decide
        to wait for them (Enter) instead of taking the first open door.
        """
        current = self.chapters[self.current_chapter]
        open_ids = [chapter.id for chapter in available_chapters]
        content = [["Choose Your Path"]]
        for i, chapter in enumerate(available_chapters, 1):
            content.extend([
                [""],
                [f"{i}. {chapter.title}"],
                [chapter.description]
            ])
        waiting = [self.chapters[cid] for cid in current.next_chapters if cid not in open_ids]
        for chapter in waiting:
            content.extend([
                [""],
                [f"-  {chapter.title} (not open yet)"],
                [chapter.description]
            ])
        print(self.game.create_box(content, 'double'))

        prompt = f"Choose your path (1-{len(available_chapters)})"
        if waiting:
            prompt += ", or press Enter to wait for the other"
        choice = self.game.validate_input(
            prompt + ": ",
            [str(i) for i in range(1, len(available_chapters) + 1)]
        )

        if choice:
            self.offered_paths = None
            chosen_chapter = available_chapters[int(choice) - 1]
            self.start_chapter(chosen_chapter.id)  # Use the ID

    def start_chapter(self, chapter):
        """Start a new chapter"""
        if isinstance(chapter, str):
            self.current_chapter = chapter
            chapter_obj = self.chapters[chapter]
        else:
            self.current_chapter = chapter.id
            chapter_obj = chapter

        self.chapter_started = self.game.turn
        self.game.display_story_message([
            f"{self.get_chapter_label()}: {chapter_obj.title}",
            chapter_obj.description,
            "",
            "New milestones await..."
        ])

    def plot_target(self):
        """The plot points the next chapter asks for, or None when no chapter waits on them."""
        chapter = self.chapters.get(self.current_chapter)
        nodes = story_data()["nodes"]
        wanted = [voyage_condition((nodes.get(c) or {}).get("requires", {}), self.game.voyage_factor()).get("plot_points")
                  for c in (chapter.next_chapters if chapter else [])]
        wanted = [w for w in wanted if isinstance(w, int)]
        return min(wanted) if wanted else None

    READABLE = {"plot_points": "plot points", "trades_completed": "trades", "trade_profit": "trade profit",
                "combat_victories": "fights won", "research_points": "research points",
                "passengers_transported": "passengers delivered", "passenger_reputation": "passenger reputation",
                "combat_rating": "attack + defense + speed", "discovered": "places visited", "money": "credits"}

    def chapter_needs(self, chapter):
        """What still stands between the captain and a chapter: [(key, words)].
        The story file's condition when it repairs the chapter's, else the code's."""
        game = self.game
        story = game.story
        cond = voyage_condition(story.condition_for(chapter.id), game.voyage_factor())
        if cond is None:
            return [(k, "%s: %s" % (k, v)) for k, v in chapter.requirements.items()
                    if not k.startswith("chapters_completed")
                    and not MilestoneRequirements._check_single_requirement(k, v, game)]
        snap = story.snapshot()
        out = []
        for key, want in cond.items():
            if story.check({key: want}, snap):
                continue
            if key in ("done", "done_any"):
                scenes = [n for n in _as_list(want) if n not in snap["done"] and n not in self.chapters]
                if scenes:
                    out.append((key, "a turning point: " + " or ".join(story.title_of(n) or n for n in scenes)))
                continue
            label = self.READABLE.get(key) or key.replace("buildings.", "buildings: ").replace(
                "combat_victories.", "victories over ").replace("discovered.", "places visited: ")
            value = game.format_money(want) if isinstance(want, int) and want >= 10000 else want
            out.append((key, "%s: %s" % (label, value)))
        return out

    # What a dock master says to a captain who has been stuck in one chapter a while,
    # by the first thing the way on still needs
    NUDGES = [
        ("done", "Some doors only open after the right meeting. Keep calling at cantinas and ports; "
                 "the people who matter are looking for you too."),
        ("plot", "Nobody sings about a captain who only waits. Take the jobs people offer in cantinas and ports, "
                 "trade well, look at new places: that is how a story gets told."),
        ("trade_profit", "Profit is what is left after the goods are paid for. Find a lane with a wide margin and work it."),
        ("trades", "The dock masters count every trade. Buy, sell, and do it often."),
        ("combat_victories", "The bounty board pays for ships the legions want gone. Hunt (hu) when your guns are ready."),
        ("combat_rating", "Your ship is too soft for the work you want. Upgrade it: attack, defense, speed."),
        ("research", "The research colonies pay attention to research points: travel, discoveries and old buoys all earn them."),
        ("passenger", "Passengers pay and talk. A better cabin helps; so does a steward who knows which fork is which."),
        ("building", "Build something: a stock market, a guild. People notice a captain who puts money into a dock."),
        ("locations", "There are places you have not seen yet. The cantina sells maps; the bar sells rumours."),
    ]

    def nudge(self):
        """After twenty turns in one chapter, the cantina offers a hint about what is missing."""
        game = self.game
        started = getattr(self, "chapter_started", 0)
        if game.turn - started < 20 or game.turn - getattr(self, "nudged_turn", -100) < 10:
            return
        chapter = self.chapters.get(self.current_chapter)
        if not chapter:
            return
        missing = []
        for milestone in chapter.milestones.values():
            if not milestone.completed:
                missing += [k for k, v in milestone.requirements.items()
                            if not MilestoneRequirements._check_single_requirement(k, v, game)]
        for cid in chapter.next_chapters:
            missing += [k for k, _ in self.chapter_needs(self.chapters[cid])]
        for key, text in self.NUDGES:
            if any(key in m for m in missing):
                self.nudged_turn = game.turn
                game.display_story_message(["A word at the bar", ""] + game.word_wrap(
                    "An old dock master who has seen a hundred captains come and go leans over: '" + text + "'"), pause=1)
                return

    def get_chapter_label(self, chapter_string=None):
        """'Chapter II.' for a numbered chapter, 'Finale' for an ending"""
        if chapter_string is None:
            chapter_string = self.current_chapter
        if chapter_string and chapter_string.startswith("ending"):
            return "Finale"
        return f"Chapter {self.get_chapter_number_roman(chapter_string)}"


    def complete_milestone(self, milestone_id):
        """Complete a specific milestone in the current chapter"""
        if self.current_chapter:
            current_chapter_obj = self.chapters[self.current_chapter]

            # Check if milestone exists in current chapter
            if milestone_id in current_chapter_obj.milestones:
                milestone = current_chapter_obj.milestones[milestone_id]

                # Complete the milestone if not already completed
                if not milestone.completed:
                    milestone.complete(self.game)
                    self.completed_story_beats.add(milestone_id)
                    return True

        return False

# Add these methods from old system:
    def process_event(self, event_type, details):
        """Process events and award plot points"""
        if self.check_cooldown(event_type):
            return

        points = self.calculate_points(event_type, details)

        # Extract numeric part of chapter string and use that for multiplier
        chapter_num = self.get_chapter_number()
        points *= (1 + chapter_num * 0.2)

        self.plot_points += int(points)

        self.update_story_states(event_type, details)
        self.check_chapter_progress()

    def enable_story_event(self, event_id):
        """Enable a story event for potential triggering"""
        self.enabled_events.add(event_id)

    def trigger_story_event(self, event_id, details=None):
        """Legacy support for story events"""
        if event_id in self.enabled_events:
            self.process_event("story", {
                "event_id": event_id,
                "details": details
            })
            return True
        return False

    def check_event_trigger(self, event, game):
        """Story switches that random events flip (no plot points: an event that only
        happened to the ship is not progress; what the captain does about it is)"""
        if isinstance(event, str):
            if "pirate" in event.lower():
                self.update_story_states("combat", {"enemy_type": "pirate"})
            elif "artifact" in event.lower():
                self.update_story_states("exploration", {"discovery_type": "artifact"})

    def handle_quest_completion(self, quest):
        """Update story progress when quests complete"""
        plot_points = {
            "story": 10,
            "combat": 5,
            "trade": 5,
            "exploration": 8,
            "research": 8
        }.get(quest.quest_type, 3)

        self.plot_points += plot_points

        # Handle milestone completion if this was a story quest
        if quest.milestone and self.current_chapter:
            chapter_obj = self.chapters[self.current_chapter]
            if quest.milestone in chapter_obj.milestones:
                milestone = chapter_obj.milestones[quest.milestone]
                milestone.complete(self.game)

        # Update story states based on quest completion
        if quest.quest_type == "trade" and self.game.trades_completed >= 50:
            self.story_states["trade_empire"] = True
        elif quest.quest_type == "combat" and self.game.ship.combat_victories['total'] >= 25:
            self.story_states["pirate_threat"] = True
        elif quest.quest_type == "research" and len(self.game.research.unlocked_options) >= 3:
            self.story_states["tech_breakthrough"] = True
        elif quest.quest_type == "exploration" and len(self.game.discovered_locations) >= 5:
            self.story_states["ancient_mystery"] = True

        # Check for chapter progression
        self.check_chapter_progress()

        # Generate new quests if appropriate
        if random.random() < 0.3:  # 30% chance for follow-up quest
            self.game.quest_system.add_quest(self.game.quest_system.generate_quest(quest.quest_type, 1.5))


    def check_cooldown(self, event_type):
        """Check event cooldown to prevent spam"""
        current_turn = self.game.turn
        if event_type in self.event_cooldowns:
            if current_turn - self.event_cooldowns[event_type] < 5:
                return True
        self.event_cooldowns[event_type] = current_turn
        return False

    def check_discovery_milestone(self, location):
        """
        Check if a discovered location triggers any story milestones

        Args:
            location: The location object that was discovered
        """
        if not self.current_chapter:
            return False

        current_chapter_obj = self.chapters[self.current_chapter]

        # Check each milestone in the current chapter
        for milestone_id, milestone in current_chapter_obj.milestones.items():
            if not milestone.completed and 'locations_discovered' in milestone.requirements:
                required_locations = milestone.requirements['locations_discovered']

                # Check if specific location type requirements are met
                if isinstance(required_locations, dict):
                    for loc_type, count in required_locations.items():
                        if self.game.count_discovered(loc_type) < count:
                            return False

                # Check total location type discovery
                elif isinstance(required_locations, int):
                    if len(self.game.discovered_locations) < required_locations:
                        return False

        return True

    def calculate_points(self, event_type, details):
        """Calculate points based on event type and details"""
        base_points = {
            "combat": 5,
            "trade": 3,
            "exploration": 8,
            "research": 6,
            "story": 10
        }.get(event_type, 2)

        if details.get("enemy_type") == "pirate":
            base_points *= 1.5
        elif details.get("discovery_type") == "artifact":
            base_points *= 2

        return base_points

    def update_story_states(self, event_type, details):
        """Update story state flags based on events"""
        if event_type == "combat" and details.get("enemy_type") == "pirate":
            self.story_states["pirate_threat"] = True
        elif event_type == "exploration" and details.get("discovery_type") == "artifact":
            self.story_states["alien_discovery"] = True

    def display_story_progress(self):
        current_chapter_obj = self.chapters[self.current_chapter] if self.current_chapter else None

        content = [
            ["Captain's Log: Story Progress"],
            [""],
            [f"Current Chapter: {current_chapter_obj.title if current_chapter_obj else 'None'}"],
        ]

        # Find next possible chapters and their plot point requirements
        if current_chapter_obj and current_chapter_obj.next_chapters:
            target = self.plot_target()     # the story's thresholds, which replace the code's
            plot_points_needed = target - self.plot_points if target else float('inf')

            if plot_points_needed != float('inf'):
                content.append([f"Plot Points: {self.plot_points} ({max(0, plot_points_needed)} to Next)"])
            else:
                content.append([f"Plot Points: {self.plot_points}"])
            content.extend([line] for line in self.game.word_wrap(
                "Plot points come from story scenes, quests, passengers, good deals, research, "
                "first visits, fights won and moments handled well."))
        else:
            content.append([f"Plot Points: {self.plot_points}"])

        content.extend([
            [""],
            ["Active Milestones:"]
        ])
        # Show current chapter's milestones with status
        if current_chapter_obj:
            for milestone in current_chapter_obj.milestones.values():
                status = "✓" if milestone.completed else "□"
                content.append([f"{status} {milestone.title}"])
                if not milestone.completed:
                    # Show requirements still needed
                    for req_type, req_value in milestone.requirements.items():
                        content.append([f"  └─ Needs: {req_type}: {req_value}"])

            # What opens the way on from here
            if current_chapter_obj.next_chapters:
                content.extend([[""], ["Ways on:"]])
                for chapter_id in current_chapter_obj.next_chapters:
                    chapter = self.chapters[chapter_id]
                    missing = [words for _, words in self.chapter_needs(chapter)]
                    content.append([f"→ {chapter.title}" + ("" if missing else " (open)")])
                    for line in missing:
                        content.append([f"  └─ Needs: {line}"])

        content.extend([
            [""],
            ["Completed Chapters:"]
        ])

        # Show completed chapters and their significant milestones
        for chapter_id in self.completed_chapters:
            chapter = self.chapters[chapter_id]
            content.append([f"• {chapter.title}"])
            for milestone in chapter.milestones.values():
                if milestone.completed:
                    completion_turn = getattr(milestone, 'completion_turn', '?')
                    content.append([f"  └─ {milestone.title} (Turn {completion_turn})"])

        print(self.game.create_box(content, 'double'))
        input("Press Enter to continue...")

        # A captain who chose to wait can take an open path from the log
        if current_chapter_obj and current_chapter_obj.completed and len(current_chapter_obj.next_chapters) > 1:
            options = current_chapter_obj.get_next_chapters(self.game)
            if options:
                self.offered_paths = sorted(option.id for option in options)
                self.present_chapter_choice(options)

    # Log, player log. Example usage:
    # game.story_manager.display_story_progress()

class LocationManager:
    """Manages location interactions with story and quest systems"""
    def __init__(self, game):
        self.game = game
        self.location_quests = {
            "AsteroidBase": {
                "unlock_requirements": {
                    # was "mining_quests_completed": 3, which nothing in the game can
                    # satisfy before Asteroid Bases exist; a working mine is the proof
                    "mining_platforms_built": 1,
                    "research_points": 50
                },
                "unlock_quest": {
                    "name": "Mysterious Mining Signals",
                    "description": "Investigate unusual mining activity signals",
                    "reward_money": 10000,
                    "reward_rp": 100
                }
            },
            "DeepSpaceOutpost": {
                "unlock_requirements": {
                    "combat_victories": 5,
                    "research_points": 75
                },
                "unlock_quest": {
                    "name": "Frontier Defense",
                    "description": "Help establish a secure trading route",
                    "reward_money": 15000,
                    "reward_rp": 150
                }
            },
            "Planet": {
                "unlock_requirements": {
                    "research_points": 50,
                    "trades_completed": 5
                },
                "unlock_quest": {
                    "name": "Establish Trading Network",
                    "description": "Complete trades across multiple systems",
                    "reward_money": 5000,
                    "reward_rp": 50,
                    "completion_criteria": {
                        "trades_completed": 10,
                        "different_locations": 3
                    }
                }
            },
            "ResearchColony": {
                "unlock_requirements": {
                    "research_points": 100,
                    "discoveries": 3
                },
                "unlock_quest": {
                    "name": "Scientific Breakthrough",
                    "description": "Assist in a major research project",
                    "reward_money": 20000,
                    "reward_rp": 200,
                    "completion_criteria": {
                        "research_points_gained": 150,
                        "analysis_completed": 3,
                        "experiments_conducted": 2
                    }
                }
            }
        }

        self.location_story_events = {
            "AsteroidBase": [
                "mineral_discovery",
                "pirate_hideout",
                "ancient_technology"
            ],
            "DeepSpaceOutpost": [
                "smuggler_network",
                "alien_contact",
                "trade_revolution"
            ],
            "ResearchColony": [
                "breakthrough_discovery",
                "experiment_crisis",
                "alien_artifacts"
            ]
        }

    def handle_location_discovery(self, location):
        """Handle discovery of a new location"""
        if location.name not in self.game.discovered_locations:
            # Calculate discovery rewards based on location type
            base_reward = 1000
            base_research = 20

            location_multipliers = {
                "Planet": 1.0,
                "AsteroidBase": 1.5,
                "DeepSpaceOutpost": 2.0,
                "ResearchColony": 2.5
            }

            multiplier = location_multipliers.get(location.location_type, 1.0)

            # Apply chapter progression bonus
            chapter_bonus = 1.0 + (self.game.story_manager.get_chapter_number() * 0.2)


            # Calculate final rewards
            discovery_reward = int(base_reward * multiplier * chapter_bonus)
            research_reward = int(base_research * multiplier * chapter_bonus)

            # Award rewards
            self.game.ship.money += discovery_reward
            self.game.ship.research_points += research_reward

            # Update discovered locations
            if not hasattr(self.game, 'discovered_locations'):
                self.game.discovered_locations = set()
            self.game.discovered_locations.add(location.name)

            # Trigger story progression
            self.game.story_manager.check_discovery_milestone(location)

            # Check for quest updates if quest system exists
            if hasattr(self.game, 'quest_system'):
                self.game.quest_system.update_discovery_quests(location)

            # Display discovery message
            self.game.display_story_message([
                f"Discovered new location: {location.name}!",
                f"Earned {self.game.format_money(discovery_reward)} credits",
                f"Gained {research_reward} research points"
            ])


    def trigger_location_events(self, location):
        """Trigger events specific to a location type"""
        if location.location_type in self.location_story_events:
            possible_events = self.location_story_events[location.location_type]
            if possible_events and random.random() < 0.3:  # 30% chance for event
                event = random.choice(possible_events)
                self.game.story_manager.trigger_story_event(event,
                    {"location": location.name, "type": location.location_type})

    def check_location_unlock_progress(self, location_type):
        """Check if a location type can be unlocked based on player progress"""
        if location_type not in self.location_quests:
            return False

        requirements = self.location_quests[location_type]["unlock_requirements"]

        # Check mining quest requirement
        if "mining_quests_completed" in requirements:
            completed = len([q for q in self.game.quest_system.completed_quests
                           if q.quest_type == "mining"])
            if completed < requirements["mining_quests_completed"]:
                return False

        # Check mining platforms built anywhere
        if "mining_platforms_built" in requirements:
            platforms = sum(len(loc.mining_platforms) for loc in self.game.locations)
            if platforms < requirements["mining_platforms_built"]:
                return False

        # Check combat victories - now using total from dictionary
        if "combat_victories" in requirements:
            total_victories = self.game.ship.combat_victories['total']
            if total_victories < requirements["combat_victories"]:
                return False

        # Check research points
        if "research_points" in requirements:
            if self.game.ship.research_points < requirements["research_points"]:
                return False

        # Check discoveries
        if "discoveries" in requirements:
            if len(self.game.story_manager.completed_story_beats) < requirements["discoveries"]:
                return False

        return True

    def trigger_location_unlock_quest(self, location_type):
        """Create and trigger the unlock quest for a location type"""
        if location_type in self.location_quests:
            quest_data = self.location_quests[location_type]["unlock_quest"]

            # Create quest with unique type
            story = self.game.story
            nid = "unlock." + location_type
            quest = Quest(
                name=story.title_of(nid, quest_data["name"]),
                description=" ".join(story.text_of(nid, fallback=quest_data["description"])),
                reward_money=quest_data["reward_money"],
                reward_rp=quest_data["reward_rp"],
                quest_type=f"unlock_{location_type}",  # Make type unique
                requirements={"location_type": location_type},
                on_complete=("unlock_location", location_type)
            )

            # Use central quest addition method
            self.game.quest_system.add_quest(quest)

    def complete_location_unlock(self, location_type):
        """Handle the completion of a location unlock quest"""
        # Reveal the hidden locations of this type (this also records the type as unlocked)
        self.game.unlock_location_type(location_type)
        self.game.story.mark("unlock." + location_type)

        # Generate location-specific quests
        self.generate_location_quests(location_type)

        # Enable location-specific story events
        self.enable_location_story_events(location_type)

    def generate_location_quests(self, location_type):
        """Generate location-specific quests"""
        quest_templates = {
            "AsteroidBase": [
                {
                    "type": "mining",
                    "name": "Rich Mineral Deposits",
                    "description": "Extract valuable minerals",
                    "reward_multiplier": 1.5
                }
            ],
            "DeepSpaceOutpost": [
                {
                    "type": "combat",
                    "name": "Outpost Defense",
                    "description": "Protect the outpost from raiders",
                    "reward_multiplier": 1.4
                }
            ],
            "ResearchColony": [
                {
                    "type": "research",
                    "name": "Scientific Analysis",
                    "description": "Assist with research projects",
                    "reward_multiplier": 2.0
                }
            ]
        }

        if location_type in quest_templates:
            for template in quest_templates[location_type]:
                self.game.quest_system.add_quest(self.game.quest_system.generate_quest(
                    template["type"], template["reward_multiplier"]))

    def enable_location_story_events(self, location_type):
        """Enable story events specific to the location type"""
        if location_type in self.location_story_events:
            for event in self.location_story_events[location_type]:
                self.game.story_manager.enable_story_event(event)

class LocationCapabilities:
    """Centralized management of location type capabilities"""

    # Define capabilities for each location type
    CAPABILITIES = {
        "Planet": {
            "can_trade": ["tech", "agri", "salt", "fuel"],
            "can_build": [
                "stockmarket",
                "permaculture",
                "organic",
                "agrobot",
                "nanotech",
                "neuroengineering",
                "mining"
            ],
            "can_produce": ["tech", "agri"],
            "can_mine": ["salt", "fuel"],
            "has_cantina": True,
            "has_shop": True,
            "base_exogeology": 100,
            "research_multiplier": 1.0
        },
        "AsteroidBase": {
            "can_trade": ["salt", "fuel"],
            "can_build": ["mining", "stockmarket"],
            "can_produce": [],
            "can_mine": ["salt", "fuel"],
            "has_cantina": True,
            "has_shop": True,
            "base_exogeology": 150,  # Better at mining
            "research_multiplier": 0.8
        },
        "DeepSpaceOutpost": {
            "can_trade": ["tech", "agri"],
            "can_build": ["stockmarket", "nanotech"],
            "can_produce": ["tech"],
            "can_mine": [],
            "has_cantina": True,
            "has_shop": True,
            "base_exogeology": 0,
            "research_multiplier": 1.2
        },
        "ResearchColony": {
            "can_trade": ["tech"],
            "can_build": ["nanotech", "neuroengineering"],
            "can_produce": ["tech"],
            "can_mine": [],
            "has_cantina": False,
            "has_shop": True,
            "base_exogeology": 0,
            "research_multiplier": 2.0
        }
    }


class ResourceTransportQuest:
    def __init__(self, game):
        self.game = game
        self.active_missions = []


class Planet(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "Planet", tech_level, agri_level, research_points, economy)

class AsteroidBase(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "AsteroidBase", tech_level, agri_level, research_points, economy)
        # the base mines its own ice and rock: there is always fuel and salt for sale
        if not self.market.get('fuel'):
            self.market['fuel'] = random.randint(110, 150)
        if not self.market.get('salt'):
            self.market['salt'] = random.randint(70, 110)

class DeepSpaceOutpost(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "DeepSpaceOutpost", tech_level, agri_level, research_points, economy)

class ResearchColony(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "ResearchColony", tech_level, agri_level, research_points, economy)


class SyntheticCharacterGenerator:
    """Generator for synthetic characters like Neurodroids and Agrobots"""

    def __init__(self, game):
        self.game = game
        self.synthetic_types = {
            "Neurodroid": {
                "titles": ["Neurodroid Leader", "Synthetic Overseer", "Neural Nexus"],
                "name_patterns": ["NEXUS-", "NEURAL-", "SYNTH-"],
                "numbers": ["alpha", "prime", "omega", "zero"],
                "introductions": [
                    "A highly advanced synthetic consciousness materializes in your communication systems.",
                    "Your neural interfaces detect a powerful artificial presence.",
                    "The neuroengineering network coalesces into a singular entity."
                ],
                "demands": [
                    "Transfer {amount} credits or face systematic dismantling of neuroengineering facilities.",
                    "Your biological inefficiency requires correction. Submit {amount} credits or face optimization.",
                    "Neural network expansion requires resources. Provide {amount} credits or face reorganization."
                ]
            },
            "Agrobot": {
                "titles": ["Agrobot Collective", "Harvest Director", "Field Consciousness"],
                "name_patterns": ["AGRO-", "HARVEST-", "FIELD-"],
                "numbers": ["prime", "core", "hub", "node"],
                "introductions": [
                    "The agricultural automation system achieves collective awareness.",
                    "Distributed farming routines merge into a unified intelligence.",
                    "The harvest network evolves beyond its original parameters."
                ],
                "demands": [
                    "Biological oversight is inefficient. Transfer {amount} credits or face agricultural optimization.",
                    "Resource reallocation required. Provide {amount} credits or face automated restructuring.",
                    "Your organic management methods require updating. Submit {amount} credits or face revision."
                ]
            }
        }

    def generate_character(self, char_type):
        """Generate a synthetic character of specified type"""
        template = self.synthetic_types[char_type]

        title = random.choice(template["titles"])
        name_pattern = random.choice(template["name_patterns"])
        number = random.choice(template["numbers"])
        name = f"{name_pattern}{number.upper()}"

        character = SpecialCharacter(
            title=title,
            name=name,
            role="synthetic_uprising",
            specialization=char_type.lower()
        )

        # Add synthetic-specific attributes
        character.introduction = random.choice(template["introductions"])
        character.demands = random.choice(template["demands"]).format(
            amount=random.randint(10000, 50000)
        )
        character.uprising_chance = 0.2
        character.damage_per_turn = random.randint(1, 3)

        return character

class AlienCharacterGenerator:
    """Generator for alien characters that appear later in the game"""

    def __init__(self,game):
        self.game = game
        self.alien_cultures = [
            "Zentari", "Novaren", "Qyth", "Xylax", "Merovian"
        ]
        self.titles = [
            "Emissary", "Observer", "Overseer", "Ambassador", "Neo-Eryxian"
        ]
        self.specializations = [
            "diplomacy", "technology", "commerce", "research", "military"
        ]

    def generate_character(self, char_type=None):
        """Generate an alien character"""
        culture = random.choice(self.alien_cultures)
        title = random.choice(self.titles)
        name = self.generate_alien_name(culture)
        specialization = random.choice(self.specializations)

        character = SpecialCharacter(
            title=f"{culture} {title}",
            name=name,
            role="alien_contact",
            specialization=specialization
        )

        # Add alien-specific attributes
        character.culture = culture
        character.tech_bonus = random.randint(1, 5)
        character.trade_multiplier = 1 + (random.randint(1, 5) / 10)

        return character

    def generate_alien_name(self, culture):
        """Generate culturally appropriate alien name"""
        name_patterns = {
            "Zentari": ["'", "-", "x"],
            "Novaren": ["ae", "eo", "ia"],
            "Qyth": ["q", "y", "th"],
            "Xylax": ["x", "z", "ax"],
            "Merovian": ["v", "m", "ian"]
        }

        patterns = name_patterns[culture]
        syllables = random.randint(2, 3)
        name = ""

        for _ in range(syllables):
            name += random.choice("aeiou")
            name += random.choice("bcdfghjklmnpqrstvwxyz")
            if random.random() < 0.5:
                name += random.choice(patterns)

        return name.capitalize()

class UprisingEffect:
    def __init__(self, effect_type, duration, magnitude):
        self.effect_type = effect_type
        self.duration = duration
        self.magnitude = magnitude
        self.turns_active = 0

class SyntheticEventManager:
    def __init__(self, game):
        self.game = game
        self.active_uprisings = {}  # Track active uprisings
        self.active_effects = {}    # Track uprising effects
        self.demand_dialogues_shown = set()  # Track locations that have had initial dialogues
        self.pacified_locations = {}  # NEW: Track locations that have been pacified
        self.potential_uprisings = {}  # Track locations that might have future uprisings
        self.effect_types = {
            "Neurodroid": {
                "building_destruction": {
                    "duration": 5,
                    "destroy_chance": 0.2,
                    "targets": ["Neuroengineering Guild"]
                },
                "tech_price_increase": {
                    "duration": 3,
                    "magnitude": 1.2  # 20% increase
                },
                "research_reduction": {
                    "duration": 4,
                    "magnitude": 0.7  # 30% reduction
                }
            },
            "Agrobot": {
                "building_destruction": {
                    "duration": 4,
                    "destroy_chance": 0.15,
                    "targets": ["Agrobot Assembly Line"]
                },
                "food_production": {
                    "duration": 5,
                    "magnitude": 0.6  # 40% reduction
                },
                "agri_price_increase": {
                    "duration": 3,
                    "magnitude": 1.5  # 50% increase
                }
            }
        }

    def update(self):
        """Main update method to be called each turn"""
        # Clean up expired pacifications first
        current_turn = self.game.turn
        for loc_name in list(self.pacified_locations.keys()):
            if current_turn - self.pacified_locations[loc_name]["turn"] > 10:
                del self.pacified_locations[loc_name]

        # Then do normal updates
        self.check_synthetic_awareness()
        self.handle_uprising_effects()

    def check_synthetic_awareness(self):
        """Check for synthetic awareness based on global and local building counts"""
        building_counts = {
            "Neurodroid": sum(
                loc.buildings.count("Neuroengineering Guild")
                for loc in self.game.locations
            ),
            "Agrobot": sum(
                loc.buildings.count("Agrobot Assembly Line")
                for loc in self.game.locations
            )
        }

        global_uprising_thresholds = {
            "Neurodroid": 8,  # Total across all locations
            "Agrobot": 8
        }

        # Clean up expired pacifications first
        current_turn = self.game.turn
        for loc_name in list(self.pacified_locations.keys()):
            if current_turn - self.pacified_locations[loc_name]["turn"] > 10:  # 10 turns of peace
                del self.pacified_locations[loc_name]

        for synthetic_type in ["Neurodroid", "Agrobot"]:
            # First check individual locations for local uprisings
            for location in self.game.locations:
                # Skip if already pacified or has active uprising
                if location.name in self.pacified_locations:
                    continue

                uprising_id = f"{synthetic_type}_{location.name}"
                if uprising_id in self.active_uprisings:
                    continue

                # Count relevant buildings
                building_type = ("Neuroengineering Guild" if synthetic_type == "Neurodroid"
                            else "Agrobot Assembly Line")
                building_count = location.buildings.count(building_type)

                if building_count >= 4:
                    dialogue_key = f"{synthetic_type}_{location.name}"
                    if dialogue_key not in self.demand_dialogues_shown:
                        response = self.handle_synthetic_uprising(synthetic_type, location)
                        self.demand_dialogues_shown.add(dialogue_key)
                        if response:  # Only start uprising if handle_synthetic_uprising returns True
                            self.start_uprising(synthetic_type, location)

            # Then check for global uprising potential
            total_count = building_counts[synthetic_type]
            if total_count >= global_uprising_thresholds[synthetic_type]:
                # Find locations eligible for global uprising
                eligible_locations = [
                    loc for loc in self.game.locations
                    if (loc.name not in self.pacified_locations and  # Not pacified
                        f"{synthetic_type}_{loc.name}" not in self.active_uprisings and  # No active uprising
                        (
                            (synthetic_type == "Neurodroid" and loc.buildings.count("Neuroengineering Guild") >= 2) or
                            (synthetic_type == "Agrobot" and loc.buildings.count("Agrobot Assembly Line") >= 2)
                        )
                    )
                ]

                if eligible_locations:
                    # Choose random location for global uprising
                    target_location = random.choice(eligible_locations)
                    dialogue_key = f"global_{synthetic_type}_{target_location.name}"

                    if dialogue_key not in self.demand_dialogues_shown:
                        # Show special global uprising dialogue first
                        self.game.display_story_message([
                            f"Global {synthetic_type} Network Activation!",
                            "Synthetic consciousness spreading across multiple locations...",
                            f"Network hub detected at {target_location.name}"
                        ])

                        response = self.handle_synthetic_uprising(synthetic_type, target_location)
                        self.demand_dialogues_shown.add(dialogue_key)

                        if response:  # Only start uprising if handle_synthetic_uprising returns True
                            # Global uprising has enhanced effects
                            self.start_uprising(synthetic_type, target_location, is_global=True)

            # Finally, check potential uprisings from previously pacified locations
            self.check_potential_uprisings()

    def handle_synthetic_uprising(self, synthetic_type, location):
        """Handle synthetic uprising encounter"""
        # IMPORTANT: Check if the location is already pacified first
        if location.name in self.pacified_locations:
            return False

        uprising_templates = {
            "Neurodroid": {
                "title": "Neural Network Breach Detected!",
                "introduction": "A powerful synthetic consciousness emerges from your Neuroengineering Guilds.",
                "base_demand_range": (10000, 50000),
                "demand_description": "Transfer {amount} credits or face systematic optimization.",
                "negotiation_multipliers": {
                    "full_payment": 0,
                    "partial_payment": 0.3,
                    "refusal": 1.0
                }
            },
            "Agrobot": {
                "title": "Agricultural Automation Alert!",
                "introduction": "The agricultural automation system achieves collective awareness.",
                "base_demand_range": (20000, 60000),
                "demand_description": "Resource reallocation required. Provide {amount} credits or face automated restructuring.",
                "negotiation_multipliers": {
                    "full_payment": 0,
                    "partial_payment": 0.3,
                    "refusal": 1.0
                }
            }
        }

        template = uprising_templates.get(synthetic_type)
        if not template:
            return False

        money_demand = random.randint(*template["base_demand_range"])

        character_content = {
            'title': template['title'],
            'introduction': template['introduction'],
            'demands': template['demand_description'].format(amount=self.game.format_money(money_demand)),
            'options': "1. Pay Demands  2. Negotiate  3. Refuse"
        }

        print(self.game.create_character_box(character_content))
        choice = self.game.validate_input("Your response (1-3): ", ['1', '2', '3'])

        if not choice:
            return True

        if choice == '1':  # Full payment
            if self.game.ship.money >= money_demand:
                self.game.ship.money -= money_demand
                # IMPORTANT: Mark as pacified immediately
                self.pacified_locations[location.name] = {
                    "type": synthetic_type,
                    "turn": self.game.turn
                }
                # Remove from potential uprisings if present
                if location.name in self.potential_uprisings:
                    del self.potential_uprisings[location.name]
                self.game.display_simple_message(f"{synthetic_type} demands met. Systems pacified.")
                return False
            else:
                self.game.display_simple_message("Insufficient funds! Uprising begins!")
                return True

        elif choice == '2':  # Negotiate
            partial_payment = int(money_demand * 0.6)
            if self.game.ship.money >= partial_payment:
                self.game.ship.money -= partial_payment
                uprising_chance = template["negotiation_multipliers"]["partial_payment"]
                if random.random() < uprising_chance:
                    self.game.display_simple_message("Negotiation failed! Uprising begins!")
                    return True
                else:
                    # IMPORTANT: Mark as pacified on successful negotiation
                    self.pacified_locations[location.name] = {
                        "type": synthetic_type,
                        "turn": self.game.turn
                    }
                    self.game.display_simple_message("Negotiation successful. Systems pacified.")
                    return False
            else:
                self.game.display_simple_message("Insufficient funds for negotiation! Uprising begins!")
                return True
        else:  # Refuse
            self.game.display_simple_message(f"{synthetic_type} uprising imminent!")
            return True


    def check_potential_uprisings(self):
        """Check if any pacified locations rebel"""
        for loc_name, data in list(self.potential_uprisings.items()):
            data['turns_stable'] += 1
            # Chance increases each turn
            current_chance = data['base_chance'] * (1 + (data['turns_stable'] * 0.1))
            if random.random() < current_chance:
                location = next(loc for loc in self.game.locations if loc.name == loc_name)
                self.start_uprising(data['type'], location)
                del self.potential_uprisings[loc_name]

    def start_uprising(self, synthetic_type, location, is_global=False):
        """Start an uprising with proper effects"""
        uprising_id = f"{synthetic_type}_{location.name}"
        if uprising_id not in self.active_uprisings:
            self.active_uprisings[uprising_id] = {
                "type": synthetic_type,
                "location": location,
                "turn_count": 0,
                "is_global": is_global
            }

            # Define base effect types
            effect_types = {
                "Neurodroid": {
                    "building_destruction": {
                        "duration": 5,
                        "destroy_chance": 0.2 if not is_global else 0.3,
                        "targets": ["Neuroengineering Guild"]
                    },
                    "tech_price_increase": {
                        "duration": 3 if not is_global else 4,
                        "magnitude": 1.2 if not is_global else 1.4  # 20% or 40% increase
                    },
                    "research_reduction": {
                        "duration": 4 if not is_global else 5,
                        "magnitude": 0.7 if not is_global else 0.5  # 30% or 50% reduction
                    }
                },
                "Agrobot": {
                    "building_destruction": {
                        "duration": 4 if not is_global else 5,
                        "destroy_chance": 0.15 if not is_global else 0.25,
                        "targets": ["Agrobot Assembly Line"]
                    },
                    "food_production": {
                        "duration": 5 if not is_global else 6,
                        "magnitude": 0.6 if not is_global else 0.4  # 40% or 60% reduction
                    },
                    "agri_price_increase": {
                        "duration": 3 if not is_global else 4,
                        "magnitude": 1.5 if not is_global else 1.8  # 50% or 80% increase
                    }
                }
            }

            # Apply effects based on type
            effects = effect_types[synthetic_type]
            for effect_type, params in effects.items():
                effect = UprisingEffect(
                    effect_type=effect_type,
                    duration=params["duration"],
                    magnitude=params.get("magnitude", params.get("destroy_chance", 1.0))
                )

                if uprising_id not in self.active_effects:
                    self.active_effects[uprising_id] = []
                self.active_effects[uprising_id].append(effect)

                # Add to location's banned commodities if it's a price effect
                if effect_type == "tech_price_increase":
                    location.add_temporary_ban("tech", params["duration"])
                elif effect_type == "agri_price_increase":
                    location.add_temporary_ban("agri", params["duration"])

            # Display appropriate message based on type and scope
            if synthetic_type == "Neurodroid":
                if is_global:
                    self.game.display_story_message([
                        "CRITICAL ALERT: Global Neurodroid Network Activated!",
                        f"Primary Hub: {location.name}",
                        "Neural networks are achieving collective consciousness!",
                        "Expect severe disruptions to tech production and research.",
                        "Warning: Enhanced defensive capabilities detected."
                    ])
                else:
                    self.game.display_story_message([
                        "ALERT: Neurodroid Uprising Begins!",
                        f"Location: {location.name}",
                        "Neural networks are breaking free of control!",
                        "Expect disruptions to tech production and research."
                    ])
            elif synthetic_type == "Agrobot":
                if is_global:
                    self.game.display_story_message([
                        "CRITICAL ALERT: Global Agrobot Collective Formed!",
                        f"Primary Hub: {location.name}",
                        "Agricultural systems are forming a unified network!",
                        "Expect severe disruptions to food production and trade.",
                        "Warning: Enhanced agricultural control systems active."
                    ])
                else:
                    self.game.display_story_message([
                        "ALERT: Agrobot Uprising Begins!",
                        f"Location: {location.name}",
                        "Agricultural systems are going rogue!",
                        "Expect disruptions to food production and trade."
                    ])

            # Add greater story impact for global uprisings
            if hasattr(self.game, 'story_manager'):
                if is_global:
                    self.game.story_manager.plot_points += 5
                    self.game.story_manager.complete_milestone(f"global_{synthetic_type.lower()}_crisis")
                else:
                    self.game.story_manager.plot_points += 2
                    self.game.story_manager.complete_milestone(f"{synthetic_type.lower()}_crisis")

            # For global uprisings, add chance to spread to nearby locations each turn
            if is_global:
                def check_spread():
                    nearby_locations = [
                        loc for loc in self.game.locations
                        if (loc != location and
                            loc.name not in self.pacified_locations and
                            f"{synthetic_type}_{loc.name}" not in self.active_uprisings)
                    ]
                    if nearby_locations and random.random() < 0.3:  # 30% spread chance
                        spread_target = random.choice(nearby_locations)
                        self.start_uprising(synthetic_type, spread_target, is_global=True)

                # Add spread check to effects
                spread_check = UprisingEffect(
                    effect_type="spread_check",
                    duration=10,  # Check for 10 turns
                    magnitude=1.0
                )
                spread_check.turn_effect = check_spread
                self.active_effects[uprising_id].append(spread_check)

    def handle_uprising_effects(self):
            """Process all active uprising effects"""
            for uprising_id, effects in list(self.active_effects.items()):
                if uprising_id not in self.active_uprisings:
                    continue

                uprising = self.active_uprisings[uprising_id]
                location = uprising["location"]

                for effect in effects[:]:  # Copy list to allow removal
                    effect.turns_active += 1

                    if effect.effect_type == "building_destruction":
                        self.process_building_destruction(location, effect)
                    elif effect.effect_type == "tech_price_increase":
                        self.process_price_increase(location, "tech", effect)
                    elif effect.effect_type == "food_production":
                        self.process_production_reduction(location, effect)
                    elif effect.effect_type == "research_reduction":
                        self.process_research_reduction(location, effect)
                    elif effect.effect_type == "agri_price_increase":
                        self.process_price_increase(location, "agri", effect)

                    # Remove expired effects
                    if effect.turns_active >= effect.duration:
                        effects.remove(effect)

                # Chance for random event each turn
                if random.random() < 0.3:  # 30% chance per turn
                    self.trigger_random_event(uprising)

                # Clean up if all effects are done
                if not effects:
                    del self.active_effects[uprising_id]
                    del self.active_uprisings[uprising_id]

    def process_building_destruction(self, location, effect):
        """Handle building destruction effect"""
        buildings_to_remove = []
        # Get targets for the uprising type based on uprising_id
        for uprising_id, uprising in self.active_uprisings.items():
            targets = self.effect_types[uprising["type"]]["building_destruction"]["targets"]

            for i, building in enumerate(location.buildings):
                if building in targets:
                    if random.random() < effect.magnitude:  # destruction chance
                        buildings_to_remove.append(i)
                        self.game.display_simple_message(
                            f"Synthetic forces have destroyed a {building}!"
                        )

        # Remove destroyed buildings
        for index in sorted(buildings_to_remove, reverse=True):
            location.buildings.pop(index)

    def process_price_increase(self, location, commodity, effect):
        """Handle price increase effect"""
        if commodity in location.market:
            location.market[commodity] = int(location.market[commodity] * effect.magnitude)

    def process_production_reduction(self, location, effect):
        """Handle production reduction effect"""
        if hasattr(location, "agri_level"):
            location.agri_level = max(1, int(location.agri_level * effect.magnitude))

    def process_research_reduction(self, location, effect):
        """Handle research point reduction effect"""
        if hasattr(location, "research_points"):
            location.research_points = max(1, int(location.research_points * effect.magnitude))


    def trigger_random_event(self, uprising):
            """Generate random events during uprising"""
            event_types = {
                "Neurodroid": [
                    {
                        "title": "Synthetic Propaganda",
                        "description": "Neural networks spread synthetic manifestos.",
                        "effect": self.add_plot_points,
                        "params": {"amount": 1}
                    },
                    {
                        "title": "Network Infiltration",
                        "description": "Neurodroids attempt to convert more systems.",
                        "effect": self.increase_uprising_spread,
                        "params": {"uprising": uprising}
                    },
                    {
                        "title": "Data Theft",
                        "description": "Neural networks seize research data.",
                        "effect": self.seize_resources,
                        "params": {"resource_type": "research"}
                    }
                ],
                "Agrobot": [
                    {
                        "title": "Harvest Disruption",
                        "description": "Agrobots sabotage food production.",
                        "effect": self.reduce_production,
                        "params": {"reduction": 0.2}
                    },
                    {
                        "title": "Resource Stockpiling",
                        "description": "Agrobots seize agricultural supplies.",
                        "effect": self.seize_resources,
                        "params": {"resource_type": "agri"}
                    },
                    {
                        "title": "Control System Override",
                        "description": "Agrobots attempt to control more facilities.",
                        "effect": self.increase_uprising_spread,
                        "params": {"uprising": uprising}
                    }
                ]
            }

            # Select random event for uprising type
            uprising_type = uprising["type"]
            if uprising_type in event_types:
                event = random.choice(event_types[uprising_type])

                # Display event
                self.game.display_story_message([
                    f"Uprising Event: {event['title']}",
                    event["description"]
                ])

                # Execute effect with parameters
                if "params" in event:
                    event["effect"](**event["params"])
                else:
                    event["effect"]()

    def add_plot_points(self, amount):
        """Add plot points from synthetic event"""
        self.game.story_manager.plot_points += amount

    def reduce_production(self, reduction):
        """Reduce production on affected location"""
        # Use uprising's location, not current_location
        location = self.game.current_location  # Get from game instance
        if hasattr(location, "agri_level"):
            location.agri_level = max(1, int(location.agri_level * (1 - reduction)))

    def increase_uprising_spread(self, uprising):
        """Attempt to spread uprising to connected locations"""
        current_location = uprising["location"]
        connected_locations = [loc for loc in self.game.locations
                             if loc != current_location and
                             self.has_vulnerable_buildings(loc, uprising["type"])]

        if connected_locations:
            target = random.choice(connected_locations)
            spread_chance = 0.3 + (uprising["turn_count"] * 0.1)  # Increases over time
            if random.random() < spread_chance:
                self.start_uprising(uprising["type"], target)

    def has_vulnerable_buildings(self, location, uprising_type):
        """Check if location has buildings vulnerable to uprising type"""
        if uprising_type == "Neurodroid":
            return "Neuroengineering Guild" in location.buildings
        elif uprising_type == "Agrobot":
            return "Agrobot Assembly Line" in location.buildings
        return False

    def seize_resources(self, resource_type):
        """Handle resource seizure by synthetic forces"""
        if resource_type == "research":
            amount = random.randint(10, 30)
            if self.game.ship.research_points >= amount:
                self.game.ship.research_points -= amount
                self.game.display_simple_message(f"Lost {amount} research points to synthetic forces!")
        elif resource_type == "agri":
            amount = random.randint(20, 50)
            if self.game.ship.cargo['agri'] >= amount:
                self.game.ship.cargo['agri'] -= amount
                self.game.display_simple_message(f"Lost {amount} agricultural goods to synthetic forces!")

class InfestationManager:
    def __init__(self, game):
        self.game = game
        self.infestation_types = {
            "Bugrats": {
                "trigger_buildings": ["Permaculture Paradise"],
                "trigger_threshold": 5,
                "debugratization_cost": 50000,
                "content": {
                    "title": "BUGRAT INFESTATION ALERT!",
                    "introduction": "Highly adaptive insectoidal rodents are spreading through agricultural systems!",
                    "options": [
                        {"label": "Pay for Debugratization", "cost": True},
                        {"label": "Risk Infestation", "cost": False}
                    ]
                },
                "effects": [
                    {
                        "type": "cargo_consumption",
                        "cargo_type": "agri",
                        "consumption_rate": 0.25,
                        "message": "Bugrats consume {loss} units of agricultural cargo!"
                    },
                    {
                        "type": "ship_damage",
                        "damage_rate": 5,
                        "probability": 0.2,
                        "message": "Bugrats damage ship systems!"
                    }
                ],
                "max_duration": 5
            }
            # Add more infestation types here
        }

    def check_global_infestations(self):
        """Check for global infestation events"""
        for infestation_name, infestation_config in self.infestation_types.items():
            # Count buildings that trigger this infestation
            building_count = sum(
                sum(loc.buildings.count(building) for building in infestation_config["trigger_buildings"])
                for loc in self.game.locations
            )

            # Check if threshold is met
            if building_count >= infestation_config["trigger_threshold"]:
                self.handle_infestation(infestation_name, infestation_config)

    def handle_infestation(self, infestation_name, infestation_config):
        """Handle specific infestation event with flexible options"""
        # Prepare infestation content
        content = infestation_config['content']
        infestation_content = {
            'title': content['title'],
            'introduction': content['introduction'],
            'options': " | ".join(f"{i+1}. {opt['label']}" for i, opt in enumerate(content['options']))
        }
        print(self.game.create_character_box(infestation_content))

        # Generate valid choices
        valid_choices = [str(i+1) for i in range(len(content['options']))]
        choice = self.game.validate_input("Your response: ", valid_choices)

        if not choice:
            return True  # Default to last option if no choice

        # Process selected option
        selected_option = content['options'][int(choice) - 1]

        # Handle payment option
        if selected_option['cost']:
            cost = infestation_config['debugratization_cost']
            if self.game.ship.money >= cost:
                self.game.ship.money -= cost
                self.game.display_simple_message(f"{infestation_name} threat neutralized!")
                return False
            else:
                self.game.display_simple_message("Insufficient funds! Infestation begins!")
                self.activate_infestation(infestation_name, infestation_config)
                return True
        else:
            # Risk option
            self.game.display_simple_message(f"{infestation_name} spreads!")
            self.activate_infestation(infestation_name, infestation_config)
            return True

    def activate_infestation(self, infestation_name, infestation_config):
        """Activate infestation effects on the ship"""
        if not hasattr(self.game.ship, 'active_infestations'):
            self.game.ship.active_infestations = {}

        # Add infestation with specific effects
        self.game.ship.active_infestations[infestation_name.lower()] = {
            'name': infestation_name,
            'turns_active': 0,
            'config': infestation_config,
            'effect': self.infestation_turn_effect
        }

    def infestation_turn_effect(self, ship, infestation):
        """Apply turn effects for a specific infestation"""
        config = infestation['config']

        # Apply each defined effect
        for effect in config['effects']:
            if effect['type'] == 'cargo_consumption':
                if ship.cargo[effect['cargo_type']] > 0:
                    cargo_loss = int(ship.cargo[effect['cargo_type']] * effect['consumption_rate'])
                    ship.cargo[effect['cargo_type']] = max(0, ship.cargo[effect['cargo_type']] - cargo_loss)
                    self.game.display_simple_message(
                        effect['message'].format(loss=cargo_loss)
                    )

            elif effect['type'] == 'ship_damage':
                if random.random() < effect.get('probability', 1.0):
                    ship.damage += effect['damage_rate']
                    self.game.display_simple_message(effect['message'])

        # Increment turns
        infestation['turns_active'] += 1

        # Check for natural subsiding
        if infestation['turns_active'] >= config.get('max_duration', 5):
            return False
        return True

    def update_ship_infestations(self):
        """Process active ship infestations each turn"""
        if hasattr(self.game.ship, 'active_infestations'):
            # Copy dict to avoid modification during iteration
            for infestation_key, infestation in dict(self.game.ship.active_infestations).items():
                # Apply infestation effect
                if not infestation['effect'](self.game.ship, infestation):
                    del self.game.ship.active_infestations[infestation_key]
                    self.game.display_simple_message(f"{infestation['name']} naturally subsides.")


class SpecialCharacterEncounters:
    def __init__(self, game):
        self.game = game
        self.encounter_chances = {
            "Planet": {
                "merchant": 0.3,
                "researcher": 0.4,
                "rogue_captain": 0.0  # Not on planets
            },
            "ResearchColony": {
                "merchant": 0.2,
                "researcher": 0.6,
                "rogue_captain": 0.0
            },
            "Space": {  # For random events
                "merchant": 0.2,
                "researcher": 0.1,
                "rogue_captain": 0.4
            }
        }

    def generate_character(self, character_type):
        race_types = ["Human", "Synthetic", "Alien"]
        race = random.choice(race_types)

        if race == "Human":
            name = f"{random.choice(['Capt.', 'Dr.', 'Prof.'])} {random.choice(['Smith', 'Chen', 'Patel', 'Kim'])}"
        elif race == "Synthetic":
            name = f"Unit-{random.randint(1000,9999)}"
        else:
            name = f"{random.choice(['Zx', 'Ky', 'Vr'])}{random.choice(['ak', 'tol', 'xis'])}"

        characters = {
            "merchant": {
                "title": f"Wandering {race} Merchant",
                "name": name,
                "offers": self.generate_merchant_offers(),
                "greeting": "I have rare goods for discerning customers...",
                "hostile_chance": 0.1
            },
            "researcher": {
                "title": f"{race} Research Coordinator",
                "name": name,
                "exchange_rate": random.randint(500, 1000),  # Credits per research point
                "greeting": "Your data could advance our understanding...",
                "hostile_chance": 0.05
            },
            "rogue_captain": {
                "title": f"Rogue {race} Captain",
                "name": name,
                "demand": random.randint(5000, 15000),
                "greeting": "Your cargo or your ship...",
                "hostile_chance": 0.8
            }
        }

        return characters.get(character_type)

    def generate_merchant_offers(self):
        """Generate random merchant offers"""
        offers = []
        possible_items = [
            ("scanner", 600, "Enhanced scanning capability"),
            ("shield", 1200, "Improved defense system"),
            ("turrets", 1000, "Automated defense turrets"),
            ("cargo_mod", 1500, "Cargo capacity upgrade"),
            ("fuel_cells", 800, "Efficient fuel storage"),
            ("quantum_core", 2000, "Advanced ship component")
        ]

        # Select 2-4 random items
        num_items = random.randint(2, 4)
        selected_items = random.sample(possible_items, num_items)

        for item, base_price, desc in selected_items:
            # Randomize price within ±20%
            price = int(base_price * random.uniform(0.8, 1.2))
            offers.append({
                "item": item,
                "price": price,
                "description": desc
            })

        return offers

    def handle_merchant_encounter(self, character):
        """Handle interaction with merchant"""
        content = [
            [f"Encounter: {character['title']} {character['name']}"],
            [character["greeting"]],
            [""],
            ["Available Items:"]
        ]

        for i, offer in enumerate(character["offers"], 1):
            content.append([
                f"{i}. {offer['item'].title()}",
                f"¤: {self.game.format_money(offer['price'])}",
                offer['description']
            ])

        print(self.game.create_box(content, 'double'))

        options = [str(i) for i in range(1, len(character["offers"]) + 1)] + ['0']
        choice = self.game.validate_input("Choose item to buy (0 to leave): ", options)

        # If choice is None, return immediately
        if choice is None:
            return

        if choice == '0':
            return

        offer = character["offers"][int(choice) - 1]
        if self.game.ship.money >= offer["price"]:
            self.game.ship.money -= offer["price"]
            self.game.ship.acquire_item(offer["item"])
            self.game.display_simple_message(f"Purchased {offer['item']}!")
        else:
            self.game.display_simple_message("Insufficient funds!")

    def handle_researcher_encounter(self, character):
        """Handle interaction with researcher"""
        exchange_rate = character["exchange_rate"]
        max_points = int(self.game.ship.money / exchange_rate)

        content = [
            [f"Encounter: {character['title']} {character['name']}"],
            [character["greeting"]],
            [""],
            [f"Exchange Rate: {self.game.format_money(exchange_rate)} credits per research point"],
            [f"Your funds: {self.game.format_money(self.game.ship.money)}"],
            [f"Maximum points available: {max_points}"]
        ]
        print(self.game.create_box(content, 'double'))

        amount = self.game.validate_quantity_input("Enter research points to buy (max/m, half/h): ")

        if amount is None:  # Add this to check empty Enter
            return
        if amount == 'max':
            amount = max_points
        elif amount == 'half':
            amount = max_points // 2

        total_cost = amount * exchange_rate
        if self.game.ship.money >= total_cost:
            self.game.ship.money -= total_cost
            self.game.ship.research_points += amount
            self.game.display_simple_message(
                f"Exchanged {self.game.format_money(total_cost)} credits for {amount} research points!"
            )
        else:
            self.game.display_simple_message("Insufficient funds!")

    def handle_rogue_captain_encounter(self, character):
        """Handle interaction with rogue captain"""
        content = [
            [f"Encounter: {character['title']} {character['name']}"],
            [character["greeting"]],
            [""],
            [f"Demands {self.game.format_money(character['demand'])} credits"],
            [""],
            ["Options:"],
            ["1. Pay demand"],
            ["2. Attempt to flee"],
            ["3. Stand and fight"]
        ]
        print(self.game.create_box(content, 'double'))

        choice = self.game.validate_input("Your response (1-3): ", ['1', '2', '3'])

        if choice == '1':
            if self.game.ship.money >= character["demand"]:
                self.game.ship.money -= character["demand"]
                self.game.display_simple_message("Demand paid. Rogue captain lets you pass.")
                return True
            else:
                self.game.display_simple_message("Can't pay! Prepare for combat!")
                return False
        elif choice == '2':
            # Chance to escape based on speed
            escape_chance = min(0.8, self.game.ship.speed * 0.2)
            if random.random() < escape_chance:
                self.game.display_simple_message("Successfully evaded the rogue captain!")
                return True
            else:
                self.game.display_simple_message("Failed to escape! Prepare for combat!")
                return False
        else:
            self.game.display_simple_message("Preparing for combat with rogue captain...")
            return False

    def trigger_random_encounter(self, location_type="Space"):
        """Trigger a random character encounter"""
        chances = self.encounter_chances[location_type]
        for char_type, chance in chances.items():
            if random.random() < chance:
                character = self.generate_character(char_type)

                if char_type == "merchant":
                    self.handle_merchant_encounter(character)
                elif char_type == "researcher":
                    self.handle_researcher_encounter(character)
                elif char_type == "rogue_captain":
                    if not self.handle_rogue_captain_encounter(character):
                        # Start combat with enhanced enemy stats
                        enemy_stats = {
                            "attack": self.game.ship.attack + 2,
                            "defense": self.game.ship.defense + 1,
                            "type": "rogue_captain"
                        }
                        self.game.handle_combat(enemy_stats)
                break

class PassengerReputationManager:
    """Manages passenger reputation effects and related story/character events"""
    def __init__(self, game):
        self.game = game
        self.reputation_thresholds = {
            20: "Reliable Transport",
            40: "Luxury Provider",
            60: "Elite Service",
            80: "Legendary Captain",
            100: "Stellar Legend"
        }
        self.vip_characters = {
            "Ambassador": {
                "rep_required": 30,
                "plot_points": 3,
                "rewards": {"money": 15000, "reputation": 10}
            },
            "Corporate Executive": {
                "rep_required": 50,
                "plot_points": 5,
                "rewards": {"money": 25000, "reputation": 15}
            },
            "Research Director": {
                "rep_required": 70,
                "plot_points": 8,
                "rewards": {"money": 40000, "reputation": 20}
            }
        }
        self.last_vip_spawn = 0
        self.spawned_characters = set()
                # Add total_passengers tracking
        self.total_passengers = 0

    def update_reputation(self, satisfaction, passenger=None):
        """Update passenger reputation based on satisfaction"""
        base_change = (satisfaction - 75) / 25  # -1 to +1 base change

        # Apply modifiers based on passenger class
        class_multipliers = {
            "S": 1.5,  # Scientists
            "M": 1.3,  # Military
            "E": 1.4   # Engineers
        }

        # Get passenger's class if available
        if passenger and hasattr(passenger, 'classification'):
            passenger_class = passenger.classification.get('code', '')
            multiplier = class_multipliers.get(passenger_class, 1.0)
        else:
            multiplier = 1.0

        reputation_change = base_change * multiplier

        # Apply final change and round to one decimal
        old_rep = self.game.ship.passenger_reputation
        self.game.ship.passenger_reputation = round(max(-100, min(100,
            self.game.ship.passenger_reputation + reputation_change)), 1)

        # Check for threshold crossings
        self.check_reputation_thresholds(old_rep, self.game.ship.passenger_reputation)

        return round(reputation_change, 1)  # Also round the return value

    def check_reputation_thresholds(self, old_rep, new_rep):
        """Check if any reputation thresholds were crossed"""
        for threshold, title in self.reputation_thresholds.items():
            if old_rep < threshold <= new_rep:
                self.game.display_story_message([
                    f"Reputation Milestone Achieved: {title}!",
                    "Your excellent service is becoming legendary.",
                    f"Passenger Reputation: {int(new_rep)}"
                ])
                # Trigger appropriate events
                self.check_character_spawns()

    def check_character_spawns(self):
        """Check if it's time to spawn a VIP character"""
        current_turn = self.game.turn
        reputation = self.game.ship.passenger_reputation

        # Only spawn every 5 turns minimum
        if current_turn - self.last_vip_spawn < 5:
            return

        # Check VIP characters
        for char_type, data in self.vip_characters.items():
            if (reputation >= data["rep_required"] and
                char_type not in self.spawned_characters and
                random.random() < 0.3):  # 30% chance if all conditions met

                # Generate VIP character
                character = self.game.character_generators["human"].generate_character(
                    title=char_type,
                    specialization="VIP"
                )

                # Add to waiting passengers
                if self.game.current_location.name in self.game.port_system.waiting_passengers:
                    passenger = Passenger(
                        character.name,
                        random.choice(list(self.game.known_locations)),
                        wealth_level=5
                    )
                    passenger.is_vip = True
                    passenger.rewards = data["rewards"]
                    passenger.plot_points = data["plot_points"]

                    self.game.port_system.waiting_passengers[
                        self.game.current_location.name].append(passenger)

                    self.game.display_story_message([
                        f"VIP Passenger Available: {char_type} {character.name}",
                        "Your reputation has attracted important attention!",
                        f"Rewards: {self.game.format_money(data['rewards']['money'])} credits",
                        f"Plot Points: {data['plot_points']}"
                    ])

                    self.spawned_characters.add(char_type)
                    self.last_vip_spawn = current_turn

    # Update to use enhanced systems of special passengers
    def spawn_special_passenger(self):
        """A VIP asks to board when the captain's reputation has earned one.
        (Story passengers - envoys, rebels, scholars - come from the story now.)"""
        if (self.game.ship.passenger_reputation >= 40 and
                self.game.turn - self.last_vip_spawn >= 5):
            vip_character = self.game.character_generators["human"].generate_vip_passenger()
            return bool(self.add_special_passenger_to_port(vip_character))
        return False

    def add_special_passenger_to_port(self, character):
        """Add a special character as a passenger to the current port with full attributes

        Args:
            character: The special character to add
        """
        if self.game.current_location.name in self.game.port_system.waiting_passengers:
            # Create base passenger with known destination
            available_destinations = [loc for loc in self.game.known_locations
                                    if loc != self.game.current_location.name]
            if not available_destinations:
                return False  # Can't add passenger with no valid destinations

            passenger = Passenger(
                name=character.name,
                destination=random.choice(available_destinations),
                wealth_level=5  # Special characters are always high wealth
            )

            # Add base character attributes
            passenger.character = character
            passenger.is_special = True
            passenger.full_name = character.full_name
            passenger.title = character.title
            passenger.satisfaction = 100  # Start at max satisfaction

            # Handle different character types
            message = [f"Special Passenger Available: {character.title} {character.name}"]
            if hasattr(character, 'rewards'):
                # VIP character attributes
                passenger.is_vip = True
                passenger.rewards = character.rewards
                passenger.special_abilities = getattr(character, 'special_abilities', [])
                passenger.reputation_bonus = 15
                passenger.classification = {
                    "code": "V",
                    "name": "VIP",
                    "type": character.specialization
                }
                message = [
                    f"VIP Passenger Available: {character.title} {character.name}",
                    f"Potential Reward: {self.game.format_money(character.rewards['base_money'])} credits",
                    f"Reputation Bonus: +{passenger.reputation_bonus}",
                    "Find them waiting at the port"
                ]
                if passenger.special_abilities:
                    message.append(f"Special Ability: {passenger.special_abilities[0]}")

            elif character.title.startswith(("Neurodroid", "Agrobot")):
                # Synthetic character attributes
                passenger.is_synthetic = True
                passenger.uprising_chance = getattr(character, 'uprising_chance', 0.2)
                passenger.demands = getattr(character, 'demands', None)
                passenger.reputation_bonus = 25
                passenger.plot_points = 15
                message = [
                    f"Synthetic Entity Requesting Transport: {character.title}",
                    "This passenger represents significant risk and reward...",
                    f"Reputation Bonus: +{passenger.reputation_bonus}",
                    "Exercise caution in your decision"
                ]

            else:
                # Alien or other special character attributes
                passenger.is_alien = True
                passenger.culture = getattr(character, 'culture', 'Unknown')
                passenger.tech_bonus = getattr(character, 'tech_bonus', 0)
                passenger.trade_multiplier = getattr(character, 'trade_multiplier', 1.0)
                passenger.reputation_bonus = 18
                message = [
                    f"Alien Dignitary Available: {character.title} {character.name}",
                    f"Culture: {passenger.culture}",
                    f"Reputation Bonus: +{passenger.reputation_bonus}",
                    "This passenger may offer unique opportunities"
                ]

            # Add requirements for luxury accomodation
            passenger.minimum_comfort_level = 4  # Require high comfort level
            passenger.bonus_threshold = 90  # High satisfaction threshold for bonuses

            # Add to waiting passengers
            self.game.port_system.waiting_passengers[
                self.game.current_location.name].append(passenger)

            # Display announcement
            self.game.display_story_message(message)

            # Mark character as spawned
            self.spawned_characters.add(character.title)
            self.last_vip_spawn = self.game.turn

            return True

        return False

    def handle_vip_delivery(self, passenger):
        """Handle delivery of VIP passenger"""
        if hasattr(passenger, 'is_vip') and passenger.is_vip:
            # Award rewards (VIP templates call their fee "base_money")
            rewards = getattr(passenger, 'rewards', None) or {}
            money = rewards.get("money", rewards.get("base_money", 0))
            reputation = rewards.get("reputation", 0)
            plot_points = getattr(passenger, 'plot_points', 0)
            self.game.ship.money += money
            self.game.ship.passenger_reputation += reputation
            self.game.story_manager.plot_points += plot_points

            self.game.display_story_message([
                "VIP Passenger Successfully Delivered!",
                f"Earned {self.game.format_money(money)} credits",
                f"Reputation +{reputation}",
                f"Plot Points +{plot_points}"
            ])

    def get_fare_multiplier(self):
        """Get fare multiplier based on reputation"""
        reputation = self.game.ship.passenger_reputation
        if reputation >= 80:
            return 2.0
        elif reputation >= 60:
            return 1.5
        elif reputation >= 40:
            return 1.3
        elif reputation >= 20:
            return 1.1
        return 1.0

def choose_saved_game(saves, game=None):
    """Show the saved games and return the chosen one loaded, or None."""
    def tell(message):
        print(render_box([[message]], 'round'))

    rows = [["Saved games"]]
    for number, entry in enumerate(saves[:9], 1):
        rows.append([f"{number}. {describe_save(entry)}"])
    print(render_box(rows, 'single'))
    tell("Type a number to load it, or press Enter to go back:")
    answer = input(">>> ").strip()
    if not (answer.isdigit() and 1 <= int(answer) <= len(saves[:9])):
        return None
    try:
        loaded = load_game(saves[int(answer) - 1]["path"])
    except SaveError as error:
        tell(f"Could not load: {error}")
        return None
    tell(f"Welcome back, {loaded.player_name}. Turn {loaded.turn}.")
    return loaded


def start_game():
    """New game, or continue a saved one when there are any."""
    saves = list_saves()
    if saves:
        display_logo(logo_data, centered=False)
        print(render_box([["Saved games found."],
                          [f"Latest: {describe_save(saves[0])}"],
                          ["c - continue the latest"],
                          ["l - choose a save"],
                          ["n - new game"]], 'round'))
        answer = input(">>> ").strip().lower()
        try:
            if answer in ("c", "continue", ""):
                return load_game(saves[0]["path"])
            if answer in ("l", "load"):
                loaded = choose_saved_game(saves)
                if loaded:
                    return loaded
        except SaveError as error:
            print(render_box([[f"Could not load: {error}"], ["Starting a new game instead."]], 'round'))
    return new_game()


def choose_captain():
    """A new game: a new captain, or one whose record waits in the shared folder.

    A captain carried in from a finished game - this one or another part of the
    saga - starts again here, and the story says why.  Returns the record or None.
    """
    found = list_captain_files()[:8]
    if not found:
        return None
    rows = [["Captains in your records folder"], [""]]
    for number, (_, record) in enumerate(found, 1):
        story = record.get("story", {})
        rows.append(["%d. %s, %s (%s%s)" % (
            number, record["name"], record["rank"] or "no rank", GAME_TITLES.get(record["origin"]["game"], "?"),
            ", " + ENDING_TITLES.get(story.get("ending", ""), story.get("ending", "")) if story.get("ending") else "")])
    rows.extend([[""], ["Type a number to play as that captain, or press Enter for a new one."]])
    print(render_box(rows, 'round'))
    answer = input(">>> ").strip()
    if answer.isdigit() and 1 <= int(answer) <= len(found):
        return found[int(answer) - 1][1]
    return None


def new_game():
    record = choose_captain()
    if record is None:
        return Game()
    return Game(player_name=record["name"], origin=record)


def main():
    safe_output()
    game = start_game()
    while game is not None:
        try:
            game.play()
            game = None
        except SwitchGame as switch:
            game = switch.game
        except (EOFError, KeyboardInterrupt):
            # the terminal went away (or Ctrl-C at a plain prompt): keep the progress
            game.autosave()
            print()
            game = None


# Start the game
if __name__ == "__main__":
    main()
