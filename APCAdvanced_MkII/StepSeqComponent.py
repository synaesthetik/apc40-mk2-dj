from itertools import chain, starmap
from ableton.v2.base import listens
from pushbase.step_seq_component import StepSeqComponent as StepSeqComponentBase
from _Framework.Util import first
from .APCMessenger import APCMessenger
from .DrumGroupFinderComponent import DrumGroupFinderComponent
from .MatrixMaps import PAD_FEEDBACK_CHANNEL, QUANTIZATION_CHANNEL, QUANTIZATION_ROOT

class StepSeqComponent(StepSeqComponentBase, APCMessenger):
  """ Step sequencer for APC40 MkII.

  Live 11 takes the note editor and the drum group as constructor arguments
  rather than building them itself, so the control surface hands them in.
  """

  def __init__(self, velocity_provider = None, *a, **k):
    super(StepSeqComponent, self).__init__(*a, **k)
    self._velocity_provider = velocity_provider
    self._quant_buttons = None
    self._setup_drum_group_finder()
    self._configure_playhead()

  def _select_track_by_name(self, name):
    for track in self.song.tracks:
      if track.name == name:
        self.song.view.selected_track = track

  def set_velocity_slider(self, button_slider):
    if self._velocity_provider:
      self._velocity_provider.set_slider(button_slider)

  def _configure_playhead(self):
    self._playhead_component._notes=tuple(chain(*starmap(range, (
         (28, 32),
         (20, 24),
         (12, 16),
         (4, 8)))))
    self._playhead_component._triplet_notes=tuple(chain(*starmap(range, (
         (28, 31),
         (20, 23),
         (12, 15),
         (4, 7)))))
    self._playhead_component._feedback_channels = [PAD_FEEDBACK_CHANNEL]

  def _setup_drum_group_finder(self):
    self._drum_group_finder = DrumGroupFinderComponent()
    self._on_drum_group_changed.subject = self._drum_group_finder
    self._drum_group_finder.update()

  @listens('drum_group')
  def _on_drum_group_changed(self):
    self.set_drum_group_device(self._drum_group_finder.drum_group)

  def set_drum_group_device(self, drum_group_device):
    self._instrument.set_drum_group_device(drum_group_device)

  def set_delete_button(self, button):
    if button:
      button.set_channel(PAD_FEEDBACK_CHANNEL)
    super(StepSeqComponent, self).set_delete_button(button)

  def set_quantization_buttons(self, buttons):
    """ When loaded, move the buttons to empty space on channel 15
    When unloaded reset them """
    if self._quant_buttons and buttons is None:
      self._quant_buttons.reset() # Reset quant buttons when released
    self._quant_buttons = buttons
    if buttons:
      for i, button in enumerate(buttons):
        if i > 3: # Only change second half's channel
          button.set_channel(QUANTIZATION_CHANNEL)
          button.set_identifier(QUANTIZATION_ROOT + i)
    super(StepSeqComponent, self).set_quantization_buttons(buttons)

  def set_button_matrix(self, matrix):
    """ This method, as with most set_* methods, is called every time
    This component is enabled """
    super(StepSeqComponent, self).set_button_matrix(matrix)
    if matrix:
      self._select_track_by_name("Drums") # Select the drum track if we can
      for button, _ in filter(first, matrix.iterbuttons()):
        button.set_channel(PAD_FEEDBACK_CHANNEL)

  def set_loop_selector_matrix(self, matrix):
    super(StepSeqComponent, self).set_loop_selector_matrix(matrix)
    if matrix:
      for button, _ in filter(first, matrix.iterbuttons()):
        button.set_channel(PAD_FEEDBACK_CHANNEL)
