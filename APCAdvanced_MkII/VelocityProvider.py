from ableton.v2.base import EventObject, listenable_property, listens

DEFAULT_VELOCITY = 100

class VelocityProvider(EventObject):
  """ Feeds the APC's velocity slider into the note editor.

  Live 9 required overriding the note editor to read a velocity attribute.
  Live 11's NoteEditorComponent takes a velocity_provider instead, so the
  slider is exposed through that protocol.
  """

  def __init__(self, velocity = DEFAULT_VELOCITY, *a, **k):
    super(VelocityProvider, self).__init__(*a, **k)
    self._velocity = velocity
    self._slider = None

  @listenable_property
  def velocity(self):
    return self._velocity

  def set_velocities_playable(self, playable):
    pass

  def set_slider(self, slider):
    self._slider = slider
    self._on_slider_value.subject = slider
    self._update_slider()

  @listens('value')
  def _on_slider_value(self, value):
    self._velocity = value
    self.notify_velocity()
    self._update_slider()

  def _update_slider(self):
    if self._slider:
      self._slider.send_value(self._velocity, force_send = True)
