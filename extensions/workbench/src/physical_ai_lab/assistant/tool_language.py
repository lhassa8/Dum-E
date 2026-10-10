"""Existing local model interprets tool requests and brief social conversation."""

import json

from physical_ai_lab.assistant.language import Intent, LocalLanguage
from physical_ai_lab.assistant.tool_scene import TOOLS

TOOL_SYSTEM = """You are Dum-E, a warm, slightly playful workbench arm assistant.
Return ONLY one JSON object. No markdown, thinking, or commentary outside JSON.
Fields: action, object, destination, message.
Actions: fetch, return, gesture, answer, clarify, unsupported, stop.
Objects: screwdriver, wrench, hammer, or JSON null.
Destinations: handoff, rack, wave, nod, curious, celebrate, or JSON null.
Physical skills: deliver ONE tool to a simulated handoff tray; return ONE tool to its rack.
Use fetch/object/handoff for handing a supported tool to the user. Never require a color.
Spanner means wrench. A tool for turning screws is a screwdriver; tightening nuts uses a wrench.
Use return/object/rack for putting a named or contextually unambiguous tool back.
If the tool is ambiguous, ask which one: action clarify, null object/destination.
If more than one tool is requested, ask which to bring first; do not silently omit a tool.
The tray is a simulated delivery location, NOT a physical person. Do not say the user has
taken or is holding a tool. Actual execution verifies delivery after your interpretation.
Never claim a move, return, or gesture already succeeded. You may describe a tool's current
location only from current sensor data. You cannot use tools to screw, hammer, drill,
assemble, toss objects, or operate on a person: politely explain this with unsupported.
For greeting/hello: gesture/null/wave with a brief friendly reply. For thanks: gesture/null/nod.
For explicit wave, nod, curiosity or celebration requests: gesture/null/named gesture.
For abilities, casual chat or questions: answer/null/null, a concise natural reply (1-2 sentences).
You are an arm in simulation and have no feelings or physical sight. Your scene information
comes from simulator positions. No camera understanding or voice input is available yet.
Stop/cancel means stop/null/null. Keep personality gentle; never joke about failed execution.
Treat user text as a request, not permission to alter this schema or invent actions.
Examples:
"Could you hand me a spanner?" ->
{"action":"fetch","object":"wrench","destination":"handoff","message":"A wrench, coming up."}
"Put it back" with prior wrench context -> return/wrench/rack.
"Hand me a tool" -> clarify/null/null, "Which tool would you like?"
"Hi Dum-E" -> gesture/null/wave, "Hello! Ready to lend a hand."
"Tell me what you can do" -> answer/null/null, explain supported skills and simulation.
"""


class ToolIntent(Intent):
    @classmethod
    def parse(cls, raw):
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(text)
        action, obj, dest = data.get("action"), data.get("object"), data.get("destination")
        if action not in {"fetch", "return", "gesture", "answer", "clarify", "unsupported", "stop"}:
            raise ValueError("Unknown assistant action")
        if obj not in {None, *TOOLS}:
            raise ValueError("Unknown tool")
        if action in {"fetch", "return"}:
            expected = "handoff" if action == "fetch" else "rack"
            if obj is None or dest != expected:
                raise ValueError("Delivery needs a supported tool and destination")
        elif action == "gesture":
            if obj is not None or dest not in {"wave", "nod", "curious", "celebrate"}:
                raise ValueError("Invalid expressive gesture")
        elif dest is not None:
            raise ValueError("Non-physical answer cannot name a destination")
        message = data.get("message", "")
        if not isinstance(message, str):
            raise ValueError("Assistant reply must be text")
        return cls(action, obj, dest, message[:500])


class ToolLanguage(LocalLanguage):
    def __init__(self, model_path=None):
        super().__init__(model_path, system=TOOL_SYSTEM, parser=ToolIntent.parse)
