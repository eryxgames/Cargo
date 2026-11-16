# The Cargo trilogy: outline

Working document, 2026-11-14, updated 2026-11-16. Machine-readable parts (characters who span the
saga, promises, timelines) live in `saga.json`. Cargo 1's scenes live in
`cargo1/*.json`, show on the story map (`map.html`) with the old text kept for
comparison, and are built into `cargo.py`, which plays them (1.2).

## Where and when

The wiki's human history gives the frame. Colonies reached Alpha Centauri from
2223; FTL became routine in 2300-2400; the Great Debacle (2501-2530) made
megastructure research a joke; Project ERYX was founded after it, and Eryxia was
found around 2552. The Collective announced itself around 2600, after centuries
underground.

So the trilogy runs from the Hauler Hansa's founding to the eve of ERYX:

| Part | Year (proposed) | What is being born | Main question |
| --- | --- | --- | --- |
| Cargo 1 | about 2420 | the Hansa and its Mark; the first corporate legion; the Collective's first node | who runs the routes |
| Cargo 2 | about 2460 | the Terran Mandate (legions merged), the Concord's houses and gates, the Binary Dawn | who owns the jump |
| Cargo 3 | from about 2533, over several centuries | Project ERYX, which needs something no faction can build | who restarts the Gyrotron, and from where |

