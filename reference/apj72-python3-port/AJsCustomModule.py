from _Framework.DeviceComponent import DeviceComponent
from _Framework.EncoderElement import EncoderElement
from _Framework.ButtonElement import ButtonElement
from _Framework.InputControlElement import MIDI_CC_TYPE, MIDI_NOTE_TYPE

import itertools
import Live

# ---- GLOBAL FX (DEVICE KNOBS 20) ----
def create_device_knobs(channel=0):
    return [EncoderElement(MIDI_CC_TYPE, channel, cc, Live.MidiMap.MapMode.absolute)
            for cc in range(16, 24)]  # Knobs 1–8 in Device Control section

class GlobalFXComponent(DeviceComponent):
    def __init__(self, knobs, *a, **k):
        super(GlobalFXComponent, self).__init__(*a, **k)
        self._parameter_controls = knobs

# ---- LOOP CONTROL ----
def create_loop_pad(note, channel=0):
    return ButtonElement(True, MIDI_NOTE_TYPE, channel, note)

class LoopLengthController:
    def __init__(self, song):
        self.song = song

    def set_loop(self, bars):
        clip = self.song.view.detail_clip
        if clip and clip.is_midi_clip:
            clip.loop_start = 0
            clip.loop_end = bars
            clip.looping = True

def setup_loop_buttons(song, note_map):
    loop_ctrl = LoopLengthController(song)
    loop_pads = {}
    for bars, note in note_map.items():
        pad = create_loop_pad(note)
        pad.add_value_listener(lambda value, b=bars: loop_ctrl.set_loop(b) if value > 0 else None)
        loop_pads[bars] = pad
    return loop_pads

# --- Custom colour rotation. 
class ColorCycler:
    def __init__(self, button):
        self.button = button
        self.color_cycle = itertools.cycle(COLOR_CYCLE)
        self.button.add_value_listener(self._on_button_press)

    def _on_button_press(self, value):
        if value > 0:
            next_color = next(self.color_cycle)
            self.button.send_value(next_color, force=True)
# --- Custom colour rotation END