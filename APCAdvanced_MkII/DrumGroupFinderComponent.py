from itertools import chain
import Live
from ableton.v2.base import find_if, listens, listens_group, liveobj_changed
from ableton.v2.control_surface import Component

def find_instrument_devices(track_or_chain):
  instrument = find_if(lambda d: d.type == Live.Device.DeviceType.instrument, track_or_chain.devices)
  if instrument and not instrument.can_have_drum_pads and instrument.can_have_chains:
    return chain([instrument], *map(find_instrument_devices, instrument.chains))
  return []


def find_drum_group_device(track_or_chain):
  instrument = find_if(lambda d: d.type == Live.Device.DeviceType.instrument, track_or_chain.devices)
  if instrument:
    if instrument.can_have_drum_pads:
      return instrument
    if instrument.can_have_chains:
      return find_if(bool, map(find_drum_group_device, instrument.chains))


class DrumGroupFinderComponent(Component):
  """ Finds the drum rack on the selected track, however deeply nested.

  Live 11 dropped Push's DrumGroupFinderComponent, so it lives here now.
  """
  __events__ = ('drum_group',)
  _drum_group = None

  def __init__(self, *a, **k):
    super(DrumGroupFinderComponent, self).__init__(*a, **k)
    self._on_selected_track_changed.subject = self.song.view
    self.update()

  @property
  def drum_group(self):
    return self._drum_group

  @property
  def root(self):
    return self.song.view.selected_track

  @listens_group('devices')
  def _on_devices_changed(self, chain):
    self.update()

  @listens_group('chains')
  def _on_chains_changed(self, chain):
    self.update()

  @listens('selected_track')
  def _on_selected_track_changed(self):
    self.update()

  def update(self):
    super(DrumGroupFinderComponent, self).update()
    if self.is_enabled():
      self._update_listeners()
      self._update_drum_group()

  def _update_listeners(self):
    root = self.root
    devices = list(find_instrument_devices(root))
    chains = list(chain([root], *[d.chains for d in devices]))
    self._on_chains_changed.replace_subjects(devices)
    self._on_devices_changed.replace_subjects(chains)

  def _update_drum_group(self):
    drum_group = find_drum_group_device(self.root)
    if liveobj_changed(self._drum_group, drum_group):
      self._drum_group = drum_group
      self.notify_drum_group()
