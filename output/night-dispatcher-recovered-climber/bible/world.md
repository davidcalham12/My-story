# World

The post sits at 2,340 m on the Kehlstein col, a prefab hut bolted to rock below the north face of the Arnkogel: limestone, one cable-car line, three huts, a north couloir that holds ice into August. Night shift is 22:00 to 06:00: one dispatcher alone, the whole mountain routed through a single chain, because the valley repeater is the only thing that reaches the road.

## Technology

- **The repeater chain** — four solar-and-battery masts (Col, Ostgrat, Sattel, Tal) relay voice and data to the valley road. Each is a store-and-forward node: what it cannot pass on at once, it queues.
- **PLB-7 transponder** — the rented beacon every registered party carries, bursting an identifier, a fix, and its own clock stamp. Returned at the valley station, or recovered with its wearer.
- **INSLOG** — the incident log: append-only, stamped by the post clock, mirrored to the valley on the hour. Every call, fix and status change is a numbered line, superseded but never deleted.

## Factions

- **Bergrettung Arnkogel** — the volunteer rescue service that staffs the post; wants every party beaconed, every fix logged, and voice first on the chain, and gets it by controlling who is dispatched and when.
- **The Hydrographic Observatory** — owns the masts and the power on them; wants its snowpack telemetry delivered unbroken, and gets it by holding priority on the data channel and setting the maintenance windows.

## Rules

- A mast that cannot reach the next hop queues up to 64 messages, retries every 20 minutes for 72 hours, then discards; a queued transmission arrives carrying its original clock stamp and no mark of the delay.
- A PLB-7 bursts every 4 minutes while moving and every 30 minutes at rest; its battery is rated 96 hours at -10 °C, and it cannot be switched off in the field.
- A fix is good to ±30 m under open sky and no better than ±120 m under rock; a fix logged without its tolerance is invalid and must be requested again.
- Only the duty controller may set a casualty RECOVERED, and only on two independent confirmations — field-team callsign and beacon tag number — entered within 30 minutes of each other; the line is permanent, and a correction is a new line.
- The night dispatcher works alone, logs a post check every 15 minutes, and may not confirm a call they took themselves; a gap of more than 20 minutes triggers an automatic valley callout.

## Texture

Quiet work with loud stakes: the hiss of an open channel, the click of the log key, a clock checked more often than the window. The mountain is known second-hand — by fix, by burst, by line number. Nothing here is true until it is logged.
