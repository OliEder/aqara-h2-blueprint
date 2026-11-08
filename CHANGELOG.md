# Changelog

All notable changes to this blueprint are listed here, in the style of [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- Switchable dimming target (optional, off by default): a double press on chosen buttons switches which lights a hold dims, using one `input_select` helper and up to three targets (lights, areas, devices or labels). The new target blinks; after a time without any press the default target is used again, with a blink of the target that is left and then of the default. A Home Assistant start puts the helper back to the default (this trigger only exists when a helper is configured). New inputs: helper, buttons, targets 1 to 3, fall-back time, blink on/off.
- Smooth fade (optional, off by default): every dimming step can send a transition as long as the interval.

With all new inputs at their defaults the blueprint behaves as 1.0.0. The blink and the fade were not tried on a real light.

## [1.0.0] - 2026-11-07

First release.

### Added

- A state trigger on the `event` entity of an Aqara H2 double rocker wall switch connected through Zigbee2MQTT (needs Home Assistant 2024.10 or newer).
- 16 optional action inputs: single, double, hold and release for the four positions `left`, `left_down`, `right`, `right_down`, grouped by button; the gestures that the tested device never sent are in a collapsed group "Actions: other models".
- Dimming of one light while a button is held, with step size, interval and a safety limit; it ends at the matching release, when the switch becomes unavailable or unknown, or at the limit. A release that arrives during the light call is not lost.
- A stateless scene cycle on a double press (the scene with the newest activation time is found and the next one in the list is activated).
- Protection against replaying the last press when the switch entity returns from `unavailable`; the first press after a restart works.
- Known limit: two releases that both arrive during one slow light call can leave one dimming loop running until the safety limit.
- Tests with `ha-blueprint-test-harness` and a mutation score of 99 % (71 of 72 loadable mutants killed; the survivor is equivalent). Device behaviour was observed on one device, not confirmed by the vendor.
