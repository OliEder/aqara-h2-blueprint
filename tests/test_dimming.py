"""The built-in dimming: a hold dims in steps, the matching release stops it.

Timing note: the harness fires timers up to half a second early, so the tests use whole-second
intervals and only look at moments at least 0.5 s away from a step (whole-second advances).
The device sequences come from docs/device-behaviour.md: one hold, nothing in between, one release.
"""

import pytest

from helpers import BLUEPRINT, LIGHT, SWITCH, _counter, names, press, start, start_with_release_during_call, steps

DIM = {"dim_light": LIGHT, "dim_up_positions": ["left"], "dim_down_positions": ["right"],
       "dim_step": 10, "dim_interval": 2, "dim_max_seconds": 60}
# The lower buttons, which the tested device sends hold and release for; left dims up, right dims down.
DOWN = {"dim_light": LIGHT, "dim_up_positions": ["left_down"], "dim_down_positions": ["right_down"],
        "dim_step": 10, "dim_interval": 2, "dim_max_seconds": 60}


async def test_a_hold_dims_up_in_steps_until_the_release(blueprint_env):
    # Arrange: left dims up by 10 % every 2 seconds.
    await start(blueprint_env, **DIM)
    # Act: hold; the first step comes at once, then one more per 2 seconds.
    await press(blueprint_env, "hold_left")
    assert steps(blueprint_env) == [10]
    await blueprint_env.advance(2)
    assert steps(blueprint_env) == [10, 10]
    await blueprint_env.advance(2)
    assert steps(blueprint_env) == [10, 10, 10]
    # Assert: the release stops it, and nothing follows however long we wait.
    await press(blueprint_env, "release_left")
    for _ in range(10):
        await blueprint_env.advance(2)
    assert steps(blueprint_env) == [10, 10, 10]
    assert all(c.entity_ids == {LIGHT} for c in blueprint_env.calls)


async def test_the_step_is_not_taken_early(blueprint_env):
    # One second into a 2 second interval there is no new step.
    await start(blueprint_env, **DIM)
    await press(blueprint_env, "hold_left")
    await blueprint_env.advance(1)
    assert steps(blueprint_env) == [10]


async def test_a_hold_dims_down_with_a_negative_step(blueprint_env):
    await start(blueprint_env, **{**DIM, "dim_step": 25})
    await press(blueprint_env, "hold_right")
    await blueprint_env.advance(2)
    assert steps(blueprint_env) == [-25, -25]


async def test_up_wins_if_a_position_is_in_both_lists(blueprint_env):
    await start(blueprint_env, **{**DIM, "dim_down_positions": ["left"]})
    await press(blueprint_env, "hold_left")
    assert steps(blueprint_env) == [10]


async def test_a_short_hold_of_0_44_seconds_gives_one_step(blueprint_env):
    # Measured on one device: hold_right_down, release 0.44 s later. One step, then nothing.
    await start(blueprint_env, **DOWN)
    await press(blueprint_env, "hold_right_down")
    await blueprint_env.advance(1)  # whole seconds only: the real 0.44 s cannot be replayed exactly; 1 s is shorter than the 2 s interval too
    await press(blueprint_env, "release_right_down")
    for _ in range(5):
        await blueprint_env.advance(2)
    assert steps(blueprint_env) == [-10]


async def test_a_release_arriving_during_the_light_call_is_not_lost(blueprint_env):
    # Arrange: the release event arrives while the first light.turn_on is still running.
    await start_with_release_during_call(blueprint_env, "release_left_down", **DOWN)
    # Act: hold, then let a long time pass.
    await press(blueprint_env, "hold_left_down")
    for _ in range(10):
        await blueprint_env.advance(2)
    # Assert: exactly the one step; without the fix it kept dimming to the safety limit.
    assert steps(blueprint_env) == [10]


async def test_a_release_of_another_position_during_the_call_is_ignored(blueprint_env):
    # The same race with the release of the OTHER rocker: dimming must go on.
    await start_with_release_during_call(blueprint_env, "release_right_down", **DOWN)
    await press(blueprint_env, "hold_left_down")
    await blueprint_env.advance(2)
    assert len(steps(blueprint_env)) >= 2
    await press(blueprint_env, "release_left_down")


