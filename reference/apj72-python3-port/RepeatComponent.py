from _Framework.ButtonElement import ButtonElement
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from _Framework.DeviceComponent import DeviceComponent
from _Framework.EncoderElement import EncoderElement
from _Framework.SubjectSlot import subject_slot_group
from _Generic.Devices import device_parameters_to_map, number_of_parameter_banks, parameter_banks, parameter_bank_names, best_of_parameter_bank
from .APCMessenger import APCMessenger


class RepeatComponent(DeviceComponent, APCMessenger):
  """ Takes buttons rather than encoders.
  Doesn't support paging because why bother? 
  """
  def __init__(self, parent, *a, **k):
    super(RepeatComponent, self).__init__(*a, **k)
    self.parent = parent
    self._device_buttons = None

  @property
  def _bank(self):
    return parameter_banks(self._device)[0]

  def set_parameter_buttons(self, buttons):
    self._parameter_buttons = buttons
    self._on_parameter_button.replace_subjects(buttons or [])


  def set_device(self, device):
    if device != None:
      if device.name == "Repeats":
        super(RepeatComponent, self).set_device(device)
    else:
      super(RepeatComponent, self).set_device(device) 


  @subject_slot_group('value')
  def _on_parameter_button(self, value, button):
    self.parent.log_message("======================")
    self.parent.log_message(str(self._device.name))
    self.parent.log_message("======================")
    parameter = self._bank[self._button_index(button)]
    if value > 0:
      parameter.value = parameter.max
    else:
      parameter.value = parameter.min

  def _button_index(self, button):
    return list(self._parameter_buttons).index(button)
