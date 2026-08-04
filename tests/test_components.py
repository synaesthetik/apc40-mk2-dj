"""Tests that run real Live 11 elements and components, not stand-ins."""
import unittest

from live_env import FakeEvents
import Live
from _Framework.Dependency import inject
from _Framework.InputControlElement import MIDI_NOTE_TYPE
from _Framework.Util import const, nop
from APCAdvanced_MkII.ButtonElement import ButtonElement
from APCAdvanced_MkII.DrumGroupFinderComponent import DrumGroupFinderComponent

def element_dependencies():
  """ What an element resolves out of the control surface when it is built """
  return inject(send_midi=const(nop), request_rebuild_midi_map=const(nop),
    register_control=const(nop)).everywhere()


class ButtonElementTest(unittest.TestCase):

  def _button(self):
    return ButtonElement(True, MIDI_NOTE_TYPE, 0, 32, name='0_Clip_0_Button')

  def test_reset_restores_the_default_message(self):
    """ The sequencer moves buttons onto feedback channels and expects reset to
    put them back """
    with element_dependencies():
      button = self._button()
      button.set_channel(14)
      button.set_identifier(100)
      button.reset()
      self.assertEqual(button.message_channel(), 0)
      self.assertEqual(button.message_identifier(), 32)

  def test_reset_lets_the_script_see_the_button_again(self):
    """ Drum pads are taken away from the script while sequencing. If reset
    leaves that in place, clip launch on those pads stays dead afterwards """
    with element_dependencies():
      button = self._button()
      button.suppress_script_forwarding = True
      button.reset()
      self.assertFalse(button.suppress_script_forwarding)


def drum_rack():
  return FakeEvents(type=(Live.Device.DeviceType.instrument), can_have_drum_pads=True,
    can_have_chains=False, chains=[])


def song_with(devices):
  track = FakeEvents(devices=devices)
  return FakeEvents(view=FakeEvents(selected_track=track))


class DrumGroupFinderTest(unittest.TestCase):

  def _finder(self, song):
    return DrumGroupFinderComponent(song=song, register_component=nop)

  def test_finds_a_drum_rack_on_the_selected_track(self):
    rack = drum_rack()
    self.assertIs(self._finder(song_with([rack])).drum_group, rack)

  def test_reports_nothing_when_the_track_has_no_drum_rack(self):
    self.assertIsNone(self._finder(song_with([])).drum_group)

  def test_tells_listeners_even_when_the_rack_has_not_changed(self):
    """ The sequencer attaches its listener after the finder is built, so it
    only learns about an already-found rack if update() notifies again """
    finder = self._finder(song_with([drum_rack()]))
    seen = []
    finder.add_drum_group_listener(lambda: seen.append(finder.drum_group))
    finder.update()
    self.assertEqual(len(seen), 1)

  def test_a_new_rack_is_reported(self):
    song = song_with([])
    finder = self._finder(song)
    seen = []
    finder.add_drum_group_listener(lambda: seen.append(finder.drum_group))
    rack = drum_rack()
    song.view.selected_track = FakeEvents(devices=[rack])
    finder.update()
    self.assertEqual(seen, [rack])


if __name__ == '__main__':
  unittest.main()
