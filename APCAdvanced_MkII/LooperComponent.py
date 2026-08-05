from contextlib import contextmanager
from ableton.v2.base import liveobj_valid
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from _Framework.SubjectSlot import subject_slot

class LooperComponent(ControlSurfaceComponent):
  """ Allows DJ-style looping of the currently selected clip.

  The clip's own loop is remembered while a DJ loop is running and put back when
  it is released, so looping a clip never costs it the markers it came with.
  """

  def __init__(self, *a, **k):
    super(LooperComponent, self).__init__(*a, **k)
    self._toggle_button = None
    self._held_clip = None
    self._held_loop = None

  # PROPERTIES
  @property
  def clip(self):
    clip = self.song().view.detail_clip
    return clip if clip and clip.is_audio_clip else None
  @property
  def start(self):
    return self.clip.loop_start
  @property
  def end(self):
    return self.clip.loop_end
  @property
  def length(self):
    return self.clip.length
  @property
  def rounded_playing_position(self):
    """ rounded to the nearest beat """
    return round(self.clip.playing_position)

  # SETTERS
  def set_toggle_button(self, button):
    self._toggle_button = button
    self._on_clip_looping_value.subject = button
    self.update()

  def set_start_button(self, button):
    self._set_start.subject = button

  def set_halve_button(self, button):
    self._on_halve.subject = button
    if button:
      button.turn_on()

  def set_double_button(self, button):
    self._on_double.subject = button
    if button:
      button.turn_on()

  def set_left_button(self, button):
    self._on_left.subject = button

  def set_right_button(self, button):
    self._on_right.subject = button

  def set_nudge_left_button(self, button):
    self._nudge_left.subject = button
    if button:
      button.turn_on()

  def set_nudge_right_button(self, button):
    self._nudge_right.subject = button
    if button:
      button.turn_on()

  def on_selected_track_changed(self):
    self.update()

  def update(self):
    super(LooperComponent, self).update()
    if self.clip and self.clip.looping and self._toggle_button:
      self._toggle_button.turn_on()
    elif self._toggle_button:
      self._toggle_button.turn_off()

  # EVENTS
  @subject_slot('value')
  def _on_clip_looping_value(self, value):
    if self.clip and value > 0:
      if self.holds_loop:
        self._release_original_loop()
      else:
        self.clip.looping = not self.clip.looping
    self.update()

  @subject_slot('value')
  def _set_start(self, value):
    if self.clip and value > 0:
      with self.hold_loop():
        self.set_loop(self.rounded_playing_position,
            self.rounded_playing_position + 8)
      self.clip.looping = True
      self.update()

  @subject_slot('value')
  def _on_left(self, value):
    """ Move left by loop length """
    if self.clip and value > 0:
      with self.hold_loop():
        self.move(-self.length)

  @subject_slot('value')
  def _on_right(self, value):
    """ Move right by loop length """
    if self.clip and value > 0:
      with self.hold_loop():
        self.move(self.length)

  @subject_slot('value')
  def _on_halve(self, value):
    if self.clip and value > 0:
      with self.hold_loop():
        self.set_loop(self.start, self.start + (self.length / 2.0))

  @subject_slot('value')
  def _on_double(self, value):
    if self.clip and value > 0:
      with self.hold_loop():
        self.set_loop(self.start, self.start + (self.length * 2))

  @subject_slot('value')
  def _nudge_left(self, value):
    """ Nudge left a bar """
    if self.clip and value > 0:
      with self.hold_loop():
        self.move(-4)

  @subject_slot('value')
  def _nudge_right(self, value):
    """ Nudge right a bar """
    if self.clip and value > 0:
      with self.hold_loop():
        self.move(4)


  def move(self, amount):
    """ Move start and end points by amount. Can be negative """
    self.set_loop(self.start + amount, self.end + amount)

  def set_loop(self, start, end):
    """
    Set start and end points to fixed values
    Will calculate correct order to make changes, e.g.
    If new start value >= current end value
    """
    self._hold_original_loop()
    self._write_loop(self.clip, start, end)

  def _write_loop(self, clip, start, end):
    if start >= clip.loop_end:
      clip.loop_end = end
      clip.loop_start = start
    else:
      clip.loop_start = start
      clip.loop_end = end

  # HOLDING THE CLIP'S OWN LOOP
  @property
  def holds_loop(self):
    """ Whether a DJ loop is running on the clip currently on show """
    return self._held_clip is not None and self._held_clip == self.clip

  def _hold_original_loop(self):
    """ Remember the clip's own loop before a DJ loop overwrites it """
    clip = self.clip
    if self._held_clip is not None and self._held_clip != clip:
      self._release_original_loop()
    if self._held_clip is None:
      self._held_clip = clip
      self._held_loop = (clip.loop_start, clip.loop_end, clip.looping)

  def _release_original_loop(self):
    """ Give the clip back the loop it came with """
    clip, loop = self._held_clip, self._held_loop
    self._held_clip, self._held_loop = None, None
    if not liveobj_valid(clip):
      return
    start, end, looping = loop
    try:
      self._write_loop(clip, start, end)
      clip.looping = looping
    except RuntimeError:
      pass

  @contextmanager
  def hold_loop(self, loop = True):
    """
    Some properties are only available when looping or not looping
    So we hold loop on/off to access these properties
    """
    self._hold_original_loop() # Before the flip below, so the clip's own state is what gets kept
    was_looping = self.clip.looping # Remember whether we were looping
    self.clip.looping = loop
    yield
    self.clip.looping = was_looping
