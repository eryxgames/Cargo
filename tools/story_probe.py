"""Drive the real story code along each path by setting stats directly.

This does not prove the stats are earnable in play (the bot does that); it proves
the chapter machinery itself can get from ch1 to each ending without crashing or stalling.
usage: story_probe.py /path/to/cargo.py
"""
import os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from headless import load, new_game, quiet

path = sys.argv[1]
cargo = load(path)

PATHS = {
    "trade":            ["ch1", "ch2a", "ch3a", "ending_trade"],
    "combat":           ["ch1", "ch2b", "ch3b", "ending_combat"],
    "discovery (2a)":   ["ch1", "ch2a", "ch3c", "ending_discovery"],
    "discovery (2b)":   ["ch1", "ch2b", "ch3c", "ending_discovery"],
}


def satisfy(game, reqs, log):
    """Force stats so that `reqs` hold, using the same fields the checker reads."""
    s = game.ship
    for k, v in reqs.items():
        if k == "plot_points":
            game.story_manager.plot_points = max(game.story_manager.plot_points, v)
        elif k == "money":
            s.money = max(s.money, v)
        elif k == "research_points":
            s.research_points = max(s.research_points, v)
        elif k == "combat_victories":
            if isinstance(v, dict):
                for t, n in v.items():
                    s.combat_victories[t] = max(s.combat_victories.get(t, 0), n)
            else:
                s.combat_victories["total"] = max(s.combat_victories["total"], v)
        elif k == "combat_rating":
            while s.attack + s.defense + s.speed < v:
                s.attack += 1
        elif k == "trades_completed":
            game.trades_completed = max(game.trades_completed, v)
        elif k == "trade_profit":
            cur = sum(s.trade_profits.values())
            if cur < v:
                s.trade_profits["tech"] = s.trade_profits.get("tech", 0) + (v - cur)
        elif k == "passengers_transported":
            game.reputation_manager.total_passengers = max(game.reputation_manager.total_passengers, v)
        elif k == "passenger_reputation":
            s.passenger_reputation = max(s.passenger_reputation, v)
        elif k == "buildings_built":
            for b, n in v.items():
                have = sum(1 for l in game.locations for x in l.buildings if x == b)
                locs = list(game.locations)
                i = 0
                while have < n:
                    locs[i % len(locs)].buildings.append(b)
                    have += 1
                    i += 1
        elif k == "research_unlocked":
            for t in v:
                if t not in game.research.unlocked_options:
                    if isinstance(game.research.unlocked_options, set):
                        game.research.unlocked_options.add(t)
                    else:
                        game.research.unlocked_options.append(t)
        elif k == "locations_discovered":
            for t, n in v.items():
                # unlock hidden locations of that type the way the game does, then "visit" them
                for group in list(game.hidden_locations.values()):
                    for l in group:
                        if l.location_type == t and l not in game.locations:
                            game.locations.append(l)
                pool = [l for l in game.locations if l.location_type == t]
                for l in pool[:n]:
                    game.discovered_locations.add(l.name)
                if game.count_discovered(t) < n:
                    log.append("  ! only %d %s locations exist, %d needed" % (game.count_discovered(t), t, n))
        elif k in ("chapters_completed", "chapters_completed_any"):
            pass
        else:
            log.append("  ! probe does not know how to satisfy %r" % k)


STORY_KEYS = {"plot_points": "plot_points", "trades_completed": "trades_completed", "trade_profit": "trade_profit",
              "research_points": "research_points", "combat_victories": "combat_victories",
              "passenger_reputation": "passenger_reputation", "combat_rating": "combat_rating"}


def satisfy_story(game, cid, log):
    """A chapter whose requirements the story file repairs: satisfy those instead."""
    cond = game.story.condition_for(cid)
    if cond is None:
        return
    reqs = {}
    for k, v in cond.items():
        if k in STORY_KEYS:
            reqs[STORY_KEYS[k]] = v
        elif k in ("done", "done_any"):
            for n in ([v] if isinstance(v, str) else v)[:1 if k == "done_any" else None]:
                if n not in game.story_manager.chapters:     # a story scene: count it as played
                    game.story.done.setdefault(n, game.turn)
        elif k not in ("act_min", "act_max"):
            log.append("  ! probe does not know how to satisfy story condition %r" % k)
    satisfy(game, reqs, log)


def tick(game):
    game.story_manager.check_milestone_progress()
    game.story_manager.check_chapter_progress()
    if hasattr(game, 'force_check_chapter_progression'):
        game.force_check_chapter_progression()


results = {}
for name, route in PATHS.items():
    log = []
    game, io = new_game(cargo)
    sm = game.story_manager
    ok = True
    ended = []
    orig_end = sm.handle_game_ending
    def _end(orig=orig_end, ended=ended, sm=sm):
        ended.append(sm.current_chapter)
        orig()
    sm.handle_game_ending = _end
    try:
        for i, ch in enumerate(route):
            if sm.current_chapter != ch:
                log.append("  ! expected to be in %s, game is in %s" % (ch, sm.current_chapter))
                ok = False
                break
            chapter = sm.chapters[ch]
            for m in chapter.milestones.values():
                satisfy(game, m.requirements, log)
            satisfy(game, chapter.requirements, log)
            satisfy_story(game, ch, log)
            nxt = route[i + 1] if i + 1 < len(route) else None
            if nxt:
                satisfy(game, sm.chapters[nxt].requirements, log)
                satisfy_story(game, nxt, log)
                # answer the path choice: position of nxt among the chapter's options
                opts = chapter.next_chapters
                io.default = "1"   # only the wanted follow-up is open in this probe
            prompts_before = len(io.asked)
            with quiet() as buf:
                for _ in range(4):
                    tick(game)
            out = buf.getvalue()
            n_choice = sum(1 for p in io.asked[prompts_before:] if "Choose your path" in p)
            undone = [m.id for m in chapter.milestones.values() if not m.completed]
            log.append("  %s: completed=%s milestones_open=%s choice_prompts=%d -> now in %s" % (
                ch, chapter.completed, undone, n_choice, sm.current_chapter))
            for line in out.splitlines():
                if "Not Met" in line or "Cannot start" in line or "Warning" in line:
                    log.append("     game said: " + line.strip())
                    break
        if ok:
            ok = bool(ended) and ended[-1] == route[-1] and sm.is_story_completed()
            log.append("  ending shown: %s (times: %d), is_story_completed=%s" % (
                ended[-1] if ended else None, len(ended), sm.is_story_completed()))
    except Exception:
        ok = False
        tb = traceback.format_exc().strip().splitlines()
        log.append("  ! EXCEPTION " + tb[-1])
        log += ["    " + l for l in tb[-5:-1]]
    results[name] = ok
    print("%s: %s" % (name, "REACHED" if ok else "BLOCKED"))
    print("\n".join(log))
print()
print("summary:", results)
