# Design decisions

## One state trigger on the event entity

The blueprint triggers on a `state` change of the switch's `event` entity and reads `trigger.to_state.attributes.event_type`. MQTT triggers and `device` triggers are not used: the test tool (`ha-blueprint-test-harness`) cannot simulate them, and the event entity is what Zigbee2MQTT already offers in Home Assistant. A state trigger also needs no device id, so the blueprint has no hard-coded ids.

The trigger has `not_from: unavailable` and `not_to: [unavailable, unknown]`. The entity returns from `unavailable` with its old timestamp and old event type; without the guard the last press would run again (observed, see [device-behaviour.md](device-behaviour.md)). `unknown` is deliberately not excluded as the old state, because the first press after a restart comes from `unknown`.

## mode parallel, max 10

A hold keeps one run busy (the dimming loop) while its release must start a run of its own, so `single` or `restart` would drop or kill runs. `parallel` allows it. `max: 10` caps simultaneous runs; further triggers are dropped with a warning. A test checks that the eleventh hold is dropped.

## Generic actions

16 optional `action` inputs, one per position and gesture, are dispatched by a `choose` on the event type. They are grouped by button. The inputs for hold, double and release on the upper buttons were never seen sent by the tested device; they are kept, in a collapsed group "Actions: other models", because other models or firmware may send them.

## The dimming loop and the lost-release race

A hold starts the loop: one `light.turn_on` with `brightness_step_pct` (negative to dim down), then a `wait_template` with a timeout of one interval, repeated.

- The first design used `wait_for_trigger`. It only listens after `light.turn_on` returned, so a release that arrives while the call is running (possible: one device sent a release 0.44 s after the hold) was lost and dimming ran to the safety limit. `wait_template` looks at the current state first, so such a release ends the loop. A test fires the release from inside the mocked light call, and fails with the old design.
- The wait template is true when `event_type` equals `release_<position>` or the switch is `unavailable`/`unknown`. Other presses do not satisfy it, so they neither stop the loop nor cause an extra step.
- The safety limit is measured in real time: the start timestamp is stored and compared with the current time after each wait.
- If the release never arrives, the loop ends at the limit (default 15 s). A `hold` is expected to be followed by a `release`, but this is not guaranteed.
- If Home Assistant restarts, the run ends with it.
- Brightness limits: the blueprint sends the step and does not read the light's brightness. What happens at 0 % or 100 % is up to the light and not tested.

## Known limit: two releases during one slow light call

`wait_template` looks at the CURRENT state of the switch, which is only the latest event. Case: two rockers are held (`hold_right_down`, then `hold_left_down`), and while the left loop's first `light.turn_on` is still running, both `release_left_down` and `release_right_down` arrive (measured about 0.2 s apart). Afterwards the left loop only sees `release_right_down`, never ends at its own release, and dims until the safety limit (default 15 s). The right loop ends correctly. The same can happen when any other event arrives right after a release while a light call is still running. It needs a light call slower than the gap between the two events (about 0.2 s), so it is narrow. A test reproduces it (`test_known_limit_...`, plus a strict `xfail` test for the wanted behaviour). I did not change the logic for it.

A real fix needs memory of events, that is an event queue or a helper, which this blueprint avoids. The cost today is bounded: extra dimming for at most the safety limit.

