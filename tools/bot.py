"""Playthrough bot: plays cargo.py through its real commands until an ending.

It reads the game's state to decide (like a player reading the screen) but acts
only by answering the game's own prompts, so every step is something a player
can type.

usage: bot.py cargo.py <path: trade|combat|discovery> <seed> [max_turns] [--verbose]
"""
import sys, os, io, re, json, random, shutil, traceback, tempfile, builtins, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import headless

path, goal, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
# --voyage=short|standard|long (default standard)
VOYAGE = {"short": "1", "standard": "2", "long": "3"}.get(
    next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--voyage=")), "standard"), "2")
max_turns = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 3000
verbose = "--verbose" in sys.argv
save_every = 0
trace_path = None
for a in sys.argv:
    if a.startswith("--save-every="):
        save_every = int(a.split("=")[1])
    if a.startswith("--trace="):
        trace_path = a.split("=", 1)[1]
trace_file = open(trace_path, "w", encoding="utf-8") if trace_path else None
ledger_on = "--ledger" in sys.argv
LEDGER = collections.defaultdict(lambda: collections.defaultdict(float))


def install_ledger(cargo):
    """Record every change to money, plot points and research points, by the
    function that made it (for tools/economy.py)."""
    def tracked(cls, attr, book):
        store = "_ledger_" + attr

        def get(self):
            return self.__dict__.get(store, 0)

        def put(self, value):
            old = self.__dict__.get(store)
            self.__dict__[store] = value
            if old is None or not isinstance(value, (int, float)):
                return
            delta = value - old
            if delta:
                frame = sys._getframe(1)
                while frame and frame.f_code.co_name in ("put", "<lambda>"):
                    frame = frame.f_back
                who = getattr(frame.f_code, "co_qualname", frame.f_code.co_name) if frame else "?"
                LEDGER[book + ("+" if delta > 0 else "-")][who] += delta
        setattr(cls, attr, property(get, put))
    tracked(cargo.Ship, "money", "money")
    tracked(cargo.Ship, "research_points", "rp")
    tracked(cargo.StoryManager, "plot_points", "plot_points")
traced_turn = [-1]


def write_trace(g, final=False):
    """One line per turn: the story kit's view of the game, and the game's own verdicts."""
    if not trace_file or g is None or (g.turn == traced_turn[0] and not final):
        return
    import cargo_story
    traced_turn[0] = g.turn
    snap = cargo_story.snapshot(g)
    snap["verdicts"] = cargo_story.game_verdicts(g)
    moment = cargo_story.story_moment(g)
    if moment:
        snap["moment"] = moment
    snap["style"] = goal
    snap["seed"] = seed
    if final:
        snap["final"] = True
        snap["ending"] = getattr(g, "ending_reached", None)
    trace_file.write(json.dumps(snap, ensure_ascii=False, separators=(",", ":")) + "\n")

home = tempfile.mkdtemp(prefix="cargo-bot-")
os.environ["CARGO_HOME"] = home
size = os.terminal_size((80, 40))
shutil.get_terminal_size = lambda fallback=(80, 24): size
cargo = headless.load(path)
if ledger_on:
    install_ledger(cargo)
headless.patch(cargo, headless.IO())
random.seed(seed)
rng = random.Random(seed * 7 + 1)

PATH_CHOICE = {   # which follow-up chapter to pick, by goal
    "trade": ["ch2a", "ch3a", "ending_trade"],
    "combat": ["ch2b", "ch3b", "ending_combat"],
    "discovery": ["ch2a", "ch3c", "ending_discovery"],
    "discovery2": ["ch2b", "ch3c", "ending_discovery"],
}[goal]


class Done(Exception):
    pass


class Bot:
    def __init__(self):
        self.game = None
        self.ctx = None            # (prompt, options) while validate_input is asking
        self.story_choices = 0     # choices made in story scenes
        self.qty = False
        self.turn_seen = -1
        self.flags = set()
        self.item = None
        self.upgrade = None
        self.building = None
        self.research = None
        self.dest = None
        self.cost = collections.defaultdict(float)   # average price paid per item
        self.sell_at = {}
        self.unknown = collections.Counter()
        self.inputs = 0
        self.stall = 0
        self.last_progress = (0, None)
        self.log = []
        self.pax_dest = None
        self.port_step = None
        self.loads = 0
        self.reload_step = None
        self.reload_turn = -1

    # ---- helpers -----------------------------------------------------
    def need(self):
        """Open requirement keys of the current chapter and of the wanted next chapter."""
        g = self.game
        sm = g.story_manager
        ch = sm.chapters[sm.current_chapter]
        reqs = []
        for m in ch.milestones.values():
            if not m.completed:
                reqs.append(m.requirements)
        reqs.append(ch.requirements)
        for nid in ch.next_chapters:
            if nid in PATH_CHOICE:
                reqs.append(sm.chapters[nid].requirements)
        out = {}
        for r in reqs:
            for k, v in r.items():
                if not cargo.MilestoneRequirements._check_single_requirement(k, v, g):
                    out.setdefault(k, v)
        return out

    def prices(self, loc, item):
        if not loc.can_trade(item):
            return None
        if item in ("salt", "fuel") and not loc.trades_bulk(item):
            return None
        p = loc.market.get(item, 0)
        return p if p and p > 0 else None

    def best_trade(self):
        g = self.game
        here = g.current_location
        best = None
        for item in ("tech", "agri", "salt", "fuel"):
            buy = self.prices(here, item)
            if not buy:
                continue
            if g.ship.hold_room(item) <= 0:
                continue
            for loc in g.locations:
                if loc is here or loc.name not in g.known_locations:
                    continue
                sell = self.prices(loc, item)
                if not sell:
                    continue
                load = min(g.ship.hold_room(item), 400)       # a full load moves both prices
                margin = loc.trade_price(item, load, True) * 0.92 - here.trade_price(item, load, False) * 1.08
                if margin > 0 and (best is None or margin / buy > best[0]):
                    best = (margin / buy, item, loc.name)
        return best

    def best_sale_elsewhere(self, item):
        g = self.game
        best = None
        for loc in g.locations:
            if loc is g.current_location:
                continue
            p = self.prices(loc, item)
            if p and (best is None or p > best[0]):
                best = (p, loc.name)
        return best

    # ---- main menu ---------------------------------------------------
    def main_action(self, options):
        g = self.game
        ship = g.ship
        here = g.current_location
        if g.turn != self.turn_seen:
            self.turn_seen = g.turn
            self.flags = set()
        need = self.need()

        # every so often: save under a name, then load that save and play on from it
        if self.reload_step == "load" and "load" in options:
            self.reload_step = None
            return "load"
        if save_every and g.turn and g.turn % save_every == 0 and g.turn != self.reload_turn and "save" in options:
            self.reload_turn = g.turn
            self.reload_step = "load"
            return "save"

        if "repair" in options and ship.damage >= 20 and "repair" not in self.flags:
            self.flags.add("repair")
            if ship.money >= ship.damage * 10:
                return "r"

        # sell what we carry when this is the planned market or a profitable one
        for item in ("tech", "agri", "salt", "fuel"):
            if ship.cargo[item] > 0 and ("sell", item) not in self.flags:
                price = self.prices(here, item)
                if price is None:
                    continue
                planned = self.sell_at.get(item) == here.name
                better = self.best_sale_elsewhere(item)
                # what the goods really cost (load size and tax included), and what selling them
                # all here would really bring, since a big load moves the price
                held = ship.cargo[item]
                cost = ship.__dict__.get("cost_basis", {}).get(item, 0) / held if held else 0
                tax = ship.trade_tax(here.calculate_tax_rate(g.rank, price))
                price = here.trade_price(item, held, selling=True) * (1 - tax)
                bought_here = self.__dict__.setdefault("bought_at", {}).get(item) == here.name
                stale = better is None or g.turn - self.__dict__.setdefault("bought_turn", {}).get(item, g.turn) > 12
                held_for = g.turn - self.__dict__.setdefault("bought_turn", {}).get(item, g.turn)
                if (price >= cost * 1.05 and not bought_here) or (planned and price >= cost) \
                        or (stale and price >= cost * 0.8) or held_for > 25:      # cut the loss
                    self.flags.add(("sell", item))
                    self.item = item
                    return "s"

        # passengers
        if "port" in options and "port" not in self.flags and goal in ("trade", "discovery") and \
                ("passengers_transported" in need or "passenger_reputation" in need or
                 any(m.passengers for m in getattr(ship, "passenger_modules", []))):
            self.flags.add("port")
            self.port_step = "start"
            return "p"

        # stock markets
        want_sm = need.get("buildings_built", {}).get("stockmarket") if isinstance(need.get("buildings_built"), dict) else None
        if want_sm and "build" in options and "build" not in self.flags and "stockmarket" not in here.buildings:
            cost = 5000 * (here.buildings.count("stockmarket") + 1)
            if ship.money >= cost * 2:
                self.flags.add("build")
                self.building = "stockmarket"
                return "bl"
        want_ng = need.get("buildings_built", {}).get("Neuroengineering Guild") if isinstance(need.get("buildings_built"), dict) else None
        if want_ng and "build" in options and "build" not in self.flags:
            if ship.money >= 7000 * (here.buildings.count("Neuroengineering Guild") + 1) * 2:
                self.flags.add("build")
                self.building = "neuroengineering"
                return "bl"

        # a mine, when the story needs Asteroid Bases and they are not open yet
        wanted_locs = need.get("locations_discovered")
        if isinstance(wanted_locs, dict) and "AsteroidBase" in wanted_locs and \
                "AsteroidBase" not in g.unlocked_location_types and \
                not any(l.mining_platforms for l in g.locations):
            if here.mineral_deposits:
                if "mine" in options and "mine" not in self.flags and ship.money >= 10000:
                    self.flags.add("mine")
                    return "m"
            elif "action" in options and "geoscan" not in self.flags and ship.research_points >= 75:
                self.flags.add("geoscan")
                self.research = "geoscan"
                return "a"

        # research
        want_res = [r for r in need.get("research_unlocked", []) if r not in g.research.unlocked_options]
        if goal.startswith("discovery") or want_res:
            todo = want_res or [r for r in g.research.research_costs if r not in g.research.unlocked_options]
            todo = [r for r in todo if ship.research_points >= g.research.research_costs.get(r, 10 ** 9)]
            if todo and "action" in options and "research" not in self.flags:
                self.flags.add("research")
                self.research = todo[0]
                return "a"

        # a heavier hull at a planet shipyard, once the money is there (fighters and explorers first)
        if "upgrade" in options and "upgrade" not in self.flags and isinstance(here, cargo.Planet) \
                and ship.hull + 1 < len(ship.HULLS):
            price = ship.HULLS[ship.hull + 1]["price"]
            if ship.money > price * (2 if goal in ("combat", "discovery", "discovery2") else 4):
                self.flags.add("upgrade")
                self.upgrade = "hull"
                return "u"

        # ship upgrades: attack decides every fight (attack must exceed the enemy's defence,
        # which goes up to 6), defence only reduces damage
        if "upgrade" in options and "upgrade" not in self.flags:
            cap = 12 if (goal == "combat" or "combat_rating" in need) else 7
            order = []
            if ship.attack < 3:
                order = [("attack", 1.15)]
            elif ship.defense < 3:
                order = [("defense", 1.5)]
            elif ship.attack < 7:
                order = [("attack", 1.6), ("defense", 4)]
            else:
                order = [("defense", 3), ("speed", 4), ("attack", 4)]
            for prop, reserve in order:
                stat = getattr(ship, prop)
                if stat < cap and ship.money >= ship.upgrade_costs[prop] * reserve:
                    self.flags.add("upgrade")
                    self.upgrade = prop
                    return "u"

        # a fighter takes bounties two days in three (a hunt uses the turn)
        fighter = goal == "combat" or "combat_victories" in need
        if fighter and "hunt" in options and "hunt" not in self.flags and ship.damage < 40 and g.turn % 3:
            self.flags.add("hunt")
            return "hu"

        # every fifth turn a look in the shop for gear that suits the captain's road
        if "shop" in options and "shop" not in self.flags and g.turn % 5 == 0 and ship.money > 20000:
            self.flags.add("shop")
            return "sh"

        # idle money buys Hansa bonds, which lower the convoy dues
        if "hansa" in options and "hansa" not in self.flags and ship.money > 15 * g.bond_price() \
                and getattr(g, "hansa_bonds", 0) < 8:
            self.flags.add("hansa")
            return "ha"

        # now and then a drink in the cantina: people, rumours, crew for hire
        if "cantina" in options and "cantina" not in self.flags and g.turn % 4 == 0:
            self.flags.add("cantina")
            return "c"

        # buy for the best route and go
        if "buy" not in self.flags:
            self.flags.add("buy")
            trade = self.best_trade()
            if trade and ship.money >= 50:
                _, item, dest = trade
                self.item = item
                self.dest = dest
                self.sell_at[item] = dest
                self.buy_price = self.prices(here, item)
                held = ship.cargo[item]
                self.__dict__.setdefault("bought_turn", {})[item] = g.turn
                self.__dict__.setdefault("bought_at", {})[item] = here.name
                self.cost[item] = self.buy_price if not held else (self.cost[item] or self.buy_price)
                return "b"

        if "travel" not in self.flags:
            self.flags.add("travel")
            dest = None
            # places the story asks us to find come first
            wanted = need.get("locations_discovered")
            if isinstance(wanted, dict):
                for loc in g.locations:
                    if loc.location_type in wanted and loc.name not in g.discovered_locations and loc is not here \
                            and g.count_discovered(loc.location_type) < wanted[loc.location_type]:
                        dest = loc.name
                        break
            # then a passenger destination, then unexplored places, then the trade plan
            if dest is None and self.pax_dest and self.pax_dest != here.name:
                dest = self.pax_dest
            # a trader who only shuttles between two docks never sees the rest of the map
            unseen = [l.name for l in g.locations if l.name not in g.known_locations]
            if dest is None and unseen and (len(g.known_locations) < 5 or g.turn % 6 == 0):
                dest = rng.choice(unseen)
            if dest is None:
                carried = [i for i in ship.cargo if ship.cargo[i] > 0 and self.sell_at.get(i) and self.sell_at[i] != here.name]
                if carried:
                    dest = self.sell_at[carried[0]]
            if dest is None:
                unknown = [l.name for l in g.locations if l.name not in g.known_locations]
                if unknown:
                    dest = rng.choice(unknown)
            if dest is None and self.dest and self.dest != here.name:
                dest = self.dest
            if dest is None:
                others = [l.name for l in g.locations if l is not here]
                dest = rng.choice(others) if others else None
            if dest:
                self.travel_to = dest
                return "t"
        return "e"

    # ---- answering prompts ---------------------------------------------
    def answer(self, tail):
        g = self.game
        self.inputs += 1
        if self.ctx is not None:
            prompt, options = self.ctx
            self.ctx = None
            options = list(options)
            p = prompt.lower()
            if "end" in options and "buy" in options:
                return self.main_action(options)
            if p.startswith(("buy which", "sell which")):
                return self.item
            if "property to upgrade" in p:
                return self.upgrade
            if "overhaul the hull" in p:
                return "yes"
            if "building type" in p:
                return self.building
            if "choose your path" in p:
                sm = g.story_manager
                ch = sm.chapters[sm.current_chapter]
                avail = ch.get_next_chapters(g)
                for i, c in enumerate(avail, 1):
                    if c.id in PATH_CHOICE:
                        return str(i)
                return ""          # wait for the wanted path to open
            if "do you want to resign" in p or "are you sure" in p or "play again" in p:
                return "no"
            if "choose action type" in p:           # research/actions menu
                if self.research == "geoscan":
                    self.research = None
                    return "geoscan"
                if self.research:
                    return "research"
                return "back"
            if "mining options" in p:
                return "build"
            if "choose deposit type" in p:
                return options[0]
            if "choose research option" in p:
                r, self.research = self.research, None
                return r if r in options else ""
            if "modules" in options and "board" in options:      # port menu
                return self.port_action()
            if "module number to buy" in p:
                if self.port_step == "buy_module":
                    self.port_step = "bought"
                    ids = [o for o in options if o != "back"]
                    mods = g.port_system.available_modules
                    afford = [i for i in ids if mods[i]["cost"] <= g.ship.money * 0.5]
                    if afford:
                        return min(afford, key=lambda i: mods[i]["cost"])
                return "back"
            if p.startswith("hansa - choose"):        # the Hansa terminal: a bond when money is idle
                if g.ship.money > 15 * g.bond_price() and getattr(g, "hansa_bonds", 0) < 8:
                    return "b"
                return ""
            if p.startswith("your move"):             # a fight, a situation or the bounty board
                return self.move(options)
            if p.startswith("your choice"):           # a story scene's choice
                self.story_choices += 1
                return random.choice(options) if options else ""
            if "choose action (1/2/3)" in p or "choose action" in p or "your response" in p:
                self.unknown[("choice", tuple(options)[:6])] += 1
                return options[0] if options else ""
            if "0 to leave" in p:
                return "0"
            if "choose item to buy" in p:
                wanted = {"trade": ["quantum_compressor", "cargo_extender", "containment_field", "stasis_vault",
                                    "auto_loader", "cargo_scanner", "shield", "patcher"],
                          "combat": ["combat_drone", "turrets", "shield", "shield_booster", "mining_laser",
                                     "advanced_radar", "patcher", "neutron_shield", "warp_core", "emergency_warp"]}.get(
                    goal, ["research_module", "data_analyzer", "quantum_scanner", "probe", "scanner", "shield",
                           "cargo_extender", "patcher"])
                prices = dict((name, data["price"]) for name, data in g.shop.current_turn_items)
                for name in wanted:
                    if name in options and not g.ship.items.get(name) and prices.get(name, 10 ** 9) * 4 < g.ship.money:
                        return name
                return "none"
            if "none" in options:
                return "none"
            if "back" in options:
                return "back"
            self.unknown[("prompt", prompt[:50])] += 1
            return ""
        if self.qty:
            asked, self.qty = str(self.qty).lower(), False
            if "research points to buy" in asked:      # a researcher selling research for credits
                if goal.startswith("discovery") and g.ship.money > 50000 and "research_points" in self.need():
                    return "half"
                return ""
            return "max"
        t = tail.lower()
        if "save as" in t:
            return "botsave"
        if "type a number to load it" in t:
            return "1"
        if "choose a location to travel to" in t or "enter location name" in t or "enter the number or name" in t:
            return self.travel_to
        if "select passengers" in t:
            if self.port_step == "board":
                self.port_step = "boarding"
                return "a"
            return ""
        if "choose destination number" in t:
            loc = g.current_location.name
            waiting = g.port_system.waiting_passengers.get(loc, [])
            dests = sorted(set(p.destination for p in waiting))
            if not dests:
                return "0"
            counts = [sum(1 for p in waiting if p.destination == d) for d in dests]
            i = max(range(len(dests)), key=lambda k: counts[k])
            self.pax_dest = dests[i]
            return str(i + 1)
        if "choose module number" in t:
            return "a"
        if "press enter" in t:
            return ""
        self.unknown[("raw", t.strip().splitlines()[-1][:50] if t.strip() else "")] += 1
        return ""

    def move(self, numbers):
        """Read the options on screen (game.move_options) and pick one like a sensible captain."""
        g = self.game
        shown = list(getattr(g, "move_options", None) or [])
        if not shown:
            return numbers[0] if numbers else ""
        keys = [k for k, _ in shown]
        fighter = goal == "combat" or "combat_victories" in self.need()
        if "leave" in keys:                                  # the bounty board
            best = None
            for i, key in enumerate(keys):
                if key == "leave":
                    continue
                label = shown[i][1]
                if "easy" in label or "good odds" in label:
                    best = i                                 # the hardest target with good odds
            return str((best if best is not None and fighter else keys.index("leave")) + 1)
        if "fight" in keys:                                  # a fight
            found = re.search(r"threat (\d)", getattr(g, "move_title", "") or "")
            power = int(found.group(1)) if found else 3
            best_key, best_chance = "fight", g.fight_chance(power)
            for key in keys:
                if key.startswith("trick:"):
                    chance = g.fight_chance(power, cargo.FIGHT_TRICKS[key[6:]][1]["edge"])
                    if chance > best_chance:
                        best_key, best_chance = key, chance
                if key.startswith("ally:"):
                    chance = g.fight_chance(power, g.ALLIES[key[5:]][2])
                    if chance > best_chance:
                        best_key, best_chance = key, chance
            for key in ("mraz", "pilgrims", "lauritz"):          # an old favour ends it peacefully
                if key in keys and not fighter:
                    return str(keys.index(key) + 1)
            if best_chance >= (0.4 if fighter else 0.6):
                return str(keys.index(best_key) + 1)
            for key in ("slip", "warp", "scan", "holy", "feed", "talk", "pay", "run"):
                if key in keys and not (key == "pay" and g.ship.money < 5000):
                    return str(keys.index(key) + 1)
            return str(keys.index(best_key) + 1)
        return random.choice(numbers) if numbers else ""      # a situation: whatever looks interesting

    def port_action(self):
        g = self.game
        ship = g.ship
        mods = getattr(ship, "passenger_modules", [])
        here = g.current_location.name
        if self.port_step == "start":
            if any(p.destination == here for m in mods for p in m.passengers):
                self.port_step = "unloaded"
                if self.pax_dest == here:
                    self.pax_dest = None
                return "u"
            self.port_step = "unloaded"
        if self.port_step == "unloaded":
            if sum(m.capacity for m in mods) < 6 and ship.money > 4000:
                self.port_step = "buy_module"
                return "m"
            self.port_step = "bought"
        if self.port_step == "bought":
            free = sum(m.capacity - len(m.passengers) for m in mods)
            aboard = sum(len(m.passengers) for m in mods)
            if free > 0 and aboard == 0 and g.port_system.waiting_passengers.get(here):
                self.port_step = "board"
                return "b"
            self.port_step = "done"
        return "back"


bot = Bot()
out = io.StringIO()
real = sys.stdout
sys.stdout = out


def fake_input(prompt=""):
    text = out.getvalue()
    tail = text[-600:]
    if len(text) > 200000:
        out.seek(0)
        out.truncate(0)
    g = bot.game
    write_trace(g)
    if g is not None:
        if g.turn >= max_turns:
            raise Done("max turns")
        if getattr(g, "ending_reached", None):
            raise Done("ending")
        if ledger_on:
            marks = bot.__dict__.setdefault("chapters_at", {})
            for chapter in g.story_manager.completed_chapters:
                if chapter not in marks:
                    marks[chapter] = {"turn": g.turn, "plot_points": g.story_manager.plot_points,
                                      "money": int(g.ship.money)}
        prog = (g.turn, g.story_manager.current_chapter)
        if prog == bot.last_progress:
            bot.stall += 1
            if bot.stall > 400:
                raise Done("stalled: no turn passes (last prompt tail: %r)" % tail[-160:])
        else:
            bot.stall = 0
            bot.last_progress = prog
    a = bot.answer(tail)
    if verbose:
        real.write("turn %s ch %s $%s -> %r\n" % (g.turn if g else "-", g.story_manager.current_chapter if g else "-",
                                                 int(g.ship.money) if g else "-", a))
    return a if a is not None else ""


builtins.input = fake_input
orig_vi = cargo.Game.validate_input
orig_vq = cargo.Game.validate_quantity_input


def vi(self, default_prompt, valid_options, prompt=None):
    bot.game = self
    bot.ctx = (prompt or default_prompt, valid_options)
    return orig_vi(self, default_prompt, valid_options, prompt)


def vq(self, prompt):
    bot.qty = prompt or True
    return orig_vq(self, prompt)


cargo.Game.validate_input = vi
cargo.Game.validate_quantity_input = vq

result = {"goal": goal, "seed": seed}
history = []
try:
    bot.ctx = None
    answers = iter(["2", VOYAGE, "Bot %s %d" % (goal, seed)])
    builtins.input = lambda prompt="": next(answers)
    game = cargo.Game()
    builtins.input = fake_input
    bot.game = game
    while True:
        try:
            game.play()
            result["end"] = "game over (play returned)"
            break
        except cargo.SwitchGame as sw:
            game = sw.game
            bot.game = game
            bot.loads += 1
        except Done as d:
            result["end"] = str(d)
            # after a save, reload it and continue (exercises save/load mid-game)
            break
        except SystemExit:
            result["end"] = "exit"
            break
except Exception:
    result["traceback"] = traceback.format_exc()[-1800:]
finally:
    sys.stdout = real
    shutil.rmtree(home, ignore_errors=True)

g = bot.game
write_trace(g, final=True)
if trace_file:
    trace_file.close()
if g is not None:
    sm = g.story_manager
    result.update({
        "turn": g.turn, "chapter": sm.current_chapter, "completed": sorted(sm.completed_chapters),
        "ending": getattr(g, "ending_reached", None), "money": int(g.ship.money),
        "plot_points": sm.plot_points, "trades": g.trades_completed,
        "victories": g.ship.combat_victories.get("total"), "defeats": g.ship.combat_defeats.get("total"),
        "rating": g.ship.attack + g.ship.defense + g.ship.speed, "damage": g.ship.damage,
        "rp": g.ship.research_points, "research": sorted(g.research.unlocked_options),
        "pax": g.reputation_manager.total_passengers, "pax_rep": g.ship.passenger_reputation,
        "trade_profit": int(sum(g.ship.trade_profits.values())),
        "stockmarkets": sum(1 for l in g.locations for b in l.buildings if b == "stockmarket"),
        "locations": len(g.locations), "known": len(g.known_locations),
        "open_requirements": {k: (v if not callable(v) else "fn") for k, v in bot.need().items()} if not result.get("traceback") else None,
        "inputs": bot.inputs, "loads": bot.loads,
        "discovered": sorted(g.discovered_locations), "all_locations": [(l.name, l.location_type) for l in g.locations],
        "here": g.current_location.name, "travel_to": getattr(bot, "travel_to", None),
        "active_quests": [q.name for q in g.quest_system.active_quests][:8],
        "unknown_prompts": [[list(map(str, k)), n] for k, n in bot.unknown.most_common(8)],
    })
    if ledger_on:
        result["ledger"] = {book: {k: round(v) for k, v in sorted(entries.items(), key=lambda kv: -abs(kv[1]))}
                            for book, entries in LEDGER.items()}
        result["chapters_at"] = getattr(bot, "chapters_at", {})
print(json.dumps(result, ensure_ascii=False, default=str))