async def test_a_10_second_hold_with_one_hold_and_one_release(blueprint_env):
    # Measured on one device: hold at 0 s, release at 10.22 s, nothing in between (no repeated hold events).
    await start(blueprint_env, **{**DOWN, "dim_interval": 2})
    await press(blueprint_env, "hold_left_down")
    for _ in range(5):
        await blueprint_env.advance(2)
    assert steps(blueprint_env) == [10] * 6
    await press(blueprint_env, "release_left_down")
    for _ in range(5):
        await blueprint_env.advance(2)
    assert steps(blueprint_env) == [10] * 6


async def test_a_release_right_after_the_hold_gives_one_step(blueprint_env):
    await start(blueprint_env, **DIM)
    await press(blueprint_env, "hold_left")
    await press(blueprint_env, "release_left")
    for _ in range(5):
        await blueprint_env.advance(2)
    assert steps(blueprint_env) == [10]


async def test_the_release_of_another_position_does_not_stop_dimming(blueprint_env):
    await start(blueprint_env, **DIM)
    await press(blueprint_env, "hold_left")
    await press(blueprint_env, "release_right")
    await blueprint_env.advance(2)
    await blueprint_env.advance(2)
    assert len(steps(blueprint_env)) == 3
    await press(blueprint_env, "release_left")
    for _ in range(5):
        await blueprint_env.advance(2)
    assert len(steps(blueprint_env)) == 3


async def test_other_presses_neither_stop_nor_speed_up_the_hold(blueprint_env):
    # A single press of another position during the hold: no extra step at once, no early step later.
    await start(blueprint_env, **DIM)
    await press(blueprint_env, "hold_left")
    await press(blueprint_env, "single_right")
    await press(blueprint_env, "double_right_down")
    assert steps(blueprint_env) == [10]
    await blueprint_env.advance(1)
    assert steps(blueprint_env) == [10]
    await blueprint_env.advance(1)
    assert steps(blueprint_env) == [10, 10]
    await press(blueprint_env, "release_left")


async def test_dimming_stops_at_the_safety_limit_without_a_release(blueprint_env):
    # Arrange: the release is lost; the limit is 6 seconds of real time, the interval 2.
    await start(blueprint_env, **{**DIM, "dim_max_seconds": 6})
    await press(blueprint_env, "hold_left")
    for _ in range(20):
        await blueprint_env.advance(2)
    # Assert: exactly 3 steps (at 0, 2 and 4 s), then it stops.
    assert steps(blueprint_env) == [10] * 3


async def test_the_safety_limit_counts_time_not_iterations(blueprint_env):
    # Other presses wake nothing, so they must not move the limit either: still 3 steps in 6 s.
    await start(blueprint_env, **{**DIM, "dim_max_seconds": 6})
    await press(blueprint_env, "hold_left")
    for _ in range(3):
        await press(blueprint_env, "single_right")
        await blueprint_env.advance(2)
    for _ in range(5):
        await blueprint_env.advance(2)
    assert steps(blueprint_env) == [10] * 3


async def test_dimming_ends_when_the_switch_becomes_unavailable(blueprint_env):
    # The switch drops out during the hold: dimming must end at once, not run to the safety limit.
    await start(blueprint_env, **DIM)
    await press(blueprint_env, "hold_left")
    await blueprint_env.advance(2)
    assert steps(blueprint_env) == [10, 10]
    await blueprint_env.set_state(SWITCH, "unavailable")
    for _ in range(10):
        await blueprint_env.advance(2)
    assert steps(blueprint_env) == [10, 10]


async def test_dimming_ends_when_the_switch_becomes_unknown(blueprint_env):
    await start(blueprint_env, **DIM)
    await press(blueprint_env, "hold_left")
    await blueprint_env.set_state(SWITCH, "unknown")
    for _ in range(5):
        await blueprint_env.advance(2)
    assert steps(blueprint_env) == [10]


async def test_the_interval_is_honoured(blueprint_env):
    await start(blueprint_env, **{**DIM, "dim_interval": 4})
    await press(blueprint_env, "hold_left")
    await blueprint_env.advance(2)
    assert len(steps(blueprint_env)) == 1
    await blueprint_env.advance(2)
    assert len(steps(blueprint_env)) == 2


