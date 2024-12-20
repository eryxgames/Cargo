import random
import os
import time
import shutil
from math import floor

# Define the Planet class
class Planet:
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        self.name = name
        self.tech_level = tech_level
        self.agri_level = agri_level
        self.research_points = research_points
        self.economy = economy
        self.market = self.generate_market()
        self.stockmarket_base = False
        self.stockmarket_cost = 5000
        self.buildings = []

    def generate_market(self):
        # Generate initial market prices based on tech and agri levels
        tech_price = 100 - (self.tech_level * 10)
        agri_price = 50 + (self.agri_level * 5)
        return {'tech': tech_price, 'agri': agri_price}

    def update_market(self, difficulty):
        # Simulate price changes based on difficulty and economy
        tech_change = random.randint(-5, 5) * (1 + difficulty)
        agri_change = random.randint(-3, 3) * (1 + difficulty)
        if self.economy == "Booming":
            tech_change += 5
            agri_change += 3
        elif self.economy == "Declining":
            tech_change -= 5
            agri_change -= 3
        self.market['tech'] = max(1, self.market['tech'] + tech_change)
        self.market['agri'] = max(1, self.market['agri'] + agri_change)
        if self.stockmarket_base:
            self.market['tech'] = max(1, self.market['tech'] - 10)
            self.market['agri'] = max(1, self.market['agri'] - 5)

    def build_stockmarket(self):
        self.stockmarket_base = True
        self.stockmarket_cost = 5000

    def build_building(self, building_name):
        if building_name == "Permaculture Paradise":
            self.market['agri'] = max(1, self.market['agri'] * 0.8)
            self.buildings.append(building_name)
        elif building_name == "Organic Certification Authority":
            self.market['agri'] = self.market['agri'] * 1.2
            self.buildings.append(building_name)
        elif building_name == "Agrobot Assembly Line":
            self.market['agri'] = max(1, self.market['agri'] * 0.6)
            self.buildings.append(building_name)
        elif building_name == "The Nanotech Nexus":
            self.market['tech'] = max(1, self.market['tech'] * 0.85)
            self.market['agri'] = max(1, self.market['agri'] * 0.85)
            self.buildings.append(building_name)
        elif building_name == "Neuroengineering Guild":
            self.market['tech'] = self.market['tech'] * 1.3
            self.buildings.append(building_name)

    def __str__(self):
        return f"{self.name} (Tech: {self.tech_level}, Agri: {self.agri_level}, RP: {self.research_points}, Economy: {self.economy})"

# Define the Ship class
class Ship:
    def __init__(self):
        self.cargo = {'tech': 0, 'agri': 0}
        self.money = 1000
        self.damage = 0
        self.upgrades = []
        self.items = []
        self.attack = 1
        self.defense = 1
        self.speed = 1
        self.quests = []

    def buy(self, item, quantity, price):
        cost = quantity * price
        if self.money >= cost:
            self.money -= cost
            self.cargo[item] += quantity
            return True
        print("Warning: Not enough money to buy.")
        return False

    def sell(self, item, quantity, price):
        if self.cargo[item] >= quantity:
            self.money += quantity * price
            self.cargo[item] -= quantity
            return True
        print("Warning: Not enough cargo to sell.")
        return False

    def repair(self, cost):
        if self.money >= cost:
            self.money -= cost
            self.damage = 0
            return True
        print("Warning: Not enough money to repair.")
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
            else:
                print(f"Warning: Invalid property name {property_name}.")
            return True
        print("Warning: Not enough money to upgrade.")
        return False

    def acquire_item(self, item_name):
        self.items.append(item_name)

    def is_empty_cargo(self):
        return self.cargo['tech'] == 0 and self.cargo['agri'] == 0

    def upgrade_property(self, property_name, amount):
        if property_name == 'attack':
            self.attack += amount
        elif property_name == 'defense':
            self.defense += amount
        elif property_name == 'speed':
            self.speed += amount
        else:
            print(f"Warning: Invalid property name {property_name}.")

    def add_quest(self, quest):
        self.quests.append(quest)

    def complete_quest(self, quest):
        if quest in self.quests:
            self.quests.remove(quest)
            return True
        return False

