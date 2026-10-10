"""Primitive, physically graspable tools in a tray and a simulated handoff area."""

import xml.etree.ElementTree as ET

from physical_ai_lab.assistant.scene import Workbench, scene_xml

TOOLS = {"screwdriver": (0.43, -0.23), "wrench": (0.45, 0.0), "hammer": (0.43, 0.23)}
HANDOFF = {"handoff": (0.64, -0.16)}
LABELS = {"screwdriver": "Screwdriver", "wrench": "Wrench", "hammer": "Hammer"}


def tool_scene_xml():
    root = ET.fromstring(scene_xml())
    world = root.find("worldbody")
    for body in list(world.findall("body")):
        if body.get("name") in {"red", "blue", "yellow"}:
            world.remove(body)
    for geom in list(world.findall("geom")):
        if geom.get("name", "").endswith("_target"):
            world.remove(geom)
    ET.SubElement(
        world,
        "geom",
        name="tool_tray",
        type="box",
        pos="0.43 0 0.0005",
        size="0.10 0.36 0.0005",
        rgba="0.25 0.30 0.34 1",
        contype="0",
        conaffinity="0",
    )
    ET.SubElement(
        world,
        "geom",
        name="handoff_area",
        type="box",
        pos="0.64 -0.16 0.001",
        size="0.085 0.125 0.001",
        rgba="0.23 0.63 0.47 1",
        contype="0",
        conaffinity="0",
    )
    metal = "0.70 0.74 0.78 1"
    for name, (x, y) in TOOLS.items():
        body = ET.SubElement(world, "body", name=name, pos=f"{x} {y} 0.026")
        ET.SubElement(body, "freejoint", name=f"{name}_joint")

        def geom(**attrs):
            mass = attrs.pop("mass", "0.008")
            return ET.SubElement(
                body, "geom", mass=mass, friction="1.5 0.04 0.01", condim="6", **attrs
            )

        # Flat handle faces give the parallel gripper a stable physical contact.
        grip_color = {
            "screwdriver": "0.95 0.53 0.15 1",
            "wrench": metal,
            "hammer": "0.40 0.24 0.14 1",
        }[name]
        geom(type="box", size="0.022 0.028 0.022", rgba=grip_color, mass="0.045")
        if name == "screwdriver":
            geom(
                type="capsule",
                fromto="0 -0.055 0 0 0.025 0",
                size="0.020",
                rgba="0.95 0.53 0.15 1",
                mass="0.025",
            )
            geom(
                type="capsule", fromto="0 0.025 0 0 0.115 0", size="0.004", rgba=metal, mass="0.004"
            )
            geom(type="box", pos="0 0.116 0", size="0.007 0.011 0.003", rgba=metal, mass="0.002")
        elif name == "wrench":
            geom(
                type="capsule",
                fromto="0 -0.060 0 0 0.050 0",
                size="0.017",
                rgba=metal,
                mass="0.020",
            )
            geom(type="box", pos="0 0.060 0", size="0.028 0.014 0.017", rgba=metal)
            for side in [-1, 1]:
                geom(
                    type="box", pos=f"{side * 0.022} 0.085 0", size="0.010 0.020 0.017", rgba=metal
                )
        else:
            geom(type="capsule", fromto="0 -0.07 0 0 0.07 0", size="0.019", rgba="0.40 0.24 0.14 1")
            geom(type="box", pos="0 0.080 0", size="0.045 0.022 0.022", rgba=metal)
    return ET.tostring(root, encoding="unicode")


class ToolWorkbench(Workbench):
    def __init__(self, seed=42):
        super().__init__(seed, xml=tool_scene_xml(), objects=TOOLS, targets=HANDOFF)
