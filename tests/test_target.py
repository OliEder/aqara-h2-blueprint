"""Version 1.1.0: the switchable dimming target (feature A) and the optional fade (feature B).

The helper is the real `input_select` component, set up before the blueprint is loaded. The light and
scene services are recorders, so a "blink" is only checked as a service call with the right target and data.
Timing note: whole seconds, and only moments at least 0.5 s away from a boundary (timers can fire early).
A press of the switch never advances the clock, so "t=0" below is the moment of the double press.
"""

import pytest
from homeassistant.setup import async_setup_component

from helpers import LIGHT, SWITCH, names, press, start, start_with_release_during_call, steps
from helpers import BLUEPRINT  # noqa: F401  (kept for tests that load the blueprint by hand)

HELPER = "input_select.dim_target"
OPTIONS = ["spots", "strip", "lamp"]
SPOTS = {"entity_id": ["light.hall_spots"]}
STRIP = {"area_id": "hall_strip"}
LAMP = {"entity_id": ["light.hall_lamp_a", "light.hall_lamp_b"]}
CYCLE = {"dim_target_helper": HELPER, "dim_switch_positions": ["right_down"], "dim_target_1": SPOTS,
         "dim_target_2": STRIP, "dim_target_3": LAMP, "dim_light": "", "dim_up_positions": ["left_down"],
         "dim_down_positions": ["left"], "dim_interval": 2}


# Creates the real input_select helper (first option selected) and loads the blueprint with the given inputs.
async def start_target(env, options=OPTIONS, initial=None, **inputs):
    ok = await async_setup_component(env.hass, "input_select",
                                     {"input_select": {"dim_target": {"options": options, "initial": initial or options[0]}}})
    assert ok
    await start(env, **inputs)


# The current option of the helper.
def option(env):
    return env.hass.states.get(HELPER).state


# Sets the helper like a user or another automation would (a real service call).
async def select(env, value):
    await env.hass.services.async_call("input_select", "select_option", {"entity_id": HELPER, "option": value}, blocking=True)


# All blink calls so far as (target, data) pairs, in order. A target is the call's data without the flash key.
def blinks(env):
    return [{k: v for k, v in c.data.items() if k != "flash"} for c in env.calls_to("light.turn_on") if c.data.get("flash") == "short"]


# All dimming steps' full data, in order.
def step_data(env):
    return [c.data for c in env.calls_to("light.turn_on") if "brightness_step_pct" in c.data]


# --- feature off equals 1.0.0 -------------------------------------------------------------------------------------

async def test_feature_off_the_dimming_data_is_exactly_the_brightness_step(blueprint_env):
    # With every new input at its default the step data is as in 1.0.0: the step and the light, nothing else.
    await start(blueprint_env, dim_light=LIGHT, dim_up_positions=["left_down"])
    await press(blueprint_env, "hold_left_down")
    assert step_data(blueprint_env) == [{"brightness_step_pct": 10, "entity_id": [LIGHT]}]
    await press(blueprint_env, "release_left_down")


async def test_feature_off_a_double_press_changes_nothing(blueprint_env):
    # No helper, no positions: a double press on any button does nothing for this feature.
    await start(blueprint_env, dim_light=LIGHT, dim_target_2=STRIP)
    await press(blueprint_env, "double_right_down")
    assert blueprint_env.calls == []


async def test_a_helper_without_switch_positions_never_switches(blueprint_env):
    await start_target(blueprint_env, **{**CYCLE, "dim_switch_positions": []})
    await press(blueprint_env, "double_right_down")
    assert option(blueprint_env) == "spots" and blueprint_env.calls == []


# --- feature B: fade ---------------------------------------------------------------------------------------------

async def test_the_fade_adds_a_transition_as_long_as_the_interval(blueprint_env):
    await start(blueprint_env, dim_light=LIGHT, dim_up_positions=["left_down"], dim_fade=True, dim_interval=2)
    await press(blueprint_env, "hold_left_down")
    assert step_data(blueprint_env) == [{"brightness_step_pct": 10, "transition": 2, "entity_id": [LIGHT]}]
    await press(blueprint_env, "release_left_down")


async def test_the_fade_off_sends_no_transition(blueprint_env):
    await start(blueprint_env, dim_light=LIGHT, dim_up_positions=["left_down"], dim_fade=False, dim_interval=2)
    await press(blueprint_env, "hold_left_down")
    assert "transition" not in blueprint_env.calls[0].data
    await press(blueprint_env, "release_left_down")