Cargo 3 opens just after the Debacle, when anyone talking about ancient
machines is laughed out of the room, and runs for several centuries of external
time on relativistic legs. It ends as the ERYX missions leave, before anyone
reaches Eryxia (the wiki's "discovery" around 2552 is remote observation). The
captain has evidence from two earlier games.

Time dilation does the rest. A captain who spends Cargo 2 on long sublight legs
can be fifteen years older at its end while the routes are forty years older.
That is how one captain can meet themselves.

## The through-line: the Gyrotron

The wiki proposes Stellar Gyrotrons, ancient orbital accelerators that throw
ships to relativistic speed, and notes that the clustering of the most distant
Kuiper belt orbits looks like the remains of one around our own Sun.

- **Cargo 1** finds pieces without knowing what they are. A grey alloy, machined,
  shows up in comet ice, collision dust and mine tailings. It was last heated
  70,000 years ago, when Scholz's Star passed through the Sun's outer comet
  cloud and pulled a segment away. The Stellar Portal is a segment that still
  turns: what goes through comes out at another time. The discovery ending files
  the course home and nobody reads it.
- **Cargo 2** opens the file. The ring is ours, around our own Sun, broken. Whoever
  holds the surviving segments holds a catapult and a door in time. The factions
  learn this one at a time.
- **Cargo 3** is the restart. ERYX needs the Gyrotron to throw its missions out
  towards targets like GW Orionis, about 1,300 light-years away. The Mandate,
  the Concord and the Collective each want to start it from their own end of the
  ring; the Hansa wants it to stay a road. Every captain who crossed the portal
  in any part is somewhere in that crowd, and the older captain in Cargo 1 has
  already told the player how it has to go: start it from home.

Other civilisations are hinted at, never met. The builders left a beacon
pointing at an empty patch of sky. Eryxians and Gordians do not appear.

## The captain across time

- With a captain record carried over, the player's captain is one person across
  all three games. A player may start a new captain; the old one lives on as an
  older non-player character.
- **The older captain in Cargo 1** appears twice, in different places, for
  different later parts:
  - a station bar in act 2, for Cargo 2: pays for your drink, knows your ship's
    private name, pays with a pellet stamped with your registry (a Hansa Mark,
    before there are any);
  - the far side of the portal, for Cargo 3: your hull, older, and a warning.
  Without a record the stranger is never named, only uncannily familiar. With a
  record from that part, the scene uses the record's name and rank: the
  player's own name means the same captain grown old; another name is the
  captain the player went on to play, who talks as if they once flew with you.
- **The clone.** A research colony's insurer grows replacement crews from customs
  scans. One of yours walks out. It has your face, your licence and your debts,
  and has paid off more of them than you have. Split the routes, report it, or
  fight it (the game's unused rogue-captain chain becomes that fight). It turns
  up in Cargo 2 as the other hauler with your name.

## Crossings: starting a part with a captain from another

A new game offers every captain record in the shared folder. Playing as one, the
first scene says who this captain was and why they start again with one ship; a
fresh captain gets a different first scene. Ranks, endings and turns come from the
record ({origin.name}, {origin.rank}, {origin.ending}, {origin.turns}).

| Into | From | Why they start again |
| --- | --- | --- |
| Cargo 1 | nobody (fresh) | a loan, an old ship, a docking slot paid up until Friday |
| Cargo 1 | Cargo 1 (finished) | retirement did not take: after the Hansa a farm drum, after the legion a desk, after the heading nobody read the file, after the tycoon ending a long complaint about prices |
| Cargo 1 | Cargo 2 | a ring segment turned the wrong way: forty years too early, with a rank nobody can read and the navigation computer pulled before the old ship was sold |
| Cargo 1 | Cargo 3 | thrown back from the restart, a century and more: no Hansa yet, the Mandate is three security firms, a shard of the ring still warm in a pocket |
| Cargo 2 (planned) | Cargo 1 | the same captain, forty years on (fewer with dilation): the intro remembers the Hansa charter, the legion, the heading or the tycoon years |
| Cargo 2 (planned) | Cargo 3 | thrown back seventy years by the restart; knows how the Mandate ends and cannot say so |
| Cargo 3 (planned) | Cargo 1 | a century later: slept through it in a Neon's spare sarcophagus, or flew it in relativistic legs |
| Cargo 3 (planned) | Cargo 2 | the old captain from the bar in Cargo 1, finally arriving at their own story |

A record can also come in as a visitor (`captain` command): then it is the older
stranger at the station bar or past the portal, named only if the record is there.

## Factions as they are in Cargo 1

| Later power | In Cargo 1 | Seen as |
| --- | --- | --- |
| Hauler Hansa | the convoy office: carries ships between the stars, charges dues, sells bonds; no common money yet | the player's people; dues and bonds; the charter and the first Mark; contracts; the quantum harp |
| Terran Mandate | security legions of OmniCorp, Stellar Dynamics and the Xylo Consortium; the first hovertank and the first exoskeleton garrison | legion contracts, the commission, the merger, the hovertank to Delta c, knees for Scholz's Star |
| Inner systems (later the Solar Union's Mandate wing) | Serac, who arranges things for Sol's defence contractors and the trading houses | the squeeze, the recall, the fire, one favour, a commission |
| Stellar Concord | research houses: House Rostrom, the Bekkenheim drive tests; underwriters; androids written off at ten years | Yzode van Rostrom, Dharr Santor; Sjoerd Hoving Wirth; the Rootstock |
| Collective | CU-113, a Curator neurodroid at the player's guild (the game's Neurodroid Overseer); the Sowers on the farm drums | the first refusal, the first node, long before vectorspace |
| Other machines | heavy agrobots (Krogg loading docks, Geod founding Delta's farms, Eela boring the Rockwardens' mine); the nanobot colony at Sigma VII; the Unsorted, robots who belong to nothing | jobs, passengers, enclave quests |
| Solarians | a reading-house at Barnard's Star that logs sunspots | Deacon Amaro, who reads trade routes in them |
| Cargo cults | the Cult of the Broken Machine (worships a broken-down hauler at an outpost), the Order of the Lost Gear (collects broken technology), the Star-Shaped Scar Tribe (Zeta Reticuli); the Cargolytes, whose council, the Sixpack, raids convoys for containers | first contact, pilgrims, the holy manifest, the unholy shelf, the brass band; a raid, a tithe counted in TEU |
| Hatters | the Grey Hats, an outpost crew | record cleaning, for a fee |
| Smugglers | the Rootstock: written-off Concord androids moving food and biomass from Beta's drums to Gamma's miners | sealed crates, a spot check, a sting, a family |
| Neonobility | Neons who sleep through decades and buy land before it is worth anything (Conte Ottavine Kraal and her heritarchist, Magister Notary Augias Pfennig); Virtuals, young Neons in holographic bodies (Karen Asquine-Kraal); fluencers, real or fake heirs who stream everything (Brisa, and Lorisa, her twin and manager) | sleeping cargo, freight rates for the weightless, a stream from your hold |
| Technoshamans | the farm drums | blessings with firmware patches, on subscription |

## Characters who outlive their game

| Character | Cargo 1 | Cargo 2 | Cargo 3 |
| --- | --- | --- | --- |
| The captain | the player | the player, or an old NPC | the player, or a name on a memorial |
| The other captain (clone) | partner, rival or runaway | the other hauler with your name | |
| CU-113, Neurodroid Overseer | first neurodroid to refuse an order; six legs and a sensor mast | a node of the Binary Dawn; remembers what you chose | unchanged, several times over |
| Eela (agrobot) | bores the Rockwardens' first gallery; asks if it is in the cooperative | | still digging for Stonewright, if given a share |
| Hedda Mraz | the pirate vendetta | founder of the Void Angels, if spared | |
| Anselm Rockwarden | the cooperative; takes Stonewright sublight | | a name on the keel; Maret Rockwarden (wiki) commands |
| Yzode van Rostrom | junior researcher, then founder of House Rostrom | head of the house | |
| Dharr Santor | flies the fourth drive test, gone eleven minutes, back with three weeks of beard | the drive carries his name | |
| Tylde Kren | archaeophysicist; the samples and the segment | old, still right | her notes, or her upload |
| Conte Ottavine Kraal | sleeping cargo to Delta; buys land next to Geod's Row | wakes thirty years on, asks for you | awake for the restart, barely older |
| Magister Notary Augias Pfennig | her heritarchist; reads your family line and bills her for it | Astin Pfennig, his son or his clone | |
| Serac | arranges the squeeze, the recall and the fire; offers one favour, then a commission | runs the Mandate's (TAM) operations and the Solar Union's inner-systems "defence" wing | has not aged |
| Meza Voce | head of the Rootstock, at half voice | remembers a double cross | |
| Dr Anna-Lise Samples | grew the clone; looks for life in brown dwarf clouds | | |

## Promises

Tracked in `saga.json`; the validator lists any a written part fails to pay.

| Promise | Made in Cargo 1 by | Paid in |
| --- | --- | --- |
| the_seed | CU-113's refusal | Cargo 2 |
| the_stranger | the old hauler and the pellet | Cargo 2 |
| the_first_mark | the Hansa charter | Cargo 2 |
| the_fourth_test | Santor's eleven minutes | Cargo 2 |
| the_other_captain | the clone | Cargo 2 |
| the_heading | the discovery ending | Cargo 2 (opened), Cargo 3 (flown) |
| the_warning | the older captain at the portal | Cargo 3 |
| the_stonewright | Anselm's long run | Cargo 3 |
| the_hollow_rock | the nanobot colony's galleries | Cargo 2 |
| the_lyra_rumour | the Maud Kettle's story and the chirps from Lyra | Cargo 2 |
| the_sleeper | Conte Ottavine goes back to sleep at Delta | Cargo 2 |

## Cargo 1: what changed

Repaired (each was in the game's data and could never happen, or happened with
no content):

- **The Gamma miners' strike** (was the "system rebellion"): waited on a number
  the game never raises; now follows the customs talks.
- **The pirate vendetta**: the game announced Mraz but the chain did not exist;
  now four scenes ending in a choice.
- **The VIP and the travelling merchant**: compared the location type with "port";
  they should appear on port and cantina visits.
- **The Neurodroid Overseer**: had nowhere to appear; it is CU-113, and visits
  after the first node.
- **The mining, combat and research quest lines**: declared, never offered; now
  the Rockwarden cooperative, the legion contracts and House Rostrom.
- **The rogue captain, merchant and researcher chains**: no trigger; now the clone
  fight, cult relics and Rostrom's recruiter.
- **Nine location beats** with a name only: now written. Three of them said
  "alien"; they are now the builders' metal and a cargo cult.
- **The tycoon ending**: ended the game without exporting a captain record.

The game plays all of it since 1.2: the scenes are built into `cargo.py` from
these files, together with a small runtime (conditions, choices, effects, names).
Character names are written once (saga characters in `saga.json`, the rest in
their story file); texts say `{pirate_captain}` or `{pirate_captain.short}`.

Balance: chapter thresholds now mean something (50 plot points for chapter 2,
150 for chapter 3, 350 for an ending), and each ending needs its turning point
(the charter, the commission, the samples). Story chains now pay, so their
rewards were scaled down. Since 1.2 trade profit is real (sale price minus what
the goods cost), the hold has a size, fights take money only when they are lost,
and passenger reputation stops at 100; the trader's chapter asks 150 000 profit
and the trade ending 400 000. Plot points come from what the captain does (scenes,
quests, passengers, good deals, research, first visits, fights won, situations
handled), not from things that merely happen to the ship. Fighters take bounties
(`hunt`), so the combat road is no longer a wait for pirates. Measured with the bot:
discovery ends in about 75 to 95 turns, combat in 115 to 135, trade in 120 to 210.

Shape: every road has a crisis at the start of chapter three (the squeeze, left
behind, the fire), a low point before the finale (margin call, the inquiry, not
proven) and a climax that opens the ending (the vote, roll call, the long burn).
Each costs money, bonds, research, guns or a crew member, and leaves a flag the
epilogue and Cargo 2 read (`cargo1/drama.json`). The trader's finale is the longest,
so it has three more beats between the low point and the vote: striking the first
Mark (full weight or a hair light), a run on it, and the trading houses' offer of a
seat on their board.

Money and the Hansa: between stars the Hansa's convoys carry every ship and charge
dues every ten turns, a little more each time; Hansa bonds lower them and count at
the charter. Markets feel big loads and recover over a few turns; the price board
and the ports' broker robot, TALLY-4, guess prices elsewhere.

Fuel and science: fuel is only burned inside a star system, where a ship flies on
its own. Nine missions after real astronomy (as published by 2026) burn it:
radio bursts at YZ Ceti, weather on Luhman 16, water at WISE 0855, an atmosphere at
TRAPPIST-1e, a starshade at Alpha Centauri, the dust that was Fomalhaut b, astrometry
at Epsilon Eridani, an interstellar comet, and a microlensing parallax
(`cargo1/science.json`). The people who want them flown keep them from getting too
solemn.

People who come back (`cargo1/recurring.json`): Allsa Targa, captain of the
Gamma-Alpha convoy, who keeps score of favours; Pell Okafor, nineteen and without a
ship, who becomes a friend, a debtor or a raider; and Hanne Lauritz, the customs inspector
who writes everything down, bribes included. Each meets the captain early and again in
the middle, can be called into fights, and turns up at the low point and the climax
depending on how they were treated. Old debts come due on their own: the harvest at
Geod's Row, the Kraal dividend, the clone's half of the profits, Mraz's old crew,
the neurodroid that was sold. The low points and climaxes offer paybacks for many earlier
choices: the forty haulers from the jump point at Alpha, Mraz under her own flag, Tadeo
out of the brig, the colony at Sigma VII keeping a copy of the logs in rock.

Hulls: Ironback and Farstrider overhauls; outposts, ruins and listening posts are rough
lanes, the far edge of the system and the systems past the portal deep ones. Voyage
length (short, standard, long) scales what the main story asks for.

Between docks: twelve kinds of enemy (scrap skiffs to a pirate dreadnought, feral
mining drones, a runaway harvester, customs, cultists, legion deserters) and twelve
situations, each with choices that the right gear or crew improves. Crew for hire
in cantinas, four bunks: Shunt the loader, Ambrose the steward, Oksana the
mechanic, Tadeo the gunner, Iolanthe the Solarian navigator and Fenn the broker
(`cargo1/crew.json`). Forty-odd lines of dock gossip fill the cantina between
story rumours (`cargo1/gossip.json`).

Serac (`cargo1/serac.json`) is behind the three crises: his name is in the dock clerks'
mouths during the squeeze, on the recall order at the jump point and on the door of the
office that chaired the fire. He offers one favour in a cantina and collects it before the
end; on the combat road he offers a commission in the inner systems' new defence wing.

People from the names pool (`cargo1/people.json`): Sergeant Hardtack, who tells you who
signed the recall (so you can name him at the inquiry); Deadstick, the pilot who followed
it and asks to fly on your wing at Alpha; Svea Firn's ice core at Sigma VII, with a grey
layer seventy thousand years down that Dr Hammerschultz, chair of the review board, can be
shown; Marit Winze and Vo Brattice at Gamma, when level nine collapses; Dr Anna-Lise
Samples, who grew the clone and drops a balloon into WISE 0855 looking for floaters,
sinkers and hunters (Sagan and Salpeter, 1976); and Lorisa, Brisa's twin and manager.

The Cargolytes (`cargo1/cargolytes.json`) arrive early: the Sixpack raids a convoy for its
containers, Sarga Farga leads the boarders, Ullage preaches at the outposts. Defend, pay a
tithe or cut loose; after the first raid their stevedores can stop a ship between docks.

Legion freight (`cargo1/legion_freight.json`) begins the Mandate's machines: a prototype
hovertank from Alpha to Delta c's dust plains (150 units of hold, its crew aboard, Serac
offering more for a different address), and exoskeleton knee actuators for the garrison at
Scholz's Star within fifteen turns. The epilogues follow both designs to Project ERYX.

The Rootstock (`cargo1/rootstock.json`): Concord androids are written off at ten years,
scrap on the books and so nobody's property. Meza Voce, a nursery model who never turned
her voice up, runs food and biomass from Beta, where the trading houses burn surplus, to
Gamma's miners, who pay company-store prices. A first run past a customs spot check, a
bigger one into a sting, a double cross if the captain wants it, enforcers if they leave.
They also want the garrison's knees.

The trade road's last chapter (`cargo1/contracts.json`) has two Hansa contracts that pay as
trade profit: twenty loader agrobots from Krogg's yard to the farms Mina Perlite is building in
Gamma's mined-out galleries (sign them to the mining company for more, or to the miners'
cooperative), and holocrystal for two towers of Dr Vedral's quantum harp at Beta and Delta,
after which the captain's forecasts are sharper. Two VIPs: Concertina, who sings as two hundred
holograms of herself, to the gala at Epsilon; and Sjoerd Hoving Wirth, a Concord underwriter who
insures the Hansa's convoys if he is flown through the honest flare lane, and whose signature
can carry the vote. In bot games chapter 3a went from about 125 turns to about 70.

