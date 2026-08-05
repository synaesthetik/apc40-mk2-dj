"""Looper tests.

The loop buttons write loop_start and loop_end on whatever clip is showing in
Detail/Clip view. His original never saved what was there before, so a DJ loop
overwrote a clip's markers for good — including the markers on an effect's dummy
clip if that happened to be the selected one. These tests pin down that the
clip is handed back the way it was found.
"""
import unittest

from live_env import FakeEvents  # noqa: F401 - also puts Live 11's API on the path
from _Framework.Util import nop
from APCAdvanced_MkII.LooperComponent import LooperComponent

class FakeClip(object):
  is_audio_clip = True

  def __init__(self, loop_start=8.0, loop_end=24.0, looping=True, playing_position=10.4):
    self._loop_start = loop_start
    self._loop_end = loop_end
    self.looping = looping
    self.playing_position = playing_position
    self.alive = True

  def _write(self, name, value):
    """ Live raises when a clip that has gone away is written to """
    if not self.alive:
      raise RuntimeError('clip no longer exists')
    self.__dict__[name] = value

  loop_start = property(lambda self: self._loop_start,
    lambda self, value: self._write('_loop_start', value))
  loop_end = property(lambda self: self._loop_end,
    lambda self, value: self._write('_loop_end', value))

  @property
  def length(self):
    return self._loop_end - self._loop_start

  @property
  def markers(self):
    return (self._loop_start, self._loop_end, self.looping)


def looper_for(clip):
  song = FakeEvents(view=FakeEvents(detail_clip=clip))
  looper = LooperComponent(song=song, register_component=nop)
  return (looper, song)


PRESS = 127

class LooperTest(unittest.TestCase):

  def test_starting_a_loop_moves_the_markers(self):
    clip = FakeClip()
    looper, _ = looper_for(clip)
    looper._set_start(PRESS)
    self.assertEqual((clip.loop_start, clip.loop_end), (10.0, 18.0))
    self.assertTrue(clip.looping)

  def test_releasing_hands_the_clip_back_untouched(self):
    clip = FakeClip(looping=False)
    before = clip.markers
    looper, _ = looper_for(clip)
    looper._set_start(PRESS)
    looper._on_clip_looping_value(PRESS)
    self.assertEqual(clip.markers, before)

  def test_releasing_after_halving_and_moving_also_restores(self):
    clip = FakeClip()
    before = clip.markers
    looper, _ = looper_for(clip)
    looper._set_start(PRESS)
    looper._on_halve(PRESS)
    looper._on_right(PRESS)
    looper._nudge_left(PRESS)
    self.assertNotEqual(clip.markers, before)
    looper._on_clip_looping_value(PRESS)
    self.assertEqual(clip.markers, before)

  def test_the_toggle_still_toggles_when_no_loop_was_started(self):
    clip = FakeClip(looping=False)
    looper, _ = looper_for(clip)
    looper._on_clip_looping_value(PRESS)
    self.assertTrue(clip.looping)
    self.assertEqual((clip.loop_start, clip.loop_end), (8.0, 24.0))

  def test_starting_a_loop_on_another_clip_restores_the_first(self):
    first = FakeClip()
    before = first.markers
    looper, song = looper_for(first)
    looper._set_start(PRESS)
    song.view.detail_clip = FakeClip(loop_start=0.0, loop_end=8.0)
    looper._set_start(PRESS)
    self.assertEqual(first.markers, before)

  def test_releasing_a_clip_that_has_gone_away_does_not_raise(self):
    clip = FakeClip()
    looper, _ = looper_for(clip)
    looper._set_start(PRESS)
    clip.alive = False
    looper._on_clip_looping_value(PRESS)

  def test_nothing_is_written_when_no_clip_is_selected(self):
    looper, song = looper_for(None)
    looper._set_start(PRESS)
    looper._on_clip_looping_value(PRESS)


if __name__ == '__main__':
  unittest.main()
