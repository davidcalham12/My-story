/-
  Chronology of the example novel: run 02412b7fe29e, "the-other-side-of-the-hill".

  Transcribed from output/the-other-side-of-the-hill/bible/timeline.md and
  bible/characters.md, the Story Bible the run itself wrote. Two invariants
  (docs/spec.md §1, validator `lean_chronology`):
    1. the events are in chronological order;
    2. every character's age is possible (0 to 120) at every event.

  Not built: elan, Lean's installer, cannot be installed on the build machine
  without administrator rights. See lean/README.md.
-/

/-- The moments of a day the timeline uses, in story order. -/
inductive Moment where
  | dawn
  | morning
  | afternoon
  | lateAfternoon
  | sunset
  | evening
  | later
  deriving Repr, DecidableEq

def Moment.rank : Moment → Nat
  | .dawn => 0
  | .morning => 1
  | .afternoon => 2
  | .lateAfternoon => 3
  | .sunset => 4
  | .evening => 5
  | .later => 6

structure Event where
  day : Nat
  moment : Moment
  what : String
  deriving Repr

/-- A single number that orders events: the day first, then the moment. -/
def Event.key (e : Event) : Nat := e.day * 10 + e.moment.rank

def events : List Event := [
  ⟨1, .morning, "Leo turns ten; Marcos gives him a leather notebook"⟩,
  ⟨1, .evening, "At supper Leo asks his father about the hill"⟩,
  ⟨2, .morning, "Leo gathers supplies: stones, the fossil, the notebook"⟩,
  ⟨2, .afternoon, "Rosa finds him at the fountain"⟩,
  ⟨3, .morning, "Leo asks Marcos about the hill"⟩,
  ⟨3, .afternoon, "Leo and Bruno explore the lower path and turn back"⟩,
  ⟨4, .morning, "Leo and Bruno set out to climb in earnest"⟩,
  ⟨4, .afternoon, "They climb past the point where the path is unclear"⟩,
  ⟨4, .lateAfternoon, "They reach the crest and meet Elena"⟩,
  ⟨4, .sunset, "Too dark to descend; Elena offers shelter"⟩,
  ⟨5, .dawn, "Leo and Elena descend the hill together"⟩,
  ⟨5, .morning, "Leo arrives home; the family is waiting"⟩,
  ⟨5, .later, "Leo tells his family about Elena; Marcos already knew"⟩
]

def nondecreasing : List Nat → Bool
  | a :: b :: rest => decide (a ≤ b) && nondecreasing (b :: rest)
  | _ => true

/-- Invariant 1: the timeline is in chronological order. -/
theorem events_in_order : nondecreasing (events.map Event.key) = true := by decide

structure Character where
  name : String
  age : Nat
  deriving Repr

/-- The characters whose age the Bible states. Marcos, the grandfather, has none. -/
def characters : List Character := [
  ⟨"Leo", 10⟩,
  ⟨"Rosa", 10⟩,
  ⟨"Elena", 12⟩
]

/-- The whole story happens within one week, so no stated age changes between events. -/
theorem story_within_one_week :
    events.all (fun e => decide (1 ≤ e.day ∧ e.day ≤ 7)) = true := by decide

/-- Invariant 2: every stated age is possible at every event (a `Nat` is never below 0). -/
theorem ages_possible :
    characters.all (fun c => decide (c.age ≤ 120)) = true := by decide