Odds and ends (`cargo1/odds.json`) are half-serious nods to the genre in the game's own
voice: a passenger whose ticket is bought next week, the licence exam's question seven
(answer (c), "Press Enter to continue", is not discussed), a volunteer in a red jumpsuit,
the ship's bugrat (which also finds leaks), a signal from beyond the edge of the system
that is a soup advert, an impact shelter that runs a satisfaction survey, a salvage
auction, a crate the auditor rounds up, a broker-robot strike, a training tutorial nobody
can skip and a medal ceremony at which, for once, nothing attacks. They also fill the places
that had no scenes (Omega XIV, Theta III, the listening post in the outer system).

Rewritten: every chapter and ending text, the passenger and synthetics chains,
and the ancient scholar (now human). New: the Hansa charter, the samples, the
legion commission, the older captain, the clone, CU-113, the Sowers'
technoshaman, Krogg, Geod, Eela, the nanobot colony, the Unsorted, the holy
manifest, the deacon, the pilgrims, the Grey Hats, the Lyra rumour, the ruins,
the Stator Field, the Builder Site and the Star-Shaped Scar Tribe.

What players of each style see (from 16 recorded bot games): traders get Krogg,
Geod, the charter, the customs talks, the strike, the deacon, the Lyra story and
sometimes the old hauler. Explorers add the
samples, the clone, the Rostrom line and the old hauler; fighters add the
legions, Mraz, CU-113 and the Unsorted. Players who build guilds and farms meet
the Sowers and the first node; those who build mining platforms meet Eela and the
nanobot colony, late in the discovery path. The ruins, the Stator Field, the
Builder Site and the signal outposts need the player to travel there. The portal
and its older captain need the tycoon's choice (offered every 10 turns to a rich
trader: keep trading, retire, or pay for the portal), so they stay rare.

