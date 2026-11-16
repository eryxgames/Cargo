'Cargo' is an experimental sci-fi text game. Find some hints in the [manual](https://github.com/eryxgames/Cargo/wiki/Cargo-Hauler-Ship-Operation-and-Technical-Manual).

# CARGO: Space Trading Saga in Eryxian Universe

A text-based space trading and exploration game where you navigate between planets, outposts, bases, and stations as a merchant captain of a modular cargo hauler.

```console
>>> 
        ╔════════ C Δ R G Ω ════════╗
        ║     Space Trading Saga    ║
        ╚═══════════════════════════╝
                Version 1.2.0

```
## Development Notes
🛠 Current Status: Experimental Prototype.
CARGO is a continuously evolving universe. Expect changes, embrace the chaos!

[Eryxian Universe Wiki](https://github.com/eryxgames/eryxian/wiki) 
- [x] New contract system
- [x] Save / load, autosave
- [x] Captain's record (carry a captain between the parts of the Cargo trilogy)
- [x] Layout that fits narrow phone screens (Termux), from 36 columns up
- [x] All three endings verified reachable (see `tools/`)
- [x] Core storyline and characters: the story is written as data in `story/`
      (storykit format, with a validator and a story map) and built into `cargo.py`
- [x] Captains from other parts of the saga: start a new game as a recorded captain,
      or meet one as an older stranger (`tools/make_captain.py` makes test records)
- [x] Captain's journal (`journal`/`j`), cantina rumours, an epilogue after every ending
- [ ] New quest system 
- [ ] New local/global events
- [ ] New items
- [ ] New enemies
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

- [x] Progressive Story Campaign
  - Chapters with unique storylines
  - Multiple story branches and achievements
  - Reputation-based progression
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
  - Each with consequences and opportunities
     
- [x] Combat System
  - Space battles with pirates, raiders, and militia
  - Combat reputation tracking
  - Enemy variety with different difficulty levels
  - Combat-based quests and story missions
  - The combat system is integrated through random encounters or missions
  - Affects story progression through milestones 
  - Victories contribute to rank progression and unlock secret location types 

- [x] Progression Systems
  - Character ranks 
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
  - Passenger contracts
  - Develop story and plot points 
  - Character Quests    

## Installation
```bash
# Clone the repository
git clone https://github.com/eryxgames/cargo.git

# Run the game
python cargo.py
```
### On a phone (Termux)
```bash
pkg install python git
git clone https://github.com/eryxgames/cargo.git
cd cargo && python cargo.py
```
The screens rearrange themselves for narrow terminals (36 columns and up); nothing
is cut off. Set `CARGO_ASCII=1` if your terminal cannot draw the box characters.
### Core dependencies
- These are standard library modules, no pip install needed.
```
base64  hashlib  json  math  os  random  re  shutil  sys  time  unicodedata  zlib
```
- The game currently uses only built-in Python modules.
- Requires Python 3.7+ for proper f-strings and dictionary ordering

## Controls
Type a command, or its short form, and press Enter. `help` (or `h`) shows every command
and how the game works; each location also lists its own commands under the status line.

| Command | Short | What it does |
|---|---|---|
| `buy` / `sell` | `b` / `s` | Trade goods: `tech/t`, `agri/a` (also `agro`), `salt/s`, `fuel/f` |
| `travel` | `t` | Move to another location |
| `port` | `p` | Passengers, VIPs and contracts |
| `hunt` | `hu` | The bounty board: pick a wanted ship and go after it (uses the turn) |
| `hansa` | `ha` | Hansa terminal: convoy dues, bonds that lower them, the price board |
| `cantina` | `c` | Rumours, people and quests |
| `shop` | `sh` | Equipment for the ship |
| `build` | `bl` | Construct buildings |
| `upgrade` | `u` | Improve attack, defense or speed |
| `repair` | `r` | Repair the hull (at research colonies `r` is `research`) |
| `mine` / `action` | `m` / `a` | Mining, and what the place offers (where available) |
| `info` | `i` | Prices, buildings and news here |
| `end` | `e` | End the turn and stay |
| `log` | `l` | Story progress: open milestones and what opens the next chapter |
| `journal` | `j` | People met, choices the future will remember, places and the real stars behind them |
| `captain` | `cap` | The captain's record: export it, or take in a captain from another game |
| `save` / `load` | `sv` / `ld` | Save under a name, or load a saved game |
| `help` | `h` | All commands, shortcuts and a short guide |
| `quit` | `q` | Leave the game |

Some commands exist only at certain places (mining at asteroid bases, research at colonies);
`help` lists them. Inside a menu, press Enter on an empty line to go back.

A few rules worth knowing:
- The hold has room for 400 units of each good, and cargo equipment adds room.
- Trade profit is what you sell for minus what you paid, so selling at a loss counts against you.
- Between docks you meet a dozen kinds of enemy (scrap skiffs, corsair wings, feral mining drones,
  a runaway harvester, customs cutters, cultists, legion deserters, motherships) and a dozen
  situations (distress beacons, derelicts, ion storms, comet tails, a stowaway, a fluencer's yacht).
  Each offers choices: fight, run, pay, talk, and better ones for the right gear or crew.
  Fights take money and cargo only when you lose.
- Cantinas have crew for hire, four bunks: a loader (more hold), a steward (better fares),
  a mechanic, a gunner, a Solarian navigator and an old broker (less tax).
- Plot points move the story. They come from doing things: scenes, quests, passengers, good deals,
  research, first visits, fights won. The status line shows how many the next chapter needs, and
  `log` shows the rest. Stuck for a while? Have a drink in the cantina.
- The Hansa's convoys carry ships between the stars. Every 10 turns they charge convoy dues,
  a little more each time; Hansa bonds lower them. Unpaid dues gather a surcharge, and the
  convoy master takes cargo for them.
- Big loads move prices: a full hold sold at once drops a planet's price by about 8%, more at
  small outposts, less where there is a stock market. Prices drift back over a few turns.
  The Hansa price board and the port's broker robot guess prices elsewhere: close for docks
  you saw lately, loose for old news, a rough guess for places you never visited.
- Fuel is cargo. Between stars the convoy carries you; inside a star system you fly yourself,
  and the science missions (radio bursts at YZ Ceti, weather on Luhman 16, a starshade at
  Alpha Centauri, an interstellar comet...) burn fuel, or you buy the burn from the depot.
- Each road through the story has a crisis in chapter three, a low point before the finale
  and a climax that opens the ending. They cost real money, bonds, research or crew.
- A new game asks for a difficulty and a voyage length. Easy has calmer lanes (fewer
  interruptions) and gentler fights, Expert busier lanes and harder ones. A short voyage's
  chapters ask for 40% less, a long one's for half as much again.
- Rich captains draw bigger pirates, and pirates take a bigger share from them.
- Hulls: the old hauler you start with, then an Ironback (60,000) and a Farstrider (220,000)
  from a planet's shipyard (`upgrade`, then `hull`). Each fights and carries better and costs far
  more to repair. Outposts, ruins and listening posts are rough going for the old hull; the far
  edge of the system and the systems past the portal need a Farstrider.
- People come back: a convoy captain, a young hauler and a customs inspector meet you early,
  again later, and turn up at the crisis or the climax depending on how you treated them.
  Old choices come due too, for better or worse, and friends can be called into a fight.
- Special cargo takes hold room until it is delivered: a legion's prototype hovertank
  (150 units, Alpha to Delta), exoskeleton parts for a garrison (40 units, on a deadline),
  sealed crates for smugglers who would rather you did not ask. You are told what is loaded
  and unloaded, the Hold figure counts it, and the `journal` lists what is aboard.
- On the trade road's last chapter the Hansa offers contracts that pay as trade profit (loader
  agrobots for Gamma's underground farms, crystal for the quantum harp's towers) and two VIPs
  want passage. The finished harp sharpens your price forecasts.
- Some enemies only turn up after the story introduces them: Cargolyte stevedores after the
  Sixpack's first raid, Rootstock enforcers after you meet the family.
- Passenger reputation runs from 0 to 100.
- Every 10 turns a rich trader is asked whether to keep trading, retire, or pay for the portal.

A new game offers to start as any captain whose record is in `~/.cargo/captains/`:
one who finished this game, or one carried back from a later part of the saga.

## The story
Cargo 1 is the first part of a trilogy. What it hands to Cargo 2 and 3 (promises, the flags a
captain record carries, characters who go on) is listed in `story/CARGO1-HANDOFF.md`.
The scenes, characters and places are written in `story/` (see `story/TRILOGY.md` for
the outline and `storykit/` for the format) and built into `cargo.py` by
`python tools/build_story.py`, so the game stays one file. Writers can play a story
file directly: `python tools/build_story.py --out my.json` then `CARGO_STORY=my.json python cargo.py`.

## Sound (optional)
A folder `cargo-kit/` next to `cargo.py` with a `sound.py` that has `play(name)` gives
the story its sound cues (intro, portal, ending...). Without it the game is silent.
`CARGO_SOUND=0` turns sound off.

## Saving
The game saves itself after every turn (slot `autosave`) and asks whether to continue
when you start it again. `save` writes a named slot, `load` lists them. Saves are plain
JSON files in `~/.cargo/cargo1/saves/` (set `CARGO_HOME` to keep them somewhere else).

## The captain's record
`captain` → `export` writes your captain to `~/.cargo/captains/` and prints the same
record as one line of text beginning with `CARGO:`. The file is picked up by the other
parts of the trilogy on the same device; the line of text can be copied to another
device or into the browser version. `captain` → `import` takes in a captain from another
part (or another playthrough). Reaching an ending writes the record automatically.
Quests and milestones can ask for a visiting captain with the requirement
`{"visiting_captain": {"game": "cargo2"}}` (optionally `"ending"` or `"flag"`).

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
