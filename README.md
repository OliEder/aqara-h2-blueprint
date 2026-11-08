# Aqara H2 wall switch blueprint

This Home Assistant automation blueprint lets you configure every button press of an Aqara H2 double rocker wall switch that is connected through Zigbee2MQTT. For each button and gesture you can run any actions. Built in are dimming a light while a button is held, and cycling through a list of scenes with a double press.

**New in 1.1.0 (both optional, off by default; see [CHANGELOG.md](CHANGELOG.md)):** a double press can switch which lights a hold dims (with a blink and an automatic fall-back), and the dimming can fade smoothly. With the new inputs left at their defaults the blueprint behaves exactly as 1.0.0.

[![Open your Home Assistant instance and show the blueprint import dialog with this blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FOliEder%2Faqara-h2-blueprint%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Faqara_h2_switch.yaml)

The button opens the import dialog of your own Home Assistant with this blueprint filled in. It works through My Home Assistant: you must have stored the address of your instance at [my.home-assistant.io](https://my.home-assistant.io) once (the data stays in your browser), and your Home Assistant must have the `my` integration, which is part of the default setup. The first time, My Home Assistant asks for that address. Without the button, follow the steps below.

## Requirements

| What | Detail |
| --- | --- |
| Home Assistant | 2024.10 or newer (`min_version: 2024.10.0`; for the 1.1.0 features the exact minimum is not verified, see the design notes). How this was checked is in [docs/design.md](docs/design.md#minimum-version). |
| Zigbee2MQTT | The switch must appear in Home Assistant as an `event` entity (for example `event.hall_h2_switch_action`). |
| Switch mode | Observed on one device: both rockers were in **decoupled** operation mode (the relays do not switch by themselves) and **multi-click** was on for the lower buttons during all measurements. Both are device settings in Zigbee2MQTT, not in Home Assistant; find them in the device's page in the Zigbee2MQTT frontend (which tab holds them was not checked). The blueprint cannot set them. Assumed, not tested: without multi-click no double press is sent (it was never measured with multi-click off). |

## Which button is which

Zigbee2MQTT names four positions: `left`, `left_down`, `right`, `right_down`. We read `left_down` as the lower button of the left rocker and `left` as its upper button. This is inferred from the naming, not confirmed by the vendor.

## Import and set up, step by step

1. Click the button above, or in Home Assistant open Settings, Automations & Scenes, Blueprints, "Import Blueprint", and enter `https://github.com/OliEder/aqara-h2-blueprint/blob/main/blueprints/automation/aqara_h2_switch.yaml`. Home Assistant remembers the address, so a later "Re-import blueprint" picks up fixes. (Or copy the file into `config/blueprints/automation/`.)
2. Click "Create automation" on the blueprint.

   ![The form for a new automation: the blueprint, its description and the option groups](docs/images/create-automation-form.png)

   The form after "Create automation" (screenshot from 2026-11-07, German user interface, nothing selected yet): the blueprint, then one group of options per button, and the groups for dimming and the scene cycle.
3. Pick the event entity of your switch (an entity whose name ends in `_action` and whose domain is `event`). Do not pick a sensor or a device.
4. Open the groups you need and fill in only those; everything else stays empty and does nothing.
5. Save. Press a button and look at the automation's trace to see what ran.

## The inputs

Everything is optional except the switch entity.

| Group | Input | What it does | Default | Example |
| --- | --- | --- | --- | --- |
| (top) | Switch event entity | The switch's `event` entity | none, required | `event.hall_h2_switch_action` |
| Actions: left | Single press on left | Your actions on `single_left` | empty | toggle `light.hall` |
| Actions: right | Single press on right | Your actions on `single_right` | empty | |
| Actions: left, down | Single, Double, Hold, Release on left, down | Your actions on `<gesture>_left_down` | empty | |
| Actions: right, down | Single, Double, Hold, Release on right, down | Your actions on `<gesture>_right_down` | empty | |
| Actions: other models | Hold, Double, Release on left and right | Your actions on those 6 events. The tested double rocker was never seen to send them; other models or firmware may. | empty | |
| Dimming (hold) | Light to dim | The light that is dimmed | empty (dimming off) | `light.hall` |
| | Hold dims up | Buttons whose hold raises the brightness | `left_down` | `left_down` |
| | Hold dims down | Buttons whose hold lowers it (up wins if a button is in both lists) | `right_down` | `right_down` |
| | Step size | Percent per step | 10 | 5 |
| | Interval | Seconds between steps | 1 | 0.5 |
| | Safety limit | Seconds after which dimming stops even without a release | 15 | 20 |
| | Smooth fade (new in 1.1.0) | When on, every dimming step also sends a transition as long as the interval | off | on |
| Dimming target (switchable) (new in 1.1.0) | Helper that holds the current target | An `input_select` helper; option 1 is target 1, option 2 target 2, option 3 target 3. Empty turns the feature off. | empty | `input_select.hall_dim_target` |
| | Double press switches the target | Buttons whose double press switches to the next target | none | `right_down` |
| | Target 1 (default target) | Lights, areas, devices or labels. If empty, "Light to dim" is target 1 | empty | area `hall` |
| | Target 2, Target 3 | More targets; an empty one is skipped | empty | `light.hall_strip` |
| | Fall back after | Seconds without any press of the switch, then the default target is used again (2 to 60) | 8 | 8 |
| | Blink the target | Blink the lights of a target when selected or left (`flash: short`) | on | on |
| Scene cycle (double press) | Scenes | The scenes, in order | empty (cycle off) | `scene.hall_bright`, `scene.hall_evening`, `scene.hall_night` |
| | Double press cycles scenes | Buttons whose double press activates the next scene | `right_down` | `right_down` |

Dimming and the scene cycle run in addition to your own actions for the same press.

## Examples

**A. Hold the lower left button to dim the hall light up, the lower right button to dim it down.**
Light to dim: `light.hall`. Hold dims up: left, down. Hold dims down: right, down. Step 10 %, interval 1 s (the defaults). Nothing else.

**B. Double press on the lower right button cycles three scenes.**
Scenes: `scene.hall_bright`, `scene.hall_evening`, `scene.hall_night`. Double press cycles scenes: right, down (the default).

**D. Switchable dimming target (new in 1.1.0).** The hold on the lower left button dims the hall ceiling spots; a double press on the lower right button switches to the hall strip, then to the two table lamps, then back to the spots. The new target blinks.
1. Create a helper: Settings, Devices & services, Helpers, "Create helper", "Dropdown" (`input_select`). Name it `hall dim target` and give it three options in this order: `spots`, `strip`, `lamps`. The entity is `input_select.hall_dim_target`.
2. In the blueprint: Dimming (hold): Hold dims up = left, down; Hold dims down = left (upper) or none; "Light to dim" may stay empty.
3. Dimming target (switchable): helper `input_select.hall_dim_target`; Double press switches the target = right, down; Target 1 = the light `light.hall_spots`; Target 2 = the light `light.hall_strip`; Target 3 = `light.hall_lamp_a` and `light.hall_lamp_b`; Fall back after = 8 s; Blink = on.
4. Use: double press the lower right button (the strip blinks), hold the lower left button (the strip dims). After 8 s without any press the strip blinks, then the spots blink, and the spots are the target again.
A 1.0.0 setup that only has "Light to dim" keeps working: that light is target 1.

**C. Both, plus your own action.**
Examples A and B together; in "Actions: left, down" set "Single press" to a "Toggle" action on `light.hall`.

## What the blueprint does not do

- It does not change device settings (decoupled mode, multi-click, LED, relay, child lock). Those are Zigbee2MQTT device settings; a blueprint reacts to events and has no access to them.
- It does not switch the relays: in decoupled mode the buttons only send events.
- It does not use MQTT or device triggers, because the test tool cannot test those; see [docs/design.md](docs/design.md).

## Known limits

- **Safety limit:** a `hold` is expected to be followed by a `release`. If the release message is lost, dimming stops at the safety limit (default 15 s of real time).
- **Parallel runs:** the automation allows 10 runs at the same time (`mode: parallel`, `max: 10`); further presses at that moment are dropped with a warning in the log. A hold uses one run until its release.
- **Switch goes unavailable** during a hold: dimming ends at once. After the entity comes back with its old timestamp and event type, that old press is ignored, so it is not replayed. If Home Assistant restarts during a hold the run ends with it.
- **Two releases during one slow light call:** the dimming wait looks at the latest event of the switch only. If two rockers are held, and BOTH releases arrive while one light call is still running (the call must be slower than the roughly 0.2 s between the two events), the loop of the first release never sees its own release and dims until the safety limit (default 15 s). Narrow, but reproduced in a test. Options for a fix are in [docs/design.md](docs/design.md#known-limit-two-releases-during-one-slow-light-call).
- **Switchable target:** the state lives in the helper only. Each watcher that waits for the fall-back occupies one of the 10 parallel runs for up to the timeout; many quick double presses can fill them (further presses are dropped with a warning). A restart of Home Assistant loses running watchers, so the blueprint also puts the helper back to option 1 when Home Assistant has started (no blink). The activity that restarts the countdown is counted per switch entity, not across several switches. A helper with fewer options than filled targets cannot reach the extra targets. If you change the helper by hand while a watcher runs, the watcher finds the default (or another target) and acts on that.
- **Brightness limits:** each step sends `brightness_step_pct`; what a light does at the minimum or maximum is up to the light. Not checked on a real light.
- **Timers:** steps are timed by Home Assistant; very short intervals (0.1 s) depend on how fast your light answers.
- **Smoothness of dimming:** with the defaults (10 % every second) the light visibly jumps from step to step. On the maintainer's ceiling light, 5 % every 0.5 s was set and looked better (a judgement by eye, not measured). A fading mode (`transition` per step) and the light's own move command are not built; they are planned for 1.1.0 ([issue 1](https://github.com/OliEder/aqara-h2-blueprint/issues/1)); see [docs/design.md](docs/design.md#ideas-not-built-smoother-dimming).

## What was verified and what was not

- Device facts come from one Aqara H2 double rocker on one day (2026-11-07), not confirmed by the vendor; see [docs/device-behaviour.md](docs/device-behaviour.md).
- The blueprint logic is tested in a throw-away Home Assistant with the test tool; see [docs/testing.md](docs/testing.md).
- **Measured on the device and replayed in the tests:** a 10 s hold, two rockers held at the same time, a tap during a hold, double then single on the other rocker.
- **Used on a real instance:** on 2026-11-07 the maintainer installed the blueprint on one Home Assistant instance, for one Aqara H2 double rocker through Zigbee2MQTT, with a ceiling light, a reading light and a closet light, a light strip (not reachable at that time), a blind and an "all lights" action, and reported that the buttons did what was configured. That was a manual check by one person; there is no recording of it, the automation traces of the last five single presses showed no errors, and the dimming runs were not looked at in detail.
- **Not verified for 1.1.0:** the blink on a real light (the tests only show that the service is called with the right target and `flash: short`; lights without flash support will not blink), the smooth fade on a real light (risk: the next step is computed from the last reported brightness, so a light that reports only after the fade can stutter), and both features on a real Home Assistant instance. The tests use the real `input_select` component in a throw-away Home Assistant.
- **Not tested:** the light strip (it was not reachable); dimming on other lights; running for weeks; holds longer than 10 s on the device; a Home Assistant restart in the middle of a hold; both releases arriving during a slow light call (known limit above, covered only by a simulated test); older Home Assistant versions than 2026.10.4 (`as_datetime` with a default, templated `wait_template` timeout).

## Run the tests

```sh
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -m pytest
# the mutation tool breaks the blueprint in 136 small ways and runs the tests for each: about 7 minutes with 4 jobs on an
# 8-core Mac (about 15 minutes one after the other); it prints a line for each mutant as it goes
.venv/bin/python -m ha_blueprint_test_harness.mutate blueprints/automation/aqara_h2_switch.yaml --jobs 4 --timeout 180 \
  -- .venv/bin/python -m pytest -q -x -p no:cacheprovider tests
```

## Checks on every change

`.github/workflows/ci.yaml` runs on every push to `main`, on every pull request and once a week:

- **tests**: the tests with the pinned test tool and Home Assistant test package (`requirements-dev.txt`, locked with hashes in `requirements-dev.lock`). This is the reproducible check.
- **mutation**: the mutation tool breaks the blueprint and fails if the tests stop noticing. The floor is 97 % (133 of 136 killed on 2026-11-09, the three survivors are explained in [docs/testing.md](docs/testing.md)).
- **tests (latest harness release)**: the same tests with the newest release of the test tool instead of the pinned one. It is an early warning: when it fails while **tests** is green, a newer release needs a change here (or in the tool) before the pin is moved. The weekly run notices a new release even when nobody changes this repository.

To move to a newer release of the test tool: put its wheel URL and the hash from its `SHA256SUMS` file into `requirements-dev.txt`, run `uv pip compile requirements-dev.txt --generate-hashes --python-platform x86_64-unknown-linux-gnu --python-version 3.14.3 -o requirements-dev.lock`, run the tests and the mutation tool, and commit both files. The actions in the workflow are pinned to commit ids; Dependabot proposes updates (check that the id belongs to the version in the comment).

## Maintenance, credits, licence

The YAML is maintained by hand (a script produced the first draft, which is not kept). Credits: Zigbee2MQTT event naming; tests built with `ha-blueprint-test-harness`. Licence: MIT, see [LICENSE](LICENSE). It covers every file in this folder (the blueprint, the tests and the documents). The blueprint file also carries the licence in its first lines, so that it stays licensed when it is copied on its own.

## More documents

- [docs/device-behaviour.md](docs/device-behaviour.md) measured device events
- [docs/design.md](docs/design.md) decisions and reasons
- [docs/testing.md](docs/testing.md) what is tested, what is not, mutation result
- [docs-friction.md](docs-friction.md) notes on the test tool's documentation
