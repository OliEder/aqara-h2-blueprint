"""The built-in scene cycle on a double press."""

import pytest

from helpers import SCENES, activated, names, press, start

CYCLE = {"scenes": SCENES, "scene_positions": ["right"]}


async def test_the_first_double_press_activates_the_first_scene(blueprint_env):
    # Arrange: no scene was ever activated (state unknown).
    await start(blueprint_env, **CYCLE)
    await press(blueprint_env, "double_right")
    assert activated(blueprint_env) == [SCENES[0]]


async def test_the_scenes_are_cycled_with_wrap_around(blueprint_env):
    await start(blueprint_env, **CYCLE)
    for _ in range(7):
        await blueprint_env.advance(1)  # scene states carry the time, so each activation needs its own second
        await press(blueprint_env, "double_right")
    assert activated(blueprint_env) == [SCENES[i % 3] for i in range(7)]


async def test_the_next_scene_follows_the_most_recently_activated_one(blueprint_env):
    # Arrange: the list's second scene was activated last (also by something outside the blueprint).
    await start(blueprint_env, **CYCLE, scene_states={SCENES[0]: "2026-01-01T08:00:00+00:00",
                                                       SCENES[1]: "2026-01-01T09:00:00+00:00"})
    await press(blueprint_env, "double_right")
    assert activated(blueprint_env) == [SCENES[2]]


async def test_the_order_of_the_list_decides_not_the_alphabet(blueprint_env):
    # A list in a non-alphabetical order is followed as given.
    order = [SCENES[2], SCENES[0], SCENES[1]]
    await start(blueprint_env, scenes=order, scene_positions=["right"],
                scene_states={SCENES[2]: "2026-01-01T09:00:00+00:00"})
    await press(blueprint_env, "double_right")
    assert activated(blueprint_env) == [SCENES[0]]


async def test_a_scene_that_is_unavailable_counts_as_never_activated(blueprint_env):
    await start(blueprint_env, **CYCLE, scene_states={SCENES[0]: "unavailable", SCENES[1]: "unavailable"})
    await press(blueprint_env, "double_right")
    assert activated(blueprint_env) == [SCENES[0]]


async def test_a_single_scene_is_activated_again_each_time(blueprint_env):
    await start(blueprint_env, scenes=[SCENES[0]], scene_positions=["right"])
    await press(blueprint_env, "double_right")
    await blueprint_env.advance(1)
    await press(blueprint_env, "double_right")
    assert activated(blueprint_env) == [SCENES[0], SCENES[0]]


@pytest.mark.parametrize("event", ["single_right", "hold_right", "release_right", "double_left",
                                   "double_left_down", "double_right_down"])
async def test_only_the_chosen_double_press_cycles(blueprint_env, event):
    await start(blueprint_env, **CYCLE)
    await press(blueprint_env, event)
    assert blueprint_env.calls == []


async def test_several_positions_share_one_cycle(blueprint_env):
    await start(blueprint_env, scenes=SCENES, scene_positions=["left", "right_down"])
    await press(blueprint_env, "double_left")
    await blueprint_env.advance(1)
    await press(blueprint_env, "double_right_down")
    assert activated(blueprint_env) == [SCENES[0], SCENES[1]]


async def test_no_scenes_means_no_call(blueprint_env):
    # Sad path: positions chosen but the list is empty.
    await start(blueprint_env, scenes=[], scene_positions=["right"])
    await press(blueprint_env, "double_right")
    assert blueprint_env.calls == []


async def test_no_positions_means_no_cycle(blueprint_env):
    await start(blueprint_env, scenes=SCENES)
    await press(blueprint_env, "double_right")
    assert blueprint_env.calls == []


async def test_the_cycle_and_own_actions_both_run(blueprint_env):
    own = [{"action": "light.toggle", "target": {"entity_id": "light.hall"}}]
    await start(blueprint_env, **CYCLE, double_right=own)
    await press(blueprint_env, "double_right")
    assert names(blueprint_env) == ["light.toggle", "scene.turn_on"]


async def test_with_equal_times_the_earlier_scene_in_the_list_counts_as_the_last(blueprint_env):
    # Two scenes carry the same activation time (for example both were set by one automation).
    same = "2026-01-01T09:00:00+00:00"
    await start(blueprint_env, **CYCLE, scene_states={SCENES[0]: same, SCENES[1]: same})
    await press(blueprint_env, "double_right")
    assert activated(blueprint_env) == [SCENES[1]]


async def test_a_scene_state_that_is_text_counts_as_never_activated(blueprint_env):
    # Garbage in a scene's state must neither crash the template nor win the comparison.
    await start(blueprint_env, **CYCLE, scene_states={SCENES[0]: "banana", SCENES[1]: "2026-01-01T09:00:00+00:00",
                                                       SCENES[2]: "not a time"})
    await press(blueprint_env, "double_right")
    assert activated(blueprint_env) == [SCENES[2]]


async def test_times_with_microseconds_are_compared_exactly(blueprint_env):
    # Real scene states carry microseconds; two scenes a few microseconds apart still have an order.
    await start(blueprint_env, **CYCLE, scene_states={SCENES[0]: "2026-01-01T09:00:00.000002+00:00",
                                                       SCENES[1]: "2026-01-01T09:00:00.000001+00:00"})
    await press(blueprint_env, "double_right")
    assert activated(blueprint_env) == [SCENES[1]]


async def test_the_default_position_is_the_lower_right_button(blueprint_env):
    # Only the scenes are given: a double press on right_down cycles, one on left_down does not.
    await start(blueprint_env, scenes=SCENES)
    await press(blueprint_env, "double_left_down")
    assert blueprint_env.calls == []
    await press(blueprint_env, "double_right_down")
    assert activated(blueprint_env) == [SCENES[0]]


async def test_the_cycle_works_on_either_lower_button(blueprint_env):
    # Observed on one device: double press arrives on both lower buttons, so either may drive the cycle.
    await start(blueprint_env, scenes=SCENES, scene_positions=["left_down", "right_down"])
    await press(blueprint_env, "double_left_down")
    await blueprint_env.advance(1)
    await press(blueprint_env, "double_right_down")
    assert activated(blueprint_env) == [SCENES[0], SCENES[1]]


async def test_a_single_on_the_other_rocker_right_after_a_double_still_runs(blueprint_env):
    # Observed on one device: double_left_down, then single_right_down 0.23 s later, both delivered.
    # The cycle runs for the double and the own action runs for the single.
    own = [{"action": "light.toggle", "target": {"entity_id": "light.hall"}}]
    await start(blueprint_env, scenes=SCENES, scene_positions=["left_down"], single_right_down=own)
    await press(blueprint_env, "double_left_down")
    await press(blueprint_env, "single_right_down")
    assert names(blueprint_env) == ["scene.turn_on", "light.toggle"]
