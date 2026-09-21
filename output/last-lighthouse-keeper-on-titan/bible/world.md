# World: The Kraken Mare Light

In 2147, Titan's northern sea is a working waterway. Barges of liquid methane and dissolved nitrogen cross Kraken Mare between the cryo-refineries of Mayda Insula and the export mass-driver at Ligeia Head, hauling hydrocarbons that cost less to lift from Titan's 1.35 m/s² gravity than to synthesize anywhere inboard of Jupiter. The sea is black under a 1.5-bar nitrogen sky at 94 K, methane drizzle falls for weeks, and radar is the only way to see anything. To keep the barges off the shoals, the Mare Authority strung a chain of nineteen crewed light stations around Kraken's coast: radar beacons, weather masts, and store-and-forward relay nodes, each one a tower, a reactor shed, and a habitat for one. Automation ate eighteen of them over thirty years. Station 12, on the Seldon Peninsula, is the last one with a person in it, kept crewed because the Authority's own charter requires a human custodian for the distress network, and because nothing else on Titan can be repaired by an argument.

## Factions

- **The Mare Authority** — wants the sea traffic legally insurable, which means an unbroken distress log; it gets this by owning the beacon chain, mandating that every distress bundle be acknowledged by a human custodian within one relay window, and retiring stations only when an audit says the network can survive without them.
- **Kraken Freight Guild** — wants cheap, fast crossings and fewer mandatory holds; it gets them by running barges under-crewed with shipboard autopilots, and by quietly filing false weather to justify shortcuts through shoal water that the Light's radar can see and their hulls cannot.
- **Huygens Ring Consortium** — wants rent on every bit that leaves Titan; it gets it by owning the three relay satellites and the Earth-facing dish at Ligeia Head, metering bandwidth by the kilobit and prioritizing paid freight telemetry over Authority traffic when a pass is congested.
- **Salvage cooperatives of Mayda Insula** — want wrecks; they get them by monitoring the open distress band, arriving before the Authority can, and treating any beacon that goes unanswered for seventy-two hours as abandoned property under Titan salvage custom.

## Technology

- **Delay-tolerant bundle network (DTN)** — the only comms fabric on Titan: messages travel as signed, timestamped bundles passed hop to hop between buoys, towers, and satellites, each hop taking custody and stamping the bundle. Bundles survive in buoy memory until delivered or expired; they are never truly live.
- **Custodial sea buoys** — sixty anchored floats across Kraken Mare, each a radar reflector, weather sensor, and 30-day bundle cache running on a 40 W radioisotope unit. They re-transmit anything in custody until acknowledged.
- **Voiceprint distress beacons** — Authority-standard pods and suits carry beacons that broadcast synthesized speech in the registered wearer's own recorded voice, so a rescuer hears who is calling and not a tone. Voices are registered once, per person, and every beacon a person has ever signed for carries that voice model.
- **Cryogenic hardsuits** — heated, pressure-neutral shells rated for six hours of surface work; below that they are coffins that conduct heat away faster than the heaters replace it.
- **Station power plant** — a 5 kW Stirling radioisotope unit with a battery bank; it runs the habitat, the radar, and the short-range buoy link continuously, but the high-gain uplink draws more than the plant makes.

## Rules

- No faster-than-light anything. Earth is 79 to 89 minutes away one way depending on orbital geometry; no conversation with anyone off Titan is ever live, and solar conjunction blacks out the Earth link entirely for eleven to fourteen days each Saturn year.
- Titan's curvature limits surface radio to line of sight: about 17 km from the Light's 60-metre mast. Anything farther reaches the station only via the buoy chain or a satellite pass — never directly.
- The Huygens Ring gives six usable passes per Earth day, eleven minutes each. Outside a pass, nothing leaves Titan and nothing arrives; a message sent at the wrong hour waits, and the wait is visible in its custody stamps.
- Bundles cannot be forged or deleted, only delayed, duplicated, or expired. Every bundle carries the signed timestamps of every node that held it, so a message's route and age are always recoverable — and a message may legitimately arrive years after it was composed.
- The station's high-gain uplink draws 7 kW against a 5 kW plant: it can transmit for no more than nine minutes per pass, and doing so browns out the habitat heaters.
- Exposed skin or a failed suit seal at 94 K in 1.5 bar of nitrogen kills by conduction in under ninety seconds. There is no free oxygen anywhere outside a sealed volume, and open flame on Titan requires carrying the oxidizer.
- Liquid methane-ethane has a density near 500 kg/m³. Human bodies, hardsuits, and unballasted cargo sink in Kraken Mare; buoyancy requires sealed tanks, and anything that goes under is at 94 K and preserved indefinitely.
- Titan is tidally locked: Saturn hangs motionless above the same patch of the Light's horizon, and day, night, and the 16-day eclipse cycle are the only clock the sky offers.

## Texture

Inside, the world is small, loud, and cold at the edges. The habitat smells of hot metal and the ammonia tang that creeps in through the airlock. Everything outside arrives as data with an age attached — the weather is four hours old, the barge positions are twenty minutes old, Earth is an hour and a half of one-sided talking. Work is maintenance: scraping tholin sludge off the radar dome, re-anchoring buoys, logging acknowledgements nobody reads. The sea makes no sound worth hearing; the wind is thick and slow and pushes harder than it should. Saturn does not move. The most unnerving thing about Titan is not the cold but the latency: nothing here is ever happening now, and the difference between a memory and a message is only a timestamp.