@pytest.mark.parametrize("event", ["single_left", "double_left", "release_left", "hold_left_down", "hold_right_down"])
async def test_only_the_chosen_holds_dim(blueprint_env, event):
    # Other gestures, and holds on positions that are not chosen, must not dim.
    await start(blueprint_env, **DIM)
    await press(blueprint_env, event)
    await blueprint_env.advance(6)
    assert blueprint_env.calls == []


async def test_nothing_dims_without_a_light(blueprint_env):
    # No light: no service call AND no logged problem (the autouse log check would fail the test otherwise),
    # so the guard does its job and Home Assistant does not have to reject an empty target.
    await start(blueprint_env, **{**DIM, "dim_light": ""})
    await press(blueprint_env, "hold_left")
    await blueprint_env.advance(6)
    assert blueprint_env.calls == []


async def test_nothing_dims_when_no_position_is_chosen(blueprint_env):
    await start(blueprint_env, dim_light=LIGHT, dim_up_positions=[], dim_down_positions=[])
    await press(blueprint_env, "hold_left_down")
    await press(blueprint_env, "hold_right_down")
    await blueprint_env.advance(6)
    assert blueprint_env.calls == []


async def test_dimming_and_own_actions_both_run(blueprint_env):
    # The user's own action for the same hold runs once, in addition to the dimming.
    own = [{"action": "light.toggle", "target": {"entity_id": LIGHT}}]
    await start(blueprint_env, **DIM, hold_left=own)
    await press(blueprint_env, "hold_left")
    assert names(blueprint_env) == ["light.toggle", "light.turn_on"]
    await press(blueprint_env, "release_left")


async def test_the_defaults_dim_up_on_left_down_and_down_on_right_down(blueprint_env):
    # Only the light is given: the default positions, a 10 % step, a 1 s interval and a 15 s limit apply.
    await start(blueprint_env, dim_light=LIGHT)
    await press(blueprint_env, "hold_left_down")
    assert steps(blueprint_env) == [10]
    await press(blueprint_env, "release_left_down")
    await press(blueprint_env, "hold_right_down")
    assert steps(blueprint_env) == [10, -10]
    # A whole second later the next step is due (interval 1 s; an interval of 2 s would not be due yet).
    await blueprint_env.advance(1)
    assert steps(blueprint_env) == [10, -10, -10]
    # The release is lost: the 15 s default limit ends it. 15 steps in all for this hold.
    for _ in range(40):
        await blueprint_env.advance(1)
    assert steps(blueprint_env) == [10] + [-10] * 15


@pytest.mark.allow_warnings
async def test_at_most_ten_runs_at_the_same_time(blueprint_env):
    # Eleven holds without a release: the blueprint allows 10 runs at once, the eleventh is dropped
    # (Home Assistant logs a warning, which this test expects).
    await start(blueprint_env, **DIM)
    for _ in range(11):
        await press(blueprint_env, "hold_left")
    assert len(steps(blueprint_env)) == 10


async def test_a_misspelled_optional_input_is_silently_ignored_by_the_harness(blueprint_env):
    # Documents a trap, not a feature: start() accepts an input name the blueprint does not have, and the
    # test then runs with the default. Never rely on it; check input names against the blueprint.
    await start(blueprint_env, dim_ligth=LIGHT)
    await press(blueprint_env, "hold_left_down")
    assert blueprint_env.calls == []


async def test_a_tap_on_another_rocker_before_the_hold_is_reported_does_not_disturb_it(blueprint_env):
    # Observed on one device: single_right_down at 0.0 s, hold_left_down at 0.2 s, release_left_down at 2.68 s.
    # The tap is reported BEFORE the hold it happened during. The tap runs its own action; the hold dims
    # without an extra step and ends at its own release.
    own = [{"action": "light.toggle", "target": {"entity_id": LIGHT}}]
    await start(blueprint_env, **DOWN, single_right_down=own)
    await press(blueprint_env, "single_right_down")
    await press(blueprint_env, "hold_left_down")
    assert names(blueprint_env) == ["light.toggle", "light.turn_on"]
    await blueprint_env.advance(2)
    assert steps(blueprint_env) == [10, 10]
    await press(blueprint_env, "release_left_down")
    for _ in range(5):
        await blueprint_env.advance(2)
    assert steps(blueprint_env) == [10, 10]
    assert names(blueprint_env).count("light.toggle") == 1


