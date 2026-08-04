from pushbase.automation_component import AutomationComponent
from pushbase.note_settings_component import NoteEditorSettingsComponent, NoteSettingsComponent
from _APC.RingedEncoderElement import RING_SIN_VALUE
from .APCMessenger import APCMessenger

class NoteEditorSettingsComponent(NoteEditorSettingsComponent, APCMessenger):
  """ Customized to highlight specific encoders for APC """

  def __init__(self, *a, **k):
    super(NoteEditorSettingsComponent, self).__init__(
        note_settings_component_class = NoteSettingsComponent,
        automation_component_class = AutomationComponent,
        *a, **k)

  def set_encoders(self, encoders):
    """ Set the encoder mode to visible and init to center """
    super(NoteEditorSettingsComponent, self).set_encoders(encoders)
    if encoders:
      for encoder in encoders:
        encoder._ring_mode_button.send_value(RING_SIN_VALUE, force=True)
        encoder.send_value(64, force=True)
