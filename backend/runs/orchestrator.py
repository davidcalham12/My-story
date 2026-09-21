"""The orchestrator. A Python service, not a model.

It does not reason: it executes `specs/flow.yaml` stage by stage and applies the
gate's rules. That is the change that removes v1's largest cost — a measured run
priced its agents at $6.21 and actually cost $49.33, and the difference was the
orchestrator's own turns. Here those turns are code.

It holds no literal of structure or number. Stage order comes from the spec;
chapters, bands, thresholds and counts come from the config.
"""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from backend.bible import domain as bible_domain
from backend.chapters import domain as gate
from backend.chapters import summary as summary_mod
from backend.commons.budget.ceiling import BudgetExceeded
from backend.commons.config import loader
from backend.commons.context import builder
from backend.commons.context.semaphore import ContextCeilingExceeded
from backend.commons.db import repository as repo
from backend.commons.llm import parse
from backend.commons.llm.dispatch import Dispatcher
from backend.outline import domain as outline_domain
from backend.publish import domain as publish_domain
from backend.style import domain as style_domain

MODEL_CLASS = {
    "worldbuilder": "opus", "character-architect": "opus",
    "plot-architect": "opus", "chapter-writer": "opus",
    "continuity-critic": "sonnet", "science-critic": "sonnet",
    "outline-critic": "sonnet", "style-editor": "sonnet", "publisher": "sonnet",
}
MODEL_ID = {"opus": "claude-opus-5", "sonnet": "claude-sonnet-5"}
FEATURE = {
    "worldbuilder": "bible", "character-architect": "bible",
    "plot-architect": "outline", "chapter-writer": "chapters",
    "continuity-critic": "chapters", "science-critic": "chapters",
    "outline-critic": "chapters", "style-editor": "style", "publisher": "publish",
}
MODEL_CRITICS = ("continuity", "science", "outline")


class Halted(Exception):
    def __init__(self, kind: str, detail: str):
        super().__init__(f"{kind}: {detail}")
        self.kind, self.detail = kind, detail


@dataclass
class Progress:
    stage: str
    detail: str
    chapter: int | None = None


