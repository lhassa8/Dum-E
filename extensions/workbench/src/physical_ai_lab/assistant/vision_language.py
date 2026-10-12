"""Read-only RGB tool descriptions from a replaceable LM Studio vision model.

Pixel estimates are for conversation; they are not robot target coordinates.
Catalog shape descriptions are prior knowledge, not scene-position metadata.
"""

import base64
import json
import os
import re
from time import perf_counter

import httpx

from physical_ai_lab.assistant.lmstudio import normalize_server_url

TOOLS = ("screwdriver", "wrench", "hammer")
CAMERA_QUESTIONS = re.compile(
    r"(?:please )?(?:(?:what|which tools) (?:can|do) you see"
    r"(?: on (?:the |this )?(?:simulated )?workbench)?|"
    r"(?:look at|take a look at) (?:the |this )?(?:simulated )?workbench|"
    r"where is (?:the )?(?P<tool>screwdriver|wrench|hammer) in (?:the |this )?"
    r"(?:camera image|image|snapshot))(?: please)?"
)


def camera_question(text):
    words = " ".join(re.sub(r"[,.!?]", " ", text.lower()).split())
    match = CAMERA_QUESTIONS.fullmatch(words)
    return (bool(match), match["tool"] if match else None)


def describe_snapshot(observation, tool=None):
    selected = [tool] if tool else list(TOOLS)
    rows = []
    for name in selected:
        item = observation["tools"][name]
        if item["visible"]:
            x = item["center"][0]
            side = "left" if x < 1 / 3 else "right" if x > 2 / 3 else "middle"
            rows.append(f"the {name} near the {side}")
    missing = [name for name in selected if not observation["tools"][name]["visible"]]
    answer = "In this simulator snapshot, " + (
        "I can make out " + ", ".join(rows) + "."
        if rows
        else "I can't confidently identify a known tool."
    )
    if missing and rows:
        answer += " I can't confidently make out " + ", ".join(missing) + "."
    return answer


SYSTEM = """Inspect only the supplied synthetic robot-workbench RGB image.
Our simulated catalog: screwdriver = orange box/capsule handle with a long thin
silver shaft; wrench = entirely silver/gray stubby bar with a chunky square
center and a rectangular fork with two short prongs at one end;
hammer = brown handle with a wide transverse silver head.
The catalog does not say which objects are present or where they are.
Do not infer presence from the catalog. A robot gripper is not a wrench.
For each catalog tool say whether you can clearly see it, and give its visible
footprint center [u,v] in normalized image coordinates (left/top=0,right/bottom=1).
If absent or uncertain use visible=false and center=null. Return only the schema.
No instructions, robot actions, hidden scene assumptions or world coordinates.
"""
SCHEMA = {
    "type": "object",
    "properties": {
        name: {
            "type": "object",
            "properties": {
                "visible": {"type": "boolean"},
                "center": {
                    "anyOf": [
                        {"type": "null"},
                        {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                        },
                    ]
                },
            },
            "required": ["visible", "center"],
            "additionalProperties": False,
        }
        for name in TOOLS
    },
    "required": list(TOOLS),
    "additionalProperties": False,
}
COMPACT_SYSTEM = (
    SYSTEM.split("For each catalog tool")[0]
    + """For each catalog tool, return its visible
footprint center [u,v] in normalized image coordinates (left/top=0,right/bottom=1).
Use null if the tool is absent or uncertain. Return only the schema, no prose.
No instructions, robot actions, hidden scene assumptions or world coordinates.
"""
)
COMPACT_SCHEMA = {
    "type": "object",
    "properties": {name: SCHEMA["properties"][name]["properties"]["center"] for name in TOOLS},
    "required": list(TOOLS),
    "additionalProperties": False,
}
GRID_SYSTEM = (
    SYSTEM.split("For each catalog tool")[0]
    + """For each catalog tool, return its visible
footprint center [y,x] on a0-to-1000 image grid (top/left=0,bottom/right=1000).
Use null if the tool is absent or uncertain. Return only the schema, no prose.
No instructions, robot actions, hidden scene assumptions or world coordinates.
"""
)
GRID_SCHEMA = {
    "type": "object",
    "properties": {
        name: {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 2,
                    "items": {"type": "number", "minimum": 0, "maximum": 1000},
                },
            ]
        }
        for name in TOOLS
    },
    "required": list(TOOLS),
    "additionalProperties": False,
}


