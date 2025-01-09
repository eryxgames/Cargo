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
        self.mining_efficiency = random.randint(60, 100)  # New: affects mining output
        self.market['salt'] = 0
        self.market['fuel'] = 0
        self.production_cooldown = {}  # New: tracks cooldown for resource production
        self.banned_commodities = []  # New: List of temporarily banned commodities
        self.ban_duration = {}  # New: Duration of bans for each commodity
        self.mineral_deposits = {}  # New: Dictionary to store discovered deposits
        self.mining_platforms = []  # New: List of mining platforms and their type

    def calculate_mining_output(self, platform_type):
        """Calculate mining output based on efficiency and random factors"""
        base_output = random.randint(10, 20)
        efficiency_bonus = self.mining_efficiency / 100
        return int(base_output * efficiency_bonus)

    def produce_resources(self):
        """Handle resource production from mining platforms"""
        for platform in self.mining_platforms:
            resource_type = platform['type']
            if resource_type not in self.production_cooldown or self.production_cooldown[resource_type] <= 0:
                output = self.calculate_mining_output(resource_type)
                if resource_type == 'salt':
                    self.market['salt'] = random.randint(80, 120)
                elif resource_type == 'fuel':
                    self.market['fuel'] = random.randint(150, 200)
                self.production_cooldown[resource_type] = 3  # 3 turns cooldown
            else:
                self.production_cooldown[resource_type] -= 1

    def build_mining_platform(self, deposit_type, cost):
        """Build a new mining platform for specified deposit"""
        if deposit_type in self.mineral_deposits:
            if self.mineral_deposits[deposit_type] > 0:
                self.mining_platforms.append({
                    'type': deposit_type,
                    'efficiency': self.mining_efficiency,
                    'capacity': random.randint(100, 200)
                })
                self.mineral_deposits[deposit_type] -= 1
                return True
        return False

    def generate_market(self):
        # Generate initial market prices based on tech and agri levels
        tech_price = 100 - (self.tech_level * 10)
        agri_price = 50 + (self.agri_level * 5)
        return {
            'tech': tech_price,
            'agri': agri_price,
            'salt': 0,  # New: Mining commodities
            'fuel': 0
        }

    def update_market(self, difficulty):
            # Base price changes with randomization and difficulty scaling
            tech_change = random.randint(-5, 5) * (1 + difficulty)
            agri_change = random.randint(-3, 3) * (1 + difficulty)
            
            # Economy effects
            if self.economy == "Booming":
                tech_change += 5
                agri_change += 3
            elif self.economy == "Declining":
                tech_change -= 5
                agri_change -= 3
            elif self.economy == "Formative":
                tech_change = int(tech_change * 1.2)  # More volatile prices
                agri_change = int(agri_change * 1.2)

            # Apply stockmarket effects if present
            if self.stockmarket_base:
                tech_change = max(1, tech_change - 10)
                agri_change = max(1, agri_change - 5)

            # Calculate new prices
            new_tech_price = max(0, self.market['tech'] + tech_change)
            new_agri_price = max(0, self.market['agri'] + agri_change)

            # Handle price changes from buildings
            for building in self.buildings:
                if building == "Permaculture Paradise":
                    new_agri_price = max(1, new_agri_price * 0.8)
                elif building == "Organic Certification Authority":
                    new_agri_price = new_agri_price * 1.2
                elif building == "Agrobot Assembly Line":
                    new_agri_price = max(1, new_agri_price * 0.6)
                elif building == "The Nanotech Nexus":
                    new_tech_price = max(1, new_tech_price * 0.85)
                    new_agri_price = max(1, new_agri_price * 0.85)
                elif building == "Neuroengineering Guild":
                    new_tech_price = new_tech_price * 1.3

            # Handle zero prices and bans
            if new_tech_price == 0 and 'tech' not in self.banned_commodities:
                self.banned_commodities.append('tech')
                self.ban_duration['tech'] = random.randint(2, 4)  # Random ban duration
            if new_agri_price == 0 and 'agri' not in self.banned_commodities:
                self.banned_commodities.append('agri')
                self.ban_duration['agri'] = random.randint(2, 4)

            # Update mining commodity prices if platforms exist
            for platform in self.mining_platforms:
                if platform['type'] == 'salt':
                    # Salt prices fluctuate less than tech/agri
                    salt_change = random.randint(-3, 3) * (1 + difficulty)
                    new_salt_price = max(60, min(150, self.market['salt'] + salt_change))
                    self.market['salt'] = new_salt_price
                elif platform['type'] == 'fuel':
                    # Fuel prices are more volatile
                    fuel_change = random.randint(-8, 8) * (1 + difficulty)
                    new_fuel_price = max(120, min(250, self.market['fuel'] + fuel_change))
                    self.market['fuel'] = new_fuel_price

            # Update final prices
            self.market['tech'] = new_tech_price
            self.market['agri'] = new_agri_price

            # Update ban durations and remove expired bans
            for commodity in list(self.ban_duration.keys()):
                self.ban_duration[commodity] -= 1
                if self.ban_duration[commodity] <= 0:
                    self.banned_commodities.remove(commodity)
                    del self.ban_duration[commodity]
                    # Reset price for previously banned commodity
                    if commodity == 'tech':
                        self.market['tech'] = 100 - (self.tech_level * 10)
                    elif commodity == 'agri':
                        self.market['agri'] = 50 + (self.agri_level * 5)

            # Ensure all prices stay within reasonable bounds
            self.market['tech'] = max(1, min(200, self.market['tech']))
            self.market['agri'] = max(1, min(150, self.market['agri']))
            
            # Production cooldown updates
            for resource_type in list(self.production_cooldown.keys()):
                if self.production_cooldown[resource_type] > 0:
                    self.production_cooldown[resource_type] -= 1

    def add_temporary_ban(self, commodity, duration):
        if commodity not in self.banned_commodities:
            self.banned_commodities.append(commodity)
            self.ban_duration[commodity] = duration

    def can_trade(self, commodity):
        return commodity not in self.banned_commodities

    def calculate_tax_rate(self, player_rank, profit):
        base_tax = 0.05  # 5% base tax
        rank_multiplier = {
            "Explorer": 1,
            "Pilot": 1.2,
            "Captain": 1.4,
            "Commander": 1.6,
            "Star Commander": 1.8,
            "Space Admiral": 2.0,
            "Stellar Hero": 2.2,
            "Galactic Legend": 2.5
        }
        
        # Reduce tax based on number of buildings
        building_discount = len(self.buildings) * 0.02  # 2% reduction per building
        
        final_tax_rate = (base_tax * rank_multiplier.get(player_rank, 1)) - building_discount
        return max(0.01, min(0.25, final_tax_rate))  # Keep between 1% and 25%

    def build_mining_platform(self):
        if not self.current_planet.mineral_deposits:
            self.display_simple_message("No mineral deposits found! Use geoscan first.")
            return
            
        available_deposits = list(self.current_planet.mineral_deposits.keys())
        deposit_type = self.validate_input(
            f"Choose deposit type to mine ({', '.join(available_deposits)}): ",
            available_deposits
        )
        
        cost = 10000
        if self.ship.money >= cost:
            self.ship.money -= cost
            self.current_planet.mining_platforms.append({
                'type': deposit_type,
                'capacity': random.randint(100, 200)
            })
            self.display_simple_message(f"Mining platform for {deposit_type} built!")
        else:
            self.display_simple_message("Not enough money to build mining platform.")

    def build_stockmarket(self):
        """
        Build a stock market on the planet. Now handled directly without separate method.
        This method is kept for backward compatibility but should be phased out.
        """
        self.stockmarket_base = True
        self.market['tech'] = max(1, self.market['tech'] - 10)
        self.market['agri'] = max(1, self.market['agri'] - 5)
        # Note: Actual construction is now handled in handle_building_construction

    def build_building(self, building_name):
        """
        Build a building and apply its effects
        Returns: cost_multiplier for the building
        """
        cost_multiplier = self.buildings.count(building_name) + 1
        
        # Apply building effects
        if building_name == "Mining Facility":
            self.mining_efficiency = min(100, self.mining_efficiency + 10)
        elif building_name == "Permaculture Paradise":
            self.market['agri'] = max(1, self.market['agri'] * 0.8)
        elif building_name == "Organic Certification Authority":
            self.market['agri'] = self.market['agri'] * 1.2
        elif building_name == "Agrobot Assembly Line":
            self.market['agri'] = max(1, self.market['agri'] * 0.6)
        elif building_name == "The Nanotech Nexus":
            self.market['tech'] = max(1, self.market['tech'] * 0.85)
            self.market['agri'] = max(1, self.market['agri'] * 0.85)
        elif building_name == "Neuroengineering Guild":
            self.market['tech'] = self.market['tech'] * 1.3
        
        # Add building to planet's buildings list
        self.buildings.append(building_name)
        
        return cost_multiplier

    def __str__(self):
        return f"{self.name} (Tech: {self.tech_level}, Agri: {self.agri_level}, RP: {self.research_points}, Economy: {self.economy})"

