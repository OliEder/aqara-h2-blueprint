# Documentation friction log

Written by an agent that had only the harness documentation (`docs/index.md` and the pages it points to) and the wheel `ha_blueprint_test_harness-0.1.0`.
Each item: page, what I needed, what happened, what the page should say.

## Source looked at (the documentation failed)

1. `ha_blueprint_test_harness/env.py`, function `advance()` only (about 10 lines).
   - Needed: why a `wait_for_trigger` with `timeout: 1` fired after `advance(0.5)`.
   - Looked at: only `advance`; it ticks a freezer and calls `async_fire_time_changed`. I did not find the cause of the early firing in it. I did not read anything else.

## Problems

1. **writing-tests.md, "Let time pass" / "Things that surprise people": sub-second timing and early timers (serious).**
   - Needed: to test dimming with an interval below 2 s and to know how precise `advance()` is.
   - Happened: timers fire up to about 0.5 s EARLY. With a timeout of 1 s the next step came after `advance(0.5)`; with 4 s it came after 3.5 s (measured: `advance(0.4)` twice gave a step, `advance(0.1)` twice did not). I only found this by probing.
   - Page should say: "`advance()` is not exact below one second: a timer can fire up to 0.5 s early. Use whole-second delays and test at least 0.5 s away from the boundary." (My explanation, that this comes from Home Assistant's test time helper, is a guess.)

2. **writing-tests.md, "Let time pass": one `advance(n)` fires a repeating timer only once.**
   - Needed: to advance 3 intervals of a `repeat` loop in one call.
   - Happened: `advance(2)` over a 1 s loop gave one step, not two, because each next timer is set relative to the jumped clock. The page only says "advance in steps if the blueprint does something every few seconds"; it does not say what happens if you do not (it is silent loss, not an error).
   - Page should say so explicitly, with the numbers.

3. **writing-tests.md, `start()` table: `effects` function signature.**
   - Needed: what `call` is inside my own effect `f(hass, call)`.
   - Happened: I assumed `call.entity_ids` (as on recorded calls). It is Home Assistant's raw `ServiceCall` (`'ServiceCall' object has no attribute 'entity_ids'`). The error appeared only in the log; the test did not fail with it but with a wrong result later.
   - Page should say: "`call` is Home Assistant's `ServiceCall`; read the target from `call.data['entity_id']` (string or list)". An example effect that sets a timestamp state (scene-like) would help.

4. **writing-tests.md, `start()` text: "an unknown input ... raises BlueprintLoadError" is wrong.**
   - Happened: `start(BLUEPRINT, {"switch_entity": ..., "singel_left": []})` did not raise; the blueprint loaded and the extra input was ignored.
   - Page should say that misspelled input names are silently ignored (so a typo in a test input makes a test pass on the default). Same sentence appears nowhere else, but the claim is in the `start()` section.

5. **writing-tests.md / configuring-your-project.md: blueprints with input sections.**
   - Needed: whether inputs inside `input: section_x: input: {...}` are passed flat or nested.
   - Happened: guessed flat; it worked. Not documented.
   - Page should say: "Inputs inside sections are passed flat by their own name."

6. **writing-tests.md: how to fire a state-based event entity.**
   - Needed: how to simulate an `event` entity press (state = timestamp, attribute `event_type`).
   - Happened: `set_state(entity, state, attributes)` fits, but the page only shows `fire_event` for bus events. Nothing says that two presses must differ in state (a state trigger fires on a changed state, so I use a counter for the timestamp), nor that `set_state` with identical state and new attributes also triggers.
   - Page should have a short "event entities (Zigbee2MQTT buttons)" pattern.

7. **mutation-testing.md: running time.**
   - The first run of 73 mutants took about 3 min 15 s with 56 tests (the page gives 8, 18, 27 mutants but no time). The command was moved to the background by my tool after 180 s with no output until the end. Page should say that output only comes at the end, and give a rough time per mutant (about 2.7 s here).

8. **mutation-testing.md, "Not mutated": input defaults of numbers.**
   - It mutates defaults (+1, 0) and these survive when every test passes explicit values. The page mentions defaults in the table but not that this is the typical survivor; "reading a survivor" should list "defaults that tests never rely on" as the most common gap.

9. **mutation-testing.md: guards that only avoid log errors are always survivors.**
   - A guard like `{{ light | length > 0 }}` mutated to `>= 0` survives because Home Assistant itself rejects the empty target before the recorder. The page's "sometimes harmless" list could mention "a guard whose failure is rejected by Home Assistant anyway".

10. **configuring-your-project.md: `conftest.py` needs `expected_lingering_timers`.** The Getting started page shows a `conftest.py` WITHOUT it, the Configuring page WITH it. Getting started should show the full file when the blueprint uses a state trigger (mine does). I used the long form from the start, so I did not see the error.

## Worked well

- Getting started: the install, `pytest.ini` and `conftest.py` instructions worked as written; the wheel installed with `uv pip install` without trouble.
- `blueprint_env.start()` / `set_state()` / `calls_to()` / `call.entity_ids` were enough for almost everything; the API table is complete.
- "A service you forgot to list fails silently" warning is accurate and useful.
- The mutation tool needed no change to my tests, and its survivor list was precise enough to act on at once.
- `sets_state` and the whole `effects` idea made the light and scene simulation easy.
- Troubleshooting page: I did not need it (no error I could not solve), so I cannot judge it.

## Things the harness could not test

- Real device behaviour, the real Zigbee2MQTT message timing, `brightness_step_pct` against a real light (the recorder accepts any data), and real scene state semantics (my scene effect sets the timestamp state like Home Assistant does; that is an assumption).
- Sub-second timing (see problem 1).

# Round 2

Read again: docs/writing-tests.md, docs/mutation-testing.md and docs/examples/test_event_entity_light.py. No harness source was opened in round 2.

## Addressed in the harness docs since round 1 (checked by reading)

- Early timers and one-fire-per-advance: now in "Let time pass" with numbers (problem 1 and 2).
- `effects` receive Home Assistant's raw `ServiceCall` (problem 3).
- Misspelled input is ignored: now under "Things that surprise people"; the `start()` section no longer claims it raises (problem 4).
- Inputs in sections are passed flat (problem 5).
- Event entities: new pattern with a `press()` helper and "same timestamp is not a new press" (problem 6).
- Mutation run time and that output comes only at the end (problem 7). Problems 8 and 9 (untested defaults and guards as typical survivors): not checked again.

## New in round 2

1. **writing-tests.md / troubleshooting.md: logged errors do not fail a test, and `caplog.records` is empty in a teardown fixture.** A template error in a blueprint (division by zero, an invalid entity id) is only logged by Home Assistant; the test still passes. I added an autouse fixture that fails on warnings or errors of the automation logger. First attempt used `caplog.records` after `yield` and silently checked nothing (it only holds the teardown phase); `caplog.get_records("call")` is right. This cost one mutation run to find out (two survivors that should have been killed). The docs should recommend this fixture and the `get_records("call")` detail.
2. **writing-tests.md, effects: how to fire an event from inside a mocked service** (to test a race). My own `async def f(hass, call)` that calls `hass.states.async_set(...)` worked, but the page does not say whether state changes made from an effect trigger the automation and whether they run before the service "returns". They did. A short example would help.
3. **mutation-testing.md: the tool runs the test folder as it is on disk.** I changed tests while a run was in progress, so that run mixed old and new tests. A one-line warning would help.
4. **writing-tests.md: how to check the frozen clock from templates.** `utcnow()` in a template follows `advance()` (used for a time-based safety limit); this worked but is not stated. A template variable that holds a datetime becomes a string, so subtract timestamps (`as_timestamp`) instead; that is a Home Assistant fact, not a harness problem.

# Round 3 (version 1.1.0)

No harness source was opened. Home Assistant's own source was read once: the `homeassistant` trigger (to find out which event it listens to).

1. **writing-tests.md, "Real components": a component that needs configuration.** `components=["sun"]` works for components that need no configuration. For `input_select` (needs options) I used `async_setup_component(env.hass, "input_select", {...})` before `start()`, as the task said. It worked, and `blueprint_env.hass` is usable before `start()`. The page should say that this is allowed and show the three lines, including how to read the helper later (`env.hass.states.get(...)`) and how to change it like a user (`hass.services.async_call(..., blocking=True)`).
2. **writing-tests.md: events other than state changes.** Firing the real Home Assistant start needs the event `homeassistant_started` (the trigger `homeassistant: start` listens to that, not to `homeassistant_start`). Not harness-specific, but a harness user will try `fire_event("homeassistant_start")` and see silence. A one-line hint would help.
3. **writing-tests.md: autouse log check and `caplog.get_records("call")`** is still not documented (round 2 item 1). This time it caught a real problem at once: a blueprint input of selector `entity` with an empty default and `!input` in an action target is rejected at load ("expected 'all' or 'none'"). The failure showed only as a logged error, never as `BlueprintLoadError`. The page for `BlueprintLoadError` should say that a blueprint that is invalid after the inputs are filled in is logged, not raised, in some cases.
3a. Related: a test with an invalid blueprint did not raise at `start()`; all 82 old tests failed through the log check instead. Without that check they would have failed with "no calls", which is a confusing message.
4. **mutation-testing.md: timeout.** With 123 tests a run took more than 8 minutes. The `--timeout` default of 120 s per test run was enough; I set 90. The page's remark about "about 3 minutes" should scale with the number of mutants times the test time.
