"""Check a story (or a whole saga) for the mistakes that break or waste content.

    python storykit/validate.py story/cargo1.story.json
    python storykit/validate.py story/saga.json            # every part, plus cross-game checks
    python storykit/validate.py FILE --json                # machine-readable, for the map
    python storykit/validate.py FILE --baseline B.json     # fail only on findings not in B
    python storykit/validate.py FILE --baseline B.json --write-baseline

Errors are things the game cannot run (unknown names, broken links).
Warnings are content a player can never see, or flags nobody uses.
Notes are facts worth knowing (empty beats, unused content, opaque conditions).
"""
import json
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story as kit  # noqa: E402


class Report:
    def __init__(self):
        self.items = []

    def add(self, level, code, where, message):
        self.items.append({"level": level, "code": code, "where": where, "message": message})

    def error(self, code, where, message):
        self.add("error", code, where, message)

    def warn(self, code, where, message):
        self.add("warning", code, where, message)

    def note(self, code, where, message):
        self.add("note", code, where, message)

    def count(self, level):
        return sum(1 for i in self.items if i["level"] == level)


def _game_id(story):
    return story.get("game", {}).get("id", os.path.basename(story.get("path", "story")))


def check_story(story, report, saga=None):
    gid = _game_id(story)
    nodes = story["nodes"]
    stats = story["stats"]
    sets = story["sets"]
    places = story["places"]
    flags = story["flags"]
    characters = dict(story["characters"])
    if saga:
        characters.update({k: v for k, v in saga.get("characters", {}).items() if k not in characters})
    effects_vocab = story["effects"]

    def where(nid):
        return "%s:%s" % (gid, nid)

    # ---- names --------------------------------------------------------------
    for nid, node in nodes.items():
        if node.get("kind") not in kit.NODE_KINDS:
            report.error("kind", where(nid), "unknown kind %r" % node.get("kind"))
        if node.get("arc") and node["arc"] not in story["arcs"]:
            report.error("arc", where(nid), "unknown arc %r" % node["arc"])
        for kind, target in kit.references(node):
            if target not in nodes:
                report.error("link", where(nid), "%s refers to unknown node %r" % (kind, target))
        for who in kit.characters_of(node):
            if who not in characters:
                report.error("character", where(nid), "unknown character %r" % who)
        if node.get("where") and node["where"] not in places:
            report.error("place", where(nid), "unknown place %r" % node["where"])

        for cond in kit.node_conditions(node):
            def visit(key, want, path, nid=nid):
                if key in kit.CORE_CONDITIONS:
                    if key in ("at", "at_type", "venue"):
                        for p in kit.as_list(want):
                            if p not in places:
                                report.error("place", where(nid), "condition names unknown place %r" % p)
                    if key == "has":
                        for name, members in want.items():
                            if name not in sets:
                                report.error("set", where(nid), "unknown set %r" % name)
                            elif sets[name].get("members"):
                                for m in kit.as_list(members):
                                    if m not in sets[name]["members"]:
                                        report.error("set", where(nid), "%r is not a member of %s" % (m, name))
                    if key in ("flag", "not_flag"):
                        for f in kit.as_list(want):
                            if f not in flags:
                                report.error("flag", where(nid), "undeclared flag %r" % f)
                    return
                if key not in stats:
                    report.error("stat", where(nid), "unknown condition or stat %r" % key)
            kit.walk_condition(cond, visit)

        for eff in kit.node_effects(node):
            for key, value in (eff or {}).items():
                if key.startswith("_") or key in kit.CORE_EFFECTS:
                    if key in ("set", "clear"):
                        for f in kit.as_list(value):
                            if f not in flags:
                                report.error("flag", where(nid), "undeclared flag %r" % f)
                    if key == "give":
                        for name in value:
                            if name not in sets:
                                report.error("set", where(nid), "unknown set %r" % name)
                    if key == "reveal":
                        for name in kit.as_list(value):
                            if name not in places:
                                report.error("place", where(nid), "reveals unknown place %r" % name)
                    continue
                if key not in stats and key not in effects_vocab:
                    report.error("effect", where(nid), "unknown effect or stat %r" % key)

    # ---- names and placeholders ------------------------------------------------
    # A character is named in one place (its story file or the saga file); texts
    # say {id} or {id.short}, so a renamed character is renamed everywhere.
    allowed = set(story.get("placeholders", []))
    check_placeholders = "placeholders" in story       # a game that declares its placeholders
    literal = []
    for cid, info in characters.items():
        if info.get("short"):
            for field in kit.NAME_FIELDS:
                if info.get(field) and info[field][:1].isupper() and len(info[field]) > 2:
                    literal.append((info[field], cid, field))
    literal.sort(key=lambda item: -len(item[0]))
    for nid, node in nodes.items():
        for text in kit.texts_of(node):
            for head, field in re.findall(r"\{([a-z_][a-z0-9_]*)(?:\.([a-z_]+))?\}", text):
                ref = head + ("." + field if field else "")
                if head in characters:
                    if field and field not in characters[head]:
                        report.error("placeholder", where(nid), "{%s}: %s has no %s" % (ref, head, field))
                elif check_placeholders and ref not in allowed:
                    report.error("placeholder", where(nid), "{%s} is neither a character nor a game value" % ref)
            bare = re.sub(r"\{[^}]*\}", "", text)
            for name, cid, field in literal:
                if re.search(r"(?<![\w])" + re.escape(name) + r"(?![\w])", bare):
                    report.warn("name-in-text", where(nid), "writes %r; use {%s%s}" % (
                        name, cid, "" if field == "name" else "." + field))
                    break
    for cid, info in story["characters"].items():
        if not info.get("name") and not info.get("generated"):
            report.warn("character-name", "%s:character %s" % (gid, cid), "has no name (story file or saga file)")

    # ---- flags ----------------------------------------------------------------
    read, written = {}, {}
    for nid, node in nodes.items():
        for f in kit.flags_read(node):
            read.setdefault(f, []).append(nid)
        for f in kit.flags_set(node):
            written.setdefault(f, []).append(nid)
    for f, info in flags.items():
        by_game = info.get("set_by_game")
        if info.get("carries_to"):
            read.setdefault(f, []).append("the captain record (%s)" % ", ".join(info["carries_to"]))
        if f in read and f not in written and not by_game:
            report.warn("flag-never-set", "%s:flag %s" % (gid, f),
                        "read by %s but nothing sets it" % ", ".join(read[f]))
        if f not in read and (f in written or by_game):
            report.warn("flag-never-read", "%s:flag %s" % (gid, f), "set (%s) but no node reads it" % (
                ", ".join(written.get(f, [])) or "by the game"))
        if f not in read and f not in written and not by_game:
            report.warn("flag-unused", "%s:flag %s" % (gid, f), "declared, never set, never read")

    # ---- reachability (structural: stats are assumed earnable unless not produced) --
    reach = reachable(story)
    max_act = max([n.get("act", 0) for n in nodes.values() if n.get("kind") in ("chapter", "ending")] or [0])
    for nid, node in nodes.items():
        state = reach.get(nid)
        if node.get("status") == "unused":
            continue
        if state == "no":
            report.warn("unreachable", where(nid), "can never happen: " + reach.why.get(nid, "?"))
        elif state == "opaque":
            report.note("opaque", where(nid), "depends on game code the tools cannot read: " + reach.why.get(nid, ""))
    endings = [nid for nid, n in nodes.items() if n.get("kind") == "ending"]
    for nid in endings:
        if reach.get(nid) == "no":
            report.error("ending", where(nid), "this ending cannot be reached")
    if not any(n.get("start") for n in nodes.values()):
        report.error("start", gid, "no node is marked start")

    # ---- choices: the sides of a path choice exclude each other ----------------
    for cid, chooser in nodes.items():
        if not chooser.get("choose"):
            continue
        sides = set(kit.as_list(chooser.get("next")))
        for nid, node in nodes.items():
            needed = []
            kit.walk_condition(node.get("requires"),
                               lambda k, v, p: needed.extend(kit.as_list(v)) if k == "done" and "any" not in p
                               and "not" not in p else None)
            both = sorted(sides & set(needed))
            if len(both) > 1:
                report.error("choice", where(nid), "needs %s, but the player picks only one of them at %s" % (
                    " and ".join(both), cid))

    # ---- structure and content ---------------------------------------------
    for nid, node in nodes.items():
        kind = node.get("kind")
        if kind == "chapter" and not node.get("next"):
            report.warn("dead-end", where(nid), "chapter leads nowhere and is not an ending")
        if kind in ("beat", "encounter", "event") and not kit.text_of(node) and not node.get("choices") \
                and not node.get("next") and not node.get("handled_by") and node.get("status") != "unused":
            report.note("empty", where(nid), "has a name but no text, choice or follow-up")
        if node.get("status") == "unused":
            report.note("unused", where(nid), "exists but nothing starts it (%s)" % "; ".join(node.get("notes", [])))
        if node.get("repeat") is True and (kit.text_of(node) or node.get("choices")) and not node.get("chance"):
            report.note("repeats", where(nid), "shown every turn while its condition holds")
        cond_acts = []
        kit.walk_condition(node.get("requires"), lambda k, v, p: cond_acts.append(v) if k == "act_min" else None)
        if cond_acts and max(cond_acts) >= max_act and kind not in ("ending", "milestone"):
            report.note("late", where(nid), "only possible in the final act (act %d)" % max(cond_acts))
        for note in node.get("notes", []):
            if "not defined" in note:
                report.error("missing", where(nid), note)

    used_chars = set()
    for node in nodes.values():
        used_chars |= kit.characters_of(node)
    for cid in story["characters"]:
        if cid not in used_chars:
            report.note("character-unused", "%s:character %s" % (gid, cid), "declared, appears in no node")
    return reach


