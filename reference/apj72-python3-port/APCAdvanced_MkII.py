
import sys
from functools import partial
from contextlib import contextmanager
#  AJ Added START
from AJsCustomModule import create_fx_knobs, GlobalFXComponent, setup_loop_buttons
from AJsCustomModule import ColorCycler
#  AJ Added END

# from itertools import izip  # Remove or comment out
izip = zip  # Add this line for compatibility

# Monkeypatch things
from . import ControlElementUtils
from . import SessionComponent
from . import SkinDefault
sys.modules['_APC.ControlElementUtils'] = ControlElementUtils
sys.modules['_APC.SessionComponent'] = SessionComponent
sys.modules['_APC.SkinDefault'] = SkinDefault

from _Framework.ModesComponent import ModesComponent, ImmediateBehaviour, AddLayerMode, DelayMode
from _Framework.Layer import Layer
from _Framework.SessionZoomingComponent import SessionZoomingComponent
from _Framework.Dependency import inject
from _Framework.Util import const, recursive_map, find_if
from _Framework.Dependency import inject
from _Framework.ComboElement import ComboElement, DoublePressElement, MultiElement, DoublePressContext
from _Framework.ButtonMatrixElement import ButtonMatrixElement 
from _Framework.SubjectSlot import subject_slot
from _Framework.Resource import PrioritizedResource, SharedResource
from _APC.APC import APC
from APC40_MkII import Colors
from .MixerComponent import MixerComponent, ChanStripComponent
# from pushbase import colors
from pushbase.colors import Rgb, Pulse, Blink


from APC40_MkII.APC40_MkII import APC40_MkII, NUM_SCENES, NUM_TRACKS
from _APC.APC import APC
from _APC.SkinDefault import make_rgb_skin, make_default_skin, make_stop_button_skin, make_crossfade_button_skin
from .SkinDefault import make_rgb_skin, make_default_skin, make_stop_button_skin, make_crossfade_button_skin
from .SessionComponent import SessionComponent
from .StepSeqComponent import StepSeqComponent
from .MatrixMaps import PAD_TRANSLATIONS, FEEDBACK_CHANNELS
from .ButtonSliderElement import ButtonSliderElement
from .PPMeter import PPMeter
from .RepeatComponent import RepeatComponent
from .LooperComponent import LooperComponent

class APCAdvanced_MkII(APC40_MkII):
  """ APC40Mk2 script with step sequencer mode """
  # def __init__(self, *a, **k):
  #   self._double_press_context = DoublePressContext()
  #   APC40_MkII.__init__(self, *a, **k)
  #   with self.component_guard():
  #     self._create_repeats()
  #     self._create_ppm()
  #     self._create_looper()
      
  def __init__(self, *a, **k):
    super(APC40_MkII, self).__init__(*a, **k)

# --- AJ START Map Device Control knobs (label 20) to global FX ---
    device_knobs = create_device_knobs()
    self._global_fx = GlobalFXComponent(device_knobs)
    self._global_fx.set_device(self.song().master_track.devices[0])  # First FX device on master

# Example: apply to 4 clip launch buttons (note values 0, 1, 2, 3 on channel 0)
    clip_launch_buttons = [create_loop_pad(note) for note in [0, 1, 2, 3]]  # or use proper ButtonElement instances

    self._color_cyclers = [ColorCycler(btn) for btn in clip_launch_buttons]
# --- Map  AJ END


    self._color_skin = make_rgb_skin()
    self._default_skin = make_default_skin()
    self._stop_button_skin = make_stop_button_skin()
    self._crossfade_button_skin = make_crossfade_button_skin()
    with self.component_guard():
      self._create_controls()
      self._create_bank_toggle()
      self._create_session()
      self._create_mixer()
      self._create_transport()
      self._create_device()
      self._create_view_control()
      self._create_quantization_selection()
      self._create_recording()
      self._session.set_mixer(self._mixer)
      
      # MY MODS
      self._create_repeats()
      self._create_ppm()
      self._create_looper()
      
    self.set_highlighting_session_component(self._session)
    self.set_device_component(self._device)

  def _create_repeats(self):
    for button in self._scene_launch_buttons_raw:
      button._resource_type = PrioritizedResource
    self._repeats = RepeatComponent(is_enabled = False, parent = self) 
    self._repeats.layer = Layer(
      parameter_buttons = self._scene_launch_buttons)
    self._repeats.set_device(find_if(lambda d: d.name == 'Repeats', self.song().master_track.devices))
    self.log_message("Repeat Components Set")

  def _create_ppm(self):
    self._ppm = PPMeter(self.song().master_track, self)
    self._ppm_layer = Layer(target_matrix = ButtonMatrixElement(rows=[self._scene_launch_buttons_raw[::-1]])) 
    self._ppm.layer = self._ppm_layer

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
    # clip_color_table = colors.CLIP_COLOR_TABLE.copy()
    clip_color_table = Colors.LIVE_COLORS_TO_MIDI_VALUES.copy()
    clip_color_table[16777215] = 119
    self._session.set_rgb_mode(clip_color_table, Colors.RGB_COLOR_TABLE)
    self._session_zoom = SessionZoomingComponent(self._session, name='Session_Overview', enable_skinning=True, is_enabled=False, layer=Layer(button_matrix=self._shifted_matrix, nav_left_button=self._with_shift(self._left_button), nav_right_button=self._with_shift(self._right_button), nav_up_button=self._with_shift(self._up_button), nav_down_button=self._with_shift(self._down_button), scene_bank_buttons=self._shifted_scene_buttons))

    self._dummy_clip_session = SessionComponent(NUM_TRACKS - 4, 
        NUM_SCENES, auto_name=True, is_enabled=False, enable_skinning=True, 
          layer = Layer(
            clip_launch_buttons=self._session_matrix.submatrix[4:8, :5]))
    self._dummy_clip_session.set_rgb_mode(clip_color_table, Colors.RGB_COLOR_TABLE)
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
            
  # @contextmanager
  # def component_guard(self):
  #   """ Customized to inject additional things """
  #   with super(APCAdvanced_MkII, self).component_guard():
  #     with self.make_injector().everywhere():
  #       with self._control_surface_injector:
  #         yield
  #
  # def make_injector(self):
  #   """ Adds some additional stuff to the injector, used in BaseMessenger """
  #   return inject(
  #     double_press_context = const(self._double_press_context),
  #     control_surface = const(self),
  #     log_message = const(self.log_message))
