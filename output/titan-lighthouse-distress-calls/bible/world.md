# World Bible — The Titan Beacon Chain

Titan, late in the second century of human presence in the Saturn system. The moon is exactly what the probes found it to be: 1.5 bar of cold nitrogen at 94 K, 0.14 g, an orange photochemical haze that never clears, water-ice bedrock as hard as granite, and methane-ethane seas in the north that rain, evaporate and rain again. Nothing here is habitable and everything here is useful, because Titan is the only place in the outer system where hydrocarbons can be dipped out of a lake instead of synthesised. Barges cross Kraken Mare; balloon haulers drift the troposphere; none of them can see. So the coasts and the sea-lanes are staked with beacons — squat radar lighthouses on ice piers, each with a keeper, each transmitting a signature pulse and a station identity into haze that swallows light. This story takes place at one of those beacons, on the northern shore, at a season when Earth is 78 light-minutes away.

## Factions

- **Huygens Beacon Authority** — wants the chain lit, continuously and provably, because its charter and its transit levies both depend on unbroken logs; gets it by posting single keepers on eighteen-month contracts, auditing the logs from Enceladus Station months after the fact, and prosecuting any keeper whose beacon goes dark.
- **Kraken Hydrocarbon Consortium** — wants cheap, fast skimming runs across the northern mares; gets it by leaning on the Authority for beacons where its barges want them, and by running its fleet closer to the weather minima than the Convention allows, betting that a late audit is no audit at all.
- **Relay Trust** — wants to remain the only path off the surface; owns the three store-and-forward satellites and rents bandwidth by the packet; gets it by keeping its cache firmware proprietary, undocumented, and decades old.
- **The Drift** — independent balloon haulers and salvage crews with no registry and no insurance; want wrecks, spilled cargo and the contents of relay archives; get them by listening to distress traffic they are not licensed to hear and arriving before anyone official can.

## Technology

- **Beacon stations** — ice-pier towers mounting a 40 kW pulsed 3 cm radar and an omnidirectional identity transmitter; range to a barge transponder about 300 km; each pulse carries a station hash the Authority treats as proof of presence.
- **Store-and-forward relay constellation** — three satellites in Titan orbit that receive surface traffic, cache it, and re-emit it on the next Earth-facing pass; cache depth is six hours, cache contents are not erased on retransmission, and no part of the protocol distinguishes a live packet from a replayed one.
- **Cryosuits** — heated hardshell suits rated for eight hours of surface exposure; heat, not air, is the consumable.
- **Aerostats and skimmer barges** — methane-filled balloons and hulled boats that move freight through haze on radar alone.
- **Station power** — two 300 W(e) radioisotope units for life support and logs, plus a methane–oxygen generator whose oxidiser must be electrolysed from mined water ice at ruinous cost; the radar runs off the genset.

## Rules

- No faster-than-light travel or signalling. Earth is 78 light-minutes one way this season (the system range is 67 to 85); no question asked of Earth is answered in under 2 hours 36 minutes, and no ship reaches Titan in under fourteen months.
- Titan's surface is 1.5 bar, 94 K, 0.14 g, with no free oxygen: nothing burns in the open air, every flame needs carried oxidiser, a breached suit kills by hypothermia in minutes rather than by vacuum, and a dropped object falls seven times slower than on Earth.
- The dense cold atmosphere strips heat by convection far faster than vacuum would. Every machine and body outdoors is on a heat budget, not an air budget; station power is capped at 600 W(e) continuous plus whatever the genset's oxidiser stock allows, and the radar and the habitat heaters cannot both run at full draw.
- The haze is opaque at visible wavelengths and sunlight at the surface is about a thousandth of Earth's. Optical sight beyond a few kilometres is impossible; all navigation, all beaconing and all rescue is done by centimetre-band radar and radio, which the haze does not block.
- Titan is tidally locked with a 15.95-day orbit, so a fixed surface station has direct line of sight to Earth for roughly eight days out of every sixteen. During the blind half, every outgoing and incoming message must pass through the Relay Trust's cache; nothing reaches or leaves the surface unrelayed.
- Titan spends part of each orbit outside Saturn's magnetopause, exposed to the solar wind. These passages produce ionospheric disturbance and total radio blackouts lasting hours, logged and predictable to within about a day.
- Automation is deterministic and dumb. Machines execute stored procedures, clocks drift, firmware misreads timestamps; no system in this world improvises, lies on purpose, or holds an opinion.
- The Beacon Convention is binding law: a keeper must acknowledge every distress signal received, log it verbatim with local timestamp, and may not power down a lit beacon for any reason. Abandonment is a criminal offence tried on Enceladus, on evidence that arrives months late.

## Texture

From inside, Titan is a place of orange dusk that never brightens and never ends, where the loudest thing is the station's own heat exchanger and the second loudest is methane drizzle on the roof. Distance is not measured in kilometres but in delay: the barge is twelve seconds away, the relay ninety, Earth an hour and eighteen minutes and an answer tomorrow. Keepers live by logs, checklists and power margins, and the horizon is a wall of haze with a radar screen painted on it. Everything you know about the world beyond your ice pier arrives as a stored packet, stamped by a clock you did not set, and you have no way at all to look outside and check.
