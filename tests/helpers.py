"""Shared helpers for the Aqara H2 blueprint tests."""

import itertools
import pathlib

import homeassistant.util.dt as dt_util

from ha_blueprint_test_harness import sets_state

BLUEPRINT = pathlib.Path(__file__).parent.parent / "blueprints" / "automation" / "aqara_h2_switch.yaml"
SWITCH = "event.hall_h2_switch_action"
LIGHT = "light.hall"
SCENES = ["scene.hall_bright", "scene.hall_evening", "scene.hall_night"]
POSITIONS = ["left", "left_down", "right", "right_down"]
GESTURES = ["single", "double", "hold", "release"]
ALL_EVENTS = [f"{g}_{p}" for p in POSITIONS for g in GESTURES]

# Every press gets a new timestamp state, like the real event entity does.
_counter = itertools.count()


# The effect receives Home Assistant's raw ServiceCall, so the target is read from call.data.
# A mocked scene.turn_on that behaves like a real scene: its state becomes the time of activation.
def scene_activated(hass, call):
    targets = call.data["entity_id"]
    for entity_id in [targets] if isinstance(targets, str) else targets:
        hass.states.async_set(entity_id, dt_util.utcnow().isoformat())


# Loads the blueprint. Services are recorded; lights and scenes change state like real ones.
async def start(env, scene_states=None, **inputs):
    states = {SWITCH: "unknown", LIGHT: "on", **{s: "unknown" for s in SCENES}, **(scene_states or {})}
    await env.start(
        BLUEPRINT,
        {"switch_entity": SWITCH, **inputs},
        states=states,
        services=["light.turn_on", "light.toggle", "scene.turn_on"],
        effects={"light.turn_on": sets_state("on"), "scene.turn_on": scene_activated},
    )


# Simulates one press of the switch: a new timestamp state with the attribute `event_type`.
async def press(env, event_type):
    stamp = f"2026-01-01T10:00:{next(_counter):02d}.000+00:00"
    await env.set_state(SWITCH, stamp, {"event_type": event_type})


# Loads the blueprint with a light mock whose first turn_on call is "the finger lifts during the call":
# the release event arrives while the light service is still running (the race seen with a 0.44 s hold).
async def start_with_release_during_call(env, release, **inputs):
    fired = []

    async def effect(hass, call):
        if not fired:
            fired.append(True)
            stamp = f"2026-01-01T11:00:{next(_counter):02d}.000+00:00"
            hass.states.async_set(SWITCH, stamp, {"event_type": release})

    states = {SWITCH: "unknown", LIGHT: "on"}
    await env.start(BLUEPRINT, {"switch_entity": SWITCH, **inputs}, states=states,
                    services=["light.turn_on", "light.toggle", "scene.turn_on"], effects={"light.turn_on": effect})


# The names of all service calls so far.
def names(env):
    return [call.name for call in env.calls]


# The brightness steps of all light.turn_on calls so far.
def steps(env):
    return [call.data["brightness_step_pct"] for call in env.calls_to("light.turn_on")]


# The scenes activated so far, in order.
def activated(env):
    return [next(iter(call.entity_ids)) for call in env.calls_to("scene.turn_on")]
