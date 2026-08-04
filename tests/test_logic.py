"""Unit tests for the parts of the script that hold real logic.

Run with a prepared Live 11 reference tree on the path:

  LIVE11_REFERENCE=/path/to/prepared/tree python3 -m unittest discover tests
"""
import unittest

import live_env  # noqa: F401 - puts Live 11's API on the path

from APCAdvanced_MkII.APCNoteEditorComponent import APCNoteEditorComponent, color_for_note
from APCAdvanced_MkII.ButtonSliderElement import ButtonSliderElement
from APCAdvanced_MkII.PPMeter import COLORS, OFF_COLOR, PPMeter
from APCAdvanced_MkII.SkinDefault import RgbColors
from APCAdvanced_MkII.VelocityProvider import VelocityProvider

class FakeNote(object):

  def __init__(self, velocity, mute=False):
    self.velocity = velocity
    self.mute = mute


class FakeButton(object):

  def __init__(self):
    self.light = None
    self.channel = None

  def set_light(self, value):
    self.light = value

  def turn_off(self):
    self.light = 'off'

  def set_channel(self, channel):
    self.channel = channel


class FakeMatrix(object):

  def __init__(self, width, height):
    self._width = width
    self._height = height
    self._buttons = [[FakeButton() for _ in range(width)] for _ in range(height)]

  def width(self):
    return self._width

  def height(self):
    return self._height

  def get_button(self, column, row):
    return self._buttons[row][column]


class FakeSlider(object):

  def __init__(self):
    self.sent = []
    self._listeners = []

  def add_value_listener(self, listener, *a, **k):
    self._listeners.append(listener)

  def remove_value_listener(self, listener):
    self._listeners.remove(listener)

  def value_has_listener(self, listener):
    return listener in self._listeners

  def send_value(self, value, force_send=False):
    self.sent.append(value)

  def fire(self, value):
    for listener in list(self._listeners):
      listener(value)


class NoteColorTest(unittest.TestCase):

  def test_five_velocity_buckets(self):
    self.assertEqual(color_for_note(FakeNote(127)), 'Full')
    self.assertEqual(color_for_note(FakeNote(126)), 'High')
    self.assertEqual(color_for_note(FakeNote(94)), 'High')
    self.assertEqual(color_for_note(FakeNote(93)), 'Medium')
    self.assertEqual(color_for_note(FakeNote(62)), 'Medium')
    self.assertEqual(color_for_note(FakeNote(61)), 'Low')
    self.assertEqual(color_for_note(FakeNote(31)), 'Low')
    self.assertEqual(color_for_note(FakeNote(30)), 'Empty')
    self.assertEqual(color_for_note(FakeNote(0)), 'Empty')

  def test_muted_notes_win(self):
    self.assertEqual(color_for_note(FakeNote(127, mute=True)), 'Muted')

  def test_every_colour_is_in_the_skin(self):
    """ A name the skin lacks raises SkinColorMissingError on the hardware """
    for velocity in range(128):
      name = color_for_note(FakeNote(velocity))
      self.assertTrue(hasattr(RgbColors.NoteEditor.Step, name), 'Step.%s missing' % name)
      self.assertTrue(hasattr(RgbColors.NoteEditor.StepEditing, name), 'StepEditing.%s missing' % name)

    self.assertTrue(hasattr(RgbColors.NoteEditor.Step, 'Muted'))
    self.assertTrue(hasattr(RgbColors.NoteEditor.StepEditing, 'Muted'))


class FourWideNoteEditor(APCNoteEditorComponent):
  """ Enough of the editor to exercise the step layout """

  def __init__(self, width, height, triplet_factor=1.0):
    self._width = width
    self._height = height
    self._triplet_factor = triplet_factor
    self._page_index = 0

  @property
  def page_length(self):
    return self._get_step_count() * self._get_step_length() * self._triplet_factor

  def _get_width(self):
    return self._width

  def _get_height(self):
    return self._height

  def _get_step_count(self):
    return self._width * self._height

  def _get_step_length(self):
    return 0.25

  def _time_step(self, time):
    return time


class VisibleStepsTest(unittest.TestCase):

  def test_four_by_four_grid_uses_every_step(self):
    editor = FourWideNoteEditor(4, 4)
    steps = editor._visible_steps()
    self.assertEqual(len(steps), 16)
    self.assertEqual([index for _, index in steps], list(range(16)))

  def test_triplets_drop_the_last_step_of_each_four(self):
    editor = FourWideNoteEditor(4, 4, triplet_factor=0.75)
    steps = editor._visible_steps()
    self.assertEqual(len(steps), 12)
    # The skipped pad in each row of four stays dark rather than shifting the
    # remaining steps left
    self.assertEqual([index for _, index in steps], [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14])

  def test_triplets_on_an_eight_wide_grid_match_live(self):
    """ Live drops indices 6 and 7 of every eight, which this generalises """
    editor = FourWideNoteEditor(8, 4, triplet_factor=0.75)
    self.assertEqual(len(editor._visible_steps()), 24)


