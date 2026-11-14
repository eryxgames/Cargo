"""Take every kind of quest the game hands out and finish it the way a player would.

    python tools/quests.py cargo.py

For each quest: it must not be done the moment it is taken (quests count from
then on), it must be done after the work it asks for, the rewards must be paid,
and a delivery must leave the ship.  Each failure is listed; exit status 1 if any.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from headless import load, new_game, quiet  # noqa: E402


def fresh(cargo):
    game, io = new_game(cargo)
    game.ship.money = 50000
    game.story_manager.plot_points = 500
    game.ship.passenger_reputation = 100
    for name in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon"):
        if name not in game.known_locations:
            game.known_locations.append(name)
    for loc in game.locations:                       # history the quest must not count
        if loc.location_type == "Planet":
            game.discovered_locations.add(loc.name)
    game.ship.combat_victories["total"] = 12
    game.ship.combat_victories["pirate"] = 9
    game.ship.cargo["salt"] = 400
    game.trades_completed = 30
    return game, io


def do_the_work(cargo, game, quest):
    """What a player would do for this quest (returns a note if it cannot)."""
    t, r, ship = quest.quest_type, quest.requirements, game.ship
    counted = quest.counted(game)
    if counted:
        target = counted[1]
    if t == "combat":
        kind = r.get("enemy_type", "total")
        ship.combat_victories[kind] = ship.combat_victories.get(kind, 0) + target
        ship.combat_victories["total"] += target if kind != "total" else 0
    elif t == "patrol":
        game.turn += target
    elif t == "research":
        for _ in range(3):
            ship.research_points += target // 3 + 1
            game.quest_system.counters()
            ship.research_points -= 5                    # spending does not undo what was gained
            game.quest_system.counters()
    elif t == "mining":
        ship.cargo[r["resource_type"]] += target
    elif t == "exploration":
        kind = r.get("location_type")
        pool = [l for g in game.hidden_locations.values() for l in g] + list(game.locations)
        new = [l for l in pool if l.name not in game.discovered_locations
               and (kind in (None, "any") or l.location_type == kind)]
        for loc in new[:target]:
            game.discovered_locations.add(loc.name)
    elif t == "rescue":
        for _ in range(target):
            game.quest_system.check_event_requirements({"type": "disaster"})
    elif t == "trade":
        game.trades_completed += target
        ship.trade_profits["tech"] = ship.trade_profits.get("tech", 0) + r.get("min_profit", 0)
    elif t in ("delivery", "mining_contract"):
        item = r.get("commodity") or r.get("resource")
        ship.cargo[item] += r["amount"]
    elif t == "item_delivery":
        ship.acquire_item(r["item"])
    elif t == "character_delivery":
        waiting = game.port_system.waiting_passengers.get(game.current_location.name, [])
        passenger = next((p for p in waiting if p.name == r["character"]), None)
        if passenger is None:
            return "the passenger is not waiting at the port"
        waiting.remove(passenger)
        module = cargo.PassengerModule("Test cabin", 4, 3, 0)
        module.passengers.append(passenger)
        ship.passenger_modules.append(module)
    if quest.destination:
        game.current_location = next(l for l in game.locations if l.name == quest.destination)
    if t.startswith("unlock_"):
        game.quest_system.update_from_travel({"destination": game.current_location.name})
    return None


def quests_to_try(cargo):
    """(label, maker): every template the game can hand out."""
    makers = []
    for kind in ("mining", "combat", "research", "story"):
        for i in range(4):
            makers.append(("generate_quest %s" % kind,
                           lambda g, kind=kind, i=i: (random.seed(i), g.quest_system.generate_quest(kind, 1))[1]))
    events = [({"type": "combat", "name": "Pirate attack"}, {"outcome": "victory"}),
              ({"type": "trade", "name": "Market crash!"}, {"outcome": "ok"}),
              ({"type": "exploration", "name": "Ancient artifact"}, {"outcome": "ok"}),
              ({"type": "disaster", "name": "Solar storm"}, {"outcome": "survived"})]
    for event, outcome in events:
        for i in range(3):
            makers.append(("event quest after %s" % event["name"],
                           lambda g, e=event, o=outcome, i=i: (random.seed(i), g.generate_event_quest(e, o))[1]))
    for i in range(40):
        makers.append(("cantina quest", lambda g, i=i: (random.seed(i), g.quest_system.generate_cantina_quest())[1]))
    for kind in ("AsteroidBase", "DeepSpaceOutpost", "ResearchColony"):
        makers.append(("unlock %s" % kind, lambda g, kind=kind: unlock_quest(g, kind)))
    return makers


def unlock_quest(game, kind):
    game.location_manager.trigger_location_unlock_quest(kind)
    return next(q for q in game.quest_system.active_quests if q.quest_type == "unlock_" + kind)


def main(argv):
    cargo = load(argv[1] if len(argv) > 1 else "cargo.py")
    failures, tried = [], {}
    for label, maker in quests_to_try(cargo):
        game, io = fresh(cargo)
        with quiet():
            quest = maker(game)
            if quest is None:
                continue
            if quest not in game.quest_system.active_quests:
                game.quest_system.add_quest(quest)
        name = "%s: %s [%s]" % (label, quest.name, quest.quest_type)
        tried[name] = tried.get(name, 0) + 1
        if tried[name] > 1:
            continue
        with quiet():
            game.quest_system.check_active_quests()
        if quest.completed:
            failures.append("%s: done the moment it was taken" % name)
            continue
        money = game.ship.money
        with quiet():
            note = do_the_work(cargo, game, quest)
        if note:
            failures.append("%s: %s" % (name, note))
            continue
        with quiet():
            game.quest_system.check_active_quests()
        if not quest.completed:
            failures.append("%s: not done after the work (%s)" % (name, quest.progress_text(game)))
            continue
        if game.ship.money < money + quest.reward_money:
            failures.append("%s: reward not paid" % name)
        r = quest.requirements
        if quest.quest_type in ("delivery", "mining_contract"):
            item = r.get("commodity") or r.get("resource")
            if game.ship.cargo[item] >= r["amount"] and item != "salt":
                failures.append("%s: the cargo stayed aboard" % name)
        if quest.quest_type == "item_delivery" and game.ship.items.get(r["item"]):
            failures.append("%s: the item stayed aboard" % name)
        if quest.quest_type == "character_delivery" and quest.quest_passenger(game):
            failures.append("%s: the passenger stayed aboard" % name)
    for name in sorted(tried):
        print("tried:", name)
    for failure in failures:
        print("FAIL:", failure)
    print("%d kinds of quest tried, %d failures" % (len(tried), len(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
