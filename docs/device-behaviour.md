# Device behaviour (measured)

Everything here was **observed on one Aqara H2 double rocker via Zigbee2MQTT in Home Assistant on 2026-11-07. It is not confirmed by the vendor.**

## Method

The event entity of the switch (an `event` entity) was read from the recorder's history: every press is a state change whose state is a timestamp and whose attribute `event_type` names the press. Times below are seconds after the first hold of a sequence. To repeat: press the button in the way described, then read the entity's history (Developer tools or the history panel, or the recorder database) and note state timestamps and `event_type`. Entity names are left out on purpose. The recorder writes in batches, so the history can lag by up to about a minute: read the entity's current state and check that its timestamp matches the last row of the history before concluding that nothing arrived.

## Setup of the tested switch

- Both rockers in decoupled operation mode (relays do not switch by themselves).
- Multi-click was on for both lower buttons; Zigbee2MQTT offers the multi-click setting only for `left_down` and `right_down`.
- Both are device settings in Zigbee2MQTT, not something a blueprint can set.

## What was seen sent

The entity's `event_types` lists 16 values (hold, single, double, release x left, left_down, right, right_down). Coverage over the whole day of measuring: seen are `single` on all four positions, and `double`, `hold` and `release` on `left_down` and `right_down`. The six types `double`, `hold` and `release` on `left` and `right` (the upper rockers) were **not seen sent by the tested device; Zigbee2MQTT lists them as possible event types**, despite repeated deliberate attempts (3 s hold, fast and slow double click, both rockers).

| Position | single | double | hold | release |
| --- | --- | --- | --- | --- |
| left (upper) | yes | not seen | not seen | not seen |
| right (upper) | yes | not seen | not seen | not seen |
| left_down (lower) | yes | yes | yes | yes |
| right_down (lower) | yes | yes | yes | yes |

For the upper buttons a 3 s hold and a fast double click produced no event at all (not even a single). Normal short presses produce `single_left` / `single_right`.

## Measured sequences

| Sequence | Result |
| --- | --- |
| hold_left_down, then release_left_down | hold at 0.0 s, release at 1.78 s, nothing in between |
| hold_right_down, then release_right_down | hold at 0.0 s, release at 0.44 s (a short hold) |
| a 10 s hold on left_down | ONE hold (0.0 s) and ONE release (10.22 s), no repeated hold events |
| double on left_down | `double_left_down` arrives alone, 2.4 s after a release; no `single_left_down` before it |
| double on right_down | `double_right_down` arrives alone, no `single_right_down` before it. Double press therefore works on BOTH lower buttons. |
| double_left_down, then a press on right_down | `double_left_down`, then `single_right_down` 0.23 s later: two separate events with their own timestamps, in order, nothing lost. Different rockers are reported independently. |
| hold left_down, tap right_down during the hold | `single_right_down` at 0.00 s, `hold_left_down` at 0.20 s, `release_left_down` at 2.68 s (2.48 s after the hold). The release still arrives, the tap arrives as its own event, nothing lost. The order is NOT press order: the tap was reported BEFORE the hold, because the hold event comes only when the hold threshold is reached. |
| both lower rockers held at once | `hold_right_down` 0.00 s, `hold_left_down` 0.21 s, `release_left_down` 4.79 s, `release_right_down` 4.98 s. Each rocker delivered its own hold and release, nothing lost. Right was held first and left released first. |
| any single | a `single_*` was never followed by a `release_*` |
| rapid presses of different rockers, 0.6 to 1.0 s apart | all delivered as separate events, each with its own timestamp |

## Upper buttons: what produced nothing

Four attempts at a double click on the upper buttons (both rockers; fast, about 0.3 s apart, and slow, about 0.8 s apart) produced NO event at all, not even a `single_*`. A 3 s hold on an upper button also produced nothing. Isolated short single presses on the upper buttons do arrive as `single_left` / `single_right`, also two of them about 1.7 s apart.

Hypothesis, **not verified and not used by the blueprint**: an upper rocker reports only a cleanly isolated single press; when a second press or a long press follows, it reports nothing at all. To test it: press twice briefly with a gap of 1.5 s, and press once followed 3 s later by another press, and read the history after each try. The exact gap at which two single presses on an upper rocker are both delivered is open.

## Availability

The event entity goes unavailable now and then (a few times per week) and comes back with the OLD timestamp state and the OLD `event_type`. A state trigger that does not exclude this would replay the last press. The first press after a restart comes from the state `unknown` and must work.

## Spacing of events (a hint, not a fact)

Eight pairs of presses on two rockers at the same time were measured, with 0.20 to 0.23 s between the two events. They covered up and down rockers: left_down then right (0.20 s), right_down then left (0.21 s), left then right (0.20 s), left_down then right_down (0.20 s), plus the earlier tap-during-hold, double-then-single and two-holds sequences. The device or Zigbee2MQTT appears to deliver events of different rockers about 0.2 s apart. Which one comes first does not follow which was pressed first. Two short presses on the same upper rocker 2.28 s apart both arrived.

## Not observed

- The exact gap at which two single presses on an upper rocker are both delivered, and the cause of the missing events on the upper buttons (see above).
- Holds longer than 10 s, and the exact hold threshold.
- Whether another model behaves the same.
- What the upper rockers do with hold and double (nothing was delivered in four attempts).
- Whether the upper positions send hold or double on other models or firmware. The Zigbee2MQTT documentation of the single rocker model WS-K07E lists hold, double and release for up and down; that was not tested.
