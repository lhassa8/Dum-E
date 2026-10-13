"""Bounded fast path for explicit familiar commands; everything else uses the model.

Match the whole utterance. Never infer action from the presence of a tool name.
Quoted, negated, hypothetical, conditional and multiple requests do not match.
"""

import re

from physical_ai_lab.assistant.tool_language import ToolIntent

TOOL = r"(?P<tool>screwdriver|wrench|spanner|hammer)"
PREFIX = r"(?:(?:actually|instead) )?(?:please )?(?:(?:could|can|would|will) you )?(?:please )?"
ARTICLE = r"(?:(?:the|a|my) )?"
SUFFIX = r"(?: please)?(?: instead)?"
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
    r"(?:actually )?(?:please )?(?:(?:don't|do not) |(?:could|can|would) you not )"
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
            "In simulation, I can bring and return tools, pause and resume tasks, "
            "wave hello, and chat while working.",
        )
    return None


def known_intent(text, recent_tool=None):
    """Resolve familiar and contextual commands without erasing quotations/negation."""
    words = " ".join(re.sub(r"[,.!?]", " ", text.lower()).split())
    if words.replace("’", "'") in {
        "don't stop",
        "do not stop",
        "please don't stop",
        "please do not stop",
        "don't stop yet",
        "do not stop yet",
        "don't stop moving",
        "do not stop moving",
    }:
        return ToolIntent("answer", None, None, "Understood. I won't cancel the task."), "continue"
    if words in {
        "resume",
        "resume please",
        "please resume",
        "continue",
        "continue please",
        "carry on",
        "resume the task",
        "continue the task",
        "keep going",
        "proceed",
        "proceed please",
        "please proceed",
        "go ahead",
    }:
        return ToolIntent("resume", None, None, ""), "context"
    if words in {
        "put it back",
        "put it back please",
        "please put it back",
        "put that back",
        "put that tool back in its rack please",
        "return it",
        "return the tool",
    }:
        intent = (
            ToolIntent("return", recent_tool, "rack", "")
            if recent_tool
            else ToolIntent("clarify", None, None, "Which tool should I put back?")
        )
        return intent, "context"
    decline = explicit_decline(text)
    return (decline, "decline") if decline else (familiar_intent(text), "familiar")


def is_stop_request(text):
    words = " ".join(re.sub(r"[^a-z\s]", " ", text.lower()).split())
    return bool(
        re.fullmatch(
            r"(?:(?:please|dum e|dume|dummy|can you|could you) )?"
            r"(?:stop|halt|cancel)(?: (?:moving|the arm|everything))?(?: (?:please|now))?",
            words,
        )
    )


def declined_tool(text):
    words = " ".join(re.sub(r"[,.!?]", " ", text.lower().replace("’", "'")).split())
    match = DECLINE.fullmatch(words)
    return ("wrench" if match["tool"] == "spanner" else match["tool"]) if match else None


def status_intent(text, snapshot):
    """Answer operational questions from current state, with no motion side effects."""
    words = " ".join(re.sub(r"[,.!?]", " ", text.lower()).split())
    if words in {
        "what are you doing",
        "what are you working on",
        "how is it going",
        "how's it going",
        "are you busy",
        "what's happening",
        "what is happening",
    }:
        task = snapshot.get("task") or {}
        tool = task.get("object")
        phase = snapshot["phase"]
        message = (
            f"I'm working on the {tool}: {phase.lower()}. Placement isn't confirmed yet."
            if snapshot["busy"] and tool
            else f"{phase}. I'm ready for your next request."
            if not snapshot["busy"]
            else f"I'm {phase.lower()}."
        )
        return ToolIntent("answer", None, None, message)
    match = re.fullmatch(r"where is (?:the |my )?(screwdriver|wrench|hammer)", words)
    if match:
        tool = match[1]
        location = snapshot.get("inventory", {}).get(tool)
        message = (
            f"The {tool} is {location}."
            if location
            else f"I don't have a reliable location for the {tool} yet."
        )
        return ToolIntent("answer", None, None, message)
    return None
