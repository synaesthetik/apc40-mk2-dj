import sys
from contextlib import contextmanager

# Monkeypatch things
from . import ControlElementUtils
from . import SessionComponent
from . import SkinDefault
sys.modules['_APC.ControlElementUtils'] = ControlElementUtils
sys.modules['_APC.SessionComponent'] = SessionComponent
sys.modules['_APC.SkinDefault'] = SkinDefault

from _Framework.ModesComponent import ModesComponent, ImmediateBehaviour, AddLayerMode, ComponentMode, DelayMode, LayerMode
from _Framework.Layer import Layer
from _Framework.SessionZoomingComponent import SessionZoomingComponent
from _Framework.Dependency import inject
from _Framework.Util import const, lazy_attribute, recursive_map, find_if
from _Framework.ComboElement import DoublePressElement, DoublePressContext
from _Framework.ButtonMatrixElement import ButtonMatrixElement
from _Framework.Resource import PrioritizedResource
from ableton.v2.base import const as v2_const, inject as v2_inject
from ableton.v2.control_surface import ClipCreator
from ableton.v2.control_surface.components import AutoArmComponent
from ableton.v2.control_surface.elements import PlayheadElement
from pushbase.grid_resolution import GridResolution

from APC40_MkII.APC40_MkII import APC40_MkII, NUM_SCENES, NUM_TRACKS
from APC40_MkII.Colors import LIVE_COLORS_TO_MIDI_VALUES, RGB_COLOR_TABLE
from .APCDrumGroupComponent import APCDrumGroupComponent
from .APCNoteEditorComponent import APCNoteEditorComponent
from .ButtonSliderElement import ButtonSliderElement
from .LooperComponent import LooperComponent
from .MatrixMaps import PAD_TRANSLATIONS, FEEDBACK_CHANNELS
from .MixerComponent import MixerComponent, ChanStripComponent
from .NoteSettings import NoteEditorSettingsComponent
from .PPMeter import PPMeter
from .RepeatComponent import RepeatComponent
from .SessionComponent import SessionComponent
from .SkinDefault import make_rgb_skin
from .StepSeqComponent import StepSeqComponent
from .StepperComponent import StepperComponent
from .VelocityProvider import VelocityProvider

class ComponentLayerMode(LayerMode):
  """ Hands a component its layer and enables it for as long as the mode lasts.

  _Framework's LayerMode only assigns the layer, and a disabled component grabs
  nothing from it. Wrapping components by hand is also the only way to put an
  ableton.v2 component in a mode: ModesComponent recognises components by
  isinstance against _Framework's base class, so a pushbase component silently
  ends up treated as something that is not a mode at all.
  """

  def enter_mode(self):
    super(ComponentLayerMode, self).enter_mode()
    self._get_component().set_enabled(True)

  def leave_mode(self):
    self._get_component().set_enabled(False)
    super(ComponentLayerMode, self).leave_mode()


