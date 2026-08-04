"""Mode wiring tests.

`_Framework.ModesComponent` recognises components with an isinstance check
against its own base class, so an `ableton.v2` component put straight into a
mode list is silently not treated as a mode and never gets enabled. These tests
pin down that the script hands ModesComponent things it can actually use.
"""
import unittest

import live_env  # noqa: F401 - puts Live 11's API on the path

from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from _Framework.Layer import Layer
from _Framework.ModesComponent import Mode, tomode
from ableton.v2.control_surface import Component
from APCAdvanced_MkII.APCAdvanced_MkII import APCAdvanced_MkII, ComponentLayerMode
from APCAdvanced_MkII.APCDrumGroupComponent import APCDrumGroupComponent
from APCAdvanced_MkII.LooperComponent import LooperComponent
from APCAdvanced_MkII.NoteSettings import NoteEditorSettingsComponent
from APCAdvanced_MkII.PPMeter import PPMeter
from APCAdvanced_MkII.RepeatComponent import RepeatComponent
from APCAdvanced_MkII.StepSeqComponent import StepSeqComponent
from APCAdvanced_MkII.StepperComponent import StepperComponent

def framework_component():
  """ A _Framework component without running its constructor, which would need
  the control surface's injected dependencies """
  return ControlSurfaceComponent.__new__(ControlSurfaceComponent)


def v2_component():
  return Component.__new__(Component)


class FakeElement(object):

  @property
  def submatrix(self):
    return self

  def __getitem__(self, key):
    return self


class RecordingComponent(object):

  def __init__(self):
    self.layer = None
    self.enabled = None

  def set_enabled(self, enable):
    self.enabled = enable


class ModeCoercionTest(unittest.TestCase):

  def test_framework_components_become_modes_on_their_own(self):
    self.assertIsInstance(tomode(framework_component()), Mode)

  def test_ableton_v2_components_do_not(self):
    """ The reason every v2 component in this script is wrapped by hand """
    self.assertNotIsInstance(tomode(v2_component()), Mode)

  def test_a_v2_component_paired_with_a_layer_breaks_on_entry(self):
    """ The pair falls through to CompoundMode, which then calls enter_mode on
    the component itself. It looks like a mode and fails when used """
    compound = tomode((v2_component(), Layer()))
    self.assertIsInstance(compound, Mode)
    self.assertRaises(AttributeError, compound.enter_mode)

  def test_wrapping_makes_a_v2_component_usable(self):
    self.assertIsInstance(tomode(ComponentLayerMode(v2_component(), Layer())), Mode)


class ComponentLayerModeTest(unittest.TestCase):

  def test_entering_hands_over_the_layer_and_enables(self):
    component = RecordingComponent()
    layer = Layer()
    ComponentLayerMode(component, layer).enter_mode()
    self.assertIs(component.layer, layer)
    self.assertTrue(component.enabled)

  def test_leaving_disables_and_takes_the_layer_back(self):
    component = RecordingComponent()
    mode = ComponentLayerMode(component, Layer())
    mode.enter_mode()
    mode.leave_mode()
    self.assertIsNone(component.layer)
    self.assertFalse(component.enabled)


class ModeLayerTest(unittest.TestCase):
  """ Build the control surface without running its constructor, fill in what
  the mode layer methods touch, and check what they hand to ModesComponent """

  def setUp(self):
    self.surface = APCAdvanced_MkII.__new__(APCAdvanced_MkII)
    for name in ('_session', '_session_zoom', '_repeats', '_ppm'):
      setattr(self.surface, name, framework_component())
    for name in ('_note_editor', '_drum_group', '_note_editor_settings', '_sequencer'):
      setattr(self.surface, name, v2_component())
    self.surface._repeats_layer = Layer()
    self.surface._ppm_layer = Layer()
    for name in ('_velocity_slider', '_double_press_matrix', '_double_press_event_matrix',
     '_user_button', '_stop_all_button', '_playhead', '_stop_buttons', '_shift_button',
     '_session_matrix', '_up_button', '_down_button'):
      setattr(self.surface, name, FakeElement())

  def test_every_session_mode_entry_is_a_mode(self):
    for entry in self.surface._session_mode_layers():
      self.assertIsInstance(tomode(entry), Mode, 'not usable as a mode: %r' % (entry,))

  def test_every_sequencer_mode_entry_is_a_mode(self):
    for entry in self.surface._sequencer_mode_layers():
      self.assertIsInstance(tomode(entry), Mode, 'not usable as a mode: %r' % (entry,))

  def test_the_components_that_need_enabling_get_enabled(self):
    """ A layer alone is not enough: a disabled component grabs nothing """
    enabling = [entry for entry in
     self.surface._session_mode_layers() + self.surface._sequencer_mode_layers()
     if isinstance(entry, ComponentLayerMode)]
    self.assertEqual(len(enabling), 4)


class LayerKeyTest(unittest.TestCase):
  """ A Layer key is resolved as set_<key>, or failing that as a control named
  <key>. Anything else raises UnhandledControlError the moment the layer is
  grabbed, which is how a renamed Live API method shows up """

  def _assert_handled(self, component_class, names):
    for name in names:
      handled = hasattr(component_class, 'set_' + name) or hasattr(component_class, name)
      self.assertTrue(handled, '%s handles neither set_%s nor %s' % (
       component_class.__name__, name, name))

  def _layer_keys(self, layer):
    return list(layer._name_to_controls.keys())

  def test_drum_group_layer(self):
    surface = APCAdvanced_MkII.__new__(APCAdvanced_MkII)
    for name in ('_session_matrix', '_up_button', '_down_button'):
      setattr(surface, name, FakeElement())
    self._assert_handled(APCDrumGroupComponent, self._layer_keys(surface._drum_group_layer()))

  def test_sequencer_layer(self):
    surface = APCAdvanced_MkII.__new__(APCAdvanced_MkII)
    for name in ('_velocity_slider', '_double_press_matrix', '_double_press_event_matrix',
     '_user_button', '_stop_all_button', '_playhead', '_stop_buttons', '_shift_button'):
      setattr(surface, name, FakeElement())
    self._assert_handled(StepSeqComponent, self._layer_keys(surface._sequencer_layer()))

  def test_layers_built_in_the_constructors(self):
    for component_class, names in (
     (NoteEditorSettingsComponent, ('initial_encoders', 'encoders')),
     (RepeatComponent, ('parameter_buttons',)),
     (PPMeter, ('target_matrix',)),
     (StepperComponent, ('playhead', 'buttons')),
     (LooperComponent, ('toggle_button', 'start_button', 'halve_button', 'double_button',
      'left_button', 'right_button', 'nudge_left_button', 'nudge_right_button'))):
      self._assert_handled(component_class, names)


if __name__ == '__main__':
  unittest.main()
