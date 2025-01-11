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

    # Update Game class methods
    def display_turn_info(self):
        self.clear_screen()
        status_content = [
            ["CΔRGΩ", "Ship", f"{self.current_location.location_type}"],
            [f"Turn: {self.turn}", f"ATK: {self.ship.attack}", f"Name: {self.current_location.name}"],
            [f"¤: {self.format_money(self.ship.money)}", f"DEF: {self.ship.defense}", f"Tech LVL: {self.current_location.tech_level}"],
            [f"Tech: {self.format_money(self.ship.cargo['tech'])}", f"SPD: {self.ship.speed}", f"Agri LVL: {self.current_location.agri_level}"],
            [f"Agri: {self.format_money(self.ship.cargo['agri'])}", f"DMG: {self.ship.damage}%", f"ECO: {self.current_location.economy}"],
            [f"Salt: {self.format_money(self.ship.cargo['salt'])}", f"RP: {self.ship.research_points}", f"EFF: {self.current_location.mining_efficiency}%"],
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
            [f"Tech: {tech_status}", f"Salt: {salt_status if any(p['type'] == 'salt' for p in self.current_location.mining_platforms) else 'No Platform'}"],
            [f"Agri: {agri_status}", f"Fuel: {fuel_status if any(p['type'] == 'fuel' for p in self.current_location.mining_platforms) else 'No Platform'}"]
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
            ["Location Information"],
            [f"Name: {self.current_location.name}"],
            [f"Type: {self.current_location.location_type}"],
            [f"Tech Level: {self.current_location.tech_level}"],
            [f"Agri Level: {self.current_location.agri_level}"],
            [f"Research Points: {self.current_location.research_points}"],
            [f"Economy: {self.current_location.economy}"],
            [f"Mining Efficiency: {self.current_location.mining_efficiency}%"],
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
                'efficiency': self.current_location.mining_efficiency,
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
        """Display initial game information with location context"""
        # Get location info based on current_location
        location_type = "industrial"
        if self.current_location.agri_level > self.current_location.tech_level:
            location_type = "agricultural"
        elif self.current_location.research_points > 15:
            location_type = "research"

        intro_text = f"\n  Welcome {self.player_name} to {self.current_location.name}, a {location_type} {self.current_location.location_type.lower()}, where your adventure begins."
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
                    choice = self.validate_input(
                        "Enter the number of the planet or the location name: ",
                        [str(i) for i in range(1, len(self.known_locations) + 1)] + self.known_locations
                    )
                    if choice:
                        # Handle numeric choice
                        if choice.isdigit():
                            index = int(choice) - 1
                            if 0 <= index < len(self.known_locations):
                                self.travel_to_location(self.known_locations[index])
                        else:
                            self.travel_to_location(choice)
                else:
                    location_name = input("Enter location name to travel: ").strip()
                    if location_name:
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
                    self.current_location.stockmarket_base = True
                    self.current_location.market['tech'] = max(1, self.current_location.market['tech'] - 10)
                    self.current_location.market['agri'] = max(1, self.current_location.market['agri'] - 5)
                    self.display_simple_message(f"Built stock market base for {self.format_money(building_costs['stockmarket'])} money.")
                else:
                    self.display_simple_message(f"Not enough money to build stock market. Cost: {self.format_money(building_costs['stockmarket'])}")
                return

            # Get base cost and multiplier
            base_cost = building_costs.get(building_name.split()[0].lower(), 3000)
            cost_multiplier = self.current_location.buildings.count(full_building_name) + 1
            final_cost = base_cost * cost_multiplier

            # Build if player can afford it
            if self.ship.money >= final_cost:
                self.ship.money -= final_cost
                self.current_location.build_building(full_building_name)
                self.display_simple_message(f"Built {full_building_name} for {self.format_money(final_cost)} money.")

    def travel_to_location(self, location_name):
        """Handle travel to a new location with research points accumulation"""
        for location in self.locations:
            if location.name.lower() == location_name.lower():
                old_location = self.current_location  # Store reference to previous location
                self.current_location = location
                self.display_simple_message(f"Traveled to {location.name}.")
                
                # Calculate research exchange based on location differences
                research_difference = location.research_points - old_location.research_points
                
                # Base gain is the location's research points if first visit
                if location.name not in self.known_locations:
                    base_research = location.research_points
                    self.known_locations.append(location.name)
                    # Trigger location discovery event
                    self.location_manager.handle_location_discovery(location)
                else:
                    # For revisits, only get bonus from research difference if positive
                    base_research = max(0, research_difference)

                # Apply bonus based on research difference
                if research_difference > 0:
                    # Traveling to more advanced location - get bonus
                    research_bonus = int(research_difference * 0.2)  # 20% of the difference
                else:
                    # Traveling to less advanced location - smaller bonus
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
                if location.name not in self.known_locations:
                    self.display_simple_message(f"Gained {total_gain} research points from discovering new location!")
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
            if 'market_manipulation' not in self.research.unlocked_options:
                self.display_simple_message("Market manipulation research required!")
                return
                
            if self.ship.research_points >= self.action.action_costs['market_manipulation']:
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
                    self.ship.research_points -= self.action.action_costs['market_manipulation']
                    success, price_change, message = self.action.manipulate_market(
                        self.current_location, commodity, self.research
                    )
                    self.display_simple_message(message)
            else:
                self.display_simple_message(f"Not enough research points! Need: {self.action.action_costs['market_manipulation']}")
                    
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

    def update_reputation(self, event_type, outcome):
        """Update player reputation based on event outcomes"""
        reputation_changes = {
            "combat": {"victory": 2, "defeat": -1},
            "trade": {"success": 1, "embargo": -1},
            "exploration": {"discovery": 3, "failure": 0},
            "disaster": {"survived": 1, "major_damage": -1}
        }
        
        change = reputation_changes.get(event_type, {}).get(outcome, 0)
        self.reputation = max(0, min(100, self.reputation + change))
        
        # Check for rank changes
        self.update_rank()


    def random_event(self):
        """Enhanced random event handler with complete implementation"""
        # Define all possible events with their categories
        event_result = self.generate_random_event()  # Previous implementation
        
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
        
        # Select event category based on ship's condition and location
        weights = []
        categories = list(events.keys())
        
        for category in categories:
            base_weight = modifiers[category]
            
            # Adjust weights based on ship condition
            if category == "combat":
                if self.ship.damage > 70:
                    base_weight *= 0.2  # Reduce combat chance when damaged
                elif "turrets" in self.ship.items:
                    base_weight *= 0.7  # Reduce combat chance with turrets
            
            # Adjust for cargo status
            elif category == "trade":
                if all(self.ship.cargo[item] == 0 for item in ['tech', 'agri', 'salt', 'fuel']):
                    base_weight *= 0.3  # Reduce trade events without cargo
            
            # Adjust for equipment
            elif category == "exploration":
                if "scanner" in self.ship.items:
                    base_weight *= 1.3  # Increase exploration chance with scanner
            
            weights.append(base_weight)
        
        # Normalize weights
        total_weight = sum(weights)
        weights = [w/total_weight for w in weights]
        
        # Select category and event
        category = random.choices(categories, weights=weights)[0]
        event = random.choice(events[category])
        
        # Log the event
        self.event_log.append({
            'turn': self.turn,
            'event': event,
            'category': category,
            'location': self.current_location.name
        })
        
        # Handle event based on category
        if category == "combat":
            self.handle_combat_event(event)
        elif category == "trade":
            self.handle_trade_event(event)
        elif category == "exploration":
            self.handle_exploration_event(event)
        elif category == "disaster":
            self.handle_disaster_event(event)
        
        # Update story progression if applicable
        self.story_manager.check_event_trigger(event, self)

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
                
            elif event_result["type"] == "disaster":
                damage_taken = self.ship.damage - details["initial_damage"]
                details["damage_taken"] = damage_taken
                details["outcome"] = "major_damage" if damage_taken > 40 else "survived"
                details["reputation_change"] = 1 if damage_taken < 20 else -1
            
            # Calculate specific losses
            details["cargo_lost"] = {
                item: details["cargo_before"][item] - self.ship.cargo[item]
                for item in self.ship.cargo
                if details["cargo_before"][item] - self.ship.cargo[item] > 0
            }
            
            details["money_lost"] = max(0, details["money_before"] - self.ship.money)
                
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
                "Choose action (buy map/bm, update map/um, listen to gossip/lg, quests/q): ",
                ['buy map', 'bm', 'update map', 'um', 'listen to gossip', 'lg', 'quests', 'q']
            )

            if action is None:
                return

            if action in ['buy map', 'bm']:
                if self.ship.money >= 200:
                    self.ship.money -= 200
                    self.display_simple_message("You bought a map! Here are some new planet names and levels:", 1)
                    for planet in self.locations:
                        if planet.name not in self.known_locations:
                            print(f"{planet.name} (Tech: {planet.tech_level}, Agri: {planet.agri_level})")
                else:
                    self.display_simple_message("Not enough money to buy a map.")
            elif action in ['update map', 'um']:
                if self.ship.money >= 350:
                    self.ship.money -= 350
                    self.display_simple_message("You updated the map! Here are the commodities wanted:", 1)
                    for planet in self.locations:
                        print(f"{planet.name}: Tech - {self.format_money(planet.market['tech'])}, Agri - {self.format_money(planet.market['agri'])}")
                else:
                    self.display_simple_message("Not enough money to update the map.")
            elif action in ['listen to gossip', 'lg']:
                if self.ship.money >= 150:
                    self.ship.money -= 150
                    self.display_simple_message("You listened to gossip! Here are some tips:", 1)
                    for planet in self.locations:
                        if planet.market['tech'] < 50:
                            print(f"Cheap tech goods available on {planet.name}.")
                        if planet.market['agri'] < 30:
                            print(f"Cheap agri goods available on {planet.name}.")
                        if planet.market['tech'] > 100:
                            print(f"High price on tech goods on {planet.name}.")
                        if planet.market['agri'] > 80:
                            print(f"High price on agri goods on {planet.name}.")
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
                    self.display_simple_message("Not enough money to listen to gossip.")
            elif action in ['quests', 'q']:
                active_quests = [q for q in self.quest_system.active_quests if isinstance(q, Quest)]
                if active_quests:
                    self.display_simple_message("Active Quests:")
                    for quest in active_quests:
                        print(f"- {quest.name}: {quest.description}")
                else:
                    self.display_simple_message("No active quests.")
                    
            # Randomly introduce a demo character after reaching a new rank
            if random.random() < 0.1:  # 10% chance
                self.display_character_message("Mysterious Stranger", "Greetings, traveler. I hear you've been making a name for yourself. Keep it up, and you might just become a legend.")

            time.sleep(3)  # Pause to let the player read the information

    def shop(self):
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
            if self.action.research(self.current_location, 'mining_efficiency', self.research):
                self.display_simple_message("Mining efficiency research completed!")
            else:
                self.display_simple_message("Not enough research points!")

    def display_mining_status(self):
        """Display mining operations status"""
        content = [
            ["Mining Status"],
            [f"Planet Efficiency: {self.current_location.mining_efficiency}%"],
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
            location.mining_efficiency += 20  # Better mining in new locations
            location.research_points *= 2     # Double research points
            location.tech_level += 2         # Higher tech levels
            
            # Special location-type bonuses
            if isinstance(location, AsteroidBase):
                location.mining_efficiency += 10  # Extra mining bonus
            elif isinstance(location, DeepSpaceOutpost):
                location.market['tech'] = max(1, location.market['tech'] * 0.8)  # Better tech prices
                
        return new_locations

#New additions to the game system

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
        self.mining_efficiency = self.get_base_mining_efficiency()
        self.banned_commodities = []
        self.ban_duration = {}
        self.mineral_deposits = {}
        self.mining_platforms = []
        self.production_cooldown = {}
        # Generate market after initializing attributes
        self.market = self.generate_market()

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
        """Generate initial market prices based on location attributes"""
        tech_price = 100 - (self.tech_level * 10)
        agri_price = 50 + (self.agri_level * 5)
        return {
            'tech': tech_price,
            'agri': agri_price,
            'salt': 0,
            'fuel': 0
        }

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
        """Build a building and apply its effects"""
        if not self.can_build(building_name):
            return 0  # Return 0 to indicate building not allowed
            
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
        """Check if this location can build a specific building"""
        return building_type in self.get_capabilities().get("can_build", [])

    def can_mine(self, resource_type):
        """Check if this location can mine a specific resource"""
        return resource_type in self.get_capabilities().get("can_mine", [])

    def get_base_mining_efficiency(self):
        """Get base mining efficiency for this location type"""
        return self.get_capabilities().get("base_mining_efficiency", 0)

    def get_research_multiplier(self):
        """Get research point multiplier for this location type"""
        return self.get_capabilities().get("research_multiplier", 1.0)          

class Planet(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "Planet", tech_level, agri_level, research_points, economy)

class AsteroidBase(Location):
    def __init__(self, name, tech_level, agri_level, research_points, economy):
        super().__init__(name, "Asteroid Base", tech_level, agri_level, research_points, economy)
        self.mining_efficiency += 20  # Asteroid bases have better mining
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
        self.chapter_statistics = {}
        self.story_progress = {}
        self.discovered_locations_by_type = {}
        self.chapter_start_money = 0
        self.chapter_start_quests = 0
        self.chapter_start_locations = 0
        self.chapter_start_combat_victories = 0
        
        # Initialize discovery milestones
        self.discovery_milestones = {
            "AsteroidBase": {
                "count": 1,
                "reward_money": 10000,
                "reward_rp": 100,
                "plot_points": 5,
                "story_event": "asteroid_base_discovery"
            },
            "DeepSpaceOutpost": {
                "count": 1,
                "reward_money": 15000,
                "reward_rp": 150,
                "plot_points": 7,
                "story_event": "outpost_discovery"
            },
            "ResearchColony": {
                "count": 1,
                "reward_money": 20000,
                "reward_rp": 200,
                "plot_points": 10,
                "story_event": "research_colony_discovery"
            }
        }
        
        # Initialize chapter data
        self.chapters = {
            0: {
                "title": "A New Beginning",
                "requirements": {"quests_completed": 0, "plot_points": 0},
                "story_beats": [
                    "first_trade",
                    "first_quest",
                    "first_combat"
                ]
            },
            1: {
                "title": "Strange Signals",
                "requirements": {"quests_completed": 5, "plot_points": 10},
                "story_beats": [
                    "discover_asteroid_base",
                    "investigate_signal",
                    "meet_researcher"
                ]
            },
            2: {
                "title": "Deep Space Mysteries",
                "requirements": {"quests_completed": 10, "plot_points": 25},
                "story_beats": [
                    "discover_outpost",
                    "alien_artifact",
                    "mysterious_transmission"
                ]
            },
            3: {
                "title": "Research and Discovery",
                "requirements": {"quests_completed": 15, "plot_points": 50},
                "story_beats": [
                    "discover_research_colony",
                    "ancient_technology",
                    "breakthrough_discovery"
                ]
            }
        }
        self.story_events = {
            "first_trade": {
                "title": "First Steps",
                "description": "Complete your first trade",
                "plot_points": 2
            },
            "discover_asteroid_base": {
                "title": "Hidden in the Rocks",
                "description": "Discover an asteroid base",
                "plot_points": 5,
                "unlock": "AsteroidBase"
            }
            # Add more story events as needed
        }

    def process_event(self, trigger, details):
        """Process story triggers with full event details and consequences"""
        if trigger in self.completed_story_beats:
            return  # Don't process the same story beat twice
            
        event_location = details.get('location', '')
        timestamp = details.get('timestamp', 0)
        
        # Define rewards and consequences for different story beats
        story_impacts = {
            # Combat-related story beats
            "pirate_defeat": {
                "plot_points": 3,
                "reputation": 2,
                "unlock": "combat_specialist",
                "message": "Your victory against pirates has been noticed!"
            },
            "defend_station": {
                "plot_points": 4,
                "reputation": 3,
                "unlock": "station_defender",
                "message": "The station is safe thanks to your efforts!"
            },
            
            # Exploration story beats
            "new_artifact": {
                "plot_points": 5,
                "reputation": 2,
                "unlock": "archaeologist",
                "message": "Your discovery will be studied by researchers!"
            },
            "alien_ruins": {
                "plot_points": 6,
                "reputation": 3,
                "unlock": "xenoarchaeologist",
                "message": "The ruins hold secrets of ancient civilizations!"
            },
            
            # Trading story beats
            "trade_monopoly": {
                "plot_points": 4,
                "reputation": 2,
                "unlock": "master_trader",
                "message": "Your trading empire grows!"
            },
            "market_dominance": {
                "plot_points": 5,
                "reputation": 3,
                "unlock": "market_manipulator",
                "message": "You've become a significant market force!"
            },
            
            # Research story beats
            "breakthrough": {
                "plot_points": 5,
                "reputation": 2,
                "unlock": "scientist",
                "message": "Your research has yielded results!"
            },
            "innovation": {
                "plot_points": 6,
                "reputation": 3,
                "unlock": "innovator",
                "message": "Your innovation changes everything!"
            },
            
            # Crisis story beats
            "emergency_repair": {
                "plot_points": 3,
                "reputation": 1,
                "unlock": "crisis_expert",
                "message": "Quick thinking saved the day!"
            },
            "crisis_management": {
                "plot_points": 4,
                "reputation": 2,
                "unlock": "emergency_specialist",
                "message": "Your leadership during crisis is noted!"
            }
        }
        
        # Get impact details for this trigger
        impact = story_impacts.get(trigger, {
            "plot_points": 1,
            "reputation": 0,
            "message": "Story continues..."
        })
        
        # Apply performance-based bonuses
        if "damage_taken" in details:
            damage = details["damage_taken"]
            if damage < 10:
                impact["plot_points"] += 2  # Excellent performance
                impact["reputation"] += 1
            elif damage < 20:
                impact["plot_points"] += 1  # Good performance
            
        # Apply location-specific bonuses
        if isinstance(details.get('location_type'), "ResearchColony"):
            if 'research' in trigger:
                impact["plot_points"] *= 1.5  # Bonus for research at appropriate location
                
        elif isinstance(details.get('location_type'), "DeepSpaceOutpost"):
            if 'combat' in trigger:
                impact["plot_points"] *= 1.5  # Bonus for combat at appropriate location
                
        # Record story progress with all details
        self.story_progress[trigger] = {
            "completed_at": timestamp,
            "location": event_location,
            "chapter": self.current_chapter,
            "performance_details": {
                "damage_taken": details.get("damage_taken", 0),
                "cargo_lost": details.get("cargo_lost", {}),
                "money_lost": details.get("money_lost", 0)
            }
        }
        
        # Update plot points
        earned_points = int(impact["plot_points"])
        self.plot_points += earned_points
        
        # Add to completed story beats
        self.completed_story_beats.add(trigger)
        
        # Handle special unlocks
        if "unlock" in impact:
            self.unlock_achievement(impact["unlock"])
        
        # Check for chapter-specific consequences
        self.handle_chapter_consequences(trigger, details)
        
        # Generate appropriate message
        message_lines = [
            impact["message"],
            f"Earned {earned_points} plot points!",
        ]
        
        if "unlock" in impact:
            message_lines.append(f"Unlocked: {impact['unlock'].replace('_', ' ').title()}!")
            
        # Display results
        self.game.display_story_message(message_lines)
        
        # Check for chapter progression
        if self.check_chapter_requirements():
            self.advance_chapter()

    def check_discovery_milestone(self, location):
        """Check if discovering this location triggers any milestones"""
        location_type = location.location_type
        
        # Initialize counter for this location type if not exists
        if location_type not in self.discovered_locations_by_type:
            self.discovered_locations_by_type[location_type] = 0
        
        # Increment counter
        self.discovered_locations_by_type[location_type] += 1
        
        # Check if milestone exists and is reached
        if location_type in self.discovery_milestones:
            milestone = self.discovery_milestones[location_type]
            if self.discovered_locations_by_type[location_type] == milestone["count"]:
                # Award rewards
                self.game.ship.money += milestone["reward_money"]
                self.game.ship.research_points += milestone["reward_rp"]
                self.plot_points += milestone["plot_points"]
                
                # Trigger story event
                if "story_event" in milestone:
                    self.trigger_story_event(milestone["story_event"], {
                        "location": location.name,
                        "type": location_type
                    })
                
                # Display milestone message
                self.game.display_story_message([
                    f"Discovery Milestone: First {location_type} Found!",
                    f"Bonus Rewards:",
                    f"• {self.game.format_money(milestone['reward_money'])} credits",
                    f"• {milestone['reward_rp']} research points",
                    f"• {milestone['plot_points']} plot points"
                ])
                
                # Check for chapter progression
                self.check_chapter_progress(self.game)

    def handle_chapter_consequences(self, trigger, details):
        """Handle chapter-specific story consequences"""
        chapter_consequences = {
            0: {  # Tutorial chapter
                "pirate_defeat": self.unlock_basic_combat,
                "trade_monopoly": self.unlock_basic_trading,
                "new_artifact": self.unlock_basic_exploration
            },
            1: {  # Early game
                "defend_station": self.unlock_station_missions,
                "breakthrough": self.unlock_research_missions,
                "crisis_management": self.unlock_emergency_missions
            },
            2: {  # Mid game
                "alien_ruins": self.unlock_alien_technology,
                "market_dominance": self.unlock_market_manipulation,
                "innovation": self.unlock_advanced_research
            },
            3: {  # Late game
                "master_trader": self.unlock_trade_empire,
                "xenoarchaeologist": self.unlock_ancient_secrets,
                "crisis_expert": self.unlock_crisis_mastery
            }
        }
        
        # Get consequences for current chapter
        chapter_triggers = chapter_consequences.get(self.current_chapter, {})
        if trigger in chapter_triggers:
            consequence_function = chapter_triggers[trigger]
            consequence_function()

    def check_chapter_requirements(self):
        """Check if requirements are met for chapter advancement"""
        chapter_requirements = {
            0: {"plot_points": 10, "story_beats": 3},
            1: {"plot_points": 25, "story_beats": 5},
            2: {"plot_points": 50, "story_beats": 8},
            3: {"plot_points": 100, "story_beats": 12}
        }
        
        if self.current_chapter not in chapter_requirements:
            return False
            
        req = chapter_requirements[self.current_chapter]
        completed_beats = len([b for b in self.completed_story_beats 
                             if self.story_progress[b]["chapter"] == self.current_chapter])
                             
        return (self.plot_points >= req["plot_points"] and 
                completed_beats >= req["story_beats"])

    def check_chapter_progress(self, game):
        """Check if player can progress to next chapter"""
        next_chapter = self.current_chapter + 1
        if next_chapter in self.chapters:
            requirements = self.chapters[next_chapter]["requirements"]
            if (len(game.quest_system.completed_quests) >= requirements["quests_completed"] and
                self.plot_points >= requirements["plot_points"]):
                self.advance_chapter(game)

    def advance_chapter(self):
        """Advance to the next story chapter with full progression handling"""
        old_chapter = self.current_chapter
        self.current_chapter += 1
        
        # Chapter definitions with names, descriptions, and rewards
        chapters = {
            1: {
                "name": "The Beginning of Adventure",
                "description": "Your first steps into the vast galaxy...",
                "rewards": {
                    "money": 5000,
                    "research_points": 50,
                    "reputation": 10
                },
                "unlocks": {
                    "locations": ["AsteroidBase"],
                    "quests": ["pirate_hunting", "mineral_survey"],
                    "equipment": ["advanced_scanner", "mining_laser"]
                }
            },
            2: {
                "name": "Rising Challenges",
                "description": "Your reputation grows as new threats emerge...",
                "rewards": {
                    "money": 15000,
                    "research_points": 100,
                    "reputation": 20
                },
                "unlocks": {
                    "locations": ["DeepSpaceOutpost"],
                    "quests": ["station_defense", "trade_monopoly"],
                    "equipment": ["combat_drone", "shield_booster"]
                }
            },
            3: {
                "name": "Galactic Impact",
                "description": "Your actions shape the future of the galaxy...",
                "rewards": {
                    "money": 50000,
                    "research_points": 200,
                    "reputation": 30
                },
                "unlocks": {
                    "locations": ["ResearchColony"],
                    "quests": ["alien_artifacts", "breakthrough_research"],
                    "equipment": ["quantum_scanner", "ai_assistant"]
                }
            },
            4: {
                "name": "Legend of the Stars",
                "description": "Your name becomes legend throughout the galaxy...",
                "rewards": {
                    "money": 150000,
                    "research_points": 500,
                    "reputation": 50
                },
                "unlocks": {
                    "locations": ["AncientRuins", "AlienOutpost"],
                    "quests": ["galactic_peace", "technological_ascension"],
                    "equipment": ["alien_tech", "stellar_manipulator"]
                }
            }
        }
        
        # Get current chapter info
        chapter = chapters.get(self.current_chapter)
        if not chapter:
            # Handle game completion if no more chapters
            self.handle_game_completion()
            return
            
        # Display chapter transition
        self.game.display_story_message([
            f"Chapter {self.current_chapter}: {chapter['name']}",
            "",
            chapter['description']
        ], style='double', color='32')  # Green color for achievement
        
        # Award chapter completion rewards
        rewards = chapter['rewards']
        self.game.ship.money += rewards['money']
        self.game.ship.research_points += rewards['research_points']
        self.game.reputation += rewards['reputation']
        
        # Display rewards
        self.game.display_story_message([
            "Chapter Rewards Earned:",
            f"• Credits: {self.game.format_money(rewards['money'])}",
            f"• Research Points: {rewards['research_points']}",
            f"• Reputation: +{rewards['reputation']}"
        ])
        
        # Unlock new content
        unlocks = chapter['unlocks']
        
        # Unlock new locations
        for location_type in unlocks['locations']:
            self.game.unlock_location_type(location_type)
            self.game.display_simple_message(f"New location type unlocked: {location_type}!")
            
        # Add new quests
        for quest_type in unlocks['quests']:
            self.game.quest_system.add_quest_type(quest_type)
            self.game.display_simple_message(f"New quest type available: {quest_type.replace('_', ' ').title()}!")
            
        # Unlock new equipment
        for equipment in unlocks['equipment']:
            self.game.shop.add_equipment(equipment)
            self.game.display_simple_message(f"New equipment available: {equipment.replace('_', ' ').title()}!")
        
        # Update game difficulty and challenges
        self.update_chapter_difficulty()
        
        # Trigger chapter-specific events
        self.trigger_chapter_events()
        
        # Save chapter progress
        self.save_chapter_progress(old_chapter)

    def update_chapter_difficulty(self):
        """Update game difficulty based on current chapter"""
        # Increase enemy strength
        self.game.combat_difficulty = 1.0 + (self.current_chapter * 0.2)
        
        # Adjust market volatility
        self.game.market_volatility = 1.0 + (self.current_chapter * 0.15)
        
        # Scale event frequency
        self.game.event_frequency = min(0.4 + (self.current_chapter * 0.1), 0.8)
        
        # Add chapter-specific challenges
        if self.current_chapter >= 2:
            self.game.enable_pirate_fleets = True
        if self.current_chapter >= 3:
            self.game.enable_alien_encounters = True
        if self.current_chapter >= 4:
            self.game.enable_space_anomalies = True

    def trigger_chapter_events(self):
        """Trigger events specific to the new chapter"""
        chapter_events = {
            1: self.trigger_tutorial_completion,
            2: self.trigger_rising_threats,
            3: self.trigger_galactic_crisis,
            4: self.trigger_final_challenges
        }
        
        if self.current_chapter in chapter_events:
            chapter_events[self.current_chapter]()

    def save_chapter_progress(self, old_chapter):
        """Save progress and statistics for the completed chapter"""
        self.chapter_statistics[old_chapter] = {
            "completion_turn": self.game.turn,
            "money_earned": self.game.ship.money - self.chapter_start_money,
            "quests_completed": len(self.game.quest_system.completed_quests) - self.chapter_start_quests,
            "locations_discovered": len(self.game.known_locations) - self.chapter_start_locations,
            "combat_victories": self.game.ship.combat_victories - self.chapter_start_combat_victories
        }
        
        # Update starting points for next chapter
        self.chapter_start_money = self.game.ship.money
        self.chapter_start_quests = len(self.game.quest_system.completed_quests)
        self.chapter_start_locations = len(self.game.known_locations)
        self.chapter_start_combat_victories = self.game.ship.combat_victories

    def handle_game_completion(self):
        """Handle the completion of all chapters"""
        self.game.display_story_message([
            "Congratulations! You have completed all chapters!",
            "Your legend will live forever in the galaxy!",
            "",
            "You may continue playing to discover all secrets..."
        ], style='double', color='32')
        
        # Award final rewards
        final_rewards = {
            "money": 500000,
            "research_points": 1000,
            "reputation": 100,
            "special_item": "Legendary Captain's Badge"
        }
        
        self.game.ship.money += final_rewards['money']
        self.game.ship.research_points += final_rewards['research_points']
        self.game.reputation += final_rewards['reputation']
        self.game.ship.acquire_item(final_rewards['special_item'])
        
        # Enable endgame content
        self.game.enable_endgame_content()

    def trigger_story_event(self, event_id, game):
        """Trigger a story event and award plot points"""
        if event_id not in self.completed_story_beats:
            event = self.story_events[event_id]
            self.plot_points += event["plot_points"]
            self.completed_story_beats.add(event_id)
            
            game.display_story_message([
                f"Story Event: {event['title']}",
                event['description'],
                f"Gained {event['plot_points']} plot points!"
            ])
            
            # Handle location unlocks
            if "unlock" in event:
                game.unlock_location_type(event["unlock"])
            
            self.check_chapter_progress(game)



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

    def unlock_chapter_locations(self, chapter):
        """Unlock chapter-specific locations"""
        if chapter in self.chapter_locations:
            for location_type, locations in self.chapter_locations[chapter].items():
                self.unlocked_location_types.add(location_type)
                self.locations.extend(locations)
                
                self.display_story_message([
                    f"Chapter {chapter} Locations Unlocked!",
                    f"New {location_type}s have been discovered.",
                    "These mysterious places hold great opportunities..."
                ])

    def get_location_by_name(self, name):
        """Get a location by its name, including hidden ones"""
        # Check current locations
        for location in self.locations:
            if location.name.lower() == name.lower():
                return location
        
        # Check hidden locations
        for locations in self.hidden_locations.values():
            for location in locations:
                if location.name.lower() == name.lower():
                    return location
        
        # Check chapter-specific locations
        for chapter_locs in self.chapter_locations.values():
            for locations in chapter_locs.values():
                for location in locations:
                    if location.name.lower() == name.lower():
                        return location
        
        return None

    def get_available_locations(self):
        """Get all currently available locations for travel"""
        return [loc for loc in self.locations 
                if loc.location_type in self.unlocked_location_types]

    def count_locations_by_type(self):
        """Count number of discovered locations by type"""
        counts = {}
        for location in self.locations:
            if location.location_type in self.unlocked_location_types:
                counts[location.location_type] = counts.get(location.location_type, 0) + 1
        return counts

    def handle_quest_completion(self, quest):
        """Handle quest completion and story progression"""
        rewards = self.quest_system.complete_quest(quest)
        self.ship.money += rewards["money"]
        self.ship.research_points += rewards["research_points"]
        
        # Check for story progression
        if quest[1] == "story":
            self.story_manager.trigger_story_event(quest[0], self)
        elif len(self.quest_system.completed_quests) in [5, 10, 15]:
            # Major quest milestones trigger story progression
            self.story_manager.check_chapter_progress(self) 

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
            "base_mining_efficiency": 100,
            "research_multiplier": 1.0
        },
        "AsteroidBase": {
            "can_trade": ["salt", "fuel"],
            "can_build": ["mining", "stockmarket"],
            "can_produce": [],
            "can_mine": ["salt", "fuel"],
            "has_cantina": True,
            "has_shop": True,
            "base_mining_efficiency": 150,  # Better at mining
            "research_multiplier": 0.8
        },
        "DeepSpaceOutpost": {
            "can_trade": ["tech", "agri"],
            "can_build": ["stockmarket", "nanotech"],
            "can_produce": ["tech"],
            "can_mine": [],
            "has_cantina": True,
            "has_shop": True,
            "base_mining_efficiency": 0,
            "research_multiplier": 1.2
        },
        "ResearchColony": {
            "can_trade": ["tech"],
            "can_build": ["nanotech", "neuroengineering"],
            "can_produce": ["tech"],
            "can_mine": [],
            "has_cantina": False,
            "has_shop": True,
            "base_mining_efficiency": 0,
            "research_multiplier": 2.0
        }
    }


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