async def test_the_fade_works_with_a_negative_step_and_a_switched_target(blueprint_env):
    await start_target(blueprint_env, **CYCLE, dim_fade=True, dim_step=20)
    await press(blueprint_env, "double_right_down")
    await press(blueprint_env, "hold_left")
    assert step_data(blueprint_env) == [{"brightness_step_pct": -20, "transition": 2, "area_id": "hall_strip"}]
    await press(blueprint_env, "release_left")


# --- switching ---------------------------------------------------------------------------------------------------

async def test_a_double_press_cycles_1_2_3_1(blueprint_env):
    await start_target(blueprint_env, **CYCLE)
    seen = []
    for _ in range(4):
        await press(blueprint_env, "double_right_down")
        seen.append(option(blueprint_env))
    assert seen == ["strip", "lamp", "spots", "strip"]


async def test_an_empty_slot_is_skipped(blueprint_env):
    # Slot 2 is empty: the cycle goes 1, 3, 1.
    await start_target(blueprint_env, **{**CYCLE, "dim_target_2": {}})
    seen = []
    for _ in range(3):
        await press(blueprint_env, "double_right_down")
        seen.append(option(blueprint_env))
    assert seen == ["lamp", "spots", "lamp"]


async def test_the_legacy_light_is_slot_1_when_target_1_is_empty(blueprint_env):
    # A 1.0.0 setup: only "Light to dim" is set; with a second slot the old light is the default target.
    await start_target(blueprint_env, **{**CYCLE, "dim_target_1": {}, "dim_light": LIGHT})
    await press(blueprint_env, "hold_left_down")
    assert step_data(blueprint_env)[0]["entity_id"] == [LIGHT]
    await press(blueprint_env, "release_left_down")
    await press(blueprint_env, "double_right_down")
    assert option(blueprint_env) == "strip"
    await select(blueprint_env, "spots")
    await press(blueprint_env, "hold_left_down")
    assert step_data(blueprint_env)[-1]["entity_id"] == [LIGHT]
    await press(blueprint_env, "release_left_down")


async def test_target_1_wins_over_the_legacy_light(blueprint_env):
    await start_target(blueprint_env, **{**CYCLE, "dim_light": LIGHT})
    await press(blueprint_env, "hold_left_down")
    assert step_data(blueprint_env)[0]["entity_id"] == ["light.hall_spots"]
    await press(blueprint_env, "release_left_down")


async def test_fewer_than_two_slots_does_nothing(blueprint_env):
    await start_target(blueprint_env, **{**CYCLE, "dim_target_2": {}, "dim_target_3": {}})
    await press(blueprint_env, "double_right_down")
    assert option(blueprint_env) == "spots" and blueprint_env.calls == []


async def test_without_a_default_slot_nothing_switches(blueprint_env):
    # Slots 2 and 3 are filled but slot 1 (and the legacy light) are empty: there is no default to come back to.
    await start_target(blueprint_env, **{**CYCLE, "dim_target_1": {}})
    await press(blueprint_env, "double_right_down")
    assert option(blueprint_env) == "spots" and blueprint_env.calls == []


async def test_a_helper_with_too_few_options_stops_at_the_last_option(blueprint_env):
    # Three slots but only two options: from slot 2 there is no option for slot 3, so nothing switches.
    await start_target(blueprint_env, options=["spots", "strip"], **CYCLE)
    await press(blueprint_env, "double_right_down")
    assert option(blueprint_env) == "strip"
    await press(blueprint_env, "double_right_down")
    assert option(blueprint_env) == "strip"


async def test_only_a_double_press_on_a_chosen_button_switches(blueprint_env):
    await start_target(blueprint_env, **CYCLE)
    for event in ("single_right_down", "hold_right_down", "double_left_down", "double_right", "release_right_down"):
        await press(blueprint_env, event)
    assert option(blueprint_env) == "spots"
    assert not blinks(blueprint_env)
    await press(blueprint_env, "release_right_down")


async def test_the_own_double_action_still_runs(blueprint_env):
    own = [{"action": "light.toggle", "target": {"entity_id": LIGHT}}]
    await start_target(blueprint_env, **CYCLE, double_right_down=own)
    await press(blueprint_env, "double_right_down")
    assert "light.toggle" in names(blueprint_env) and option(blueprint_env) == "strip"


