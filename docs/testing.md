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
- Real Zigbee2MQTT timing, the 0.2 s spacing of events, a Home Assistant restart during a hold, holds longer than 10 s, and anything about a real light beyond the maintainer's manual check on 2026-11-07 (see the README). (A 10 s hold and two held rockers were measured on the device and are replayed.)
- That the scene entity's state is a timestamp (assumed from Home Assistant's behaviour; the test effect sets it).
- `as_datetime(value, default)` and the other templates on Home Assistant versions older than 2026.10.4.

## Mutation result

Run: `.venv/bin/python -m ha_blueprint_test_harness.mutate blueprints/automation/aqara_h2_switch.yaml --jobs 4 --timeout 180 -- .venv/bin/python -m pytest -q -x -p no:cacheprovider tests` (about 7 minutes for 1.1.0 with 4 jobs on an 8-core Mac; one line per mutant as it goes).

82 tests pass and 1 is a strict xfail (the known limit). 72 loadable mutants.

- First run of the reworked blueprint (75 to 77 tests, taken while I was still adding tests): 69 killed, 3 survived, 96 %.
- Two of those survivors (`dim_light | length > 0` to `>= 0`, `scenes | length > 0` to `>= 0`) should have been killed by the log check, but the first version of the check read an empty log (see docs-friction.md). After the fix: **71 killed, 1 survived, 0 invalid, 99 %** (81 tests).
- The one survivor, `M008` (`default('', true)` to `default('', false)` for `event_type`): it only matters when `event_type` is an empty string or null. Then no branch matches and no service runs, whichever default is used. It changes nothing a user can see (an extra log line at most). Accepted.

**Version 1.1.0, measured on 2026-11-09 with harness 0.4.1: 136 mutants, 133 killed, 3 survived, 0 invalid, 97.79 %** (134 tests: 133 pass, 1 strict xfail). The first run of that day killed 131; two tests were added for the two survivors that were real gaps:

- `M028` (`helper_options | length > 0` to `>= 0` in the start trigger): killed by `test_a_home_assistant_start_with_a_helper_that_does_not_exist_runs_quietly`.
- `M117` (the pause of the inactivity watcher dropped, so its loop would check again and again): killed by `test_the_inactivity_watcher_waits_instead_of_checking_in_a_loop`, which reads the trace of the run.
- The 3 survivors left: `M016` (`default('', true)`, accepted above as `M008`) and the two comparisons `dim_target_helper | length > 0` to `>= 0` (`M027` in the start trigger, `M098` in the switch branch). The helper id is empty only when its options list is empty, and the next condition (`helper_options | length > 0`, `helper_options | length > next_slot`) already rules that case out, so the change has no effect. Equivalent.

The CI fails when the score drops below 97 %.

Not mutated by the tool: numbers inside templates, the bodies of `choose` branches, list defaults. The default positions are covered by hand-written tests, not by mutants.

# Version 1.1.0

`tests/test_target.py` is new; the files of 1.0.0 are unchanged (their 82 tests pass unchanged and the strict xfail is still an xfail). The helper is the real `input_select` component, set up with `async_setup_component(env.hass, "input_select", {...})` before `start()`; it is changed like a user would with a real `input_select.select_option` call. The light and scene services are recorders, so a blink is only seen as a `light.turn_on` call with `flash: short` and the right target.

## What is covered

| Feature | Tests |
| --- | --- |
| Off equals 1.0.0 | the dimming step data is exactly `brightness_step_pct` and the light; a double press does nothing without a helper, and without switch positions |
| Fade | with the fade on the step data has `transition` equal to the interval (also with a negative step and a switched target); off, no `transition` |
| Switching | cycle 1, 2, 3, 1; an empty slot is skipped; fewer than two slots does nothing; no default slot does nothing; a helper with too few options stops at its last option; only a double press on a chosen button switches; own double actions and the scene cycle still run |
| The helper's state | unknown text, a fourth option, and an unavailable helper all mean slot 1 for a hold |
| The current target | a hold dims the target of the current slot (entity list, area, device, label, several areas); the legacy `dim_light` is slot 1; target 1 wins over it; the loop keeps its target when the helper changes during the hold, the next hold uses the new one |
| Blink | new target blinks with `flash: short` and the right target; can be switched off |
| Fall-back | leaving target blinks first and the default 1.5 s later (not at once); the timeout input and its default; every press restarts the countdown (also hold and release); nothing happens when already on the default; several quick switches give one confirmation sequence; works again after a fall-back; the switch going unavailable and unknown; a hold during the watch; the helper turning garbage, a fourth option, an empty slot or unavailable during the wait |
| Restart and compatibility | the event `homeassistant_started` puts the helper back without a blink; a press still works after it; without a helper no run happens (`last_triggered` stays empty); with only the inputs of a 1.0.0 setup the start trigger adds no listener, with a helper it adds one |
| Run limit | ten watchers fill the ten runs, the eleventh press is dropped |

The log check of 1.0.0 now also fails a test on warnings of Home Assistant's template logger (for example an index that does not exist). It found a real problem during development: an empty helper default used with `!input` in a service target makes the whole blueprint invalid.

## Timing

Whole seconds, and only moments at least 0.5 s from a boundary. A watcher's first delay is the whole timeout; a press at t=5 moves the fall-back to 13 s, which is why those tests look at 10 s and 14 s. The 1.5 s between the two fall-back blinks is checked at 0.4 s after the first blink (not yet) and 2 s later (done).

## What the harness cannot test (new in 1.1.0)

- That a real light blinks (`flash`) or fades (`transition`) as intended, and the stutter risk of the fade.
- A real restart with a real helper (the restart part is tested by firing `homeassistant_started`).
- Two watchers ending in the very same instant on a real instance (the gap between a watcher's check and its change of the helper).

## Mutation result (1.1.0)

131 tests pass and 1 is the strict xfail. 136 loadable mutants. The run took about 14 to 15 minutes (measured by the clock: 23:58 to 00:12; an earlier estimate of 25 minutes was too high) and prints only at the end.

- First run (before the review fixes): 126 killed, 9 survived, 93 %.
- After 5 new tests (the helper changing while a watcher waits) and the template logger added to the log check: 130 killed, 5 survived, 96 %.
- Last run, after the start-trigger fix (`enabled`) and its tests: **131 killed, 5 survived, 0 invalid, 96 %** of 136 mutants; the survivors are the same five (M016 = the old M015, M027, M028, M098, M117; the numbers moved by one because the trigger adds a mutant).
- The 4 survivors that were closed: `now_slot` with `<=` instead of `<` (and `slot_index` the same), and two `and` to `or` changes. They showed that nothing tested the helper turning garbage, a fourth option or an empty slot during the wait.

Remaining survivors, none a test gap I can close:
- `M015` (now M016) `default('', true)` to `false` for `event_type`: same as in 1.0.0, no visible effect.
- `M026`, `M027`, `M097` (the first `length > 0` of two redundant guards in the helper checks, mutated to `>= 0`): each guard is covered by the other one (with no helper the options list is empty too), so the changes alter nothing. The guard that is not redundant (`helper_options | length > next_slot`) is checked by hand: changing it to `>=` makes the test "a helper with too few options" fail.
- `M116` (dropping the `delay` of the watcher): the loop then spins without waiting and still ends at the right moment, because the harness clock only moves when the test moves it. So the frozen clock cannot tell a waiting loop from a busy loop. A real instance would burn CPU in that case; it is not detectable with this harness.
