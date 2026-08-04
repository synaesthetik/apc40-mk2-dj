from APC40_MkII.MixerComponent import MixerComponent as MixerComponentBase, ChannelStripComponent as ChannelStripComponentBase
from APCMessenger import APCMessenger

class ChanStripComponent(ChannelStripComponentBase, APCMessenger):
  """ Customized to select playing clip when selected """

  def _select_value(self, value):
    super(ChanStripComponent, self)._select_value(value)
    if value > 0 and self.song().is_playing:
      self._go_to_playing_clip()


  def _go_to_playing_clip(self):
    if self._track and self._track.fired_slot_index is -1:
      song_view = self.song().view
      playing_clip_slot = self._playing_clip_slot()
      if playing_clip_slot:
        song_view.highlighted_clip_slot = playing_clip_slot
        song_view.detail_clip = playing_clip_slot.clip
        self.application().view.show_view('Detail/Clip')

  def _playing_clip_slot(self):
    track = self._track
    try:
      playing_slot_index = track.playing_slot_index
      slot = track.clip_slots[playing_slot_index] if 0 <= playing_slot_index < len(track.clip_slots) else None
      return slot
    except RuntimeError:
      pass

class MixerComponent(MixerComponentBase, APCMessenger):
    """ Customized to use a different chan strip """
    def _create_strip(self):
      return ChanStripComponent()