Options for a fix, for the maintainer to choose:
1. End a loop on ANY release event seen after its start (fails safe; but a release of the other rocker then also ends this rocker's dimming while it is still held).
2. Run the dimming in a separate script with `mode: restart` per position: a new hold of that position replaces the old loop, and a release calls a stop. More moving parts, two files to install.
3. A helper per position (for example an `input_boolean` set by the release) that the loop reads: exact, but the user must create helpers.
4. Compare the timestamp of the last release event of the position instead of the latest event: needs a place to keep it, so again a helper.

## Several positions at once

Observed on one device: events of other positions can arrive before or during a held position, and the hold event itself comes only when the hold threshold is reached, so the blueprint never assumes that a hold comes first. Each hold starts its own run and its own loop, and each loop waits only for the release of its own position. Two held rockers therefore mean two parallel loops on the light: with opposite directions they cancel out step by step, and with the same direction the light gets two steps per interval. That is intended and tested; the loops end independently at their own releases. Other presses never end a loop and never cause an extra step.

## Defaults and the down positions

On the tested device only the lower buttons send hold, double and release. So the defaults are: hold on `left_down` dims up, hold on `right_down` dims down, double press on `right_down` cycles scenes. Nothing happens until a light or scenes are chosen. The positions can be changed to any button for other models.

## Stateless scene cycle, with a tie rule

A scene entity's state is the time of its last activation. The blueprint finds the scene of the list with the newest time and activates the one after it, wrapping around. If none has a time, the first is used. A state that is not a time (unknown, unavailable, text) counts as never activated. On equal times the earlier scene in the list counts as the last one used, so the next one follows it. No helper is needed, so there is nothing to create, name or keep in sync, and the state survives restarts because the scene entity keeps it. A weakness: a scene activated by anything else also counts as "last".

## Minimum version

`min_version: 2024.10.0`. Checked in the Home Assistant release notes (home-assistant.io blog) on 2026-11-07:
- 2024.6: "collapsible sections" for blueprint inputs;
- 2024.8: the action key `service` is now called `action`;
- 2024.10: `trigger:` became `triggers:` and `platform:` became `trigger:`.

The highest of these is 2024.10. Not verified: the `as_datetime(value, default)` template function, `wait_template` with a templated `seconds` timeout and `not_from`/`not_to` on older versions; they are only tested with 2026.10.4. I believe they are older than 2024.10, which is not checked.

## Why no helper, and why hand-maintained YAML

No `input_*` helper: the scene cycle reads state that already exists. The YAML was first produced with a script; it is now maintained by hand and the script is not kept (it was not clean enough to be worth keeping).

## Ideas not built: smoother dimming

Planned for 1.1.0, tracked in [issue 1](https://github.com/OliEder/aqara-h2-blueprint/issues/1). The first version was kept as it is because it works.

With the defaults, dimming sends 10 % every second, and the light jumps from step to step. Setting a smaller step and a shorter interval (for example 5 % every 0.5 s) is a configuration change and was the first thing tried. Three further ways, none built or tried:

1. **Fade each step.** Send `transition` equal to the interval with every step, so that the light ramps to the next value. Risk: Home Assistant computes `brightness_step_pct` from the brightness the light **last reported**. If the light reports only at the end of the fade, the next step is computed from a stale value and the dimming can stutter. This can be judged only on the real light.
2. **Let the light dim itself.** Zigbee2MQTT knows a `brightness_move` command (the light ramps until a `stop` arrives). It gives a smooth ramp with little radio traffic, but the blueprint would have to publish MQTT messages (a new input for the light's topic), and the test tool cannot simulate MQTT.
3. **Smaller steps at a higher rate.** For example 3 % every 0.3 s. More radio traffic; whether the light and the mesh keep up was not checked.


# Version 1.1.0

Both features are opt-in. Every new input has a default, no input of 1.0.0 was renamed or removed, and with all new inputs at their defaults the blueprint behaves as 1.0.0 (the 82 tests of 1.0.0 pass unchanged, and a dimming step still sends exactly `brightness_step_pct`).

## Switchable dimming target

**Idea.** A hold dims one set of lights. A double press on chosen buttons switches the set; the new set blinks; after a few seconds without any press the default set is used again, with a blink of the set that is left and then of the default.

**State lives in one `input_select` helper, nowhere else.** The current target must survive between runs (the hold and the double press are different runs) and a Home Assistant restart, and a blueprint has no variables of its own. The helper is the smallest thing that does this; it keeps its state over restarts, is visible and can be reset by hand, and other automations can read it. Option number i of the helper stands for target slot i (the helper's `options` attribute is read at run time). Why only one helper: the inactivity watcher needs no second one, because the switch's own event entity already says when the last press was (its `last_changed`).

**Options for the slot mapping that were considered.** (1) Slot i = i-th option of the helper (chosen: the option names are free, the user only orders them). (2) Match option names to fixed words such as `default`, `strip`: fragile and needs documentation of magic words. (3) One helper per slot: more helpers for no gain. If the helper's state is not one of its options, or is beyond the third option, or names an empty slot, slot 1 is used.

**Slot 1 is the default.** It is `dim_target_1`; if that is empty it is the old `dim_light`, so a 1.0.0 setup keeps working. Switching needs the helper, slot 1 filled, at least one more filled slot, and a helper option for the next slot. Empty slots are skipped. `target` selectors accept lights, areas, devices and labels; the whole `target:` of the service call is a template (`"{{ hold_target }}"`), which Home Assistant accepts (tested).

**A hold reads the target once.** The current slot is computed when the run starts (a top-level variable). The loop keeps that target even if the helper changes during the hold; the next hold uses the new one. This is tested.

**The inactivity watcher.** After a switch the same run waits: it computes the time since `last_changed` of the switch entity, waits the rest of the timeout with a `delay`, and repeats until the whole timeout has passed. Every press of the switch changes the entity's state, so every press (also a hold, a release, an unavailable state) counts as activity and moves the fall-back later. Activity is per switch entity: with several switches, presses on another switch do not count. At the end the current slot is read FRESH from the helper. If it is not slot 1, the helper is set to option 1 FIRST, then the leaving target blinks, 1.5 s later the default blinks.

**Idempotence.** Several watchers can exist (every double press starts one). All of them end at about the same moment and read the helper fresh. The first sets the helper to the default before it blinks, so the others find the default and do nothing: one confirmation sequence in total (tested with two quick switches). There is a theoretical gap between a watcher's check and its change of the helper (two watchers ending in the same instant could both pass the check); in the tests this did not happen, but it is not excluded for a real instance. If you change the helper by hand while a watcher runs, the watcher acts on what it finds.

**Cost of the watchers.** Each watcher occupies one of the 10 parallel runs (`max: 10`) for up to the timeout (default 8 s, up to 60 s). Ten quick double presses fill all runs and the next press is dropped with a warning; holds also need a run. This is tested.

**Restarts.** The helper keeps its state over a restart; running watchers are lost. Without handling, a switched target would stay until the next press or a manual reset. Clean handling was found: a second trigger on `homeassistant` `started` runs a part that sets the helper back to option 1 (no blink) when it is configured and not already on option 1. The trigger carries `enabled: "{{ helper_configured | length > 0 }}"`, with the helper bound in `trigger_variables`, so it only EXISTS when a helper is configured: a setup without the helper has the single state trigger of 1.0.0 and no extra run, trace or `last_triggered` after a restart (a first version had the trigger always on; a review found that this broke the compatibility rule, and tests now check it through the bus listener count and `last_triggered`). `enabled` with a template over `trigger_variables` worked in the harness on Home Assistant 2026.10.4. The event type is empty for this trigger, so none of the other parts reacts to it. (The `homeassistant` trigger fires on `homeassistant_started`; the tests fire that event.) A restart in the middle of a switch is not tested on a real instance.

**Blink.** `light.turn_on` with `flash: short` on the targeted lights. It is a service call that was only checked in the harness for target and data; lights without flash support will not blink, and it was not tried on a real light. It can be switched off (`dim_target_blink`), then switching and the fall-back still happen silently.

**Deviation from the task text.** None in behaviour. One detail: the helper entity is given to the services as a template (`"{{ dim_target_helper }}"`) rather than `!input`, because an empty default would be rejected by Home Assistant at load time ("expected 'all' or 'none'"), and the helper is empty when the feature is off.

## Smooth fade

`dim_fade` (default off). On: the step data also has `transition` equal to the interval in seconds. Off: the data is exactly `{brightness_step_pct}`. Risk, from the issue text: the next step is computed from the last REPORTED brightness; a light that reports its brightness only when the fade has finished can make the dimming stutter. Not tried on a real light; the harness only shows the data of the service call.

## Minimum version

`min_version: 2024.10.0`, unchanged. What was checked, on 2026-11-07, in the Home Assistant release notes and docs (web pages, not an old installation):
- verified: sections (2024.6), the action key `action` (2024.8), `triggers:`/`trigger:` (2024.10): the highest is 2024.10; `enabled` on triggers, conditions and actions (2022.5 release notes).
- NOT verified (I found no version number): that `enabled` accepts a template and since when; since when `trigger_variables` exist; the version of `homeassistant` trigger `event: start`, `flash` in `light.turn_on`, `input_select.select_option`, and a template as the whole `target:` of an action. The docs page for triggers describes `enabled` templates and `trigger_variables` as current features. I believe all are older than 2024.10, but I cannot claim it. If one of them is newer, 1.1.0 would not load on a Home Assistant between 2024.10 and that version. Everything is tested only with 2026.10.4.