class Reach(dict):
    def __init__(self):
        dict.__init__(self)
        self.why = {}


def reachable(story):
    """Which nodes can ever happen, by structure alone.

    yes      some path makes it available
    opaque   available only if game code (a 'code' condition) allows it
    no       never: a missing link, an unset flag, a stat the game never produces ...
    """
    nodes = story["nodes"]
    stats = story["stats"]
    flags = story["flags"]
    places = story["places"]
    sets = story["sets"]
    result = Reach()
    max_act = max([n.get("act", 0) for n in nodes.values() if n.get("kind") in ("chapter", "ending")] or [0])

    entered_by = {}          # node -> nodes whose 'next' or choices lead to it
    for nid, node in nodes.items():
        for kind, target in kit.references(node):
            if kind in ("next", "start"):
                entered_by.setdefault(target, []).append(nid)

    obtainable = {name: set(info.get("members", [])) if info.get("obtainable", True) else set()
                  for name, info in sets.items()}
    gifts = {}
    for nid, node in nodes.items():
        for eff in kit.node_effects(node):
            for name, items in ((eff or {}).get("give") or {}).items():
                for item in kit.as_list(items):
                    gifts.setdefault((name, item), []).append(nid)

    def flag_ok(f, level):
        if flags.get(f, {}).get("set_by_game"):
            return "yes"
        best = "no"
        for nid, node in nodes.items():
            if f in kit.flags_set(node) and level.get(nid) in ("yes", "opaque"):
                if level[nid] == "yes":
                    return "yes"
                best = "opaque"
        return best

    def cond_level(cond, level):
        """yes / opaque / no for one condition, plus a reason."""
        verdict = ["yes", ""]

        def worse(v, why):
            order = {"yes": 0, "opaque": 1, "no": 2}
            if order[v] > order[verdict[0]]:
                verdict[0], verdict[1] = v, why

        def visit(key, want, path):
            negated = "not" in path
            in_any = "any" in path
            if negated or in_any:
                return                      # judged loosely: never blocks structurally
            if key == "since":              # structurally the same as having happened
                key, want = "done", list(want)
            if key == "code":
                worse("opaque", str(want)[:80])
            elif key in ("done", "done_any"):
                targets = kit.as_list(want)
                levels = [level.get(t, "no") if t in nodes else "no" for t in targets]
                if key == "done":
                    bad = [t for t, lv in zip(targets, levels) if lv != "yes"]
                    if any(level.get(t, "no") == "no" or t not in nodes for t in bad):
                        worse("no", "needs %s" % ", ".join(bad))
                    elif bad:
                        worse("opaque", "needs %s" % ", ".join(bad))
                else:
                    if "yes" not in levels:
                        worse("no" if "opaque" not in levels else "opaque", "needs one of %s" % ", ".join(targets))
            elif key == "flag":
                for f in kit.as_list(want):
                    lv = flag_ok(f, level)
                    if lv != "yes":
                        worse(lv, "flag %r is never set" % f if lv == "no" else "flag %r set only via code" % f)
            elif key == "act_min":
                if want > max_act:
                    worse("no", "act %s does not exist" % want)
            elif key in ("at", "at_type"):
                if not any(p in places for p in kit.as_list(want)):
                    worse("no", "place %s does not exist" % ", ".join(kit.as_list(want)))
            elif key == "has":
                for name, items in want.items():
                    for item in kit.as_list(items):
                        if item in obtainable.get(name, set()):
                            continue
                        lv = [level.get(g, "no") for g in gifts.get((name, item), [])]
                        if "yes" not in lv:
                            worse("opaque" if "opaque" in lv else "no", "%s %r can never be had" % (name, item))
            elif key == "chapter":
                if not any(c in nodes for c in kit.as_list(want)):
                    worse("no", "chapter %s does not exist" % ", ".join(kit.as_list(want)))
            elif key in ("turn_min", "turn_max", "act_max", "not_flag", "not_done", "visiting_captain",
                         "player_origin", "venue"):
                return
            elif key in stats and stats[key].get("produced") is False:
                worse("no", "the game never produces %r" % key)
        kit.walk_condition(cond, visit)
        return verdict

    level = {nid: "no" for nid in nodes}
    for _ in range(len(nodes) + 2):
        changed = False
        for nid, node in nodes.items():
            if node.get("status") == "unused":
                new, why = "no", "unused"
            else:
                new, why = cond_level(node.get("requires"), level)
                # stages and chapters are entered from somewhere; milestones need their chapter
                kind = node.get("kind")
                gate = None
                if node.get("in"):
                    gate = level.get(node["in"], "no")
                    if gate != "yes":
                        why = why or "its chapter %s cannot be reached" % node["in"]
                elif kind in ("chapter", "ending", "stage") and not node.get("start"):
                    sources = entered_by.get(nid, [])
                    lv = [level.get(s, "no") for s in sources]
                    gate = "yes" if "yes" in lv else ("opaque" if "opaque" in lv else "no")
                    if gate != "yes" and not why:
                        why = "nothing leads here" if not sources else "reached only from %s" % ", ".join(sources)
                if gate is not None:
                    order = {"yes": 0, "opaque": 1, "no": 2}
                    if order[gate] > order[new]:
                        new = gate
            if level[nid] != new:
                # only move upwards (no -> opaque -> yes) to reach a fixpoint
                order = {"no": 0, "opaque": 1, "yes": 2}
                if order[new] > order[level[nid]]:
                    level[nid] = new
                    changed = True
            result.why[nid] = why
        if not changed:
            break
    result.update(level)
    return result