class Research:
    def __init__(self):
        self.unlocked_options = set()
        self.research_costs = {
            'advanced_trading': 100,
            'improved_scanning': 150,
            'geological_survey': 200,
            'political_influence': 250,
            'mining_efficiency': 300,  # New research option
            'market_manipulation': 350  # New research option
        }
        self.research_benefits = {
            'advanced_trading': {'tax_reduction': 0.02},
            'improved_scanning': {'scout_success': 0.2},
            'geological_survey': {'mining_efficiency': 0.15},
            'political_influence': {'revolution_success': 0.2},
            'mining_efficiency': {'output_bonus': 0.25},
            'market_manipulation': {'price_control': 0.1}
        }
    
    def can_unlock(self, option, research_points):
        return research_points >= self.research_costs.get(option, float('inf'))

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
            'market_manipulation': 60
        }
        
        # Success chances for various actions
        self.base_success_rates = {
            'scout': 0.65,
            'geoscan': 0.70,
            'revolution': 0.50,
            'market_manipulation': 0.60
        }

    def research(self, planet, option, research_system):
        """
        Attempt to research a new technology
        Returns: (bool success, str message)
        """
        if option in research_system.unlocked_options:
            return False, "This research has already been completed."
            
        # Apply immediate benefits based on research type
        if option == 'mining_efficiency':
            planet.mining_efficiency = min(100, 
                int(planet.mining_efficiency * (1 + research_system.research_benefits['mining_efficiency']['output_bonus'])))
        
        return True, f"Successfully researched {option}!"

    def scout_area(self, planet, research_system):
        """
        Scout the area for resources or items
        Returns: (bool success, str type, any value, str message)
        """
        # Calculate success chance
        success_chance = self.base_success_rates['scout']
        if 'improved_scanning' in research_system.unlocked_options:
            success_chance += research_system.research_benefits['improved_scanning']['scout_success']
            
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
        if 'geological_survey' in research_system.unlocked_options:
            success_chance += research_system.research_benefits['geological_survey']['mining_efficiency']
            
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
        if 'political_influence' in research_system.unlocked_options:
            success_chance += research_system.research_benefits['political_influence']['revolution_success']
            
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
        if random.random() < self.base_success_rates['market_manipulation']:
            manipulation_power = research_system.research_benefits['market_manipulation']['price_control']
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
    def __init__(self):
        self.cargo = {'tech': 0, 'agri': 0, 'salt': 0, 'fuel': 0}
        self.money = 1000
        self.damage = 0
        self.upgrades = []
        self.items = {}
        self.attack = 1
        self.defense = 1
        self.speed = 1
        self.quests = []
        self.research_points = 0  # Add research points to ship
        self.upgrade_costs = {
            'attack': 2000,
            'defense': 2000,
            'speed': 2000
        }
        self.item_purchase_count = {}  # Track number of purchases for price scaling

    def buy(self, item, quantity, price, planet, player_rank):
        # Check if item can be traded
        if not planet.can_trade(item):
            print(f"Warning: {item} trading is banned on this planet.")
            return False

        # Check if mining platform exists for salt and fuel
        if item in ['salt', 'fuel']:
            has_platform = any(p['type'] == item for p in planet.mining_platforms)
            if not has_platform:
                print(f"Warning: No mining platform for {item} on this planet.")
                return False

        cost = quantity * price
        if self.money >= cost:
            # Calculate and apply tax
            tax_rate = planet.calculate_tax_rate(player_rank, cost)
            tax_amount = cost * tax_rate
            total_cost = cost + tax_amount
            
            if self.money >= total_cost:
                self.money -= total_cost
                self.cargo[item] += quantity
                return True
            else:
                print(f"Warning: Not enough money to cover cost plus {tax_rate*100}% tax.")
                return False
        print("Warning: Not enough money to buy.")
        return False

    def sell(self, item, quantity, price, planet, player_rank):
        if not planet.can_trade(item):
            print(f"Warning: {item} trading is banned on this planet.")
            return False

        # Check if mining platform exists for salt and fuel
        if item in ['salt', 'fuel']:
            has_platform = any(p['type'] == item for p in planet.mining_platforms)
            if not has_platform:
                print(f"Warning: No mining platform for {item} on this planet.")
                return False
                
        if self.cargo[item] >= quantity:
            revenue = quantity * price
            # Calculate and apply tax
            tax_rate = planet.calculate_tax_rate(player_rank, revenue)
            tax_amount = revenue * tax_rate
            net_revenue = revenue - tax_amount
            
            self.money += net_revenue
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
        if item_name in self.items:
            self.items[item_name] += 1
        else:
            self.items[item_name] = 1

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
        self.research = Research()
        self.action = Action()

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

    def create_box(self, content, style='single'):
        term_width = shutil.get_terminal_size().columns
        width = term_width - 4  # Adjust for padding

        chars = {
            'single': {'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘', 'h': '─', 'v': '│'},
            'double': {'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝', 'h': '═', 'v': '║'},
            'round': {'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯', 'h': '─', 'v': '│'}
        }[style]

        lines = []
        lines.append(f"{chars['tl']}{chars['h'] * width}{chars['tr']}")

        # Determine the number of columns
        num_columns = len(content[0])
        col_widths = [max(len(str(cell)) for cell in col) for col in zip(*content)]

        for row in content:
            formatted_row = []
            for i, cell in enumerate(row):
                formatted_row.append(f"{str(cell):<{col_widths[i]}}")
            lines.append(f"{chars['v']} {'  '.join(formatted_row):<{width-2}} {chars['v']}")

        lines.append(f"{chars['bl']}{chars['h'] * width}{chars['br']}")
        return '\n'.join(lines)

    def create_turn_info_box(self, content, style='single'):
        term_width = shutil.get_terminal_size().columns
        styles = {
            'single': ('┌', '┐', '└', '┘', '─', '│', '├', '┤', '┬', '┴'),
            'double': ('╔', '╗', '╚', '╝', '═', '║', '╠', '╣', '╦', '╩'),
            'round': ('╭', '╮', '╰', '╯', '─', '│', '├', '┤', '┬', '┴')
        }
        tl, tr, bl, br, h, v, ml, mr, mt, mb = styles[style]

        # Calculate column widths based on content
        cols = len(content[0])
        col_widths = [max(len(str(cell)) + 2 for cell in col) for col in zip(*content)]

        # Use terminal width minus padding for margins
        total_width = term_width - 4

        # Distribute remaining width proportionally
        total_content_width = sum(col_widths)
        remaining_width = total_width - (cols + 1)  # Account for vertical borders
        if remaining_width > total_content_width:
            extra_per_col = (remaining_width - total_content_width) // cols
            col_widths = [w + extra_per_col for w in col_widths]

        def create_row(cells, widths, left, mid, right):
            row = left
            for i, (cell, width) in enumerate(zip(cells, widths)):
                row += f"{str(cell):^{width}}"
                row += right if i == len(cells) - 1 else mid
            return row

        # Create the box
        box = [create_row([h * w for w in col_widths], col_widths, tl, mt, tr)]
        for row in content:
            box.append(create_row(row, col_widths, v, v, v))
        box.append(create_row([h * w for w in col_widths], col_widths, bl, mb, br))

        return '\n'.join(box)

    def display_simple_message(self, message, pause=2, style='round', color=None):
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
        term_width = shutil.get_terminal_size().columns
        width = term_width - 4  # Adjust for padding

        chars = {
            'single': {'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘', 'h': '─', 'v': '│'},
            'double': {'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝', 'h': '═', 'v': '║'},
            'round': {'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯', 'h': '─', 'v': '│'}
        }[style]

        lines = []
        lines.append(f"{chars['tl']}{chars['h'] * width}{chars['tr']}")

        for row in content:
            wrapped_row = self.word_wrap(row, width - 2)
            for line in wrapped_row:
                lines.append(f"{chars['v']} {line:<{width-2}} {chars['v']}")

        lines.append(f"{chars['bl']}{chars['h'] * width}{chars['br']}")
        return '\n'.join(lines)

    def display_message(self, message, pause=2, style='round', color=None):
        if isinstance(message, list):
            box_content = message
        else:
            box_content = [message]

        box = self.create_box(box_content, style)
        if color:
            box = f"\033[{color}m{box}\033[0m"
        print(box)
        if pause > 0:
            time.sleep(pause)

    def validate_input(self, prompt, valid_options):
        term_width = shutil.get_terminal_size().columns

        while True:
            wrapped_prompt = self.word_wrap(prompt, term_width - 4)  # Account for padding
            self.display_simple_message(wrapped_prompt, 0)

            try:
                user_input = input(">>> ").strip().lower()
                if not user_input:
                    self.display_simple_message("Command cancelled.")
                    return None
                if user_input in valid_options:
                    return user_input
                self.display_simple_message(f"Invalid input, try: {', '.join(valid_options)}", 1)
            except KeyboardInterrupt:
                print(f"Do you want to exit? (yes/no):")
