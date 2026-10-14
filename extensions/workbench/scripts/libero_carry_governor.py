"""Experimental OSC-delta limiter from robot proprioception; no object-state input."""

import math
import time

import numpy as np


def limit_carry_delta(delta, controller, *, budget_rad=.01, reserve_fraction=.5):
    """Heuristic stopping-range model, not a certified bound or a joint-position action.

    Native OSC has already updated its Jacobian, inertia and gravity/bias fields.
    Delta consists of three metres and three axis-angle radians for one policy step.
    Estimate joint velocity with the minimum-norm Jacobian inverse, then combine
    ideal kp300/damping2 impulse displacement with torque-limited braking distance.
    A scalar reduction preserves the native pose-delta direction. Native clipping
    remains authoritative. The model omits contact forces and changing dynamics.
    """
    started = time.perf_counter_ns()
    delta = np.asarray(delta, dtype=float)
    jacobian = np.asarray(controller.J_full, dtype=float)
    mass = np.asarray(controller.mass_matrix, dtype=float)
    bias = np.asarray(controller.torque_compensation, dtype=float)
    low, high = (np.asarray(v, dtype=float) for v in controller.actuator_limits)
    if delta.shape != (6,) or jacobian.shape != (6, 7) or mass.shape != (7, 7):
        raise ValueError("Requires native six-axis OSC deltas and a seven-joint arm")
    if not all(np.isfinite(v).all() for v in (delta, jacobian, mass, bias, low, high)):
        raise ValueError("Nonfinite robot/controller readings; no fallback")
    if budget_rad <= 0 or not 0 < reserve_fraction <= 1:
        raise ValueError("Invalid governor margin")
    period = 1 / float(controller.control_freq)
    proposal = np.linalg.pinv(jacobian, rcond=1e-4) @ (delta / period)
    momentum = mass @ proposal
    reserve = np.where(momentum >= 0, bias-low, high-bias) * reserve_fraction
    speed = float(np.max(np.abs(proposal)))
    # Peak displacement per unit initial velocity for an ideal overdamped joint.
    omega, damping = math.sqrt(300), 2
    root = math.sqrt(damping*damping-1)
    slow, fast = omega*(damping-root), omega*(damping+root)
    peak_time = math.log(fast/slow)/(fast-slow)
    response = (math.exp(-slow*peak_time)-math.exp(-fast*peak_time))/(fast-slow)
    blocked = bool(np.any((reserve <= 0) & (np.abs(momentum) > 1e-12)))
    brake_time = (float("inf") if blocked else
                  float(np.max(np.abs(momentum)/np.maximum(reserve, 1e-12))))
    quadratic, linear = .5*speed*brake_time, response*speed
    if blocked:
        alpha = 0.0
        predicted = None
    else:
        predicted = quadratic+linear
        alpha = (1.0 if predicted <= budget_rad else
                 2*budget_rad/(linear+math.sqrt(linear*linear+4*quadratic*budget_rad)))
    limited = delta*alpha
    record = {
        "requested_delta": delta.tolist(), "applied_delta": limited.tolist(),
        "alpha": alpha, "period_s": period, "joint_velocity_proposal": proposal.tolist(),
        "measured_joint_velocity": controller.joint_vel.tolist(),
        "jacobian": jacobian.tolist(), "mass_matrix": mass.tolist(), "bias": bias.tolist(),
        "torque_low": low.tolist(), "torque_high": high.tolist(),
        "budget_rad": budget_rad, "reserve_fraction": reserve_fraction,
        "ideal_joint_peak_s": response, "predicted_unscaled_range_rad": predicted,
        "predicted_scaled_range_rad": (None if blocked else
                                       quadratic*alpha*alpha+linear*alpha),
        "reserve_unavailable": blocked, "elapsed_ns": time.perf_counter_ns()-started,
    }
    return limited, record
