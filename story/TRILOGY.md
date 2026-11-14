# The Cargo trilogy: outline

Working document, 2026-11-14. Proposals to accept, change or throw out.
Machine-readable parts (characters, promises, timelines) live in `saga.json`.
Cargo 1's new and rewritten scenes live in `cargo1/*.json` and show on the story
map (`map.html`), with the old text kept for comparison. They are drafts until
the game reads its story from the file.

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
| Cargo 3 | about 2533 | Project ERYX, which needs something no faction can build | who restarts the Gyrotron, and from where |

Cargo 3 opens just after the Debacle, when anyone talking about ancient
machines is laughed out of the room. The captain has evidence from two earlier
games.

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

## Factions as they are in Cargo 1

| Later power | In Cargo 1 | Seen as |
| --- | --- | --- |
| Hauler Hansa | independent haulers, a few cooperatives, no common money | the player's people; the charter and the first Mark |
| Terran Mandate | security legions of OmniCorp, Stellar Dynamics and the Xylo Consortium | legion contracts, the commission, the merger |
| Stellar Concord | research houses: House Rostrom, the Bekkenheim drive tests | Ysolde van Rostrom, Dharr Santor |
| Collective | Curator Unit 113 at the player's guild; the Sowers on the farm drums | the first refusal, the first node |
| Solarians | a reading-house at Barnard's Star that logs sunspots | Deacon Amaro, who reads trade routes in them |
| Cargo cults | the Order of the Tarnished Gear (an outpost), the Cult of the Broken Machine (Zeta Reticuli) | first contact, pilgrims, relics |
| Hatters | the Grey Hats, an outpost crew | record cleaning, for a fee |
| Technoshamans | the farm drums | blessings with firmware patches, on subscription |

## Characters who outlive their game

| Character | Cargo 1 | Cargo 2 | Cargo 3 |
| --- | --- | --- | --- |
| The captain | the player | the player, or an old NPC | the player, or a name on a memorial |
| The other captain (clone) | partner, rival or runaway | the other hauler with your name | |
| Curator Unit 113 | first neurodroid to refuse an order | a node of the Binary Dawn; remembers what you chose | unchanged, several times over |
| Hedda Mraz | the pirate vendetta | founder of the Void Angels, if spared | |
| Anselm Rockwarden | the cooperative; takes Stonewright sublight | | a name on the keel; Maret Rockwarden (wiki) commands |
| Ysolde van Rostrom | junior researcher, then founder of House Rostrom | head of the house | |
| Dharr Santor | flies the fourth drive test, gone eleven minutes, back with three weeks of beard | the drive carries his name | |
| Matylda Korinek | archaeophysicist; the samples and the segment | old, still right | her notes, or her upload |

## Promises

Tracked in `saga.json`; the validator lists any a written part fails to pay.

| Promise | Made in Cargo 1 by | Paid in |
| --- | --- | --- |
| the_seed | Unit 113's refusal | Cargo 2 |
| the_stranger | the old hauler and the pellet | Cargo 2 |
| the_first_mark | the Hansa charter | Cargo 2 |
| the_fourth_test | Santor's eleven minutes | Cargo 2 |
| the_other_captain | the clone | Cargo 2 |
| the_heading | the discovery ending | Cargo 2 (opened), Cargo 3 (flown) |
| the_warning | the older captain at the portal | Cargo 3 |
| the_stonewright | Anselm's long run | Cargo 3 |

## Cargo 1: what changed

Repaired (each was in the game's data and could never happen, or happened with
no content):

- **The Gamma miners' strike** (was the "system rebellion"): waited on a number
  the game never raises; now follows the customs talks.
- **The pirate vendetta**: the game announced Mraz but the chain did not exist;
  now four scenes ending in a choice.
- **The VIP and the travelling merchant**: compared the location type with "port";
  they should appear on port and cantina visits.
- **The Neurodroid Overseer**: had nowhere to appear; now Unit 113 visiting after
  the first node.
- **The mining, combat and research quest lines**: declared, never offered; now
  the Rockwarden cooperative, the legion contracts and House Rostrom.
- **The rogue captain, merchant and researcher chains**: no trigger; now the clone
  fight, cult relics and Rostrom's recruiter.
- **Nine location beats** with a name only: now written. Three of them said
  "alien"; they are now the builders' metal and a cargo cult.
- **The tycoon ending**: ended the game without exporting a captain record.

Rewritten: every chapter and ending text, the passenger and synthetics chains,
and the ancient scholar (now human). New: the Hansa charter, the samples, the
legion commission, the older captain, the clone, Unit 113, the Sowers'
technoshaman, the deacon, the pilgrims, the Grey Hats, the stator field, the
beacon and the cult capital.

What players of each style see (from 16 recorded bot games): traders, whose game
lasts about 45 turns, get the charter, the customs talks, the strike, the deacon
and sometimes the old hauler; explorers add the samples, the clone, the Rostrom
line and the old hauler; fighters add the legions, Mraz and Unit 113. Players who
build guilds and farms meet the Sowers and the first node. The portal and its
older captain need the tycoon ending's secret coordinate, so they stay rare.

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
| Ancient Ruins Alpha / Beta | our outer system near Sedna; Scholz's Star's wake | | stator fields (rename proposed) |
| Alien Outpost X / Y | our far outer system; Scholz's Star's track | | builder sites, empty (rename proposed) |
| Zeta, Eta, Theta, Omega-1, DSO-Delta (past the portal) | Zeta Reticuli, Eta Corvi, Gliese 667 C, Vega, Gliese 229 B | 19-59 | farther systems, another time |

The Gordian moon's system (a G and a K star, a 2.5 Jupiter-mass giant, in Lyra,
hidden in a molecular cloud) has no real match. The nearest candidate is
HD 178911 in Lyra, about 160 ly away: a close G+K pair plus a Sun-like third star
with a planet of at least 6 Jupiter masses. It is too close and too visible to be
hidden, so Er stays fictional; Cargo 2 can send an expedition to HD 178911 to
chase the rumour and come back with a better one.

## Open questions

1. Are the years right (2420, 2460, 2533)?
2. Cargo 2's data has alien cultures (Zentari, Novaren, Qyth...). Keep them as
   human cultures with alien-sounding names, or cut them?
3. Should the game show the real system next to the code (for example
   "Gamma (Ross 154)") in the location info?
4. Rename "Alien Outpost" and "Ancient Ruins" in the game, as proposed?