## Cargo 1 is finished

Cargo 1 (1.2.0) is complete: four endings and the tycoon's, each road with a crisis, a low
point and a climax; 521 story nodes, all reachable and all played by `tools/scenes.py` with
every choice. What it hands on is listed in `CARGO1-HANDOFF.md` (written by
`tools/handoff.py`): eleven promises, 82 flags meant for later parts, and the characters whose
timelines continue (Serac, Meza Voce and the Magister joined the saga file). A captain record
keeps up to 160 flags, the carried ones first.

Left for Dan: a playtest by a person, on a phone in Termux too; the wiki's Ysolde → Yzode.
Optional: the sound kit (cues are already marked in the story).

## The places

Cargo 1's location codes stand for real nearby systems, following the wiki
where it names them (Barnard's Star agricultural, Ross 154 mining, Wolf 359
research, Tau Ceti Synthesis). Astronomy as published by November 2026;
colonies and politics are invented. Details per place: `cargo1/places.json`.

| Code | Real system | ly | Why it fits |
| --- | --- | --- | --- |
| Alpha | Alpha Centauri | 4.4 | the first colonies; Proxima b; an unconfirmed giant in Alpha Cen A's habitable zone |
| Beta | Barnard's Star | 6 | four small planets, all too hot: the farms are mirror-lit drums |
| Gamma | Ross 154 | 9.7 | flare star, no planets known: mined out and cooked |
| Delta | Teegarden's Star | 12.5 | two Earth-mass planets in the habitable zone: the young colony |
| Epsilon | Epsilon Eridani | 10.5 | a Jupiter-mass planet and two belts: the ore exchange |
| Omega XIV | Tau Ceti | 12 | heavy debris disk: Synthesis habitats |
| Sigma VII | Epsilon Indi | 12 | cold giant imaged by JWST, brown dwarf pair: ice mining |
| Theta III | Fomalhaut | 25 | planetesimals collide in its belt (2004, 2023): salvage |
| DSO-Alpha | Luhman 16 | 6.5 | nearest brown dwarf pair: waypoint |
| DSO-Beta | WISE 0855 | 7.4 | coldest brown dwarf, water clouds that come and go: water |
| DSO-Gamma | Scholz's Star | 20 | crossed the outer comet cloud 70,000 years ago |
| Nova Labs | Wolf 359 | 7.9 | flare star, unconfirmed planets |
| Quantum Center | YZ Ceti | 12 | radio bursts from a planet stirring its star's field |
| Stellar Institute | TRAPPIST-1 | 40 | seven rocky planets |
| Ancient Ruins Alpha / Beta | Tau Ceti's debris disk; a moon of Epsilon Indi Ab | | builder foundations and an "anchor" |
| Alien Signal Research Outpost X / Y (game: Alien Outpost) | our far outer system; a dish pointed at Lyra | | listening posts; Y hears the chirps from Lyra |
| Stator Field Megastructure (new) | our outer system, near Sedna's orbit | | the ring's segments, turning together |
| Builder Site (new) | Scholz's Star's wake | | the stolen segment and its beacon |
| Zeta, Eta, Theta, Omega-1, DSO-Delta (past the portal) | Zeta Reticuli, Eta Corvi, Gliese 667 C, Vega, Gliese 229 B | 19-59 | farther systems, another time |

