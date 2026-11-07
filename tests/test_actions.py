"""The generic mapping: one optional action input per position and gesture."""

import pytest

from ha_blueprint_test_harness import BlueprintLoadError

from helpers import ALL_EVENTS, BLUEPRINT, LIGHT, SWITCH, names, press, start


# Every one of the 16 inputs gets its own tag, so the test can tell which one ran.
def all_actions():
    return {e: [{"action": "light.toggle", "target": {"entity_id": LIGHT}, "data": {"tag": e}}] for e in ALL_EVENTS}


@pytest.mark.parametrize("event", ALL_EVENTS)
async def test_each_event_runs_only_its_own_actions(blueprint_env, event):
    # Arrange: all 16 inputs filled, each with its own tag.
    await start(blueprint_env, **all_actions())
    # Act: the switch sends one event.
    await press(blueprint_env, event)
    # Assert: exactly the matching input ran, once, on the light.
    assert [c.data["tag"] for c in blueprint_env.calls] == [event]
    assert blueprint_env.calls[0].entity_ids == {LIGHT}


async def test_empty_inputs_do_nothing(blueprint_env):
    # Arrange: nothing configured except the switch.
    await start(blueprint_env)
    # Act: every possible event.
    for event in ALL_EVENTS:
        await press(blueprint_env, event)
    # Assert: no service call at all.
    assert blueprint_env.calls == []


async def test_a_sequence_of_several_actions_runs_in_order(blueprint_env):
    # Arrange: a single press with two actions.
    seq = [{"action": "light.toggle", "target": {"entity_id": LIGHT}, "data": {"tag": n}} for n in ("a", "b")]
    await start(blueprint_env, single_left=seq)
    await press(blueprint_env, "single_left")
    assert [c.data["tag"] for c in blueprint_env.calls] == ["a", "b"]


async def test_an_unknown_event_type_does_nothing(blueprint_env):
    # Arrange/Act: event types that are not in the switch's list, an empty one and a missing one.
    await start(blueprint_env, **all_actions())
    for event in ("triple_left", "single", "single_middle", ""):
        await press(blueprint_env, event)
    await blueprint_env.set_state(SWITCH, "2026-01-01T11:00:00.000+00:00")  # no event_type attribute at all
    assert blueprint_env.calls == []


@pytest.mark.parametrize("old, new", [("unavailable", "2026-01-01T10:00:00+00:00"),
                                      ("2026-01-01T10:00:00+00:00", "unavailable"),
                                      ("2026-01-01T10:00:00+00:00", "unknown")])
async def test_unavailable_and_unknown_are_ignored(blueprint_env, old, new):
    # Arrange: the entity carries an old event_type; going to or from unavailable must not replay it.
    await start(blueprint_env, **all_actions(), scene_states={SWITCH: (old, {"event_type": "single_left"})})
    await blueprint_env.set_state(SWITCH, new, {"event_type": "single_left"})
    assert blueprint_env.calls == []


async def test_the_first_press_after_unknown_works(blueprint_env):
    # A switch that was never pressed has the state "unknown"; its first press must still count.
    await start(blueprint_env, **all_actions())
    await press(blueprint_env, "single_left")
    assert names(blueprint_env) == ["light.toggle"]


async def test_other_entities_are_ignored(blueprint_env):
    # Arrange/Act: a different event entity changes.
    await start(blueprint_env, **all_actions())
    await blueprint_env.set_state("event.kitchen_h2_switch_action", "2026-01-01T10:00:00+00:00", {"event_type": "single_left"})
    assert blueprint_env.calls == []


@pytest.mark.allow_warnings  # Home Assistant logs the failed load; the test expects that
async def test_a_missing_switch_entity_does_not_load(blueprint_env):
    # Sad path: the only required input is missing.
    with pytest.raises(BlueprintLoadError):
        await blueprint_env.start(BLUEPRINT, {}, services=["light.toggle"])


async def test_the_device_coming_back_from_unavailable_does_not_replay_the_last_press(blueprint_env):
    # Observed on one device: the entity goes unavailable now and then and returns with its OLD timestamp
    # and OLD event_type. That must not run the last press again.
    await start(blueprint_env, **all_actions())
    await blueprint_env.set_state(SWITCH, "2026-01-01T10:00:00.000+00:00", {"event_type": "single_left"})
    assert len(blueprint_env.calls) == 1
    await blueprint_env.set_state(SWITCH, "unavailable")
    await blueprint_env.set_state(SWITCH, "2026-01-01T10:00:00.000+00:00", {"event_type": "single_left"})
    assert len(blueprint_env.calls) == 1
    # A real new press after that works again.
    await press(blueprint_env, "single_right")
    assert [c.data["tag"] for c in blueprint_env.calls] == ["single_left", "single_right"]


async def test_events_with_microseconds_in_the_timestamp_work(blueprint_env):
    # The real entity uses timestamps with microseconds; two presses a fraction of a second apart count twice.
    await start(blueprint_env, **all_actions())
    await blueprint_env.set_state(SWITCH, "2026-01-01T10:00:00.123456+00:00", {"event_type": "single_left_down"})
    await blueprint_env.set_state(SWITCH, "2026-01-01T10:00:00.623457+00:00", {"event_type": "single_right_down"})
    assert [c.data["tag"] for c in blueprint_env.calls] == ["single_left_down", "single_right_down"]


async def test_a_double_press_arrives_alone_without_a_single_before_it(blueprint_env):
    # Observed on one device: double_left_down comes alone, no single_left_down first.
    await start(blueprint_env, **all_actions())
    await press(blueprint_env, "double_left_down")
    assert [c.data["tag"] for c in blueprint_env.calls] == ["double_left_down"]


# Observed on one device, not confirmed by the vendor: double_right_down also arrives alone.
async def test_a_double_press_on_the_lower_right_button_arrives_alone(blueprint_env):
    await start(blueprint_env, **all_actions())
    await press(blueprint_env, "double_right_down")
    assert [c.data["tag"] for c in blueprint_env.calls] == ["double_right_down"]
