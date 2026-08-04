# APC40 MkII DJ Template — Live 11 / Python 3

Will Marshall's APC40 MkII control surface script, ported from Ableton Live 9/10
(Python 2) to Live 11 (Python 3).

Lineage:

1. **Will Marshall** wrote the original script for his APC40 MkII DJ Template.
   It is no longer distributed anywhere. The pristine Python 2 sources are kept
   here under `reference/will-marshall-original/`.
2. **[apj72/AKAI_MPC40MKII_2025](https://github.com/apj72/AKAI_MPC40MKII_2025)**
   preserved those sources and started a Python 3 conversion, which is what this
   repository is forked from. It is kept under `reference/apj72-python3-port/`.
3. **This repository** carries the port through the Live 11 API changes and adds
   a way to check the result outside Ableton.

Everything you install lives in `APCAdvanced_MkII/`.

## Install

Copy the script folder into Live's user Remote Scripts folder and restart Live:

    ./install.sh

Or by hand — macOS:

    ~/Music/Ableton/User Library/Remote Scripts/APCAdvanced_MkII

Windows:

    %USERPROFILE%\Documents\Ableton\User Library\Remote Scripts\APCAdvanced_MkII

Then in Live: **Preferences → Link/Tempo/MIDI → Control Surface → APCAdvanced_MkII**,
with the APC40 MkII as both Input and Output.

## What the script does

On top of Live's stock APC40 MkII script:

- **Four-deck layout.** The left four columns drive a session that is offset to
  scene 3; the right four columns drive a second, fixed session for dummy clips.
- **Track select follows the playing clip.** Selecting a track jumps the Clip
  view to whatever is playing on it.
- **Pan / Sends / User encoder modes**, as stock, with the encoders behaving as
  pseudo-relative controls so they can be MIDI-mapped without value jumps.
- **FX on the scene launch buttons** — momentary control of the first eight
  parameters of a device named `Repeats` on the master track.
- **Volume meter on the scene launch buttons** in session mode, scaled to the
  top 40% of the meter range so it reads usefully while DJing.
- **DJ looping** on mute/crossfade buttons 5–8: loop on/off, set an 8-beat loop
  from the playhead, halve, double, move by a loop length, nudge by a bar.
- **Step sequencer** on the User button: a 4×4 drum pad area, a 4×4 step grid, a
  loop selector row, quantisation on the track stop buttons, a velocity column
  on the scene launch buttons, and playhead feedback on the pads.
- **Visual metronome** component (`StepperComponent`), built but not bound to a
  mode — as in the original.

### What is not included

The Live Set itself. The script expects a set that provides:

- a track named `Drums` holding a drum rack (the sequencer selects it and the
  master fader/select button control it)
- a track named `Stepper` if you wire up the visual metronome
- a device named `Repeats` on the master track for the FX buttons

Each of those is looked up by name and simply stays inactive when missing, so the
script loads fine without them.

## Porting notes

Python 2 → 3 was the small part. Live 11 replaced the Push components this script
was built on, so the substantive changes are:

- **`Push.*` → `pushbase.*`.** Live 11 has no `Push.StepSeqComponent`,
  `Push.NoteEditorComponent`, `Push.DrumGroupComponent`, `Push.GridResolution`,
  `Push.Colors` or `Push.SkinDefault`. They live in `pushbase` under snake_case
  names, and `PlayheadElement` and `AutoArmComponent` moved to `ableton.v2`.
- **Two frameworks, two injection registries.** `pushbase` is built on
  `ableton.v2`, which keeps its own dependency registry, while the stock APC40
  MkII script this subclasses is `_Framework`. A `pushbase` component built
  inside a `_Framework` control surface cannot resolve `song` or
  `register_component` and refuses to be constructed, so `component_guard()` now
  opens an `ableton.v2` injector as well. This is the load-bearing change.
- **`ableton.v2` components are tracked separately.** `_Framework` calls
  `on_selected_track_changed()` and friends on everything it registers, and
  `ableton.v2` components do not implement them, so they are kept out of
  `self._components` and updated, enabled and disconnected explicitly.
- **The step sequencer is wired from outside.** Live 11's `StepSeqComponent`
  takes `note_editor_component` and `instrument_component` as arguments instead
  of building them itself, and it no longer accepts `note_editor_settings`. The
  note editor, drum group and note settings are now created in
  `_create_sequencer()`, the way the stock Push script does it.
- **Modes are wrapped by hand.** `ModesComponent` recognises components with an
  isinstance check against `_Framework`'s base class, so a `pushbase` component
  dropped into a mode list is quietly treated as something that is not a mode and
  never enabled. On top of that, `LayerMode` only hands over a layer, and a
  disabled component grabs nothing from one, so the original's
  `(component, layer)` pairs became `ComponentLayerMode`, which assigns the layer
  and enables the component.
- **`DrumGroupFinderComponent` is gone from Live 11** and is reimplemented here
  on `ableton.v2`, following the selected track.
- **Velocity comes from a provider.** Live 11's note editor reads note velocity
  from an injected `velocity_provider`, so the scene-launch velocity column feeds
  `VelocityProvider` rather than overriding `_add_note_in_step`. Notes are
  created by Live through `Live.Clip.MidiNoteSpecification`, and note objects
  have `.velocity`/`.mute` where Live 9 passed tuples.
- **Pads switch modes differently.** `ableton.v2` flips pads between playing and
  reporting to the script via an element's `script_forwarding`, which
  `_Framework` elements do not have; `APCDrumGroupComponent` applies the
  equivalent `suppress_script_forwarding` instead.
- **`ConfigurableButtonElement` is gone.** RGB clip buttons are plain
  `ButtonElement`s tagged `is_rgb`, as the stock Live 11 script does it.
- **Colours by name.** `PPMeter` sent raw colour objects to buttons; Live 11
  button elements take skin colour names, so the meter's five steps are skin
  entries (`PPM.Step0`…`PPM.Step4`).
- **Clip colour table renamed** — `Push.Colors.CLIP_COLOR_TABLE` is now
  `APC40_MkII.Colors.LIVE_COLORS_TO_MIDI_VALUES`.
- **Python 3 proper:** `izip`/`imap`/`ifilter`/`xrange` removed, implicit relative
  imports made explicit, tuple-unpacking lambdas rewritten, `is -1` → `== -1`.

### Behaviour differences from the original

- The sequencer's shift button is mapped to the note editor's **mute button**.
  Live 11 has no `set_shift_button` on `StepSeqComponent`; the original's note
  editor read `self._mute_button` to enter muted notes, and shift was the only
  button in that layer that could have supplied it.
- Drum bank up/down move from the step sequencer to the drum group's
  `scroll_page_up_button` / `scroll_page_down_button`, which is where Live 11
  keeps them.
- Step colours use five velocity buckets, as before. Live 11 natively supports
  three, so `_determine_color` is overridden rather than the whole matrix update.

## Verifying it

Live ships its remote scripts as bytecode, so the API cannot be imported outside
Ableton. `tools/check.sh` works around that: it fetches a decompilation of Live
11's MIDI Remote Scripts, repairs the artefacts that stop it from importing,
imports this package against it, and runs the tests.

    tools/check.sh

That gives you:

- every import in the package resolved against the real Live 11 module tree
- every `super().method()` call checked against the actual base classes
- every keyword passed to a base constructor checked against its signature,
  following the whole cooperative `__init__` chain
- every `self._attribute` read checked against the class and its bases
- every entry in a mode list checked to be something `ModesComponent` can
  actually enter, and every `Layer` key checked to resolve to a handler on the
  component it is given to
- unit tests for the logic that changed — velocity buckets and their skin
  colours, four-wide triplet step layout, meter scaling, velocity provider,
  velocity column LEDs

**What it does not prove:** nothing here has been run on hardware. Live has not
loaded the script, no MIDI has moved, and the components have never been
instantiated — that needs Live 11 and an APC40 MkII. The checks catch the class
of failure that breaks these ports (renamed, moved and re-signatured API), not
mapping or feel.

## Layout

    APCAdvanced_MkII/                     the script — this is what you install
    install.sh                            copies it into Live's User Library
    tools/check.sh                        end-to-end verification
    tools/prepare_reference.py            makes a decompiled Live 11 tree importable
    tools/verify.py                       imports and checks the package
    tools/live_stub.py                    stand-in for Live's built-in module
    tests/test_logic.py                   unit tests
    reference/will-marshall-original/     the original Python 2 script, untouched
    reference/apj72-python3-port/         the partial port this is forked from

## Credit

Original script by **Will Marshall**. Preserved and first converted by
**[apj72](https://github.com/apj72/AKAI_MPC40MKII_2025)**. Live 11 port in
`APCAdvanced_MkII/`.
