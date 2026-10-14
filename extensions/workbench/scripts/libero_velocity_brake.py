"""Experimental short velocity brake within native arm torque limits."""

import time

import numpy as np


def velocity_brake(controller, *, step_s=.002):
    """Choose the largest feasible common deceleration of measured joint velocity.

    Native bias and inertia are already updated by the joint controller. Under
    the local inertia model, torque = bias - rate * M * velocity gives common
    exponential deceleration. Cap rate at one physics step's inverse to avoid
    modeled sign reversal. Contacts and time-varying dynamics are not a guarantee.
    This does not change a goal, gripper command, actuator bound or object state.
    """
    started = time.perf_counter_ns()
    mass = np.asarray(controller.mass_matrix, dtype=float)
    bias = np.asarray(controller.torque_compensation, dtype=float)
    velocity = np.asarray(controller.joint_vel, dtype=float)
    low, high = (np.asarray(v, dtype=float) for v in controller.actuator_limits)
    if mass.shape != (7, 7) or any(v.shape != (7,) for v in (bias, velocity, low, high)):
        raise ValueError("Requires native seven-joint inertia, velocity and torque readings")
    if not all(np.isfinite(v).all() for v in (mass, bias, velocity, low, high)):
        raise ValueError("Nonfinite robot/controller readings; no fallback")
    if step_s <= 0 or np.any(bias < low) or np.any(bias > high):
        raise ValueError("Bias is infeasible within native limits; no fallback")
    momentum = mass @ velocity
    reserve = np.where(momentum >= 0, bias-low, high-bias)
    moving = np.abs(momentum) > 1e-12
    feasible = float(np.min(reserve[moving]/np.abs(momentum[moving]))) if moving.any() else (
        1/step_s)
    rate = min(feasible, 1/step_s)
    torque = bias-rate*momentum
    assert np.all(torque >= low-1e-9) and np.all(torque <= high+1e-9)
    torque = np.clip(torque, low, high)  # Numerical roundoff only.
    return torque, {
        "mass_matrix": mass.tolist(), "bias": bias.tolist(),
        "joint_velocity": velocity.tolist(), "momentum": momentum.tolist(),
        "torque_low": low.tolist(), "torque_high": high.tolist(),
        "feasible_rate_s_inv": feasible, "rate_s_inv": rate, "step_s": step_s,
        "torque": torque.tolist(), "elapsed_ns": time.perf_counter_ns()-started,
    }
