"""Launching Claude Code and reading what it says.

**Claude Code is the orchestrator.** It executes
`.claude/skills/novaforge/SKILL.md` and dispatches the nine agents as subagents
with their own `tools:` lists. This module launches it, reads its event stream,
and hands each event to whoever is watching.

There is no Anthropic SDK here and no `ANTHROPIC_API_KEY` anywhere in the
project. The only access to a model is the user's Claude Code session, on this
machine.

**What that buys back.** The chapter writer's isolation returns to being
structural: it holds `tools: Glob`, which returns paths and cannot return
contents, so a previous chapter's prose is *unreachable* rather than merely not
passed. That is the strongest guarantee this project has ever had and it was
about to be traded for a type and a test.

**What it costs.** Python no longer assembles the prompts, so it cannot reserve
tokens before a call. The ceiling becomes a procedure in SKILL.md plus a measured
stop here — see `watch.py`. Neither is a guarantee taken in advance, and
`verification.md` says so.
"""

from __future__ import annotations

import json
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

# Every rule in this list came from a mistake already made. They are not
# preferences.
ALLOWED_TOOLS = [
    "Read", "Write", "Edit", "Glob", "Grep",
    # The subagent tool is `Agent`. `Task` is the older spelling, and allowing
    # only the wrong one produces a run that quietly dispatches nothing.
    "Agent", "Task",
    "Bash(wc *)", "Bash(mkdir *)", "Bash(cat *)", "Bash(ls *)",
    "Bash(node *)", "Bash(date *)", "Bash(diff *)",
    # Added for retrieval: the orchestrator runs `python -m novaforge.search`
    # itself and pastes the fragments into the continuity critic's prompt, so
    # the critic keeps `tools: Glob` and never gains a way to read.
    "Bash(python *)",
]


class ClaudeNotAvailable(RuntimeError):
    """`claude` is not on PATH, or has no session on this machine."""


def build_prompt(premise: str, profile: str, tone: str = "") -> str:
    """What goes in on stdin. Nothing else.

    `premise:`, `profile:`, optionally `tone:`. The procedure lives in
    `SKILL.md`; restating it here would be a second source of truth for the one
    thing that must have exactly one.
    """
    lines = [
        "Run the novaforge skill.",
        "",
        f"premise: {premise.strip()}",
        f"profile: {profile}",
    ]
    if tone.strip():
        lines.append(f"tone: {tone.strip()}")
    lines += [
        "",
        "Follow .claude/skills/novaforge/SKILL.md exactly.",
        "Do not ask me anything: proceed with the plan and report at the end.",
    ]
    return "\n".join(lines) + "\n"


@dataclass
class RunProcess:
    """One `claude -p` subprocess, and its stream.

    The prompt goes on **stdin, never in argv**. Passing a task as an argument
    with `shell=True` on Windows was command injection and shipped for about an
    hour; the fix is not to quote more carefully, it is to stop putting model
    input on a command line.
    """

    command: list[str]
    prompt: str
    cwd: Path
    #: Lines that would not parse, kept verbatim. A stream that quietly loses
    #: lines is indistinguishable from one that never had them (SPEC-007 AC-2).
    skipped: list[str] = field(default_factory=list)
    _process: subprocess.Popen | None = field(default=None, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @classmethod
    def for_run(cls, *, premise: str, profile: str, tone: str, cwd: Path,
                executable: str = "claude") -> "RunProcess":
        command = [
            executable, "-p",
            # stream-json REQUIRES --verbose. Without it the process exits 1 and
            # no events appear at all.
            "--output-format", "stream-json", "--verbose",
            "--permission-mode", "acceptEdits",
            # No `--restricted`: it breaks `--agent`, and Claude Code falls back
            # to its built-in agents. Each agent's own `tools:` line is the
            # boundary, and it is a better one.
            "--allowedTools", *ALLOWED_TOOLS,
        ]
        return cls(command=command, prompt=build_prompt(premise, profile, tone), cwd=cwd)

    def start(self) -> None:
        try:
            self._process = subprocess.Popen(
                self.command,
                cwd=str(self.cwd),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                # No shell, on any platform. The argument list is explicit.
                shell=False,
            )
        except FileNotFoundError as exc:
            raise ClaudeNotAvailable(
                f"{self.command[0]!r} is not on PATH. Claude Code is the "
                f"orchestrator; there is no API fallback."
            ) from exc

        assert self._process.stdin is not None
        # Written and CLOSED. Left open, Claude Code waits three seconds and
        # prints a warning into the output being parsed.
        self._process.stdin.write(self.prompt)
        self._process.stdin.close()

    def events(self) -> Iterator[dict]:
        """One parsed event per line, as they arrive.

        A line that will not parse is skipped rather than fatal: the stream
        belongs to someone else and may grow shapes this reader has never seen.
        """
        if self._process is None or self._process.stdout is None:
            raise RuntimeError("start() first")
        for line in self._process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                self.skipped.append(line[:500])
                continue

    def stop(self) -> None:
        """End the process. Used by the budget and context watchers."""
        with self._lock:
            if self._process and self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self._process.kill()

    @property
    def returncode(self) -> int | None:
        return self._process.poll() if self._process else None

    def stderr_text(self) -> str:
        if self._process and self._process.stderr:
            return self._process.stderr.read()
        return ""


@dataclass
class ReplayProcess:
    """A fake `claude` that replays a recorded stream.

    This is the mock. It exists because the runner, the parser, the persistence,
    the SSE and both watchers can all be tested exhaustively at $0 against a real
    recording — while **the procedure in SKILL.md cannot be tested for free at
    all**, and pretending otherwise would be the more comfortable lie.

    So: everything Python does is covered by tests. What Claude Code does is
    covered by real runs and measured with the LOOP-003 instruments. That split
    is stated in `verification.md` rather than blurred.
    """

    fixture: Path
    prompt: str = ""
    stopped: bool = False
    skipped: list[str] = field(default_factory=list)
    _stop_after: int | None = None

    def start(self) -> None:
        return None

    def events(self) -> Iterator[dict]:
        emitted = 0
        for line in self.fixture.read_text(encoding="utf-8").splitlines():
            if self.stopped:
                return
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                self.skipped.append(line[:500])
                continue
            yield event
            emitted += 1
            if self._stop_after is not None and emitted >= self._stop_after:
                return

    def stop(self) -> None:
        self.stopped = True

    @property
    def returncode(self) -> int | None:
        return 0

    def stderr_text(self) -> str:
        return ""


def available(executable: str = "claude") -> bool:
    """Whether this machine can orchestrate at all."""
    import shutil

    return shutil.which(executable) is not None