def check_saga(saga, report):
    parts = [p["game"] for p in saga.get("parts", [])]
    stories = saga["stories"]
    order = {g: i for i, g in enumerate(parts)}
    reaches = {}
    for gid, story in stories.items():
        reaches[gid] = check_story(story, report, saga)

    # characters across the saga
    open_parts = {part.get("game"): part.get("open", False) for part in saga.get("parts", [])}
    appears = {}
    for gid, story in stories.items():
        for nid, node in story["nodes"].items():
            for who in kit.characters_of(node):
                appears.setdefault(who, set()).add(gid)
    for cid, info in saga.get("characters", {}).items():
        for entry in info.get("timeline", []):
            g = entry.get("game")
            if g not in order:
                report.error("saga-game", "saga:character %s" % cid, "timeline names unknown game %r" % g)
            elif g in stories and g not in appears.get(cid, set()):
                if open_parts.get(g):
                    report.note("timeline-pending", "saga:character %s" % cid,
                                "timeline places them in %s (still being written)" % g)
                else:
                    report.warn("timeline", "saga:character %s" % cid,
                                "timeline places them in %s, but no node there uses them" % g)
        for g in appears.get(cid, set()):
            if info.get("timeline") and g not in [e.get("game") for e in info["timeline"]]:
                report.warn("timeline", "saga:character %s" % cid, "appears in %s, which their timeline does not list" % g)

    # promises: made somewhere, paid in the same or a later part
    made, paid = {}, {}
    for gid, story in stories.items():
        for nid, node in story["nodes"].items():
            for p in kit.as_list(node.get("promises")):
                made.setdefault(p, []).append((gid, nid))
            for p in kit.as_list(node.get("pays")):
                paid.setdefault(p, []).append((gid, nid))
    declared = saga.get("promises", {})
    for p in set(made) | set(paid):
        if p not in declared:
            report.error("promise", "saga:promise %s" % p, "used by nodes but not declared in the saga")
    for p, info in declared.items():
        pay_by = info.get("pay_by")
        if p not in made:
            report.warn("promise", "saga:promise %s" % p, "declared, but no node makes it yet")
        if p in paid:
            early = [(g, n) for g, n in paid[p] for mg, mn in made.get(p, []) if order.get(g, 0) < order.get(mg, 0)]
            if early:
                report.warn("promise", "saga:promise %s" % p, "paid before it is made: %s" % early)
            continue
        if pay_by and pay_by not in stories:
            report.note("promise-pending", "saga:promise %s" % p, "to be paid in %s (not written yet)" % pay_by)
        elif pay_by and open_parts.get(pay_by):
            report.note("promise-pending", "saga:promise %s" % p, "to be paid in %s (still being written)" % pay_by)
        else:
            report.warn("promise-unpaid", "saga:promise %s" % p, "made but never paid")

    # carried flags: a flag a part marks for a later part should be read there, through
    # player_origin (the captain record that came in); pending while the later part is open
    for gid, story in stories.items():
        for f, info in story.get("flags", {}).items():
            for target in info.get("carries_to") or []:
                if target not in stories or target == gid:
                    continue
                read = set()
                for nid, node in stories[target]["nodes"].items():
                    for cond in kit.node_conditions(node):
                        def visit(key, want, path, read=read):
                            if key == "player_origin" and isinstance(want, dict) and want.get("flag"):
                                read.add(want["flag"])
                        kit.walk_condition(cond, visit)
                if f not in read:
                    if open_parts.get(target):
                        report.note("carried-pending", "%s:flag %s" % (gid, f), "for %s, not read there yet" % target)
                    else:
                        report.warn("carried-unread", "%s:flag %s" % (gid, f), "carried to %s, which never reads it" % target)

    # crossings: visiting captains must come from a part of the saga
    for gid, story in stories.items():
        for nid, node in story["nodes"].items():
            for cond in kit.node_conditions(node):
                def visit(key, want, path, gid=gid, nid=nid):
                    if key == "visiting_captain" and want.get("game") and want["game"] not in order:
                        report.error("crossing", "%s:%s" % (gid, nid), "captain from unknown game %r" % want["game"])
                    if key == "visiting_captain" and want.get("game") in order and \
                            order[want["game"]] == order.get(gid):
                        report.note("crossing", "%s:%s" % (gid, nid), "a captain from the same game (another playthrough)")
                kit.walk_condition(cond, visit)
    return reaches


