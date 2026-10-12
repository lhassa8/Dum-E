"""Declared primitive tool catalog; never simulator object-state queries."""


def parts(name):
    boxes = [([0, 0, 0], [0.022, 0.028, 0.022])]
    capsules = []
    if name == "screwdriver":
        capsules = [([0, -0.015, 0], 0.040, 0.020), ([0, 0.070, 0], 0.045, 0.004)]
        boxes.append(([0, 0.116, 0], [0.007, 0.011, 0.003]))
    elif name == "wrench":
        capsules = [([0, -0.005, 0], 0.055, 0.017)]
        boxes += [([0, 0.060, 0], [0.028, 0.014, 0.017])]
        boxes += [([side * 0.022, 0.085, 0], [0.010, 0.020, 0.017]) for side in [-1, 1]]
    elif name == "hammer":
        capsules = [([0, 0, 0], 0.070, 0.019)]
        boxes.append(([0, 0.080, 0], [0.045, 0.022, 0.022]))
    else:
        raise ValueError("Unknown tool catalog")
    return boxes, capsules