The Gordian moon's system (a G and a K star, a 2.5 Jupiter-mass giant, in Lyra,
hidden in a molecular cloud) has no real match. The nearest candidate is
HD 178911 in Lyra, about 160 ly away: a close G+K pair plus a Sun-like third star
with a planet of at least 6 Jupiter masses. It is too close and too visible to be
hidden, so Er stays fictional. Cargo 1 plants the rumour: a crashed hauler's
survivor whose electronics failed near a moon in Lyra, and magnetic chirps
logged by a research outpost. On the Gordian moon ordinary electronics fail,
which is why its inhabitants are only found much later. Cargo 2 can send an
expedition past HD 178911 to chase it.

## Decided (2026-11-14)

1. Years: about 2420, 2460, and 2533 onwards; Cargo 3 may span several hundred years.
2. Cargo 2's "alien" cultures stay undefined: hybrid colonists of human, biorobot or
   synthetic descent. Some characters call them aliens anyway.
3. "Alien Outpost" becomes "Alien Signal Research Outpost"; "Ancient Ruins" stays;
   "Builder Site" and "Stator Field Megastructure" are added as new locations.
4. The Neurodroid Overseer stays, as CU-113. Neurodroids are synthetic life,
   sometimes humanoid, usually not.

## Open questions

1. The real systems are shown in the captain's journal (`journal`). Should they
   also appear next to the code elsewhere, for example "Gamma (Ross 154)" in the
   location info?
