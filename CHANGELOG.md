# Changes

The release workflow takes each version's notes from this file (the section whose heading is
the version number), so write them for players.

## 1.3.0

Your captain now stays the same captain across the whole trilogy, and the later parts can send
them back here.

- **One captain, every part.** A game started as a recorded captain keeps the captain's id and
  log, and the record now carries the captain's history: what they left in each part, their own
  time (the turns they have lived, whatever the year), and the line of the timeline each game
  is. A save is never rewritten by what happens in another part.
- **Errands from the future.** Cargo 3 can send a captain back to 2420 with a task. The first
  one: level nine's plaque at Gamma has a blank thirteenth line "for the hauler who brought the
  air", and the captain can fill it, or leave it blank, and see the result in 2533.
- **Records from newer games are kept whole.** What a newer game writes into a captain's record
  and this one does not know, it keeps and writes out again.
- **Older versions are named, not broken.** A record that went through Cargo 1.2.1 lost its
  history there; starting with it offers to join it back up with the captain's newer record,
  and says so. An errand meant for a newer version is named when you start and when you export,
  and stays in the record until you update.
- The captain menu shows your own time, your line and your errands.

## 1.2.1

- Saves and captain records move to their own folder, `~/.cargo-saga` (or `CARGO_SAGA_HOME`).
  They used to live in `~/.cargo`, which Rust's package manager also uses, and `CARGO_HOME`,
  which Rust also reads. The first start copies Cargo's files over; the old ones stay put.
- The README now says what the game has long needed: Python 3.8 or newer.

## 1.2.0

Cargo now plays its whole story. It is the first part of a trilogy, set long before Eryxia is
reached, in the years the Hauler Hansa is founded.

- **Three roads, one saga.** Trade, combat or discovery, each with a crisis, a low point and a
  climax: the price squeeze and the vote on the first Mark; the escort recalled at the jump point
  and the pirate dreadnought at the merger parade; the Institute fire and the long burn to the ring.
  Your choices are remembered in an epilogue and in your captain's record, which later parts read.
- **People who come back:** a convoy captain who keeps score of favours, a young hauler, a customs
  inspector who writes everything down, the man from the inner systems who arranges things, a
  family of written-off androids who smuggle food to miners, the Cargolytes' Sixpack, and many
  more.
- **Between docks:** fourteen kinds of enemy and twelve situations, with choices that the right
  gear and crew improve; a bounty board (`hunt`); crew for hire in cantinas.
- **Money:** real trade profit, a hold with a size, markets that feel big loads and recover,
  price forecasts from the Hansa board and the port's broker robot, convoy dues every ten turns
  and bonds that lower them, contracts on the trade road, special cargo that takes hold room.
- **Science:** eleven in-system missions after real astronomy, from radio bursts at YZ Ceti to a
  starshade at Alpha Centauri, flown on your own fuel or bought from the depot.
- **Ships:** the Ironback and Farstrider hulls, and lanes that need them.
- **A new game** asks for difficulty (calmer or busier lanes) and voyage length (short, standard,
  long), and can start from any captain's record, including one from a later part.
- **Help everywhere:** `help`/`h`, short forms for every command, `log` for what the next chapter
  needs, `journal` for people, choices and places (with the real star systems).
- **Fixes:** quests that could not be finished, commands refused inside sub-menus, shop items that
  did nothing, a captain's record that dropped story choices, and many crashes.
- Plays in any terminal from 36 columns wide, Termux included. Standard library only.

## 1.1.0

The base release: the game can be finished on every road. Saves with autosave and continue; the
captain's record (`captain`) to carry a captain between the parts of the saga; one box layout
that fits narrow phone screens; `CARGO_ASCII=1` for terminals without box characters.
