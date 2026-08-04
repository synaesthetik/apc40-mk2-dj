from pushbase.drum_group_component import DrumGroupComponent
from .APCMessenger import APCMessenger
from .MatrixMaps import PAD_FEEDBACK_CHANNEL

class APCDrumGroupComponent(DrumGroupComponent, APCMessenger):
  """ Customized to use its own feedback channel.

  Live 11 switches pads between playing and reporting to the script through
  the element's script_forwarding property, which only exists on ableton.v2
  elements. The APC's buttons are _Framework elements, so the same switch is
  applied here through suppress_script_forwarding.
  """

  def set_matrix(self, matrix):
    super(APCDrumGroupComponent, self).set_matrix(matrix)
    self._update_pads_from_script()

  def _update_control_from_script(self):
    super(APCDrumGroupComponent, self)._update_control_from_script()
    self._update_pads_from_script()

  def _update_pads_from_script(self):
    takeover_pads = self._takeover_pads or bool(self.pressed_pads)
    for pad in self.matrix:
      element = pad.control_element
      if element:
        element.set_channel(PAD_FEEDBACK_CHANNEL)
        element.suppress_script_forwarding = not takeover_pads