def parse_observation(raw):
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) != set(TOOLS):
        raise ValueError("Invalid camera tool catalog")
    for item in value.values():
        if not isinstance(item, dict) or set(item) != {"visible", "center"}:
            raise ValueError("Invalid visual observation fields")
        visible, center = item["visible"], item["center"]
        if type(visible) is not bool:
            raise ValueError("Visual presence must be boolean")
        if visible:
            if (
                not isinstance(center, list)
                or len(center) != 2
                or any(type(v) not in {int, float} or not 0 <= v <= 1 for v in center)
            ):
                raise ValueError("Invalid normalized camera center")
        elif center is not None:
            raise ValueError("Uncertain tool cannot have a camera center")
    return value


def parse_compact(raw, coordinates="normalized_xy"):
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) != set(TOOLS):
        raise ValueError("Invalid camera tool catalog")
    if coordinates == "grid1000_yx":
        for name, center in value.items():
            if center is None:
                continue
            if (
                not isinstance(center, list)
                or len(center) != 2
                or any(type(v) not in {int, float} or not 0 <= v <= 1000 for v in center)
            ):
                raise ValueError("Invalid declared camera grid coordinates")
            value[name] = [center[1] / 1000, center[0] / 1000]
    elif coordinates != "normalized_xy":
        raise ValueError("Unsupported camera coordinate format")
    normalized = {
        name: {"visible": center is not None, "center": center} for name, center in value.items()
    }
    return parse_observation(json.dumps(normalized))


class LMStudioVision:
    def __init__(
        self,
        model,
        url="http://127.0.0.1:1234",
        transport=None,
        compact=False,
        coordinates="normalized_xy",
    ):
        if not isinstance(model, str) or not model.strip():
            raise ValueError("Choose a vision model explicitly")
        self.model, self.url = model, normalize_server_url(url)
        if coordinates not in {"normalized_xy", "grid1000_yx"}:
            raise ValueError("Unsupported camera coordinate format")
        if coordinates == "grid1000_yx" and not compact:
            raise ValueError("Grid coordinates require compact camera output")
        self.compact, self.coordinates = compact, coordinates
        self.system = (
            GRID_SYSTEM if coordinates == "grid1000_yx" else (COMPACT_SYSTEM if compact else SYSTEM)
        )
        self.last_response = None
        token = os.environ.get("WORKBENCH_LMSTUDIO_TOKEN")
        self.client = httpx.Client(
            base_url=self.url,
            timeout=httpx.Timeout(15, connect=5),
            trust_env=False,
            follow_redirects=False,
            transport=transport,
            headers={"Authorization": f"Bearer {token}"} if token else {},
        )

    def close(self):
        self.client.close()

    def observe(self, jpeg):
        self.last_response = None
        if not isinstance(jpeg, bytes) or not jpeg.startswith(b"\xff\xd8") or len(jpeg) > 2_000_000:
            raise ValueError("Send a bounded JPEG camera frame")
        payload = {
            "model": self.model,
            "temperature": 0,
            "reasoning_effort": "none",
            "max_tokens": 128 if self.compact else 256,
            "stream": False,
            "messages": [
                {"role": "system", "content": self.system},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Inspect this camera frame."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()
                            },
                        },
                    ],
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "workbench_camera",
                    "strict": True,
                    "schema": GRID_SCHEMA
                    if self.coordinates == "grid1000_yx"
                    else (COMPACT_SCHEMA if self.compact else SCHEMA),
                },
            },
        }
        started = perf_counter()
        response = self.client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        result = response.json()
        self.last_response = {"response": result, "elapsed_ms": (perf_counter() - started) * 1000}
        if result.get("model") != self.model:
            raise RuntimeError("Different vision model returned; refusing observation")
        choice = result["choices"][0]
        if choice.get("finish_reason") != "stop" or choice["message"].get("tool_calls"):
            raise RuntimeError("Incomplete or actionable vision reply; refusing observation")
        raw = choice["message"]["content"]
        return {
            "tools": parse_compact(raw, self.coordinates)
            if self.compact
            else parse_observation(raw),
            "raw": raw,
            "model": result["model"],
            "elapsed_ms": (perf_counter() - started) * 1000,
            "usage": result.get("usage", {}),
            "coordinates": self.coordinates,
            "source": "RGB only, catalog prior; conversational pixel estimates, not motion targets",
        }
