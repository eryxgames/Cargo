import random
import os
import time
import shutil
from math import floor
# Define your logo data ONCE, at the module level:
logo_data = [
    "╔════════ C Δ R G Ω ════════╗",
    "║     Space Trading Saga    ║",
    "╚═══════════════════════════╝"
]

def display_logo(logo, centered=True):
    """Displays the logo, optionally centered."""
    try:
        terminal_width = os.get_terminal_size().columns
    except OSError:
        terminal_width = 80  # Default if not in a terminal

    for line in logo:
        if centered:
            padding = (terminal_width - len(line)) // 2
            print(" " * padding + line)
        else:
            print(line)  # Just print without centering

def print_centered_text(text):
    try:
        terminal_width = os.get_terminal_size().columns
    except OSError:
        terminal_width = 80  # Default if not in a terminal
    print(text.center(terminal_width))

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
        self.exogeology = random.randint(60, 100)  # New: affects mining output
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
        efficiency_bonus = self.exogeology / 100
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
                    'efficiency': self.exogeology,
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
        if not self.current_location.mineral_deposits:
            self.display_simple_message("No mineral deposits found! Use geoscan first.")
            return
            
        available_deposits = list(self.current_location.mineral_deposits.keys())
        deposit_type = self.validate_input(
            f"Choose deposit type to mine ({', '.join(available_deposits)}): ",
            available_deposits
        )
        
        cost = 10000
        if self.ship.money >= cost:
            self.ship.money -= cost
            self.current_location.mining_platforms.append({
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


    def __str__(self):
        return f"{self.name} (Tech: {self.tech_level}, Agri: {self.agri_level}, RP: {self.research_points}, Economy: {self.economy})"

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
    def __init__(self):
        self.cargo = {'tech': 0, 'agri': 0, 'salt': 0, 'fuel': 0}
        self.money = 1000
        self.damage = 0
        self.upgrades = []
        self.items = {}
        self.attack = 1
        self.defense = 1
        self.speed = 1
        self.research_points = 0
        self.upgrade_costs = {
            'attack': 2000,
            'defense': 2000,
            'speed': 2000
        }
        self.item_purchase_count = {}
        self.combat_victories = 0
        self.combat_defeats = 0
        self.combat_stats = {
            'pirates_defeated': 0,
            'raiders_defeated': 0,
            'militia_defeated': 0
        }
        self.trade_profits = {}
        self.enemy_victories = {
            'pirate': 0,
            'raider': 0,
            'militia': 0,
            'alien': 0
        }

    def record_combat_victory(self, enemy_type=None):
        self.combat_victories += 1
        if enemy_type and enemy_type in self.enemy_victories:
            self.enemy_victories[enemy_type] += 1
            stat_key = f'{enemy_type}s_defeated'
            if stat_key in self.combat_stats:
                self.combat_stats[stat_key] += 1

    def record_combat_defeat(self, enemy_type=None):
        self.combat_defeats += 1
        if enemy_type and enemy_type in self.enemy_victories:
            if 'defeats_by_type' not in self.combat_stats:
                self.combat_stats['defeats_by_type'] = {}
            if enemy_type not in self.combat_stats['defeats_by_type']:
                self.combat_stats['defeats_by_type'][enemy_type] = 0
            self.combat_stats['defeats_by_type'][enemy_type] += 1

    def buy(self, item, quantity, price, planet, player_rank):
        # Quest-related information can be tracked here and passed to QuestSystem
        if not planet.can_trade(item):
            return False

        if item in ['salt', 'fuel']:
            has_platform = any(p['type'] == item for p in planet.mining_platforms)
            if not has_platform:
                return False

        cost = quantity * price
        if self.money >= cost:
            tax_rate = planet.calculate_tax_rate(player_rank, cost)
            tax_amount = cost * tax_rate
            total_cost = cost + tax_amount
            
            if self.money >= total_cost:
                self.money -= total_cost
                self.cargo[item] += quantity
                return True
            return False
        return False

    def sell(self, item, quantity, price, planet, player_rank):
        if not planet.can_trade(item):
            return False

        if item in ['salt', 'fuel']:
            has_platform = any(p['type'] == item for p in planet.mining_platforms)
            if not has_platform:
                return False
                
        if self.cargo[item] >= quantity:
            revenue = quantity * price
            tax_rate = planet.calculate_tax_rate(player_rank, revenue)
            tax_amount = revenue * tax_rate
            net_revenue = revenue - tax_amount
            
            self.money += net_revenue
            self.cargo[item] -= quantity
            
            # Track trade profits
            if item not in self.trade_profits:
                self.trade_profits[item] = 0
            self.trade_profits[item] += net_revenue
            
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

# Define the Game class
class Game:
    def __init__(self):
        self.term_width = self.get_terminal_width()
        self.term_height = self.get_terminal_height()
        self.difficulty = self.choose_difficulty()
        self.locations = self.generate_initial_locations()  # Generate all locations
        self.current_location = random.choice([loc for loc in self.locations if isinstance(loc, Planet)])  # Start at a planet
        self.shop = Shop()  # Initialize the shop system
        self.ship = Ship()
        self.turn = 0
        self.known_locations = [self.current_location.name]  
        self.event_log = []
        self.player_name = self.get_player_name()
        self.rank = "Explorer"
        self.reputation = 0
        self.story_manager = StoryManager(self)
        self.quest_system = QuestSystem(self)
        self.unlocked_location_types = {"Planet"}
        self.location_manager = LocationManager(self)
        self.display_starting_info()
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
                    Location("Alien Outpost X", "Alien Outpost", 20, 5, 100, "Unknown"),
                    Location("Alien Outpost Y", "Alien Outpost", 25, 5, 120, "Unknown")
                ]
            }
        }
        
        # Initialize unlocked locations tracking
        self.unlocked_location_types = {"Planet"}  # Start with only regular planets
        self.discovered_locations = set()  # Track which specific locations player has found
        
        return initial_locations

    def create_box(self, content, style='single'):
        """Create a box that expands to terminal width consistently with validate_input width."""
        # Get terminal width, subtracting exactly the same as word_wrap
        term_width = shutil.get_terminal_size().columns - 4  # Match word_wrap padding exactly
        
        # Define box characters
        chars = {
            'single': {'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘', 'h': '─', 'v': '│', 'sep': '│'},
            'double': {'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝', 'h': '═', 'v': '║', 'sep': '║'},
            'round': {'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯', 'h': '─', 'v': '│', 'sep': '│'}
        }[style]

        # Calculate number of columns
        num_cols = max(len(row) for row in content)
        max_lengths = [0] * num_cols
        
        # Get maximum content length for each column
        for row in content:
            for i, cell in enumerate(row):
                if i < num_cols:
                    max_lengths[i] = max(max_lengths[i], len(str(cell)))

        # Calculate spacing requirements
        separator_space = 3  # Space for " │ " between columns
        total_separator_width = separator_space * (num_cols - 1)
        
        # Calculate available space for content
        available_content_width = term_width - total_separator_width

        # Calculate proportional column widths
        total_content_length = sum(max_lengths)
        col_widths = []
        remaining_width = available_content_width
        
        for i in range(num_cols):
            if i == num_cols - 1:
                # Last column gets remaining width
                width = remaining_width
            else:
                # Calculate proportional width based on content length
                proportion = max_lengths[i] / total_content_length
                width = max(3, min(
                    int(available_content_width * proportion),
                    max_lengths[i] + 2
                ))
                remaining_width -= width
            col_widths.append(width)

        # Ensure minimum widths
        for i in range(num_cols):
            col_widths[i] = max(3, min(col_widths[i], max_lengths[i] + 10))

        # Create the box
        lines = []
        
        # Calculate the exact width used in word_wrap
        horizontal_width = term_width
        
        # Top border
        lines.append(f"{chars['tl']}{chars['h'] * horizontal_width}{chars['tr']}")
        
        # Content rows
        for row in content:
            # Pad row with empty strings if necessary
            padded_row = row + [''] * (num_cols - len(row))
            
            # Format each cell
            formatted_cells = []
            for i, cell in enumerate(padded_row):
                cell_str = str(cell)
                if len(cell_str) > col_widths[i]:
                    cell_str = cell_str[:col_widths[i]-3] + "..."
                formatted_cells.append(f"{cell_str:<{col_widths[i]}}")
            
            # Join cells with separators and ensure total width matches
            row_content = f" {(' ' + chars['sep'] + ' ').join(formatted_cells)}"
            # Pad to match exact width if needed
            padding_needed = horizontal_width - len(row_content)
            if padding_needed > 0:
                row_content += ' ' * padding_needed
            row_str = f"{chars['v']}{row_content}{chars['v']}"
            lines.append(row_str)
        
        # Bottom border
        lines.append(f"{chars['bl']}{chars['h'] * horizontal_width}{chars['br']}")
        
        return '\n'.join(lines)

    def create_wide_box(self, content, style='single'):
        """Create a box that expands to terminal width with proportionally sized columns."""
        # Get terminal width and account for borders and spacing
        term_width = shutil.get_terminal_size().columns
        usable_width = term_width - 4  # Account for borders and minimum spacing
        
        # Define box characters
        chars = {
            'single': {'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘', 'h': '─', 'v': '│', 'sep': '│'},
            'double': {'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝', 'h': '═', 'v': '║', 'sep': '║'},
            'round': {'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯', 'h': '─', 'v': '│', 'sep': '│'}
        }[style]

        # Calculate number of columns and get content lengths
        num_cols = max(len(row) for row in content)
        max_lengths = [0] * num_cols
        
        # Get maximum content length for each column
        for row in content:
            for i, cell in enumerate(row):
                if i < num_cols:
                    max_lengths[i] = max(max_lengths[i], len(str(cell)))

        # Calculate spacing requirements
        separator_space = 3  # Space for " │ " between columns
        total_separator_width = separator_space * (num_cols - 1)
        padding_width = 2  # Space for padding around content " x "
        
        # Calculate available space for content
        available_content_width = usable_width - total_separator_width - padding_width
        
        # Calculate proportional column widths
        total_content_length = sum(max_lengths)
        col_widths = []
        remaining_width = available_content_width
        
        for i in range(num_cols):
            if i == num_cols - 1:
                # Last column gets remaining width
                width = remaining_width
            else:
                # Calculate proportional width
                proportion = max_lengths[i] / total_content_length
                width = max(3, min(
                    int(available_content_width * proportion),
                    max_lengths[i] + 2
                ))
                remaining_width -= width
            col_widths.append(width)

        # Ensure minimum widths and adjust if necessary
        for i in range(num_cols):
            col_widths[i] = max(3, min(col_widths[i], max_lengths[i] + 10))

        # Calculate final horizontal width
        horizontal_width = sum(col_widths) + total_separator_width + padding_width

        # Create the box
        lines = []
        
        # Top border
        lines.append(f"{chars['tl']}{chars['h'] * horizontal_width}{chars['tr']}")
        
        # Content rows
        for row in content:
            # Pad row with empty strings if necessary
            padded_row = row + [''] * (num_cols - len(row))
            
            # Format each cell
            formatted_cells = []
            for i, cell in enumerate(padded_row):
                cell_str = str(cell)
                if len(cell_str) > col_widths[i]:
                    cell_str = cell_str[:col_widths[i]-3] + "..."
                formatted_cells.append(f"{cell_str:<{col_widths[i]}}")
            
            # Join cells with separators
            row_str = f"{chars['v']} {(' ' + chars['sep'] + ' ').join(formatted_cells)} {chars['v']}"
            lines.append(row_str)
        
        # Bottom border
        lines.append(f"{chars['bl']}{chars['h'] * horizontal_width}{chars['br']}")
        
        return '\n'.join(lines)

    def create_compact_box(self, content, style='single'):
        """Create a box with properly aligned borders and content."""
        # Get terminal width and account for borders and spacing
        term_width = shutil.get_terminal_size().columns
        max_width = term_width - 4  # Account for left and right borders and minimum spacing
        
        # Define box characters
        chars = {
            'single': {'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘', 'h': '─', 'v': '│', 'sep': '│'},
            'double': {'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝', 'h': '═', 'v': '║', 'sep': '║'},
            'round': {'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯', 'h': '─', 'v': '│', 'sep': '│'}
        }[style]

        # Calculate number of columns and maximum width for each
        num_cols = max(len(row) for row in content)
        col_widths = [0] * num_cols
        
        # First pass: get maximum width needed for each column
        for row in content:
            for i, cell in enumerate(row):
                if i < num_cols:
                    col_widths[i] = max(col_widths[i], len(str(cell)))

        # Calculate spacing components
        separator_space = 3  # Space for " │ " between columns
        total_separators_width = separator_space * (num_cols - 1)
        content_width = sum(col_widths)

        # Calculate total width including all spacing
        total_width = content_width + total_separators_width + 2  # +2 for single space padding on each side

        # If total width exceeds max_width, reduce column widths proportionally
        if total_width > max_width:
            excess = total_width - max_width
            # Distribute reduction across columns
            for i in range(num_cols):
                reduction = int(excess * (col_widths[i] / content_width))
                col_widths[i] = max(3, col_widths[i] - reduction)  # Ensure minimum width of 3
                content_width = sum(col_widths)  # Recalculate content width after reduction

        # Calculate final width for horizontal borders (should match content row width)
        horizontal_width = content_width + total_separators_width + 2  # +2 for spaces next to borders

        # Create the box
        lines = []
        
        # Top border
        lines.append(f"{chars['tl']}{chars['h'] * horizontal_width}{chars['tr']}")
        
        # Content rows
        for row in content:
            # Pad row with empty strings if necessary
            padded_row = row + [''] * (num_cols - len(row))
            
            # Format each cell
            formatted_cells = []
            for i, cell in enumerate(padded_row):
                cell_str = str(cell)
                if len(cell_str) > col_widths[i]:
                    cell_str = cell_str[:col_widths[i]-3] + "..."
                formatted_cells.append(f"{cell_str:<{col_widths[i]}}")
            
            # Join cells with separators
            row_str = f"{chars['v']} {(' ' + chars['sep'] + ' ').join(formatted_cells)} {chars['v']}"
            lines.append(row_str)
        
        # Bottom border
        lines.append(f"{chars['bl']}{chars['h'] * horizontal_width}{chars['br']}")
        
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

    # For buy map display in visit_cantina:
    def format_map_content(self, new_locations):
        map_content = []
        # Header - keep it minimal
        map_content.append(["Location", "Type", "T", "A", "Features"])
        
        # Location data
        for location in new_locations:
            features = []
            if location.mining_platforms:
                features.append("M")  # Mining
            if location.buildings:
                features.append("B")  # Buildings
            if location.stockmarket_base:
                features.append("S")  # Stock Market
            
            map_content.append([
                location.name[:15],  # Limit name length
                location.location_type[:10],  # Abbreviate type
                str(location.tech_level),
                str(location.agri_level),
                "/".join(features) if features else "-"
            ])
        
        return map_content

    # For update map display in visit_cantina:
    def format_market_content(self, locations):
        market_content = []
        # Header - keep it compact
        market_content.append(["Location", "Tech", "Agri", "S/F", "Features"])
        
        for location in locations:
            # Format prices compactly
            tech_price = "BAN" if 'tech' in location.banned_commodities else self.format_money(location.market['tech'])
            agri_price = "BAN" if 'agri' in location.banned_commodities else self.format_money(location.market['agri'])
            
            # Combine salt/fuel status
            mining_status = []
            if any(p['type'] == 'salt' for p in location.mining_platforms):
                mining_status.append("S")
            if any(p['type'] == 'fuel' for p in location.mining_platforms):
                mining_status.append("F")
            mining_str = "/".join(mining_status) if mining_status else "-"
            
            # Combine features into compact format
            features = []
            if location.stockmarket_base:
                features.append("S")
            if location.buildings:
                features.append(f"B:{len(location.buildings)}")
            if location.mining_platforms:
                features.append(f"M:{len(location.mining_platforms)}")
            
            market_content.append([
                location.name[:15],  # Limit name length
                tech_price,
                agri_price,
                mining_str,
                "/".join(features) if features else "-"
            ])
        
        return market_content

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
        if 'xenoeconomy' in self.research.unlocked_options:
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
            if 'psychodynamics' in self.research.unlocked_options:
                for commodity in ['tech', 'agri', 'salt', 'fuel']:
                    if random.random() < 0.2:  # 20% chance for each commodity
                        self.action.manipulate_market(planet, commodity, self.research)

    # Update Game class methods
    def display_turn_info(self):
        self.clear_screen()
        status_content = [
            ["CΔRGΩ", "Ship", f"{self.current_location.location_type}"],
            [f"Turn: {self.turn}", f"ATK: {self.ship.attack}", f"Name: {self.current_location.name}"],
            [f"¤: {self.format_money(self.ship.money)}", f"DEF: {self.ship.defense}", f"Tech LVL: {self.current_location.tech_level}"],
            [f"Tech: {self.format_money(self.ship.cargo['tech'])}", f"SPD: {self.ship.speed}", f"Agri LVL: {self.current_location.agri_level}"],
            [f"Agri: {self.format_money(self.ship.cargo['agri'])}", f"DMG: {self.ship.damage}%", f"ECO: {self.current_location.economy}"],
            [f"Salt: {self.format_money(self.ship.cargo['salt'])}", f"RP: {self.ship.research_points}", f"EFF: {self.current_location.exogeology}%"],
            [f"Fuel: {self.format_money(self.ship.cargo['fuel'])}", f"★ {self.rank}", f"NET: {len(self.current_location.buildings)}"]
        ]
        
        # Add story progress if available
        if hasattr(self, 'story_manager'):
            chapter = self.story_manager.chapters[self.story_manager.current_chapter]
            status_content.append([
                f"Chapter {self.story_manager.current_chapter}",
                f"Plot Points: {self.story_manager.plot_points}",
                chapter["title"]
            ])

        status_box = self.create_box(status_content, 'double')
        print(status_box)

        # Market prices with banned commodities indicator
        tech_status = "BANNED" if 'tech' in self.current_location.banned_commodities else str(self.format_money(self.current_location.market['tech']))
        agri_status = "BANNED" if 'agri' in self.current_location.banned_commodities else str(self.format_money(self.current_location.market['agri']))
        salt_status = "BANNED" if 'salt' in self.current_location.banned_commodities else str(self.format_money(self.current_location.market['salt']))
        fuel_status = "BANNED" if 'fuel' in self.current_location.banned_commodities else str(self.format_money(self.current_location.market['fuel']))

        # Market content with two columns
        market_content = [
            [f"Tech: {tech_status}", f"Salt: {salt_status if any(p['type'] == 'salt' for p in self.current_location.mining_platforms) else '——'}"],
            [f"Agri: {agri_status}", f"Fuel: {fuel_status if any(p['type'] == 'fuel' for p in self.current_location.mining_platforms) else '——'}"]
        ]

        # Add ban duration if any commodities are banned
        if self.current_location.banned_commodities:
            market_content.append(["", ""])  # Empty line for spacing
            market_content.append(["Trade Bans:", "Duration:"])
            for commodity in self.current_location.banned_commodities:
                duration = self.current_location.ban_duration.get(commodity, "Permanent")
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

    def display_location_info(self):
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

        # Add combat statistics if they exist
        if hasattr(self.ship, 'combat_victories'):
            ship_info.extend([
                ["Combat Record:"],
                [f"  Victories: {self.ship.combat_victories}"],
                [f"  Defeats: {self.ship.combat_defeats}"]
            ])
            if hasattr(self.ship, 'enemy_victories'):
                for enemy_type, count in self.ship.enemy_victories.items():
                    if count > 0:
                        ship_info.append([f"  {enemy_type.capitalize()} defeats: {count}"])
        
        # Location section
        location_info = [
            ["MAP"],
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
        location_info.append(["Buildings:"])
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
            location_line = location_info[i][0] if i < len(location_info) else ""
            content.append([ship_line, location_line])

        print(self.create_box(content, 'double'))
        time.sleep(3)

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

    def format_buildings(self):
        building_counts = {}
        for building in self.current_location.buildings:
            if building in building_counts:
                building_counts[building] += 1
            else:
                building_counts[building] = 1
        return [f"{building} {count}" for building, count in building_counts.items()]

    def choose_difficulty(self):
        self.clear_screen()
        display_logo(logo_data, centered=False)
        difficulty_info = [
            ["DIFFICULTY SELECTION"],
            ["  1. EASY"],
            ["  2. NORMAL"],
            ["  3. EXPERT"],
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

    def enable_psychodynamics(self):
        """Enable market manipulation capabilities"""
        if 'psychodynamics' not in self.research.research_costs:
            self.research.research_costs['psychodynamics'] = 300
            self.research.research_benefits['psychodynamics'] = {'price_control': 0.15}

    def enable_trade_empire_features(self):
        """Enable advanced trading features"""
        self.trade_bonus = 0.2  # 20% better trade prices
        self.stockmarket_cost *= 0.8  # 20% cheaper stockmarkets
        self.ship.trade_reputation = True

    def enable_ancient_research(self):
        """Enable ancient technology research"""
        self.research.research_costs['ancient_tech'] = 500
        self.research.research_benefits['ancient_tech'] = {'tech_boost': 0.3}
        self.story_manager.story_states['ancient_research'] = True

    def enable_crisis_mastery(self):
        """Enable crisis management bonuses"""
        self.ship.crisis_bonus = True
        self.combat_bonus = 0.25  # 25% combat effectiveness
        self.repair_discount = 0.3  # 30% cheaper repairs

    def increase_threat_level(self):
        """Increase general threat level"""
        self.combat_difficulty *= 1.5
        self.pirate_frequency *= 1.5
        self.event_risk *= 1.25

    def activate_crisis_events(self):
        """Enable crisis-specific events"""
        self.crisis_active = True
        self.crisis_events = [
            "anomaly_surge",
            "system_instability", 
            "mass_migration"
        ]
        self.event_probability *= 1.5

    def activate_endgame_events(self):
        """Enable endgame content"""
        self.endgame_active = True
        self.enable_stellar_portal = True
        self.legendary_items_available = True
        self.final_crisis_events = True
        
    def unlock_advanced_equipment(self):
        """Unlock advanced equipment in shop"""
        new_equipment = {
            "quantum_drive": 50000,
            "neutron_shield": 40000,
            "warp_core": 75000
        }
        self.shop.base_equipment.update(new_equipment)

    def get_trade_volume(self, location):
        """Calculate total trade volume at location"""
        if not hasattr(location, 'trade_history'):
            location.trade_history = []
        return sum(trade['value'] for trade in location.trade_history)

    def record_trade(self, location, value):
        """Record trade for statistics"""
        if not hasattr(location, 'trade_history'):
            location.trade_history = []
        location.trade_history.append({
            'turn': self.turn,
            'value': value
        })
        self.trades_completed += 1

    def check_controlled_locations(self):
        """Count player-controlled locations"""
        return len([loc for loc in self.locations if getattr(loc, 'controlled_by_player', False)])

    def get_chapter_statistics(self):
        """Get current chapter performance stats"""
        return {
            'trades': self.trades_completed,
            'combat': self.ship.combat_victories,
            'discoveries': len(self.known_locations),
            'research': self.ship.research_points,
            'wealth': self.ship.money
        }

    def trigger_crisis_event(self):
        """Handle crisis event generation"""
        if not self.crisis_active:
            return
        
        events = {
            "anomaly_surge": self.handle_anomaly,
            "system_instability": self.handle_instability,
            "mass_migration": self.handle_migration
        }
        
        event = random.choice(list(events.keys()))
        events[event]()

    def handle_anomaly(self):
        damage = random.randint(10, 30)
        self.ship.damage += damage
        self.display_simple_message(f"Anomaly surge! Ship took {damage}% damage!")

    def handle_instability(self):
        loss = int(self.ship.money * 0.1)
        self.ship.money -= loss
        self.display_simple_message(f"System instability! Lost {self.format_money(loss)} credits!")

    def handle_migration(self):
        for location in self.locations:
            location.market['tech'] *= 1.2
            location.market['agri'] *= 1.2
        self.display_simple_message("Mass migration affecting market prices!")

    def handle_research_breakthrough(self):
        tech_boost = 0.2
        self.ship.research_points *= (1 + tech_boost)
        self.story_manager.trigger_milestone("tech_breakthrough")

    def handle_alien_artifact(self):
        reward = 10000 * (1 + self.story_manager.current_chapter)
        self.ship.money += reward
        self.story_manager.trigger_milestone("first_artifact")
        
    def check_final_crisis(self):
        return (self.story_manager.current_chapter >= 5 and 
                self.check_controlled_locations() >= 3 and
                self.ship.research_points >= 1000)
    
    def update_story_progress(self):
        for location in self.locations:
            # Update story states based on world state
            if self.get_trade_volume(location) > 50000:
                self.story_manager.story_states["trade_empire"] = True
            if len([p for p in location.mining_platforms]) > 2:
                self.story_manager.story_states["resource_empire"] = True

    def check_story_requirements(self):
        """Check and update story progression each turn"""
        self.update_story_progress()
        if self.crisis_active:
            self.trigger_crisis_event()
        if self.check_final_crisis():
            self.activate_endgame_events()                    

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

    def display_starting_info(self):
        """Display initial game information with location context"""
        # Get location info based on current_location
        location_type = "industrial"
        if self.current_location.agri_level > self.current_location.tech_level:
            location_type = "agricultural"
        elif self.current_location.research_points > 15:
            location_type = "research"

        intro_text = f"\n  You arrive on {self.current_location.name}, a {location_type} {self.current_location.location_type.lower()}, where your adventure begins."
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
            self.check_location_unlocks()  # Check for new unlocks each turn
            self.check_milestone_triggers() # Check for StoryManager

            valid_actions = [
                'buy', 'b', 'sell', 's', 'upgrade', 'u', 'travel', 't', 
                'repair', 'r', 'info', 'i', 'build', 'bl', 'cantina', 'c', 
                'shop', 'sh', 'action', 'a', 'mine', 'm', 'end', 'e',
                'quit', 'q', 'resign', 'rs', 'version', 'v'
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
                if not self.current_location.can_trade(item):
                    self.display_simple_message(f"Trading of {item} is banned on this planet!")
                    return

                # Check for mining platform requirement for salt and fuel
                if item in ['salt', 'fuel']:
                    has_platform = any(p['type'] == item for p in self.current_location.mining_platforms)
                    if not has_platform:
                        self.display_simple_message(f"No mining platform for {item} on this planet.")
                        return

                quantity = self.validate_quantity_input("Enter quantity (or 'max' for maximum): ")
                if quantity is None:
                    return

                if quantity == 'max':
                    # Only calculate max if the item's price is non-zero
                    price = self.current_location.market[item]
                    if price <= 0:
                        self.display_simple_message(f"Cannot calculate maximum: {item} has no valid price.")
                        return
                        
                    # Calculate tax rate for this transaction
                    tax_rate = self.current_location.calculate_tax_rate(self.rank, price)
                    price_with_tax = price * (1 + tax_rate)
                    quantity = int(self.ship.money / price_with_tax)

                if self.ship.buy(item, quantity, self.current_location.market[item], 
                                self.current_location, self.rank):
                    self.display_simple_message(f"Bought {self.format_money(quantity)} {item}.")
                    self.handle_trade('buy')  # Handle story attributes

            elif action in ['sell', 's']:
                item = self.validate_input("Choose item (tech/agri/salt/fuel): ", 
                                        ['tech', 'agri', 'salt', 'fuel'])
                if item is None:
                    return

                if not self.current_location.can_trade(item):
                    self.display_simple_message(f"Trading of {item} is banned on this planet!")
                    return

                quantity = self.validate_quantity_input("Enter quantity (or 'max' for maximum): ")
                if quantity is None:
                    return

                if quantity == 'max':
                    quantity = self.ship.cargo[item]

                if self.ship.sell(item, quantity, self.current_location.market[item], 
                                self.current_location, self.rank):
                    self.display_simple_message(f"Sold {self.format_money(quantity)} {item}.")
                    self.handle_trade('sell')  # tracking for story


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
                    self.display_simple_message("Choose a location to travel to:")
                    for i, location in enumerate(self.known_locations, 1):
                        print(f"{i}. {location}")
                    
                    self.display_simple_message("Enter the number or name of the location (or 'cancel'): ", 0)
                    choice = input(">>> ").strip()
                    
                    if not choice or choice.lower() == 'cancel':
                        self.display_simple_message("Travel cancelled.")
                        return
                        
                    if choice.isdigit():
                        index = int(choice) - 1
                        if 0 <= index < len(self.known_locations):
                            self.travel_to_location(self.known_locations[index])
                        else:
                            self.display_simple_message("Invalid location number.")
                    else:
                        self.travel_to_location(choice)
                else:
                    self.display_simple_message("Enter location name (or 'cancel'): ", 0)
                    location_name = input(">>> ").strip()
                    
                    if not location_name or location_name.lower() == 'cancel':
                        self.display_simple_message("Travel cancelled.")
                        return
                        
                    self.travel_to_location(location_name)

            elif action in ['repair', 'r']:
                cost = self.ship.damage * 10
                if self.ship.repair(cost):
                    self.display_simple_message("Ship repaired.")
                else:
                    self.display_simple_message(
                        f"Not enough money to repair. Cost: {self.format_money(cost)}"
                    )

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
                    'mining': 10000
                }

                # Create the validation options list
                valid_options = [
                    'stockmarket', 'sm',
                    'permaculture', 'pc',
                    'organic', 'oc',
                    'agrobot', 'ab',
                    'nanotech', 'nt',
                    'neuroengineering', 'ne',
                    'mining', 'm'
                ]

                building_name = self.validate_input(
                    "Choose building type: ",
                    valid_options
                )
                
                if building_name is None:
                    return

                # Handle building construction - removed building_options parameter
                self.handle_building_construction(building_name, building_costs)

            elif action in ['cantina', 'c']:
                self.visit_cantina()

            elif action in ['shop', 'sh']:
                self.visit_shop()  # Changed from self.shop()

            elif action in ['action', 'a']:
                self.handle_actions()

            elif action in ['mine', 'm']:
                self.handle_mining()

            elif action in ['version', 'v']:
                display_logo(logo_data, centered=True)
                print_centered_text("Version 1.0")
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

            elif action in ['end', 'e']:
                self.turn += 1
                self.random_event()
                return

            else:
                self.display_simple_message("Invalid action.")

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
        """Handle building construction with proper capability checking"""
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
            'm': ('Mining Facility', 'mining')
        }

        # Get the full building name and base type
        if building_name not in building_mapping:
            self.display_simple_message("Invalid building type.")
            return
            
        full_building_name, base_type = building_mapping[building_name]

        # Debug info
        capabilities = self.current_location.get_capabilities()
        can_build = capabilities.get("can_build", [])
        
        self.display_simple_message(f"Debug: Location type: {self.current_location.location_type}")
        self.display_simple_message(f"Debug: Building base type: {base_type}")
        self.display_simple_message(f"Debug: Can build list: {can_build}")

        # Check if location can build this type of building
        if base_type not in can_build:
            self.display_simple_message(f"Cannot build {full_building_name} at this location type.")
            return

        # Get base cost and calculate final cost
        base_cost = building_costs.get(base_type, 3000)
        cost_multiplier = self.current_location.buildings.count(full_building_name) + 1
        final_cost = base_cost * cost_multiplier

        # Build if player can afford it
        if self.ship.money >= final_cost:
            self.ship.money -= final_cost
            success = self.current_location.build_building(full_building_name)
            if success:
                self.display_simple_message(f"Built {full_building_name} for {self.format_money(final_cost)} money.")
            else:
                self.ship.money += final_cost  # Refund if building failed
                self.display_simple_message(f"Failed to build {full_building_name}.")
        else:
            self.display_simple_message(f"Not enough money. Cost: {self.format_money(final_cost)}")

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
            
            # Add research points to the ship
            self.ship.research_points += total_gain
            
            # Display informative message about research gain
            if found_location.name not in self.known_locations:
                self.display_simple_message(f"Gained {total_gain} research points from discovering new location!")
            elif research_difference > 0:
                self.display_simple_message(f"Gained {total_gain} research points from studying advanced technology!")
            else:
                self.display_simple_message(f"Gained {total_gain} research points from comparative analysis!")
            
            self.turn += 1
            self.random_event()
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
        # Update story progression
        story_triggers = {
            "combat_victory": ["pirate_defeat", "defend_station"],
            "exploration_discovery": ["new_artifact", "alien_ruins"],
            "disaster_survived": ["emergency_repair", "crisis_management"]
        }
        event_key = f"{event_type}_{outcome}"
        if event_key in story_triggers:
            for trigger in story_triggers[event_key]:
                self.story_manager.process_event(trigger, details)
        
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
        # Define all possible events with their categories
        events = {
            "combat": [
                "Pirate attack!",
                "Rogue Corsair!",
                "Militia Patrol!",
                "Pirate mothership!",
                "Rogue Warship!",
                "Guerrilla Militia!"
            ],
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
            "Planet": {"combat": 1.0, "trade": 1.0, "exploration": 1.0, "disaster": 1.0},
            "Asteroid Base": {"combat": 1.2, "trade": 0.8, "exploration": 1.1, "disaster": 1.3},
            "Deep Space Outpost": {"combat": 1.3, "trade": 0.7, "exploration": 1.2, "disaster": 1.1},
            "Research Colony": {"combat": 0.7, "trade": 0.9, "exploration": 1.4, "disaster": 0.9}
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
            "name": event,
            "location": self.current_location.name,
            "turn": self.turn
        }
        
        # Handle event based on category
        if category == "combat":
            self.handle_combat_event(event)
        elif category == "trade":
            self.handle_trade_event(event)
        elif category == "exploration":
            self.handle_exploration_event(event)
        elif category == "disaster":
            self.handle_disaster_event(event)
        
        # Process event outcome
        outcome_details = self.process_event_outcome(event_result)
        
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
            if "market_crash" in event_result["name"].lower():
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
            chapter_multiplier = 1 + (self.story_manager.current_chapter * 0.2)
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

    def process_event_outcome(self, event_result):
        """Process and categorize event outcomes with detailed information"""
        details = {
            "location": self.current_location.name,
            "location_type": self.current_location.location_type,
            "initial_damage": self.ship.damage,
            "cargo_before": dict(self.ship.cargo),
            "money_before": self.ship.money,
            "timestamp": self.turn
        }
        
        # Calculate specific event impacts
        if event_result["type"] == "combat":
            damage_taken = self.ship.damage - details["initial_damage"]
            details["damage_taken"] = damage_taken
            details["outcome"] = "victory" if damage_taken < 30 else "defeat"
            details["reputation_change"] = 2 if damage_taken < 30 else -1
            
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

    def handle_combat_event(self, event):
        """Complete combat event handler with statistics tracking"""
        # Define combat scenarios with their difficulties
        combat_scenarios = {
            "Pirate attack!": {"atk": 2, "def": 1, "reward_mult": 1.0, "enemy_type": "pirate"},
            "Rogue Corsair!": {"atk": 3, "def": 2, "reward_mult": 1.2, "enemy_type": "pirate"},
            "Militia Patrol!": {"atk": 4, "def": 3, "reward_mult": 1.5, "enemy_type": "militia"},
            "Pirate mothership!": {"atk": 5, "def": 4, "reward_mult": 2.0, "enemy_type": "pirate"},
            "Rogue Warship!": {"atk": 6, "def": 5, "reward_mult": 2.5, "enemy_type": "raider"},
            "Guerrilla Militia!": {"atk": 7, "def": 6, "reward_mult": 3.0, "enemy_type": "militia"}
        }
        
        scenario = combat_scenarios.get(event, combat_scenarios["Pirate attack!"])
        enemy_type = scenario["enemy_type"]
        
        # Check for automatic defense
        if "turrets" in self.ship.items and random.random() < 0.4:
            self.display_simple_message(f"Event! {event} repelled by defense systems!", 3, color='32')
            # Count automatic defense as a victory
            self.ship.record_combat_victory(enemy_type)
            # Gain some experience even when automatically defending
            self.ship.research_points += int(5 * scenario["reward_mult"])
            return
        
        # Calculate base damage
        damage = random.randint(10, 25) * scenario["atk"] / self.ship.defense
        damage *= (1 + self.difficulty)
        
        # Apply defensive equipment effects
        if "shield" in self.ship.items:
            damage *= 0.7  # 30% damage reduction
        if "armor" in self.ship.items:
            damage *= 0.8  # 20% damage reduction
        
        # Ensure damage doesn't exceed 99%
        final_damage = min(99, int(self.ship.damage + damage))
        damage_dealt = final_damage - self.ship.damage
        self.ship.damage = final_damage
        
        # Handle cargo/money loss
        losses = []
        
        if self.ship.money > 0:
            stolen = random.randint(1, max(1, int(self.ship.money // 2)))
            self.ship.money -= stolen
            losses.append(f"{self.format_money(stolen)} credits")
        
        # Only steal cargo that exists
        for cargo_type in ['tech', 'agri', 'salt', 'fuel']:
            if self.ship.cargo[cargo_type] > 0:
                stolen_cargo = random.randint(1, max(1, int(self.ship.cargo[cargo_type] // 3)))
                self.ship.cargo[cargo_type] -= stolen_cargo
                if stolen_cargo > 0:
                    losses.append(f"{stolen_cargo} {cargo_type}")
        
        # Check for counter-attack opportunity
        if self.ship.attack > scenario["def"]:
            # Counter-attack successful - record victory
            self.ship.record_combat_victory(enemy_type)
            
            reward_mult = scenario["reward_mult"]
            rewards = {
                "money": int(random.randint(100, 500) * reward_mult),
                "research": int(random.randint(10, 25) * reward_mult)
            }
            
            self.ship.money += rewards["money"]
            self.ship.research_points += rewards["research"]
            
            if losses:
                loss_text = ", ".join(losses)
                self.display_simple_message(
                    f"Event! {event} caused {damage_dealt}% damage and stole {loss_text}!\n" +
                    f"Counter-attack successful! Gained {self.format_money(rewards['money'])} credits and {rewards['research']} research points!",
                    3, color='32'
                )
            else:
                self.display_simple_message(
                    f"Event! {event} caused {damage_dealt}% damage!\n" +
                    f"Counter-attack successful! Gained {self.format_money(rewards['money'])} credits and {rewards['research']} research points!",
                    3, color='32'
                )
        else:
            # Combat defeat - record defeat with enemy type
            self.ship.record_combat_defeat(enemy_type)
            
            if losses:
                loss_text = ", ".join(losses)
                self.display_simple_message(
                    f"Event! {event} caused {damage_dealt}% damage and stole {loss_text}!",
                    3, color='31'
                )
            else:
                self.display_simple_message(
                    f"Event! {event} caused {damage_dealt}% damage!",
                    3, color='31'
                )

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
    def handle_trade(self, action_type):
        """Track trade completion"""
        self.trades_completed += 1


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

        # Add story-specific dialogue based on current chapter
        if self.story_manager.current_chapter > 0:
            chapter = self.story_manager.chapters[self.story_manager.current_chapter]
            self.display_character_message("Cantina Owner",
                f"Word is spreading about your adventures. Have you heard about {chapter['title']}?")

        action = self.validate_input(
            "Choose action (buy map/bm, update map/um, listen to gossip/lg, quests/q, story/s): ",
            ['buy map', 'bm', 'update map', 'um', 'listen to gossip', 'lg', 'quests', 'q', 'story', 's']
        )

        if action is None:
            return

        if action in ['story', 's']:
            story_content = [["Story Progress & Achievements"]]
            story_content.append([""])
            
            # Current chapter info
            chapter = self.story_manager.chapters[self.story_manager.current_chapter]
            story_content.append([f"Current Chapter: {self.story_manager.current_chapter} - {chapter['title']}"])
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
            
            # Ensure all rows have same number of columns
            max_cols = max(len(row) for row in story_content)
            story_content = [row + [""] * (max_cols - len(row)) for row in story_content]
            print(self.create_box(story_content, 'double'))
            input("Press Enter to continue...")

        elif action in ['buy map', 'bm']:
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
                    
                    # Ensure all rows have same number of columns
                    max_cols = max(len(row) for row in map_content)
                    map_content = [row + [""] * (max_cols - len(row)) for row in map_content]
                    print(self.create_box(map_content, 'double'))
                    input("Press Enter to continue...")
                else:
                    self.ship.money += 200  # Refund if no new locations
                    self.display_simple_message("No new locations to discover!")
            else:
                self.display_simple_message("Not enough money to buy a map.")

        elif action in ['update map', 'um']:
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
                        # Get market prices with potential trade bans
                        tech_price = "BANNED" if 'tech' in location.banned_commodities else self.format_money(location.market['tech'])
                        agri_price = "BANNED" if 'agri' in location.banned_commodities else self.format_money(location.market['agri'])
                        salt_price = "BANNED" if 'salt' in location.banned_commodities else self.format_money(location.market['salt'])
                        fuel_price = "BANNED" if 'fuel' in location.banned_commodities else self.format_money(location.market['fuel'])
                        
                        market_content.append([
                            location.name,
                            tech_price,
                            agri_price,
                            salt_price if any(p['type'] == 'salt' for p in location.mining_platforms) else "No Mine",
                            fuel_price if any(p['type'] == 'fuel' for p in location.mining_platforms) else "No Mine"
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
                
                # Show newly unlocked location types
                potential_locations = [loc for loc in self.locations 
                                    if loc.location_type in self.unlocked_location_types]
                if len(potential_locations) > len(self.known_locations):
                    market_content.append([""])
                    market_content.append(["New Areas for Exploration"])
                    for loc_type in self.unlocked_location_types:
                        count = sum(1 for loc in potential_locations 
                                if loc.location_type == loc_type and loc.name not in self.known_locations)
                        if count > 0:
                            market_content.append([f"• {count} undiscovered {loc_type}s", "", "", "", ""])
                    has_data = True
                
                if has_data:
                    # Ensure all rows have same number of columns
                    max_cols = max(len(row) for row in market_content)
                    market_content = [row + [""] * (max_cols - len(row)) for row in market_content]
                    print(self.create_box(market_content, 'double'))
                    input("Press Enter to continue...")
                else:
                    self.ship.money += 350  # Refund if no data to show
                    self.display_simple_message("No new information available!")
            else:
                self.display_simple_message("Not enough money to update the map.")

        elif action in ['listen to gossip', 'lg']:
            if self.ship.money >= 150:
                self.ship.money -= 150
                gossip_content = [["Latest Market Gossip"]]
                gossip_content.append([""])
                
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
                    # Ensure all rows have same number of columns
                    max_cols = max(len(row) for row in gossip_content)
                    gossip_content = [row + [""] * (max_cols - len(row)) for row in gossip_content]
                    print(self.create_box(gossip_content, 'double'))
                    
                    if random.random() < 0.3:  # 30% chance to get a quest
                        quest = Quest(
                            name=random.choice([
                                "Deliver Tech Goods",
                                "Transport Agri Supplies",
                                "Rescue Mission",
                                "Mining Intel",
                                "Eliminate Pirates"
                            ]),
                            description="Complete this mission for the cantina",
                            reward_money=random.randint(500, 2500),
                            reward_rp=random.randint(25, 100),
                            quest_type="cantina"
                        )
                        self.quest_system.add_quest(quest)
                else:
                    self.display_simple_message("No interesting gossip today!")
            else:
                self.display_simple_message("Not enough money to listen to gossip.")
                
        elif action in ['quests', 'q']:
            active_quests = [q for q in self.quest_system.active_quests if isinstance(q, Quest)]
            if active_quests:
                quest_content = [["Active Quests"]]
                quest_content.append([""])
                for quest in active_quests:
                    quest_content.append([quest.name])
                    quest_content.append([f"└─ {quest.description}"])
                    quest_content.append([f"└─ Rewards: {self.format_money(quest.reward_money)} credits, {quest.reward_rp} RP"])
                    quest_content.append([""])
                
                # Ensure all rows have same number of columns
                max_cols = max(len(row) for row in quest_content)
                quest_content = [row + [""] * (max_cols - len(row)) for row in quest_content]
                print(self.create_box(quest_content, 'double'))
            else:
                self.display_simple_message("No active quests.")
        
        # Randomly introduce a demo character after reaching a new rank
        if random.random() < 0.1:  # 10% chance
            self.display_character_message(
                "Mysterious Stranger", 
                "Greetings, traveler. I hear you've been making a name for yourself. Keep it up, and you might just become a legend."
            )

        time.sleep(3)  # Pause to let the player read the information

    def visit_shop(self):
        self.display_simple_message("Welcome to the Shop!", 1)
            # Modify shop inventory based on location type
        if isinstance(self.current_location, AsteroidBase):
            available_items = ["mining_laser", "cargo_scanner", "shield_booster"]
        elif isinstance(self.current_location, DeepSpaceOutpost):
            available_items = ["advanced_radar", "combat_drone", "repair_bot"]
        elif isinstance(self.current_location, ResearchColony):
            available_items = ["research_module", "data_analyzer", "quantum_scanner"]
        else:
            available_items = ["navcomp", "scanner", "probe", "turrets", "shield"]

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
            if self.action.research(self.current_location, 'exogeology', self.research):
                self.display_simple_message("Mining efficiency research completed!")
            else:
                self.display_simple_message("Not enough research points!")

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


    def check_quest_story_impact(self, quest):
        """Check if quest completion affects story"""
        if quest.quest_type == "story":
            self.story_manager.process_event("quest", {
                "type": "story",
                "quest_name": quest.name
            })
        self.story_manager.handle_quest_completion(quest)

    def generate_story_quest(self):
        """Generate story-driven quests"""
        chapter = self.story_manager.chapters[self.story_manager.current_chapter]
        for milestone in chapter["milestones"]:
            if milestone not in self.story_manager.completed_story_beats:
                quest = self.quest_system.generate_quest("story", 2.0)
                if quest:
                    quest.milestone = milestone
                    self.quest_system.add_quest(quest)
                break

    def check_milestone_triggers(self):
        """Check for milestone triggers each turn"""
        # First trade
        if self.trades_completed == 2:
            self.story_manager.complete_milestone("first_trade")

        # First combat
        if self.ship.combat_victories == 1:
            self.story_manager.complete_milestone("first_combat")
            
        # Basic license (after 5 successful trades)
        if self.trades_completed >= 5 and "basic_license" not in self.story_manager.completed_story_beats:
            self.story_manager.complete_milestone("basic_license")

        # Pirates and route security
        if self.ship.enemy_victories.get('pirate', 0) >= 5:
            self.story_manager.complete_milestone("defeat_pirates")
            if self.trades_completed >= 20:
                self.story_manager.complete_milestone("secure_route")

        # Mining milestones
        if any(loc.mining_platforms for loc in self.locations):
            self.story_manager.complete_milestone("first_mining")
            miners_defended = self.ship.combat_victories >= 10
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
            
            if valid_locations and all(loc.stockmarket_base for loc in valid_locations):
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
                        self.display_simple_message("You have paid for the secret quest and a Stellar Portal appears on this location.")
                        # Generate new locations
                        new_locations = self.generate_new_locations()
                        self.locations.extend(new_locations)
                        self.current_location = random.choice(new_locations)
                        self.known_locations = [self.current_location.name]
                        self.display_simple_message("You have traveled to a new set of locations with more volatile price movements.")
                    else:
                        self.display_simple_message("Not enough money to pay for the secret quest.")

            # Ask to play again
            if turn_result == "quit":
                play_again = self.validate_input("Do you want to play again? (yes/no): ", ['yes', 'no'])
                if play_again == 'yes':
                    self.__init__()
                    self.play()
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

    def generate_station_missions(self):
        """Generate station defense missions"""
        quest = Quest(
            name="Station Defense",
            description="Defend the station from incoming threats",
            reward_money=5000,
            reward_rp=50,
            quest_type="combat",
            requirements={"victories": 3, "damage_threshold": 20}
        )
        self.quest_system.add_quest(quest)

    def generate_research_missions(self):
        """Generate research-related missions"""
        quest = Quest(
            name="Scientific Discovery",
            description="Collect research data from various phenomena",
            reward_money=4000,
            reward_rp=100,
            quest_type="research",
            requirements={"research_points": 50}
        )
        self.quest_system.add_quest(quest)

    def generate_emergency_missions(self):
        """Generate emergency response missions"""
        quest = Quest(
            name="Emergency Response",
            description="Help ships in distress while avoiding damage",
            reward_money=6000,
            reward_rp=75,
            quest_type="combat",
            requirements={"rescues": 2, "max_damage": 30}
        )
        self.quest_system.add_quest(quest)

    def handle_location_discovery(self, location):
        """Handle discovery of a new location"""
        if location.name not in self.discovered_locations:
            self.discovered_locations.add(location.name)
            
            # Award discovery rewards
            discovery_reward = 1000 * (self.story_manager.current_chapter + 1)
            research_reward = 20 * (self.story_manager.current_chapter + 1)
            
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

class Shop:
    def __init__(self):
        # Original equipment merged with transport equipment
        self.base_equipment = {
            # Navigation and Scanning
            "navcomp": {
                "price": 500,
                "description": "Navigation computer for improved travel"
            },
            "scanner": {
                "price": 700,
                "description": "Basic scanner for resource detection"
            },
            "probe": {
                "price": 900,
                "description": "Probe for detailed exploration"
            },

            # Combat and Defense
            "turrets": {
                "price": 1200,
                "description": "Defense system against pirates"
            },
            "shield": {
                "price": 2000,
                "description": "Shield generator for protection"
            },
            "patcher": {
                "price": 300,
                "description": "Basic repair system"
            },

            # Basic Transport Equipment
            "cargo_extender": {
                "price": 5000,
                "description": "Increases cargo capacity by 20%",
                "effect": {"type": "cargo", "value": 1.2}
            },
            "containment_field": {
                "price": 8000,
                "description": "Specialized storage for salt/fuel. +30% capacity for special resources",
                "effect": {"type": "special_cargo", "value": 1.3}
            },
            "auto_loader": {
                "price": 12000,
                "description": "Reduces loading/unloading time. -1 turn per trade",
                "effect": {"type": "trade_time", "value": -1}
            },

            # Advanced Transport Equipment
            "quantum_compressor": {
                "price": 20000,
                "description": "Advanced compression. +50% capacity for all cargo",
                "effect": {"type": "cargo", "value": 1.5}
            },
            "stasis_vault": {
                "price": 25000,
                "description": "Perfect resource preservation. +75% capacity for special resources",
                "effect": {"type": "special_cargo", "value": 1.75}
            },
            "temporal_accelerator": {
                "price": 30000,
                "description": "Time dilation for faster delivery. -2 turns per trade",
                "effect": {"type": "trade_time", "value": -2}
            }
        }

        # Location-specific equipment
        self.specialized_equipment = {
            "AsteroidBase": {
                "mining_laser": {
                    "price": 8000,
                    "description": "Advanced mining equipment for better resource extraction"
                },
                "cargo_scanner": {
                    "price": 6000,
                    "description": "Specialized scanner for detecting valuable cargo"
                },
                "shield_booster": {
                    "price": 7000,
                    "description": "Enhanced shields for asteroid field protection"
                },
                "mining_compressor": {
                    "price": 15000,
                    "description": "Specialized for asteroid mining. +40% capacity for mined resources",
                    "effect": {"type": "special_cargo", "value": 1.4}
                }
            },
            "DeepSpaceOutpost": {
                "advanced_radar": {
                    "price": 9000,
                    "description": "Long-range radar system for deep space navigation"
                },
                "combat_drone": {
                    "price": 12000,
                    "description": "Automated defense drone for combat support"
                },
                "repair_bot": {
                    "price": 10000,
                    "description": "Automated repair system for hull maintenance"
                },
                "emergency_warp": {
                    "price": 18000,
                    "description": "Emergency escape system. 50% chance to avoid combat during transport",
                    "effect": {"type": "combat_avoid", "value": 0.5}
                }
            },
            "ResearchColony": {
                "research_module": {
                    "price": 11000,
                    "description": "Advanced research equipment for scientific studies"
                },
                "data_analyzer": {
                    "price": 13000,
                    "description": "Sophisticated data analysis system"
                },
                "quantum_scanner": {
                    "price": 15000,
                    "description": "High-precision quantum scanning device"
                },
                "containment_optimizer": {
                    "price": 22000,
                    "description": "Smart cargo optimization. +25% capacity and -1 turn per trade",
                    "effect": {"type": "hybrid", "cargo": 1.25, "time": -1}
                }
            }
        }

    def get_available_items(self, location_type=None):
        """Get available items, optionally filtered by location type"""
        # Start with base equipment
        available = dict(random.sample(list(self.base_equipment.items()), 
                        min(3, len(self.base_equipment))))
        
        # Add location-specific items if applicable
        if location_type and location_type in self.specialized_equipment:
            available.update(self.specialized_equipment[location_type])
            
        return available

    def get_price(self, item_name):
        """Get the price of an item"""
        if item_name in self.base_equipment:
            return self.base_equipment[item_name]["price"]
        
        # Check specialized equipment
        for location_items in self.specialized_equipment.values():
            if item_name in location_items:
                return location_items[item_name]["price"]
        return None

    def add_equipment(self, equipment_name):
        """Add new equipment to the shop's inventory"""
        if equipment_name not in self.base_equipment:
            self.base_equipment[equipment_name] = {
                "price": 10000,  # Default price
                "description": f"New equipment: {equipment_name}",
                "effect": {"type": "generic", "value": 1.0}
            }           

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

    def calculate_mining_output(self, platform_type):
        """Calculate mining output based on efficiency and random factors"""
        base_output = random.randint(10, 20)
        efficiency_bonus = self.exogeology / 100
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
                    'efficiency': self.exogeology,
                    'capacity': random.randint(100, 200)
                })
                self.mineral_deposits[deposit_type] -= 1
                return True
        return False

    def generate_market(self):
        """Generate market prices including mining commodities"""
        market = {
            'tech': 100 - (self.tech_level * 10),
            'agri': 50 + (self.agri_level * 5),
            'salt': 0,  # Base price for salt
            'fuel': 0   # Base price for fuel
        }
        
        # Set prices for mined commodities if platforms exist
        for platform in self.mining_platforms:
            if platform.current_amount > 0:  # Only set price if resources available
                if platform.resource_type == 'salt':
                    market['salt'] = 10  # Base price at source
                elif platform.resource_type == 'fuel':
                    market['fuel'] = 15  # Base price at source

        # Higher prices if refinery exists but no local mining
        has_refinery = any(b == "Refinery" for b in self.buildings)
        if has_refinery:
            if market['salt'] == 0:  # No local mining
                market['salt'] = 80  # Base selling price
            if market['fuel'] == 0:  # No local mining
                market['fuel'] = 150  # Base selling price
            
            # Improve prices if there is a refinery
            if market['salt'] > 0:
                market['salt'] = int(market['salt'] * 1.5)  # 50% better price
            if market['fuel'] > 0:
                market['fuel'] = int(market['fuel'] * 1.5)  # 50% better price

        return market
    
    def display_market_info(self):
        """Display market information with mining details"""
        market_content = [["Commodity", "Price", "Status"]]
        
        # Regular commodities
        market_content.append(["Tech", str(self.market['tech']), ""])
        market_content.append(["Agri", str(self.market['agri']), ""])
        
        # Mining commodities
        for resource in ['salt', 'fuel']:
            price = self.market[resource]
            status = ""
            
            # Check for mining platform
            platform = next((p for p in self.mining_platforms 
                            if p.resource_type == resource), None)
            if platform:
                status = f"M: {platform.current_amount}/{platform.max_capacity}"
            elif any(b == "Refinery" for b in self.buildings):
                status = "R"  # Show refinery indicator
                
            if price > 0 or status:  # Only show if tradeable
                market_content.append([
                    resource.capitalize(),
                    str(price),
                    status
                ])
        
        return self.create_box(market_content, 'single')    

    def update_market(self, difficulty):
        """Update market prices with location-specific logic"""
        capabilities = self.get_capabilities()
        tradeable = capabilities.get("can_trade", [])
        
        for commodity in self.market:
            if commodity not in tradeable:
                continue
                
            # Base price changes with randomization and difficulty scaling
            base_change = random.randint(-5, 5) * (1 + difficulty)
            
            # Apply economic effects
            if self.economy == "Booming":
                base_change += 5
            elif self.economy == "Declining":
                base_change -= 5
            elif self.economy == "Formative":
                base_change = int(base_change * 1.2)  # More volatile prices
            
            # Apply stockmarket effects if present
            if self.stockmarket_base:
                base_change = max(1, base_change - 10)
            
            # Handle building effects
            for building in self.buildings:
                if building == "Permaculture Paradise" and commodity == 'agri':
                    base_change = max(1, base_change * 0.8)
                elif building == "The Nanotech Nexus":
                    base_change = max(1, base_change * 0.85)

            # Calculate new price
            new_price = max(1, self.market[commodity] + base_change)
            
            # Apply commodity-specific limits
            if commodity == 'salt':
                new_price = min(new_price, 150)
            elif commodity == 'fuel':
                new_price = min(new_price, 250)
            else:
                new_price = min(new_price, 200)
                
            self.market[commodity] = new_price

            # Handle zero prices and bans
            if new_price == 0 and commodity not in self.banned_commodities:
                self.add_temporary_ban(commodity, random.randint(2, 4))

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

        # Update production cooldowns
        for resource_type in list(self.production_cooldown.keys()):
            if self.production_cooldown[resource_type] > 0:
                self.production_cooldown[resource_type] -= 1

    def calculate_tax_rate(self, player_rank, profit):
        """Calculate tax rate based on player rank and location type"""
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

    def build_building(self, building_name):
        """Build a building and apply its effects.
        Returns: cost_multiplier for the building"""
        if not self.can_build(building_name.lower()):
            return 0  # Return 0 to indicate building not allowed
            
        cost_multiplier = self.buildings.count(building_name) + 1
        
        # Apply building effects
        if building_name == "Mining Facility":
            self.exogeology = min(100, self.exogeology + 10)
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
        elif building_name == "stockmarket":
            self.stockmarket_base = True
            self.market['tech'] = max(1, self.market['tech'] - 10)
            self.market['agri'] = max(1, self.market['agri'] - 5)
        
        # Add building to location's buildings list
        self.buildings.append(building_name)
        
        return cost_multiplier

    def get_capabilities(self):
        """Get capabilities for this location type"""
        return LocationCapabilities.CAPABILITIES.get(self.location_type, {})

    def get_term(self, term_type, use_variant=False):
        """Get contextual terminology for this location"""
        return LocationTerminology.get_term(self.location_type, term_type, use_variant)

    def can_trade(self, commodity):
        """Check if this location can trade a specific commodity"""
        if commodity in self.banned_commodities:
            return False
        return commodity in self.get_capabilities().get("can_trade", [])

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
        """Get base mining efficiency for this location type"""
        return self.get_capabilities().get("base_exogeology", 0)

    def get_research_multiplier(self):
        """Get research point multiplier for this location type"""
        return self.get_capabilities().get("research_multiplier", 1.0)          

class Planet(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "Planet", tech_level, agri_level, research_points, economy)

class AsteroidBase(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "Asteroid Base", tech_level, agri_level, research_points, economy)
        self.exogeology += 20  # Asteroid bases have better mining
        self.quest_requirements = ["complete_basic_mining"]

    def generate_market(self):
        market = super().generate_market()
        # Asteroid bases have better prices for minerals
        market['salt'] = random.randint(100, 150)
        market['fuel'] = random.randint(180, 250)
        return market

class DeepSpaceOutpost(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "Deep Space Outpost", tech_level, agri_level, research_points, economy)
        self.quest_requirements = ["complete_combat_missions"]
        
    def generate_market(self):
        market = super().generate_market()
        # Outposts have better tech prices
        market['tech'] = max(50, market['tech'] - 20)
        return market

class ResearchColony(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "Research Colony", tech_level, agri_level, research_points, economy)
        self.research_points *= 2  # Double research points
        self.quest_requirements = ["complete_research_missions"]

    def generate_market(self):
        market = super().generate_market()
        # Research colonies have advanced tech
        market['tech'] = min(150, market['tech'] + 30)
        return market

class Quest:
    def __init__(self, name, description, reward_money, reward_rp, quest_type="generic", 
                 requirements=None, on_complete=None):
        self.name = name
        self.description = description
        self.reward_money = reward_money
        self.reward_rp = reward_rp  # Research Points reward
        self.quest_type = quest_type
        self.requirements = requirements or {}
        self.on_complete = on_complete
        self.progress = 0
        self.completed = False
        self.target_progress = self.requirements.get('target_progress', 1)
        self.location_requirement = self.requirements.get('location_type', None)

    def check_completion(self, game):
        """Check if quest requirements are met"""
        if self.completed:
            return False

        if self.quest_type == "mining":
            return self.check_mining_completion(game)
        elif self.quest_type == "combat":
            return self.check_combat_completion(game)
        elif self.quest_type == "trade":
            return self.check_trade_completion(game)
        elif self.quest_type == "exploration":
            return self.check_exploration_completion(game)
        elif self.quest_type == "research":
            return self.check_research_completion(game)
        
        # Generic quest completion check
        return self.progress >= self.target_progress

    def check_mining_completion(self, game):
        """Check mining quest requirements"""
        if 'resource_type' in self.requirements:
            resource = self.requirements['resource_type']
            target_amount = self.requirements.get('amount', 0)
            return game.ship.cargo[resource] >= target_amount
        return False

    def check_combat_completion(self, game):
        """Check combat quest requirements"""
        if 'enemy_type' in self.requirements:
            return game.ship.combat_victories.get(
                self.requirements['enemy_type'], 0) >= self.requirements.get('amount', 1)
        return game.ship.combat_victories >= self.requirements.get('amount', 1)

    def check_trade_completion(self, game):
        """Check trading quest requirements"""
        if 'commodity' in self.requirements:
            target_profit = self.requirements.get('profit', 0)
            return game.ship.trade_profits.get(
                self.requirements['commodity'], 0) >= target_profit
        return False

    def check_exploration_completion(self, game):
        """Check exploration quest requirements"""
        if 'location_type' in self.requirements:
            discovered = len([loc for loc in game.discovered_locations 
                            if loc.location_type == self.requirements['location_type']])
            return discovered >= self.requirements.get('amount', 1)
        return False

    def check_research_completion(self, game):
        """Check research quest requirements"""
        if 'research_type' in self.requirements:
            return self.requirements['research_type'] in game.research.unlocked_options
        return game.ship.research_points >= self.requirements.get('target_points', 0)

    def complete(self, game):
        """Complete the quest and award rewards"""
        if not self.completed:
            self.completed = True
            game.ship.money += self.reward_money
            game.ship.research_points += self.reward_rp
            
            # Call completion callback if exists
            if self.on_complete:
                self.on_complete()
            
            # Display completion message
            game.display_story_message([
                f"Quest Completed: {self.name}",
                f"Rewards:",
                f"• {game.format_money(self.reward_money)} credits",
                f"• {self.reward_rp} research points"
            ])

    def update_progress(self, amount=1):
        """Update quest progress"""
        if not self.completed:
            self.progress += amount
            return self.progress >= self.target_progress
        return False

class QuestSystem:
    def __init__(self, game):
        self.game = game
        self.active_quests = []  # For Quest objects
        self.available_quests = []  # For tuple-based quests (legacy support)
        self.completed_quests = []
        self.story_progress = 0
        
        # Quest line progression tracking
        self.quest_lines = {
            "mining": ["basic_mining", "advanced_mining", "expert_mining"],
            "combat": ["patrol_duty", "pirate_hunting", "fleet_command"],
            "research": ["data_collection", "experiment_assistance", "breakthrough"]
        }
        self.quest_line_progress = {
            "mining": 0,
            "combat": 0,
            "research": 0
        }

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

    def add_quest_type(self, quest_type):
        """Add a new type of quest to the available pool"""
        if not hasattr(self, 'available_quest_types'):
            self.available_quest_types = set()
        self.available_quest_types.add(quest_type)

    def generate_station_missions(self):
        """Generate station defense missions"""
        quest = Quest(
            name="Station Defense",
            description="Defend the station from incoming threats",
            reward_money=5000,
            reward_rp=50,
            quest_type="combat",
            requirements={"victories": 3, "damage_threshold": 20}
        )
        self.add_quest(quest)

    def generate_research_missions(self):
        """Generate research-related missions"""
        quest = Quest(
            name="Scientific Discovery",
            description="Collect research data from various phenomena",
            reward_money=4000,
            reward_rp=100,
            quest_type="research",
            requirements={"research_points": 50}
        )
        self.add_quest(quest)

    def generate_emergency_missions(self):
        """Generate emergency response missions"""
        quest = Quest(
            name="Emergency Response",
            description="Help ships in distress while avoiding damage",
            reward_money=6000,
            reward_rp=75,
            quest_type="combat",
            requirements={"rescues": 2, "max_damage": 30}
        )
        self.add_quest(quest)

    def check_event_requirements(self, event_result):
        """Check if an event satisfies any quest requirements"""
        event_type = event_result.get("type", "")
        for quest in self.active_quests:
            if quest.quest_type == event_type:
                quest.progress += 1
                self.display_quest_progress(quest)
                if quest.check_completion(self.game):
                    self.complete_quest(quest)

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
            quest = Quest(
                name=template["name"],
                description=template["description"],
                reward_money=template["reward_money"],
                reward_rp=template["reward_rp"],
                quest_type=template["type"],
                requirements=template["requirements"]
            )
            return quest
        return None

    def update_from_event(self, event_type, outcome, details):
        """Update quest progress based on events"""
        # Update Quest objects
        for quest in self.active_quests:
            progress_made = False
            
            if quest.quest_type == "combat" and event_type == "combat":
                if outcome == "victory":
                    damage_taken = details.get('damage_taken', 0)
                    if damage_taken < quest.requirements.get('damage_threshold', float('inf')):
                        quest.progress += 1
                        progress_made = True
                    
            elif quest.quest_type == "trade" and event_type == "trade":
                money_lost = details.get('money_lost', 0)
                if money_lost < quest.requirements.get('loss_threshold', float('inf')):
                    quest.progress += 1
                    progress_made = True
                    
            elif quest.quest_type == "exploration" and event_type == "exploration":
                if outcome == "discovery" and details.get('location') == quest.requirements.get('target_location'):
                    quest.progress += 1
                    progress_made = True
            
            if progress_made:
                self.display_quest_progress(quest)
                if quest.check_completion(self.game):
                    self.complete_quest(quest)

        # Update legacy tuple-based quests
        self.check_quest_completion(self.game.ship, self.game.current_location)

    def complete_quest(self, quest):
        """Handle quest completion and progression"""
        if isinstance(quest, Quest):
            # Handle Quest object completion
            quest.complete(self.game)
            self.active_quests.remove(quest)
            self.completed_quests.append(quest)
            
            # Update quest line progression if applicable
            for line_type, progression in self.quest_lines.items():
                if quest.name in progression:
                    self.quest_line_progress[line_type] += 1
                    self.check_quest_line_completion(line_type)
        else:
            # Handle legacy tuple-based quest completion
            self.available_quests.remove(quest)
            self.completed_quests.append(quest)
            self.story_progress += 1

    def check_quest_line_completion(self, line_type):
        """Check if a quest line has been completed"""
        if self.quest_line_progress[line_type] >= len(self.quest_lines[line_type]):
            reward_multiplier = 2.0
            bonus_reward = int(5000 * reward_multiplier)
            bonus_rp = int(100 * reward_multiplier)
            
            self.game.ship.money += bonus_reward
            self.game.ship.research_points += bonus_rp
            
            self.game.display_story_message([
                f"Quest Line Completed: {line_type.title()}!",
                f"Bonus Reward: {self.game.format_money(bonus_reward)}",
                f"Bonus Research Points: {bonus_rp}"
            ])
            
            # Trigger relevant story progression
            self.game.story_manager.handle_quest_line_completion(line_type)

    def display_quest_progress(self, quest):
        """Display quest progress update"""
        if isinstance(quest, Quest):
            progress_text = f"Quest Progress: {quest.name}"
            if quest.target_progress > 1:
                progress_text += f" ({quest.progress}/{quest.target_progress})"
            self.game.display_simple_message(progress_text)

    def get_available_quest_types(self):
        """Get available quest types based on game progress"""
        available_types = ["mining", "combat", "trade"]  # Basic types
        
        # Add research quests if conditions met
        if self.game.ship.research_points >= 50:
            available_types.append("research")
            
        # Add story quests if conditions met
        if self.story_progress >= 5:
            available_types.append("story")
            
        return available_types

    def add_quest(self, quest):
        """Add a new quest to active quests"""
        if isinstance(quest, Quest):
            self.active_quests.append(quest)
            self.game.display_story_message([
                "New Quest Available!",
                quest.name,
                quest.description,
                f"Rewards: {self.game.format_money(quest.reward_money)} credits, {quest.reward_rp} RP"
            ])        

class StoryManager:
    def __init__(self, game):
        self.game = game
        self.current_chapter = 0
        self.plot_points = 0
        self.completed_story_beats = set()
        self.milestone_display_names = {
            "first_trade": "First Trades",
            "first_combat": "First Combat Victories",
            "basic_license": "Basic Trading License",
            "defeat_pirates": "Pirate Threat Eliminated",
            "secure_route": "Trade Route Secured", 
            "establish_base": "New Base Established"
        }        
        self.story_states = {
            "pirate_threat": False,
            "alien_discovery": False,
            "trade_empire": False,
            "ancient_mystery": False,
            "galactic_crisis": False
        }

        # Old StoryManager class trackers
        self.discovered_locations_by_type = {}
        self.unlocked_achievements = set()
        self.event_cooldowns = {}
        self.enabled_events = set()
        self.chapter_statistics = {}
        self.event_log = []

        # Add quest tracking
        self.quest_milestones = {
            "mining": ["first_mining", "resource_empire"],
            "combat": ["defeat_pirates", "secure_route"],
            "research": ["tech_breakthrough", "alien_database"],
            "trade": ["trade_empire", "unite_systems"]
        }

        # Track chapter-specific stats
        self.chapter_start_money = 0
        self.chapter_start_quests = 0
        self.chapter_start_locations = 0
        self.chapter_start_combat_victories = 0
        
        # Discovery milestone tracking
        self.discovery_milestones = {
            "AsteroidBase": {"count": 1, "reward_money": 10000, "reward_rp": 100},
            "DeepSpaceOutpost": {"count": 1, "reward_money": 15000, "reward_rp": 150},
            "ResearchColony": {"count": 1, "reward_money": 20000, "reward_rp": 200}
        }

        # Core storyline
        self.chapters = {
            0: {
                "title": "First Steps",
                "description": "Learn the basics of space trading",
                "requirements": {"plot_points": 0},
                "milestones": [
                    "first_trade", 
                    "first_combat",
                    "basic_license"
                ],
                "rewards": {
                    "money": 5000,
                    "research_points": 25,
                    "unlock": "navcomp"
                }
            },
            1: {
                "title": "The Pirate Threat",
                "description": "Protect trade routes from increasing pirate activity",
                "requirements": {
                    "plot_points": 15,
                    "combat_victories": 3,
                    "trades_completed": 10
                },
                "milestones": [
                    "defeat_pirates",
                    "secure_route", 
                    "establish_base"
                ],
                "rewards": {
                    "money": 15000,
                    "research_points": 50,
                    "unlock": "AsteroidBase"
                }
            },
            2: {
                "title": "Mining Frontiers", 
                "description": "Exploit rich asteroid resources",
                "requirements": {
                    "plot_points": 30,
                    "mining_platforms": 1,
                    "research_points": 100
                },
                "milestones": [
                    "first_mining",
                    "resource_empire",
                    "defend_miners"
                ],
                "rewards": {
                    "money": 30000,
                    "research_points": 100,
                    "unlock": "mining_laser"
                }
            },
            3: {
                "title": "Strange Signals",
                "description": "Investigate mysterious deep space transmissions",
                "requirements": {
                    "plot_points": 50,
                    "research_points": 200,
                    "locations_discovered": 5
                },
                "milestones": [
                    "signal_source",
                    "alien_contact",
                    "first_artifact"
                ],
                "rewards": {
                    "money": 50000,
                    "research_points": 200,
                    "unlock": "DeepSpaceOutpost"
                }
            },
            4: {
                "title": "Research & Discovery",
                "description": "Study ancient alien technology",
                "requirements": {
                    "plot_points": 75,
                    "research_points": 400,
                    "artifacts_found": 3
                },
                "milestones": [
                    "research_hub",
                    "tech_breakthrough",
                    "alien_database"
                ],
                "rewards": {
                    "money": 100000,
                    "research_points": 400,
                    "unlock": "ResearchColony"
                }
            },
            5: {
                "title": "Galactic Crisis",
                "description": "Face an awakening ancient threat",
                "requirements": {
                    "plot_points": 100,
                    "controlled_stations": 3,
                    "research_complete": True
                },
                "milestones": [
                    "crisis_warning",
                    "unite_systems",
                    "final_stand"
                ],
                "rewards": {
                    "money": 500000,
                    "research_points": 1000,
                    "unlock": "legendary_status"
                }
            }
        }

        self.milestone_points = {
            "first_trade": 5,
            "first_combat": 5,
            "basic_license": 5,
            "defeat_pirates": 10,
            "secure_route": 10,
            "establish_base": 10,
            "first_mining": 15,
            "resource_empire": 15,
            "defend_miners": 15,
            "signal_source": 20,
            "alien_contact": 20,
            "first_artifact": 20,
            "research_hub": 25,
            "tech_breakthrough": 25,
            "alien_database": 25,
            "crisis_warning": 30,
            "unite_systems": 30,
            "final_stand": 30
        }

        self.event_rewards = {
            "trade": {
                "base": 1,
                "profit_threshold": 1000,
                "bonus": 2
            },
            "combat": {
                "base": 2,
                "victory_bonus": 3,
                "no_damage_bonus": 2
            },
            "exploration": {
                "base": 3,
                "new_location": 5,
                "artifact_bonus": 10
            },
            "mining": {
                "base": 2,
                "efficiency_threshold": 0.8,
                "bonus": 3
            },
            "research": {
                "base": 3,
                "breakthrough_bonus": 5
            }
        }

    def handle_quest_completion(self, quest):
        """Update story progress when quests complete"""
        for quest_type, milestones in self.quest_milestones.items():
            if quest.quest_type == quest_type:
                for milestone in milestones:
                    if milestone not in self.completed_story_beats:
                        self.complete_milestone(milestone)
                        return


    def process_event(self, event_type, details):
        """Process events and award plot points"""
        if self.check_cooldown(event_type):
            return

        # Calculate base points
        points = self.calculate_points(event_type, details)
        
        # Apply chapter scaling
        points *= (1 + self.current_chapter * 0.2)
        
        # Award points
        self.plot_points += int(points)
        
        # Check milestones
        self.check_milestones(event_type, details)
        
        # Update story states
        self.update_story_states(event_type, details)
        
        # Check chapter progression
        self.check_chapter_progress()

    def calculate_points(self, event_type, details):
        """Calculate points based on event type and details"""
        if event_type not in self.event_rewards:
            return 0
            
        reward = self.event_rewards[event_type]
        points = reward["base"]
        
        # Add conditional bonuses
        if event_type == "trade":
            if details.get("profit", 0) > reward["profit_threshold"]:
                points += reward["bonus"]
                
        elif event_type == "combat":
            if details.get("victory", False):
                points += reward["victory_bonus"]
            if details.get("damage_taken", 0) == 0:
                points += reward["no_damage_bonus"]
                
        elif event_type == "mining":
            if details.get("efficiency", 0) > reward["efficiency_threshold"]:
                points += reward["bonus"]
                
        return points

    def check_cooldown(self, event_type):
        """Prevent event spam with cooldowns"""
        if not hasattr(self, 'cooldowns'):
            self.cooldowns = {}
            
        current_turn = self.game.turn
        if event_type in self.cooldowns:
            if current_turn - self.cooldowns[event_type] < 5:
                return True
                
        self.cooldowns[event_type] = current_turn
        return False

    def check_milestones(self, event_type, details):
        """Check if event triggers any milestones"""
        chapter = self.chapters[self.current_chapter]
        for milestone in chapter["milestones"]:
            if milestone not in self.completed_story_beats:
                if self.check_milestone_requirements(milestone, event_type, details):
                    self.complete_milestone(milestone)

    def check_milestone_requirements(self, milestone, event_type, details):
        """Check if milestone requirements are met"""
        # Milestone requirement logic here
        return True  # Placeholder

    def complete_milestone(self, milestone):
        """Handle milestone completion"""
        if milestone not in self.completed_story_beats:
            self.completed_story_beats.add(milestone)
            points = self.milestone_points.get(milestone, 0)
            self.plot_points += points
            display_name = self.milestone_display_names.get(milestone, milestone.replace("_", " ").title())
            self.game.display_story_message([
                f"Milestone Completed: {display_name}!",
                f"Earned {points} plot points"
            ])

    def check_chapter_progress(self):
        """Check for chapter advancement"""
        next_chapter = self.current_chapter + 1
        if next_chapter in self.chapters:
            requirements = self.chapters[next_chapter]["requirements"]
            
            if self.check_requirements(requirements):
                self.advance_chapter()

    def check_requirements(self, requirements):
        """Check if chapter requirements are met"""
        for req, value in requirements.items():
            if req == "plot_points" and self.plot_points < value:
                return False
            elif req == "combat_victories" and self.game.ship.combat_victories < value:
                return False
            elif req == "research_points" and self.game.ship.research_points < value:
                return False
            # Add other requirement checks
        return True

    def advance_chapter(self):
        """Handle chapter advancement"""
        self.current_chapter += 1
        chapter = self.chapters[self.current_chapter]
        
        # Award chapter rewards
        rewards = chapter["rewards"]
        self.game.ship.money += rewards["money"]
        self.game.ship.research_points += rewards.get("research_points", 0)
        
        # Handle unlocks
        if "unlock" in rewards:
            if rewards["unlock"] in ["AsteroidBase", "DeepSpaceOutpost", "ResearchColony"]:
                self.game.unlock_location_type(rewards["unlock"])
            else:
                self.game.ship.acquire_item(rewards["unlock"])
        
        # Display chapter transition
        self.game.display_story_message([
            f"Chapter {self.current_chapter}: {chapter['title']}",
            chapter["description"],
            "",
            "Rewards:",
            f"• {self.game.format_money(rewards['money'])} credits",
            f"• {rewards.get('research_points', 0)} research points",
            f"• Unlocked: {rewards['unlock']}"
        ])

    def update_story_states(self, event_type, details):
        """Update story state flags based on events"""
        if event_type == "combat" and details.get("enemy_type") == "pirate":
            self.story_states["pirate_threat"] = True
        elif event_type == "exploration" and details.get("discovery_type") == "alien":
            self.story_states["alien_discovery"] = True
        # Add other state updates

    def handle_quest_line_completion(self, quest_line):
        """Update story progress when a quest line is completed"""
        story_impacts = {
            "mining": self.progress_resource_story,
            "combat": self.progress_security_story,
            "research": self.progress_discovery_story,
            "trade": self.progress_empire_story
        }
        
        if quest_line in story_impacts:
            story_impacts[quest_line]()
            self.check_chapter_progress()

    def progress_resource_story(self):
        if not self.story_states["resource_empire"]:
            self.story_states["resource_empire"] = True
            self.plot_points += 15
            self.complete_milestone("resource_empire")

    def progress_security_story(self):
        if not self.story_states["pirate_threat"]:
            self.story_states["pirate_threat"] = True
            self.plot_points += 15
            self.complete_milestone("secure_route")

    def progress_discovery_story(self):
        if not self.story_states["alien_discovery"]:
            self.story_states["alien_discovery"] = True
            self.plot_points += 20
            self.complete_milestone("first_artifact")

    def progress_empire_story(self):
        if not self.story_states["trade_empire"]:
            self.story_states["trade_empire"] = True
            self.plot_points += 25
            self.trigger_milestone("unite_systems")

    def check_discovery_milestone(self, location):
        """Handle discovery of significant locations"""
        location_milestones = {
            "AsteroidBase": "establish_base",
            "DeepSpaceOutpost": "signal_source", 
            "ResearchColony": "research_hub"
        }
        
        if location.location_type in location_milestones:
            self.complete_milestone(location_milestones[location.location_type])

    def get_current_objectives(self):
        """Get current chapter objectives for display"""
        chapter = self.chapters[self.current_chapter]
        incomplete = [m for m in chapter["milestones"] 
                    if m not in self.completed_story_beats]
        return incomplete

    def get_chapter_progress(self):
        """Get current chapter completion percentage"""
        chapter = self.chapters[self.current_chapter]
        completed = sum(1 for m in chapter["milestones"] 
                    if m in self.completed_story_beats)
        return (completed / len(chapter["milestones"])) * 100

    def save_progress(self):
        """Return story progress data for saving"""
        return {
            "chapter": self.current_chapter,
            "plot_points": self.plot_points,
            "completed_beats": list(self.completed_story_beats),
            "story_states": dict(self.story_states)
        }

    def load_progress(self, data):
        """Load story progress from saved data"""
        self.current_chapter = data["chapter"]
        self.plot_points = data["plot_points"]
        self.completed_story_beats = set(data["completed_beats"])
        self.story_states.update(data["story_states"])       

    def trigger_story_event(self, event_id, details=None):
        """Legacy support for story events"""
        if event_id in self.milestone_points:
            self.complete_milestone(event_id)
            return True
        return False

    def enable_story_event(self, event_id):
        """Support for enabling events"""
        if not hasattr(self, 'enabled_events'):
            self.enabled_events = set()
        self.enabled_events.add(event_id)

    def process_story_event(self, event_id):
        """Extension point for modding"""
        if hasattr(self, 'enabled_events') and event_id in self.enabled_events:
            self.process_event("story", {"event_id": event_id})

    def check_event_trigger(self, event, game):
        """Check if an event triggers any story progression"""
        # Handle event triggers based on event name
        if isinstance(event, str):
            if "Pirate" in event:
                self.process_event("combat", {"enemy_type": "pirate"})
            elif "artifact" in event.lower():
                self.process_event("exploration", {"discovery_type": "artifact"})
            elif "trade" in event.lower():
                self.process_event("trade", {})
            elif "research" in event.lower():
                self.process_event("research", {})

class LocationManager:
    """Manages location interactions with story and quest systems"""
    def __init__(self, game):
        self.game = game
        self.location_quests = {
            "AsteroidBase": {
                "unlock_requirements": {
                    "mining_quests_completed": 3,
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
            "ResearchColony": {
                "unlock_requirements": {
                    "research_points": 100,
                    "discoveries": 3
                },
                "unlock_quest": {
                    "name": "Scientific Breakthrough",
                    "description": "Assist in a major research project",
                    "reward_money": 20000,
                    "reward_rp": 200
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
            chapter_bonus = 1.0 + (self.game.story_manager.current_chapter * 0.2)
            
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

            # Check for location-specific events
            if location.location_type in self.location_story_events:
                self.trigger_location_events(location)

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
                
        # Check combat victories
        if "combat_victories" in requirements:
            if self.game.ship.combat_victories < requirements["combat_victories"]:
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
            
            quest = Quest(
                name=quest_data["name"],
                description=quest_data["description"],
                reward_money=quest_data["reward_money"],
                reward_rp=quest_data["reward_rp"],
                quest_type="location_unlock",
                requirements={"location_type": location_type},
                on_complete=lambda: self.complete_location_unlock(location_type)
            )
            
            self.game.quest_system.add_quest(quest)
            self.game.display_story_message([
                f"New Quest Available: {quest_data['name']}",
                quest_data["description"]
            ])

    def complete_location_unlock(self, location_type):
        """Handle the completion of a location unlock quest"""
        # Add location type to unlocked types
        if not hasattr(self.game, 'unlocked_location_types'):
            self.game.unlocked_location_types = set()
        self.game.unlocked_location_types.add(location_type)
        
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
                self.game.quest_system.generate_quest(template["type"], 
                    template["reward_multiplier"])

    def enable_location_story_events(self, location_type):
        """Enable story events specific to the location type"""
        if location_type in self.location_story_events:
            for event in self.location_story_events[location_type]:
                self.game.story_manager.enable_story_event(event)

    def enable_story_event(self, event_id):
        """Enable a story event for potential triggering"""
        if event_id not in self.story_events:
            self.story_events[event_id] = {
                "enabled": True,
                "triggered": False
            }

    def trigger_story_event(self, event_id, details=None):
        """Trigger a story event with details"""
        if event_id in self.story_events:
            event = self.story_events[event_id]
            if event.get("enabled", True) and not event.get("triggered", False):
                # Mark event as triggered
                event["triggered"] = True
                
                # Award plot points
                points = event.get("plot_points", 0)
                self.plot_points += points
                
                # Display event message if available
                if "title" in event and "description" in event:
                    self.game.display_story_message([
                        f"Story Event: {event['title']}",
                        event['description'],
                        f"Gained {points} plot points!"
                    ])
                
                # Handle any special event effects
                if "unlock" in event:
                    self.game.unlock_location_type(event["unlock"])
                
                # Check for chapter progression
                self.check_chapter_progress(self.game)
                
                return True
        return False                

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

class MiningPlatform:
    def __init__(self, resource_type, efficiency):
        self.resource_type = resource_type
        self.efficiency = efficiency  # 0-100%
        self.max_capacity = 0  # Set when geoscan discovers deposit
        self.current_amount = 0
        
    def set_deposit(self, amount):
        """Set deposit size from geoscan"""
        self.max_capacity = amount
        self.current_amount = amount
        
    def replenish(self):
        """Replenish resources based on efficiency"""
        if self.current_amount < self.max_capacity:
            # Calculate replenishment amount (efficiency% of missing amount)
            missing = self.max_capacity - self.current_amount
            replenish_amount = int((missing * self.efficiency) / 100)
            self.current_amount = min(self.max_capacity, self.current_amount + replenish_amount)
            return replenish_amount
        return 0
        
    def remove_resources(self, amount):
        """Remove resources when bought"""
        if amount <= self.current_amount:
            self.current_amount -= amount
            return True
        return False
        
    def get_status(self):
        """Get current mining status"""
        return {
            "current": self.current_amount,
            "maximum": self.max_capacity,
            "efficiency": self.efficiency,
            "replenish_rate": f"{self.efficiency}% of missing amount per turn"
        }

class ResourceTransportQuest:
    def __init__(self, game):
        self.game = game
        self.active_missions = []
        
    def generate_transport_mission(self):
        """Generate a resource transport mission"""
        # Find mining planets
        mining_planets = [loc for loc in self.game.locations 
                         if loc.mining_platforms and 
                         any(p.current_amount > 0 for p in loc.mining_platforms)]
        
        # Find planets with refineries
        refinery_planets = [loc for loc in self.game.locations 
                          if any(b == "Refinery" for b in loc.buildings)]
        
        if not mining_planets or not refinery_planets:
            return None
            
        # Select source and destination
        source = random.choice(mining_planets)
        destination = random.choice(refinery_planets)
        
        # Select resource type and amount
        platform = random.choice([p for p in source.mining_platforms if p.current_amount > 0])
        resource_type = platform.resource_type
        
        # Calculate mission amount (25-50% of available resources)
        available = platform.current_amount
        amount = random.randint(int(available * 0.25), int(available * 0.5))
        
        # Calculate reward (better than normal trading profit)
        base_cost = amount * source.market[resource_type]  # Cost at source
        sell_value = amount * destination.market[resource_type]  # Value at destination
        normal_profit = sell_value - base_cost
        reward = int(normal_profit * 1.5)  # 50% bonus over normal trading
        
        # Create mission
        mission = {
            "type": "transport",
            "resource": resource_type,
            "amount": amount,
            "source": source.name,
            "destination": destination.name,
            "reward": reward,
            "time_limit": 10,  # 10 turns to complete
            "bonus_conditions": {
                "quick_delivery": {"turns": 5, "bonus": int(reward * 0.3)},
                "no_damage": {"bonus": int(reward * 0.2)}
            }
        }
        
        self.active_missions.append(mission)
        return mission
        
    def check_mission_completion(self, ship, current_location):
        """Check if any transport missions are completed"""
        for mission in self.active_missions[:]:  # Copy list to allow removal
            if (current_location.name == mission["destination"] and
                ship.cargo[mission["resource"]] >= mission["amount"]):
                
                # Calculate bonus rewards
                total_reward = mission["reward"]
                bonus_text = []
                
                if mission["time_limit"] > 5:  # Quick delivery bonus
                    total_reward += mission["bonus_conditions"]["quick_delivery"]["bonus"]
                    bonus_text.append(f"Quick Delivery: +{mission['bonus_conditions']['quick_delivery']['bonus']}")
                    
                if ship.damage == 0:  # No damage bonus
                    total_reward += mission["bonus_conditions"]["no_damage"]["bonus"]
                    bonus_text.append(f"Safe Delivery: +{mission['bonus_conditions']['no_damage']['bonus']}")
                
                # Remove resources and give reward
                ship.cargo[mission["resource"]] -= mission["amount"]
                ship.money += total_reward
                
                # Remove completed mission
                self.active_missions.remove(mission)
                
                # Format completion message
                completion_text = [
                    f"Transport Mission Complete!",
                    f"Delivered {mission['amount']} {mission['resource']}",
                    f"Base Reward: {mission['reward']}"]
                if bonus_text:
                    completion_text.extend(bonus_text)
                completion_text.append(f"Total Reward: {total_reward}")
                
                return True, completion_text
                
        return False, None
        
    def update_missions(self):
        """Update mission timers and remove expired missions"""
        for mission in self.active_missions[:]:  # Copy list to allow removal
            mission["time_limit"] -= 1
            if mission["time_limit"] <= 0:
                self.active_missions.remove(mission)
                self.game.display_simple_message(
                    f"Transport mission expired: {mission['amount']} {mission['resource']} " +
                    f"from {mission['source']} to {mission['destination']}"
                )
    
    def display_available_missions(self):
        """Display all available transport missions"""
        if not self.active_missions:
            return [["No active transport missions"]]
            
        mission_content = [["Resource", "Amount", "From", "To", "Reward", "Time"]]
        for mission in self.active_missions:
            mission_content.append([
                mission["resource"].capitalize(),
                str(mission["amount"]),
                mission["source"],
                mission["destination"],
                str(mission["reward"]),
                f"{mission['time_limit']} turns"
            ])
        return mission_content    

class Planet(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "Planet", tech_level, agri_level, research_points, economy)

class AsteroidBase(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "AsteroidBase", tech_level, agri_level, research_points, economy)

class DeepSpaceOutpost(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "DeepSpaceOutpost", tech_level, agri_level, research_points, economy)

class ResearchColony(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "ResearchColony", tech_level, agri_level, research_points, economy)

class LocationTerminology:
    """Manages context-appropriate terminology for different location types"""
    
    TERMS = {
        "Planet": {
            "name": "planet",
            "here": "on this planet",
            "to": "to the planet",
            "at": "on",
            "from": "from the planet",
            "possessive": "planet's",
            "local": "planetary",
            "variants": ["world", "globe", "planetoid"]
        },
        "AsteroidBase": {
            "name": "base",
            "here": "at this base",
            "to": "to the base",
            "at": "at",
            "from": "from the base",
            "possessive": "base's",
            "local": "base",
            "variants": ["asteroid station", "mining post", "rock station"]
        },
        "DeepSpaceOutpost": {
            "name": "outpost",
            "here": "at this outpost",
            "to": "to the outpost",
            "at": "at",
            "from": "from the outpost",
            "possessive": "outpost's",
            "local": "outpost",
            "variants": ["station", "waypoint", "trading post"]
        },
        "ResearchColony": {
            "name": "colony",
            "here": "in this colony",
            "to": "to the colony",
            "at": "in",
            "from": "from the colony",
            "possessive": "colony's",
            "local": "colonial",
            "variants": ["research station", "science base", "research facility"]
        }
    }
    
    @staticmethod
    def get_term(location_type, term_type, use_variant=False):
        """Get appropriate terminology for a location type"""
        terms = LocationTerminology.TERMS.get(location_type, LocationTerminology.TERMS["Planet"])
        if use_variant and random.random() < 0.3:  # 30% chance to use variant
            if term_type == "name":
                return random.choice(terms["variants"])
        return terms.get(term_type, terms["name"])        

# Start the game
if __name__ == "__main__":
    game = Game()
    game.play()
