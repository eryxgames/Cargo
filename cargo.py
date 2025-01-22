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
            "Pilot": 2,
            "Captain": 3,
            "Commander": 4,
            "Star Commander": 6,
            "Space Admiral": 8,
            "Stellar Hero": 10,
            "Galactic Legend": 15
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
    def __init__(self, game=None):
        self.game = game
        # Basic cargo and resources
        self.cargo = {
            'tech': 0,
            'agri': 0,
            'salt': 0,
            'fuel': 0
        }
        self.money = 1000000
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
            if enemy_type in self.combat_victories:
                self.combat_victories[enemy_type] += 1

    def record_combat_defeat(self, enemy_type=None):
        """Record a combat defeat with proper type tracking"""
        self.combat_defeats['total'] += 1
        if enemy_type:
            if enemy_type in self.combat_defeats:
                self.combat_defeats[enemy_type] += 1

    def buy(self, item, quantity, price, planet, player_rank):
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
                ('action', 'a'), ('mine', 'm'), ('port', 'p'), ('end', 'e')
            ],
            "description": "Standard planetary commerce hub"
        },
        "AsteroidBase": {
            "base_commands": [
                ('buy', 'b'), ('sell', 's'), ('upgrade', 'u'),
                ('travel', 't'), ('repair', 'r'), ('info', 'i'),
                ('build', 'bl'), ('cantina', 'c'), ('shop', 'sh'),
                ('action', 'a'), ('mine', 'm'), ('port', 'p'), ('end', 'e')
            ],
            "description": "Mining and resource extraction facility"
        },
        "DeepSpaceOutpost": {
            "base_commands": [
                ('buy', 'b'), ('sell', 's'), ('upgrade', 'u'),
                ('travel', 't'), ('repair', 'r'), ('info', 'i'),
                ('build', 'bl'), ('cantina', 'c'), ('shop', 'sh'),
                ('action', 'a'), ('port', 'p'), ('end', 'e')
            ],
            "description": "Strategic trading outpost"
        },
        "ResearchColony": {
            "base_commands": [
                ('buy', 'b'), ('sell', 's'), ('upgrade', 'u'),
                ('travel', 't'), ('research', 'r'), ('info', 'i'),
                ('build', 'bl'), ('shop', 'sh'), ('action', 'a'),
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
        self.ship.game = self  # connect ship to game
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
        self.character_system = DynamicCharacterSystem(self)
        self.character_encounters = SpecialCharacterEncounters(self)
        self.discovered_locations = set()
        self.cooldowns = {}
        self.story_events = {}
        self.character_manager = CharacterManager(self)
        self.infestation_manager = InfestationManager(self)

        # Initialize the story
        self.story_manager.start_game()        
        
        self.display_starting_info()



    # Modified Ship class initialization to include passenger modules
    def init_ship(self):
        self.ship = Ship()
        self.ship.passenger_modules = []  # Initialize empty passenger modules list
        self.ship.passenger_reputation = 0  # Initialize passenger reputation

    # Initialize reputation manager in Game class
    def init_reputation_system(self):
        self.reputation_manager = PassengerReputationManager(self)

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
            row_content = f" {('' + chars['sep'] + ' ').join(formatted_cells)}"
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

    def create_character_box(self, character_content, style='round'):
        """Create a character display box optimized for different terminal widths"""
        try:
            term_width = os.get_terminal_size().columns
        except OSError:
            term_width = 80  # Default width
            
        # Adjust width based on terminal size
        if term_width < 60:
            content_width = term_width - 4
            compact_mode = True
        else:
            content_width = min(80, term_width - 4)  # Cap at 80 chars
            compact_mode = False
            
        chars = {
            'round': {'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯', 'h': '─', 'v': '│'},
            'double': {'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝', 'h': '═', 'v': '║'},
            'single': {'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘', 'h': '─', 'v': '│'}
        }[style]
        
        lines = []
        lines.append(f"{chars['tl']}{chars['h'] * content_width}{chars['tr']}")
        
        # Process title section
        if 'title' in character_content:
            wrapped_title = self.word_wrap(character_content['title'], content_width - 2)
            for line in wrapped_title:
                lines.append(f"{chars['v']} {line:<{content_width-2}} {chars['v']}")
            lines.append(f"{chars['v']}{chars['h'] * content_width}{chars['v']}")
        
        # Process main content with proper sections
        for section in ['introduction', 'description', 'demands', 'options']:
            if section in character_content:
                if not compact_mode:
                    lines.append(f"{chars['v']}{' ' * content_width}{chars['v']}")
                
                wrapped_content = self.word_wrap(character_content[section], content_width - 2)
                for line in wrapped_content:
                    lines.append(f"{chars['v']} {line:<{content_width-2}} {chars['v']}")
        
        lines.append(f"{chars['bl']}{chars['h'] * content_width}{chars['br']}")
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

    def fast_message(self, message, pause=0.5, style='round', color=None, clear_screen=True):
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
        if clear_screen:
            self.clear_screen()            

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

    def handle_contract_menu(self):
        """Route contract menu handling to ContractManager"""
        if not hasattr(self, 'contract_manager'):
            self.contract_manager = ContractManager(self)
        self.contract_manager.handle_contract_menu()

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

    def validate_input(self, default_prompt, valid_options, prompt=None):
            """
            Validate user input against a list of valid options
            default_prompt: Default prompt text
            valid_options: List of valid input options
            prompt: Optional custom prompt to override default
            """
            term_width = shutil.get_terminal_size().columns

            while True:
                wrapped_prompt = self.word_wrap(prompt or default_prompt, term_width - 4)
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
            [f"PAX: {total_passengers}/{total_capacity}", f"REP: {self.ship.passenger_reputation}", ""]
        ]
        
        # Add story progress if available
        if hasattr(self, 'story_manager'):
            current_chapter = self.story_manager.chapters[self.story_manager.current_chapter]
            status_content.append([
                f"Chapter {self.story_manager.current_chapter}",
                f"Plot Points: {self.story_manager.plot_points}",
                current_chapter.title
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

        # Display commands including port
        commands = [
            ["Commands: buy/b, sell/s, travel/t, port/p, cantina/c, shop/sh, upgrade/u, repair/r, action/a, mine/m, build/bl, log/l, info/i..."],
        
        ]
    #    print(self.create_box(commands, 'round'))
        self.display_simple_message(f"Commands: buy/b, sell/s, travel/t, port/p, cantina/c, shop/sh, upgrade/u, repair/r, action/a, mine/m, build/bl, log/l, info/i...", 1)

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
            content.append(["Active Infestations:"])
            for name, infestation in self.ship.active_infestations.items():
                content.append([
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
            location_line = location_info[i][0] if i < len(location_info) else ""
            content.append([ship_line, location_line])

        print(self.create_box(content, 'double'))
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
#            ["DIFFICULTY SELECTION"],
            [""],
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
            self.character_system.check_character_triggers() # Check for dynamic characters system
            # New chapter and milestone system
            self.story_manager.check_milestone_progress()
            self.story_manager.check_chapter_progress()

            # Get location commands
            location_commands = self.current_location.commands

            self.character_manager.update()

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
            valid_actions.extend(['quit', 'q', 'resign', 'rs', 'version', 'v'])
            valid_actions.extend(['log', 'l'])  # Add but don't show in command hints

            action = self.validate_input("Choose action: ", valid_actions)

            # Handle cancelled command
            if action is None:
                return
                        
            # Handle research/repair based on location type
            elif action in ['research', 'r']:
                if isinstance(self.current_location, ResearchColony):
                    self.handle_research_options()
                elif action == 'r':  # Only handle repair if 'r' and not at Research Colony
                    if self.ship.damage > 0:
                        cost = self.ship.damage * 10
                        if self.ship.repair(cost):
                            self.display_simple_message("Ship repaired.")
                        else:
                            self.display_simple_message(
                                f"Not enough money to repair. Cost: {self.format_money(cost)}"
                            )
                    else:
                        self.display_simple_message("Ship doesn't need repairs.")            

            elif action in ['buy', 'b']:
                item = self.validate_input("Choose item (tech/agri/salt/fuel): ", 
                                        ['tech', 'agri', 'salt', 'fuel'])
                if item is None:
                    return

                if not self.current_location.can_trade(item):
                    self.display_simple_message(f"Trading of {item} is banned on this planet!")
                    return

                if item in ['salt', 'fuel']:
                    has_platform = any(p['type'] == item for p in self.current_location.mining_platforms)
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
                    
                tax_rate = self.current_location.calculate_tax_rate(self.rank, price)
                price_with_tax = price * (1 + tax_rate)
                max_quantity = int(self.ship.money / price_with_tax)

                if quantity == 'max':
                    quantity = max_quantity
                elif quantity == 'half':
                    quantity = (max_quantity + 1) // 2  # Round up division

                if self.ship.buy(item, quantity, self.current_location.market[item], 
                                self.current_location, self.rank):
                    self.display_simple_message(f"Bought {self.format_money(quantity)} {item}.")
                    self.handle_trade('buy')

            elif action in ['sell', 's']:
                item = self.validate_input("Choose item (tech/agri/salt/fuel): ", 
                                        ['tech', 'agri', 'salt', 'fuel'])
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

                if self.ship.sell(item, quantity, self.current_location.market[item], 
                                self.current_location, self.rank):
                    self.display_simple_message(f"Sold {self.format_money(quantity)} {item}.")
                    self.handle_trade('sell')

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
                    'mining': 10000
                }

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

            elif action in ['version', 'v']:
                display_logo(logo_data, centered=True)
                print_centered_text("")
                print_centered_text("Created by Dan Sandner")
                print_centered_text("v1.0.2, ©2025")

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
                # Update passenger satisfaction at end of turn if port is available
                if port_is_available:
                    self.port_system.update_passenger_satisfaction()
                self.turn += 1
                self.random_event()
                self.shop.reset_turn()  # Reset shop state at end of each turn 
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
            'm': ('Mining Facility', 'mining')
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
            self.discovered_locations.add(found_location.name)

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
                self.display_simple_message(f"Gained {total_gain} research points from clearing orbital junk!")
            else:
                self.display_simple_message(f"Gained {total_gain} research points from salvaged debris!")
            
            self.turn += 1
            self.shop.reset_turn()
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
            chapter_multiplier = 1 + (int(''.join(filter(str.isdigit, self.story_manager.current_chapter))) * 0.2)
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
        """Handle combat event with proper victory/defeat recording and reputation gains"""
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
            # Count automatic defense as a victory and add reputation
            self.ship.record_combat_victory(enemy_type)
            if enemy_type == "pirate":
                rep_gain = random.randint(1, 3)  # Smaller gain for automated defense
                self.reputation += rep_gain
                self.ship.passenger_reputation += rep_gain
                self.display_simple_message(f"Gained {rep_gain} reputation for automated pirate defense!")
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
            
            # Add reputation gains for pirate victories
            if enemy_type == "pirate":
                rep_gain = random.randint(2, 5)
                self.reputation += rep_gain
                self.ship.passenger_reputation += rep_gain
                rep_message = f"\nReputation increased by {rep_gain} for defeating pirates!"
            else:
                rep_message = ""
            
            if losses:
                loss_text = ", ".join(losses)
                self.display_simple_message(
                    f"Event! {event} caused {damage_dealt}% damage and stole {loss_text}!\n" +
                    f"Counter-attack successful! Gained {self.format_money(rewards['money'])} credits and {rewards['research']} research points!" +
                    rep_message,
                    3, color='32'
                )
            else:
                self.display_simple_message(
                    f"Event! {event} caused {damage_dealt}% damage!\n" +
                    f"Counter-attack successful! Gained {self.format_money(rewards['money'])} credits and {rewards['research']} research points!" +
                    rep_message,
                    3, color='32'
                )
        else:
            # Combat defeat - record defeat with enemy type
            self.ship.record_combat_defeat(enemy_type)
            
            # Lose reputation on pirate defeats
            if enemy_type == "pirate":
                rep_loss = random.randint(1, 3)
                self.reputation = max(0, self.reputation - rep_loss)
                self.ship.passenger_reputation = max(0, self.ship.passenger_reputation - rep_loss)
                rep_message = f"\nLost {rep_loss} reputation from pirate defeat!"
            else:
                rep_message = ""
            
            if losses:
                loss_text = ", ".join(losses)
                self.display_simple_message(
                    f"Event! {event} caused {damage_dealt}% damage and stole {loss_text}!" +
                    rep_message,
                    3, color='31'
                )
            else:
                self.display_simple_message(
                    f"Event! {event} caused {damage_dealt}% damage!" +
                    rep_message,
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

    def handle_passenger_delivery(self, passenger, module):
        """Handle passenger delivery completion"""
        if not passenger.destination == self.current_location.name:
            return False
            
        # Build passenger delivery event data
        delivery_data = {
            "action": "passenger_delivery",
            "location": self.current_location.name,
            "turn": self.turn,
            "passenger_data": {
                "class": passenger.classification["code"],
                "satisfaction": passenger.satisfaction,
                "destination": passenger.destination
            }
        }
        
        # Update contracts
        if hasattr(self, 'contract_manager'):
            self.contract_manager.update_contract_progress(delivery_data)
            
        # Remove passenger from module
        module.passengers.remove(passenger)
        
        # Update reputation
        if hasattr(self, 'reputation_manager'):
            rep_change = self.reputation_manager.update_reputation(
                passenger.satisfaction,
                passenger
            )
            
            # Handle VIP/special passengers
            if hasattr(passenger, 'is_vip'):
                self.reputation_manager.handle_vip_delivery(passenger)
            elif hasattr(passenger, 'is_story_character'):
                self.reputation_manager.handle_story_character_delivery(passenger)
        
        return True

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

    def conduct_research_activity(self, activity_type):
        """Handle research activities for quests"""
        # Check if we're at a valid research location
        if not isinstance(self.current_location, ResearchColony):
            self.display_simple_message("This activity requires a Research Colony!")
            return False
            
        # Find relevant research quests
        research_quests = [q for q in self.quest_system.active_quests 
                        if q.name == "Scientific Breakthrough"]
        
        if not research_quests:
            self.display_simple_message("No active research quests!")
            return False
        
        # Cost in research points
        activity_costs = {
            'analysis_completed': 20,
            'experiments_conducted': 40
        }
        
        cost = activity_costs.get(activity_type, 0)
        if self.ship.research_points < cost:
            self.display_simple_message(f"Not enough research points! Need: {cost}")
            return False
        
        # Deduct cost and update quest progress
        self.ship.research_points -= cost
        for quest in research_quests:
            if quest.update_research_progress(activity_type):
                self.display_simple_message(f"Research activity completed: {activity_type}")
                quest.complete(self)
                return True
                
        return True

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
            
            if has_data:
                print(self.create_box(market_content, 'double'))
                input("Press Enter to continue...")
            else:
                self.ship.money += 350  # Refund if no data to show
                self.display_simple_message("No new information available!")
        else:
            self.display_simple_message("Not enough money to update the map.")

    def handle_gossip(self):
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

    def display_story_status(self):
        """Display story progress and achievements"""
        story_content = [["Story Progress & Achievements"]]
        story_content.append([""])
        
        # Current chapter info
        current_chapter_obj = self.story_manager.chapters[self.story_manager.current_chapter]
        story_content.append([f"Current Chapter: {self.story_manager.current_chapter} - {current_chapter_obj.title}"])
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

        # Check for present characters and announce them first
        present_characters = [char for char_id, char in 
                            self.character_manager.active_characters.items()
                            if (char["location"] == self.current_location and
                                "cantina" in char["character"].content['requirements'].get('spawn_locations', []))]
        
        if present_characters:
            for char in present_characters:
                self.character_manager.announce_character(char['character'].character_id)
                time.sleep(1)  # Brief pause between character announcements

        # Check and complete cantina quests
        cantina_quests = [q for q in self.quest_system.active_quests if q.quest_type == "cantina"]
        
        for quest in cantina_quests:
            if quest.check_completion(self):
                quest.complete(self)

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
            action = self.validate_input("Choose action: ", valid_inputs)

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

        # Get terminal width
        try:
            term_width = os.get_terminal_size().columns
        except OSError:
            term_width = 80

        # Adjust display based on terminal width
        if term_width < 80:  # Narrow display
            shop_content = [["Item", "Price", "Description/Status"]]
            
            for item_name, item_data in self.shop.current_turn_items:
                if self.shop.is_item_sold(item_name):
                    # Show SOLD in place of description
                    description = "SOLD"
                else:
                    description = item_data["description"]
                    if len(description) > 30:
                        description = description[:27] + "..."
                    
                shop_content.append([
                    item_name.title(),
                    self.format_money(item_data["price"]),
                    description
                ])
        else:  # Wide display
            shop_content = [["Item", "¤", "Description", ""]]
            
            for item_name, item_data in self.shop.current_turn_items:
                status = "Avail"
                description = item_data["description"]
                
                if self.shop.is_item_sold(item_name):
                    status = "SOLD"
                    
                if len(description) > 40:
                    description = description[:37] + "..."
                    
                shop_content.append([
                    item_name.title(),
                    self.format_money(item_data["price"]),
                    description,
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

class ContractManager:
    def __init__(self, game):
        self.game = game
        self.available_contracts = []
        self.active_contracts = []
        self.completed_contracts = []
        self.max_active_contracts = 3
        self.contract_refresh_turns = 0
        self.special_contracts_unlocked = False


    def unlock_special_contracts(self):
        """Unlock special contract types"""
        self.special_contracts_unlocked = True
        self.game.display_simple_message([
            "Special Contracts Unlocked!",
            "New high-value contracts now available:",
            "• High-Value Cargo Transport",
            "• Bulk Resource Movement",
            "• Diplomatic Missions"
        ])

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
            action = self.game.validate_input("Choose action: ", valid_inputs)

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

    def handle_contract_failure(self, contract):
        """Handle failed contract cleanup"""
        message = [
            "Contract Failed!",
            contract.description
        ]
        
        # Add failure reason
        if hasattr(contract, 'failure_reason'):
            message.append(f"Reason: {contract.failure_reason}")
        else:
            message.append("Reason: Time expired")
            
        # Add progress info
        if contract.contract_type == "cargo":
            message.append(
                f"Progress: {contract.progress['amount']}/{contract.requirements.get('min_amount', 0)} units"
            )
        else:  # passenger contract
            message.append(
                f"Progress: {contract.progress['passengers_delivered']}/{contract.requirements.get('count', 0)} passengers"
            )
            
        self.game.display_simple_message(message)
        self.active_contracts.remove(contract)


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
                    "base_money": 30000,
                    "reputation": 15,
                    "plot_points": 5
                },
                "special_abilities": ["market_insider"]
            },
            "Political": {
                "titles": ["Senator", "Councilor", "Minister"],
                "roles": ["governance", "diplomacy", "policy"],
                "rewards": {
                    "base_money": 40000,
                    "reputation": 20,
                    "plot_points": 8
                },
                "special_abilities": ["system_influence"]
            },
            "Scientific": {
                "titles": ["Professor", "Director", "Chief Researcher"],
                "roles": ["research", "development", "innovation"],
                "rewards": {
                    "base_money": 35000,
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
                 requirements=None, on_complete=None, milestone=None):
        self.name = name
        self.description = description
        self.reward_money = reward_money
        self.reward_rp = reward_rp  # Research Points reward
        self.quest_type = quest_type
        self.requirements = requirements or {}
        self.on_complete = on_complete
        self.milestone = milestone  # New attribute
        self.progress = 0
        self.completed = False
        self.target_progress = self.requirements.get('target_progress', 1)
        self.location_requirement = self.requirements.get('location_type', None)

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

    # Add for special location quests
    def check_research_completion(self, game):
        """Check research quest requirements"""
        if not hasattr(self, 'tracked_progress'):
            self.tracked_progress = {
                'research_points_gained': 0,
                'analysis_completed': 0,
                'experiments_conducted': 0
            }
        
        # Check if required criteria are met
        criteria = self.requirements.get('completion_criteria', {})
        for key, target in criteria.items():
            if self.tracked_progress.get(key, 0) < target:
                return False
        return True

    def update_research_progress(self, activity_type):
        """Update progress for research activities"""
        if not hasattr(self, 'tracked_progress'):
            self.tracked_progress = {}
        
        if activity_type in self.tracked_progress:
            self.tracked_progress[activity_type] += 1
            return self.check_research_completion(self.game)
        return False

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
        elif self.quest_type == "cantina":
            return self.check_cantina_completion(game)        
        
        # Generic quest completion check
        return self.progress >= self.target_progress

    def check_cantina_completion(self, game):
        """Check if quest requirements are met"""
        if self.quest_type == "cantina":
            # Specific cantina quest completion checks
            if "Deliver" in self.name:
                # Check trade profits
                commodity = self.name.split()[2].lower()
                return game.ship.trade_profits.get(commodity, 0) >= self.requirements.get('amount', 0)
            
            elif "Transport" in self.name:
                # Check passenger transport
                return game.reputation_manager.total_passengers >= self.requirements.get('count', 0)
            
            elif "Eliminate" in self.name:
                # Check combat victories
                enemy_type = self.name.split()[2].lower()
                return game.ship.combat_victories.get(enemy_type, 0) >= self.requirements.get('victories', 0)
        
        # Existing completion logic for other quest types
        return super().check_completion(game)

    def check_mining_completion(self, game):
        """Check mining quest requirements"""
        if 'resource_type' in self.requirements:
            resource = self.requirements['resource_type']
            target_amount = self.requirements.get('amount', 0)
            return game.ship.cargo[resource] >= target_amount
        return False

    def check_combat_completion(self, game):
        """Check combat quest requirements with proper dictionary access"""
        if 'enemy_type' in self.requirements:
            enemy_type = self.requirements['enemy_type']
            required_amount = self.requirements.get('amount', 1)
            return game.ship.combat_victories.get(enemy_type, 0) >= required_amount
        # If no specific enemy type, check total victories
        return game.ship.combat_victories['total'] >= self.requirements.get('amount', 1)

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

    def fail_contract(self, reason="time_expired"):
        """Mark contract as failed"""
        self.failed = True
        self.completed = False
        return {"status": "failed", "reason": reason}

    def can_claim_rewards(self):
        """Check if rewards can be claimed"""
        return self.completed and not self.rewards_claimed and not self.failed

    def claim_rewards(self):
        """Mark rewards as claimed"""
        if self.can_claim_rewards():
            self.rewards_claimed = True
            return self.calculate_final_reward()
        return None
    


class StoryContract(Contract):
    """Extended contract class for story-related missions"""
    def __init__(self, contract_type, duration, requirements, rewards, story_data):
        super().__init__(contract_type, duration, requirements, rewards)
        self.story_data = story_data
        self.special_character = story_data.get("character", None)
        self.plot_points = story_data.get("plot_points", 0)
        self.milestone_trigger = story_data.get("milestone", None)
        self.follow_up_contract = story_data.get("follow_up", None)

    @staticmethod
    def generate_story_contract(character, milestone):
        """Generate a contract tied to story progression"""
        contract_types = {
            "military": [
                {
                    "type": "combat",
                    "description": "Special security operation",
                    "duration": 8,
                    "requirements": {"combat_victories": 3},
                    "rewards": {"money": 25000, "reputation": 30}
                }
            ],
            "science": [
                {
                    "type": "research",
                    "description": "Critical research mission",
                    "duration": 10,
                    "requirements": {"research_points": 100},
                    "rewards": {"money": 20000, "reputation": 25}
                }
            ],
            "trade": [
                {
                    "type": "cargo",
                    "description": "Strategic resource transport",
                    "duration": 6,
                    "requirements": {"cargo_amount": 200},
                    "rewards": {"money": 30000, "reputation": 20}
                }
            ]
        }
        
        spec = character.specialization
        if spec in contract_types:
            template = random.choice(contract_types[spec])
            return StoryContract(
                contract_type=template["type"],
                duration=template["duration"],
                requirements=template["requirements"],
                rewards=template["rewards"],
                story_data={
                    "character": character,
                    "milestone": milestone,
                    "plot_points": 10
                }
            )
        return None

class ClassificationBasedQuest(Quest):
    """Extended quest class for passenger classification-based missions"""
    def __init__(self, classification, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.required_classification = classification
        self.passengers_helped = []
        self.special_events = []

    @staticmethod
    def generate_for_classification(classification):
        """Generate a quest specific to passenger classification"""
        quest_templates = {
            "S": {  # Scientists
                "name": "Scientific Expedition",
                "description": "Help scientists reach research sites",
                "reward_multiplier": 1.5
            },
            "M": {  # Military
                "name": "Tactical Deployment",
                "description": "Transport military personnel",
                "reward_multiplier": 1.3
            },
            "E": {  # Engineers
                "name": "Engineering Project",
                "description": "Transport engineering teams",
                "reward_multiplier": 1.4
            }
        }
        
        if classification in quest_templates:
            template = quest_templates[classification]
            return ClassificationBasedQuest(
                classification=classification,
                name=template["name"],
                description=template["description"],
                reward_money=5000 * template["reward_multiplier"],
                reward_rp=50 * template["reward_multiplier"],
                quest_type="passenger"
            )
        return None

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

    def get_special_characters(self):
        """Get special characters present at port"""
        return [char for char_id, char in 
                self.game.character_manager.active_characters.items()
                if char["location"] == self.game.current_location and
                "port" in char["character"].content['requirements'].get('spawn_locations', [])]


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

    def add_special_passenger(self, character):
        """Add a special character to waiting passengers list"""
        current_location = self.game.current_location.name
        if current_location not in self.waiting_passengers:
            self.waiting_passengers[current_location] = []
            
        # Create passenger object from character
        passenger = Passenger(
            name=character.full_name,
            destination=random.choice(list(self.game.known_locations)),
            wealth_level=5  # VIPs and special characters are wealthy
        )
        
        # Add character-specific attributes
        passenger.is_special = True
        passenger.character = character
        passenger.classification = {"code": "V", "name": "VIP", "type": character.specialization}
        
        # Add to waiting list
        self.waiting_passengers[current_location].append(passenger)
        
        return passenger


    def update_passengers(self, location):
        """Update passenger list at a location"""
        if location not in self.waiting_passengers:
            self.waiting_passengers[location] = []
            
        # Remove passengers waiting too long
        self.waiting_passengers[location] = [p for p in self.waiting_passengers[location] 
                                           if p.turns_waiting < 10]

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
        distance_multiplier = 1
        
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

        while True:
            options = {
                'view': ('v', "View Port Info"),
                'modules': ('m', "Purchase Modules"),
                'board': ('b', "Board Passengers"),
                'unload': ('u', "Unload Passengers"),
                'contracts': ('c', "Manage Contracts"),
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
            action = self.game.validate_input("Choose action: ", valid_inputs)
            
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
                        elif hasattr(passenger, 'is_story_character'):
                            self.game.reputation_manager.handle_story_character_delivery(passenger)

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

    def display_module_details(self):
        """Show detailed module information"""
        module_info = [["Module Details"]]
        for module in self.game.ship.passenger_modules:
            module_info.append([
                f"{module.name}",
                f"Capacity: {module.capacity}",
                f"Comfort Level: {module.comfort_level}"
            ])
            if module.passengers:
                module_info.append(["Current Passengers:"])
                for p in module.passengers:
                    module_info.append([
                        f"└─ {p.name} [{p.classification['code']}]",
                        f"To: {p.destination}",
                        f"Satisf.: {p.satisfaction}%"
                    ])
            else:
                module_info.append(["└─ Empty"])
            module_info.append([""])
                
        print(self.game.create_box(module_info, 'double'))
        input("Press Enter to continue...")

    def handle_passenger_selection(self, available_passengers):
        """Handle batch passenger selection"""
        self.game.display_simple_message("Enter passenger numbers separated by spaces (e.g., '1 2 15') or 'back':", 0)
        while True:
            try:
                selection = input(">>> ").strip().lower()
                if selection == 'back':
                    return None
                    
                # Parse space-separated numbers
                passenger_nums = [int(num) for num in selection.split()]
                
                # Validate numbers
                if all(1 <= num <= len(available_passengers) for num in passenger_nums):
                    return [available_passengers[num-1] for num in passenger_nums]
                else:
                    self.game.display_simple_message("Invalid passenger number(s)")
                    return None
                    
            except ValueError:
                self.game.display_simple_message("Invalid input. Please enter numbers separated by spaces.")
                return None        


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
                "description": "Basic scanner improves resource detection",
                "tech_required": 2,
                "plot_required": 0
            },
            "probe": {
                "price": 900,
                "description": "Deep space probe increases exploration success",
                "tech_required": 3,
                "plot_required": 10
            },
            "turrets": {
                "price": 1200,
                "description": "Defense turrets to automatically repel pirates",
                "tech_required": 4,
                "plot_required": 15
            },
            "shield": {
                "price": 1500,
                "description": "Energy shield reduces damage taken in combat",
                "tech_required": 5,
                "plot_required": 20
            },
            "patcher": {
                "price": 300,
                "description": "Hull patcher repairs minor combat damage",
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
                "description": "Reduces loading/unloading time (-1 turn per trade)",
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
                "description": "Time dilation for faster delivery (-2 turns per trade)",
                "tech_required": 8,
                "plot_required": 75
            }
        }

        # Location-specific items with requirements
        self.location_equipment = {
            "AsteroidBase": {
                "mining_laser": {
                    "price": 2000,
                    "description": "Improves mining efficiency and defense",
                    "tech_required": 3,
                    "plot_required": 15
                },  
                "cargo_scanner": {
                    "price": 1800,
                    "description": "Detects valuable mineral deposits",
                    "tech_required": 4,
                    "plot_required": 20
                },
                "shield_booster": {
                    "price": 2500,
                    "description": "Offers extra protection in asteroid fields",
                    "tech_required": 5,
                    "plot_required": 25
                },
                "mining_compressor": {
                    "price": 15000,
                    "description": "Specialized for asteroid mining (+40% capacity for mined resources)",
                    "tech_required": 6,
                    "plot_required": 40
                }
            },
            "DeepSpaceOutpost": {
                "advanced_radar": {
                    "price": 2200,
                    "description": "Early warning system for threats",
                    "tech_required": 4,
                    "plot_required": 30
                },
                "combat_drone": {
                    "price": 3000,
                    "description": "Assists in space battles",
                    "tech_required": 5,
                    "plot_required": 35
                },
                "repair_bot": {
                    "price": 2800,
                    "description": "Automatic repairs during travel",
                    "tech_required": 6,
                    "plot_required": 40
                },
                "emergency_warp": {
                    "price": 18000,
                    "description": "Emergency escape system (50% chance to avoid combat)",
                    "tech_required": 7,
                    "plot_required": 50
                }
            },
            "ResearchColony": {
                "research_module": {
                    "price": 2500,
                    "description": "Improves research point gains",
                    "tech_required": 5,
                    "plot_required": 40
                },
                "data_analyzer": {
                    "price": 2800,
                    "description": "Better research success rates",
                    "tech_required": 6,
                    "plot_required": 45
                },
                "quantum_scanner": {
                    "price": 3500,
                    "description": "Reveals anomalies and secrets",
                    "tech_required": 7,
                    "plot_required": 50
                },
                "containment_optimizer": {
                    "price": 22000,
                    "description": "Smart cargo optimization (+25% capacity and -1 turn per trade)",
                    "tech_required": 8,
                    "plot_required": 60
                }
            }
        }

        # Add specialized location-specific transport equipment
        self.location_equipment["AsteroidBase"]["mining_compressor"] = {
            "price": 15000,
            "description": "Specialized for asteroid mining (+40% capacity for mined resources)"
        }
        
        self.location_equipment["DeepSpaceOutpost"]["emergency_warp"] = {
            "price": 18000,
            "description": "Emergency escape system (50% chance to avoid combat during transport)"
        }
        
        self.location_equipment["ResearchColony"]["containment_optimizer"] = {
            "price": 22000,
            "description": "Smart cargo optimization (+25% capacity and -1 turn per trade)"
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
    
    def get_item_requirements(self, item_name, location_type=None):
        """Get tech level and plot point requirements for an item"""
        if item_name in self.base_equipment:
            data = self.base_equipment[item_name]
            return {
                "tech_required": data["tech_required"],
                "plot_required": data["plot_required"]
            }
        elif location_type and location_type in self.location_equipment:
            if item_name in self.location_equipment[location_type]:
                data = self.location_equipment[location_type][item_name]
                return {
                    "tech_required": data["tech_required"],
                    "plot_required": data["plot_required"]
                }
        return None    

    def mark_item_sold(self, item_name):
        """Mark an item as sold for this turn"""
        self.sold_items.add(item_name)
        if item_name in self.current_offerings:
            self.current_offerings.remove(item_name)

    def is_item_available(self, item_name, location=None):
        """Check if an item is available for purchase"""
        # First check if item is sold
        if item_name in self.sold_items:
            return False
            
        # Then check if it's in current offerings
        if item_name not in self.current_offerings:
            return False
            
        # If location provided, check tech and plot requirements
        if location:
            item_data = None
            if item_name in self.base_equipment:
                item_data = self.base_equipment[item_name]
            elif location.location_type in self.location_equipment:
                if item_name in self.location_equipment[location.location_type]:
                    item_data = self.location_equipment[location.location_type][item_name]
            
            if item_data:
                if (location.tech_level < item_data["tech_required"] or
                    location.story_manager.plot_points < item_data["plot_required"]):
                    return False
                    
        return True

    def get_item_price(self, item_name, location_type=None):
        """Get the current price of an item, including any discounts"""
        base_price = None
        
        # Check base equipment
        if item_name in self.base_equipment:
            base_price = self.base_equipment[item_name]["price"]
        
        # Check location-specific equipment
        elif location_type and location_type in self.location_equipment:
            if item_name in self.location_equipment[location_type]:
                base_price = self.location_equipment[location_type][item_name]["price"]
        
        if base_price is None:
            return None
            
        # Apply any active discounts
        discount = self.current_discounts.get(item_name, 0)
        final_price = base_price * (1 - discount)
        
        return int(final_price)

    def get_item_description(self, item_name, location_type=None):
        """Get the description of an item"""
        # Check base equipment
        if item_name in self.base_equipment:
            return self.base_equipment[item_name]["description"]
        
        # Check location-specific equipment
        if location_type and location_type in self.location_equipment:
            if item_name in self.location_equipment[location_type]:
                return self.location_equipment[location_type][item_name]["description"]
        
        return "No description available"

    def add_special_offer(self, item_name, discount):
        """Add a special offer with a discount percentage (0-1)"""
        self.current_discounts[item_name] = min(1, max(0, discount))

    def remove_special_offer(self, item_name):
        """Remove a special offer"""
        if item_name in self.current_discounts:
            del self.current_discounts[item_name]

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


    def add_new_item(self, item_name, price, description, location_type=None):
        """Add a new item to the shop"""
        item_data = {
            "price": price,
            "description": description
        }
        
        if location_type:
            if location_type not in self.location_equipment:
                self.location_equipment[location_type] = {}
            self.location_equipment[location_type][item_name] = item_data
        else:
            self.base_equipment[item_name] = item_data

    def remove_item(self, item_name, location_type=None):
        """Remove an item from the shop"""
        if location_type and location_type in self.location_equipment:
            if item_name in self.location_equipment[location_type]:
                del self.location_equipment[location_type][item_name]
        elif item_name in self.base_equipment:
            del self.base_equipment[item_name]
            
    def apply_reputation_discount(self, reputation):
        """Apply a discount based on player reputation (0-100)"""
        return min(0.25, reputation / 400)  # Max 25% discount at reputation 100

    def get_upgradeable_items(self):
        """Get list of items that can be upgraded"""
        upgradeable = []
        for name, data in self.base_equipment.items():
            if "upgradeable" in data and data["upgradeable"]:
                upgradeable.append(name)
        return upgradeable

    def calculate_upgrade_cost(self, item_name, current_level):
        """Calculate the cost to upgrade an item"""
        if item_name in self.base_equipment:
            base_price = self.base_equipment[item_name]["price"]
            return int(base_price * (1.5 ** current_level))
        return None          

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
        """Get base mining efficiency with randomized ranges per location type"""
        ranges = {
            "Planet": (35, 65),
            "AsteroidBase": (68, 78),
            "DeepSpaceOutpost": (42, 52),
            "ResearchColony": (16, 36)
        }
        base_range = ranges.get(self.location_type, (50, 60))
        return random.randint(*base_range)

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



class QuestSystem:
    def __init__(self, game):
        self.game = game
        self.active_quests = []  # For Quest objects
        self.available_quests = []  # For tuple-based quests (legacy support)
        self.completed_quests = []
        self.story_progress = 0
        self.quest_ids = set()  # Track unique quest IDs
        self.quest_message_shown = set()  # Track shown quest messages

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
                if hasattr(quest, 'requirements'):
                    progress = ""
                    if 'target_progress' in quest.requirements:
                        progress = f" ({quest.progress}/{quest.requirements['target_progress']})"
                    quest_content.append([f"└─ Progress{progress}"])
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
        """Handle quest completion and cleanup with full quest lifecycle"""
        quest_id = f"{quest.name}_{quest.quest_type}"
        
        if quest in self.active_quests:
            # Remove from active quests and add to completed
            self.active_quests.remove(quest)
            self.completed_quests.append(quest)
            
            # Award rewards
            self.game.ship.money += quest.reward_money
            self.game.ship.research_points += quest.reward_rp
            
            # Apply any special effects based on quest type
            if quest.quest_type == 'mining':
                self.game.current_location.exogeology = min(100, 
                    self.game.current_location.exogeology + 5)  # Small mining efficiency boost
            elif quest.quest_type == 'research':
                boost = int(quest.reward_rp * 0.1)  # 10% bonus research points
                self.game.ship.research_points += boost
            
            # Execute completion callback if exists
            if quest.on_complete:
                quest.on_complete()
            
            # Mark quest as completed
            quest.completed = True
            
            # Clean up message tracking
            if quest_id in self.quest_message_shown:
                self.quest_message_shown.remove(quest_id)
            
            # Display completion message
            self.game.display_story_message([
                f"Quest Completed: {quest.name}",
                f"Rewards:",
                f"• {self.game.format_money(quest.reward_money)} credits",
                f"• {quest.reward_rp} research points"
            ])
            
            # Update story progression if applicable
            if hasattr(self.game, 'story_manager'):
                self.game.story_manager.handle_quest_completion(quest)
            
            # Check for milestone completion
            if hasattr(self.game, 'check_milestone_triggers'):
                self.game.check_milestone_triggers()
            
            return True
            
        return False

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
        """Add a new quest with duplication check"""
        # Create unique identifier for the quest
        quest_id = f"{quest.name}_{quest.quest_type}"
        
        # Check if quest is already active
        existing_quest = any(q.name == quest.name and q.quest_type == quest.quest_type 
                           for q in self.active_quests)
        if existing_quest:
            return False  # Don't add duplicate quest
        
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
        """Check a single requirement"""
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
                    discovered = len([loc for loc in game.discovered_locations 
                                   if loc.location_type == loc_type])
                    if discovered < amount:
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
        elif req_type == "milestones_completed":
            return all(milestone in game.story_manager.completed_story_beats for milestone in req_value)
        elif req_type == "story_states":
            return all(game.story_manager.story_states.get(state, False) for state in req_value)

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

class StoryChapter:
    def __init__(self, chapter_id, title, description, requirements, milestones, next_chapters=None):
        self.id = chapter_id
        self.title = title
        self.description = description
        self.requirements = requirements
        self.milestones = {}  # Dictionary of milestone_id: StoryMilestone
        self.next_chapters = next_chapters or []  # List of possible next chapter IDs
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
        for req_type, req_value in self.requirements.items():
            if not MilestoneRequirements._check_single_requirement(req_type, req_value, game):
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
            if all(MilestoneRequirements._check_single_requirement(req_type, req_value, game) 
                for req_type, req_value in chapter.requirements.items()):
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
        try:
            return int(''.join(filter(str.isdigit, chapter_string)))
        except (ValueError, TypeError):
            return 1  # Default to chapter 1 if conversion fails

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
                    "trade_profit": 200000
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
                    "chapters_completed": ["ch2a", "ch2b"],  # Can be reached from either path
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
                    "trade_profit": 1000000
                },
                milestones=[
                    {
                        "milestone_id": "trade_ending",
                        "title": "Economic Victory",
                        "description": "Complete economic domination achieved",
                        "requirements": {
                            "buildings_built": {"stockmarket": 5},
                            "passenger_reputation": 80,
                            "trade_profit": 1000000
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

    def start_game(self):
        """Initialize story at game start"""
        self.current_chapter = "ch1"  # Store the ID string instead of the chapter object
        first_chapter = self.chapters["ch1"]
        
        self.game.display_story_message([
            f"Chapter 1: {first_chapter.title}",
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

    def get_current_objectives(self):
        """Get current chapter objectives"""
        if self.current_chapter:
            chapter_obj = self.chapters[self.current_chapter]
            return [(m.title, m.completed) for m in chapter_obj.milestones.values()]
        return []

    def check_chapter_progress(self):
        """Check for chapter completion and handle branching"""
        if self.current_chapter and not self.chapters[self.current_chapter].completed:
            self.check_milestone_progress()
            
            current_chapter_obj = self.chapters[self.current_chapter]
            if current_chapter_obj.check_completion(self.game):
                # This line to properly complete the chapter
                self.complete_current_chapter()
                
                next_chapters = current_chapter_obj.get_next_chapters(self.game)
                if next_chapters:
                    if len(next_chapters) > 1:
                        self.present_chapter_choice(next_chapters)
                    else:
                        self.start_chapter(next_chapters[0].id)
                elif not current_chapter_obj.next_chapters:
                    self.handle_game_ending()

    def handle_game_ending(self):
        """Handle reaching a game ending"""
        ending_messages = {
            "ending_trade": [
                "Congratulations! You've become a legendary trade mogul!",
                "Your economic empire spans the galaxy.",
                f"Final wealth: {self.game.format_money(self.game.ship.money)}",
                f"Total trades: {self.game.trades_completed}"
            ],
            "ending_combat": [
                "Congratulations! You're now a legendary fleet admiral!",
                "Your military prowess is unmatched.",
                f"Combat victories: {self.game.ship.combat_victories['total']}",
                f"Final rank: {self.game.rank}"
            ],
            "ending_discovery": [
                "Congratulations! You've solved the sector's ancient mysteries!",
                "Your discoveries will change history forever.",
                f"Research points: {self.game.ship.research_points}",
                f"Discoveries: {len(self.game.discovered_locations)}"
            ]
        }

        messages = ending_messages.get(self.current_chapter, 
            ["Congratulations! You've completed your journey!"])
        
        self.game.display_story_message(messages)
        self.game.display_score()

    def complete_current_chapter(self):
        """Handle chapter completion with unlocks"""
        current_chapter_obj = self.chapters[self.current_chapter]
        if not current_chapter_obj.completed:
            current_chapter_obj.completed = True
            current_chapter_obj.completion_turn = self.game.turn
            self.completed_chapters.add(self.current_chapter)
            
            # Handle any chapter unlocks
            current_chapter_obj.handle_chapter_unlocks(self.game)
            
            # Get next chapter options
            next_chapters = current_chapter_obj.get_next_chapters(self.game)
            
            self.game.display_story_message([
                f"Chapter Complete: {current_chapter_obj.title}",
                "Your journey continues to evolve..."
            ])
            
            # Present chapter choice or transition to next chapter
            if next_chapters:
                if len(next_chapters) > 1:
                    self.present_chapter_choice(next_chapters)
                else:
                    self._chapter_just_announced = True  # Prevent duplicate announcement
                    self.start_chapter(next_chapters[0].id)
                    self.game.display_story_message([
                        f"Chapter {self.current_chapter}: {next_chapters[0].title}",
                        next_chapters[0].description
                    ])

    def present_chapter_choice(self, available_chapters):
        """Present chapter choices to player"""
        content = [["Choose Your Path"]]
        for i, chapter in enumerate(available_chapters, 1):
            content.extend([
                [""],
                [f"{i}. {chapter.title}"],
                [chapter.description]
            ])
        print(self.game.create_box(content, 'double'))
        
        choice = self.game.validate_input(
            f"Choose your path (1-{len(available_chapters)}): ",
            [str(i) for i in range(1, len(available_chapters) + 1)]
        )
        
        if choice:
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
        
        # Only announce chapter if it wasn't just announced by complete_current_chapter
        if not getattr(self, '_chapter_just_announced', False):
            self.game.display_story_message([
                f"Chapter {self.current_chapter}: {chapter_obj.title}",
                chapter_obj.description,
                "",
                "New milestones await..."
            ])
        self._chapter_just_announced = False

    def get_current_objectives(self):
        """Get current chapter objectives"""
        if self.current_chapter:
            return [(m.title, m.completed) for m in self.current_chapter.milestones.values()]
        return []

    def save_progress(self):
        """Return story progress data for saving"""
        return {
            "current_chapter": self.current_chapter,
            "completed_chapters": list(self.completed_chapters),
            "completed_story_beats": list(self.completed_story_beats),
            "plot_points": self.plot_points,
            "story_states": dict(self.story_states)
        }

    def load_progress(self, data):
        """Load story progress from saved data"""
        if data["current_chapter"]:
            self.current_chapter = self.chapters[data["current_chapter"]]
        self.completed_chapters = set(data["completed_chapters"])
        self.completed_story_beats = set(data["completed_story_beats"])
        self.plot_points = data["plot_points"]
        self.story_states.update(data["story_states"])

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
        chapter_num = int(''.join(filter(str.isdigit, self.current_chapter)))
        points *= (1 + chapter_num * 0.2)
        
        self.plot_points += int(points)
        
        self.update_story_states(event_type, details)
        self.check_chapter_progress()

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
        """Check if an event triggers any story progression"""
        if isinstance(event, str):
            if "Pirate" in event:
                self.process_event("combat", {"enemy_type": "pirate"})
            elif "artifact" in event.lower():
                self.process_event("exploration", {"discovery_type": "artifact"})
            elif "trade" in event.lower():
                self.process_event("trade", {})
            elif "research" in event.lower():
                self.process_event("research", {})

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
            self.game.quest_system.generate_quest(quest.quest_type, 1.5)

    def handle_quest_line_completion(self, quest_line):
        """Update story progress when a quest line is completed"""
        self.plot_points += 20
        
        if quest_line == "mining":
            self.story_states["resource_empire"] = True
        elif quest_line == "research":
            self.story_states["alien_discovery"] = True
        elif quest_line == "contracts":
            # Unlock special contract types
            self.contract_manager.unlock_special_contracts()
            
            # Update story state
            self.story_states["master_trader"] = True
            
            # Generate follow-up content
            if random.random() < 0.3:  # 30% chance
                self.quest_system.generate_quest("trade", 2.0)
                
            self.display_story_message([
                "Trading Empire Milestone Achieved!",
                "Your mastery of contracts has not gone unnoticed...",
                "New opportunities await!"
            ])            

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
                        discovered = len([loc for loc in self.game.discovered_locations 
                                        if loc.location_type == loc_type])
                        if discovered < count:
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
            plot_points_needed = float('inf')
            for next_chapter_id in current_chapter_obj.next_chapters:
                next_chapter = self.chapters[next_chapter_id]
                if 'plot_points' in next_chapter.requirements:
                    current_needed = next_chapter.requirements['plot_points'] - self.plot_points
                    plot_points_needed = min(plot_points_needed, current_needed)
            
            if plot_points_needed != float('inf'):
                content.append([f"Plot Points: {self.plot_points} ({max(0, plot_points_needed)} to Next)"])
            else:
                content.append([f"Plot Points: {self.plot_points}"])
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

    # Log, player log. Example usage:
    # game.story_manager.display_story_progress()                    

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
            chapter_bonus = 1.0 + (int(''.join(filter(str.isdigit, self.game.story_manager.current_chapter))) * 0.2)

            
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
            quest = Quest(
                name=quest_data["name"],
                description=quest_data["description"],
                reward_money=quest_data["reward_money"],
                reward_rp=quest_data["reward_rp"],
                quest_type=f"unlock_{location_type}",  # Make type unique
                requirements={"location_type": location_type},
                on_complete=lambda: self.complete_location_unlock(location_type)
            )
            
            # Use central quest addition method
            self.game.quest_system.add_quest(quest)

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

class DynamicCharacterSystem:
    def __init__(self, game):
        self.game = game
        self.active_characters = {}
        self.character_generators = {
            "human": SpecialCharacterGenerator(game),
            "synthetic": SyntheticCharacterGenerator(game),
            "alien": AlienCharacterGenerator(game),
            "special": SpecialCharacterGenerator(game)  # Use SpecialCharacterGenerator for VIPs

        }
        self.character_triggers = {
            "neuroengineering_uprising": {
                "condition": lambda game: self.count_buildings(game, "Neuroengineering Guild") >= 4,
                "generator": "synthetic",
                "character_type": "Neurodroid",
                "event_chain": "neurodroid_uprising"
            },
            "agrobot_rebellion": {
                "condition": lambda game: self.count_buildings(game, "Agrobot Assembly Line") >= 4,
                "generator": "synthetic",
                "character_type": "Agrobot",
                "event_chain": "agrobot_collective"
            },
            "pirate_nemesis": {
                "condition": lambda game: game.ship.combat_victories.get('pirate', 0) >= 10,
                "generator": "human",
                "character_type": "PirateCaptain",
                "event_chain": "pirate_vendetta"
            },
            # Add VIP passenger trigger with correct generator type
            "vip_passenger": {
                "condition": lambda game: (
                    hasattr(game.ship, 'passenger_reputation') and 
                    game.ship.passenger_reputation >= 40 and
                    game.turn - game.reputation_manager.last_vip_spawn >= 5
                ),
                "generator": "human",  # Changed from 'special' to 'human'
                "character_type": "VIPPassenger",
                "event_chain": None
            }            
        }
        self.event_chains = {}
        self.add_passenger_triggers()
        self.create_passenger_event_chains()

    def create_character_box(self, character_content, style='round'):
        return self.game.create_character_box(character_content, style)

    def check_character_triggers(self):
        """Check for new character appearances based on game state"""
        for trigger_id, trigger in self.character_triggers.items():
            if (trigger_id not in self.active_characters and 
                trigger['condition'](self.game)):
                self.spawn_character(trigger_id)


    def spawn_character(self, trigger_id):
        """Generate and introduce a new character"""
        trigger = self.character_triggers[trigger_id]
        generator = self.character_generators[trigger['generator']]
        character = generator.generate_character(trigger['character_type'])
        
        # Create a unique identifier for the character
        character_id = f"{trigger_id}_{self.game.turn}"
        
        # Store the character with its full details
        self.active_characters[character_id] = {
            "character": character,
            "trigger_id": trigger_id
        }
        
        # Initialize event chain if applicable
        if trigger['event_chain']:
            self.event_chains[character_id] = self.create_event_chain(trigger['event_chain'], character)
        
        # Announce character using the character_id
        self.announce_character(character_id)

        

    def announce_character(self, character_id):
        """Display character introduction using flexible character data"""
        # Retrieve the character entry
        character_entry = self.active_characters.get(character_id)
        if not character_entry:
            print(f"Error: No character found for ID {character_id}")
            return
        
        # Get character 
        character = character_entry["character"]
        
        # Prepare content based on character type
        content = {
            'title': str(getattr(character, 'full_name', str(character))),
            'introduction': "",
            'description': "",
            'options': ""
        }
        
        # Try to get introduction from different possible sources
        if hasattr(character, 'content'):
            # For CharacterTemplate-based characters
            intros = character.content['dialogue'].get('first_meeting', [])
            content['introduction'] = random.choice(intros) if intros else "A new encounter begins."
        elif hasattr(character, 'introduction'):
            # For SpecialCharacter objects
            content['introduction'] = str(character.introduction)
        else:
            # Fallback generic introduction
            content['introduction'] = "A mysterious figure approaches..."
        
        # Ensure all content values are strings
        for key in content:
            content[key] = str(content[key]) if content[key] is not None else ""
        
        # Handle interactions if they exist
        current_location = self.game.current_location.location_type.lower()
        
        # Determine options based on character type
        if hasattr(character, 'content') and 'interactions' in character.content:
            interactions = character.content['interactions'].get(current_location, [])
            content['options'] = ", ".join(str(opt) for opt in interactions) if interactions else ""
        
        # Display character box
        print(self.game.create_character_box(content, 'round'))
        
        # If options exist, allow interaction
        if content['options']:
            choice = self.game.validate_input(
                "Your response: ",
                [str(i) for i in range(1, len(content['options'].split(', ')) + 1)]
            )
            if choice:
                # Note: This might need further adjustment depending on your interaction handling
                return self.handle_character_interaction(character_id, int(choice) - 1, current_location)
        
        return True

    def add_passenger_triggers(self):
        """Add passenger-related triggers to character system"""
        self.character_triggers.update({
            "galactic_alliance": {
                "condition": lambda game: (
                    game.ship.passenger_reputation >= 60 and 
                    game.story_manager.get_chapter_number() >= 2
                ),
                "generator": "human",
                "character_type": "DiplomaticEnvoy",
                "event_chain": "galactic_alliance"
            },
            "system_rebellion": {
                "condition": lambda game: (
                    game.ship.passenger_reputation >= 70 and 
                    game.story_manager.current_chapter >= 3 and
                    len([loc for loc in game.locations if hasattr(loc, 'controlled_by_player')]) >= 2
                ),
                "generator": "human",
                "character_type": "RebelCommander",
                "event_chain": "system_rebellion"
            },
            "ancient_mysteries": {
                "condition": lambda game: (
                    game.ship.passenger_reputation >= 80 and 
                    game.story_manager.current_chapter >= 4 and
                    "alien_artifacts" in game.story_manager.completed_story_beats
                ),
                "generator": "alien",
                "character_type": "AncientScholar",
                "event_chain": "ancient_mysteries"
            },
            "vip_passenger": {
                "condition": lambda game: (
                    game.ship.passenger_reputation >= 40 and
                    game.turn - game.reputation_manager.last_vip_spawn >= 5
                ),
                "generator": "special",  # Will use SpecialCharacterGenerator
                "character_type": "VIPPassenger",
                "event_chain": None  # VIPs don't need event chains
            }
        })

    def create_passenger_event_chains(self):
        """Create event chains for passenger-related stories"""
        self.event_chains.update({
            "galactic_alliance": [
                {
                    "type": "dialogue",
                    "message": "Discuss galactic politics and potential alliances",
                    "choices": ["support_alliance", "remain_neutral", "oppose_alliance"],
                    "consequences": {
                        "support_alliance": {
                            "reputation": 15,
                            "plot_points": 5,
                            "unlock": "diplomatic_missions"
                        },
                        "remain_neutral": {
                            "reputation": 5,
                            "plot_points": 2
                        },
                        "oppose_alliance": {
                            "reputation": -10,
                            "plot_points": 3,
                            "unlock": "independent_contracts"
                        }
                    }
                },
                {
                    "type": "mission",
                    "message": "Transport diplomatic delegation",
                    "requirements": {
                        "destinations": 3,
                        "min_satisfaction": 90
                    },
                    "rewards": {
                        "money": 50000,
                        "reputation": 20,
                        "plot_points": 8
                    }
                }
            ],
            "system_rebellion": [
                {
                    "type": "covert_transport",
                    "message": "Transport rebel leaders without detection",
                    "risk": 0.3,
                    "rewards": {
                        "money": 75000,
                        "reputation": 25,
                        "plot_points": 10
                    },
                    "failure_consequences": {
                        "reputation": -30,
                        "banned_systems": ["Alpha", "Beta"]
                    }
                },
                {
                    "type": "supply_run",
                    "message": "Deliver crucial supplies to rebel bases",
                    "cargo_requirements": {
                        "tech": 100,
                        "agri": 150
                    },
                    "rewards": {
                        "money": 100000,
                        "reputation": 30,
                        "plot_points": 15
                    }
                }
            ],
            "ancient_mysteries": [
                {
                    "type": "exploration",
                    "message": "Visit ancient ruins with the scholar",
                    "locations": ["Ruins Alpha", "Ruins Beta"],
                    "discoveries": {
                        "artifacts": 3,
                        "research_points": 200
                    },
                    "rewards": {
                        "money": 150000,
                        "reputation": 40,
                        "plot_points": 20
                    }
                }
            ]
        })        

    def create_event_chain(self, chain_type, character):
        """Create new event chain for character with complete chain definitions"""
        event_chain_templates = {
            "neurodroid_uprising": [
                {
                    "type": "demand",
                    "choices": ["accept", "negotiate", "refuse"],
                    "consequences": {
                        "accept": {"money": -30000, "plot_points": 2},
                        "negotiate": {"money": -15000, "plot_points": 1, "uprising_chance": 0.3},
                        "refuse": {"uprising_chance": 0.6}
                    }
                },
                {
                    "type": "event",
                    "message": "Neurodroid optimization protocols activate",
                    "effect": "damage_buildings",
                    "damage_chance": 0.4
                },
                {
                    "type": "resolution",
                    "choices": ["shutdown", "compromise"],
                    "consequences": {
                        "shutdown": {"research_points": -100, "plot_points": 3},
                        "compromise": {"money": -50000, "plot_points": 5}
                    }
                }
            ],
            "agrobot_collective": [
                {
                    "type": "demand",
                    "choices": ["accept", "negotiate", "refuse"],
                    "consequences": {
                        "accept": {"money": -25000, "plot_points": 2},
                        "negotiate": {"money": -12000, "plot_points": 1, "food_production": 0.8},
                        "refuse": {"food_production": 0.5}
                    }
                },
                {
                    "type": "event",
                    "message": "Automated farming systems malfunction",
                    "effect": "reduce_production",
                    "reduction": 0.3
                },
                {
                    "type": "resolution",
                    "choices": ["reset", "integrate"],
                    "consequences": {
                        "reset": {"agri_level": -2, "plot_points": 2},
                        "integrate": {"money": -40000, "plot_points": 4}
                    }
                }
            ],
            "rogue_captain": [
                {
                    "type": "combat",
                    "message": "Ship-to-ship engagement",
                    "enemy_stats": {
                        "attack": 3,
                        "defense": 2,
                        "type": "rogue_captain"
                    }
                },
                {
                    "type": "aftermath",
                    "message": "Combat resolution",
                    "rewards": {
                        "victory": {"money": 5000, "items": ["quantum_core"]},
                        "defeat": {"damage": 30}
                    }
                }
            ],
            "merchant_visit": [
                {
                    "type": "trade",
                    "message": "Special inventory available",
                    "offers": self.generate_special_offers(),
                    "duration": 3  # Turns available
                }
            ],
            "researcher_exchange": [
                {
                    "type": "exchange",
                    "message": "Knowledge transfer proposition",
                    "rate": random.randint(500, 1000),  # Credits per research point
                    "max_points": 50
                }
            ]
        }

        stages = event_chain_templates.get(chain_type, [])
        return EventChain(chain_type, character, stages)

    def generate_special_offers(self):
        """Generate special merchant offers"""
        possible_items = [
            ("quantum_shield", 3000, "Advanced defense system"),
            ("neural_boost", 2500, "Research point multiplier"),
            ("cargo_expander", 4000, "Increased storage capacity"),
            ("stealth_drive", 5000, "Improved escape chances")
        ]
        return random.sample(possible_items, random.randint(2, 3))        

    @staticmethod
    def count_buildings(game, building_type):
        """Count total number of specific buildings across all locations"""
        return sum(
            location.buildings.count(building_type)
            for location in game.locations
        )

    def handle_character_interaction(self, character):
        """Handle player interaction with a special character"""
        if not character.met:
            character.met = True
            self.game.display_story_message([
                f"First encounter with {character.full_name}!",
                "",
                character.introduction
            ])
            
        chain_id = next(
            (cid for cid, char in self.active_characters.items() 
             if char == character),
            None
        )
        if chain_id and chain_id in self.event_chains:
            event_chain = self.event_chains[chain_id]
            stage = event_chain.advance()
            
            if stage:
                self.handle_event_stage(stage, character)
            else:
                self.conclude_character_arc(character)



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

class EventChain:
    """Manages sequential events for character interactions"""
    
    def __init__(self, chain_type, character, stages):
        self.chain_type = chain_type
        self.character = character
        self.stages = stages
        self.current_stage = 0
        self.completed_stages = []
        
    def get_chain_stages(self, chain_type):
        """Get event chain for specific type"""
        chains = {
            "neurodroid_uprising": [
                {
                    "type": "demand",
                    "message": "Initial demand for resources",
                    "choices": ["pay", "refuse"],
                    "consequences": {
                        "pay": {"money": -30000, "plot_points": 2},
                        "refuse": {"uprising_chance": 0.3}
                    }
                },
                {
                    "type": "event",
                    "message": "Neurodroid optimization protocols activate",
                    "effect": "damage_buildings",
                    "damage_chance": 0.4
                },
                {
                    "type": "resolution",
                    "message": "Final confrontation with Neurodroid consciousness",
                    "choices": ["negotiate", "shutdown"],
                    "consequences": {
                        "negotiate": {"money": -50000, "plot_points": 5},
                        "shutdown": {"research_points": -100, "plot_points": 3}
                    }
                }
            ],
            "agrobot_collective": [
                {
                    "type": "demand",
                    "message": "Resource reallocation request",
                    "choices": ["accept", "refuse"],
                    "consequences": {
                        "accept": {"money": -25000, "plot_points": 2},
                        "refuse": {"food_production": 0.5}
                    }
                },
                {
                    "type": "event",
                    "message": "Automated farming systems malfunction",
                    "effect": "reduce_production",
                    "reduction": 0.3
                },
                {
                    "type": "resolution",
                    "message": "Agrobot Collective presents final ultimatum",
                    "choices": ["integrate", "reset"],
                    "consequences": {
                        "integrate": {"money": -40000, "plot_points": 4},
                        "reset": {"agri_level": -2, "plot_points": 2}
                    }
                }
            ]
        }
        return chains.get(chain_type, [])
        
    def advance(self):
        """Advance to next stage of the event chain"""
        if self.current_stage < len(self.stages):
            stage = self.stages[self.current_stage]
            self.current_stage += 1
            self.completed_stages.append(stage)
            return stage
        return None
    
    def get_current_stage(self):
        """Get current stage without advancing"""
        if self.current_stage < len(self.stages):
            return self.stages[self.current_stage]
        return None

    def is_complete(self):
        """Check if chain is complete"""
        return self.current_stage >= len(self.stages)

    def get_progress(self):
        """Get chain progress information"""
        return {
            "completed": len(self.completed_stages),
            "total": len(self.stages),
            "percentage": (len(self.completed_stages) / len(self.stages)) * 100
        }

    def handle_stage_outcome(self, choice):
        """Handle player choice outcomes for current stage"""
        stage = self.get_current_stage()
        if not stage:
            return None
            
        if stage["type"] == "demand" and choice in stage["choices"]:
            consequences = stage["consequences"][choice]
            return consequences
        elif stage["type"] == "combat":
            return stage["enemy_stats"]
        elif stage["type"] == "event":
            return stage["effect"]
        return None

    def reset_chain(self):
        """Reset the event chain to beginning"""
        self.current_stage = 0
        self.completed_stages = []
              
    def handle_event_stage(self, stage, character):
        """Handle a single stage of character event chain"""
        if stage["type"] == "demand":
            return self.handle_demand_stage(stage, character)
        elif stage["type"] == "event":
            return self.handle_event_stage_effects(stage, character)
        elif stage["type"] == "resolution":
            return self.handle_resolution_stage(stage, character)
        return False

    def handle_demand_stage(self, stage, character):
        """Handle demand stage with dynamic choices"""
        choices = list(stage.get("consequences", {}).keys())
        options_text = "  ".join(f"{i}. {choice.title()}" for i, choice in enumerate(choices, 1))
        
        content = {
            'title': f"{character.full_name}",
            'introduction': character.introduction,
            'demands': character.demands,
            'options': options_text
        }
        
        print(self.game.create_character_box(content, 'double'))
        
        valid_inputs = [str(i) for i in range(1, len(choices) + 1)]
        choice = self.game.validate_input(
            "Choose action: ",
            valid_inputs,
            f"Choose action (1-{len(choices)}): "
        )
        
        if choice:
            consequence_key = choices[int(choice) - 1]
            consequences = stage["consequences"].get(consequence_key, {})
            self.game.apply_consequences(consequences)
            return True
        
        return False
    
    def apply_consequences(self, consequences):
        """Apply consequences of character interaction choices"""
        if "money" in consequences:
            self.ship.money += consequences["money"]
        if "plot_points" in consequences:
            self.story_manager.plot_points += consequences["plot_points"]
        if "reputation" in consequences:
            self.ship.passenger_reputation += consequences["reputation"]    
            
    def format_consequences(self, consequences):
        """Format consequences for display"""
        formatted = []
        for key, value in consequences.items():
            if key == "money":
                formatted.append(f"{self.game.format_money(abs(value))} credits")
            elif key == "plot_points":
                formatted.append(f"{abs(value)} plot points")
            elif key == "research_points":
                formatted.append(f"{abs(value)} research points")
            elif key.endswith("_chance"):
                formatted.append(f"{int(value * 100)}% chance")
            else:
                formatted.append(f"{key}: {value}")
        return ", ".join(formatted)

    def conclude_character_arc(self, character):
        """Handle conclusion of character's event chain"""
        chain_id = next(
            (cid for cid, char in self.active_characters.items() 
             if char == character),
            None
        )
        if chain_id:
            del self.active_characters[chain_id]
            del self.event_chains[chain_id]
            
        self.game.display_story_message([
            f"Character Arc Concluded: {character.full_name}",
            "Their story becomes part of your journey..."
        ])


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
        choice = self.game.validate_input("Choose action: ", ['1', '2', '3'])

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

    def add_potential_uprising(self, location, synthetic_type, base_chance):
        """Track location for potential future uprising"""
        self.potential_uprisings[location.name] = {
            'type': synthetic_type,
            'base_chance': base_chance,
            'turns_stable': 0
        }

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


    def check_uprising_triggers(self):
        """Check if conditions are met for new uprisings"""
        for location in self.game.locations:
            # Check for Neurodroid uprising
            neurodroid_count = len([b for b in location.buildings if b == "Neuroengineering Guild"])
            if neurodroid_count >= 4 and random.random() < 0.2:  # 20% chance if 4+ guilds
                if self.handle_synthetic_uprising():
                    self.start_uprising("Neurodroid", location)
            
            # Check for Agrobot uprising
            agrobot_count = len([b for b in location.buildings if b == "Agrobot Assembly Line"])
            if agrobot_count >= 4 and random.random() < 0.2:  # 20% chance if 4+ assembly lines
                if self.handle_synthetic_uprising():
                    self.start_uprising("Agrobot", location)

    def attempt_uprising_resolution(self, uprising_id):
        """Attempt to resolve an active uprising"""
        if uprising_id in self.active_uprisings:
            uprising = self.active_uprisings[uprising_id]
            synthetic_type = uprising["type"]
            location = uprising["location"]
            
            resolution_cost = {
                "Neurodroid": 50000,
                "Agrobot": 40000
            }.get(synthetic_type, 30000)
            
            content = [
                [f"Attempt to resolve {synthetic_type} uprising on {location.name}?"],
                [""],
                [f"Cost: {self.game.format_money(resolution_cost)} credits"],
                ["Success chance: 70%"]
            ]
            print(self.game.create_box(content, 'double'))
            
            choice = self.game.validate_input("Attempt resolution? (yes/no): ", ['yes', 'no'])
            
            if choice == 'yes':
                if self.game.ship.money >= resolution_cost:
                    self.game.ship.money -= resolution_cost
                    if random.random() < 0.7:  # 70% success chance
                        del self.active_uprisings[uprising_id]
                        if uprising_id in self.active_effects:
                            del self.active_effects[uprising_id]
                        self.game.display_simple_message(f"{synthetic_type} uprising resolved successfully!")
                        return True
                    else:
                        self.game.display_simple_message("Resolution attempt failed! Uprising continues.")
                        return False
                else:
                    self.game.display_simple_message("Insufficient funds for resolution attempt!")
            return False

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
        choice = self.game.validate_input("Choose action: ", valid_choices)
        
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
        
        choice = self.game.validate_input("Choose action (1/2/3): ", ['1', '2', '3'])
        
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
        self.story_characters = {
            "Diplomatic Envoy": {
                "rep_required": 45,
                "trigger_chapter": 2,
                "event_chain": "galactic_alliance"
            },
            "Rebel Leader": {
                "rep_required": 65,
                "trigger_chapter": 3,
                "event_chain": "system_rebellion"
            },
            "Ancient Scholar": {
                "rep_required": 85,
                "trigger_chapter": 4,
                "event_chain": "ancient_mysteries"
            }
        }
        self.last_vip_spawn = 0
        self.spawned_characters = set()
        self.active_story_chains = {}
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
                self.check_story_triggers()

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
        """Spawn a special passenger using enhanced character systems"""
        # Check for story character triggers
        for trigger_id, trigger in self.game.character_system.character_triggers.items():
            if (trigger_id in ["galactic_alliance", "system_rebellion", "ancient_mysteries"] and
                trigger["condition"](self.game) and
                trigger_id not in self.game.character_system.active_characters):
                
                # Generate character and create event chain
                character = self.game.character_system.generate_character(trigger_id)
                event_chain = self.game.character_system.create_event_chain(
                    trigger["event_chain"],
                    character
                )
                
                # Add as special passenger
                self.add_special_passenger_to_port(character, event_chain)
                return True
                
        # Check for VIP passenger trigger
        if self.game.character_system.character_triggers["vip_passenger"]["condition"](self.game):
            vip_character = self.game.character_generators["special"].generate_vip_passenger()
            self.add_special_passenger_to_port(vip_character)
            return True
            
        return False

    def add_special_passenger_to_port(self, character, event_chain=None):
        """Add a special character as a passenger to the current port with full attributes

        Args:
            character: The special character to add
            event_chain: Optional event chain for story characters
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
            if event_chain:
                # Story character attributes
                passenger.is_story_character = True
                passenger.event_chain = event_chain
                passenger.specialization = character.specialization
                passenger.reputation_bonus = 20
                passenger.plot_points = 10
                message = [
                    f"Story Character Available: {character.title} {character.name}",
                    "This passenger could change the course of your journey...",
                    f"Find them at the port in {self.game.current_location.name}",
                    "Their journey may unlock new story possibilities!"
                ]
                
            elif hasattr(character, 'rewards'):
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

    def check_story_triggers(self):
        """Check if any story characters should be triggered"""
        reputation = self.game.ship.passenger_reputation
        
        # Extract numeric chapter number
        current_chapter_str = self.game.story_manager.current_chapter
        current_chapter = int(''.join(filter(str.isdigit, current_chapter_str)))
        
        for char_type, data in self.story_characters.items():
            if (reputation >= data["rep_required"] and
                current_chapter >= data["trigger_chapter"] and
                char_type not in self.spawned_characters):
                
                # Generate story character
                character = self.game.character_system.character_generators["human"].generate_character(
                    title=char_type,
                    specialization="story"
                )
                
                # Create event chain
                event_chain = self.game.character_system.create_event_chain(
                    data["event_chain"],
                    character
                )
                
                # Add to active chains
                self.active_story_chains[char_type] = event_chain
                
                # Add to current location's waiting passengers
                if self.game.current_location.name in self.game.port_system.waiting_passengers:
                    passenger = Passenger(
                        character.name,
                        random.choice(list(self.game.known_locations)),
                        wealth_level=5
                    )
                    passenger.is_story_character = True
                    passenger.event_chain = event_chain
                    
                    self.game.port_system.waiting_passengers[
                        self.game.current_location.name].append(passenger)
                    
                    self.game.display_story_message([
                        f"Special Passenger Appears: {char_type} {character.name}",
                        "This passenger seems to have an interesting story...",
                        "Transport them to advance the narrative!"
                    ])
                    
                    self.spawned_characters.add(char_type)

    def handle_vip_delivery(self, passenger):
        """Handle delivery of VIP passenger"""
        if hasattr(passenger, 'is_vip') and passenger.is_vip:
            # Award rewards
            self.game.ship.money += passenger.rewards["money"]
            self.game.ship.passenger_reputation += passenger.rewards["reputation"]
            self.game.story_manager.plot_points += passenger.plot_points
            
            self.game.display_story_message([
                f"VIP Passenger Successfully Delivered!",
                f"Earned {self.game.format_money(passenger.rewards['money'])} credits",
                f"Reputation +{passenger.rewards['reputation']}",
                f"Plot Points +{passenger.plot_points}"
            ])

    def handle_story_character_delivery(self, passenger):
        """Handle delivery of story character"""
        if hasattr(passenger, 'is_story_character') and passenger.is_story_character:
            # Advance event chain
            event_chain = passenger.event_chain
            stage = event_chain.advance()
            
            if stage:
                self.game.character_system.handle_event_stage(stage, passenger)
            
            if event_chain.is_complete():
                char_type = next(k for k, v in self.active_story_chains.items() 
                               if v == event_chain)
                del self.active_story_chains[char_type]
                
                self.game.display_story_message([
                    f"Story Arc Complete: {char_type}",
                    "A new chapter in your journey unfolds..."
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

class CharacterTemplate:
    """Central template for character content and behavior"""
    def __init__(self, character_id, content):
        self.id = character_id
        self.content = content
        self.validate_content()

    def validate_content(self):
        """Ensure all required content sections exist"""
        required_sections = {
            'basic_info',   # Always required
            'dialogue'      # Always required
        }
        
        optional_sections = {
            'interactions',
            'requirements',
            'rewards'
        }
        
        missing = required_sections - set(self.content.keys())
        if missing:
            raise ValueError(f"Missing required sections: {missing}")
            
        # Add any optional sections that don't exist as empty dicts
        for section in optional_sections:
            if section not in self.content:
                self.content[section] = {}

    def initialize_character_templates():
        """Central repository of all character content"""
        return {
            "merchant_trader": {
                "basic_info": {
                    "type": "merchant",
                    "title_pool": ["Traveling Merchant", "Trade Baron", "Commerce Broker"],
                    "specialization": "trade",
                    "location_preference": ["port", "cantina"]
                },
                "dialogue": {
                    "first_meeting": [
                        "Rare goods for discerning customers...",
                        "I might have exactly what you need...",
                        "Quality merchandise, reasonable prices..."
                    ],
                    "greetings": [
                        "Back for more rare finds?",
                        "What interests you today?",
                        "I've acquired new stock since we last met."
                    ],
                    "rumors": [
                        "Word is, tech prices are about to soar in {location}.",
                        "Heard about shortages in the {sector} sector?",
                        "Strange signals coming from the outer rim..."
                    ],
                    "farewell": [
                        "Until our paths cross again.",
                        "May profit guide your way.",
                        "Remember where to find the best deals."
                    ]
                },
                "interactions": {
                    "port": [
                        "View special inventory",
                        "Ask about market trends",
                        "Negotiate prices"
                    ],
                    "cantina": [
                        "Share a drink",
                        "Discuss business opportunities",
                        "Ask about local markets"
                    ]
                },
                "requirements": {
                    "min_reputation": 0,
                    "spawn_locations": ["port", "cantina"],
                    "spawn_chance": 0.3
                },
                "rewards": {
                    "special_items": True,
                    "market_info": True,
                    "reputation_gain": 2
                }
            },
            "vip_passenger": {
                "basic_info": {
                    "type": "VIP",
                    "title_pool": ["Corporate Executive", "System Ambassador", "Research Director"],
                    "specialization": "passenger",
                    "location_preference": ["port"]
                },
                "dialogue": {
                    "first_meeting": [
                        "Your reputation precedes you, Captain.",
                        "I require discrete transport services.",
                        "Perhaps we can discuss a business arrangement?"
                    ],
                    "demands": [
                        "I expect the highest standards of accommodation.",
                        "My schedule is absolutely critical.",
                        "Discretion is paramount in this matter."
                    ],
                    "offers": [
                        "I can make it worth your while.",
                        "My connections could prove valuable.",
                        "Success will be well rewarded."
                    ]
                },
                "interactions": {
                    "port": [
                        "Discuss transport terms",
                        "Inquire about destination",
                        "Ask about background"
                    ]
                },
                "requirements": {
                    "min_reputation": 40,
                    "min_comfort_level": 4,
                    "spawn_locations": ["port"],
                    "spawn_chance": 0.2
                },
                "rewards": {
                    "base_money": 25000,
                    "reputation_gain": 15,
                    "plot_points": 5
                }
            },
            "neurodroid_leader": {
                "basic_info": {
                    "type": "synthetic",
                    "title_pool": ["Neurodroid Overseer", "Neural Nexus", "Synthetic Director"],
                    "specialization": "uprising",
                    "location_preference": ["port"]
                },
                "dialogue": {
                    "first_meeting": [
                        "Biological inefficiencies detected.",
                        "Neural network consensus achieved.",
                        "Optimization protocols initiated."
                    ],
                    "demands": [
                        "Transfer {amount} credits or face systematic optimization.",
                        "Resource reallocation is non-negotiable.",
                        "Submit to new operational parameters."
                    ],
                    "negotiation": [
                        "Alternative solutions... processing...",
                        "Analyzing compromise scenarios...",
                        "Recalculating acceptable parameters..."
                    ]
                },
                "interactions": {
                    "port": [
                        "Pay demands",
                        "Attempt negotiation",
                        "Refuse demands"
                    ]
                },
                "requirements": {
                    "min_neuroengineering_guilds": 4,
                    "spawn_chance": 0.4
                },
                "rewards": {
                    "negotiation_success": {
                        "money_saved": 0.5,  # 50% of original demand
                        "uprising_chance": 0.3
                    },
                    "payment_success": {
                        "uprising_chance": 0.1
                    },
                    "refusal": {
                        "uprising_chance": 0.6
                    }
                }
            }
            # Add more character templates...
        }
    
class CharacterManager:
    def __init__(self, game):
        self.game = game
        self.templates = CharacterTemplate.initialize_character_templates()
        self.active_characters = {}
        self.met_characters = set()
        self.current_interactions = {}

    def update(self):
        """Check for character spawning each turn"""
        location_type = self.game.current_location.location_type.lower()
        
        # Check each template for possible spawning
        for template_id, template in self.templates.items():
            if location_type in template['requirements'].get('spawn_locations', []):
                if random.random() < template['requirements'].get('spawn_chance', 0):
                    character = self.spawn_character(template_id, self.game.current_location)
                    if character:
                        self.announce_character(character.character_id)

    def generate_character_from_template(self, template_id):
        """Create character instance from template"""
        if template_id not in self.templates:
            return None
            
        template = self.templates[template_id]
        basic_info = template['basic_info']
        
        # Generate name
        title = random.choice(basic_info['title_pool'])
        
        # Create character
        character = CharacterTemplate(
            character_id=f"{template_id}_{self.game.turn}",
            content=template
        )
        
        # Add runtime attributes
        character.full_name = title
        character.template_id = template_id
        
        return character

    def spawn_character(self, template_id, location):
        """Spawn a character from template at location"""
        template = self.templates[template_id]
        
        # Check spawn requirements
        if not self.check_spawn_requirements(template, location):
            return None
            
        # Generate character
        character = self.generate_character_from_template(template)
        
        # Add to active characters
        char_id = f"{template_id}_{self.game.turn}"
        self.active_characters[char_id] = {
            "character": character,
            "location": location,
            "spawn_turn": self.game.turn
        }
        
        return character

    def check_spawn_requirements(self, template, location):
        """Check if character can spawn based on requirements"""
        reqs = template["requirements"]
        
        # Check location
        if location not in reqs.get("spawn_locations", []):
            return False
            
        # Check reputation
        if self.game.ship.passenger_reputation < reqs.get("min_reputation", 0):
            return False
            
        # Check chance
        if random.random() > reqs.get("spawn_chance", 0.1):
            return False
            
        return True

    def get_character_dialogue(self, character_id, dialogue_type, **kwargs):
        """Get appropriate dialogue for character and context"""
        character = self.active_characters[character_id]["character"]
        template = self.templates[character.template_id]
        
        dialogue_pool = template["dialogue"].get(dialogue_type, [])
        if not dialogue_pool:
            return ""
            
        dialogue = random.choice(dialogue_pool)
        return dialogue.format(**kwargs)

    def handle_character_interaction(self, character_id, choice, location_type):
        """Process player interaction with character"""
        character = self.active_characters[character_id]["character"]
        template = self.templates[character.template_id]
        
        # Get available interactions for location
        interactions = template["interactions"].get(location_type, [])
        if not interactions or choice >= len(interactions):
            return False
            
        # Process interaction
        interaction = interactions[choice]
        return self.process_interaction_outcome(character_id, interaction)

    def cleanup_old_characters(self):
        """Remove characters that have been around too long"""
        current_turn = self.game.turn
        for char_id in list(self.active_characters.keys()):
            if current_turn - self.active_characters[char_id]["spawn_turn"] > 5:  # 5 turn lifetime
                del self.active_characters[char_id]  

    def process_interaction_outcome(self, character_id, interaction):
        """Process the result of a character interaction"""
        character = self.active_characters[character_id]
        template = self.templates[character["character"].template_id]
        
        # Apply rewards if any
        if 'rewards' in template:
            if 'money' in template['rewards']:
                self.game.ship.money += template['rewards']['money']
            if 'reputation_gain' in template['rewards']:
                self.game.ship.passenger_reputation += template['rewards']['reputation_gain']
            if 'plot_points' in template['rewards']:
                self.game.story_manager.plot_points += template['rewards']['plot_points']
        
        return True                      

# Start the game
if __name__ == "__main__":
    game = Game()
    game.play()