class APCAdvanced_MkII(APC40_MkII):
  """ APC40Mk2 script with step sequencer mode """
  def __init__(self, *a, **k):
    self._double_press_context = DoublePressContext()
    self._v2_components = []
    APC40_MkII.__init__(self, *a, **k)
    with self.component_guard():
      self._create_sequencer()
      self._create_repeats()
      self._create_stepper()
      self._init_auto_arm()
      self._create_ppm()
      self._create_looper()
      self._create_session_mode()
    self.set_pad_translations(PAD_TRANSLATIONS)
    self.set_feedback_channels(FEEDBACK_CHANNELS)

  def _create_controls(self):
    """ Add some additional stuff baby """
    super(APCAdvanced_MkII, self)._create_controls()
    self._grid_resolution = GridResolution()
    self._velocity_slider = ButtonSliderElement(tuple(self._scene_launch_buttons_raw[::-1]))
    double_press_rows = recursive_map(DoublePressElement, self._matrix_rows_raw)
    self._double_press_matrix = ButtonMatrixElement(name='Double_Press_Matrix', rows=double_press_rows)
    self._double_press_event_matrix = ButtonMatrixElement(name='Double_Press_Event_Matrix', rows=recursive_map(lambda x: x.double_press, double_press_rows))
    self._playhead = PlayheadElement(self._c_instance.playhead)
    # Make these prioritized resources, which share between Layers() equally
    # Rather than building a stack
    self._pan_button._resource_type = PrioritizedResource
    self._user_button._resource_type = PrioritizedResource
    for button in self._scene_launch_buttons_raw:
      button._resource_type = PrioritizedResource

  def _create_stepper(self):
    self._stepper = StepperComponent(grid_resolution = self._grid_resolution,
        is_enabled = False,
        layer = Layer(playhead = self._playhead,
        buttons = self._stepper_buttons()))

  def _create_repeats(self):
    self._repeats = RepeatComponent(is_enabled = False)
    self._repeats_layer = Layer(
      parameter_buttons = self._scene_launch_buttons)
    self._repeats.set_device(find_if(lambda d: d.name == 'Repeats', self.song().master_track.devices))

  def _create_ppm(self):
    self._ppm = PPMeter(self.song().master_track)
    self._ppm_layer = Layer(target_matrix = ButtonMatrixElement(rows=[self._scene_launch_buttons_raw[::-1]]))

  def _create_looper(self):
    mutes = self._mute_buttons._orig_buttons[0]
    fades = self._crossfade_buttons._orig_buttons[0]
    self._looper = LooperComponent(is_enabled = False, layer = Layer(
      toggle_button = mutes[4],
      start_button = fades[4],
      halve_button = mutes[5],
      double_button = fades[5],
      left_button = mutes[6],
      right_button = fades[6],
      nudge_left_button = mutes[7],
      nudge_right_button = fades[7]))

  def _create_session(self):
    """ We use two session objects, one of which never moves """
    def when_bank_on(button):
      return self._bank_toggle.create_toggle_element(on_control=button)
    def when_bank_off(button):
      return self._bank_toggle.create_toggle_element(off_control=button)

    self._session = SessionComponent(NUM_TRACKS - 4, NUM_SCENES, auto_name=True, is_enabled=False, enable_skinning=True,
          layer = Layer(track_bank_left_button=when_bank_off(self._left_button),
          track_bank_right_button=when_bank_off(self._right_button),
          scene_bank_up_button=when_bank_off(self._up_button),
          scene_bank_down_button=when_bank_off(self._down_button),
          page_left_button=when_bank_on(self._left_button),
          page_right_button=when_bank_on(self._right_button),
          page_up_button=when_bank_on(self._up_button),
          page_down_button=when_bank_on(self._down_button),
          stop_track_clip_buttons=self._stop_buttons.submatrix[:4, :1],
          stop_all_clips_button=self._stop_all_button,
          clip_launch_buttons=self._session_matrix.submatrix[:4, :5]))
    clip_color_table = LIVE_COLORS_TO_MIDI_VALUES.copy()
    clip_color_table[16777215] = 119
    self._session.set_rgb_mode(clip_color_table, RGB_COLOR_TABLE)
    self._session_zoom = SessionZoomingComponent(self._session, name='Session_Overview', enable_skinning=True, is_enabled=False, layer=Layer(button_matrix=self._shifted_matrix, nav_left_button=self._with_shift(self._left_button), nav_right_button=self._with_shift(self._right_button), nav_up_button=self._with_shift(self._up_button), nav_down_button=self._with_shift(self._down_button), scene_bank_buttons=self._shifted_scene_buttons))

    self._dummy_clip_session = SessionComponent(NUM_TRACKS - 4,
        NUM_SCENES, auto_name=True, is_enabled=False, enable_skinning=True,
          layer = Layer(
            clip_launch_buttons=self._session_matrix.submatrix[4:8, :5]))
    self._dummy_clip_session.set_rgb_mode(clip_color_table, RGB_COLOR_TABLE)
    self._dummy_clip_session.set_offsets(4, 2)
    self._session.set_offsets(0, 2)



  def _create_mixer(self):
    """ Disabling the second group of four:
    Arms, Mutes, Crossfaders, Solos, Selects """
    self._mixer = MixerComponent(NUM_TRACKS, auto_name=True, is_enabled=False, invert_mute_feedback=True)
    self._mixer.master_strip().layer = Layer(volume_control=self._master_volume_control, select_button=self._master_select_button)
    self._encoder_mode = ModesComponent(name='Encoder_Mode', is_enabled=False)
    self._encoder_mode.default_behaviour = ImmediateBehaviour()
    self._encoder_mode.add_mode('pan', [AddLayerMode(self._mixer, Layer(pan_controls=self._mixer_encoders))])
    self._encoder_mode.add_mode('sends', [AddLayerMode(self._mixer, Layer(send_controls=self._mixer_encoders)), DelayMode(AddLayerMode(self._mixer, Layer(send_select_buttons=self._send_select_buttons)))])
    self._encoder_mode.add_mode('user', [AddLayerMode(self._mixer, Layer(user_controls=self._mixer_encoders))])
    self._encoder_mode.layer = Layer(pan_button=self._pan_button, sends_button=self._sends_button, user_button=self._user_button)
    self._encoder_mode.selected_mode = 'pan'
    self._mixer.layer = Layer(
          volume_controls=self._volume_controls,
          arm_buttons=self._arm_buttons.submatrix[:4, :1],
          solo_buttons=self._solo_buttons.submatrix[:4, :1],
          mute_buttons=self._mute_buttons.submatrix[:4, :1],
          track_select_buttons=self._select_buttons.submatrix[:4, :1],
          crossfade_buttons=self._crossfade_buttons.submatrix[:4, :1],
          shift_button=self._shift_button,
          prehear_volume_control=self._prehear_control,
          crossfader_control=self._crossfader_control)

    self._drum_chan = None
    for track in self.song().tracks:
      if track.name == 'Drums':
        self._drum_chan = ChanStripComponent()
        self._drum_chan.set_track(track)
        self._drum_chan.layer = Layer(select_button = self._master_select_button, volume_control =
            self._master_volume_control)


  def _create_sequencer(self):
    """ Live 11 wires the note editor and the drum group up from outside,
    the way the stock Push script does """
    self._velocity_provider = VelocityProvider()
    self._note_editor = APCNoteEditorComponent(
        clip_creator = ClipCreator(),
        grid_resolution = self._grid_resolution,
        velocity_provider = self._velocity_provider,
        is_enabled = False)
    self._drum_group = APCDrumGroupComponent(is_enabled = False)
    self._note_editor_settings = NoteEditorSettingsComponent(
        grid_resolution = self._grid_resolution,
        initial_encoder_layer = Layer(initial_encoders = self._mixer_encoders),
        encoder_layer = Layer(encoders = self._mixer_encoders),
        is_enabled = False)
    self._note_editor_settings.add_editor(self._note_editor)
    self._sequencer = StepSeqComponent(
        clip_creator = ClipCreator(),
        skin = make_rgb_skin(),
        grid_resolution = self._grid_resolution,
        note_editor_component = self._note_editor,
        instrument_component = self._drum_group,
        velocity_provider = self._velocity_provider,
        is_enabled = False)

  def _create_session_mode(self):
    """ Switch between Session and StepSequencer modes """
    self._session_mode = ModesComponent(name='Session_Mode', is_enabled = False)
    self._session_mode.default_behaviour = ImmediateBehaviour()
    self._session_mode.add_mode('session', self._session_mode_layers())
    self._session_mode.add_mode('session_2', self._session_mode_layers())
    self._session_mode.add_mode('sequencer', self._sequencer_mode_layers())
    self._session_mode.layer = Layer(
        session_button = self._pan_button,
        session_2_button = self._sends_button,
        sequencer_button = self._user_button)
    self._session_mode.selected_mode = "session"

  def _session_mode_layers(self):
    return [ self._session, self._session_zoom,
        ComponentLayerMode(self._repeats, self._repeats_layer),
        ComponentLayerMode(self._ppm, self._ppm_layer)]

  def _sequencer_mode_layers(self):
    return [
      ComponentMode(self._note_editor),
      ComponentLayerMode(self._drum_group, self._drum_group_layer()),
      ComponentMode(self._note_editor_settings),
      ComponentLayerMode(self._sequencer, self._sequencer_layer())]

  def _stepper_buttons(self):
    return self._select_buttons.submatrix[4:8, :1]

  def _drum_group_layer(self):
    """ Live 11 takes the pad matrix and the bank buttons on the drum group
    itself rather than through the step sequencer """
    return Layer(
        matrix = self._session_matrix.submatrix[:4, 1:5],
        scroll_page_up_button = self._up_button,
        scroll_page_down_button = self._down_button)

  def _sequencer_layer(self):
    return Layer(
        velocity_slider = self._velocity_slider,
        button_matrix = self._double_press_matrix.submatrix[4:8, 1:5],
        select_button = self._user_button,
        delete_button = self._stop_all_button,
        playhead = self._playhead,
        quantization_buttons = self._stop_buttons,
        mute_button = self._shift_button,
        loop_selector_matrix = self._double_press_matrix.submatrix[:8, :1],
        short_loop_selector_matrix = self._double_press_event_matrix.submatrix[:8, :1])

  def _init_auto_arm(self):
    self._auto_arm = AutoArmComponent(is_enabled = True)

  # EVENT HANDLING FUNCTIONS
  def reset_controlled_track(self):
    self.set_controlled_track(self.song().view.selected_track)

  def update(self):
    self.reset_controlled_track()
    super(APCAdvanced_MkII, self).update()
    with self.component_guard():
      for component in self._v2_components:
        if component.is_enabled():
          component.update()

  def disconnect(self):
    for component in self._v2_components:
      component.disconnect()
    self._v2_components = []
    super(APCAdvanced_MkII, self).disconnect()

  def set_enabled(self, enable):
    super(APCAdvanced_MkII, self).set_enabled(enable)
    for component in self._v2_components:
      if component.is_root:
        component._set_enabled_recursive(bool(enable))

  @contextmanager
  def component_guard(self):
    """ Customized to inject additional things.

    Both injectors wrap the inherited guard rather than sitting inside it, so
    they are still registered while OptimizedControlSurface commits the
    ownership changes it defers to the end of the guard.
    """
    with self.make_injector().everywhere():
      with self._v2_injector:
        with super(APCAdvanced_MkII, self).component_guard():
          yield

  def make_injector(self):
    """ Adds some additional stuff to the injector, used in BaseMessenger """
    return inject(
      double_press_context = const(self._double_press_context),
      control_surface = const(self),
      log_message = const(self.log_message))

  @lazy_attribute
  def _v2_injector(self):
    """ Live 11's Push components come from ableton.v2, which keeps its own
    injection registry. Without this they cannot resolve song or
    register_component and refuse to be built """
    return v2_inject(
      element_ownership_handler = v2_const(self._optimized_ownership_handler),
      parent_task_group = v2_const(self._task_group),
      show_message = v2_const(self.show_message),
      register_component = v2_const(self._register_v2_component),
      register_control = v2_const(self._register_control),
      request_rebuild_midi_map = v2_const(self.request_rebuild_midi_map),
      set_pad_translations = v2_const(self.set_pad_translations),
      send_midi = v2_const(self._send_midi),
      song = v2_const(self.song()),
      set_session_highlight = v2_const(self._c_instance.set_session_highlight)).everywhere()

  def _register_v2_component(self, component):
    """ ableton.v2 components don't implement the _Framework component
    callbacks, so they are kept out of self._components and updated here """
    self._v2_components.append(component)