async def test_the_scene_cycle_and_the_target_switch_can_share_a_button(blueprint_env):
    await start_target(blueprint_env, **CYCLE, scenes=["scene.hall_bright", "scene.hall_night"], scene_positions=["right_down"])
    await press(blueprint_env, "double_right_down")
    assert option(blueprint_env) == "strip" and "scene.turn_on" in names(blueprint_env)


# --- the helper's state ------------------------------------------------------------------------------------------

async def test_a_helper_state_that_is_not_an_option_means_slot_1(blueprint_env):
    await start_target(blueprint_env, **CYCLE)
    await blueprint_env.set_state(HELPER, "garbage", {"options": OPTIONS})
    await press(blueprint_env, "hold_left_down")
    assert step_data(blueprint_env)[0]["entity_id"] == ["light.hall_spots"]
    await press(blueprint_env, "release_left_down")


async def test_a_fourth_option_means_slot_1(blueprint_env):
    await start_target(blueprint_env, options=OPTIONS + ["extra"], initial="extra", **CYCLE)
    await press(blueprint_env, "hold_left_down")
    assert step_data(blueprint_env)[0]["entity_id"] == ["light.hall_spots"]
    await press(blueprint_env, "release_left_down")


async def test_an_unavailable_helper_does_not_break_dimming(blueprint_env):
    # The helper is gone: dimming falls back to slot 1 (no state, no options) and nothing is logged as an error.
    await start_target(blueprint_env, **CYCLE)
    await blueprint_env.set_state(HELPER, "unavailable")
    await press(blueprint_env, "hold_left_down")
    assert step_data(blueprint_env)[0]["entity_id"] == ["light.hall_spots"]
    await press(blueprint_env, "release_left_down")


# --- a hold dims the CURRENT target -----------------------------------------------------------------------------

@pytest.mark.parametrize("chosen, expected", [("spots", {"entity_id": ["light.hall_spots"]}),
                                              ("strip", {"area_id": "hall_strip"}),
                                              ("lamp", {"entity_id": ["light.hall_lamp_a", "light.hall_lamp_b"]})])
async def test_a_hold_dims_the_target_of_the_current_slot(blueprint_env, chosen, expected):
    await start_target(blueprint_env, **CYCLE)
    await select(blueprint_env, chosen)
    await press(blueprint_env, "hold_left_down")
    assert step_data(blueprint_env) == [{"brightness_step_pct": 10, **expected}]
    await press(blueprint_env, "release_left_down")


@pytest.mark.parametrize("target, key", [({"device_id": "device_hall_strip"}, "device_id"),
                                         ({"label_id": "ceiling"}, "label_id"),
                                         ({"area_id": ["hall", "kitchen"]}, "area_id")])
async def test_device_label_and_area_targets_are_passed_on(blueprint_env, target, key):
    await start_target(blueprint_env, **{**CYCLE, "dim_target_2": target})
    await select(blueprint_env, "strip")
    await press(blueprint_env, "hold_left_down")
    assert step_data(blueprint_env)[0][key] == target[key]
    await press(blueprint_env, "release_left_down")


async def test_the_loop_keeps_its_target_when_the_helper_changes_during_the_hold(blueprint_env):
    # The target is read once at the start of the hold. A double press switches the helper while the hold runs.
    await start_target(blueprint_env, **CYCLE)
    await press(blueprint_env, "hold_left_down")
    await press(blueprint_env, "double_right_down")
    assert option(blueprint_env) == "strip"
    await blueprint_env.advance(2)
    dims = step_data(blueprint_env)
    assert [d["entity_id"] for d in dims] == [["light.hall_spots"]] * 2
    await press(blueprint_env, "release_left_down")
    await press(blueprint_env, "hold_left_down")  # the NEXT hold uses the new target
    assert step_data(blueprint_env)[-1]["area_id"] == "hall_strip"
    await press(blueprint_env, "release_left_down")


# --- the blink ----------------------------------------------------------------------------------------------------