async def test_two_held_rockers_run_two_loops_and_each_release_ends_only_its_own(blueprint_env):
    # Observed on one device: hold_right_down 0.0, hold_left_down 0.21, release_left_down 4.79,
    # release_right_down 4.98. Left dims up, right dims down; both loops run, each ends at its own release.
    await start(blueprint_env, **DOWN)
    await press(blueprint_env, "hold_right_down")
    await press(blueprint_env, "hold_left_down")
    assert sorted(steps(blueprint_env)) == [-10, 10]
    await blueprint_env.advance(2)
    assert sorted(steps(blueprint_env)) == [-10, -10, 10, 10]
    # The left loop ends first although it was held second; only the right loop keeps going.
    await press(blueprint_env, "release_left_down")
    await blueprint_env.advance(2)
    assert sorted(steps(blueprint_env)) == [-10, -10, -10, 10, 10]
    await press(blueprint_env, "release_right_down")
    for _ in range(5):
        await blueprint_env.advance(2)
    assert sorted(steps(blueprint_env)) == [-10, -10, -10, 10, 10]


async def test_two_held_rockers_dimming_the_same_way_add_up(blueprint_env):
    # Both lower rockers set to dim up: two loops, so the light gets two steps per interval (documented).
    await start(blueprint_env, **{**DOWN, "dim_up_positions": ["left_down", "right_down"], "dim_down_positions": []})
    await press(blueprint_env, "hold_right_down")
    await press(blueprint_env, "hold_left_down")
    await blueprint_env.advance(2)
    assert steps(blueprint_env) == [10, 10, 10, 10]
    await press(blueprint_env, "release_right_down")
    await blueprint_env.advance(2)
    assert len(steps(blueprint_env)) == 5
    await press(blueprint_env, "release_left_down")


# Loads the blueprint with a light mock that, on its SECOND call overall (the first call of the left loop),
# lets both releases arrive during the call: release_left_down, then release_right_down.
async def start_with_two_releases_during_call(env, **inputs):
    calls = []

    async def effect(hass, call):
        calls.append(call)
        if len(calls) == 2:
            for event in ("release_left_down", "release_right_down"):
                stamp = f"2026-01-01T12:00:{next(_counter):02d}.000+00:00"
                hass.states.async_set(SWITCH, stamp, {"event_type": event})

    await env.start(BLUEPRINT, {"switch_entity": SWITCH, **inputs}, states={SWITCH: "unknown", LIGHT: "on"},
                    services=["light.turn_on"], effects={"light.turn_on": effect})


# Replays: hold_right_down, hold_left_down, both releases during the left loop's first light call.
async def replay_two_releases_during_the_call(env):
    await start_with_two_releases_during_call(env, **DOWN)
    await press(env, "hold_right_down")
    await press(env, "hold_left_down")
    assert steps(env) == [-10, 10]
    for _ in range(10):
        await env.advance(2)


async def test_known_limit_two_releases_during_one_slow_call_leave_a_loop_running_to_the_limit(blueprint_env):
    # KNOWN LIMIT (documented in docs/design.md): the wait only sees the LATEST event of the switch. When two
    # releases arrive during one light call (needs a call slower than the ~0.2 s gap between events), the left
    # loop sees only release_right_down, never ends at its own release and dims until the safety limit.
    # This test asserts the bounded behaviour: it does end at the limit (60 s here: 30 more steps at most).
    await replay_two_releases_during_the_call(blueprint_env)
    assert steps(blueprint_env)[:2] == [-10, 10]
    assert steps(blueprint_env).count(10) > 1  # still dimming 20 s later: the limit, not the release, ends it
    for _ in range(40):
        await blueprint_env.advance(2)
    count = len(steps(blueprint_env))
    for _ in range(5):
        await blueprint_env.advance(2)
    assert len(steps(blueprint_env)) == count  # and it does stop (at the 60 s safety limit)


@pytest.mark.xfail(strict=True, reason="known limit: the wait sees only the latest event, see docs/design.md")
async def test_ideal_no_step_after_both_releases_arrived_during_one_call(blueprint_env):
    # The behaviour we would like: after both releases nothing dims any more. Fails today (strict xfail), so
    # the day someone fixes the limit this test turns into an error and the two tests are replaced.
    await replay_two_releases_during_the_call(blueprint_env)
    assert steps(blueprint_env) == [-10, 10]
