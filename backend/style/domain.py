"""The style pass, checked with arithmetic rather than trust."""

from __future__ import annotations


def keep_or_discard(before: str, after: str) -> tuple[str, bool]:
    """Returns the text to publish and whether the pass was kept.

    The style editor may normalise presentation and may not change a word. The
    check is a word count, which is arithmetic and not judgement - and it has
    fired on a pass that changed no word at all, when closing the space in
    `+/- 0.30` merged two tokens into one. That is the rule working: the
    published text must be the text the gate approved, and `wc` cannot tell
    presentation from editing.
    """
    if len(before.split()) == len(after.split()):
        return after, True
    return before, False