async def test_the_new_target_blinks_with_flash_short(blueprint_env):
    await start_target(blueprint_env, **CYCLE)
    await press(blueprint_env, "double_right_down")
    assert blinks(blueprint_env) == [{"area_id": "hall_strip"}]
    await press(blueprint_env, "double_right_down")
    assert blinks(blueprint_env)[-1] == {"entity_id": ["light.hall_lamp_a", "light.hall_lamp_b"]}
    assert blueprint_env.calls[0].data["flash"] == "short"


async def test_the_blink_can_be_switched_off(blueprint_env):
    await start_target(blueprint_env, **CYCLE, dim_target_blink=False)
    await press(blueprint_env, "double_right_down")
    assert option(blueprint_env) == "strip"
    assert blueprint_env.calls == []
    for _ in range(5):
        await blueprint_env.advance(3)
    assert option(blueprint_env) == "spots"   # the fall-back still happens
    assert blueprint_env.calls == []


# --- the fall-back ------------------------------------------------------------------------------------------------

async def test_the_fall_back_blinks_the_leaving_target_then_the_default(blueprint_env):
    # Timeout 8 s. Switch to the strip at t=0. Nothing before 7.5 s; at 8 s the helper is back on the first
    # option and the leaving target (the strip) has blinked; the default blinks 1.5 s later, not at once.
    await start_target(blueprint_env, **CYCLE)
    await press(blueprint_env, "double_right_down")
    assert blinks(blueprint_env) == [STRIP]
    await blueprint_env.advance(6)
    assert option(blueprint_env) == "strip" and len(blinks(blueprint_env)) == 1
    await blueprint_env.advance(2)
    assert option(blueprint_env) == "spots"
    assert blinks(blueprint_env) == [STRIP, STRIP]
    await blueprint_env.advance(0.4)
    assert len(blinks(blueprint_env)) == 2
    await blueprint_env.advance(2)
    assert blinks(blueprint_env) == [STRIP, STRIP, SPOTS]
    for _ in range(5):
        await blueprint_env.advance(3)
    assert len(blinks(blueprint_env)) == 3


async def test_the_timeout_input_is_honoured(blueprint_env):
    await start_target(blueprint_env, **CYCLE, dim_target_timeout=20)
    await press(blueprint_env, "double_right_down")
    await blueprint_env.advance(10)
    assert option(blueprint_env) == "strip"
    await blueprint_env.advance(5)
    await blueprint_env.advance(6)
    assert option(blueprint_env) == "spots"


async def test_the_default_timeout_is_8_seconds(blueprint_env):
    # Only the helper and slots are given, so the timeout is the default.
    inputs = {k: v for k, v in CYCLE.items()}
    await start_target(blueprint_env, **inputs)
    await press(blueprint_env, "double_right_down")
    await blueprint_env.advance(7)
    assert option(blueprint_env) == "strip"
    await blueprint_env.advance(2)
    assert option(blueprint_env) == "spots"


async def test_every_press_restarts_the_countdown(blueprint_env):
    # A press of the switch at t=5 moves the fall-back from 8 s to 13 s.
    await start_target(blueprint_env, **CYCLE)
    await press(blueprint_env, "double_right_down")
    await blueprint_env.advance(5)
    await press(blueprint_env, "single_left")
    await blueprint_env.advance(5)          # t=10
    assert option(blueprint_env) == "strip"
    await blueprint_env.advance(4)          # t=14
    assert option(blueprint_env) == "spots"


async def test_a_hold_and_its_release_count_as_activity(blueprint_env):
    await start_target(blueprint_env, **CYCLE)
    await press(blueprint_env, "double_right_down")
    await blueprint_env.advance(6)
    await press(blueprint_env, "hold_left_down")
    await blueprint_env.advance(2)
    await press(blueprint_env, "release_left_down")
    await blueprint_env.advance(6)
    assert option(blueprint_env) == "strip"   # 6 s after the release
    await blueprint_env.advance(4)
    assert option(blueprint_env) == "spots"


async def test_no_fall_back_and_no_blink_when_already_on_the_default(blueprint_env):
    # The user sets the helper back by hand before the time is up: the watcher finds the default and does nothing.
    await start_target(blueprint_env, **CYCLE)
    await press(blueprint_env, "double_right_down")
    await select(blueprint_env, "spots")
    for _ in range(5):
        await blueprint_env.advance(3)
    assert option(blueprint_env) == "spots"
    assert blinks(blueprint_env) == [STRIP]   # only the blink of the switch itself


