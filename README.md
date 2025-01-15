'Cargo' is an experimental sci-fi text game. Find some hints in the [manual](https://github.com/eryxgames/Cargo/wiki/Cargo-Hauler-Ship-Operation-and-Technical-Manual).

# CARGO: Space Trading Saga in Eryxian Universe

A text-based space trading and exploration game where you navigate between planets, outposts, bases, and stations as a merchant captain of a modular cargo hauler.

```console
>>> 
                  ╔════════ C Δ R G Ω ════════╗
                  ║     Space Trading Saga    ║
                  ╚═══════════════════════════╝
                          Version 1.0.1a

```

## Features
- [x] Dynamic Trading System
  - Multiple commodities (tech, agricultural goods, minerals, fuel)
  - Market prices affected by local economy and events
  - Trade embargoes and temporary bans
  - Tariff rates based on reputation and location

- [x] Multiple Location Types
  - Planets with diverse economies
  - Asteroid Mining Bases
  - Deep Space Outposts
  - Research Colonies
  - Each with unique capabilities and bonuses

- [x] Progressive Story Campaign
  - 5 chapters with unique storylines
  - Multiple story branches and achievements
  - Reputation-based rank progression
  - Plot points system unlocking new content

- [x] Resource Management
  - Mining operations with efficiency ratings
  - Building construction (stockmarkets, refineries, etc.)
  - Ship upgrades and equipment
  - Research points and technology unlocks

- [x] Quest System
  - Story missions
  - Transport contracts
  - Combat missions
  - Mining operations
  - Research projects

- [x] Random Events
  - Combat encounters
  - Market fluctuations
  - Natural disasters
  - Discoveries
  - Each with unique consequences and opportunities
     
- [x] Combat System
  - Space battles with pirates, raiders, and militia
  - Combat stats affecting battles (attack, defense, speed)
  - Combat equipment (turrets, shields)
  - Automatic defense systems
  - Battle rewards and penalties
  - Combat reputation tracking
  - Enemy variety with different difficulty levels
  - Combat-based quests and story missions
  - The combat system is integrated through random encounters or missions
  - Affects story progression through milestones 
  - Victories contribute to rank progression and unlock secret location types 

- [x] Progression Systems
  - Character ranks from Explorer to Galactic Legend
  - Ship upgrades (attack, defense, speed)
  - Research technologies
  - Location unlocks
  - Building development

- [x] Cantina and Shop Systems
  - Location information and maps
  - Quest availability
  - Market updates and items
  - Story progression tracking
     
- [x] Passenger Transport
  - Passengers can embark on locations
  - Develop story and plot points 
  - Character Quests    

## Installation
```bash
# Clone the repository
git clone https://github.com/eryxgames/cargo.git

# Run the game
python cargo.py
```
### Core dependencies
- These are standard library modules, no pip install needed.
```
random
os
time
shutil
math
```
- The game currently uses only built-in Python modules.
- Requires Python 3.7+ for proper f-strings and dictionary ordering

## Controls
Simple text commands to navigate gameplay:
- `buy/sell` - Trade goods
- `travel` - Move between locations
- `build` - Construct buildings
- `upgrade` - Improve ship
- `action` - Special actions
- And more...

## Development Screenshots

```console
╔══════════════════════════════════════════════════╗
║ CΔRGΩ      ║ Ship             ║ Planet           ║
║ Turn: 2    ║ ATK: 1           ║ Name: Alpha      ║
║ ¤: 2.0K    ║ DEF: 1           ║ Tech LVL: 5      ║
║ Tech: 0    ║ SPD: 1           ║ Agri LVL: 3      ║
║ Agri: 0    ║ DMG: 28%         ║ ECO: Stable      ║
║ Salt: 0    ║ RP: 43           ║ EFF: 54%         ║
║ Fuel: 0    ║ Explorer         ║ NET: 0           ║
║ Chapter 0  ║ Plot Points: 16  ║ First Steps      ║
╚══════════════════════════════════════════════════╝
┌──────────────────────────────────────────────────┐
│ Tech: 50  │ Salt: ——                             │
│ Agri: 65  │ Fuel: ——                             │
└──────────────────────────────────────────────────┘
╭──────────────────────────────────────────────────╮
│ Commands: buy/b, sell/s, upgrade/u,              │
│ travel/t, repair/r, info/i, build/bl,            │
│ cantina/c, shop/sh, action/a, end/e              │
╰──────────────────────────────────────────────────╯
╭──────────────────────────────────────────────────╮
│ Choose action:                                   │
╰──────────────────────────────────────────────────╯
```

```console
>>> action        
╭──────────────────────────────────────────────────────────────╮
│ Available Research Points: 43                                │
╰──────────────────────────────────────────────────────────────╯
┌──────────────────────────────────────────────────────────────┐
│ Actions:    │ Cost/Description                               │
│ research    │ Research new technologies                      │
│ scout       │ Scout area (Cost: 50 RP)                       │
│ geoscan     │ Geological scan (Cost: 75 RP)                  │
│ revolution  │ Incite revolution (Cost: 100 RP)               │
│ manipulate  │ Manipulate market (Cost: 60 RP)                │
│ status      │ View research status                           │
│ back        │ Return to main menu                            │
└──────────────────────────────────────────────────────────────┘
╭──────────────────────────────────────────────────────────────╮
│ Choose action type:                                          │
╰──────────────────────────────────────────────────────────────╯
>>> research
┌──────────────────────────────────────────────────────────────┐
│ Research Option │ Cost│ Description                          │
│ xenoeconomy     │ 100 │ Reduces trade taxes                  │
│ telemetry       │ 150 │ Increases scout success rate         │
│ geophysics      │ 200 │ Improves mining efficiency           │
│ chronopolitics  │ 250 │ Increases revolution success rate    │
│ exogeology      │ 300 │ Increases mining output              │
│ psychodynamics  │ 350 │ Allows market price manipulation     │
└──────────────────────────────────────────────────────────────┘
╭──────────────────────────────────────────────────────────────╮
│ Choose research option (xenoeconomy, telemetry, geophysics,  │
│ chronopolitics, exogeology, psychodynamics):                 │  
╰──────────────────────────────────────────────────────────────╯  
>>>
```

```console
>>> information
╔══════════════════════════════════════════════════════════════╗
║ Ship Information      ║ MAP                                  ║
║ Attack: 1             ║ Name: Gamma                          ║
║ Defense: 1            ║ Type: Planet                         ║
║ Speed: 1              ║ Tech Level: 8                        ║
║ Hull Damage: 99%      ║ Agri Level: 2                        ║
║ Money: 1.5K           ║ Research Points: 20                  ║
║ Research Points: 147  ║ Economy: Declining                   ║
║ Cargo:                ║ Mining Efficiency: 45%               ║
║   Tech: 55            ║ Current Market:                      ║
║   Agri: 0             ║   Tech: 22                           ║
║   Salt: 0             ║   Agri: 70                           ║
║   Fuel: 0             ║   Salt: 60                           ║
║ Items:                ║   Fuel: 120                          ║
║   Scanner: 1          ║ Buildings:                           ║
║ Combat Record:        ║   No buildings                       ║
║   Victories: 0        ║ Mining Operations:                   ║
║   Defeats: 2          ║   No mining platforms                ║
╚══════════════════════════════════════════════════════════════╝
>>>
```
