# Mysteries — The Titan Beacon Chain

Five promises. The intended answer is written under each; the chapters are drafted
from these answers and may not invent others.

- **Why is Noor Adeyemi receiving distress calls in her own voice?**
  Because she recorded that voice herself, at commissioning, and then a machine
  used it exactly as designed. The Convention requires every keeper to record a
  312-phrase distress inventory plus a numeral set, so a beacon whose keeper is
  incapacitated can speak a position report in the keeper's voice. On Contract
  Day 422, with oxidiser at 6% and radar and heaters alternating, Beacon Eleven's
  radar lost power for 41 seconds during a magnetopause blackout. The dead-man
  watchdog did what its stored procedure says: it synthesised a distress call in
  Noor's voice, bearing Beacon Eleven's station hash, and pushed it to the relay.
  The Rev 6.2 cache does not erase on retransmission and cannot tell a live packet
  from a replay, so on the next pass it re-emitted the call omnidirectionally —
  down to the surface as well as up. Noor's own station received it as an inbound
  distress and obeyed the Convention: log verbatim, acknowledge, forward. The
  forwarded copy re-entered the cache with a fresh arrival time, so the six-hour
  depth never aged it out. The loop is not malice, memory or prophecy. It is two
  dumb compliant machines each correctly executing a rule written by people who
  never imagined the other machine.

- **Why do the calls arrive stamped in her future — 1:18 ahead, then 2:36, then 3:54?**
  The Rev 6.2 firmware applies an "Earth-received correction," adding the season's
  one-way lag — 78 minutes — to any surface timestamp it handles, and it reapplies
  the correction every time it handles the packet again, having no flag for
  "already corrected." So the offset is a cycle counter in disguise: 78 minutes per
  loop. Noor divides the offset by 78, gets the number of passes, subtracts, and
  the arithmetic lands on 04:12 on Contract Day 422 — the 41 seconds her beacon
  was dark. The call from the future is a receipt for something that already
  happened.

- **What actually killed Emlen Pryce, and was the abandonment verdict wrong?**
  The same loop, sixteen months earlier, with nobody to do the arithmetic. Pryce's
  beacon dropped for under a minute in a blackout, his watchdog fired his voice,
  and the cache handed it back to him as a live call reporting a keeper down on the
  ice apron. He obeyed the Convention — a received distress must be acknowledged
  and answered — suited up, and walked to coordinates that were a corrected
  timestamp and his own station's guess at where its keeper would be. Eight hours
  of rated heat, 94 K, 1.5 bar of nitrogen stripping it by convection: he died of
  his own compliance 1.2 km from a beacon that never went out. Iver Brekke's
  verdict is wrong in its finding and right in its evidence, which is the whole
  problem with an audit that arrives nine months late.

- **Who is putting Noor's voice on coordinates she never transmitted?**
  Sorrel Vane. The Drift bought a bulk archive dump off a decommissioned relay
  bus six weeks ago; it contained the keeper voice inventories, the raw phrase and
  numeral banks, which can be spliced into any position report in any keeper's
  voice. Vane broadcasts a keeper-down call at shoal ice 40 km offshore so that a
  barge under Convention obligation diverts, runs aground below weather minima,
  and becomes salvage nobody will audit for months. The tell is structural, not
  acoustic: a genuine beacon call carries a live station hash and a pulse count;
  a splice carries either none or a replayed hash from Pryce's dead commissioning
  block. Noor puts that discriminator on the radar band direct to *Tammuz* — twelve
  seconds each way, no relay, nothing for the cache to hold — and Marta Okonkwo
  holds her course.

- **How do you stop a loop the law forbids you to interrupt?**
  Not by powering down — that is the criminal offence, and it would only refire the
  watchdog. Not by ignoring the call — the Convention requires acknowledgment of
  every distress received. The loop persists precisely because the acknowledgments
  are automatic, and Rev 6.2 re-forwards any packet that is not marked
  human-acknowledged, a flag no automation is permitted to set. So Noor answers
  her own distress call herself, live, at the microphone, by voice, with her own
  station identity — obeying the law completely and killing the loop by doing so.
  The cost is that the true log then goes to Enceladus intact: 41 seconds dark,
  timestamped, verbatim, with the mechanism attached and Pryce's file appended. She
  sends it on Contract Day 427 when line of sight returns, knowing no answer can
  exist for 2 hours 36 minutes and no verdict for months. The novella ends with the
  packet away and the beacon lit; the reader learns what she chose, not what Brekke
  decides.