def run(path):
    report = Report()
    with open(path, encoding="utf-8") as handle:
        fmt = json.load(handle).get("format")
    if fmt == kit.SAGA_FORMAT:
        saga = kit.load_saga(path)
        reaches = check_saga(saga, report)
    else:
        story = kit.load(path)
        reaches = {_game_id(story): check_story(story, report)}
    return report, reaches


def finding_key(item):
    return "%s|%s|%s" % (item["code"], item["where"], item["message"])


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    report, reaches = run(argv[1])
    baseline = None
    if "--baseline" in argv:
        bpath = argv[argv.index("--baseline") + 1]
        if "--write-baseline" in argv:
            keys = sorted(finding_key(i) for i in report.items if i["level"] in ("error", "warning"))
            with open(bpath, "w", encoding="utf-8") as handle:
                json.dump({"about": "Findings accepted for now; validate.py --baseline fails only on new ones.",
                           "accepted": keys}, handle, indent=1, ensure_ascii=False)
                handle.write("\n")
            print("wrote %s: %d accepted findings" % (bpath, len(keys)))
            return 0
        with open(bpath, encoding="utf-8") as handle:
            baseline = set(json.load(handle).get("accepted", []))
    if "--json" in argv:
        print(json.dumps({"items": report.items,
                          "reach": {g: dict(r) for g, r in reaches.items()},
                          "why": {g: r.why for g, r in reaches.items()}}, indent=1, ensure_ascii=False))
    else:
        for level in ("error", "warning", "note"):
            items = [i for i in report.items if i["level"] == level]
            if not items:
                continue
            print("%s (%d)" % (level.upper() + "S", len(items)))
            for i in sorted(items, key=lambda i: (i["code"], i["where"])):
                print("  %-18s %-44s %s" % (i["code"], i["where"], i["message"]))
            print()
        for g, r in reaches.items():
            counts = {}
            for v in r.values():
                counts[v] = counts.get(v, 0) + 1
            print("%s: %d nodes - can happen %d, depends on code %d, never %d" % (
                g, len(r), counts.get("yes", 0), counts.get("opaque", 0), counts.get("no", 0)))
        print("%d errors, %d warnings, %d notes" % (report.count("error"), report.count("warning"), report.count("note")))
    if baseline is not None:
        new = [i for i in report.items if i["level"] in ("error", "warning") and finding_key(i) not in baseline]
        gone = len(baseline - {finding_key(i) for i in report.items})
        print("baseline: %d new, %d fixed since the baseline" % (len(new), gone))
        for i in new:
            print("  NEW %-8s %-18s %-40s %s" % (i["level"], i["code"], i["where"], i["message"]))
        return 1 if any(i["level"] == "error" for i in new) else 0
    return 1 if report.count("error") else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