#                self.display_message("Do you want to exit? (yes/no)", 0)
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
                if user_input == 'max':
                    return 'max'
                quantity = int(user_input)
                if quantity > 0:
                    return quantity
                self.display_simple_message("Please enter a positive number or 'max'", 1)
            except ValueError:
                self.display_simple_message("Invalid input. Please enter a number or 'max'", 1)

    def validate_planet_input(self, prompt):
        while True:
            self.display_simple_message(prompt, 0)
            try:
                user_input = input(">>> ").strip().lower()
                if not user_input:
                    self.display_simple_message("Command cancelled.")
                    return None
                if user_input.isdigit():
                    index = int(user_input) - 1
                    if 0 <= index < len(self.known_planets):
                        return self.known_planets[index]
                for planet in self.planets:
                    if planet.name.lower() == user_input:
                        return planet.name
                self.display_simple_message(f"Invalid input. Valid options: {', '.join([planet.name for planet in self.planets])}", 1)
            except KeyboardInterrupt:
                print(f"Do you want to exit? (yes/no):")
#                self.display_message("Do you want to exit? (yes/no)", 0)
                confirm = input(">>> ").strip().lower()
                if confirm == 'yes':
                    self.display_simple_message("Goodbye!", 1)
                    exit()

    def calculate_quest_reward(self, base_reward):
        """Calculate quest reward based on rank and research"""
        multiplier = self.rank_multiplier()
        if 'advanced_trading' in self.research.unlocked_options:
            multiplier *= 1.2  # 20% bonus from research
        return int(base_reward * multiplier)

    def validate_price(self, commodity, price):
        """Validate if a price is reasonable for a commodity"""
        if commodity == 'salt':
            return 60 <= price <= 150
        elif commodity == 'fuel':
            return 120 <= price <= 250
        return True  # Default for other commodities

    def update_market_prices(self):
        """Update market prices with new logic"""
        for planet in self.planets:
            # Update basic commodities
            planet.update_market(self.difficulty)
            
            # Update mining commodities
            planet.produce_resources()
            
            # Apply market manipulation if researched
            if 'market_manipulation' in self.research.unlocked_options:
                for commodity in ['tech', 'agri', 'salt', 'fuel']:
                    if random.random() < 0.2:  # 20% chance for each commodity
                        self.action.manipulate_market(planet, commodity, self.research)

    def display_turn_info(self):
        self.clear_screen()
        status_content = [
            ["CΔRGΩ", "Ship", "Planet"],
            [f"Turn: {self.turn}", f"ATK: {self.ship.attack}", f"Name: {self.current_planet.name}"],
            [f"¤: {self.format_money(self.ship.money)}", f"DEF: {self.ship.defense}", f"Tech LVL: {self.current_planet.tech_level}"],
            [f"Tech: {self.format_money(self.ship.cargo['tech'])}", f"SPD: {self.ship.speed}", f"Agri LVL: {self.current_planet.agri_level}"],
            [f"Agri: {self.format_money(self.ship.cargo['agri'])}", f"DMG: {self.ship.damage}%", f"ECO: {self.current_planet.economy}"],
            [f"Salt: {self.format_money(self.ship.cargo['salt'])}", f"RP: {self.ship.research_points}", f"EFF: {self.current_planet.mining_efficiency}%"],
            [f"Fuel: {self.format_money(self.ship.cargo['fuel'])}", f"★: {self.rank}", f"NET: {len(self.current_planet.buildings)}"]
        ]

        status_box = self.create_box(status_content, 'double')
        print(status_box)

        # Market prices with banned commodities indicator
        tech_status = "BANNED" if 'tech' in self.current_planet.banned_commodities else str(self.format_money(self.current_planet.market['tech']))
        agri_status = "BANNED" if 'agri' in self.current_planet.banned_commodities else str(self.format_money(self.current_planet.market['agri']))
        salt_status = "BANNED" if 'salt' in self.current_planet.banned_commodities else str(self.format_money(self.current_planet.market['salt']))
        fuel_status = "BANNED" if 'fuel' in self.current_planet.banned_commodities else str(self.format_money(self.current_planet.market['fuel']))
        # Market content with two columns
        market_content = [
 #           ["Base Commodities", "Special Resources"],  # Header row with two columns
 #           ["-" * 20, "-" * 20],  # Separator line
            [f"Tech: {tech_status}", f"Salt: {salt_status if any(p['type'] == 'salt' for p in self.current_planet.mining_platforms) else 'No Platform'}"],
            [f"Agri: {agri_status}", f"Fuel: {fuel_status if any(p['type'] == 'fuel' for p in self.current_planet.mining_platforms) else 'No Platform'}"]
        ]

        # Add ban duration if any commodities are banned
        if self.current_planet.banned_commodities:
            market_content.append(["", ""])  # Empty line for spacing
            market_content.append(["Trade Bans:", "Duration:"])
            for commodity in self.current_planet.banned_commodities:
                duration = self.current_planet.ban_duration.get(commodity, "Permanent")
                market_content.append([f"{commodity.capitalize()}", f"{duration} turns"])
        print(self.create_box(market_content, 'single'))

        # Command menu with new options
        commands = [
            ["Commands: buy/b, sell/s, upgrade/u,"],
            ["travel/t, repair/r, info/i, build/bl,"],
            ["cantina/c, shop/sh, action/a, end/e"],
        ]
        print(self.create_box(commands, 'round'))

        # Display active effects
        if self.research.unlocked_options:
            effects = [["Active Research Effects"]]
            for research in self.research.unlocked_options:
                effects.append([f"- {research.replace('_', ' ').title()}"])
            print(self.create_box(effects, 'round'))

    def display_planet_info(self):
        # Ship section
        ship_info = [
            ["Ship Information"],
            [f"Attack: {self.ship.attack}"],
            [f"Defense: {self.ship.defense}"],
            [f"Speed: {self.ship.speed}"],
            [f"Hull Damage: {self.ship.damage}%"],
            [f"Money: {self.format_money(self.ship.money)}"],
            [f"Research Points: {self.ship.research_points}"],
            ["Cargo:"],
            [f"  Tech: {self.format_money(self.ship.cargo['tech'])}"],
            [f"  Agri: {self.format_money(self.ship.cargo['agri'])}"],
            [f"  Salt: {self.format_money(self.ship.cargo['salt'])}"],
            [f"  Fuel: {self.format_money(self.ship.cargo['fuel'])}"],
            ["Items:"]
        ]
        
        # Add items if any exist
        if self.ship.items:
            for item, count in self.ship.items.items():
                ship_info.append([f"  {item.capitalize()}: {count}"])
        else:
            ship_info.append(["  No items"])
        
        # Planet section
        planet_info = [
            ["Planet Information"],
            [f"Name: {self.current_planet.name}"],
            [f"Tech Level: {self.current_planet.tech_level}"],
            [f"Agri Level: {self.current_planet.agri_level}"],
            [f"Research Points: {self.current_planet.research_points}"],
            [f"Economy: {self.current_planet.economy}"],
            [f"Mining Efficiency: {self.current_planet.mining_efficiency}%"],
            ["Current Market:"],
            [f"  Tech: {self.format_money(self.current_planet.market['tech'])}"],
            [f"  Agri: {self.format_money(self.current_planet.market['agri'])}"],
            [f"  Salt: {self.format_money(self.current_planet.market['salt'])}"],
            [f"  Fuel: {self.format_money(self.current_planet.market['fuel'])}"]
        ]

        # Add banned commodities if any
        if self.current_planet.banned_commodities:
            planet_info.append(["Banned Commodities:"])
            for commodity in self.current_planet.banned_commodities:
                duration = self.current_planet.ban_duration.get(commodity, "Permanent")
                planet_info.append([f"  {commodity.capitalize()}: {duration} turns"])

        # Add buildings
        planet_info.append(["Buildings:"])
        if self.current_planet.buildings:
            building_counts = {}
            for building in self.current_planet.buildings:
                building_counts[building] = building_counts.get(building, 0) + 1
            for building, count in building_counts.items():
                planet_info.append([f"  {building} x{count}"])
        else:
            planet_info.append(["  No buildings"])

        # Add mining information
        planet_info.append(["Mining Operations:"])
        if self.current_planet.mining_platforms:
            for platform in self.current_planet.mining_platforms:
                planet_info.append([
                    f"  {platform['type'].capitalize()} Platform",
                    f"  (Efficiency: {platform['efficiency']}%",
                    f"  Capacity: {platform['capacity']})"
                ])
        else:
            planet_info.append(["  No mining platforms"])

        # Add mineral deposits if any
        if self.current_planet.mineral_deposits:
            planet_info.append(["Mineral Deposits:"])
            for deposit_type, amount in self.current_planet.mineral_deposits.items():
                planet_info.append([f"  {deposit_type.capitalize()}: {amount} units"])
        
        # Create content by combining ship and planet info
        content = []
        max_length = max(len(ship_info), len(planet_info))
        
        for i in range(max_length):
            ship_line = ship_info[i][0] if i < len(ship_info) else ""
            planet_line = planet_info[i][0] if i < len(planet_info) else ""
            content.append([ship_line, planet_line])

        print(self.create_box(content, 'double'))
        time.sleep(3)

    def build_mining_platform(self):
        """Build a new mining platform on the current planet"""
        if not self.current_planet.mineral_deposits:
            self.display_simple_message("No mineral deposits found! Use geoscan first.")
            return
            
        available_deposits = list(self.current_planet.mineral_deposits.keys())
        deposit_type = self.validate_input(
            f"Choose deposit type to mine ({', '.join(available_deposits)}): ",
            available_deposits
        )
        
        if deposit_type is None:
            return
            
        cost = 10000
        if self.ship.money >= cost:
            self.ship.money -= cost
            self.current_planet.mining_platforms.append({
                'type': deposit_type,
                'efficiency': self.current_planet.mining_efficiency,
                'capacity': random.randint(100, 200)
            })
            self.display_simple_message(f"Mining platform for {deposit_type} built!")
        else:
            self.display_simple_message("Not enough money to build mining platform.")

    def format_buildings(self):
        building_counts = {}
        for building in self.current_planet.buildings:
            if building in building_counts:
                building_counts[building] += 1
            else:
                building_counts[building] = 1
        return [f"{building} {count}" for building, count in building_counts.items()]

    def choose_difficulty(self):
        self.clear_screen()
        
        difficulty_info = [
            ["DIFFICULTY SELECTION"],
            ["  1. EASY"],
            ["     Lower risks, higher profits"],
            ["  2. NORMAL"],
            ["     Standard trading conditions"],
            ["  3. EXPERT"],
            ["     High risk, high reward"]
            
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

    def generate_planets(self):
        return [
            Planet("Alpha", 5, 3, 10, "Stable"),
            Planet("Beta", 2, 7, 15, "Booming"),
            Planet("Gamma", 8, 2, 20, "Declining"),
            Planet("Delta", 4, 6, 25, "Formative"),
            Planet("Epsilon", 7, 4, 30, "Stable")
        ]

    def get_player_name(self):
        self.clear_screen()
        
        title = [
            "╔════════ C Δ R G Ω ════════╗",
            "║    Space Trading Saga     ║",
            "╚═══════════════════════════╝"
        ]
        
        for line in title:
            print(line)
            time.sleep(0.1)

        self.display_simple_message([
            "Enter your pilot name",
            "Press Enter for random"
        ], 0)
        
        name = input(">>> ").strip()
        
        if not name:
            titles = ["Captain", "Commander", "Pilot", "Admiral"]
            surnames = ["Nova", "Drake", "Phoenix", "Wolf"]
            name = f"{random.choice(titles)} {random.choice(surnames)}"
            self.display_simple_message(f"Generated name: {name}")
        
        self.display_simple_message(f"Welcome aboard, {name}!")    
        return name

    def display_starting_info(self):
        planet_type = "industrial"
        if self.current_planet.agri_level > self.current_planet.tech_level:
            planet_type = "agricultural"
        elif self.current_planet.research_points > 15:
            planet_type = "research"

        intro_text = f"\n  Welcome {self.player_name} to {self.current_planet.name}, a boring {planet_type} outpost, where your adventure begins."
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

    def word_wrap(self, text, width=None):
        if width is None:
            term_width = shutil.get_terminal_size().columns
            width = term_width - 4  # Account for padding

        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + len(current_line) > width:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
            else:
                current_line.append(word)
                current_length += len(word)

        if current_line:
            lines.append(' '.join(current_line))

        return lines

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

    def display_character_message(self, character_name, message, pause=2, style='round', color=None):
        box_content = [f"{character_name}: {message}"]
        box = self.create_simple_box(box_content, style)
        if color:
            box = f"\033[{color}m{box}\033[0m"
        print(box)
        if pause > 0:
            time.sleep(pause)

    def clear_screen(self):
        os.system('clear' if os.name == 'posix' else 'cls')

    def play_turn(self):
            self.display_turn_info()

            valid_actions = [
                'buy', 'b', 'sell', 's', 'upgrade', 'u', 'travel', 't', 
                'repair', 'r', 'info', 'i', 'build', 'bl', 'cantina', 'c', 
                'shop', 'sh', 'action', 'a', 'mine', 'm', 'end', 'e',
                'quit', 'q', 'resign', 'rs'
            ]

            action = self.validate_input("Choose action: ", valid_actions)

            # Handle cancelled command
            if action is None:
                return

            elif action in ['buy', 'b']:
                item = self.validate_input("Choose item (tech/agri/salt/fuel): ", 
                                        ['tech', 'agri', 'salt', 'fuel'])
                if item is None:
                    return

                # Check if item can be traded
                if not self.current_planet.can_trade(item):
                    self.display_simple_message(f"Trading of {item} is banned on this planet!")
                    return

                # Check for mining platform requirement for salt and fuel
                if item in ['salt', 'fuel']:
                    has_platform = any(p['type'] == item for p in self.current_planet.mining_platforms)
                    if not has_platform:
                        self.display_simple_message(f"No mining platform for {item} on this planet.")
                        return

                quantity = self.validate_quantity_input("Enter quantity (or 'max' for maximum): ")
                if quantity is None:
                    return

                if quantity == 'max':
                    # Only calculate max if the item's price is non-zero
                    price = self.current_planet.market[item]
                    if price <= 0:
                        self.display_simple_message(f"Cannot calculate maximum: {item} has no valid price.")
                        return
                        
                    # Calculate tax rate for this transaction
                    tax_rate = self.current_planet.calculate_tax_rate(self.rank, price)
                    price_with_tax = price * (1 + tax_rate)
                    quantity = int(self.ship.money / price_with_tax)

                if self.ship.buy(item, quantity, self.current_planet.market[item], 
                                self.current_planet, self.rank):
                    self.display_simple_message(f"Bought {self.format_money(quantity)} {item}.")
                
            elif action in ['sell', 's']:
                item = self.validate_input("Choose item (tech/agri/salt/fuel): ", 
                                        ['tech', 'agri', 'salt', 'fuel'])
                if item is None:
                    return

                if not self.current_planet.can_trade(item):
                    self.display_simple_message(f"Trading of {item} is banned on this planet!")
                    return

                quantity = self.validate_quantity_input("Enter quantity (or 'max' for maximum): ")
                if quantity is None:
                    return

                if quantity == 'max':
                    quantity = self.ship.cargo[item]

                if self.ship.sell(item, quantity, self.current_planet.market[item], 
                                self.current_planet, self.rank):
                    self.display_simple_message(f"Sold {self.format_money(quantity)} {item}.")

            elif action in ['upgrade', 'u']:
                property_name = self.validate_input(
                    "Choose property to upgrade (attack/defense/speed): ", 
                    ['attack', 'defense', 'speed']
                )
                if property_name is None:
                    return

                cost = self.ship.upgrade_costs[property_name]
                if self.ship.upgrade(property_name, cost):
                    self.display_simple_message(f"Upgraded {property_name}.")
                    # Increase cost for next upgrade
                    self.ship.upgrade_costs[property_name] = int(cost * 1.5)

            elif action in ['travel', 't']:
                if "navcomp" in self.ship.items:
                    self.display_simple_message("Choose a planet to travel to:")
                    for i, planet in enumerate(self.known_planets):
                        print(f"{i+1}. {planet}")
                    choice = self.validate_planet_input(
                        "Enter the number of the planet or the planet name: "
                    )
                    if choice:
                        self.travel_to_planet(choice)
                else:
                    planet_name = input("Enter planet name to travel: ").strip()
                    if planet_name:
                        self.travel_to_planet(planet_name)

            elif action in ['repair', 'r']:
                cost = self.ship.damage * 10
                if self.ship.repair(cost):
                    self.display_simple_message("Ship repaired.")
                else:
                    self.display_simple_message(
                        f"Not enough money to repair. Cost: {self.format_money(cost)}"
                    )

            elif action in ['info', 'i']:
                self.display_planet_info()

            elif action in ['build', 'bl']:
                building_options = {
                    'stockmarket': ['stockmarket', 'sm'],
                    'permaculture': ['permaculture', 'pc'],
                    'organic': ['organic', 'oc'],
                    'agrobot': ['agrobot', 'ab'],
                    'nanotech': ['nanotech', 'nt'],
                    'neuroengineering': ['neuroengineering', 'ne'],
                    'mining': ['mining', 'm']
                }
                
                building_costs = {
                    'stockmarket': 5000,
                    'permaculture': 3000,
                    'organic': 4000,
                    'agrobot': 5000,
                    'nanotech': 6000,
                    'neuroengineering': 7000,
                    'mining': 10000
                }

                # Create the validation options list
                valid_options = []
                for options in building_options.values():
                    valid_options.extend(options)

                building_name = self.validate_input(
                    "Choose building type: ",
                    valid_options
                )
                if building_name is None:
                    return

                # Handle building construction
                self.handle_building_construction(building_name, building_options, building_costs)

            elif action in ['cantina', 'c']:
                self.visit_cantina()

            elif action in ['shop', 'sh']:
                self.shop()

            elif action in ['action', 'a']:
                self.handle_actions()

            elif action in ['mine', 'm']:
                self.handle_mining()

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

            elif action in ['end', 'e']:
                self.turn += 1
                self.random_event()
                return

            else:
                self.display_simple_message("Invalid action.")

    def handle_building_construction(self, building_name, building_options, building_costs):
            # Updated building costs dictionary
            building_costs = {
                'stockmarket': 5000,
                'permaculture': 3000,
                'organic': 4000,
                'agrobot': 5000,
                'nanotech': 6000,
                'neuroengineering': 7000,
                'mining': 10000  # Mining Facility cost
            }
            
            # Map short commands to full building names
            building_mapping = {
                'stockmarket': 'stockmarket',
                'sm': 'stockmarket',
                'permaculture': 'Permaculture Paradise',
                'pc': 'Permaculture Paradise',
                'organic': 'Organic Certification Authority',
                'oc': 'Organic Certification Authority',
                'agrobot': 'Agrobot Assembly Line',
                'ab': 'Agrobot Assembly Line',
                'nanotech': 'The Nanotech Nexus',
                'nt': 'The Nanotech Nexus',
                'neuroengineering': 'Neuroengineering Guild',
                'ne': 'Neuroengineering Guild',
                'mining': 'Mining Facility',
                'm': 'Mining Facility'
            }

            # Get the full building name
            full_building_name = building_mapping.get(building_name)
            
            if not full_building_name:
                self.display_simple_message("Invalid building type.")
                return
                
            # Handle special cases
            if full_building_name == 'stockmarket':
                if self.ship.money >= building_costs['stockmarket']:
                    self.ship.money -= building_costs['stockmarket']
                    self.current_planet.stockmarket_base = True
                    self.current_planet.market['tech'] = max(1, self.current_planet.market['tech'] - 10)
                    self.current_planet.market['agri'] = max(1, self.current_planet.market['agri'] - 5)
                    self.display_simple_message(f"Built stock market base for {self.format_money(building_costs['stockmarket'])} money.")
                else:
                    self.display_simple_message(f"Not enough money to build stock market. Cost: {self.format_money(building_costs['stockmarket'])}")
                return

            # Get base cost and multiplier
            base_cost = building_costs.get(building_name.split()[0].lower(), 3000)
            cost_multiplier = self.current_planet.buildings.count(full_building_name) + 1
            final_cost = base_cost * cost_multiplier

            # Build if player can afford it
            if self.ship.money >= final_cost:
                self.ship.money -= final_cost
                self.current_planet.build_building(full_building_name)
                self.display_simple_message(f"Built {full_building_name} for {self.format_money(final_cost)} money.")

    def travel_to_planet(self, planet_name):
        """Handle travel to a new planet with research points accumulation"""
        for planet in self.planets:
            if planet.name.lower() == planet_name.lower():
                old_planet = self.current_planet  # Store reference to previous planet
                self.current_planet = planet
                self.display_simple_message(f"Traveled to {planet.name}.")
                
                # Calculate research exchange based on planet differences
                research_difference = planet.research_points - old_planet.research_points
                
                # Base gain is the planet's research points if first visit
                if planet.name not in self.known_planets:
                    base_research = planet.research_points
                    self.known_planets.append(planet.name)
                else:
                    # For revisits, only get bonus from research difference if positive
                    base_research = max(0, research_difference)

                # Apply bonus based on research difference
                if research_difference > 0:
                    # Traveling to more advanced planet - get bonus
                    research_bonus = int(research_difference * 0.2)  # 20% of the difference
                else:
                    # Traveling to less advanced planet - smaller bonus
                    research_bonus = int(abs(research_difference) * 0.1)  # 10% of the difference
                
                # Apply rank multiplier to the bonus
                rank_multiplier = {
                    "Explorer": 1,
                    "Pilot": 1.2,
                    "Captain": 1.5,
                    "Commander": 1.8,
                    "Star Commander": 2.2,
                    "Space Admiral": 2.5,
                    "Stellar Hero": 3.0,
                    "Galactic Legend": 3.5
                }
                
                # Calculate final research gain
                total_gain = base_research + max(1, int(research_bonus * rank_multiplier.get(self.rank, 1) * (1 + self.difficulty)))
                
                # Add research points to the ship
                self.ship.research_points += total_gain
                
                # Display informative message about research gain
                if planet.name not in self.known_planets:
                    self.display_simple_message(f"Gained {total_gain} research points from discovering new planet!")
                elif research_difference > 0:
                    self.display_simple_message(f"Gained {total_gain} research points from studying advanced technology!")
                else:
                    self.display_simple_message(f"Gained {total_gain} research points from comparative analysis!")
                
                self.turn += 1
                self.random_event()
                return True
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
            'manipulate': f"Manipulate market (Cost: {self.action.action_costs['market_manipulation']} RP)",
            'status': "View research status",
            'back': "Return to main menu"
        }

        # Display available actions
        action_content = [["Available Actions:", "Cost/Description"]]
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
                'advanced_trading': "Reduces trade taxes",
                'improved_scanning': "Increases scout success rate",
                'geological_survey': "Improves mining efficiency",
                'political_influence': "Increases revolution success rate",
                'mining_efficiency': "Increases mining output",
                'market_manipulation': "Allows market price manipulation"
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
                    success, message = self.action.research(self.current_planet, option, self.research)
                    self.display_simple_message(message)
                else:
                    self.display_simple_message(f"Not enough research points! Need: {self.research.research_costs[option]}")
                
        elif action == 'scout':
            if self.ship.research_points >= self.action.action_costs['scout']:
                self.ship.research_points -= self.action.action_costs['scout']
                success, type_, value, message = self.action.scout_area(self.current_planet, self.research)
                self.display_simple_message(message)
                
                if success:
                    if type_ == 'item':
                        self.ship.acquire_item(value)
                        self.display_simple_message(f"Item added to inventory!")
                    else:
                        self.current_planet.market[type_] += value
                        self.display_simple_message(f"Resources added to market!")
            else:
                self.display_simple_message(f"Not enough research points! Need: {self.action.action_costs['scout']}")
                
        elif action == 'geoscan':
            if self.ship.research_points >= self.action.action_costs['geoscan']:
                self.ship.research_points -= self.action.action_costs['geoscan']
                success, deposit_type, amount, message = self.action.geoscan(self.current_planet, self.research)
                self.display_simple_message(message)
                
                if success:
                    self.display_simple_message(f"Use 'build mining' command to exploit the deposit.")
            else:
                self.display_simple_message(f"Not enough research points! Need: {self.action.action_costs['geoscan']}")
                
        elif action == 'revolution':
            if self.ship.research_points >= self.action.action_costs['revolution']:
                self.ship.research_points -= self.action.action_costs['revolution']
                success, new_economy, message = self.action.incite_revolution(self.current_planet, self.research)
                self.display_simple_message(message)
            else:
                self.display_simple_message(f"Not enough research points! Need: {self.action.action_costs['revolution']}")
                
        elif action == 'manipulate':
            if 'market_manipulation' not in self.research.unlocked_options:
                self.display_simple_message("Market manipulation research required!")
                return
                
            if self.ship.research_points >= self.action.action_costs['market_manipulation']:
                # Show current market prices
                market_content = [["Commodity", "Current Price"]]
                for commodity in ['tech', 'agri', 'salt', 'fuel']:
                    if commodity not in self.current_planet.banned_commodities:
                        market_content.append([commodity.capitalize(), 
                                        str(self.format_money(self.current_planet.market[commodity]))])
                print(self.create_box(market_content, 'single'))
                
                commodity = self.validate_input(
                    "Choose commodity to manipulate (tech/agri/salt/fuel): ",
                    ['tech', 'agri', 'salt', 'fuel']
                )
                
                if commodity:
                    self.ship.research_points -= self.action.action_costs['market_manipulation']
                    success, price_change, message = self.action.manipulate_market(
                        self.current_planet, commodity, self.research
                    )
                    self.display_simple_message(message)
            else:
                self.display_simple_message(f"Not enough research points! Need: {self.action.action_costs['market_manipulation']}")
                    
        # Update production cooldowns after any action
        for resource_type in list(self.current_planet.production_cooldown.keys()):
            if self.current_planet.production_cooldown[resource_type] > 0:
                self.current_planet.production_cooldown[resource_type] -= 1

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
        
    def get_research_benefit_description(self, research):
        """Get description of research benefit"""
        benefits = {
            'advanced_trading': "Trading tax reduced by 2%",
            'improved_scanning': "Scout success +20%",
            'geological_survey': "Mining efficiency +15%",
            'political_influence': "Revolution success +20%",
            'mining_efficiency': "Mining output +25%",
            'market_manipulation': "Price control ±10%"
        }
        return benefits.get(research, "Unknown benefit")


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
            "Gravitational anomaly!",
            "Guerilla Militia Patrol attacking!",
            "Rogue Warship attacking!",
            "Camouflaged Asteroid Base attacking!"
            "Trade embargo!",
            "Resource shortage!",
            "Market manipulation!"
        ]
        event = random.choice(events)
        self.event_log.append({'turn': self.turn, 'event': event})

        if event == "Pirate attack!":
            if "turrets" in self.ship.items and random.random() < 0.35:
                self.display_simple_message("Event! Pirate attack repelled by laser turrets!", 3, color='32')
            else:
                self.ship.damage += min(random.randint(10, 25) * (1 + self.difficulty), 49)
                if self.ship.money > 0:
                    # Fix: Convert money to integer before using randint
                    stolen_money = random.randint(1, max(1, int(self.ship.money // 2)))
                    self.ship.money -= stolen_money
                    self.display_simple_message(f"Event! Pirates stole {self.format_money(stolen_money)} money and caused {self.ship.damage}% damage.", 3, color='31')
                else:
                    self.display_simple_message(f"Event! Pirates caused {self.ship.damage}% damage.", 3, color='31')
        elif event == "Market crash!":
            self.current_planet.update_market(self.difficulty)
            self.display_simple_message("Event! Market prices have changed.", 3, color='31')
        elif event == "Technological breakthrough!":
            self.current_planet.tech_level += 1
            self.display_simple_message("Event! Technological breakthrough! Tech level increased.", 3, color='32')
        elif event == "Exotic radiation!":
            destroyed_tech = random.randint(1, max(1, int(self.ship.cargo['tech'])))
            self.ship.cargo['tech'] = max(0, self.ship.cargo['tech'] - destroyed_tech)
            self.display_simple_message(f"Event! Exotic radiation destroyed {self.format_money(destroyed_tech)} tech goods.", 3, color='31')
        elif event == "Contamination!":
            destroyed_agri = random.randint(1, max(1, int(self.ship.cargo['agri'])))
            self.ship.cargo['agri'] = max(0, self.ship.cargo['agri'] - destroyed_agri)
            self.display_simple_message(f"Event! Contamination destroyed {self.format_money(destroyed_agri)} agri goods.", 3, color='31')
        elif event == "Cargo bay hit by asteroid!":
            self.ship.damage += min(random.randint(5, 15) * (1 + self.difficulty), 49)
            total_cargo = int(self.ship.cargo['tech']) + int(self.ship.cargo['agri'])
            destroyed_cargo = random.randint(1, max(1, total_cargo // 2))
            self.ship.cargo['tech'] = max(0, self.ship.cargo['tech'] - destroyed_cargo // 2)
            self.ship.cargo['agri'] = max(0, self.ship.cargo['agri'] - destroyed_cargo // 2)
            self.display_simple_message(f"Event! Asteroid hit destroyed {self.format_money(destroyed_cargo)} units of cargo and caused {self.ship.damage}% damage.", 3, color='31')
        elif event == "Cargo bay raided by guerrilla!":
            total_cargo = int(self.ship.cargo['tech']) + int(self.ship.cargo['agri'])
            stolen_cargo = random.randint(1, max(1, total_cargo // 2))
            self.ship.cargo['tech'] = max(0, self.ship.cargo['tech'] - stolen_cargo // 2)
            self.ship.cargo['agri'] = max(0, self.ship.cargo['agri'] - stolen_cargo // 2)
            self.display_simple_message(f"Event! Guerrilla raid stole {self.format_money(stolen_cargo)} units of cargo.", 3, color='31')
        elif event == "Spacetime rift!":
            self.ship.damage += min(random.randint(15, 35) * (1 + self.difficulty), 49)
            self.display_simple_message(f"Event! Spacetime rift caused {self.ship.damage}% damage.", 3, color='31')
        elif event == "Rogue Corsair attacking!":
            self.battle_event(2, 1, 1)
        elif event == "Pirate mothership attacking!":
            self.battle_event(5, 5, 5)
        elif event == "Gravitational anomaly!":
            self.gravitational_anomaly_event()
        elif event == "Guerilla Militia Patrol attacking!":
            self.battle_event(3, 2, 2)
        elif event == "Rogue Warship attacking!":
            self.battle_event(4, 3, 3)
        elif event == "Camouflaged Asteroid Base attacking!":
            self.battle_event(6, 4, 4)
        # Handle new events
        elif event == "Trade embargo!":
            commodity = random.choice(['tech', 'agri'])
            duration = random.randint(2, 4)
            self.current_planet.add_temporary_ban(commodity, duration)
            self.display_simple_message(f"Event! {commodity} trading banned for {duration} turns!", 3, color='31')
            
        elif event == "Resource shortage!":
            commodity = random.choice(['tech', 'agri'])
            self.current_planet.market[commodity] = 0
            self.current_planet.banned_commodities.append(commodity)
            self.display_simple_message(f"Event! {commodity} shortage! Trading banned until prices recover.", 3, color='31')
            
        elif event == "Market manipulation!":
            commodity = random.choice(['tech', 'agri'])
            price_multiplier = random.uniform(1.5, 3.0)
            self.current_planet.market[commodity] *= price_multiplier
            self.display_simple_message(f"Event! {commodity} prices manipulated!", 3, color='31')


        if "shield" in self.ship.items:
            self.ship.damage = max(0, self.ship.damage - 5)

    def gravitational_anomaly_event(self):
        print("You have encountered a gravitational anomaly!")
        outcome = random.choice(["rare elements", "scientific samples"])
        if outcome == "rare elements":
            tech_goods = random.randint(5, 15)
            self.ship.cargo['tech'] += tech_goods
            self.display_simple_message(f"You found {self.format_money(tech_goods)} tech goods.", 3, color='32')
        elif outcome == "scientific samples":
            research_points = random.randint(5, 15)
            self.ship.research_points+= research_points
            self.display_simple_message(f"You gained {self.format_money(research_points)} research points.", 3, color='32')

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
            print("You lost the battle!")
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

    def visit_cantina(self):
        self.display_simple_message("Welcome to the Cantina!", 1)

        action = self.validate_input(
            "Choose action (buy map/bm, update map/um, listen to gossip/lg, quests/q): ",
            ['buy map', 'bm', 'update map', 'um', 'listen to gossip', 'lg', 'quests', 'q']
        )

        if action is None:
            return

        if action in ['buy map', 'bm']:
            if self.ship.money >= 200:
                self.ship.money -= 200
                self.display_simple_message("You bought a map! Here are some new planet names and levels:", 1)
                for planet in self.planets:
                    if planet.name not in self.known_planets:
                        self.known_planets.append(planet.name)
                        print(f"{planet.name} (Tech: {planet.tech_level}, Agri: {planet.agri_level})")
            else:
                self.display_simple_message("Not enough money to buy a map.")
        elif action in ['update map', 'um']:
            if self.ship.money >= 350:
                self.ship.money -= 350
                self.display_simple_message("You updated the map! Here are the commodities wanted:", 1)
                for planet in self.planets:
                    print(f"{planet.name}: Tech - {self.format_money(planet.market['tech'])}, Agri - {self.format_money(planet.market['agri'])}")
            else:
                self.display_simple_message("Not enough money to update the map.")
        elif action in ['listen to gossip', 'lg']:
            if self.ship.money >= 150:
                self.ship.money -= 150
                self.display_simple_message("You listened to gossip! Here are some tips:", 1)
                for planet in self.planets:
                    if planet.market['tech'] < 50:
                        print(f"Cheap tech goods available on {planet.name}.")
                    if planet.market['agri'] < 30:
                        print(f"Cheap agri goods available on {planet.name}.")
                    if planet.market['tech'] > 100:
                        print(f"High price on tech goods on {planet.name}.")
                    if planet.market['agri'] > 80:
                        print(f"High price on agri goods on {planet.name}.")
                if random.random() < 0.3:  # 30% chance to get a quest
                    quest = random.choice([
                        ("Deliver 10 tech goods to Alpha", "tech", 10, 500),
                        ("Deliver 15 agri goods to Beta", "agri", 15, 700),
                        ("Deliver 20 tech goods to Gamma", "tech", 20, 1000),
                        ("Deliver 25 agri goods to Delta", "agri", 25, 1200),
                        ("Rescue mission to Epsilon", "rescue", 0, 1500),
                        ("Mining asteroid intel to Zeta", "mining", 0, 2000),
                        ("Eliminate Guerilla Militia Patrol", "guerilla", 0, 1800),
                        ("Eliminate Rogue Warship", "rogue", 0, 2200),
                        ("Eliminate Camouflaged Asteroid Base", "asteroid", 0, 2500)
                    ])
                    self.ship.add_quest(quest)
                    self.display_simple_message(f"You received a quest: {quest[0]}")
                    self.display_simple_message(f"Reward: {self.format_money(quest[3])} money")
            else:
                self.display_simple_message("Not enough money to listen to gossip.")
        elif action in ['quests', 'q']:
            if self.ship.quests:
                self.display_simple_message("Active Quests:")
                for quest in self.ship.quests:
                    print(f"- {quest[0]}")
            else:
                self.display_simple_message("No active quests.")

        # Randomly introduce a demo character after reaching a new rank
        if random.random() < 0.1:  # 10% chance
            self.display_character_message("Mysterious Stranger", "Greetings, traveler. I hear you've been making a name for yourself. Keep it up, and you might just become a legend.")

        time.sleep(3)  # Pause to let the player read the information

    def shop(self):
        self.display_simple_message("Welcome to the Shop!", 1)
        available_items = random.sample([
            ("navcomp", 500),
            ("scanner", 700),
            ("probe", 900),
            ("turrets", 1200),
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
                    self.display_simple_message(f"You bought a {item}.")
                else:
                    self.display_simple_message("Not enough money to buy this item.")
                return

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
            if self.action.research(self.current_planet, 'mining_efficiency', self.research):
                self.display_simple_message("Mining efficiency research completed!")
            else:
                self.display_simple_message("Not enough research points!")

    def display_mining_status(self):
        """Display mining operations status"""
        content = [
            ["Mining Status"],
            [f"Planet Efficiency: {self.current_planet.mining_efficiency}%"],
            ["Active Platforms:"]
        ]
        
        for platform in self.current_planet.mining_platforms:
            content.append([
                f"{platform['type'].capitalize()}: "
                f"Efficiency {platform['efficiency']}% "
                f"Capacity {platform['capacity']}"
            ])
            
        if self.current_planet.mineral_deposits:
            content.append(["Available Deposits:"])
            for deposit, amount in self.current_planet.mineral_deposits.items():
                content.append([f"{deposit.capitalize()}: {amount} units"])
                
        print(self.create_box(content, 'double'))

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
            ["─" * 25, "─" * 25],  # Separator
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
                    self.display_simple_message("You have chosen to continue your adventure into the unknown.")
                    self.stellar_portal_available = True
                    if self.ship.money >= 1500:
                        self.ship.money -= 1500
                        self.display_simple_message("You have paid for the secret quest and a Stellar Portal appears on this planet.")
                        self.planets = self.generate_new_planets()
                        self.current_planet = random.choice(self.planets)
                        self.known_planets = [self.current_planet.name]
                        self.display_simple_message("You have traveled to a new set of planets with more volatile price movements.")
                    else:
                        self.display_simple_message("Not enough money to pay for the secret quest.")

        # Ask to play again
        play_again = self.validate_input("Do you want to play again? (yes/no): ", ['yes', 'no'])
        if play_again == 'yes':
            self.__init__()
            self.play()

    def generate_new_planets(self):
        return [
            Planet("Zeta", 10, 1, 5, "Stable"),
            Planet("Eta", 1, 10, 5, "Booming"),
            Planet("Theta", 8, 8, 10, "Declining"),
            Planet("Iota", 5, 5, 15, "Formative"),
            Planet("Kappa", 3, 3, 20, "Stable")
        ]

    def clear_screen(self):
        os.system('clear' if os.name == 'posix' else 'cls')

# Start the game
if __name__ == "__main__":
    game = Game()
    game.play()