# Define the Game class
class Game:
    def __init__(self):
        self.term_width = self.get_terminal_width()
        self.term_height = self.get_terminal_height()
        self.difficulty = self.choose_difficulty()
        self.planets = self.generate_planets()
        self.ship = Ship()
        self.current_planet = random.choice(self.planets)
        self.turn = 0
        self.known_planets = [self.current_planet.name]
        self.event_log = []
        self.player_name = self.get_player_name()
        self.rank = "Explorer"
        self.display_starting_info()
        self.secret_quest_available = False
        self.stellar_portal_available = False

    def get_terminal_width(self):
        return shutil.get_terminal_size().columns

    def get_terminal_height(self):
        return shutil.get_terminal_size().lines

    def format_money(self, amount):
        if amount >= 1_000_000_000:
            return f"{amount/1_000_000_000:.1f}B"
        elif amount >= 1_000_000:
            return f"{amount/1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"{amount/1_000:.1f}K"
        return str(floor(amount))

    def create_box(self, content, style='single', width=None):
        if not width:
            width = self.term_width - 4

        chars = {
            'single': {'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘', 'h': '─', 'v': '│'},
            'double': {'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝', 'h': '═', 'v': '║'},
            'round': {'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯', 'h': '─', 'v': '│'}
        }[style]

        lines = []
        lines.append(f"{chars['tl']}{chars['h'] * width}{chars['tr']}")

        if isinstance(content, str):
            content = [content]

        for line in content:
            if isinstance(line, (list, tuple)):
                # Handle multi-column layout
                col_width = (width - len(line) + 1) // len(line)
                formatted_line = chars['v']
                for col in line:
                    formatted_line += f" {str(col):<{col_width-1}}{chars['v']}"
                lines.append(formatted_line)
            else:
                lines.append(f"{chars['v']} {str(line):<{width-2}} {chars['v']}")

        lines.append(f"{chars['bl']}{chars['h'] * width}{chars['br']}")
        return '\n'.join(lines)

    def display_message(self, message, pause=2, style='round'):
        box = self.create_box(message, style)
        print(box)
        if pause > 0:
            time.sleep(pause)

    def validate_input(self, prompt, valid_options):
        while True:
            self.display_message(prompt, 0)
            try:
                user_input = input(">>> ").strip().lower()
                if not user_input:
                    self.display_message("Command cancelled.")
                    return None
                if user_input in valid_options:
                    return user_input
                self.display_message(f"Invalid input. Valid options: {', '.join(valid_options)}", 1)
            except KeyboardInterrupt:
                self.display_message("Do you want to exit? (yes/no)", 0)
                confirm = input(">>> ").strip().lower()
                if confirm == 'yes':
                    self.display_message("Goodbye!", 1)
                    exit()

    def validate_quantity_input(self, prompt):
        while True:
            self.display_message(prompt, 0)
            try:
                user_input = input(">>> ").strip().lower()
                if user_input == 'max':
                    return 'max'
                quantity = int(user_input)
                if quantity > 0:
                    return quantity
                self.display_message("Please enter a positive number or 'max'", 1)
            except ValueError:
                self.display_message("Invalid input. Please enter a number or 'max'", 1)

    def display_turn_info(self):
        self.clear_screen()

        # Status table
        status_content = [
            ["Game Status", "Ship Status", "Planet Status"],
            [f"Turn: {self.turn}", f"Attack: {self.ship.attack}", f"Name: {self.current_planet.name}"],
            [f"Money: {self.format_money(self.ship.money)}", f"Defense: {self.ship.defense}", f"Tech Level: {self.current_planet.tech_level}"],
            [f"Tech Cargo: {self.format_money(self.ship.cargo['tech'])}", f"Speed: {self.ship.speed}", f"Agri Level: {self.current_planet.agri_level}"],
            [f"Agri Cargo: {self.format_money(self.ship.cargo['agri'])}", f"Damage: {self.ship.damage}%", f"Economy: {self.current_planet.economy}"],
            [f"Rank: {self.rank}", f"Items: {len(self.ship.items)}", f"Buildings: {len(self.current_planet.buildings)}"]
        ]

        print(self.create_box(status_content, 'double'))

        # Market prices
        market_content = [
            ["Market Prices"],
            [f"Tech: {self.format_money(self.current_planet.market['tech'])}"],
            [f"Agri: {self.format_money(self.current_planet.market['agri'])}"]
        ]
        print(self.create_box(market_content, 'single'))

        # Command menu
        commands = [
            "Commands: buy/b, sell/s, upgrade/u, travel/t,",
            "repair/r, info/i, build/bl, cantina/c,",
            "shop/sh, end/e"
        ]
        print(self.create_box(commands, 'round'))

    def display_planet_info(self):
        content = [
            ["Planet Information", "Ship Information"],
            [f"Name: {self.current_planet.name}", f"Attack: {self.ship.attack}"],
            [f"Tech Level: {self.current_planet.tech_level}", f"Defense: {self.ship.defense}"],
            [f"Agri Level: {self.current_planet.agri_level}", f"Speed: {self.ship.speed}"],
            [f"Research Points: {self.current_planet.research_points}", f"Items: {', '.join(self.ship.items) or 'None'}"],
            [f"Economy: {self.current_planet.economy}", f"Upgrades: {', '.join(self.ship.upgrades) or 'None'}"],
            [f"Buildings: {', '.join(self.current_planet.buildings) or 'None'}", ""]
        ]
        print(self.create_box(content, 'double'))
        time.sleep(3)

    def choose_difficulty(self):
        print("Choose difficulty level:")
        print("1. Easy")
        print("2. Normal")
        print("3. Expert")
        choice = input("Enter the number of your choice: ").strip()
        if choice == '1':
            return 0  # Easy
        elif choice == '2':
            return 1  # Normal
        elif choice == '3':
            return 2  # Expert
        else:
            print("Invalid choice. Defaulting to Normal.")
            return 1  # Normal

    def generate_planets(self):
        return [
            Planet("Alpha", 5, 3, 10, "Stable"),
            Planet("Beta", 3, 7, 15, "Booming"),
            Planet("Gamma", 8, 2, 20, "Declining"),
            Planet("Delta", 4, 6, 25, "Transformative"),
            Planet("Epsilon", 7, 4, 30, "Stable")
        ]

    def get_player_name(self):
        self.clear_screen()
        print("+" + "-"*self.term_width + "+")
        print("|" + " Welcome to Cargo! ".center(self.term_width) + "|")
        print("+" + "-"*self.term_width + "+")
        name = input("Enter your name (or press Enter for a random name): ").strip()
        if not name:
            name = random.choice(["Captain", "Commander", "Pilot", "Admiral", "Spacefarer"])
        return name

    def display_starting_info(self):
        planet_type = "industrial"
        if self.current_planet.agri_level > self.current_planet.tech_level:
            planet_type = "agricultural"
        elif self.current_planet.research_points > 15:
            planet_type = "research"

        print(f"Welcome {self.player_name} to {self.current_planet.name}, a boring {planet_type} outpost, where your adventure begins.")
        special_events = [
            "Revolutions are happening!",
            "Economy boom!",
            "Technological advancements!",
            "Agricultural breakthroughs!",
            "Nothing special happening."
        ]
        special_event = random.choice(special_events)
        print(f"Special Event: {special_event}")
        time.sleep(3)  # Pause to let the player read the information

    def clear_screen(self):
        os.system('clear' if os.name == 'posix' else 'cls')

    def validate_planet_input(self, prompt):
        while True:
            self.display_message(prompt, 0)
            try:
                user_input = input(">>> ").strip().lower()
                if not user_input:
                    self.display_message("Command cancelled.")
                    return None
                for planet in self.planets:
                    if planet.name.lower() == user_input:
                        return planet.name
                self.display_message(f"Invalid input. Valid options: {', '.join([planet.name for planet in self.planets])}", 1)
            except KeyboardInterrupt:
                self.display_message("Do you want to exit? (yes/no)", 0)
                confirm = input(">>> ").strip().lower()
                if confirm == 'yes':
                    self.display_message("Goodbye!", 1)
                    exit()

    def play_turn(self):
        self.display_turn_info()

        action = self.validate_input(
            "Choose action (buy/b, sell/s, upgrade/u, travel/t, repair/r, info/i, build/bl, cantina/c, end/e): ",
            ['buy', 'b', 'sell', 's', 'upgrade', 'u', 'travel', 't', 'repair', 'r', 'info', 'i', 'build', 'bl', 'cantina', 'c', 'end', 'e']
        )

        # Handle cancelled command
        if action is None:
            return

        if action in ['buy', 'b']:
            item = self.validate_input("Choose item (tech/agri): ", ['tech', 'agri'])
            quantity = self.validate_quantity_input("Enter quantity (or 'max' for maximum): ")
            if quantity == 'max':
                quantity = self.ship.money // self.current_planet.market[item]
            if self.ship.buy(item, quantity, self.current_planet.market[item]):
                self.display_message(f"Bought {self.format_money(quantity)} {item}.")
        elif action in ['sell', 's']:
            item = self.validate_input("Choose item (tech/agri): ", ['tech', 'agri'])
            quantity = self.validate_quantity_input("Enter quantity (or 'max' for maximum): ")
            if quantity == 'max':
                quantity = self.ship.cargo[item]
            if self.ship.sell(item, quantity, self.current_planet.market[item]):
                self.display_message(f"Sold {self.format_money(quantity)} {item}.")
        elif action in ['upgrade', 'u']:
            property_name = self.validate_input("Choose property to upgrade (attack/defense/speed): ", ['attack', 'defense', 'speed'])
            cost = 2000
            if self.ship.upgrade(property_name, cost):
                self.display_message(f"Upgraded {property_name}.")
        elif action in ['travel', 't']:
            if "navcomp" in self.ship.items:
                self.display_message("Choose a planet to travel to:")
                for i, planet in enumerate(self.known_planets):
                    print(f"{i+1}. {planet}")
                choice = self.validate_planet_input("Enter the number of the planet or the planet name: ")
                for planet in self.planets:
                    if planet.name.lower() == choice.lower():
                        self.current_planet = planet
                        self.display_message(f"Traveled to {planet.name}.")
                        self.turn += 1
                        self.random_event()
                        # Check for quest completion
                        for quest in self.ship.quests:
                            if quest[1] == 'tech' and self.ship.cargo['tech'] >= quest[2]:
                                self.ship.complete_quest(quest)
                                reward_money = quest[3] * (1 + self.rank_multiplier())
                                self.ship.money += reward_money
                                self.display_message(f"Quest completed: {quest[0]}")
                                self.display_message(f"Reward: {self.format_money(reward_money)} money")
                            elif quest[1] == 'agri' and self.ship.cargo['agri'] >= quest[2]:
                                self.ship.complete_quest(quest)
                                reward_money = quest[3] * (1 + self.rank_multiplier())
                                self.ship.money += reward_money
                                self.display_message(f"Quest completed: {quest[0]}")
                                self.display_message(f"Reward: {self.format_money(reward_money)} money")
                        return
                else:
                    self.display_message("Invalid choice.")
            else:
                planet_name = input("Enter planet name to travel: ").strip()
                for planet in self.planets:
                    if planet.name.lower() == planet_name.lower():
                        self.current_planet = planet
                        self.display_message(f"Traveled to {planet_name}.")
                        self.turn += 1
                        self.random_event()
                        # Check for quest completion
                        for quest in self.ship.quests:
                            if quest[1] == 'tech' and self.ship.cargo['tech'] >= quest[2]:
                                self.ship.complete_quest(quest)
                                reward_money = quest[3] * (1 + self.rank_multiplier())
                                self.ship.money += reward_money
                                self.display_message(f"Quest completed: {quest[0]}")
                                self.display_message(f"Reward: {self.format_money(reward_money)} money")
                            elif quest[1] == 'agri' and self.ship.cargo['agri'] >= quest[2]:
                                self.ship.complete_quest(quest)
                                reward_money = quest[3] * (1 + self.rank_multiplier())
                                self.ship.money += reward_money
                                self.display_message(f"Quest completed: {quest[0]}")
                                self.display_message(f"Reward: {self.format_money(reward_money)} money")
                        return
                else:
                    self.display_message("Planet not found.")
        elif action in ['repair', 'r']:
            cost = self.ship.damage * 10  # Proportional repair cost
            if self.ship.repair(cost):
                self.display_message("Ship repaired.")
            else:
                self.display_message(f"Not enough money to repair. Repair cost: {self.format_money(cost)}")
        elif action in ['info', 'i']:
            self.display_planet_info()
        elif action in ['build', 'bl']:
            building_name = self.validate_input("Choose building to build (stockmarket/sm, permaculture/pc, organic/oc, agrobot/ab, nanotech/nt, neuroengineering/ne): ",
                                               ['stockmarket', 'sm', 'permaculture', 'pc', 'organic', 'oc', 'agrobot', 'ab', 'nanotech', 'nt', 'neuroengineering', 'ne'])
            if building_name in ['stockmarket', 'sm']:
                if not self.current_planet.stockmarket_base:
                    if self.ship.money >= self.current_planet.stockmarket_cost:
                        self.ship.money -= self.current_planet.stockmarket_cost
                        self.current_planet.build_stockmarket()
                        self.display_message(f"Stockmarket Base built on {self.current_planet.name}.")
                    else:
                        self.display_message("Not enough money to build a Stockmarket Base.")
                else:
                    self.display_message("Stockmarket Base already built on this planet.")
            elif building_name in ['permaculture', 'pc']:
                if self.ship.money >= 3000:
                    self.ship.money -= 3000
                    self.current_planet.build_building("Permaculture Paradise")
                    self.display_message(f"Permaculture Paradise built on {self.current_planet.name}.")
                else:
                    self.display_message("Not enough money to build Permaculture Paradise.")
            elif building_name in ['organic', 'oc']:
                if self.ship.money >= 4000:
                    self.ship.money -= 4000
                    self.current_planet.build_building("Organic Certification Authority")
                    self.display_message(f"Organic Certification Authority built on {self.current_planet.name}.")
                else:
                    self.display_message("Not enough money to build Organic Certification Authority.")
            elif building_name in ['agrobot', 'ab']:
                if self.ship.money >= 5000:
                    self.ship.money -= 5000
                    self.current_planet.build_building("Agrobot Assembly Line")
                    self.display_message(f"Agrobot Assembly Line built on {self.current_planet.name}.")
                else:
                    self.display_message("Not enough money to build Agrobot Assembly Line.")
            elif building_name in ['nanotech', 'nt']:
                if self.ship.money >= 6000:
                    self.ship.money -= 6000
                    self.current_planet.build_building("The Nanotech Nexus")
                    self.display_message(f"The Nanotech Nexus built on {self.current_planet.name}.")
                else:
                    self.display_message("Not enough money to build The Nanotech Nexus.")
            elif building_name in ['neuroengineering', 'ne']:
                if self.ship.money >= 7000:
                    self.ship.money -= 7000
                    self.current_planet.build_building("Neuroengineering Guild")
                    self.display_message(f"Neuroengineering Guild built on {self.current_planet.name}.")
                else:
                    self.display_message("Not enough money to build Neuroengineering Guild.")
        elif action in ['cantina', 'c']:
            self.visit_cantina()
        elif action in ['shop', 'sh']:
            self.shop()
        elif action in ['end', 'e']:
            self.turn += 1
            self.random_event()
            return
        else:
            self.display_message("Invalid action.")

    def random_event(self):
        events = [
            "Pirate attack!",
            "Market crash!",
            "Technological breakthrough!",
            "Exotic radiation!",
            "Contamination!",
            "Cargo bay hit by asteroid!",
            "Cargo bay raided by guerrilla!",
            "Spacetime rift!",
            "Rogue Corsair attacking!",
            "Pirate mothership attacking!",
            "Gravitational anomaly!"
        ]
        event = random.choice(events)
        self.event_log.append({'turn': self.turn, 'event': event})
        print(f"Random Event: {event}")
        if event == "Pirate attack!":
            if "turrets" in self.ship.items and random.random() < 0.35:
                print("Event! Pirate attack repelled by laser turrets!")
            else:
                self.ship.damage += min(random.randint(10, 25) * (1 + self.difficulty), 49)
                stolen_money = random.randint(1, int(self.ship.money // 2))
                self.ship.money -= stolen_money
                print(f"Event! Pirates stole {self.format_money(stolen_money)} money and caused {self.ship.damage}% damage.")
        elif event == "Market crash!":
            self.current_planet.update_market(self.difficulty)
            print("Event! Market prices have changed.")
        elif event == "Technological breakthrough!":
            self.current_planet.tech_level += 1
            print("Event! Technological breakthrough! Tech level increased.")
        elif event == "Exotic radiation!":
            destroyed_tech = random.randint(1, max(1, self.ship.cargo['tech']))
            self.ship.cargo['tech'] = max(0, self.ship.cargo['tech'] - destroyed_tech)
            print(f"Event! Exotic radiation destroyed {self.format_money(destroyed_tech)} tech goods.")
        elif event == "Contamination!":
            destroyed_agri = random.randint(1, max(1, self.ship.cargo['agri']))
            self.ship.cargo['agri'] = max(0, self.ship.cargo['agri'] - destroyed_agri)
            print(f"Event! Contamination destroyed {self.format_money(destroyed_agri)} agri goods.")
        elif event == "Cargo bay hit by asteroid!":
            self.ship.damage += min(random.randint(5, 15) * (1 + self.difficulty), 49)
            total_cargo = self.ship.cargo['tech'] + self.ship.cargo['agri']
            destroyed_cargo = random.randint(1, max(1, total_cargo // 2))
            self.ship.cargo['tech'] = max(0, self.ship.cargo['tech'] - destroyed_cargo // 2)
            self.ship.cargo['agri'] = max(0, self.ship.cargo['agri'] - destroyed_cargo // 2)
            print(f"Event! Asteroid hit destroyed {self.format_money(destroyed_cargo)} units of cargo and caused {self.ship.damage}% damage.")
        elif event == "Cargo bay raided by guerrilla!":
            total_cargo = self.ship.cargo['tech'] + self.ship.cargo['agri']
            stolen_cargo = random.randint(1, max(1, total_cargo // 2))
            self.ship.cargo['tech'] = max(0, self.ship.cargo['tech'] - stolen_cargo // 2)
            self.ship.cargo['agri'] = max(0, self.ship.cargo['agri'] - stolen_cargo // 2)
            print(f"Event! Guerrilla raid stole {self.format_money(stolen_cargo)} units of cargo.")
        elif event == "Spacetime rift!":
            self.ship.damage += min(random.randint(15, 35) * (1 + self.difficulty), 49)
            print(f"Event! Spacetime rift caused {self.ship.damage}% damage.")
        elif event == "Rogue Corsair attacking!":
            self.battle_event(2, 1, 1)
        elif event == "Pirate mothership attacking!":
            self.battle_event(5, 5, 5)
        elif event == "Gravitational anomaly!":
            self.gravitational_anomaly_event()

        if "shield" in self.ship.items:
            self.ship.damage = max(0, self.ship.damage - 5)

    def gravitational_anomaly_event(self):
        print("You have encountered a gravitational anomaly!")
        outcome = random.choice(["rare elements", "scientific samples"])
        if outcome == "rare elements":
            tech_goods = random.randint(5, 15)
            self.ship.cargo['tech'] += tech_goods
            print(f"You found {self.format_money(tech_goods)} tech goods.")
        elif outcome == "scientific samples":
            research_points = random.randint(5, 15)
            self.current_planet.research_points += research_points
            print(f"You gained {self.format_money(research_points)} research points.")

    def battle_event(self, enemy_attack, enemy_defense, enemy_speed):
        print(f"An enemy is attacking! Enemy stats: ATK {enemy_attack}, DEF {enemy_defense}, SPD {enemy_speed}")

        player_damage = max(0, enemy_attack - self.ship.defense)
        enemy_damage = max(0, self.ship.attack - enemy_defense)

        if self.ship.speed > enemy_speed:
            print("You have the speed advantage!")
            enemy_damage += 5
        elif self.ship.speed < enemy_speed:
            print("Enemy has the speed advantage!")
            player_damage += 5

        # Introduce randomness based on stats
        if random.random() < 0.5:
            player_damage = max(0, player_damage - random.randint(0, self.ship.defense))
        if random.random() < 0.5:
            enemy_damage = max(0, enemy_damage - random.randint(0, enemy_defense))

        print(f"You deal {enemy_damage} damage to the enemy.")
        print(f"The enemy deals {player_damage} damage to you.")

        if enemy_damage > player_damage:
            print("You won the battle!")
            reward = random.choice([
                ("money", random.randint(100, 500)),
                ("tech", random.randint(5, 15)),
                ("agri", random.randint(5, 15)),
                ("item", random.choice(["navcomp", "shield", "turrets", "scanner"]))
            ])
            if reward[0] == "money":
                self.ship.money += reward[1]
                print(f"Reward: {self.format_money(reward[1])} money")
            elif reward[0] == "tech":
                self.ship.cargo['tech'] += reward[1]
                print(f"Reward: {self.format_money(reward[1])} tech goods")
            elif reward[0] == "agri":
                self.ship.cargo['agri'] += reward[1]
                print(f"Reward: {self.format_money(reward[1])} agri goods")
            elif reward[0] == "item":
                self.ship.acquire_item(reward[1])
                print(f"Reward: {reward[1]} item")
        else:
            print("You lost the battle!")
            penalty = random.choice([
                ("money", random.randint(50, 200)),
                ("tech", random.randint(2, 10)),
                ("agri", random.randint(2, 10)),
                ("damage", random.randint(10, 30))
            ])
            if penalty[0] == "money":
                self.ship.money = max(0, self.ship.money - penalty[1])
                print(f"Penalty: Lost {self.format_money(penalty[1])} money")
            elif penalty[0] == "tech":
                self.ship.cargo['tech'] = max(0, self.ship.cargo['tech'] - penalty[1])
                print(f"Penalty: Lost {self.format_money(penalty[1])} tech goods")
            elif penalty[0] == "agri":
                self.ship.cargo['agri'] = max(0, self.ship.cargo['agri'] - penalty[1])
                print(f"Penalty: Lost {self.format_money(penalty[1])} agri goods")
            elif penalty[0] == "damage":
                self.ship.damage += penalty[1]
                print(f"Penalty: {penalty[1]}% additional damage")

    def visit_cantina(self):
        self.display_message("Welcome to the Cantina!", 1)

        action = self.validate_input(
            "Choose action (buy map/bm, update map/um, listen to gossip/lg, quests/q): ",
            ['buy map', 'bm', 'update map', 'um', 'listen to gossip', 'lg', 'quests', 'q']
        )

        if action is None:
            return

        if action in ['buy map', 'bm']:
            if self.ship.money >= 200:
                self.ship.money -= 200
                self.display_message("You bought a map! Here are some new planet names and levels:", 1)
                for planet in self.planets:
                    if planet.name not in self.known_planets:
                        self.known_planets.append(planet.name)
                        print(f"{planet.name} (Tech: {planet.tech_level}, Agri: {planet.agri_level})")
            else:
                self.display_message("Not enough money to buy a map.")
        elif action in ['update map', 'um']:
            if self.ship.money >= 350:
                self.ship.money -= 350
                self.display_message("You updated the map! Here are the commodities wanted:", 1)
                for planet in self.planets:
                    print(f"{planet.name}: Tech - {self.format_money(planet.market['tech'])}, Agri - {self.format_money(planet.market['agri'])}")
            else:
                self.display_message("Not enough money to update the map.")
        elif action in ['listen to gossip', 'lg']:
            if self.ship.money >= 150:
                self.ship.money -= 150
                self.display_message("You listened to gossip! Here are some tips:", 1)
                for planet in self.planets:
                    if planet.market['tech'] < 50:
                        print(f"Cheap tech goods available on {planet.name}.")
                    if planet.market['agri'] < 30:
                        print(f"Cheap agri goods available on {planet.name}.")
                if random.random() < 0.3:  # 30% chance to get a quest
                    quest = random.choice([
                        ("Deliver 10 tech goods to Alpha", "tech", 10, 500),
                        ("Deliver 15 agri goods to Beta", "agri", 15, 700),
                        ("Deliver 20 tech goods to Gamma", "tech", 20, 1000),
                        ("Deliver 25 agri goods to Delta", "agri", 25, 1200)
                    ])
                    self.ship.add_quest(quest)
                    self.display_message(f"You received a quest: {quest[0]}")
                    self.display_message(f"Reward: {self.format_money(quest[3])} money")
            else:
                self.display_message("Not enough money to listen to gossip.")
        elif action in ['quests', 'q']:
            if self.ship.quests:
                self.display_message("Active Quests:")
                for quest in self.ship.quests:
                    print(f"- {quest[0]}")
            else:
                self.display_message("No active quests.")
        time.sleep(3)  # Pause to let the player read the information

    def shop(self):
        self.display_message("Welcome to the Shop!", 1)
        available_items = random.sample([
            ("navcomp", 500),
            ("scanner", 700),
            ("probe", 900),
            ("patcher", 300)
        ], k=2)  # Randomly select 2 items
        for item, price in available_items:
            print(f"{item.capitalize()}: {self.format_money(price)} money")
        item_choice = self.validate_input("Choose item to buy (or 'none' to exit): ", [item[0] for item in available_items] + ['none'])
        if item_choice == 'none':
            return
        for item, price in available_items:
            if item_choice == item:
                if self.ship.money >= price:
                    self.ship.money -= price
                    self.ship.acquire_item(item)
                    self.display_message(f"You bought a {item}.")
                else:
                    self.display_message("Not enough money to buy this item.")
                return

    def display_score(self):
        score = self.ship.money + (self.ship.cargo['tech'] * 10) + (self.ship.cargo['agri'] * 5)
        rank = (score / self.turn) if self.turn > 0 else score
        print("+" + "-"*self.term_width + "+")
        print(f"| Game Over! Your score is: {self.format_money(score):<{self.term_width-18}} |")
        print(f"| Money: {self.format_money(self.ship.money):<{self.term_width-13}} |")
        print(f"| Cargo: Tech - {self.format_money(self.ship.cargo['tech']):<2}, Agri - {self.format_money(self.ship.cargo['agri']):<{self.term_width-21}} |")
        print(f"| Upgrades: {', '.join(self.ship.upgrades) if self.ship.upgrades else 'None':<{self.term_width-10}} |")
        print(f"| Items: {', '.join(self.ship.items) if self.ship.items else 'None':<{self.term_width-7}} |")
        print(f"| Rank: {rank:.2f} ".center(self.term_width) + "|")
        print("+" + "-"*self.term_width + "+")

    def update_rank(self):
        score = self.ship.money + (self.ship.cargo['tech'] * 10) + (self.ship.cargo['agri'] * 5)
        if score >= 1000000:
            self.rank = "Galactic Legend"
        elif score >= 500000:
            self.rank = "Interstellar Hero"
        elif score >= 200000:
            self.rank = "Star Commander"
        elif score >= 100000:
            self.rank = "Space Admiral"
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
        elif self.rank == "Interstellar Hero":
            return 8
        elif self.rank == "Star Commander":
            return 6
        elif self.rank == "Space Admiral":
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
            self.play_turn()
            self.update_rank()

            if self.ship.money <= 0 and self.ship.is_empty_cargo():
                self.display_message("Game Over: No money and no cargo left.", 2)
                self.display_score()
                break

            if self.ship.damage >= 100:
                self.display_message("Game Over: Ship destroyed!", 2)
                self.display_score()
                break

            if all(planet.stockmarket_base for planet in self.planets):
                self.secret_quest_available = True
                resign = self.validate_input("Do you want to resign? (yes/no): ", ['yes', 'no'])
                if resign == 'yes':
                    self.display_score()
                    print("You are the Galactic Tycoon!")
                    print(f"Congratulations, {self.player_name}! You have achieved the rank of {self.rank}.")
                    print("Your story will be remembered throughout the galaxy.")
                    break
                else:
                    self.display_message("You have chosen to continue your adventure into the unknown.")
                    self.stellar_portal_available = True
                    if self.ship.money >= self.ship.money - 1500:
                        self.ship.money = 1500
                        self.display_message("You have paid for the secret quest and a Stellar Portal appears on this planet.")
                        self.planets = self.generate_new_planets()
                        self.current_planet = random.choice(self.planets)
                        self.known_planets = [self.current_planet.name]
                        self.display_message("You have traveled to a new set of planets with more volatile price movements.")
                    else:
                        self.display_message("Not enough money to pay for the secret quest.")

        play_again = self.validate_input("Do you want to play again? (yes/no): ", ['yes', 'no'])
        if play_again == 'yes':
            self.__init__()
            self.play()

    def generate_new_planets(self):
        return [
            Planet("Zeta", 10, 1, 5, "Stable"),
            Planet("Eta", 1, 10, 5, "Booming"),
            Planet("Theta", 8, 8, 10, "Declining"),
            Planet("Iota", 5, 5, 15, "Transformative"),
            Planet("Kappa", 3, 3, 20, "Stable")
        ]

    def clear_screen(self):
        os.system('clear' if os.name == 'posix' else 'cls')

# Start the game
if __name__ == "__main__":
    game = Game()
    game.play()
