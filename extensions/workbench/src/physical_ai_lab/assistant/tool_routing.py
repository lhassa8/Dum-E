"""Bounded fast path for explicit familiar commands; everything else uses the model.

Match the whole utterance. Never infer action from the presence of a tool name.
Quoted, negated, hypothetical, conditional and multiple requests do not match.
"""

import re

from physical_ai_lab.assistant.tool_language import ToolIntent

TOOL = r"(?P<tool>screwdriver|wrench|spanner|hammer)"
PREFIX = r"(?:please )?(?:(?:could|can|would|will) you )?(?:please )?"
ARTICLE = r"(?:(?:the|a|my) )?"
SUFFIX = r"(?: please)?"
RACK = r"(?:its|the|my|your) (?:tool )?(?:rack|tray)|tool (?:rack|tray)"
RACK = r"(?:" + RACK + r")"
FETCH = re.compile(
    PREFIX
    + r"(?:bring|fetch|hand|pass|get)(?: me)? "
    + ARTICLE
    + TOOL
    + r"(?: to (?:the )?handoff tray)?"
    + SUFFIX
)
RETURN = re.compile(PREFIX + r"return " + ARTICLE + TOOL + r"(?: to " + RACK + r")?" + SUFFIX)
# Named groups cannot occur twice in a single expression.
PUT_BACK = re.compile(
    PREFIX
    + r"(?:put|place) "
    + ARTICLE
    + TOOL
    + r" back(?: (?:in|into|on) "
    + RACK
    + r")?"
    + SUFFIX
)
DECLINE = re.compile(
    r"(?:please )?(?:(?:don't|do not) |(?:could|can|would) you not )"
    + r"(?:bring|fetch|hand|pass|get)(?: me)? "
    + ARTICLE
    + TOOL
    + SUFFIX
)


def explicit_decline(text):
    """A complete negative request cancels any inference from old dialogue context."""
    words = " ".join(re.sub(r"[,.!?]", " ", text.lower().replace("’", "'")).split())
    if DECLINE.fullmatch(words):
        return ToolIntent("answer", None, None, "Okay. I won't fetch a tool.")
    return None


def familiar_intent(text):
    """Return a validated supported intent, or None to ask the language model."""
    words = " ".join(re.sub(r"[,.!?]", " ", text.lower()).split())
    for pattern, action, destination in [
        (FETCH, "fetch", "handoff"),
        (RETURN, "return", "rack"),
        (PUT_BACK, "return", "rack"),
    ]:
        match = pattern.fullmatch(words)
        if match:
            tool = match["tool"]
            tool = "wrench" if tool == "spanner" else tool
            return ToolIntent(action, tool, destination, "")
    if words in {
        "hello",
        "hi",
        "hello dum-e",
        "hello dum e",
        "hi dum-e",
        "hi dum e",
        "wave",
        "wave hello",
        "wave hello please",
        "please wave",
        "wave please",
    }:
        return ToolIntent("gesture", None, "wave", "Hello! Ready to lend a hand.")
    if words in {"what can you help me with", "what can you do", "tell me what you can do"}:
        return ToolIntent(
            "answer",
            None,
            None,
            "I can bring a screwdriver, wrench or hammer to the handoff tray, put it back, "
            "and wave hello. Say stop to pause, then resume to continue. We're in simulation.",
        )
    return None