async def test_several_quick_switches_give_exactly_one_confirmation_sequence(blueprint_env):
    # Two double presses: spots -> strip -> lamp, two watchers. In all: 2 switch blinks + ONE leaving blink
    # (the lamp) + ONE default blink.
    await start_target(blueprint_env, **CYCLE)
    await press(blueprint_env, "double_right_down")
    await press(blueprint_env, "double_right_down")
    assert option(blueprint_env) == "lamp"
    for _ in range(8):
        await blueprint_env.advance(3)
    assert option(blueprint_env) == "spots"
    assert blinks(blueprint_env) == [STRIP, LAMP, LAMP, SPOTS]


async def test_a_second_switch_after_the_fall_back_works_again(blueprint_env):
    await start_target(blueprint_env, **CYCLE)
    await press(blueprint_env, "double_right_down")
    for _ in range(5):
        await blueprint_env.advance(3)
    assert option(blueprint_env) == "spots"
    await press(blueprint_env, "double_right_down")
    assert option(blueprint_env) == "strip"
    for _ in range(5):
        await blueprint_env.advance(3)
    assert option(blueprint_env) == "spots"
    assert len(blinks(blueprint_env)) == 6


async def test_the_watcher_survives_the_switch_going_unavailable_and_unknown(blueprint_env):
    # The switch drops out at t=5. That is activity (its state changed), so the fall-back comes at 13 s.
    await start_target(blueprint_env, **CYCLE)
    await press(blueprint_env, "double_right_down")
    await blueprint_env.advance(5)
    await blueprint_env.set_state(SWITCH, "unavailable")
    await blueprint_env.advance(5)
    assert option(blueprint_env) == "strip"
    await blueprint_env.set_state(SWITCH, "unknown")
    await blueprint_env.advance(1)
    for _ in range(5):
        await blueprint_env.advance(3)
    assert option(blueprint_env) == "spots"


async def test_a_press_while_a_hold_loop_runs_does_not_end_the_loop_or_the_watcher(blueprint_env):
    await start_target(blueprint_env, **CYCLE)
    await press(blueprint_env, "double_right_down")      # watcher starts
    await press(blueprint_env, "hold_left_down")          # a hold on the strip while the watcher waits
    await blueprint_env.advance(2)
    await press(blueprint_env, "release_left_down")
    assert [d["area_id"] for d in step_data(blueprint_env)] == ["hall_strip"] * 2
    for _ in range(6):
        await blueprint_env.advance(3)
    assert option(blueprint_env) == "spots"


# --- restarts -----------------------------------------------------------------------------------------------------

async def test_a_home_assistant_start_puts_the_target_back_without_a_blink(blueprint_env):
    await start_target(blueprint_env, **CYCLE)
    await select(blueprint_env, "lamp")
    await blueprint_env.fire_event("homeassistant_started")
    assert option(blueprint_env) == "spots"
    assert blueprint_env.calls == []


async def test_with_a_helper_a_switch_press_still_works_after_the_start_trigger(blueprint_env):
    # The configured helper makes the start trigger exist; the normal state trigger must work as before.
    await start_target(blueprint_env, **CYCLE)
    await blueprint_env.fire_event("homeassistant_started")
    await press(blueprint_env, "double_right_down")
    assert option(blueprint_env) == "strip"
    await press(blueprint_env, "hold_left_down")
    assert step_data(blueprint_env)[0]["area_id"] == "hall_strip"
    await press(blueprint_env, "release_left_down")


# The automation made from the blueprint (its entity id is the alias of the test environment).
def automation_state(env):
    return env.hass.states.get("automation.blueprint_under_test")


async def test_a_home_assistant_start_without_a_helper_runs_nothing(blueprint_env):
    # Without the helper the start trigger must not exist: no run, no trace, last_triggered stays empty.
    await start(blueprint_env, dim_light=LIGHT, dim_up_positions=["left_down"])
    await blueprint_env.fire_event("homeassistant_started")
    assert blueprint_env.calls == []
    assert automation_state(blueprint_env).attributes["last_triggered"] is None
    assert automation_state(blueprint_env).attributes["current"] == 0


# How many listeners the bus has for the event that the `homeassistant` start trigger waits for.
def start_listeners(env):
    return env.hass.bus.async_listeners().get("homeassistant_started", 0)


