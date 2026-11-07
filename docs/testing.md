# Testing

Tests use `ha-blueprint-test-harness`: the blueprint runs as a real automation in a throw-away Home Assistant, services are recorded, the clock is frozen and moved with `advance()`.

## How a press is replayed

`tests/helpers.py` has `press(env, event_type)`: it sets the event entity's state to a NEW timestamp and the attribute `event_type`, like the real entity. The device sequences in [device-behaviour.md](device-behaviour.md) are replayed in the order they were reported, with `advance()` in whole seconds in between (hold, time passes, release). The tap-before-hold order and two held rockers are replayed as measured.

## What is covered

| Feature | Tests (file) |
| --- | --- |
| Generic actions | all 16 event types each run only their own input once, aimed at the right target; empty inputs do nothing; several actions run in order; unknown, empty or missing `event_type`; other entities; first press from `unknown`; unavailable and unknown are ignored; the old press is NOT replayed after `unavailable`; microsecond timestamps; double alone without a single; missing required input (`test_actions.py`) |
| Dimming | up and down with the step size; both lists (up wins); interval and "not early"; stop at the matching release; release of another rocker ignored; release during the light call (the race), also with another rocker's release; 10 s hold with one hold and one release; short hold; other presses neither stop nor speed it up; safety limit counts time; ends on unavailable and on unknown; no light, no positions; defaults; at most 10 runs; tap before the hold; two held rockers (opposite and same direction); an ignored misspelled input documented (`test_dimming.py`) |
| Scene cycle | first scene when none activated; wrap-around over 7 presses; follows the newest activation; list order; unavailable and text states; microsecond order; equal times; one scene; only chosen buttons and gestures; empty list or no positions; defaults; either lower button; double followed by a single on the other rocker (`test_scenes.py`) |

The known limit "two releases during one slow light call" (see design.md) is covered by two tests: one asserts the bounded behaviour (the left loop ends only at the safety limit), one is a strict `xfail` with the behaviour we would like (no step after both releases). Both replay the probe: the light mock counts its calls and, on the left loop's first call, sets the switch state twice (`release_left_down`, then `release_right_down`).

Every test also fails if the automation logged a warning or error (`conftest.py`, fixture `no_automation_warnings`), unless it carries the marker `allow_warnings` (the run-limit test and the failed-load test). This is what makes the guards `dim_light | length > 0` and `scenes | length > 0` testable: without them Home Assistant logs an error.

## What the harness cannot test

- Sub-second timing: timers can fire up to 0.5 s early, so only whole-second intervals are tested. The real 0.44 s hold is replayed as "release before the next step".
- Real light behaviour (`brightness_step_pct` is accepted with any data, limits at 0 % and 100 %).
- Real Zigbee2MQTT timing, the 0.2 s spacing of events, a Home Assistant restart during a hold, holds longer than 10 s, and a real running automation with a real light. (A 10 s hold and two held rockers were measured on the device and are replayed.)
- That the scene entity's state is a timestamp (assumed from Home Assistant's behaviour; the test effect sets it).
- `as_datetime(value, default)` and the other templates on Home Assistant versions older than 2026.10.4.

## Mutation result

Run: `.venv/bin/python -m ha_blueprint_test_harness.mutate blueprints/automation/aqara_h2_switch.yaml --timeout 60 -- .venv/bin/python -m pytest -q -x -p no:cacheprovider tests` (about 4 minutes, output only at the end).

82 tests pass and 1 is a strict xfail (the known limit). 72 loadable mutants.

- First run of the reworked blueprint (75 to 77 tests, taken while I was still adding tests): 69 killed, 3 survived, 96 %.
- Two of those survivors (`dim_light | length > 0` to `>= 0`, `scenes | length > 0` to `>= 0`) should have been killed by the log check, but the first version of the check read an empty log (see docs-friction.md). After the fix: **71 killed, 1 survived, 0 invalid, 99 %** (81 tests).
- The one survivor, `M008` (`default('', true)` to `default('', false)` for `event_type`): it only matters when `event_type` is an empty string or null. Then no branch matches and no service runs, whichever default is used. It changes nothing a user can see (an extra log line at most). Accepted.

Not mutated by the tool: numbers inside templates, the bodies of `choose` branches, list defaults. The default positions are covered by hand-written tests, not by mutants.
