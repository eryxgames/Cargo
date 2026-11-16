#!/usr/bin/env python3
"""Play every story scene the game plays on its own, with every choice, on a well-stocked
ship: no crashes, and no {name} left unfilled in what the player reads. Also checks special
cargo (story hooks 'stow' and 'unstow') and the enemies that wait for the story.
Usage: python3 tools/scenes.py cargo.py"""
import os, re, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from headless import load, new_game, quiet  # noqa: E402

cargo = load(sys.argv[1] if len(sys.argv) > 1 else "cargo.py")
data = cargo.story_data()
plays = cargo.StoryRuntime.PLAYS
FLAGS = ("convoy_friend", "aela_member", "nano_trusted", "hardtack_told", "deadstick_wing", "owes_serac",
         "fluencer_exposed", "ship_bugrat", "hovertank_aboard", "exoparts_aboard", "biomass_aboard",
         "met_rootstock", "rootstock_delivered", "big_run", "rootstock_family", "loaders_aboard",
         "harp_aboard", "concertina_aboard", "wirth_aboard", "concertina_pleased")
problems = played = 0
for nid, node in sorted(data["nodes"].items()):
    if node.get("kind") not in plays or node.get("handled_by") or node.get("status") == "unused":
        continue
    for pick in range(1, 1 + max(1, len(node.get("choices", [])))):
        random.seed(pick)
        g, io = new_game(cargo)
        g.ship.money = 500000
        g.ship.cargo.update(tech=100, agri=100, fuel=100, salt=50)
        g.ship.crew.extend(["loader", "steward", "mechanic", "gunner", "navigator", "broker"])
        g.ship.items.update({"probe": 1, "scanner": 1, "data_analyzer": 1, "advanced_radar": 1})
        for flag in FLAGS:
            g.story_manager.story_states[flag] = True
        io.feed([str(pick)] + [""] * 40)
        try:
            with quiet() as buf:
                g.story.play(nid)
            left = re.findall(r"\{[a-z_]+(?:\.[a-z]+)?\}", buf.getvalue())
            if left:
                problems += 1
                print("unfilled", nid, "choice", pick, left[:3])
            played += 1
        except Exception as e:  # report and go on: one broken scene should not hide the rest
            problems += 1
            print("CRASH", nid, "choice", pick, repr(e)[:200])

g, io = new_game(cargo)
room = g.ship.hold_room("tech")
with quiet() as buf:
    cargo.story_hook(g, "stow 150 hovertank as the legion's prototype hovertank")
if g.ship.hold_room("tech") != room - 150:
    problems += 1; print("FAIL stow does not take hold room")
if "the legion's prototype hovertank" not in buf.getvalue():
    problems += 1; print("FAIL loading does not name the special cargo")
io.feed([""] * 3)
with quiet() as buf:
    g.story.journal()
if "prototype hovertank (150 units" not in buf.getvalue():
    problems += 1; print("FAIL the journal does not list special cargo")
before = sum(g.ship.trade_profits.values()), g.ship.money
with quiet():
    cargo.story_hook(g, "profit 25000")
if (sum(g.ship.trade_profits.values()) - before[0], g.ship.money - before[1]) != (25000, 25000):
    problems += 1; print("FAIL contract profit is not paid as trade profit")
with quiet():
    cargo.story_hook(g, "unstow hovertank")
if g.ship.hold_room("tech") != room:
    problems += 1; print("FAIL unstow does not free hold room")
for enemy in ("cargolytes", "rootstock"):
    if any(g.pick_enemy(4) == enemy for _ in range(300)):
        problems += 1; print("FAIL", enemy, "turn up before the story introduces them")
    for move in ("1", "2", "3", "4", ""):
        io.feed([move] + [""] * 5)
        with quiet():
            out = g.encounter(enemy)
        if out not in ("victory", "defeat", "escaped", "paid", "talked"):
            problems += 1; print("FAIL", enemy, "fight ended", out)
print("%d scenes and choices played, %d problems" % (played, problems))
sys.exit(1 if problems else 0)