async def test_a_1_0_0_setup_has_exactly_one_trigger_and_ignores_the_start(blueprint_env):
    # The compatibility rule: with only the inputs of a 1.0.0 setup the blueprint behaves as 1.0.0. The
    # automation then has only its state trigger: the start trigger adds no listener for the start event,
    # and a Home Assistant start changes nothing (no run, no trace, last_triggered stays empty).
    own = [{"action": "light.toggle", "target": {"entity_id": LIGHT}}]
    before = start_listeners(blueprint_env)
    await start(blueprint_env, single_left=own, dim_light=LIGHT, dim_up_positions=["left_down"],
                scenes=["scene.hall_bright"], scene_positions=["right_down"])
    assert start_listeners(blueprint_env) == before
    await blueprint_env.fire_event("homeassistant_started")
    assert blueprint_env.calls == []
    assert automation_state(blueprint_env).attributes["last_triggered"] is None


async def test_with_a_helper_the_start_trigger_exists(blueprint_env):
    # The counterpart: with a helper there is one more listener, the start trigger.
    before = start_listeners(blueprint_env)
    await start_target(blueprint_env, **CYCLE)
    assert start_listeners(blueprint_env) == before + 1


# --- the run limit ------------------------------------------------------------------------------------------------

@pytest.mark.allow_warnings
async def test_every_watcher_occupies_one_of_the_ten_runs(blueprint_env):
    # Ten double presses make ten watchers, which fill all 10 parallel runs; the 11th press is dropped.
    await start_target(blueprint_env, **{**CYCLE, "dim_target_timeout": 60})
    for _ in range(11):
        await press(blueprint_env, "double_right_down")
    assert len(blinks(blueprint_env)) == 10


# --- the helper changes while a watcher waits (the slot is read FRESH at the end) ------------------------------------

async def _switch_then_let_the_timeout_pass(env, change):
    # Switch to the strip at t=0, let `change` alter the helper, then wait far beyond the timeout.
    await press(env, "double_right_down")
    await change()
    for _ in range(5):
        await env.advance(3)


async def test_a_helper_that_becomes_garbage_during_the_wait_causes_no_fall_back_and_no_error(blueprint_env):
    await start_target(blueprint_env, **CYCLE)
    await _switch_then_let_the_timeout_pass(blueprint_env, lambda: blueprint_env.set_state(HELPER, "garbage", {"options": OPTIONS}))
    assert option(blueprint_env) == "garbage"
    assert blinks(blueprint_env) == [STRIP]


async def test_a_helper_on_a_fourth_option_during_the_wait_causes_no_fall_back(blueprint_env):
    await start_target(blueprint_env, options=OPTIONS + ["extra"], **CYCLE)
    await _switch_then_let_the_timeout_pass(blueprint_env, lambda: select(blueprint_env, "extra"))
    assert option(blueprint_env) == "extra"
    assert blinks(blueprint_env) == [STRIP]


async def test_a_helper_on_an_empty_slot_during_the_wait_causes_no_fall_back(blueprint_env):
    # Slot 2 is empty, so its option counts as the default: the watcher finds "the default" and does nothing.
    await start_target(blueprint_env, **{**CYCLE, "dim_target_2": {}})
    await press(blueprint_env, "double_right_down")      # to the lamp (slot 3), the empty slot 2 is skipped
    await select(blueprint_env, "strip")                   # the user picks the option of the empty slot
    for _ in range(5):
        await blueprint_env.advance(3)
    assert option(blueprint_env) == "strip"
    assert blinks(blueprint_env) == [LAMP]


async def test_a_helper_that_goes_unavailable_during_the_wait_causes_no_error(blueprint_env):
    await start_target(blueprint_env, **CYCLE)
    await _switch_then_let_the_timeout_pass(blueprint_env, lambda: blueprint_env.set_state(HELPER, "unavailable"))
    assert blinks(blueprint_env) == [STRIP]


async def test_the_fall_back_works_from_the_third_slot_too(blueprint_env):
    await start_target(blueprint_env, **CYCLE)
    await press(blueprint_env, "double_right_down")
    await press(blueprint_env, "double_right_down")
    for _ in range(8):
        await blueprint_env.advance(3)
    assert option(blueprint_env) == "spots"
    assert blinks(blueprint_env)[-2:] == [LAMP, SPOTS]