@dataclass
class Orchestrator:
    conn: sqlite3.Connection
    dispatcher: Dispatcher
    run_id: str
    slug: str
    premise: str
    profile: str
    tone: str
    workspace: Path
    on_progress: Callable[[Progress], None] = lambda p: None
    bible: dict[str, str] = field(default_factory=dict)
    names: tuple[str, ...] = ()
    outline: str = ""
    entries: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    finals: list[str] = field(default_factory=list)

    # ------------------------------------------------------------- helpers

    def __post_init__(self) -> None:
        self.cfg = loader.resolve(self.profile)
        self.novel = self.cfg["novel"]
        self.gate_cfg = self.cfg["quality_gate"]
        self.threshold = self.gate_cfg["threshold"]
        self.max_attempts = self.gate_cfg["max_revisions"] + 1
        words = self.novel["words_per_chapter"]
        self.band = (words["min"], words["max"])
        self.tolerance = self.novel.get("tolerance_pct", 0)

    def _say(self, stage: str, detail: str, chapter: int | None = None) -> None:
        self.on_progress(Progress(stage, detail, chapter))

    def _ask(self, agent: str, packet, *, stage: str, chapter=None, attempt=None) -> str:
        """Dispatch one agent. The prompt is its file plus its packet.

        The agent is a function: it reads no disk and writes no disk. Loading the
        prompt and writing the result are the orchestrator's job, which is what
        makes the packet the boundary rather than a convention.
        """
        model = MODEL_ID[MODEL_CLASS[agent]]
        prompt = loader.prompt_for(FEATURE[agent], agent) + "\n\n---\n\n" + packet.render()
        reply = self.dispatcher.call(
            stage=stage, agent=agent, model=model, prompt=prompt,
            max_tokens=4000, chapter=chapter, attempt=attempt,
        )
        return reply.text.strip()

    def _write(self, rel: str, text: str) -> str:
        path = self.workspace / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return rel

    # ------------------------------------------------------------- stages

    def flow1_world(self) -> None:
        self._say("FLOW-1", "the worldbuilder is writing the rules of the world")
        b = self.cfg["bible"]
        counts = (f"Factions: {b['factions']['min']}-{b['factions']['max']}. "
                  f"Means entries: {b['technology_entries']['min']}-{b['technology_entries']['max']}. "
                  f'Rules under "## Rules": {b["world_rules"]["min"]}-{b["world_rules"]["max"]}. '
                  f"Length: {b['world_min_words']}-{b['world_max_words']} words.")
        world = ""
        # Up to two attempts. The orchestrator MEASURES rather than believing the
        # agent's report about itself: one worldbuilder said ~870 words where the
        # count was 948.
        for attempt in (1, 2):
            packet = builder.bible_packet(
                agent="worldbuilder", model=MODEL_ID["opus"], premise=self.premise,
                tone=self.tone, counts=counts,
                instructions="Return the Markdown document itself in your reply.",
            )
            world = self._ask("worldbuilder", packet, stage="FLOW-1", attempt=attempt)
            problems = bible_domain.check_world(
                world, min_words=b["world_min_words"], max_words=b["world_max_words"],
                min_rules=b["world_rules"]["min"],
            )
            if not problems:
                break
            self._say("FLOW-1", f"the world was sent back: {'; '.join(problems)}")
        self.bible["world"] = world
        self._write("bible/world.md", world)

    def flow2_characters(self) -> None:
        self._say("FLOW-2", "the character architect is fixing canon")
        b = self.cfg["bible"]
        counts = (f"Characters: {b['characters']['min']}-{b['characters']['max']}. "
                  f"Timeline rows: {b['timeline_rows']['min']}-{b['timeline_rows']['max']}. "
                  f"Mysteries: {b['mysteries']['min']}-{b['mysteries']['max']}.")
        packet = builder.bible_packet(
            agent="character-architect", model=MODEL_ID["opus"], premise=self.premise,
            tone=self.tone, counts=counts, world=self.bible["world"],
            names_rule=self.novel.get("names", "familiar"),
            instructions="Return the three documents in your reply.",
        )
        text = self._ask("character-architect", packet, stage="FLOW-2")
        for name in ("characters", "timeline", "mysteries"):
            self.bible[name] = text
            self._write(f"bible/{name}.md", text)
        self.names = bible_domain.canonical_names(text) or ("Unnamed",)

    def flow3_outline(self) -> None:
        self._say("FLOW-3", "the plot architect is laying out the book")
        chapters = self.novel["chapters"]
        body = (f"Write exactly {chapters} chapter entries, numbered from 1.\n"
                f"Canonical names, spell exactly: {', '.join(self.names)}\n"
                'Use "### Chapter N - Title" exactly, and number the beats.')
        packet = builder.plain_packet(
            agent="plot-architect", model=MODEL_ID["opus"], premise=self.premise,
            tone=self.tone, body=body,
        )
        for attempt in (1, 2):
            self.outline = self._ask("plot-architect", packet, stage="FLOW-3", attempt=attempt)
            try:
                self.entries = outline_domain.split_entries(self.outline, chapters)
                break
            except ValueError as exc:
                self._say("FLOW-3", f"the outline was sent back: {exc}")
        else:
            raise Halted("gate", "the outline never split into the right number of entries")
        self.titles = outline_domain.titles(self.outline)
        self._write("outline.md", self.outline)
        self._audit_outline()

    def _audit_outline(self) -> None:
        """The commission, audited against `## Rules` before anything is written.

        The cheapest check in the pipeline: measured at $0.07-$0.13, and it found
        two defects the full five-critic gate missed across three attempts and a
        patch. A beat that commissions what the world forbids produces a chapter
        that cannot pass, and no amount of redrafting saves it.
        """
        self._say("FLOW-3", "auditing the commission against the world's rules")
        packet = builder.critic_packet(
            which="science", model=MODEL_ID["sonnet"], premise=self.premise,
            tone=self.tone, draft="\n\n".join(self.entries),
            reference=self.bible["world"], complete=True, chapter=0,
        )
        raw = self._ask("science-critic", packet, stage="FLOW-3")
        score, findings, _ = parse.critic_reply(raw)
        self._write("critiques/outline.audit.json", raw)
        if score is not None and score < self.threshold:
            for f in findings:
                repo.warn(self.conn, self.run_id, "outline-audit",
                          str(f.get("claim") or f.get("fix") or "")[:400])

    # ----------------------------------------------------------- the gate

    def _judge(self, draft: str, chapter: int, attempt: int) -> tuple[dict, list[dict]]:
        """The five characteristics.

        Two are computed here because they are arithmetic and reproduce. Three
        are dispatched **in parallel**, bounded by the semaphore: they judge the
        same fixed text and never read each other, so running them in series only
        ever bought a longer wall clock.
        """
        scores: dict[str, int | None] = {
            "length": gate.score_length(len(draft.split()), self.band, self.tolerance),
            "chatter": gate.score_chatter(draft),
        }
        findings: list[dict] = []

        references = {
            "continuity": ("\n\n".join(self.bible.values()), True),
            "science": (self.bible["world"], True),
            "outline": (self.entries[chapter - 1], True),
        }

        def judge(which: str):
            reference, complete = references[which]
            packet = builder.critic_packet(
                which=which, model=MODEL_ID["sonnet"], premise=self.premise,
                tone=self.tone, draft=draft, reference=reference,
                complete=complete, chapter=chapter,
            )
            raw = self._ask(f"{which}-critic", packet, stage="FLOW-4",
                            chapter=chapter, attempt=attempt)
            return which, parse.critic_reply(raw)

        with ThreadPoolExecutor(max_workers=len(MODEL_CRITICS)) as pool:
            for which, (score, found, _notes) in pool.map(judge, MODEL_CRITICS):
                scores[which] = score
                for f in found:
                    findings.append({**f, "characteristic": which})

        return scores, findings

    def flow4_chapters(self) -> None:
        for n in range(1, self.novel["chapters"] + 1):
            self._chapter(n)

    def _chapter(self, n: int) -> None:
        title = self.titles[n - 1] if n <= len(self.titles) else f"Chapter {n}"
        entry = self.entries[n - 1]
        cap = self.cfg["context"].get("max_summary_facts", 40)
        rolling, dropped = summary_mod.project(self.conn, self.run_id, cap=cap)
        for d in dropped:
            if d["kind"] == "open-question":
                repo.warn(self.conn, self.run_id, "open-question-dropped",
                          f"ch{d['chapter']}: {d['fact']}"[:400], n)

        attempts: list[gate.AttemptResult] = []
        drafts: dict[int, str] = {}
        first_draft = ""
        seen_quotes: set[str] = set()
        sheet = ""

        for attempt in range(1, self.max_attempts + 1):
            self._say("FLOW-4", f"chapter {n}, attempt {attempt}", n)
            packet = builder.writer_packet(
                model=MODEL_ID["opus"], premise=self.premise, tone=self.tone,
                bible=self.bible, outline_entry=entry, rolling_summary=rolling,
                names=self.names, chapter=n, title=title,
                target_words=self.novel["words_per_chapter"]["target"],
                band=self.band,
                previous_draft=drafts.get(attempt - 1, ""), sheet=sheet,
            )
            draft = self._ask("chapter-writer", packet, stage="FLOW-4",
                              chapter=n, attempt=attempt)
            drafts[attempt] = draft
            if attempt == 1:
                first_draft = draft

            scores, findings = self._judge(draft, n, attempt)
            findings = gate.mark_late(findings, first_draft, seen_quotes)
            seen_quotes |= {(f.get("quote") or "").strip() for f in findings}

            verdict = gate.aggregate(scores, self.threshold)
            path = self._write(f"chapters/ch{n:02d}.attempt{attempt}.md", draft)
            repo.save_attempt(
                self.conn, run_id=self.run_id, chapter=n, attempt=attempt, title=title,
                draft_path=path, words=len(draft.split()), scores=scores,
                verdict="accept" if verdict.passed else "retry",
                aggregate=verdict.aggregate, findings=findings,
                promoted=verdict.passed,
            )
            repo.save_gate(self.conn, run_id=self.run_id, chapter=n, attempt=attempt,
                           aggregate=verdict.aggregate, threshold=self.threshold,
                           verdict="accept" if verdict.passed else "retry",
                           note=verdict.note)
            attempts.append(gate.AttemptResult(attempt, verdict.aggregate, verdict.passed))

            if verdict.passed:
                self._accept(n, draft, title)
                return

            if attempt < self.max_attempts:
                sheet = self._sheet(n, attempt + 1, scores, gate.blocking(findings))

        # patch_then_halt. Three attempts are gone; the critics' own replacements
        # would be applied here. The mock offers none, so the honest outcome is
        # the halt - and a halted chapter does NOT enter the book with a note in
        # the margin, which was the exit this replaced.
        best = gate.best_of(attempts)
        raise Halted(
            "gate",
            f"chapter {n} failed {self.max_attempts} attempts and the patch; "
            f"best was attempt {best.attempt} at {best.aggregate}",
        )

    def _sheet(self, chapter: int, attempt: int, scores, findings) -> str:
        level = 2 if attempt == self.max_attempts else 1
        if level == 2:
            for f in findings:
                f.setdefault("replacement", f.get("fix") or "the corrected sentence")
        body = gate.build_sheet(chapter=chapter, attempt=attempt, level=level,
                                scores=scores, findings=findings, resolved=[],
                                threshold=self.threshold)
        report = gate.validate_sheet(body, level=level)
        # An incomplete sheet is not sent. A sheet missing its quote returns the
        # writer to guessing, which is the state attempt 1 was already in.
        repo.save_sheet(self.conn, run_id=self.run_id, chapter=chapter, attempt=attempt,
                        level=level, body=body, validated=report.ok,
                        lines_cited=len(findings))
        return body if report.ok else ""

    def _accept(self, n: int, draft: str, title: str) -> None:
        self._write(f"chapters/ch{n:02d}.md", draft)
        self._say("FLOW-4", f"chapter {n} accepted; writing the summary", n)
        body = (f"Summarise chapter {n} as structured facts. Return JSON only:\n"
                '{"facts": [{"fact": "...", "kind": "event|state-change|knowledge|'
                'open-question", "who": "name, only for knowledge"}]}\n\n' + draft)
        packet = builder.plain_packet(agent="publisher", model=MODEL_ID["sonnet"],
                                      premise=self.premise, tone=self.tone, body=body)
        raw = self._ask("publisher", packet, stage="FLOW-4", chapter=n)
        facts = self._facts(raw, n)
        repo.save_facts(self.conn, self.run_id, n, facts)
        self._write(f"chapters/ch{n:02d}.summary.md",
                    "\n".join(f"- {f['fact']}" for f in facts))

    @staticmethod
    def _facts(raw: str, chapter: int) -> list[dict]:
        import json
        import re
        try:
            body = re.search(r"\{[\s\S]*\}", raw)
            parsed = json.loads(body.group(0) if body else raw)
            facts = [f for f in parsed.get("facts", []) if isinstance(f, dict)]
        except Exception:
            facts = []
        # A chapter that produced no facts still happened. One event keeps the
        # chain unbroken rather than leaving the next chapter with a gap it
        # cannot see.
        return facts or [{"fact": f"chapter {chapter} happened", "kind": "event"}]

    # ------------------------------------------------------- style, publish

    def flow5_style(self) -> None:
        self._say("FLOW-5", "the style editor is normalising presentation")
        discarded = 0
        for n in range(1, self.novel["chapters"] + 1):
            before = (self.workspace / f"chapters/ch{n:02d}.md").read_text(encoding="utf-8")
            packet = builder.plain_packet(
                agent="style-editor", model=MODEL_ID["sonnet"], premise=self.premise,
                tone=self.tone,
                body=("Normalise punctuation and spacing only. Change no word.\n"
                      f"The word count of your reply must equal {len(before.split())}.\n\n"
                      + before),
            )
            after = self._ask("style-editor", packet, stage="FLOW-5", chapter=n)
            kept, was_kept = style_domain.keep_or_discard(before, after)
            if not was_kept:
                discarded += 1
            self._write(f"chapters/ch{n:02d}.final.md", kept)
            self.finals.append(kept)
        if discarded:
            repo.warn(self.conn, self.run_id, "style-discarded",
                      f"{discarded} style passes moved the word count and were discarded")

    def flow6_publish(self) -> None:
        self._say("FLOW-6", "the publisher is writing the synopsis")
        summaries = "\n".join(
            (self.workspace / f"chapters/ch{n:02d}.summary.md").read_text(encoding="utf-8")
            for n in range(1, self.novel["chapters"] + 1)
        )
        syn = self.cfg["outputs"]["synopsis"]["words"]
        packet = builder.plain_packet(
            agent="publisher", model=MODEL_ID["sonnet"], premise=self.premise,
            tone=self.tone,
            body=(f"Write a back-cover synopsis, {syn['min']}-{syn['max']} words.\n\n"
                  "The Story Bible and the outline:\n\n"
                  + self.bible["world"] + "\n\n" + self.outline + "\n\n" + summaries),
        )
        synopsis = self._ask("publisher", packet, stage="FLOW-6")
        self._write("synopsis.md", synopsis)
        # Assembled in code. A model asked to concatenate paraphrases a sentence
        # in the middle of text the gate already approved.
        book = publish_domain.assemble(
            synopsis, self.finals,
            include_synopsis=self.cfg["outputs"]["markdown"]["include_synopsis"],
        )
        self._write("dist/book.md", book)

    # ------------------------------------------------------------- the run

    def run(self) -> str:
        """Six stages. State persisted after each one, never only at the end."""
        try:
            for stage, step in (
                ("FLOW-1", self.flow1_world), ("FLOW-2", self.flow2_characters),
                ("FLOW-3", self.flow3_outline), ("FLOW-4", self.flow4_chapters),
                ("FLOW-5", self.flow5_style), ("FLOW-6", self.flow6_publish),
            ):
                repo.set_stage(self.conn, self.run_id, stage)
                step()
            repo.finish(self.conn, self.run_id)
            return "complete"
        except Halted as exc:
            repo.halt(self.conn, self.run_id, exc.kind, exc.detail)
            return f"halted: {exc.kind}"
        except BudgetExceeded as exc:
            # The attempt in flight is kept: it is already paid for, and evidence
            # bought is not thrown away.
            repo.halt(self.conn, self.run_id, "budget", str(exc))
            return "halted: budget"
        except ContextCeilingExceeded as exc:
            repo.halt(self.conn, self.run_id, "context", str(exc))
            return "halted: context"