class PPMeterTest(unittest.TestCase):

  def _meter(self, left, right, width=5, height=1):
    meter = PPMeter.__new__(PPMeter)
    meter.top = 1.0
    meter.bottom = 0.6
    meter.track = type('Track', (object,), {'output_meter_left': left, 'output_meter_right': right})()
    meter.target_matrix = FakeMatrix(width, height)
    return meter

  def test_silence_lights_nothing(self):
    meter = self._meter(0.0, 0.0)
    self.assertEqual(meter.led_index, 0)

  def test_full_scale_lights_every_led(self):
    meter = self._meter(1.0, 1.0)
    self.assertEqual(meter.led_index, meter.led_count + 1)

  def test_values_below_the_window_are_clamped(self):
    self.assertEqual(self._meter(0.3, 0.3).scaled_mean_peak, 0.0)

  def test_values_above_the_window_are_clamped(self):
    self.assertEqual(self._meter(1.4, 1.4).scaled_mean_peak, 0.4)

  def test_mean_of_both_channels(self):
    self.assertAlmostEqual(self._meter(1.0, 0.6).mean_peak, 0.8)

  def test_lights_run_from_the_bottom_up(self):
    meter = self._meter(0.8, 0.8)
    meter.set_light()
    lit = [meter.target_matrix.get_button(x, 0).light for x in range(meter.led_count)]
    self.assertEqual(lit[:meter.led_index], COLORS[:meter.led_index])
    self.assertTrue(all(colour == OFF_COLOR for colour in lit[meter.led_index:]))


class VelocityProviderTest(unittest.TestCase):

  def test_starts_at_the_live_default(self):
    self.assertEqual(VelocityProvider().velocity, 100)

  def test_slider_moves_change_the_velocity(self):
    provider = VelocityProvider()
    slider = FakeSlider()
    provider.set_slider(slider)
    slider.fire(31)
    self.assertEqual(provider.velocity, 31)

  def test_slider_is_lit_to_the_current_velocity(self):
    provider = VelocityProvider()
    slider = FakeSlider()
    provider.set_slider(slider)
    self.assertEqual(slider.sent, [100])
    slider.fire(127)
    self.assertEqual(slider.sent[-1], 127)

  def test_listeners_are_notified(self):
    provider = VelocityProvider()
    slider = FakeSlider()
    provider.set_slider(slider)
    seen = []
    provider.add_velocity_listener(lambda: seen.append(provider.velocity))
    slider.fire(62)
    self.assertEqual(seen, [62])


class ButtonSliderTest(unittest.TestCase):

  def _slider(self, count=5):
    slider = ButtonSliderElement.__new__(ButtonSliderElement)
    slider._buttons = [FakeButton() for _ in range(count)]
    slider._last_sent_value = -1
    return slider

  def test_zero_lights_only_the_first_button(self):
    slider = self._slider()
    slider.send_value(0)
    self.assertEqual([button.light for button in slider._buttons],
      ['NoteEditor.Step.Empty', 'off', 'off', 'off', 'off'])

  def test_full_lights_every_button(self):
    slider = self._slider()
    slider.send_value(127)
    self.assertEqual([button.light for button in slider._buttons], list(
      'NoteEditor.Step.' + name for name in ('Empty', 'Low', 'Medium', 'High', 'Full')))

  def test_middle_lights_half_the_column(self):
    slider = self._slider()
    slider.send_value(64)
    self.assertEqual([button.light for button in slider._buttons][:3],
      ['NoteEditor.Step.Empty', 'NoteEditor.Step.Low', 'NoteEditor.Step.Medium'])
    self.assertEqual([button.light for button in slider._buttons][3:], ['off', 'off'])

  def test_force_send_repeats_the_same_value(self):
    slider = self._slider()
    slider.send_value(127)
    slider._buttons[0].light = None
    slider.send_value(127)
    self.assertIsNone(slider._buttons[0].light)
    slider.send_value(127, force_send=True)
    self.assertEqual(slider._buttons[0].light, 'NoteEditor.Step.Empty')


if __name__ == '__main__':
  unittest.main()
